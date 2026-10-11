"""SQLite lifecycle tests for persisted Card development groups."""

from __future__ import annotations

from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
)
from comfyreview.application.card_battler_development_groups import (
    CardDevelopmentCandidateComposer,
    CardDevelopmentCandidateGroupService,
)
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from tests.test_card_development_candidate_groups import (
    _Development,
    _Identities,
    _Presentations,
    _Seeds,
    _Visuals,
)
from tests.test_card_pool_repository import _ready_group


def _accepted_card(tmp_path: Path):
    ready = _ready_group(tmp_path)
    cards = SqliteCardPoolRepository(tmp_path / "card-runtime.sqlite3")
    return cards.accept_initial_candidate(
        ready.group_id,
        ready.candidates[0].candidate_id,
        expected_revision=ready.revision,
        card_id="card-1",
    )


def test_development_group_round_trips_source_dna_and_exact_actions(
    tmp_path: Path,
) -> None:
    card = _accepted_card(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    groups = SqliteCardCandidateGroupRepository(database_path)
    reservation = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    )
    reserved = reservation.reserve("card-1", expected_revision=1)

    assert groups.get(reserved.group_id) == reserved
    assert groups.claim_next_queued() is None
    claimed = groups.claim_next_queued(CardCandidateGroupKind.DEVELOPMENT)
    assert claimed is not None
    composer = CardDevelopmentCandidateComposer(
        development=_Development(),
        visual_projector=_Visuals(card.visual_recipe),
        presentation_realizer=_Presentations(card.presentation),
    )
    composition = composer.compose(
        card,
        tuple(
            candidate.materialization_seed for candidate in claimed.candidates
        ),
    )

    persisted = groups.complete_development_composition(
        claimed.group_id,
        expected_revision=claimed.revision,
        candidates=composition.candidates,
    )

    assert persisted.status is CardCandidateGroupStatus.GENERATING
    assert persisted.semantic_profile == card.semantic_profile
    assert persisted.imprint == card.state.identity.imprint
    assert persisted.source_card_id == "card-1"
    assert all(
        candidate.artifacts is not None
        and candidate.artifacts.development is not None
        and candidate.artifacts.card.tier_ordinal == 2
        for candidate in persisted.candidates
    )


def test_development_group_rejects_stale_source_card_atomically(
    tmp_path: Path,
) -> None:
    card = _accepted_card(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    groups = SqliteCardCandidateGroupRepository(database_path)
    reserved = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    ).reserve("card-1", expected_revision=1)
    claimed = groups.claim_next_queued(CardCandidateGroupKind.DEVELOPMENT)
    assert claimed is not None
    composition = CardDevelopmentCandidateComposer(
        development=_Development(),
        visual_projector=_Visuals(card.visual_recipe),
        presentation_realizer=_Presentations(card.presentation),
    ).compose(
        card,
        tuple(
            candidate.materialization_seed for candidate in claimed.candidates
        ),
    )

    with pytest.raises(CardCandidateGroupConflictError, match="stale"):
        groups.complete_development_composition(
            reserved.group_id,
            expected_revision=reserved.revision,
            candidates=composition.candidates,
        )

    assert groups.get(claimed.group_id) == claimed
