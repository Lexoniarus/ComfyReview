"""Canonical filesystem adapter for Card Factory source image bytes."""

from __future__ import annotations

import hashlib
from typing import Protocol

from comfyreview.application.card_battler_semantics import CardSourceImage
from comfyreview.application.reviews import OutputImageReference, ReviewImage


class CanonicalCardImageResolver(Protocol):
    """Resolve canonical identity through the existing validated boundary."""

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        """Return an already path-validated canonical image."""
        ...


class CanonicalCardSourceImageProvider:
    """Read bytes only after canonical UID and output-root validation."""

    def __init__(self, resolver: CanonicalCardImageResolver) -> None:
        self._resolver = resolver

    def load(self, image_uid: str) -> CardSourceImage:
        """Return PNG bytes for one canonical live image UID."""
        reference = OutputImageReference.from_client_uid(image_uid)
        image = self._resolver.resolve(reference)
        content = image.pair.png_path.read_bytes()
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            raise ValueError("canonical Card source is not a PNG image")
        return CardSourceImage(
            image_uid=image.image_uid,
            mime_type="image/png",
            content=content,
            content_hash=hashlib.sha256(content).hexdigest(),
        )
