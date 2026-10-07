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
    AnalyticsCoverageService,
    AnalyticsReportService,
    AnalyticsService,
    ArenaService,
    CanonicalSchemaLifecycle,
    CatalogEvidenceService,
    CompiledLoraGraphPolicy,
    CompositionAnalyticsService,
    CurationService,
    DraftOverridePolicy,
    GenerationLifecycleCoordinator,
    GenerationLifecycleWorker,
    GenerationOutputCollector,
    GenerationOutputRecoveryService,
    GenerationQueryService,
    GenerationReconciliationService,
    GenerationService,
    GeneratorStateService,
    ImageContentLevelService,
    ImageContextQueryService,
    ImageGeneratorHandoffService,
    ImageGeometryProjectionService,
    LoraCatalogService,
    LoraDraftSelectionService,
    LoraSelectionContentPolicy,
    LoraTriggerValidationService,
    OutputImageCatalog,
    PlaygroundEvidenceService,
    PlaygroundGenerationPolicy,
    PlaygroundGenerationSweepPolicy,
    PlaygroundService,
    PlaygroundSubmissionService,
    PromptCatalogService,
    PromptContentPolicy,
    PromptPromotionCoordinator,
    PromptRenderer,
    PromptSelectionPolicy,
    PromptVariantGuidanceService,
    RenderAnalyticsService,
    RenderGuidanceService,
    ReviewCandidateService,
    ReviewHistoryService,
    ReviewService,
    RuntimeConfigurationSnapshot,
    RuntimeDiagnosticsService,
    ScopeFacetService,
    WorkflowCompiler,
    WorkflowDefaultsService,
    WorkspacePreferencesService,
)
from comfyreview.observability import (
    RequestTracingMiddleware,
    configure_logging,
)
from comfyreview.providers import (
    CanonicalOutputImageCatalog,
    LocalCurationFileManager,
    LocalGenerationOutputRecoverySource,
    LocalGenerationOutputSource,
    NativeComfyUiProvider,
    OutputFileUrlMapper,
    PngHeaderDimensionReader,
    UrlLibJsonTransport,
    UuidGenerationIdentitySource,
    UuidPromptIdentitySource,
)
from comfyreview.repositories.filesystem import (
    JsonComfyUiCapabilityCache,
    JsonWorkflowBlueprintRepository,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteAnalyticsCoverageRepository,
    SqliteAnalyticsReportRepository,
    SqliteAnalyticsRepository,
    SqliteArenaRepository,
    SqliteCatalogEvidenceRepository,
    SqliteCompositionAnalyticsRepository,
    SqliteCurationRepository,
    SqliteGenerationOutputRepository,
    SqliteGenerationQueryRepository,
    SqliteGenerationRepository,
    SqliteGeneratorStateRepository,
    SqliteImageContentLevelRepository,
    SqliteImageContextRepository,
    SqliteImageFileRepository,
    SqliteImageGeneratorHandoffRepository,
    SqliteImageGeometryRepository,
    SqliteLoraCatalogRepository,
    SqliteOutputImageRepository,
    SqlitePlaygroundEvidenceRepository,
    SqlitePromptCatalogRepository,
    SqlitePromptPromotionRepository,
    SqlitePromptVariantEvidenceRepository,
    SqliteRenderAnalyticsRepository,
    SqliteRenderEvidenceRepository,
    SqliteReviewCandidateRepository,
    SqliteReviewHistoryRepository,
    SqliteReviewRepository,
    SqliteScopeFacetRepository,
    SqliteWorkspacePreferencesRepository,
)
from comfyreview.repositories.sqlite.canonical_schema import SCHEMA_VERSION
from comfyreview.revalidating_static_files import RevalidatingStaticFiles
from comfyreview.settings import Settings, load_settings
from routers.api_v2_router import router as api_v2_router
from routers.arena_router import router as arena_router
from routers.index_router import router as index_router
from routers.playground import router as playground_router
from routers.settings_router import router as settings_router
from routers.stats_router import router as stats_router
from routers.top_router import router as top_router
from services.analytics_page_service import AnalyticsPageService
from services.output_file_service import OutputFileService
from services.playground_discovery_service import PlaygroundDiscoveryService
from services.playground_label_service import PromptLabelService
from services.playground_render_guidance_service import (
    PlaygroundRenderGuidanceService,
)
from services.prompt_catalog_view_service import PromptCatalogViewService


