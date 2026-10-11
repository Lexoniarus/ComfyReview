"""Resolve original and accepted Card-session reference image bytes."""

from __future__ import annotations

import hashlib
from typing import Protocol

from comfyreview.application.card_battler_semantics import (
    CardSourceImage,
    CardSourceImageProvider,
)
from comfyreview.application.card_battler_sessions import (
    CardActiveImageKind,
    CardSession,
)
from comfyreview.application.generation_outputs import GenerationOutput


class CardRuntimeOutputQuery(Protocol):
    """Resolve one isolated Card output identity to validated metadata."""

    def output_by_image_uid(self, image_uid: str) -> GenerationOutput | None:
        """Return one Card output without canonical DB lookup."""
        ...


class CanonicalCardSessionReferenceImageProvider:
    """Load active source or Card-runtime output bytes by stable identity."""

    def __init__(
        self,
        canonical_sources: CardSourceImageProvider,
        card_outputs: CardRuntimeOutputQuery,
    ) -> None:
        self._canonical_sources = canonical_sources
        self._card_outputs = card_outputs

    def load(self, session: CardSession) -> CardSourceImage:
        """Return bytes whose UID and hash match the persisted active reference."""
        if session.active_image_kind is CardActiveImageKind.SOURCE:
            image = self._canonical_sources.load(session.active_image_uid)
        else:
            output = self._card_outputs.output_by_image_uid(
                session.active_image_uid
            )
            if output is None:
                raise FileNotFoundError(session.active_image_uid)
            content = output.path.read_bytes()
            image = CardSourceImage(
                output.image_uid,
                "image/png",
                content,
                hashlib.sha256(content).hexdigest(),
            )
        if image.content_hash != session.active_content_hash:
            raise ValueError("active Card reference hash no longer matches")
        return image
