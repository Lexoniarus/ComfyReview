"""Concrete external-system providers used by the composition root."""

from comfyreview.providers.curation_files import LocalCurationFileManager
from comfyreview.providers.legacy_output_import import (
    LocalLegacyOutputImportSource,
)
from comfyreview.providers.output_images import CanonicalOutputImageCatalog

__all__ = [
    "CanonicalOutputImageCatalog",
    "LocalCurationFileManager",
    "LocalLegacyOutputImportSource",
]
