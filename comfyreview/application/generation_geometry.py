"""Typed generation geometry and rebuildable image classification."""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum


class AspectFormat(StrEnum):
    """Name one supported output aspect and orientation."""

    PORTRAIT_2_3 = "2:3"
    LANDSCAPE_3_2 = "3:2"
    LANDSCAPE_16_9 = "16:9"
    PORTRAIT_9_16 = "9:16"
    SQUARE_1_1 = "1:1"


class ResolutionClass(StrEnum):
    """Name one output class by its stable browser-facing value."""

    HD_720 = "720"
    FULL_HD_1080 = "1080"
    UHD_2160 = "2160"


class OutputTier(StrEnum):
    """Persisted compatibility representation of a resolution class."""

    HD_720 = "hd_720"
    FULL_HD_1080 = "full_hd_1080"
    UHD_4K = "uhd_4k"

    @classmethod
    def from_resolution_class(
        cls, resolution_class: ResolutionClass
    ) -> OutputTier:
        """Translate the browser-facing class to stored provenance."""
        return {
            ResolutionClass.HD_720: cls.HD_720,
            ResolutionClass.FULL_HD_1080: cls.FULL_HD_1080,
            ResolutionClass.UHD_2160: cls.UHD_4K,
        }[resolution_class]

    def to_resolution_class(self) -> ResolutionClass:
        """Translate stored provenance to the browser-facing class."""
        return {
            self.HD_720: ResolutionClass.HD_720,
            self.FULL_HD_1080: ResolutionClass.FULL_HD_1080,
            self.UHD_4K: ResolutionClass.UHD_2160,
        }[self]


@dataclass(frozen=True, slots=True)
class GenerationGeometry:
    """Preserve semantic selection plus concrete workflow dimensions."""

    aspect_format: AspectFormat
    resolution_class: ResolutionClass
    source_width: int
    source_height: int
    output_tier: OutputTier
    output_width: int
    output_height: int


@dataclass(frozen=True, slots=True)
class ImageGeometryProjection:
    """Describe one rebuildable classification of actual image dimensions."""

    image_uid: str
    actual_width: int
    actual_height: int
    aspect_format: AspectFormat
    resolution_class: ResolutionClass
    target_width: int
    target_height: int
    exact: bool
    classifier_version: int = 1


class GenerationGeometryPolicy:
    """Resolve the fixed product matrix for generation and analysis."""

    _SOURCE_DIMENSIONS = {
        AspectFormat.PORTRAIT_2_3: (768, 1152),
        AspectFormat.LANDSCAPE_3_2: (1152, 768),
        AspectFormat.LANDSCAPE_16_9: (1280, 720),
        AspectFormat.PORTRAIT_9_16: (720, 1280),
        AspectFormat.SQUARE_1_1: (1024, 1024),
    }
    _TARGET_DIMENSIONS = {
        (AspectFormat.PORTRAIT_2_3, ResolutionClass.HD_720): (720, 1080),
        (AspectFormat.PORTRAIT_2_3, ResolutionClass.FULL_HD_1080): (
            1080,
            1620,
        ),
        (AspectFormat.PORTRAIT_2_3, ResolutionClass.UHD_2160): (3072, 4608),
        (AspectFormat.LANDSCAPE_3_2, ResolutionClass.HD_720): (1080, 720),
        (AspectFormat.LANDSCAPE_3_2, ResolutionClass.FULL_HD_1080): (
            1620,
            1080,
        ),
        (AspectFormat.LANDSCAPE_3_2, ResolutionClass.UHD_2160): (4608, 3072),
        (AspectFormat.LANDSCAPE_16_9, ResolutionClass.HD_720): (1280, 720),
        (AspectFormat.LANDSCAPE_16_9, ResolutionClass.FULL_HD_1080): (
            1920,
            1080,
        ),
        (AspectFormat.LANDSCAPE_16_9, ResolutionClass.UHD_2160): (5120, 2880),
        (AspectFormat.PORTRAIT_9_16, ResolutionClass.HD_720): (720, 1280),
        (AspectFormat.PORTRAIT_9_16, ResolutionClass.FULL_HD_1080): (
            1080,
            1920,
        ),
        (AspectFormat.PORTRAIT_9_16, ResolutionClass.UHD_2160): (2880, 5120),
        (AspectFormat.SQUARE_1_1, ResolutionClass.HD_720): (720, 720),
        (AspectFormat.SQUARE_1_1, ResolutionClass.FULL_HD_1080): (1080, 1080),
        (AspectFormat.SQUARE_1_1, ResolutionClass.UHD_2160): (4096, 4096),
    }
    _ASPECT_RATIOS = {
        key: dimensions[0] / dimensions[1]
        for key, dimensions in _SOURCE_DIMENSIONS.items()
    }
    _SHORT_EDGES = {
        ResolutionClass.HD_720: 720,
        ResolutionClass.FULL_HD_1080: 1080,
        ResolutionClass.UHD_2160: 2160,
    }

    def resolve(
        self,
        aspect_format: AspectFormat,
        resolution_class: ResolutionClass,
    ) -> GenerationGeometry:
        """Return validated concrete source and output matrix dimensions."""
        try:
            source_width, source_height = self._SOURCE_DIMENSIONS[
                aspect_format
            ]
            output_width, output_height = self._TARGET_DIMENSIONS[
                (aspect_format, resolution_class)
            ]
        except KeyError as error:
            raise ValueError("unsupported generation geometry") from error
        return GenerationGeometry(
            aspect_format=aspect_format,
            resolution_class=resolution_class,
            source_width=source_width,
            source_height=source_height,
            output_tier=OutputTier.from_resolution_class(resolution_class),
            output_width=output_width,
            output_height=output_height,
        )

    def classify(
        self,
        image_uid: str,
        width: int,
        height: int,
    ) -> ImageGeometryProjection:
        """Classify actual dimensions without changing the source image."""
        if width < 1 or height < 1:
            raise ValueError("image dimensions must be positive")
        ratio = width / height
        formats = tuple(AspectFormat)
        aspect_format = min(
            formats,
            key=lambda candidate: (
                abs(math.log(ratio / self._ASPECT_RATIOS[candidate])),
                formats.index(candidate),
            ),
        )
        short_edge = min(width, height)
        resolution_class = min(
            ResolutionClass,
            key=lambda candidate: (
                abs(short_edge - self._SHORT_EDGES[candidate]),
                -self._SHORT_EDGES[candidate],
            ),
        )
        target_width, target_height = self._TARGET_DIMENSIONS[
            (aspect_format, resolution_class)
        ]
        return ImageGeometryProjection(
            image_uid=str(image_uid),
            actual_width=width,
            actual_height=height,
            aspect_format=aspect_format,
            resolution_class=resolution_class,
            target_width=target_width,
            target_height=target_height,
            exact=(width, height) == (target_width, target_height),
        )
