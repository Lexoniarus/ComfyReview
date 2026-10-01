"""SQLite persistence adapters."""

from comfyreview.repositories.sqlite.analytics import SqliteAnalyticsRepository
from comfyreview.repositories.sqlite.analytics_reports import (
    SqliteAnalyticsReportRepository,
)
from comfyreview.repositories.sqlite.arena import SqliteArenaRepository
from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)
from comfyreview.repositories.sqlite.curation import SqliteCurationRepository
from comfyreview.repositories.sqlite.generation_outputs import (
    SqliteGenerationOutputRepository,
)
from comfyreview.repositories.sqlite.generations import (
    SqliteGenerationRepository,
)
from comfyreview.repositories.sqlite.image_queries import (
    SqliteImageContextRepository,
    SqliteReviewCandidateRepository,
    SqliteScopeFacetRepository,
)
from comfyreview.repositories.sqlite.legacy_schema import LegacySchemaManager
from comfyreview.repositories.sqlite.output_images import (
    SqliteOutputImageRepository,
)
from comfyreview.repositories.sqlite.prompt_catalog import (
    SqlitePromptCatalogRepository,
)
from comfyreview.repositories.sqlite.ranking import SqliteRankingRepository
from comfyreview.repositories.sqlite.reviews import SqliteReviewRepository

__all__ = [
    "SqliteAnalyticsRepository",
    "SqliteAnalyticsReportRepository",
    "CanonicalSchemaManager",
    "CanonicalSchemaValidationError",
    "LegacySchemaManager",
    "SqliteOutputImageRepository",
    "SqlitePromptCatalogRepository",
    "SqliteArenaRepository",
    "SqliteCurationRepository",
    "SqliteGenerationRepository",
    "SqliteGenerationOutputRepository",
    "SqliteImageContextRepository",
    "SqliteRankingRepository",
    "SqliteReviewRepository",
    "SqliteReviewCandidateRepository",
    "SqliteScopeFacetRepository",
    "connect_existing",
    "connect_read_only",
]
