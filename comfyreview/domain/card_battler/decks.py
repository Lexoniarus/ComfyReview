"""Immutable POC deck facts."""

from __future__ import annotations

from dataclasses import dataclass

POC_DECK_CAPACITY = 40
POC_DECK_ID = "poc-deck"


@dataclass(frozen=True, slots=True)
class CardDeckEntry:
    """Place one unique confirmed card at one stable deck position."""

    card_id: str
    position: int

    def __post_init__(self) -> None:
        if not self.card_id.strip():
            raise ValueError("Deck card identity must be non-empty")
        if self.position < 0:
            raise ValueError("Deck position must not be negative")


@dataclass(frozen=True, slots=True)
class CardDeck:
    """Represent the one revision-safe POC deck."""

    deck_id: str
    revision: int
    entries: tuple[CardDeckEntry, ...]
    capacity: int = POC_DECK_CAPACITY

    def __post_init__(self) -> None:
        if not self.deck_id.strip():
            raise ValueError("Deck identity must be non-empty")
        if self.revision < 1:
            raise ValueError("Deck revision must be positive")
        if self.capacity != POC_DECK_CAPACITY:
            raise ValueError("POC deck capacity is fixed at forty")
        if len(self.entries) > self.capacity:
            raise ValueError("POC deck capacity exceeded")
        card_ids = tuple(entry.card_id for entry in self.entries)
        if len(card_ids) != len(set(card_ids)):
            raise ValueError("A card may appear in the POC deck only once")
        if tuple(entry.position for entry in self.entries) != tuple(
            range(len(self.entries))
        ):
            raise ValueError("Deck positions must be contiguous and ordered")
