"""Policy and command tests for the bounded revision-safe POC deck."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from comfyreview.application.card_battler_deck import (
    CardDeckConflictError,
    CardDeckNotFoundError,
    CardDeckPolicy,
    CardDeckService,
)
from comfyreview.domain.card_battler import (
    POC_DECK_CAPACITY,
    POC_DECK_ID,
    CardDeck,
    CardDeckEntry,
)


class _Decks:
    def __init__(self) -> None:
        self.deck = CardDeck(POC_DECK_ID, 1, ())

    def get(self, deck_id=POC_DECK_ID):
        return self.deck if deck_id == POC_DECK_ID else None

    def replace_entries(self, deck_id, entries, *, expected_revision):
        if self.deck.revision != expected_revision:
            raise CardDeckConflictError("Deck revision is stale")
        self.deck = CardDeck(deck_id, expected_revision + 1, entries)
        return self.deck


class _Cards:
    def __init__(self, *card_ids: str) -> None:
        self.card_ids = set(card_ids)

    def get(self, card_id):
        if card_id not in self.card_ids:
            return None
        return SimpleNamespace(card_id=card_id)


def test_deck_policy_enforces_unique_cards_capacity_and_exact_order() -> None:
    policy = CardDeckPolicy()
    deck = CardDeck(
        POC_DECK_ID,
        1,
        (CardDeckEntry("card-1", 0), CardDeckEntry("card-2", 1)),
    )

    assert policy.add(deck, "card-3")[-1] == CardDeckEntry("card-3", 2)
    assert policy.remove(deck, "card-1") == (CardDeckEntry("card-2", 0),)
    assert policy.reorder(deck, ("card-2", "card-1")) == (
        CardDeckEntry("card-2", 0),
        CardDeckEntry("card-1", 1),
    )
    with pytest.raises(CardDeckConflictError, match="already belongs"):
        policy.add(deck, "card-1")
    with pytest.raises(CardDeckConflictError, match="every current Card"):
        policy.reorder(deck, ("card-1", "card-3"))
    full = CardDeck(
        POC_DECK_ID,
        1,
        tuple(
            CardDeckEntry(f"card-{index}", index)
            for index in range(POC_DECK_CAPACITY)
        ),
    )
    with pytest.raises(CardDeckConflictError, match="capacity exceeded"):
        policy.add(full, "overflow")


def test_deck_service_requires_revision_and_existing_pool_card() -> None:
    decks = _Decks()
    service = CardDeckService(
        decks=decks,
        cards=_Cards("card-1", "card-2"),
        policy=CardDeckPolicy(),
    )

    assert service.get() == CardDeck(POC_DECK_ID, 1, ())
    with pytest.raises(CardDeckNotFoundError):
        service.add("missing", expected_revision=1)
    with pytest.raises(CardDeckConflictError, match="revision is stale"):
        service.add("card-1", expected_revision=2)

    first = service.add("card-1", expected_revision=1)
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
    assert removed.revision == 5
