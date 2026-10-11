"""Application contracts for confirmed POC Cards and Candidate acceptance."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
)
from comfyreview.application.card_battler_semantics import SemanticImageProfile
from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.card_battler import CardState


class CardPoolConflictError(RuntimeError):
    """Reject stale acceptance or an illegal Candidate transition."""


class CardPoolNotFoundError(LookupError):
    """Report an unknown Candidate group, Candidate, or confirmed Card."""


@dataclass(frozen=True, slots=True)
class CardPoolCard:
    """Expose one confirmed Card with inspectable semantic/visual artifacts."""

    state: CardState
    semantic_profile: SemanticImageProfile
    visual_recipe: VisualPromptRecipe
    presentation: CardPresentationResult
    accepted_group_id: str
    accepted_candidate_id: str

    def __post_init__(self) -> None:
        if (
            not self.accepted_group_id.strip()
            or not self.accepted_candidate_id.strip()
        ):
            raise ValueError("Accepted Candidate provenance is required")
        identity = self.state.identity
        if (
            self.semantic_profile.image_uid != identity.source_image_uid
            or self.semantic_profile.semantic_revision
            != identity.semantic_revision
        ):
            raise ValueError("Confirmed Card semantic provenance is invalid")
        if self.visual_recipe.tier_ordinal != self.state.visual_tier:
            raise ValueError("Confirmed Card visual Recipe tier is invalid")


class CardIdentitySource(Protocol):
    """Create opaque stable identities for accepted POC Cards."""

    def new_card_id(self) -> str:
        """Return one new Card identity."""
        ...


class CardPoolRepository(Protocol):
    """Persist and query confirmed Cards in the isolated runtime store."""

    def accept_initial_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
        card_id: str,
    ) -> CardPoolCard:
        """Atomically accept one initial Candidate and complete its group."""
        ...

    def accept_development_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardPoolCard:
        """Atomically replace one Card state from a development Candidate."""
        ...

    def get(self, card_id: str) -> CardPoolCard | None:
        """Return one current confirmed Card."""
        ...

    def list_cards(self) -> tuple[CardPoolCard, ...]:
        """Return the unbounded POC Card pool in stable order."""
        ...


class CardCandidateAcceptanceRepository(Protocol):
    """Persist only the two atomic Candidate acceptance transitions."""

    def accept_initial_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
        card_id: str,
    ) -> CardPoolCard:
        """Create one Card from an initial Candidate by group CAS."""
        ...

    def accept_development_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardPoolCard:
        """Replace one current Card from a development Candidate."""
        ...


class InitialCardCandidateAcceptancePolicy:
    """Validate the business facts required for initial Candidate acceptance."""

    @staticmethod
    def select(
        group: CardCandidateGroup,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidate:
        """Return the completed Candidate or reject the comparison state."""
        if group.revision != expected_revision:
            raise CardPoolConflictError("Candidate group revision is stale")
        if group.kind is not CardCandidateGroupKind.INITIAL:
            raise CardPoolConflictError(
                "Initial acceptance requires an initial Candidate group"
            )
        if group.status not in {
            CardCandidateGroupStatus.READY,
            CardCandidateGroupStatus.PARTIAL_FAILURE,
        }:
            raise CardPoolConflictError(
                "Candidate group is not comparison-ready"
            )
        candidate = next(
            (
                item
                for item in group.candidates
                if item.candidate_id == candidate_id
            ),
            None,
        )
        if candidate is None:
            raise CardPoolNotFoundError(candidate_id)
        if candidate.status is not CardCandidateStatus.COMPLETED:
            raise CardPoolConflictError(
                "Only a completed Candidate can be accepted"
            )
        return candidate


class DevelopmentCardCandidateAcceptancePolicy:
    """Validate one comparison-ready adjacent-tier Candidate selection."""

    @staticmethod
    def select(
        group: CardCandidateGroup,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidate:
        """Return one completed Development Candidate or reject the state."""
        if group.revision != expected_revision:
            raise CardPoolConflictError("Candidate group revision is stale")
        if (
            group.kind is not CardCandidateGroupKind.DEVELOPMENT
            or group.source_card_id is None
            or group.source_card_revision is None
        ):
            raise CardPoolConflictError(
                "Development acceptance requires a source Card revision"
            )
        if group.status not in {
            CardCandidateGroupStatus.READY,
            CardCandidateGroupStatus.PARTIAL_FAILURE,
        }:
            raise CardPoolConflictError(
                "Candidate group is not comparison-ready"
            )
        candidate = next(
            (
                item
                for item in group.candidates
                if item.candidate_id == candidate_id
            ),
            None,
        )
        if candidate is None:
            raise CardPoolNotFoundError(candidate_id)
        if (
            candidate.status is not CardCandidateStatus.COMPLETED
            or candidate.artifacts is None
            or candidate.artifacts.development is None
        ):
            raise CardPoolConflictError(
                "Only a completed Development Candidate can be accepted"
            )
        return candidate


class CardCandidateAcceptanceService:
    """Accept comparison-ready Candidates into the persistent Card pool."""

    def __init__(
        self,
        *,
        groups: ProtocolCardCandidateGroupQuery,
        cards: CardCandidateAcceptanceRepository,
        identities: CardIdentitySource,
        policy: InitialCardCandidateAcceptancePolicy,
        development_policy: DevelopmentCardCandidateAcceptancePolicy
        | None = None,
    ) -> None:
        self._groups = groups
        self._cards = cards
        self._identities = identities
        self._policy = policy
        self._development_policy = (
            development_policy or DevelopmentCardCandidateAcceptancePolicy()
        )

    def accept(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardPoolCard:
        """Create one stable Card identity through an atomic repository CAS."""
        group = self._groups.get(group_id)
        if group is None:
            raise CardPoolNotFoundError(group_id)
        if group.kind is CardCandidateGroupKind.INITIAL:
            self._policy.select(
                group,
                candidate_id,
                expected_revision=expected_revision,
            )
            return self._cards.accept_initial_candidate(
                group_id,
                candidate_id,
                expected_revision=expected_revision,
                card_id=self._identities.new_card_id(),
            )
        self._development_policy.select(
            group,
            candidate_id,
            expected_revision=expected_revision,
        )
        return self._cards.accept_development_candidate(
            group_id,
            candidate_id,
            expected_revision=expected_revision,
        )


class ProtocolCardCandidateGroupQuery(Protocol):
    """Read Candidate groups without exposing persistence details."""

    def get(self, group_id: str) -> CardCandidateGroup | None:
        """Return one Candidate group."""
        ...
