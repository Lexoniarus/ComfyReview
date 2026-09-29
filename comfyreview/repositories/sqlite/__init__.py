"""SQLite persistence adapters."""

from comfyreview.repositories.sqlite.connection import connect_existing
from comfyreview.repositories.sqlite.legacy_schema import LegacySchemaManager

__all__ = ["LegacySchemaManager", "connect_existing"]
