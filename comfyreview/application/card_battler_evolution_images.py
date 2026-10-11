"""Application contracts for staging Card reference images in ComfyUI."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.card_battler_semantics import CardSourceImage


@dataclass(frozen=True, slots=True)
class StagedCardReferenceImage:
    """Carry only the relative LoadImage name returned by ComfyUI."""

    relative_name: str
    content_hash: str

    def __post_init__(self) -> None:
        if not self.relative_name or self.relative_name.startswith(
            ("/", "\\")
        ):
            raise ValueError("staged Card reference name must be relative")
        if ".." in self.relative_name.replace("\\", "/").split("/"):
            raise ValueError("staged Card reference name must not traverse")
        if not self.content_hash:
            raise ValueError("staged Card reference hash is required")


class CardReferenceImageStager(Protocol):
    """Stage validated bytes for a later ComfyUI LoadImage binding."""

    def stage(self, image: CardSourceImage) -> StagedCardReferenceImage:
        """Upload one image and return its provider-relative name."""
        ...
