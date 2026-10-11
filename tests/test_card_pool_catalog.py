"""Behavior tests for current Card-pool queries."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application.card_battler_card_catalog import (
    CardPoolCatalogService,
)
from comfyreview.application.card_battler_card_pool import (
    CardPoolNotFoundError,
    CardPoolRepository,
)
from tests.test_card_development_candidate_groups import _pool_card


class _Cards:
    def __init__(self) -> None:
        self.card = _pool_card()

    def list_cards(self):
        return (self.card,)

    def get(self, card_id):
        return (
            self.card if card_id == self.card.state.identity.card_id else None
        )


def test_card_pool_catalog_lists_and_requires_current_cards() -> None:
    cards = _Cards()
    service = CardPoolCatalogService(cast(CardPoolRepository, cards))

    assert service.list_cards() == (cards.card,)
    assert service.get(cards.card.state.identity.card_id) == cards.card
    with pytest.raises(CardPoolNotFoundError, match="missing"):
        service.get("missing")
