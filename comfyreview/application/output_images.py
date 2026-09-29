"""Application contracts for reading discovered ComfyUI output images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class OutputImageReadModel:
    """Describe one output image without assigning canonical identity."""

    png_path: Path
    json_path: Path
    subdir: str
    model_branch: str
    checkpoint: str
    combo_key: str
    meta: dict[str, Any]


class OutputImageCatalog(Protocol):
    """Provide the current read-only catalog of output images."""

    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        """Return discovered output images in stable catalog order."""
        ...
