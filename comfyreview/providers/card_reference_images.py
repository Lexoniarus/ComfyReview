"""Resolve original and accepted Card-candidate reference image bytes."""

from __future__ import annotations

import hashlib
from typing import Protocol

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImage,
    CardSourceImageProvider,
)
from comfyreview.application.generation_outputs import GenerationOutput


class CardRuntimeOutputQuery(Protocol):
    """Resolve one isolated Card output identity to validated metadata."""

    def output_by_image_uid(self, image_uid: str) -> GenerationOutput | None:
        """Return one Card output without canonical DB lookup."""
        ...


class CanonicalCardCandidateReferenceImageProvider:
    """Load a Candidate group's original or accepted reference image."""

    def __init__(
        self,
        canonical_sources: CardSourceImageProvider,
        card_outputs: CardRuntimeOutputQuery,
    ) -> None:
        self._canonical_sources = canonical_sources
        self._card_outputs = card_outputs

    def load(self, group: CardCandidateGroup) -> CardSourceImage:
        """Return bytes matching the persisted reference provenance."""
        if group.reference_image_uid == group.source_image_uid:
            image = self._canonical_sources.load(group.reference_image_uid)
        else:
            output = self._card_outputs.output_by_image_uid(
                group.reference_image_uid
            )
            if output is None:
                raise FileNotFoundError(group.reference_image_uid)
            content = output.path.read_bytes()
            image = CardSourceImage(
                output.image_uid,
                "image/png",
                content,
                hashlib.sha256(content).hexdigest(),
            )
        if image.content_hash != group.reference_content_hash:
            raise ValueError("Candidate reference hash no longer matches")
        return image
