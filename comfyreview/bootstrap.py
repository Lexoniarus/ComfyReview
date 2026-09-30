"""FastAPI composition root and owned application lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from comfyreview.application import (
    AnalyticsService,
    ArenaService,
    CanonicalSchemaLifecycle,
    CurationService,
    GenerationService,
    LegacySchemaLifecycle,
    OutputImageCatalog,
    PlaygroundService,
    PromptCatalogService,
    PromptRenderer,
    PromptSelectionPolicy,
    RankingService,
    ReviewService,
    WorkflowCompiler,
)
from comfyreview.observability import (
    RequestTracingMiddleware,
    configure_logging,
)
from comfyreview.providers import (
    CanonicalOutputImageCatalog,
    LocalCurationFileManager,
    NativeComfyUiProvider,
    UrlLibJsonTransport,
    UuidGenerationIdentitySource,
    UuidPromptIdentitySource,
)
from comfyreview.repositories.filesystem import JsonWorkflowBlueprintRepository
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    LegacySchemaManager,
    SqliteAnalyticsRepository,
    SqliteArenaRepository,
    SqliteCurationRepository,
    SqliteGenerationRepository,
    SqliteOutputImageRepository,
    SqlitePromptCatalogRepository,
    SqliteRankingRepository,
    SqliteReviewRepository,
)
from comfyreview.settings import Settings, load_settings
from routers.arena_router import router as arena_router
from routers.index_router import router as index_router
from routers.playground import router as playground_router
from routers.stats_router import router as stats_router
from routers.top_router import router as top_router
from services.analytics_page_service import AnalyticsPageService
from services.file_urls import existing_png_path_to_url
from services.output_file_service import OutputFileService
from services.playground_hub_service import PlaygroundHubService


@dataclass(frozen=True)
class ApplicationContainer:
    """Own configured application resources and their lifecycle ports."""

    settings: Settings
    canonical_schema: CanonicalSchemaLifecycle
    schema_lifecycle: LegacySchemaLifecycle
    output_images: OutputImageCatalog
    analytics_service: AnalyticsService
    analytics_pages: AnalyticsPageService
    playground_hub: PlaygroundHubService
    generation_service: GenerationService
    prompt_catalog_service: PromptCatalogService
    playground_service: PlaygroundService
    review_service: ReviewService
    ranking_service: RankingService
    arena_service: ArenaService
    curation_service: CurationService


def _prepare_directories(settings: Settings) -> None:
    directories = (
        settings.output_root,
        settings.data_directory,
        settings.trash_root,
        settings.lora_export_root,
        settings.workflows_directory,
        settings.comfyui_checkpoints_directory,
    )
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


def build_application_container(
    settings: Settings | None = None,
) -> ApplicationContainer:
    """Build the default adapters for one application instance."""
    configured = settings if settings is not None else load_settings()
    output_images = CanonicalOutputImageCatalog(
        output_root=configured.output_root,
        canonical_images=SqliteOutputImageRepository(
            configured.canonical_database_path
        ),
    )
    review_service = ReviewService(
        image_resolver=output_images,
        reviews=SqliteReviewRepository(configured.canonical_database_path),
        deletions=OutputFileService(
            output_root=configured.output_root,
            trash_root=configured.trash_root,
        ),
        preserve_deleted_files=configured.soft_delete_to_trash,
    )
    ranking_service = RankingService(
        SqliteRankingRepository(
            configured.canonical_database_path,
            output_root=configured.output_root,
            allowed_set_keys=configured.curation_set_keys,
        )
    )
    prompt_catalog_service = PromptCatalogService(
        repository=SqlitePromptCatalogRepository(
            configured.canonical_database_path
        ),
        identities=UuidPromptIdentitySource(),
    )
    analytics_service = AnalyticsService(
        SqliteAnalyticsRepository(configured.canonical_database_path)
    )
    return ApplicationContainer(
        settings=configured,
        canonical_schema=CanonicalSchemaManager(
            configured.canonical_database_path
        ),
        schema_lifecycle=LegacySchemaManager(
            configured,
            startup_database_names=("playground",),
        ),
        output_images=output_images,
        analytics_service=analytics_service,
        analytics_pages=AnalyticsPageService(
            database_path=configured.canonical_database_path,
            analytics=analytics_service,
            image_url=existing_png_path_to_url,
        ),
        playground_hub=PlaygroundHubService(
            analytics=analytics_service,
            image_url=existing_png_path_to_url,
            default_max_attempts=configured.default_max_tries,
        ),
        generation_service=GenerationService(
            blueprints=JsonWorkflowBlueprintRepository(
                configured.workflows_directory
            ),
            compiler=WorkflowCompiler(),
            generations=SqliteGenerationRepository(
                configured.canonical_database_path
            ),
            comfyui=NativeComfyUiProvider(
                UrlLibJsonTransport(configured.comfyui_base_url)
            ),
            identities=UuidGenerationIdentitySource(),
        ),
        prompt_catalog_service=prompt_catalog_service,
        playground_service=PlaygroundService(
            catalog=prompt_catalog_service,
            selection_policy=PromptSelectionPolicy(),
            renderer=PromptRenderer(),
        ),
        review_service=review_service,
        ranking_service=ranking_service,
        arena_service=ArenaService(
            rankings=ranking_service,
            repository=SqliteArenaRepository(
                configured.canonical_database_path
            ),
        ),
        curation_service=CurationService(
            repository=SqliteCurationRepository(
                configured.canonical_database_path
            ),
            files=LocalCurationFileManager(configured.output_root),
            allowed_set_keys=configured.curation_set_keys,
        ),
    )


def create_app(container: ApplicationContainer | None = None) -> FastAPI:
    """Compose a FastAPI app without starting its owned resources."""
    resources = (
        container if container is not None else build_application_container()
    )

    @asynccontextmanager
    async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
        _prepare_directories(resources.settings)
        resources.canonical_schema.prepare_startup()
        resources.schema_lifecycle.prepare_startup()
        yield

    configure_logging()
    application = FastAPI(title="Comfy Review", lifespan=lifespan)
    application.state.container = resources
    application.add_middleware(RequestTracingMiddleware)
    application.mount(
        "/files",
        StaticFiles(
            directory=str(resources.settings.output_root),
            check_dir=False,
        ),
        name="files",
    )
    application.mount(
        "/static",
        StaticFiles(
            directory=str(Path(resources.settings.base_directory) / "static"),
            check_dir=False,
        ),
        name="static",
    )
    application.include_router(index_router)
    application.include_router(top_router)
    application.include_router(arena_router)
    application.include_router(stats_router)
    application.include_router(playground_router)
    return application
