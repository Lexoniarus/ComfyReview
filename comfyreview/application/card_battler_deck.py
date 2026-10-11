"""Application policy and commands for the one bounded POC Card deck."""

from __future__ import annotations

from typing import Protocol

from comfyreview.application.card_battler_card_pool import CardPoolCard
from comfyreview.domain.card_battler import (
    POC_DECK_CAPACITY,
    POC_DECK_ID,
    CardDeck,
    CardDeckEntry,
)


class CardDeckConflictError(RuntimeError):
    """Reject stale revisions or illegal deck membership changes."""


class CardDeckNotFoundError(LookupError):
    """Report an unknown Card or missing POC deck."""


class CardDeckRepository(Protocol):
    """Persist one deck aggregate in the isolated Card runtime store."""

    def get(self, deck_id: str = POC_DECK_ID) -> CardDeck | None:
        """Return the current POC deck."""
        ...

    def replace_entries(
        self,
        deck_id: str,
        entries: tuple[CardDeckEntry, ...],
        *,
        expected_revision: int,
    ) -> CardDeck:
        """Atomically replace ordered membership by revision CAS."""
        ...


class CardPoolCardQuery(Protocol):
    """Resolve current pool membership without accepting Candidates."""

    def get(self, card_id: str) -> CardPoolCard | None:
        """Return one current pool Card."""
        ...


class CardDeckPolicy:
    """Calculate legal immutable membership changes without persistence."""

    @staticmethod
    def add(deck: CardDeck, card_id: str) -> tuple[CardDeckEntry, ...]:
        """Append one new unique Card within the fixed capacity."""
        normalized = card_id.strip()
        if not normalized:
            raise ValueError("Card identity is required")
        if any(entry.card_id == normalized for entry in deck.entries):
            raise CardDeckConflictError("Card already belongs to the deck")
        if len(deck.entries) >= POC_DECK_CAPACITY:
            raise CardDeckConflictError("POC deck capacity exceeded")
        return (*deck.entries, CardDeckEntry(normalized, len(deck.entries)))

    @staticmethod
    def remove(deck: CardDeck, card_id: str) -> tuple[CardDeckEntry, ...]:
        """Remove one member and compact all positions."""
        remaining = tuple(
            entry for entry in deck.entries if entry.card_id != card_id
        )
        if len(remaining) == len(deck.entries):
            raise CardDeckNotFoundError(card_id)
        return tuple(
            CardDeckEntry(entry.card_id, position)
            for position, entry in enumerate(remaining)
        )

    @staticmethod
    def reorder(
        deck: CardDeck,
        ordered_card_ids: tuple[str, ...],
    ) -> tuple[CardDeckEntry, ...]:
        """Apply one complete permutation of current deck membership."""
        if len(ordered_card_ids) != len(set(ordered_card_ids)):
            raise CardDeckConflictError("Deck order contains duplicate Cards")
        current = {entry.card_id for entry in deck.entries}
        if set(ordered_card_ids) != current:
            raise CardDeckConflictError(
                "Deck order must contain every current Card exactly once"
            )
        return tuple(
            CardDeckEntry(card_id, position)
            for position, card_id in enumerate(ordered_card_ids)
        )


class CardDeckService:
    """Expose revision-safe commands for the one current POC deck."""

    def __init__(
        self,
        *,
        decks: CardDeckRepository,
        cards: CardPoolCardQuery,
        policy: CardDeckPolicy,
    ) -> None:
        self._decks = decks
        self._cards = cards
        self._policy = policy

    def get(self) -> CardDeck:
        """Return the initialized POC deck."""
        deck = self._decks.get()
        if deck is None:
            raise CardDeckNotFoundError(POC_DECK_ID)
        return deck

    def add(self, card_id: str, *, expected_revision: int) -> CardDeck:
        """Append one existing pool Card by CAS."""
        deck = self._current(expected_revision)
        if self._cards.get(card_id) is None:
            raise CardDeckNotFoundError(card_id)
        return self._decks.replace_entries(
            deck.deck_id,
            self._policy.add(deck, card_id),
            expected_revision=expected_revision,
        )

    def remove(self, card_id: str, *, expected_revision: int) -> CardDeck:
        """Remove one current member by CAS."""
        deck = self._current(expected_revision)
        return self._decks.replace_entries(
            deck.deck_id,
            self._policy.remove(deck, card_id),
            expected_revision=expected_revision,
        )

    def reorder(
        self,
        ordered_card_ids: tuple[str, ...],
        *,
        expected_revision: int,
    ) -> CardDeck:
        """Replace deck order with one complete membership permutation."""
        deck = self._current(expected_revision)
        return self._decks.replace_entries(
            deck.deck_id,
            self._policy.reorder(deck, ordered_card_ids),
            expected_revision=expected_revision,
        )

    def _current(self, expected_revision: int) -> CardDeck:
        deck = self.get()
        if deck.revision != expected_revision:
            raise CardDeckConflictError("Deck revision is stale")
        return deck
