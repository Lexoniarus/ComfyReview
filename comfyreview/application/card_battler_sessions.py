"""Typed contracts for persistent Card Factory prototype sessions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
)
from comfyreview.application.card_battler_semantics import SemanticImageProfile
from comfyreview.application.card_battler_visuals import VisualPromptRecipe
from comfyreview.domain.card_battler import CardImprint, StructuredCardSpec


class CardSessionOperationState(StrEnum):
    """Name the one externally visible Card-session operation state."""

    IDLE = "idle"
    GENERATING = "generating"


class CardActiveImageKind(StrEnum):
    """Distinguish the original source from an accepted candidate."""

    SOURCE = "source"
    CANDIDATE = "candidate"


@dataclass(frozen=True, slots=True)
class CardSession:
    """Persist one revisioned POC Card identity and current projection."""

    session_id: str
    revision: int
    source_image_uid: str
    source_content_hash: str
    semantic_profile: SemanticImageProfile
    imprint: CardImprint
    card: StructuredCardSpec
    visual_recipe: VisualPromptRecipe
    presentation: CardPresentationResult
    active_image_uid: str
    active_content_hash: str
    active_image_kind: CardActiveImageKind
    active_visual_tier: int
    operation_state: CardSessionOperationState

    def __post_init__(self) -> None:
        text_values = (
            self.session_id,
            self.source_image_uid,
            self.source_content_hash,
            self.active_image_uid,
            self.active_content_hash,
        )
        if any(
            not isinstance(value, str) or not value.strip()
            for value in text_values
        ):
            raise ValueError("Card session identities must be non-empty")
        if self.revision < 1:
            raise ValueError("Card session revision must be positive")
        if self.active_visual_tier < 0:
            raise ValueError("active visual tier must not be negative")
        if self.semantic_profile.image_uid != self.source_image_uid:
            raise ValueError(
                "Card session semantics must retain the source UID"
            )
        if self.imprint.source_image_uid != self.source_image_uid:
            raise ValueError("Card session imprint must retain the source UID")
        if (
            self.semantic_profile.semantic_revision
            != self.imprint.semantic_revision
        ):
            raise ValueError(
                "Card session semantic revision does not match imprint"
            )
        if self.card.imprint != self.imprint:
            raise ValueError(
                "Card session spec must retain its immutable imprint"
            )
        if self.visual_recipe.tier_ordinal != self.card.tier_ordinal:
            raise ValueError(
                "Card session visual recipe does not match Card tier"
            )


class CardSessionNotFoundError(LookupError):
    """Report an unknown prototype Card session."""


class CardSessionConflictError(RuntimeError):
    """Report a stale revision or forbidden concurrent mutation."""


class CardSessionCapacityError(RuntimeError):
    """Report that the bounded prototype store reached its session limit."""


class CardSessionRepository(Protocol):
    """Persist bounded revisioned prototype sessions with compare-and-swap."""

    def create(self, session: CardSession) -> CardSession:
        """Insert one initial session without evicting existing sessions."""
        ...

    def get(self, session_id: str) -> CardSession | None:
        """Return one session when present."""
        ...

    def replace(
        self,
        session: CardSession,
        *,
        expected_revision: int,
    ) -> CardSession:
        """Atomically replace one exact revision with its next revision."""
        ...
