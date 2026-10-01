"""FastAPI composition root and owned application lifecycle."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    AnalyticsReportService,
    AnalyticsService,
    ArenaService,
    CanonicalSchemaLifecycle,
    CurationService,
    DraftOverridePolicy,
    GenerationOutputCollector,
    GenerationQueryService,
    GenerationReconciliationService,
    GenerationService,
    ImageContextQueryService,
    OutputImageCatalog,
    PlaygroundGenerationPolicy,
    PlaygroundService,
    PlaygroundSubmissionService,
    PromptCatalogService,
    PromptRenderer,
    PromptSelectionPolicy,
    ReviewCandidateService,
    ReviewService,
    ScopeFacetService,
    WorkflowCompiler,
    WorkflowDefaultsService,
)
from comfyreview.observability import (
    RequestTracingMiddleware,
    configure_logging,
)
from comfyreview.providers import (
    CanonicalOutputImageCatalog,
    LocalCurationFileManager,
    LocalGenerationOutputSource,
    NativeComfyUiProvider,
    OutputFileUrlMapper,
    UrlLibJsonTransport,
    UuidGenerationIdentitySource,
    UuidPromptIdentitySource,
)
from comfyreview.repositories.filesystem import (
    JsonComfyUiCapabilityCache,
    JsonWorkflowBlueprintRepository,
    PlaygroundGeneratorStateRepository,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteAnalyticsReportRepository,
    SqliteAnalyticsRepository,
    SqliteArenaRepository,
    SqliteCurationRepository,
    SqliteGenerationOutputRepository,
    SqliteGenerationQueryRepository,
    SqliteGenerationRepository,
    SqliteImageContextRepository,
    SqliteImageFileRepository,
    SqliteOutputImageRepository,
    SqlitePromptCatalogRepository,
    SqliteReviewCandidateRepository,
    SqliteReviewRepository,
    SqliteScopeFacetRepository,
)
from comfyreview.settings import Settings, load_settings
from routers.api_v2_router import router as api_v2_router
from routers.arena_router import router as arena_router
from routers.index_router import router as index_router
from routers.playground import router as playground_router
from routers.stats_router import router as stats_router
from routers.top_router import router as top_router
from services.analytics_page_service import AnalyticsPageService
from services.output_file_service import OutputFileService
from services.playground_discovery_service import PlaygroundDiscoveryService
from services.playground_generator_ui.ports import PlaygroundGeneratorState
from services.playground_hub_service import PlaygroundHubService
from services.playground_label_service import PromptLabelService
from services.prompt_catalog_view_service import PromptCatalogViewService


@dataclass(frozen=True)
class ApplicationContainer:
    """Own configured application resources and their lifecycle ports."""

    settings: Settings
    canonical_schema: CanonicalSchemaLifecycle
    output_images: OutputImageCatalog
    file_urls: OutputFileUrlMapper
    image_contexts: ImageContextQueryService
    scope_facets: ScopeFacetService
    review_candidates: ReviewCandidateService
    image_responses: ImageResponseMapper
    analytics_service: AnalyticsService
    analytics_reports: AnalyticsReportService
    analytics_pages: AnalyticsPageService
    playground_hub: PlaygroundHubService
    playground_discovery: PlaygroundDiscoveryService
    playground_ui_state: PlaygroundGeneratorState
    generation_service: GenerationService
    generation_queries: GenerationQueryService
    generation_reconciliation: GenerationReconciliationService
    prompt_catalog_service: PromptCatalogService
    prompt_catalog_views: PromptCatalogViewService
    prompt_labels: PromptLabelService
    playground_service: PlaygroundService
    playground_submission_service: PlaygroundSubmissionService
    workflow_defaults: WorkflowDefaultsService
    review_service: ReviewService
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
    file_urls = OutputFileUrlMapper(configured.output_root)
    prompt_renderer = PromptRenderer()
    draft_overrides = DraftOverridePolicy(prompt_renderer)
    image_contexts = ImageContextQueryService(
        SqliteImageContextRepository(configured.canonical_database_path),
        draft_overrides,
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
    prompt_catalog_service = PromptCatalogService(
        repository=SqlitePromptCatalogRepository(
            configured.canonical_database_path
        ),
        identities=UuidPromptIdentitySource(),
    )
    analytics_service = AnalyticsService(
        SqliteAnalyticsRepository(configured.canonical_database_path)
    )
    analytics_reports = AnalyticsReportService(
        SqliteAnalyticsReportRepository(configured.canonical_database_path)
    )
    comfyui_provider = NativeComfyUiProvider(
        UrlLibJsonTransport(configured.comfyui_base_url)
    )
    blueprints = JsonWorkflowBlueprintRepository(
        configured.workflows_directory
    )
    generation_output_collector = GenerationOutputCollector(
        comfyui=comfyui_provider,
        source=LocalGenerationOutputSource(configured.output_root),
        repository=SqliteGenerationOutputRepository(
            configured.canonical_database_path
        ),
    )
    generation_service = GenerationService(
        blueprints=blueprints,
        compiler=WorkflowCompiler(),
        generations=SqliteGenerationRepository(
            configured.canonical_database_path
        ),
        comfyui=comfyui_provider,
        outputs=generation_output_collector,
        identities=UuidGenerationIdentitySource(),
    )
    generation_reconciliation = GenerationReconciliationService(
        generations=SqliteGenerationRepository(
            configured.canonical_database_path
        ),
        comfyui=comfyui_provider,
        outputs=generation_output_collector,
    )
    return ApplicationContainer(
        settings=configured,
        canonical_schema=CanonicalSchemaManager(
            configured.canonical_database_path
        ),
        output_images=output_images,
        file_urls=file_urls,
        image_contexts=image_contexts,
        scope_facets=ScopeFacetService(
            SqliteScopeFacetRepository(configured.canonical_database_path)
        ),
        review_candidates=ReviewCandidateService(
            SqliteReviewCandidateRepository(
                configured.canonical_database_path
            ),
            draft_overrides,
        ),
        image_responses=ImageResponseMapper(
            files=SqliteImageFileRepository(
                configured.canonical_database_path
            ),
            urls=file_urls,
        ),
        analytics_service=analytics_service,
        analytics_reports=analytics_reports,
        analytics_pages=AnalyticsPageService(
            analytics=analytics_service,
            reports=analytics_reports,
            image_url=file_urls.existing_url,
        ),
        playground_hub=PlaygroundHubService(
            analytics=analytics_service,
            image_url=file_urls.existing_url,
            default_max_attempts=configured.default_max_tries,
        ),
        playground_discovery=PlaygroundDiscoveryService(
            comfyui_provider,
            JsonComfyUiCapabilityCache(
                configured.data_directory
                / "ui_state"
                / "comfy_discovery_cache.json"
            ),
        ),
        playground_ui_state=PlaygroundGeneratorStateRepository(
            head_path=(
                configured.data_directory
                / "ui_state"
                / "playground_generator_last.json"
            ),
            preview_path=(
                configured.data_directory
                / "ui_state"
                / "playground_generator_preview.json"
            ),
        ),
        generation_service=generation_service,
        generation_queries=GenerationQueryService(
            SqliteGenerationQueryRepository(configured.canonical_database_path)
        ),
        generation_reconciliation=generation_reconciliation,
        prompt_catalog_service=prompt_catalog_service,
        prompt_catalog_views=PromptCatalogViewService(prompt_catalog_service),
        prompt_labels=PromptLabelService(prompt_catalog_service),
        playground_service=PlaygroundService(
            catalog=prompt_catalog_service,
            selection_policy=PromptSelectionPolicy(),
            renderer=prompt_renderer,
        ),
        playground_submission_service=PlaygroundSubmissionService(
            generation=generation_service,
            policy=PlaygroundGenerationPolicy(
                blueprint_uid="default-character",
                blueprint_version=1,
                expected_output_roles=("primary",),
            ),
        ),
        workflow_defaults=WorkflowDefaultsService(blueprints),
        review_service=review_service,
        arena_service=ArenaService(
            images=image_contexts,
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
    application.include_router(api_v2_router)
    application.include_router(top_router)
    application.include_router(arena_router)
    application.include_router(stats_router)
    application.include_router(playground_router)
    return application
