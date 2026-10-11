"""External-work orchestration for queued initial Card candidate groups."""

from __future__ import annotations

import logging

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupRepository,
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
