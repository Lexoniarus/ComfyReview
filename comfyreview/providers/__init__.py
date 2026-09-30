"""Concrete external-system providers used by the composition root."""

from comfyreview.providers.comfyui import (
    JsonHttpResponse,
    NativeComfyUiProvider,
    UrlLibJsonTransport,
)
from comfyreview.providers.curation_files import LocalCurationFileManager
from comfyreview.providers.generation_outputs import (
    LocalGenerationOutputSource,
)
from comfyreview.providers.legacy_output_import import (
    LocalLegacyOutputImportSource,
)
from comfyreview.providers.output_images import CanonicalOutputImageCatalog
from comfyreview.providers.prompt_identities import (
    UuidGenerationIdentitySource,
    UuidPromptIdentitySource,
)

__all__ = [
    "CanonicalOutputImageCatalog",
    "LocalCurationFileManager",
    "LocalGenerationOutputSource",
    "LocalLegacyOutputImportSource",
    "JsonHttpResponse",
    "NativeComfyUiProvider",
    "UrlLibJsonTransport",
    "UuidGenerationIdentitySource",
    "UuidPromptIdentitySource",
]
