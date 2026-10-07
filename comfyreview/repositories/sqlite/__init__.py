"""SQLite persistence adapters."""

from comfyreview.repositories.sqlite.analytics import SqliteAnalyticsRepository
from comfyreview.repositories.sqlite.analytics_coverage import (
    SqliteAnalyticsCoverageRepository,
)
from comfyreview.repositories.sqlite.analytics_reports import (
    SqliteAnalyticsReportRepository,
)
from comfyreview.repositories.sqlite.arena import SqliteArenaRepository
from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
)
from comfyreview.repositories.sqlite.catalog_evidence import (
    SqliteCatalogEvidenceRepository,
)
from comfyreview.repositories.sqlite.composition_analytics import (
    SqliteCompositionAnalyticsRepository,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)
from comfyreview.repositories.sqlite.content_classification import (
    SqliteImageContentLevelRepository,
    SqliteLoraCatalogRepository,
)
from comfyreview.repositories.sqlite.curation import SqliteCurationRepository
from comfyreview.repositories.sqlite.generation_outputs import (
    SqliteGenerationOutputRepository,
)
from comfyreview.repositories.sqlite.generation_queries import (
    SqliteGenerationQueryRepository,
)
from comfyreview.repositories.sqlite.generations import (
    SqliteGenerationRepository,
)
from comfyreview.repositories.sqlite.generator_state import (
    SqliteGeneratorStateRepository,
)
from comfyreview.repositories.sqlite.image_generator_handoff import (
    SqliteImageGeneratorHandoffRepository,
)
from comfyreview.repositories.sqlite.image_geometry import (
    SqliteImageGeometryRepository,
)
from comfyreview.repositories.sqlite.image_queries import (
    SqliteImageContextRepository,
    SqliteImageFileRepository,
    SqliteReviewCandidateRepository,
    SqliteScopeFacetRepository,
)
from comfyreview.repositories.sqlite.legacy_schema import LegacySchemaManager
from comfyreview.repositories.sqlite.output_images import (
    SqliteOutputImageRepository,
)
from comfyreview.repositories.sqlite.playground_evidence import (
    SqlitePlaygroundEvidenceRepository,
)
from comfyreview.repositories.sqlite.prompt_catalog import (
    SqlitePromptCatalogRepository,
)
from comfyreview.repositories.sqlite.ranking import SqliteRankingRepository
from comfyreview.repositories.sqlite.render_analytics import (
    SqliteRenderAnalyticsRepository,
)
from comfyreview.repositories.sqlite.render_guidance import (
    SqliteRenderEvidenceRepository,
)
from comfyreview.repositories.sqlite.reviews import (
    SqliteReviewHistoryRepository,
    SqliteReviewRepository,
)
from comfyreview.repositories.sqlite.workspace_settings import (
    SqliteGenerationProfileRepository,
    SqliteWorkspacePreferencesRepository,
)

__all__ = [
    "SqliteAnalyticsRepository",
    "SqliteAnalyticsCoverageRepository",
    "SqliteAnalyticsReportRepository",
    "SqliteCompositionAnalyticsRepository",
    "SqliteRenderAnalyticsRepository",
    "SqliteRenderEvidenceRepository",
    "CanonicalSchemaManager",
    "CanonicalSchemaValidationError",
    "SqliteCatalogEvidenceRepository",
    "LegacySchemaManager",
    "SqliteOutputImageRepository",
    "SqlitePlaygroundEvidenceRepository",
    "SqlitePromptCatalogRepository",
    "SqliteArenaRepository",
    "SqliteCurationRepository",
    "SqliteGenerationRepository",
    "SqliteGeneratorStateRepository",
    "SqliteGenerationOutputRepository",
    "SqliteGenerationQueryRepository",
    "SqliteImageContextRepository",
    "SqliteImageContentLevelRepository",
    "SqliteLoraCatalogRepository",
    "SqliteImageFileRepository",
    "SqliteImageGeometryRepository",
    "SqliteImageGeneratorHandoffRepository",
    "SqliteRankingRepository",
    "SqliteReviewRepository",
    "SqliteReviewHistoryRepository",
    "SqliteReviewCandidateRepository",
    "SqliteScopeFacetRepository",
    "SqliteGenerationProfileRepository",
    "SqliteWorkspacePreferencesRepository",
    "connect_existing",
    "connect_read_only",
]
