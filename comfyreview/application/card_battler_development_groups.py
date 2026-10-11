"""Reservation and deterministic composition of Card development groups."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.card_battler_candidate_group_service import (
    CardCandidateGroupIdentitySource,
    CardCandidateGroupSeedSource,
)
from comfyreview.application.card_battler_candidate_groups import (
    CARD_CANDIDATE_COUNT,
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupRepository,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
)
from comfyreview.application.card_battler_card_pool import (
    CardPoolCard,
    CardPoolConflictError,
    CardPoolNotFoundError,
    CardPoolRepository,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationRealizer,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_visual_projection import (
    VisualPromptProjector,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentResult,
    StructuredCardSpec,
)

CARD_DEVELOPMENT_CANDIDATE_REVISION = "card-development-candidate-v1"
_SQLITE_INTEGER_MODULO = 2**63 - 1


def development_candidate_seeds(
    card_id: str,
    source_card_revision: int,
    target_tier: int,
    group_seed: int,
) -> tuple[int, ...]:
    """Derive four independent replayable seeds for one development group."""
    if (
        not card_id.strip()
        or source_card_revision < 1
        or target_tier < 2
        or group_seed < 0
    ):
        raise ValueError("Development Candidate seed inputs are invalid")
    random = DomainSeparatedCardRandom(
        (
            CARD_DEVELOPMENT_CANDIDATE_REVISION,
            card_id,
            str(source_card_revision),
            str(target_tier),
            str(group_seed),
        )
    )
    return tuple(
        random.integer(
            f"development:{target_tier}:candidate:{slot_index}",
            modulo=_SQLITE_INTEGER_MODULO,
        )
        for slot_index in range(CARD_CANDIDATE_COUNT)
    )


class CardDevelopmentStep(Protocol):
    """Advance one immutable Card by exactly one legal tier/action."""

    def advance(self, card: StructuredCardSpec) -> CardDevelopmentResult:
        """Return one complete adjacent-tier development result."""
        ...


@dataclass(frozen=True, slots=True)
class CardDevelopmentCandidateComposition:
    """Carry four inspectable development Candidates for persistence."""

    candidates: tuple[CompleteCardCandidateArtifacts, ...]

    def __post_init__(self) -> None:
        if len(self.candidates) != CARD_CANDIDATE_COUNT:
            raise ValueError(
                "Development composition requires four Candidates"
            )


class CardDevelopmentCandidateComposer:
    """Compose four one-step variants without VLM or Imprint mapping."""

    def __init__(
        self,
        *,
        development: CardDevelopmentStep,
        visual_projector: VisualPromptProjector,
        presentation_realizer: CardPresentationRealizer,
    ) -> None:
        self._development = development
        self._visual_projector = visual_projector
        self._presentation_realizer = presentation_realizer

    def compose(
        self,
        card: CardPoolCard,
        candidate_seeds: tuple[int, ...],
    ) -> CardDevelopmentCandidateComposition:
        """Build four candidates from the same current immutable Card state."""
        if len(candidate_seeds) != CARD_CANDIDATE_COUNT:
            raise ValueError("Development composition requires four seeds")
        candidates = []
        for seed in candidate_seeds:
            result = self._development.advance(card.state.card)
            recipe = self._visual_projector.project(
                card.semantic_profile,
                result.card,
                explicit_seed=seed,
            )
            presentation = self._presentation_realizer.realize(
                card.semantic_profile,
                result.card,
                existing=card.presentation.presentation,
            )
            candidates.append(
                CompleteCardCandidateArtifacts(
                    card=result.card,
                    visual_recipe=recipe,
                    presentation=presentation,
                    materialization_seed=seed,
                    development=result,
                    materialization_revision=(
                        CARD_DEVELOPMENT_CANDIDATE_REVISION
                    ),
                )
            )
        return CardDevelopmentCandidateComposition(tuple(candidates))


class CardDevelopmentCandidateGroupService:
    """Reserve four slots from one current confirmed Card revision."""

    def __init__(
        self,
        *,
        cards: CardPoolRepository,
        groups: CardCandidateGroupRepository,
        identities: CardCandidateGroupIdentitySource,
        seeds: CardCandidateGroupSeedSource,
    ) -> None:
        self._cards = cards
        self._groups = groups
        self._identities = identities
        self._seeds = seeds

    def reserve(
        self,
        card_id: str,
        *,
        expected_revision: int,
    ) -> CardCandidateGroup:
        """Persist a development group without rerunning semantic analysis."""
        card = self._cards.get(card_id)
        if card is None:
            raise CardPoolNotFoundError(card_id)
        if card.state.revision != expected_revision:
            raise CardPoolConflictError("Card revision is stale")
        group_id = self._identities.new_group_id()
        group_seed = self._seeds.new_seed()
        candidate_seeds = development_candidate_seeds(
            card_id,
            expected_revision,
            card.state.card.tier_ordinal + 1,
            group_seed,
        )
        return self._groups.create(
            CardCandidateGroup(
                group_id=group_id,
                revision=1,
                kind=CardCandidateGroupKind.DEVELOPMENT,
                status=CardCandidateGroupStatus.QUEUED,
                source_image_uid=card.state.identity.source_image_uid,
                source_content_hash=card.state.identity.source_content_hash,
                reference_image_uid=card.state.active_image_uid,
                reference_content_hash=card.state.active_content_hash,
                group_seed=group_seed,
                candidates=tuple(
                    CardCandidate(
                        candidate_id=self._identities.candidate_id(
                            group_id,
                            slot_index,
                        ),
                        group_id=group_id,
                        group_revision=1,
                        slot_index=slot_index,
                        status=CardCandidateStatus.QUEUED,
                        materialization_seed=candidate_seed,
                    )
                    for slot_index, candidate_seed in enumerate(
                        candidate_seeds
                    )
                ),
                semantic_profile=card.semantic_profile,
                imprint=card.state.identity.imprint,
                source_card_id=card_id,
                source_card_revision=expected_revision,
            )
        )