@dataclass(frozen=True)
class ApplicationContainer:
    """Own configured application resources and their lifecycle ports."""

    settings: Settings
    canonical_schema: CanonicalSchemaLifecycle
    output_images: OutputImageCatalog
    file_urls: OutputFileUrlMapper
    image_contexts: ImageContextQueryService
    image_generator_handoffs: ImageGeneratorHandoffService
    scope_facets: ScopeFacetService
    review_candidates: ReviewCandidateService
    image_responses: ImageResponseMapper
    analytics_service: AnalyticsService
    analytics_reports: AnalyticsReportService
    analytics_pages: AnalyticsPageService
    analytics_coverage: AnalyticsCoverageService
    render_guidance: RenderGuidanceService
    playground_render_guidance: PlaygroundRenderGuidanceService
    playground_discovery: PlaygroundDiscoveryService
    playground_generator_settings: GeneratorStateService
    generation_service: GenerationService
    generation_worker: GenerationLifecycleWorker
    generation_queries: GenerationQueryService
    generation_reconciliation: GenerationReconciliationService
    prompt_catalog_service: PromptCatalogService
    prompt_variant_guidance: PromptVariantGuidanceService
    prompt_promotions: PromptPromotionCoordinator
    catalog_evidence: CatalogEvidenceService
    prompt_renderer: PromptRenderer
    prompt_catalog_views: PromptCatalogViewService
    prompt_labels: PromptLabelService
    playground_service: PlaygroundService
    playground_submission_service: PlaygroundSubmissionService
    playground_generation_sweeps: PlaygroundGenerationSweepPolicy
    playground_evidence: PlaygroundEvidenceService
    workflow_defaults: WorkflowDefaultsService
    review_service: ReviewService
    review_history: ReviewHistoryService
    arena_service: ArenaService
    curation_service: CurationService
    workspace_preferences: WorkspacePreferencesService
    runtime_diagnostics: RuntimeDiagnosticsService
    lora_catalog: LoraCatalogService
    lora_drafts: LoraDraftSelectionService
    lora_triggers: LoraTriggerValidationService
    image_content_levels: ImageContentLevelService


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
    lora_catalog = LoraCatalogService(
        SqliteLoraCatalogRepository(configured.canonical_database_path)
    )
    lora_content = LoraSelectionContentPolicy(lora_catalog)
    lora_triggers = LoraTriggerValidationService(lora_catalog)
    preferences_repository = SqliteWorkspacePreferencesRepository(
        configured.canonical_database_path
    )
    image_contexts = ImageContextQueryService(
        SqliteImageContextRepository(configured.canonical_database_path),
        draft_overrides,
    )
    prompt_variant_guidance = PromptVariantGuidanceService(
        SqlitePromptVariantEvidenceRepository(
            configured.canonical_database_path
        )
    )
    prompt_promotions = PromptPromotionCoordinator(
        guidance=prompt_variant_guidance,
        repository=SqlitePromptPromotionRepository(
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
        prompt_promotions=prompt_promotions,
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
    render_analytics = RenderAnalyticsService(
        SqliteRenderAnalyticsRepository(configured.canonical_database_path)
    )
    render_guidance = RenderGuidanceService(
        SqliteRenderEvidenceRepository(configured.canonical_database_path)
    )
    analytics_coverage = AnalyticsCoverageService(
        repository=SqliteAnalyticsCoverageRepository(
            configured.canonical_database_path
        ),
        render_guidance=render_guidance,
    )
    composition_analytics = CompositionAnalyticsService(
        SqliteCompositionAnalyticsRepository(
            configured.canonical_database_path
        )
    )
    comfyui_provider = NativeComfyUiProvider(
        UrlLibJsonTransport(configured.comfyui_base_url)
    )
    capability_cache = JsonComfyUiCapabilityCache(
        configured.data_directory / "ui_state" / "comfy_discovery_cache.json"
    )
    blueprints = JsonWorkflowBlueprintRepository(
        configured.workflows_directory
    )
    image_geometry = ImageGeometryProjectionService(
        SqliteImageGeometryRepository(configured.canonical_database_path),
        PngHeaderDimensionReader(configured.output_root),
    )
    generation_repository = SqliteGenerationRepository(
        configured.canonical_database_path
    )
    generation_output_repository = SqliteGenerationOutputRepository(
        configured.canonical_database_path
    )
    generation_output_collector = GenerationOutputCollector(
        comfyui=comfyui_provider,
        source=LocalGenerationOutputSource(configured.output_root),
        repository=generation_output_repository,
        image_geometry=image_geometry,
    )
    generation_service = GenerationService(
        blueprints=blueprints,
        compiler=WorkflowCompiler(),
        generations=generation_repository,
        comfyui=comfyui_provider,
        outputs=generation_output_collector,
        identities=UuidGenerationIdentitySource(),
        lora_content=lora_content,
        lora_triggers=lora_triggers,
        lora_graph_policy=CompiledLoraGraphPolicy(),
    )
    generation_reconciliation = GenerationReconciliationService(
        generations=generation_repository,
        comfyui=comfyui_provider,
        outputs=generation_output_collector,
        recovery=GenerationOutputRecoveryService(
            source=LocalGenerationOutputRecoverySource(configured.output_root),
            repository=generation_output_repository,
            collector=generation_output_collector,
        ),
    )
    generation_worker = GenerationLifecycleWorker(
        GenerationLifecycleCoordinator(
            generations=generation_repository,
            observer=generation_service,
        )
    )
    playground_discovery = PlaygroundDiscoveryService(
        comfyui_provider,
        capability_cache,
    )
    return ApplicationContainer(
        settings=configured,
        canonical_schema=CanonicalSchemaManager(
            configured.canonical_database_path
        ),
        output_images=output_images,
        file_urls=file_urls,
        image_contexts=image_contexts,
        image_generator_handoffs=ImageGeneratorHandoffService(
            images=image_contexts,
            repository=SqliteImageGeneratorHandoffRepository(
                configured.canonical_database_path
            ),
            capabilities=comfyui_provider,
        ),
        scope_facets=ScopeFacetService(
            SqliteScopeFacetRepository(configured.canonical_database_path)
        ),
        review_candidates=ReviewCandidateService(
            SqliteReviewCandidateRepository(
                configured.canonical_database_path
            ),
            draft_overrides,
            preferences_repository,
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
            render_analytics=render_analytics,
            composition_analytics=composition_analytics,
            image_url=file_urls.existing_url,
        ),
        analytics_coverage=analytics_coverage,
        render_guidance=render_guidance,
        playground_discovery=playground_discovery,
        playground_render_guidance=PlaygroundRenderGuidanceService(
            guidance=render_guidance,
            discovery=playground_discovery,
        ),
        playground_generator_settings=GeneratorStateService(
            SqliteGeneratorStateRepository(configured.canonical_database_path)
        ),
        generation_service=generation_service,
        generation_worker=generation_worker,
        generation_queries=GenerationQueryService(
            SqliteGenerationQueryRepository(configured.canonical_database_path)
        ),
        generation_reconciliation=generation_reconciliation,
        prompt_catalog_service=prompt_catalog_service,
        prompt_variant_guidance=prompt_variant_guidance,
        prompt_promotions=prompt_promotions,
        catalog_evidence=CatalogEvidenceService(
            SqliteCatalogEvidenceRepository(configured.canonical_database_path)
        ),
        prompt_renderer=prompt_renderer,
        prompt_catalog_views=PromptCatalogViewService(prompt_catalog_service),
        prompt_labels=PromptLabelService(prompt_catalog_service),
        playground_service=PlaygroundService(
            catalog=prompt_catalog_service,
            selection_policy=PromptSelectionPolicy(),
            renderer=prompt_renderer,
            preferences=preferences_repository,
            content_policy=PromptContentPolicy(),
        ),
        playground_submission_service=PlaygroundSubmissionService(
            generation=generation_service,
            policy=PlaygroundGenerationPolicy(
                blueprint_uid="default-character",
                blueprint_version=4,
                expected_output_roles=("primary",),
            ),
        ),
        playground_generation_sweeps=PlaygroundGenerationSweepPolicy(),
        playground_evidence=PlaygroundEvidenceService(
            SqlitePlaygroundEvidenceRepository(
                configured.canonical_database_path
            )
        ),
        workflow_defaults=WorkflowDefaultsService(blueprints),
        review_service=review_service,
        review_history=ReviewHistoryService(
            SqliteReviewHistoryRepository(configured.canonical_database_path)
        ),
        arena_service=ArenaService(
            images=image_contexts,
            repository=SqliteArenaRepository(
                configured.canonical_database_path
            ),
            prompt_promotions=prompt_promotions,
        ),
        curation_service=CurationService(
            repository=SqliteCurationRepository(
                configured.canonical_database_path
            ),
            files=LocalCurationFileManager(configured.output_root),
            allowed_set_keys=configured.curation_set_keys,
        ),
        workspace_preferences=WorkspacePreferencesService(
            preferences_repository,
            curation_set_keys=configured.curation_set_keys,
        ),
        runtime_diagnostics=RuntimeDiagnosticsService(
            RuntimeConfigurationSnapshot(
                comfyui_base_url=configured.comfyui_base_url,
                output_root=str(configured.output_root),
                workflows_directory=str(configured.workflows_directory),
                canonical_database_path=str(
                    configured.canonical_database_path
                ),
                schema_version=SCHEMA_VERSION,
                runtime_mode="canonical",
                environment_variables=(
                    "COMFYREVIEW_COMFYUI_BASE_URL",
                    "COMFYREVIEW_OUTPUT_ROOT",
                    "COMFYREVIEW_WORKFLOWS_DIR",
                    "COMFYREVIEW_DATABASE",
                ),
            ),
            comfyui_provider,
            capability_cache,
        ),
        lora_catalog=lora_catalog,
        lora_drafts=LoraDraftSelectionService(
            lora_catalog, preferences_repository
        ),
        lora_triggers=lora_triggers,
        image_content_levels=ImageContentLevelService(
            SqliteImageContentLevelRepository(
                configured.canonical_database_path
            )
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
        resources.generation_worker.start()
        try:
            yield
        finally:
            resources.generation_worker.stop()

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
        RevalidatingStaticFiles(
            directory=str(Path(resources.settings.base_directory) / "static"),
            check_dir=False,
        ),
        name="static",
    )
    application.include_router(index_router)
    application.include_router(api_v2_router)
    application.include_router(settings_router)
    application.include_router(top_router)
    application.include_router(arena_router)
    application.include_router(stats_router)
    application.include_router(playground_router)
    return application
