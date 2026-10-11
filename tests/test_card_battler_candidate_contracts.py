"""Behavior tests for complete Card candidate and deck contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
    candidate_materialization_seeds,
)
from comfyreview.domain.card_battler import (
    POC_DECK_ID,
    CardDeck,
    CardDeckEntry,
    CardIdentity,
    CardState,
)
from tests.card_battler_fixtures import (
    absent_presentation,
    card_imprint,
    card_source_image,
    semantic_profile,
    structured_card,
    visual_recipe,
)


def _slots(group_id: str) -> tuple[CardCandidate, ...]:
    seeds = candidate_materialization_seeds("image-1", 42)
    return tuple(
        CardCandidate(
            candidate_id=f"candidate-{index}",
            group_id=group_id,
            group_revision=1,
            slot_index=index,
            status=CardCandidateStatus.QUEUED,
            materialization_seed=seeds[index],
        )
        for index in range(4)
    )


def test_candidate_group_requires_four_ordered_same_group_slots() -> None:
    group = CardCandidateGroup(
        group_id="group-1",
        revision=1,
        kind=CardCandidateGroupKind.INITIAL,
        status=CardCandidateGroupStatus.QUEUED,
        source_image_uid="image-1",
        source_content_hash="hash-1",
        reference_image_uid="image-1",
        reference_content_hash="hash-1",
        group_seed=42,
        candidates=_slots("group-1"),
    )

    assert group.candidates[3].slot_index == 3
    with pytest.raises(FrozenInstanceError):
        group.revision = 2  # type: ignore[misc]

    with pytest.raises(ValueError, match="exactly four"):
        CardCandidateGroup(
            group_id="group-2",
            revision=1,
            kind=CardCandidateGroupKind.INITIAL,
            status=CardCandidateGroupStatus.QUEUED,
            source_image_uid="image-1",
            source_content_hash="hash-1",
            reference_image_uid="image-1",
            reference_content_hash="hash-1",
            group_seed=42,
            candidates=_slots("group-2")[:3],
        )


def test_development_group_requires_card_identity_and_revision() -> None:
    with pytest.raises(ValueError, match="source Card"):
        CardCandidateGroup(
            group_id="group-1",
            revision=1,
            kind=CardCandidateGroupKind.DEVELOPMENT,
            status=CardCandidateGroupStatus.QUEUED,
            source_image_uid="image-1",
            source_content_hash="hash-1",
            reference_image_uid="image-1",
            reference_content_hash="hash-1",
            group_seed=42,
            candidates=_slots("group-1"),
        )


def test_submitted_candidate_requires_generation_provenance() -> None:
    queued = _slots("group-1")[0]

    with pytest.raises(ValueError, match="complete artifacts"):
        CardCandidate(
            candidate_id=queued.candidate_id,
            group_id=queued.group_id,
            group_revision=queued.group_revision,
            slot_index=queued.slot_index,
            status=CardCandidateStatus.SUBMITTED,
            materialization_seed=queued.materialization_seed,
        )
    artifacts = CompleteCardCandidateArtifacts(
        structured_card(),
        visual_recipe(),
        absent_presentation(),
        queued.materialization_seed,
    )
    with pytest.raises(ValueError, match="generation provenance"):
        CardCandidate(
            candidate_id=queued.candidate_id,
            group_id=queued.group_id,
            group_revision=queued.group_revision,
            slot_index=queued.slot_index,
            status=CardCandidateStatus.SUBMITTED,
            materialization_seed=queued.materialization_seed,
            artifacts=artifacts,
        )


def test_confirmed_card_state_retains_identity_dna_and_tier() -> None:
    source = card_source_image()
    imprint = card_imprint()
    profile = semantic_profile()
    card = structured_card()
    identity = CardIdentity(
        card_id="card-1",
        source_image_uid=source.image_uid,
        source_content_hash=source.content_hash,
        semantic_revision=profile.semantic_revision,
        imprint=imprint,
    )
    state = CardState(
        identity=identity,
        revision=1,
        card=card,
        active_image_uid="output-1",
        active_content_hash="output-hash",
        visual_tier=card.tier_ordinal,
    )

    assert state.card.imprint == imprint
    with pytest.raises(ValueError, match="visual tier"):
        CardState(
            identity=identity,
            revision=1,
            card=card,
            active_image_uid="output-1",
            active_content_hash="output-hash",
            visual_tier=99,
        )


def test_poc_deck_requires_unique_contiguous_entries_and_caps_at_forty() -> (
    None
):
    deck = CardDeck(
        deck_id=POC_DECK_ID,
        revision=1,
        entries=(CardDeckEntry("card-1", 0), CardDeckEntry("card-2", 1)),
    )

    assert deck.capacity == 40
    with pytest.raises(ValueError, match="only once"):
        CardDeck(
            deck_id=POC_DECK_ID,
            revision=2,
            entries=(CardDeckEntry("card-1", 0), CardDeckEntry("card-1", 1)),
        )
    with pytest.raises(ValueError, match="contiguous"):
        CardDeck(
            deck_id=POC_DECK_ID,
            revision=2,
            entries=(CardDeckEntry("card-1", 1),),
        )
