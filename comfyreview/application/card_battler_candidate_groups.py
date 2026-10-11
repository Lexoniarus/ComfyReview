"""Immutable contracts for four-card candidate groups."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
)
from comfyreview.application.card_battler_semantics import SemanticImageProfile
from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.card_battler import CardImprint, StructuredCardSpec

CARD_CANDIDATE_COUNT = 4
CARD_CANDIDATE_MATERIALIZATION_REVISION = "card-candidate-materialization-v1"


class CardCandidateGroupKind(StrEnum):
    """Distinguish initial creation from development of a confirmed card."""

    INITIAL = "initial"
    DEVELOPMENT = "development"


class CardCandidateGroupStatus(StrEnum):
    """Name the persisted lifecycle of one four-card candidate group."""

    QUEUED = "queued"
    COMPOSING = "composing"
    GENERATING = "generating"
    READY = "ready"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"
    COMPLETED = "completed"
    REJECTED = "rejected"


class CardCandidateStatus(StrEnum):
    """Name one complete candidate slot lifecycle state."""

    QUEUED = "queued"
    COMPOSING = "composing"
    SUBMITTED = "submitted"
    COMPLETED = "completed"
    FAILED = "failed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


@dataclass(frozen=True, slots=True)
class CompleteCardCandidateArtifacts:
    """Hold every inspectable non-technical artifact of one candidate."""

    card: StructuredCardSpec
    visual_recipe: VisualPromptRecipe
    presentation: CardPresentationResult
    materialization_seed: int
    materialization_revision: str = CARD_CANDIDATE_MATERIALIZATION_REVISION

    def __post_init__(self) -> None:
        if self.materialization_seed < 0:
            raise ValueError(
                "Candidate materialization seed must not be negative"
            )
        if not self.materialization_revision.strip():
            raise ValueError("Candidate materialization revision is required")
        if self.visual_recipe.tier_ordinal != self.card.tier_ordinal:
            raise ValueError("Candidate recipe must match its Card tier")


@dataclass(frozen=True, slots=True)
class CardCandidate:
    """Represent one stable slot in a four-card comparison group."""

    candidate_id: str
    group_id: str
    group_revision: int
    slot_index: int
    status: CardCandidateStatus
    artifacts: CompleteCardCandidateArtifacts | None = None
    generation_uid: str | None = None
    failure_category: str | None = None
    output_image_uid: str | None = None
    output_content_hash: str | None = None

    def __post_init__(self) -> None:
        if not self.candidate_id.strip() or not self.group_id.strip():
            raise ValueError("Candidate identities must be non-empty")
        if self.group_revision < 1:
            raise ValueError("Candidate group revision must be positive")
        if not 0 <= self.slot_index < CARD_CANDIDATE_COUNT:
            raise ValueError("Candidate slot must be between zero and three")
        if (self.output_image_uid is None) != (
            self.output_content_hash is None
        ):
            raise ValueError(
                "Candidate output identity and hash are inseparable"
            )
        if (
            self.status
            in (
                CardCandidateStatus.SUBMITTED,
                CardCandidateStatus.COMPLETED,
                CardCandidateStatus.ACCEPTED,
            )
            and self.artifacts is None
        ):
            raise ValueError("Submitted candidates require complete artifacts")
        if (
            self.status
            in (
                CardCandidateStatus.COMPLETED,
                CardCandidateStatus.ACCEPTED,
            )
            and self.output_image_uid is None
        ):
            raise ValueError("Completed candidates require an output image")


@dataclass(frozen=True, slots=True)
class CardCandidateGroup:
    """Freeze one revisioned initial or development comparison group."""

    group_id: str
    revision: int
    kind: CardCandidateGroupKind
    status: CardCandidateGroupStatus
    source_image_uid: str
    source_content_hash: str
    group_seed: int
    candidates: tuple[CardCandidate, ...]
    semantic_profile: SemanticImageProfile | None = None
    imprint: CardImprint | None = None
    source_card_id: str | None = None
    source_card_revision: int | None = None
    failure_category: str | None = None

    def __post_init__(self) -> None:
        required = (
            self.group_id,
            self.source_image_uid,
            self.source_content_hash,
        )
        if any(not value.strip() for value in required):
            raise ValueError("Candidate group identities must be non-empty")
        if self.revision < 1 or self.group_seed < 0:
            raise ValueError("Candidate group revision and seed are invalid")
        if len(self.candidates) != CARD_CANDIDATE_COUNT:
            raise ValueError("Candidate group requires exactly four slots")
        if tuple(item.slot_index for item in self.candidates) != (0, 1, 2, 3):
            raise ValueError(
                "Candidate slots must be ordered zero through three"
            )
        if any(item.group_id != self.group_id for item in self.candidates):
            raise ValueError("Candidate belongs to another group")
        if (self.semantic_profile is None) != (self.imprint is None):
            raise ValueError(
                "Semantic profile and imprint become available together"
            )
        if self.semantic_profile is not None and (
            self.semantic_profile.image_uid != self.source_image_uid
            or self.imprint is None
            or self.imprint.source_image_uid != self.source_image_uid
            or self.imprint.semantic_revision
            != self.semantic_profile.semantic_revision
        ):
            raise ValueError("Candidate group source DNA is inconsistent")
        development = self.kind is CardCandidateGroupKind.DEVELOPMENT
        if development != (self.source_card_id is not None):
            raise ValueError("Development groups require a source Card")
        if development != (self.source_card_revision is not None):
            raise ValueError("Development groups require a source revision")
        if (
            self.source_card_revision is not None
            and self.source_card_revision < 1
        ):
            raise ValueError("Source Card revision must be positive")
