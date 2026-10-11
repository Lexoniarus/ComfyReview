"""Immutable confirmed Card Battler identity and current-state facts."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.domain.card_battler.cards import (
    CardImprint,
    StructuredCardSpec,
)


@dataclass(frozen=True, slots=True)
class CardIdentity:
    """Identify one confirmed POC card independently from its current state."""

    card_id: str
    source_image_uid: str
    source_content_hash: str
    semantic_revision: str
    imprint: CardImprint

    def __post_init__(self) -> None:
        values = (
            self.card_id,
            self.source_image_uid,
            self.source_content_hash,
            self.semantic_revision,
        )
        if any(not value.strip() for value in values):
            raise ValueError("Card identity fields must be non-empty")
        if self.imprint.source_image_uid != self.source_image_uid:
            raise ValueError("Card identity imprint must retain its source")
        if self.imprint.semantic_revision != self.semantic_revision:
            raise ValueError("Card identity semantic revision must match")


@dataclass(frozen=True, slots=True)
class CardState:
    """Freeze the one active rules-and-image state of a confirmed card."""

    identity: CardIdentity
    revision: int
    card: StructuredCardSpec
    active_image_uid: str
    active_content_hash: str
    visual_tier: int

    def __post_init__(self) -> None:
        if self.revision < 1:
            raise ValueError("Card state revision must be positive")
        if (
            not self.active_image_uid.strip()
            or not self.active_content_hash.strip()
        ):
            raise ValueError("Card state image provenance must be complete")
        if self.card.imprint != self.identity.imprint:
            raise ValueError("Card state must retain its identity imprint")
        if self.visual_tier != self.card.tier_ordinal:
            raise ValueError(
                "Card state visual tier must match its rules tier"
            )
