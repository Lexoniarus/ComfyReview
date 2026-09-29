"""Application contracts for reading ComfyUI output images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CanonicalOutputImageRecord:
    """Describe one live canonical image joined to generation facts."""

    image_uid: str
    generation_uid: str
    png_path: Path
    json_path: Path | None
    output_node_id: str
    output_index: int
    model_branch: str
    checkpoint: str
    combo_key: str
    seed: int | None
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None
    loras_json: str
    positive_prompt: str
    negative_prompt: str
    source: str
    raw_metadata_json: str | None
    workflow_json: str | None
    current_rating: int | None
    review_version: int | None


@dataclass(frozen=True, slots=True)
class OutputImageReadModel:
    """Describe one output image for gallery/review presentation."""

    png_path: Path
    json_path: Path | None
    subdir: str
    model_branch: str
    checkpoint: str
    combo_key: str
    meta: dict[str, Any]
    image_uid: str | None = None
    generation_uid: str | None = None
    output_node_id: str = ""
    output_index: int = 0
    current_rating: int | None = None
    review_version: int | None = None
    source: str = "legacy_sidecar"


class CanonicalOutputImageSource(Protocol):
    """Read normalized live images from canonical persistence."""

    def list_live_images(self) -> tuple[CanonicalOutputImageRecord, ...]:
        """Return every currently live canonical image."""
        ...

    def get_live_image(
        self,
        image_uid: str,
    ) -> CanonicalOutputImageRecord | None:
        """Return one live image by stable image identity."""
        ...


class OutputImageCatalog(Protocol):
    """Provide the current read-only catalog of output images."""

    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        """Return discovered output images in stable catalog order."""
        ...
