"""Concrete external-system providers used by the composition root."""

from comfyreview.providers.output_images import (
    CanonicalFirstOutputImageCatalog,
    LocalOutputImageCatalog,
)

__all__ = [
    "CanonicalFirstOutputImageCatalog",
    "LocalOutputImageCatalog",
]
