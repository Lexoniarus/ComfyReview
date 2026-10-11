"""Behavior tests for four-Candidate development groups."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
)
from comfyreview.application.card_battler_card_pool import (
    CardPoolCard,
    CardPoolConflictError,
)
from comfyreview.application.card_battler_development_groups import (
    CARD_DEVELOPMENT_CANDIDATE_REVISION,
    CardDevelopmentCandidateComposer,
    CardDevelopmentCandidateGroupService,
    development_candidate_seeds,
)
from comfyreview.application.card_battler_presentation import CardPresentation
from comfyreview.domain.card_battler import (
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    CardDevelopmentProvenance,
    CardDevelopmentResult,
    CardIdentity,
    CardState,
    StructuredCardSpec,
    TraitDevelopmentAction,
)
from tests.test_card_battler_session_repository import _session


def _pool_card() -> CardPoolCard:
    session = _session()
    identity = CardIdentity(
        "card-1",
        session.source_image_uid,
        session.source_content_hash,
        session.semantic_profile.semantic_revision,
        session.imprint,
    )
    return CardPoolCard(
        state=CardState(
            identity,
            1,
            session.card,
            "accepted-image",
            "accepted-hash",
            session.card.tier_ordinal,
        ),
        semantic_profile=session.semantic_profile,
        visual_recipe=session.visual_recipe,
        presentation=session.presentation,
        accepted_group_id="initial-group",
        accepted_candidate_id="initial-candidate",
    )


class _Development:
    def __init__(self) -> None:
        self.calls: list[StructuredCardSpec] = []

    def advance(self, card):
        self.calls.append(card)
        developed = replace(
            card,
            rarity_key="common",
            level=2,
            tier_ordinal=2,
        )
        provenance = CardDevelopmentProvenance(
            "prototype_development",
            1,
            CARD_DEVELOPMENT_ALGORITHM_REVISION,
        )
        return CardDevelopmentResult(
            developed,
            TraitDevelopmentAction(
                "improve_existing_trait",
                0,
                card.traits[0],
                developed.traits[0],
            ),
            provenance,
        )


class _Visuals:
    def __init__(self, recipe) -> None:
        self.recipe = recipe
        self.seeds: list[int] = []

    def project(self, semantic_profile, card, *, explicit_seed):
        assert semantic_profile == _pool_card().semantic_profile
        assert card.tier_ordinal == 2
        self.seeds.append(explicit_seed)
        return replace(self.recipe, tier_ordinal=2)


class _Presentations:
    def __init__(self, result) -> None:
        self.result = result
        self.existing: list[CardPresentation | None] = []

    def realize(self, semantic_profile, card, *, existing=None):
        assert semantic_profile == _pool_card().semantic_profile
        assert card.tier_ordinal == 2
        self.existing.append(existing)
        return self.result


class _Cards:
    def __init__(self, card: CardPoolCard) -> None:
        self.card = card

    def get(self, card_id):
        return (
            self.card if card_id == self.card.state.identity.card_id else None
        )


class _Groups:
    def __init__(self) -> None:
        self.created: list[CardCandidateGroup] = []

    def create(self, group):
        self.created.append(group)
        return group


class _Identities:
    def new_group_id(self):
        return "development-group"

    def candidate_id(self, group_id, slot_index):
        return f"{group_id}-candidate-{slot_index}"


class _Seeds:
    def new_seed(self):
        return 91


def test_development_candidate_seeds_are_stable_and_revision_separated() -> (
    None
):
    first = development_candidate_seeds("card-1", 1, 2, 91)

    assert first == development_candidate_seeds("card-1", 1, 2, 91)
    assert len(first) == len(set(first)) == 4
    assert first != development_candidate_seeds("card-1", 2, 3, 91)


def test_development_composer_builds_four_one_step_candidates() -> None:
    card = _pool_card()
    development = _Development()
    visuals = _Visuals(card.visual_recipe)
    presentations = _Presentations(card.presentation)
    composer = CardDevelopmentCandidateComposer(
        development=development,
        visual_projector=visuals,
        presentation_realizer=presentations,
    )
    seeds = development_candidate_seeds("card-1", 1, 2, 91)

    result = composer.compose(card, seeds)

    assert len(result.candidates) == 4
    assert len(development.calls) == 4
    assert visuals.seeds == list(seeds)
    assert all(
        candidate.development is not None
        and candidate.card == candidate.development.card
        and candidate.card.tier_ordinal == 2
        and candidate.materialization_revision
        == CARD_DEVELOPMENT_CANDIDATE_REVISION
        for candidate in result.candidates
    )


def test_development_group_reserves_from_current_card_without_analysis() -> (
    None
):
    card = _pool_card()
    groups = _Groups()
    service = CardDevelopmentCandidateGroupService(
        cards=_Cards(card),
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    )

    group = service.reserve("card-1", expected_revision=1)

    assert group.kind is CardCandidateGroupKind.DEVELOPMENT
    assert group.status is CardCandidateGroupStatus.QUEUED
    assert group.semantic_profile == card.semantic_profile
    assert group.imprint == card.state.identity.imprint
    assert group.reference_image_uid == card.state.active_image_uid
    assert group.source_card_id == "card-1"
    assert group.source_card_revision == 1
    assert tuple(item.materialization_seed for item in group.candidates) == (
        development_candidate_seeds("card-1", 1, 2, 91)
    )
    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        service.reserve("card-1", expected_revision=2)
