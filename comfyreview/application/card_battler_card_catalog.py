"""Application queries for the confirmed POC Card pool."""

from __future__ import annotations

from comfyreview.application.card_battler_card_pool import (
    CardPoolCard,
    CardPoolNotFoundError,
    CardPoolRepository,
)


class CardPoolCatalogService:
    """Expose current confirmed Cards without leaking a repository to routes."""

    def __init__(self, cards: CardPoolRepository) -> None:
        self._cards = cards

    def list_cards(self) -> tuple[CardPoolCard, ...]:
        """Return every current POC Card in stable repository order."""
        return self._cards.list_cards()

    def get(self, card_id: str) -> CardPoolCard:
        """Return one current POC Card or a typed not-found failure."""
        card = self._cards.get(card_id)
        if card is None:
            raise CardPoolNotFoundError(card_id)
        return card
