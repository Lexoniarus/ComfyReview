"""Concrete external-system providers used by the composition root."""

from comfyreview.providers.comfyui import (
    JsonHttpResponse,
    NativeComfyUiProvider,
    UrlLibJsonTransport,
)
from comfyreview.providers.curation_files import LocalCurationFileManager
from comfyreview.providers.file_urls import OutputFileUrlMapper
from comfyreview.providers.generation_outputs import (
    LocalGenerationOutputRecoverySource,
    LocalGenerationOutputSource,
)
from comfyreview.providers.image_geometry import (
    InvalidPngError,
    PngHeaderDimensionReader,
)
from comfyreview.providers.legacy_output_import import (
    LocalLegacyOutputImportSource,
)
from comfyreview.providers.lm_studio import (
    LmStudioJsonResponse,
    NativeLmStudioProvider,
    UrlLibLmStudioJsonTransport,
)
from comfyreview.providers.output_images import CanonicalOutputImageCatalog
from comfyreview.providers.prompt_identities import (
    UuidGenerationIdentitySource,
    UuidGenerationProfileIdentitySource,
    UuidPromptIdentitySource,
)

__all__ = [
    "CanonicalOutputImageCatalog",
    "LocalCurationFileManager",
    "LocalGenerationOutputSource",
    "LocalGenerationOutputRecoverySource",
    "LocalLegacyOutputImportSource",
    "InvalidPngError",
    "PngHeaderDimensionReader",
    "JsonHttpResponse",
    "LmStudioJsonResponse",
    "NativeComfyUiProvider",
    "NativeLmStudioProvider",
    "OutputFileUrlMapper",
    "UrlLibJsonTransport",
    "UrlLibLmStudioJsonTransport",
    "UuidGenerationIdentitySource",
    "UuidGenerationProfileIdentitySource",
    "UuidPromptIdentitySource",
]
