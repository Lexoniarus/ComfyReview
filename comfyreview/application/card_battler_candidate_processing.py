"""External-work orchestration for queued initial Card candidate groups."""

from __future__ import annotations

import logging
from threading import Event, Lock, Thread
from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupKind,
    CardCandidateGroupRepository,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_candidate_image_service import (
    CardCandidateImageService,
)
from comfyreview.application.card_battler_card_pool import CardPoolRepository
from comfyreview.application.card_battler_development_groups import (
    CardDevelopmentCandidateComposer,
)
from comfyreview.application.card_battler_factory import CardFactory
from comfyreview.application.card_battler_semantics import (
    CardSourceImageProvider,
    SemanticImageAnalyzer,
)


class InitialCardCandidateGroupProcessor:
    """Claim, analyze, compose, and persist one queued initial group."""

    def __init__(
        self,
        *,
        groups: CardCandidateGroupRepository,
        source_images: CardSourceImageProvider,
        analyzer: SemanticImageAnalyzer,
        factory: CardFactory,
    ) -> None:
        self._groups = groups
        self._source_images = source_images
        self._analyzer = analyzer
        self._factory = factory
        self._logger = logging.getLogger("comfyreview.card_battler.candidates")

    def recover_interrupted(self) -> int:
        """Fail interrupted compositions without repeating model inference."""
        return self._groups.fail_interrupted_compositions()

    def process_next(self) -> bool:
        """Process at most one queued group outside repository transactions."""
        group = self._groups.claim_next_queued()
        if group is None:
            return False
        self._logger.info(
            "card_battler.candidate_group.composition_started",
            extra={"group_id": group.group_id},
        )
        try:
            source = self._source_images.load(group.source_image_uid)
            if source.content_hash != group.source_content_hash:
                raise ValueError("candidate source content changed")
            semantic_profile = self._analyzer.analyze(source)
            composition = self._factory.compose_candidates(
                semantic_profile,
                group_seed=group.group_seed,
            )
            persisted = self._groups.complete_composition(
                group.group_id,
                expected_revision=group.revision,
                semantic_profile=semantic_profile,
                imprint=composition.mapping.imprint,
                candidates=composition.candidates,
            )
        except Exception as error:
            self._groups.fail_composition(
                group.group_id,
                expected_revision=group.revision,
                failure_category=type(error).__name__,
            )
            self._logger.warning(
                "card_battler.candidate_group.composition_failed",
                extra={
                    "group_id": group.group_id,
                    "error_type": type(error).__name__,
                },
            )
            return True
        self._logger.info(
            "card_battler.candidate_group.composition_completed",
            extra={
                "group_id": persisted.group_id,
                "group_revision": persisted.revision,
            },
        )
        return True


class DevelopmentCardCandidateGroupProcessor:
    """Compose queued development groups from one current confirmed Card."""

    def __init__(
        self,
        *,
        groups: CardCandidateGroupRepository,
        cards: CardPoolRepository,
        composer: CardDevelopmentCandidateComposer,
    ) -> None:
        self._groups = groups
        self._cards = cards
        self._composer = composer
        self._logger = logging.getLogger("comfyreview.card_battler.candidates")

    def process_next(self) -> bool:
        """Compose one development group without analysis or remapping."""
        group = self._groups.claim_next_queued(
            CardCandidateGroupKind.DEVELOPMENT
        )
        if group is None:
            return False
        self._logger.info(
            "card_battler.development_group.composition_started",
            extra={"group_id": group.group_id},
        )
        try:
            if (
                group.source_card_id is None
                or group.source_card_revision is None
            ):
                raise ValueError("development group source Card is missing")
            card = self._cards.get(group.source_card_id)
            if (
                card is None
                or card.state.revision != group.source_card_revision
            ):
                raise ValueError("development source Card revision changed")
            composition = self._composer.compose(
                card,
                tuple(
                    candidate.materialization_seed
                    for candidate in group.candidates
                ),
            )
            persisted = self._groups.complete_development_composition(
                group.group_id,
                expected_revision=group.revision,
                candidates=composition.candidates,
            )
        except Exception as error:
            self._groups.fail_composition(
                group.group_id,
                expected_revision=group.revision,
                failure_category=type(error).__name__,
            )
            self._logger.warning(
                "card_battler.development_group.composition_failed",
                extra={
                    "group_id": group.group_id,
                    "error_type": type(error).__name__,
                },
            )
            return True
        self._logger.info(
            "card_battler.development_group.composition_completed",
            extra={
                "group_id": persisted.group_id,
                "group_revision": persisted.revision,
            },
        )
        return True


