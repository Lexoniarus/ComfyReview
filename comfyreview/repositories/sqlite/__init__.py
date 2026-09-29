"""SQLite persistence adapters."""

from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
)
from comfyreview.repositories.sqlite.connection import connect_existing
from comfyreview.repositories.sqlite.legacy_schema import LegacySchemaManager
from comfyreview.repositories.sqlite.path_relink import SqlitePathRelinker
from comfyreview.repositories.sqlite.reviews import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)

__all__ = [
    "CanonicalSchemaManager",
    "CanonicalSchemaValidationError",
    "LegacyProjectionJobQueue",
    "LegacySchemaManager",
    "SqlitePathRelinker",
    "SqlitePromptRepository",
    "SqliteReviewRepository",
    "connect_existing",
]
