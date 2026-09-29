"""SQLite persistence adapters."""

from comfyreview.repositories.sqlite.connection import connect_existing
from comfyreview.repositories.sqlite.legacy_schema import LegacySchemaManager
from comfyreview.repositories.sqlite.reviews import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)

__all__ = [
    "LegacyProjectionJobQueue",
    "LegacySchemaManager",
    "SqlitePromptRepository",
    "SqliteReviewRepository",
    "connect_existing",
]