class CardCandidateCompositionCoordinator:
    """Prioritize initial analysis before bounded development composition."""

    def __init__(
        self,
        *,
        initial: InitialCardCandidateGroupProcessor,
        development: DevelopmentCardCandidateGroupProcessor,
    ) -> None:
        self._initial = initial
        self._development = development

    def recover_interrupted(self) -> int:
        """Fail all composition work interrupted before process startup."""
        return self._initial.recover_interrupted()

    def process_next(self) -> bool:
        """Compose at most one initial or development group."""
        return self._initial.process_next() or self._development.process_next()


class CardCandidateGroupLifecycleProcessor:
    """Advance composition, submission, or observation by one bounded pass."""

    def __init__(
        self,
        *,
        composition: CardCandidateGroupProcessingPass,
        groups: CardCandidateGroupRepository,
        images: CardCandidateImageService,
    ) -> None:
        self._composition = composition
        self._groups = groups
        self._images = images
        self._poll_index = 0

    def recover_interrupted(self) -> int:
        """Fail only interrupted inference/composition work."""
        return self._composition.recover_interrupted()

    def process_next(self) -> bool:
        """Advance one queued or generating group without a busy poll loop."""
        if self._composition.process_next():
            return True
        groups = self._groups.generating_groups()
        if not groups:
            return False
        composing = next(
            (
                group
                for group in groups
                if any(
                    candidate.status is CardCandidateStatus.COMPOSING
                    for candidate in group.candidates
                )
            ),
            None,
        )
        if composing is not None:
            self._images.submit(
                composing.group_id,
                expected_revision=composing.revision,
            )
            return True
        group = groups[self._poll_index % len(groups)]
        self._poll_index += 1
        synchronized = self._images.synchronize(
            group.group_id,
            expected_revision=group.revision,
        )
        return synchronized.revision != group.revision


class CardCandidateGroupProcessingPass(Protocol):
    """Expose one recoverable candidate-group polling pass."""

    def recover_interrupted(self) -> int:
        """Fail groups interrupted before the current process started."""
        ...

    def process_next(self) -> bool:
        """Process at most one queued group."""
        ...


class CardCandidateGroupWorker:
    """Own exactly one polling thread for Card candidate composition."""

    def __init__(
        self,
        processor: CardCandidateGroupProcessingPass,
        *,
        poll_interval_seconds: float = 0.5,
    ) -> None:
        self._processor = processor
        self._poll_interval_seconds = max(
            0.05,
            float(poll_interval_seconds),
        )
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._logger = logging.getLogger("comfyreview.card_battler.candidates")

    def start(self) -> None:
        """Recover interrupted work and start one owned polling thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            recovered = self._processor.recover_interrupted()
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="comfyreview-card-candidate-groups",
                daemon=True,
            )
            self._thread.start()
        if recovered:
            self._logger.warning(
                "card_battler.candidate_group.interrupted_recovered",
                extra={"recovered_count": recovered},
            )

    def stop(self, *, timeout_seconds: float = 5.0) -> bool:
        """Request shutdown and report whether the worker stopped in time."""
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is None:
            return True
        thread.join(timeout=max(0.0, float(timeout_seconds)))
        stopped = not thread.is_alive()
        if stopped:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
        else:
            self._logger.warning(
                "card_battler.candidate_group.shutdown_timeout",
                extra={"error_type": "CardCandidateGroupShutdownTimeout"},
            )
        return stopped

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                processed = self._processor.process_next()
            except Exception as error:  # keep the owned resource alive
                self._logger.exception(
                    "card_battler.candidate_group.pass_failed",
                    extra={"error_type": type(error).__name__},
                )
                processed = False
            if not processed:
                self._stop_event.wait(self._poll_interval_seconds)
