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
)
from comfyreview.domain.card_battler import (
    POC_DECK_ID,
    CardDeck,
    CardDeckEntry,
    CardIdentity,
    CardState,
)
from tests.test_card_battler_session_repository import _session


def _slots(group_id: str) -> tuple[CardCandidate, ...]:
    return tuple(
        CardCandidate(
            candidate_id=f"candidate-{index}",
            group_id=group_id,
            group_revision=1,
            slot_index=index,
            status=CardCandidateStatus.QUEUED,
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
            group_seed=42,
            candidates=_slots("group-1"),
        )


def test_confirmed_card_state_retains_identity_dna_and_tier() -> None:
    session = _session()
    identity = CardIdentity(
        card_id="card-1",
        source_image_uid=session.source_image_uid,
        source_content_hash=session.source_content_hash,
        semantic_revision=session.semantic_profile.semantic_revision,
        imprint=session.imprint,
    )
    state = CardState(
        identity=identity,
        revision=1,
        card=session.card,
        active_image_uid="output-1",
        active_content_hash="output-hash",
        visual_tier=session.card.tier_ordinal,
    )

    assert state.card.imprint == session.imprint
    with pytest.raises(ValueError, match="visual tier"):
        CardState(
            identity=identity,
            revision=1,
            card=session.card,
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
