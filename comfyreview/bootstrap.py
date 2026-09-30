"""FastAPI composition root and owned application lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from comfyreview.application import (
    ArenaService,
    CanonicalSchemaLifecycle,
    CurationService,
    LegacySchemaLifecycle,
    OutputImageCatalog,
    PromptCatalogService,
    RankingService,
    ReviewService,
    WorkerRuntime,
)
from comfyreview.infrastructure import LegacyWorkerRuntime
from comfyreview.observability import (
    RequestTracingMiddleware,
    configure_logging,
)
from comfyreview.providers import (
    CanonicalOutputImageCatalog,
    LocalCurationFileManager,
    UuidPromptIdentitySource,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    LegacyProjectionJobQueue,
    LegacySchemaManager,
    SqliteArenaRepository,
    SqliteCurationRepository,
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
from services.output_file_service import OutputFileService


@dataclass(frozen=True)
class ApplicationContainer:
    """Own configured application resources and their lifecycle ports."""

    settings: Settings
    canonical_schema: CanonicalSchemaLifecycle
    schema_lifecycle: LegacySchemaLifecycle
    worker: WorkerRuntime
    output_images: OutputImageCatalog
    prompt_catalog_service: PromptCatalogService
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
    worker = LegacyWorkerRuntime(
        queue_database_path=configured.worker_queue_database_path,
        state_database_path=configured.worker_queue_database_path,
        ratings_database_path=configured.canonical_database_path,
        prompt_tokens_database_path=configured.canonical_database_path,
        prompt_ratings_database_path=configured.prompt_ratings_database_path,
        combo_database_path=configured.combo_prompts_database_path,
        playground_database_path=configured.playground_database_path,
        images_database_path=configured.images_database_path,
        debounce_seconds=configured.worker_debounce_seconds,
    )
    output_images = CanonicalOutputImageCatalog(
        output_root=configured.output_root,
        canonical_images=SqliteOutputImageRepository(
            configured.canonical_database_path
        ),
    )
    review_service = ReviewService(
        image_resolver=output_images,
        reviews=SqliteReviewRepository(configured.canonical_database_path),
        jobs=LegacyProjectionJobQueue(configured.worker_queue_database_path),
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
    legacy_runtime_settings = replace(
        configured,
        ratings_database_path=(
            configured.data_directory / "_legacy_runtime" / "ratings.sqlite3"
        ),
        prompt_tokens_database_path=(
            configured.data_directory
            / "_legacy_runtime"
            / "prompt_tokens.sqlite3"
        ),
    )
    return ApplicationContainer(
        settings=configured,
        canonical_schema=CanonicalSchemaManager(
            configured.canonical_database_path
        ),
        schema_lifecycle=LegacySchemaManager(legacy_runtime_settings),
        worker=worker,
        output_images=output_images,
        prompt_catalog_service=PromptCatalogService(
            repository=SqlitePromptCatalogRepository(
                configured.canonical_database_path
            ),
            identities=UuidPromptIdentitySource(),
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
        resources.worker.start()
        try:
            yield
        finally:
            resources.worker.stop(
                resources.settings.worker_shutdown_timeout_seconds
            )

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
