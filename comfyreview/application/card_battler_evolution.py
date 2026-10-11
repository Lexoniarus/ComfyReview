"""Persistent four-slot Card evolution orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Protocol

from comfyreview.application.card_battler_evolution_images import (
    CardReferenceImageStager,
)
from comfyreview.application.card_battler_generation_prompt import (
    CardEvolutionComfyUiPromptRenderer,
    CardEvolutionPromptAdapter,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_semantics import CardSourceImage
from comfyreview.application.card_battler_sessions import (
    CardSession,
    CardSessionConflictError,
    CardSessionOperationState,
    CardSessionRepository,
)
from comfyreview.application.comfyui import ComfyUiError
from comfyreview.application.generation import (
    GenerationCanvas,
    GenerationMutationError,
    GenerationOutputPolicy,
    GenerationPort,
    GenerationPromptSnapshot,
    GenerationReconciliationRequired,
    GenerationRequest,
    GenerationSamplerSettings,
    GenerationSubmission,
    GenerationValidationError,
)
from comfyreview.application.generation_outputs import GenerationOutput

CARD_EVOLUTION_GENERATION_POLICY_REVISION = "card-evolution-generation-v1"
_CANDIDATE_COUNT = 4


class CardCandidateStatus(StrEnum):
    """Name one stable Card evolution candidate lifecycle state."""

    PENDING = "pending"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
    ACCEPTED = "accepted"


@dataclass(frozen=True, slots=True)
class CardEvolutionCandidate:
    """Persist one slot tied to an exact session, tier, recipe and reference."""

    candidate_id: str
    session_id: str
    session_revision: int
    slot_index: int
    tier_ordinal: int
    recipe_revision: str
    recipe_hash: str
    reference_image_uid: str
    reference_content_hash: str
    status: CardCandidateStatus
    generation_uid: str | None = None
    failure_category: str | None = None
    output_image_uid: str | None = None

    def __post_init__(self) -> None:
        if not 0 <= self.slot_index < _CANDIDATE_COUNT:
            raise ValueError("Card candidate slot is invalid")
        if self.session_revision < 1 or self.tier_ordinal < 1:
            raise ValueError(
                "Card candidate revision and tier must be positive"
            )
        required = (
            self.candidate_id,
            self.session_id,
            self.recipe_revision,
            self.recipe_hash,
            self.reference_image_uid,
            self.reference_content_hash,
        )
        if any(not item for item in required):
            raise ValueError("Card candidate provenance must be complete")


class CardCandidateRepository(Protocol):
    """Persist four-slot batches and atomic Candidate acceptance."""

    def reserve(
        self,
        session_id: str,
        *,
        expected_revision: int,
        candidates: tuple[CardEvolutionCandidate, ...],
    ) -> CardSession:
        """Reserve one exact four-slot batch and advance the session revision."""
        ...

    def list_for_session(
        self, session_id: str, *, session_revision: int
    ) -> tuple[CardEvolutionCandidate, ...]:
        """Return stable slot order for one batch revision."""
        ...

    def latest_for_session(
        self, session_id: str
    ) -> tuple[CardEvolutionCandidate, ...]:
        """Return the latest persisted batch in stable slot order."""
        ...

    def mark_submitted(
        self, candidate_id: str, generation_uid: str
    ) -> CardEvolutionCandidate:
        """Attach one accepted shared-generation lifecycle."""
        ...

    def mark_failed(
        self, candidate_id: str, failure_category: str
    ) -> CardEvolutionCandidate:
        """Mark one independent slot failure."""
        ...

    def mark_completed(
        self, candidate_id: str, output: GenerationOutput
    ) -> CardEvolutionCandidate:
        """Attach the one validated primary output."""
        ...

    def accept(
        self,
        session_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardSession:
        """Atomically select one current completed Candidate."""
        ...


class CardSessionReferenceImageProvider(Protocol):
    """Load bytes for either original or accepted active Card reference."""

    def load(self, session: CardSession) -> CardSourceImage:
        """Return verified active image bytes."""
        ...


class CardGenerationLifecycle(GenerationPort, Protocol):
    """Submit and observe one shared GenerationService lifecycle."""

    def observe(self, generation_uid: str) -> GenerationSubmission:
        """Refresh one external generation without blocking."""
        ...


class CardGenerationOutputQuery(Protocol):
    """Read the validated primary output collected for a Card generation."""

    def primary_output(self, generation_uid: str) -> GenerationOutput | None:
        """Return exactly one primary output when collected."""
        ...


class CardEvolutionGenerationPolicy:
    """Build one fresh GenerationRequest from the current recipe only."""

    def __init__(self, *, checkpoint: str) -> None:
        if not checkpoint.strip():
            raise ValueError("Card evolution checkpoint is required")
        self._checkpoint = checkpoint

    def build_requests(
        self,
        session: CardSession,
        *,
        staged_reference: str,
    ) -> tuple[GenerationRequest, ...]:
        """Build four deterministic requests with independent seed domains."""
        if not staged_reference.strip():
            raise ValueError("staged reference image is required")
        handoff = CardEvolutionPromptAdapter.adapt(session.visual_recipe)
        rendered = CardEvolutionComfyUiPromptRenderer.render(handoff)
        if not rendered.positive_prompt or not rendered.negative_prompt:
            raise ValueError(
                "Card evolution recipe requires both prompt channels"
            )
        recipe_hash = _recipe_hash(session)
        random = DomainSeparatedCardRandom(
            (
                CARD_EVOLUTION_GENERATION_POLICY_REVISION,
                session.session_id,
                str(session.revision),
                str(session.card.tier_ordinal),
                recipe_hash,
                session.active_content_hash,
            )
        )
        return tuple(
            GenerationRequest(
                prompt=GenerationPromptSnapshot(
                    rendered.positive_prompt,
                    rendered.negative_prompt,
                    (),
                ),
                blueprint_uid="card-evolution",
                blueprint_version=1,
                model_branch="card-evolution",
                combo_key=(
                    f"{session.session_id}:tier-{session.card.tier_ordinal}:"
                    f"candidate-{slot}"
                ),
                checkpoint=self._checkpoint,
                sampler_stages=(
                    GenerationSamplerSettings(
                        role="base_sampler",
                        seed=random.integer(
                            f"evolution:{session.card.tier_ordinal}:candidate:{slot}",
                            modulo=2**63 - 1,
                        ),
                        steps=32,
                        cfg=6.0,
                        sampler="sa_solver",
                        scheduler="simple",
                        denoise=0.55,
                    ),
                ),
                output_policy=GenerationOutputPolicy(
                    "card-battler",
                    f"{session.session_id}-t{session.card.tier_ordinal}-c{slot}",
                    ("primary",),
                ),
                reference_image=staged_reference,
                canvas=GenerationCanvas(1024, 1024),
            )
            for slot in range(_CANDIDATE_COUNT)
        )


class CardEvolutionService:
    """Reserve, submit, synchronize and accept four persistent Candidates."""

    def __init__(
        self,
        *,
        sessions: CardSessionRepository,
        candidates: CardCandidateRepository,
        reference_images: CardSessionReferenceImageProvider,
        stager: CardReferenceImageStager,
        policy: CardEvolutionGenerationPolicy,
        generations: CardGenerationLifecycle,
        outputs: CardGenerationOutputQuery,
    ) -> None:
        self._sessions = sessions
        self._candidates = candidates
        self._reference_images = reference_images
        self._stager = stager
        self._policy = policy
        self._generations = generations
        self._outputs = outputs

    def generate_candidates(
        self, session_id: str, *, expected_revision: int
    ) -> tuple[CardEvolutionCandidate, ...]:
        """Reserve four slots, then stage and submit each outside the lock."""
        session = self._required_session(session_id)
        if session.revision != expected_revision:
            raise CardSessionConflictError("Card session revision is stale")
        if session.operation_state is not CardSessionOperationState.IDLE:
            raise CardSessionConflictError(
                "Card session operation is in progress"
            )
        reserved_revision = expected_revision + 1
        reserved = tuple(
            _candidate(session, reserved_revision=reserved_revision, slot=slot)
            for slot in range(_CANDIDATE_COUNT)
        )
        reserved_session = self._candidates.reserve(
            session.session_id,
            expected_revision=expected_revision,
            candidates=reserved,
        )
        try:
            reference = self._reference_images.load(reserved_session)
            staged = self._stager.stage(reference)
            requests = self._policy.build_requests(
                reserved_session,
                staged_reference=staged.relative_name,
            )
        except (ComfyUiError, FileNotFoundError, OSError, ValueError) as error:
            for candidate in reserved:
                self._candidates.mark_failed(
                    candidate.candidate_id, type(error).__name__
                )
            return self._candidates.list_for_session(
                session_id,
                session_revision=reserved_revision,
            )
        for candidate, request in zip(reserved, requests, strict=True):
            try:
                submission = self._generations.submit(request)
                self._candidates.mark_submitted(
                    candidate.candidate_id,
                    submission.generation_uid,
                )
            except (
                GenerationMutationError,
                GenerationReconciliationRequired,
                GenerationValidationError,
            ) as error:
                self._candidates.mark_failed(
                    candidate.candidate_id,
                    type(error).__name__,
                )
        return self._candidates.list_for_session(
            session_id,
            session_revision=reserved_revision,
        )

    def synchronize(
        self, session_id: str, *, session_revision: int
    ) -> tuple[CardEvolutionCandidate, ...]:
        """Observe submitted slots once and attach collected primary outputs."""
        candidates = self._candidates.list_for_session(
            session_id,
            session_revision=session_revision,
        )
        for candidate in candidates:
            if (
                candidate.status is not CardCandidateStatus.SUBMITTED
                or candidate.generation_uid is None
            ):
                continue
            try:
                submission = self._generations.observe(
                    candidate.generation_uid
                )
            except (
                GenerationReconciliationRequired,
                GenerationValidationError,
            ) as error:
                self._candidates.mark_failed(
                    candidate.candidate_id,
                    type(error).__name__,
                )
                continue
            if submission.status == "failed":
                self._candidates.mark_failed(
                    candidate.candidate_id, "generation_failed"
                )
            elif submission.status == "completed":
                output = self._outputs.primary_output(candidate.generation_uid)
                if output is None:
                    self._candidates.mark_failed(
                        candidate.candidate_id,
                        "primary_output_missing",
                    )
                else:
                    self._candidates.mark_completed(
                        candidate.candidate_id, output
                    )
        return self._candidates.list_for_session(
            session_id,
            session_revision=session_revision,
        )

    def accept(
        self,
        session_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardSession:
        """Accept one completed current Candidate without changing Card facts."""
        return self._candidates.accept(
            session_id,
            candidate_id,
            expected_revision=expected_revision,
        )

    def _required_session(self, session_id: str) -> CardSession:
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"Unknown Card session: {session_id}")
        return session


def _recipe_hash(session: CardSession) -> str:
    payload = json.dumps(
        asdict(session.visual_recipe),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _candidate(
    session: CardSession,
    *,
    reserved_revision: int,
    slot: int,
) -> CardEvolutionCandidate:
    recipe_hash = _recipe_hash(session)
    identity = hashlib.sha256(
        (
            f"{session.session_id}\0{reserved_revision}\0{slot}\0"
            f"{session.card.tier_ordinal}\0{recipe_hash}\0"
            f"{session.active_content_hash}"
        ).encode()
    ).hexdigest()
    return CardEvolutionCandidate(
        candidate_id="card-candidate-" + identity,
        session_id=session.session_id,
        session_revision=reserved_revision,
        slot_index=slot,
        tier_ordinal=session.card.tier_ordinal,
        recipe_revision=(
            session.visual_recipe.provenance.visual_projection_algorithm_revision
        ),
        recipe_hash=recipe_hash,
        reference_image_uid=session.active_image_uid,
        reference_content_hash=session.active_content_hash,
        status=CardCandidateStatus.PENDING,
    )
