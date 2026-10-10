"""Immutable, provider-free Card Battler crafting lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum

from comfyreview.domain.card_battler.cards import StructuredCardSpec


class CardCraftingError(ValueError):
    """Reject inconsistent snapshots and invalid crafting transitions."""


def _require_identity(value: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise CardCraftingError("identity must be a non-empty string")


@dataclass(frozen=True, slots=True)
class CraftingSessionIdentity:
    """Identify one crafting attempt, independent of a card or image."""

    value: str

    def __post_init__(self) -> None:
        _require_identity(self.value)


@dataclass(frozen=True, slots=True)
class CardIdentity:
    """Identify the card across its confirmed revisions."""

    value: str

    def __post_init__(self) -> None:
        _require_identity(self.value)


@dataclass(frozen=True, slots=True)
class CardRevisionIdentity:
    """Identify one explicitly confirmed revision of a card."""

    value: str

    def __post_init__(self) -> None:
        _require_identity(self.value)


@dataclass(frozen=True, slots=True)
class ConfirmedCardRevision:
    """Freeze one committed card fact without persisting it."""

    card_identity: CardIdentity
    revision_identity: CardRevisionIdentity
    spec: StructuredCardSpec
    image_uid: str
    previous_revision_identity: CardRevisionIdentity | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.card_identity, CardIdentity) or not isinstance(
            self.revision_identity, CardRevisionIdentity
        ):
            raise CardCraftingError("invalid confirmed card identity")
        if not isinstance(self.spec, StructuredCardSpec):
            raise CardCraftingError("confirmed card rules must be structured")
        _require_identity(self.image_uid)
        if self.previous_revision_identity is not None and not isinstance(
            self.previous_revision_identity, CardRevisionIdentity
        ):
            raise CardCraftingError("invalid previous revision identity")
        if self.previous_revision_identity == self.revision_identity:
            raise CardCraftingError("revision cannot follow itself")


class CraftingStage(StrEnum):
    """Track the explicit approval and selection boundaries of one attempt."""

    SOURCE_SELECTED = "source_selected"
    ANALYSIS_AVAILABLE = "analysis_available"
    ANALYSIS_APPROVED = "analysis_approved"
    DRAFT_AVAILABLE = "draft_available"
    ROUND_PREPARED = "round_prepared"
    CANDIDATES_AVAILABLE = "candidates_available"
    CANDIDATE_SELECTED = "candidate_selected"
    ROUND_REJECTED = "round_rejected"
    READY_FOR_CONFIRMATION = "ready_for_confirmation"
    CONFIRMED = "confirmed"


@dataclass(frozen=True, slots=True)
class CandidateSlot:
    """Hold one stable slot in the current four-candidate round."""

    number: int
    image_uid: str | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.number, int)
            or isinstance(self.number, bool)
            or not 1 <= self.number <= 4
        ):
            raise CardCraftingError("candidate slot number must be 1-4")
        if self.image_uid is not None:
            _require_identity(self.image_uid)


_DRAFT_STAGES = frozenset(
    {
        CraftingStage.DRAFT_AVAILABLE,
        CraftingStage.ROUND_PREPARED,
        CraftingStage.CANDIDATES_AVAILABLE,
        CraftingStage.CANDIDATE_SELECTED,
        CraftingStage.ROUND_REJECTED,
        CraftingStage.READY_FOR_CONFIRMATION,
        CraftingStage.CONFIRMED,
    }
)
_ROUND_STAGES = _DRAFT_STAGES - {CraftingStage.DRAFT_AVAILABLE}
_GENERATED_STAGES = _ROUND_STAGES - {CraftingStage.ROUND_PREPARED}
_SELECTED_STAGES = frozenset(
    {
        CraftingStage.CANDIDATE_SELECTED,
        CraftingStage.READY_FOR_CONFIRMATION,
        CraftingStage.CONFIRMED,
    }
)


@dataclass(frozen=True, slots=True)
class CardCraftingSession:
    """One immutable crafting snapshot; transitions produce new snapshots."""

    session_identity: CraftingSessionIdentity
    card_identity: CardIdentity
    source_image_uid: str
    stage: CraftingStage = CraftingStage.SOURCE_SELECTED
    semantic_revision: str | None = None
    draft: StructuredCardSpec | None = None
    round_number: int = 0
    slots: tuple[CandidateSlot, ...] = ()
    selected_slot: int | None = None
    base_revision: ConfirmedCardRevision | None = None
    confirmed_revision: ConfirmedCardRevision | None = None

    def __post_init__(self) -> None:
        _require_identity(self.source_image_uid)
        if not isinstance(self.session_identity, CraftingSessionIdentity) or (
            not isinstance(self.card_identity, CardIdentity)
        ):
            raise CardCraftingError("invalid session or card identity")
        if not isinstance(self.stage, CraftingStage):
            raise CardCraftingError("invalid crafting stage")
        if self.base_revision is not None:
            if not isinstance(self.base_revision, ConfirmedCardRevision):
                raise CardCraftingError("invalid base card revision")
            if self.base_revision.card_identity != self.card_identity:
                raise CardCraftingError("development must keep card identity")
        if (self.semantic_revision is None) != (
            self.stage is CraftingStage.SOURCE_SELECTED
        ):
            raise CardCraftingError("stage and analysis do not agree")
        if self.semantic_revision is not None:
            _require_identity(self.semantic_revision)
        if (self.draft is not None) != (self.stage in _DRAFT_STAGES):
            raise CardCraftingError("stage and card draft do not agree")
        if self.draft is not None:
            self._validate_draft(self.draft)
        if (
            not isinstance(self.round_number, int)
            or isinstance(self.round_number, bool)
            or self.round_number < 0
        ):
            raise CardCraftingError("round number must be non-negative")
        if not isinstance(self.slots, tuple) or any(
            not isinstance(slot, CandidateSlot) for slot in self.slots
        ):
            raise CardCraftingError("candidate slots must be immutable values")
        has_round = self.stage in _ROUND_STAGES
        if has_round != (self.round_number > 0):
            raise CardCraftingError("stage and round number do not agree")
        if has_round:
            if tuple(slot.number for slot in self.slots) != (1, 2, 3, 4):
                raise CardCraftingError("round must have four ordered slots")
        elif self.slots:
            raise CardCraftingError("slots require a prepared round")
        generated = self.stage in _GENERATED_STAGES
        if any(
            (slot.image_uid is not None) != generated for slot in self.slots
        ):
            raise CardCraftingError("candidate results do not match stage")
        if generated and len({slot.image_uid for slot in self.slots}) != 4:
            raise CardCraftingError("candidate image identities must differ")
        if (self.selected_slot is not None) != (
            self.stage in _SELECTED_STAGES
        ):
            raise CardCraftingError("selected candidate does not match stage")
        if self.selected_slot is not None and (
            not isinstance(self.selected_slot, int)
            or isinstance(self.selected_slot, bool)
            or self.selected_slot not in range(1, 5)
        ):
            raise CardCraftingError("selected candidate is not a round slot")
        if (self.confirmed_revision is not None) != (
            self.stage is CraftingStage.CONFIRMED
        ):
            raise CardCraftingError("confirmation does not match stage")
        if self.confirmed_revision is not None:
            if not isinstance(self.confirmed_revision, ConfirmedCardRevision):
                raise CardCraftingError("invalid confirmed card revision")
            assert self.selected_slot is not None
            if (
                self.confirmed_revision.card_identity != self.card_identity
                or self.confirmed_revision.spec != self.draft
                or self.confirmed_revision.image_uid
                != self.slots[self.selected_slot - 1].image_uid
                or self.confirmed_revision.previous_revision_identity
                != (
                    self.base_revision.revision_identity
                    if self.base_revision is not None
                    else None
                )
            ):
                raise CardCraftingError(
                    "confirmed revision disagrees with draft"
                )

    @classmethod
    def begin(
        cls,
        *,
        session_identity: CraftingSessionIdentity,
        card_identity: CardIdentity,
        source_image_uid: str,
    ) -> CardCraftingSession:
        """Reserve a card identity without creating a confirmed card."""
        return cls(session_identity, card_identity, source_image_uid)

    @classmethod
    def begin_development(
        cls,
        *,
        session_identity: CraftingSessionIdentity,
        source_image_uid: str,
        base_revision: ConfirmedCardRevision,
    ) -> CardCraftingSession:
        """Start a new draft while retaining the last confirmed revision."""
        if not isinstance(base_revision, ConfirmedCardRevision):
            raise CardCraftingError("development needs a confirmed revision")
        return cls(
            session_identity,
            base_revision.card_identity,
            source_image_uid,
            base_revision=base_revision,
        )

    def record_analysis(self, semantic_revision: str) -> CardCraftingSession:
        """Record a versioned analysis reference, not implicit approval."""
        self._require_stage(CraftingStage.SOURCE_SELECTED)
        _require_identity(semantic_revision)
        return replace(
            self,
            semantic_revision=semantic_revision,
            stage=CraftingStage.ANALYSIS_AVAILABLE,
        )

    def approve_analysis(self) -> CardCraftingSession:
        """Explicitly accept the recorded semantic revision."""
        self._require_stage(CraftingStage.ANALYSIS_AVAILABLE)
        return replace(self, stage=CraftingStage.ANALYSIS_APPROVED)

    def attach_draft(self, spec: StructuredCardSpec) -> CardCraftingSession:
        """Accept existing authoritative structured card rules as a draft."""
        self._require_stage(CraftingStage.ANALYSIS_APPROVED)
        self._validate_draft(spec)
        return replace(self, draft=spec, stage=CraftingStage.DRAFT_AVAILABLE)

    def prepare_round(self) -> CardCraftingSession:
        """Create exactly four empty slots for the next generation round."""
        self._require_stage(
            CraftingStage.DRAFT_AVAILABLE, CraftingStage.ROUND_REJECTED
        )
        return replace(
            self,
            round_number=self.round_number + 1,
            slots=tuple(CandidateSlot(number) for number in range(1, 5)),
            selected_slot=None,
            stage=CraftingStage.ROUND_PREPARED,
        )

    def record_candidates(
        self, image_uids: tuple[str, str, str, str]
    ) -> CardCraftingSession:
        """Bind four distinct generated image identities to prepared slots."""
        if self.stage is CraftingStage.CANDIDATES_AVAILABLE:
            if tuple(slot.image_uid for slot in self.slots) == image_uids:
                return self
        self._require_stage(CraftingStage.ROUND_PREPARED)
        if len(image_uids) != 4:
            raise CardCraftingError("a generation round requires four images")
        for uid in image_uids:
            _require_identity(uid)
        if len(set(image_uids)) != 4:
            raise CardCraftingError("candidate image identities must differ")
        return replace(
            self,
            slots=tuple(
                CandidateSlot(index, uid)
                for index, uid in enumerate(image_uids, start=1)
            ),
            stage=CraftingStage.CANDIDATES_AVAILABLE,
        )

    def select_candidate(self, number: int) -> CardCraftingSession:
        """Select exactly one generated slot without confirming a card."""
        if (
            self.stage is CraftingStage.CANDIDATE_SELECTED
            and self.selected_slot == number
        ):
            return self
        self._require_stage(CraftingStage.CANDIDATES_AVAILABLE)
        if (
            not isinstance(number, int)
            or isinstance(number, bool)
            or number not in range(1, 5)
        ):
            raise CardCraftingError("selection must reference a valid slot")
        return replace(
            self,
            selected_slot=number,
            stage=CraftingStage.CANDIDATE_SELECTED,
        )

    def reject_all(self) -> CardCraftingSession:
        """Reject all candidates without creating or changing a card."""
        if self.stage is CraftingStage.ROUND_REJECTED:
            return self
        self._require_stage(CraftingStage.CANDIDATES_AVAILABLE)
        return replace(self, stage=CraftingStage.ROUND_REJECTED)

    def mark_ready(self) -> CardCraftingSession:
        """Mark a selected image and draft ready for explicit confirmation."""
        if self.stage is CraftingStage.READY_FOR_CONFIRMATION:
            return self
        self._require_stage(CraftingStage.CANDIDATE_SELECTED)
        return replace(self, stage=CraftingStage.READY_FOR_CONFIRMATION)

    def confirm(
        self, revision_identity: CardRevisionIdentity
    ) -> CardCraftingSession:
        """Confirm a selected draft as one immutable card revision."""
        if self.stage is CraftingStage.CONFIRMED:
            if self.confirmed_revision is not None and (
                self.confirmed_revision.revision_identity == revision_identity
            ):
                return self
        self._require_stage(CraftingStage.READY_FOR_CONFIRMATION)
        if (
            self.base_revision is not None
            and self.base_revision.revision_identity == revision_identity
        ):
            raise CardCraftingError(
                "development needs a new revision identity"
            )
        assert self.draft is not None
        assert self.selected_slot is not None
        image_uid = self.slots[self.selected_slot - 1].image_uid
        assert image_uid is not None
        return replace(
            self,
            stage=CraftingStage.CONFIRMED,
            confirmed_revision=ConfirmedCardRevision(
                card_identity=self.card_identity,
                revision_identity=revision_identity,
                spec=self.draft,
                image_uid=image_uid,
                previous_revision_identity=(
                    self.base_revision.revision_identity
                    if self.base_revision is not None
                    else None
                ),
            ),
        )

    def _validate_draft(self, spec: StructuredCardSpec) -> None:
        if not isinstance(spec, StructuredCardSpec):
            raise CardCraftingError("draft must contain structured card rules")
        imprint = spec.imprint
        provenance = spec.provenance
        if (
            imprint.source_image_uid != self.source_image_uid
            or imprint.semantic_revision != self.semantic_revision
            or (
                imprint.ruleset_key,
                imprint.ruleset_version,
                imprint.mapping_policy_key,
                imprint.mapping_policy_version,
                imprint.rng_policy_key,
                imprint.rng_policy_version,
                imprint.rng_algorithm,
                imprint.explicit_seed,
            ) != (
                provenance.ruleset_key,
                provenance.ruleset_version,
                provenance.mapping_policy_key,
                provenance.mapping_policy_version,
                provenance.rng_policy_key,
                provenance.rng_policy_version,
                provenance.rng_algorithm,
                provenance.explicit_seed,
            )
        ):
            raise CardCraftingError(
                "draft disagrees with source or provenance"
            )

    def _require_stage(self, *expected: CraftingStage) -> None:
        if self.stage not in expected:
            raise CardCraftingError(
                f"invalid crafting transition from {self.stage.value}"
            )
