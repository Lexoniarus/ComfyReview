"""SQLite behavior tests for the isolated POC Card deck."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_deck import (
    CardDeckConflictError,
    CardDeckPolicy,
    CardDeckService,
)
from comfyreview.domain.card_battler import CardDeckEntry
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from comfyreview.repositories.sqlite.card_battler_deck import (
    SqliteCardDeckRepository,
)
from tests.test_card_pool_repository import _ready_group


def _cards(tmp_path: Path) -> SqliteCardPoolRepository:
    ready = _ready_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    cards.accept_initial_candidate(
        ready.group_id,
        ready.candidates[0].candidate_id,
        expected_revision=ready.revision,
        card_id="card-1",
    )
    connection = sqlite3.connect(database_path)
    try:
        connection.execute(
            """
            INSERT INTO cards(
                card_id, revision, source_image_uid, source_content_hash,
                semantic_profile_json, card_imprint_json,
                structured_card_spec_json, visual_recipe_json,
                presentation_json, presentation_status,
                presentation_error_category, active_image_uid,
                active_content_hash, visual_tier, accepted_group_id,
                accepted_candidate_id, created_at, updated_at
            )
            SELECT 'card-2', revision, source_image_uid, source_content_hash,
                semantic_profile_json, card_imprint_json,
                structured_card_spec_json, visual_recipe_json,
                presentation_json, presentation_status,
                presentation_error_category, active_image_uid,
                active_content_hash, visual_tier, accepted_group_id,
                accepted_candidate_id, datetime('now'), datetime('now')
            FROM cards WHERE card_id = 'card-1'
            """
        )
        connection.commit()
    finally:
        connection.close()
    return cards


def test_sqlite_deck_persists_add_remove_and_order_by_revision(
    tmp_path: Path,
) -> None:
    cards = _cards(tmp_path)
    decks = SqliteCardDeckRepository(tmp_path / "card-runtime.sqlite3")
    service = CardDeckService(
        decks=decks,
        cards=cards,
        policy=CardDeckPolicy(),
    )

    empty = service.get()
    first = service.add("card-1", expected_revision=empty.revision)
    second = service.add("card-2", expected_revision=first.revision)
    ordered = service.reorder(
        ("card-2", "card-1"),
        expected_revision=second.revision,
    )
    removed = service.remove(
        "card-1",
        expected_revision=ordered.revision,
    )

    assert removed.entries == (CardDeckEntry("card-2", 0),)
    assert decks.get() == removed
    assert tuple(
        card.state.identity.card_id for card in cards.list_cards()
    ) == (
        "card-1",
        "card-2",
    )


def test_sqlite_deck_rolls_back_stale_and_missing_membership(
    tmp_path: Path,
) -> None:
    _cards(tmp_path)
    decks = SqliteCardDeckRepository(tmp_path / "card-runtime.sqlite3")
    original = decks.get()
    assert original is not None

    with pytest.raises(CardDeckConflictError, match="revision is stale"):
        decks.replace_entries(
            original.deck_id,
            (CardDeckEntry("card-1", 0),),
            expected_revision=original.revision + 1,
        )
    assert decks.get() == original

    with pytest.raises(CardDeckConflictError, match="unavailable"):
        decks.replace_entries(
            original.deck_id,
            (CardDeckEntry("missing", 0),),
            expected_revision=original.revision,
        )
    assert decks.get() == original
