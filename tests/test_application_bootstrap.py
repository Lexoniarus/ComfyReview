"""Tests for the FastAPI composition root and owned lifespan."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    AnalyticsCoverageService,
    AnalyticsReportService,
    AnalyticsService,
    ArenaService,
    CanonicalSchemaReport,
    CatalogEvidenceService,
    CurationImage,
    CurationService,
    GenerationLifecycleWorker,
    GenerationQueryService,
    GenerationReconciliationService,
    GenerationService,
    ImageContentLevelService,
    ImageContextQueryService,
    ImageGeneratorHandoffService,
    LoraCatalogService,
    LoraDraftSelectionService,
    OutputImageReadModel,
    PlaygroundEvidenceService,
    PlaygroundGenerationSweepPolicy,
    PlaygroundService,
    PlaygroundSubmissionService,
    PromptCatalogService,
    PromptRenderer,
    RenderGuidanceService,
    ReviewCandidateService,
    ReviewHistoryService,
    ReviewResult,
    ReviewService,
    RuntimeDiagnosticsService,
    ScopeFacetService,
    SubmitReviewCommand,
    WorkflowDefaultsService,
    WorkspacePreferencesService,
)
from comfyreview.bootstrap import (
    ApplicationContainer,
    build_application_container,
    create_app,
)
from comfyreview.providers import (
    CanonicalOutputImageCatalog,
    OutputFileUrlMapper,
)
from comfyreview.repositories.filesystem import (
    PlaygroundGeneratorStateRepository,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.settings import Settings, load_settings
from services.analytics_page_service import AnalyticsPageService
from services.playground_discovery_service import PlaygroundDiscoveryService
from services.playground_generator_ui.settings_state import (
    PlaygroundGeneratorSettingsService,
)
from services.playground_label_service import PromptLabelService
from services.playground_render_guidance_service import (
    PlaygroundRenderGuidanceService,
)
from services.prompt_catalog_view_service import PromptCatalogViewService


class _RecordingCanonicalSchema:
    def __init__(self, settings: Settings, events: list[str]) -> None:
        self._settings = settings
        self._events = events

    def prepare_startup(self) -> CanonicalSchemaReport:
        assert self._settings.data_directory.is_dir()
        self._events.append("canonical")
        return CanonicalSchemaReport(initialized=True, schema_version=1)

    def validate(self) -> CanonicalSchemaReport:
        return CanonicalSchemaReport(schema_version=1)


class _EmptyOutputImageCatalog:
    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        return ()


class _RecordingReviewService:
    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        del command
        return ReviewResult(review_id=1, run=1, deleted=False)


class _EmptyArenaRepository:
    def pairing_history(self, image_uids):
        del image_uids
        from comfyreview.application import ArenaPairingHistory

        return ArenaPairingHistory(frozenset(), ())

    def get_competitors(self, left_image_uid, right_image_uid):
        raise AssertionError((left_image_uid, right_image_uid))

    def save_decision(self, decision):
        raise AssertionError(decision)


class _EmptyCurationRepository:
    def get_live_image(self, image_uid):
        return CurationImage(image_uid, Path("image.png"), None)

    def assign(self, assignment):
        raise AssertionError(assignment)


class _EmptyCurationFiles:
    def stage_move(self, image, set_key):
        raise AssertionError((image, set_key))


class _RecordingGenerationWorker:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def start(self) -> None:
        self._events.append("worker-start")

    def stop(self) -> bool:
        self._events.append("worker-stop")
        return True


def _container(tmp_path: Path, events: list[str]) -> ApplicationContainer:
    settings = load_settings(base_directory=tmp_path, environ={})
    playground_ui_state = PlaygroundGeneratorStateRepository(
        head_path=tmp_path / "head.json",
        preview_path=tmp_path / "preview.json",
    )
    return ApplicationContainer(
        settings=settings,
        canonical_schema=_RecordingCanonicalSchema(settings, events),
        output_images=_EmptyOutputImageCatalog(),
        file_urls=OutputFileUrlMapper(settings.output_root),
        image_contexts=cast(ImageContextQueryService, object()),
        image_generator_handoffs=cast(ImageGeneratorHandoffService, object()),
        scope_facets=cast(ScopeFacetService, object()),
        review_candidates=cast(ReviewCandidateService, object()),
        image_responses=cast(ImageResponseMapper, object()),
        analytics_service=cast(AnalyticsService, object()),
        analytics_reports=cast(AnalyticsReportService, object()),
        analytics_pages=cast(AnalyticsPageService, object()),
        analytics_coverage=cast(AnalyticsCoverageService, object()),
        render_guidance=cast(RenderGuidanceService, object()),
        playground_render_guidance=cast(
            PlaygroundRenderGuidanceService, object()
        ),
        playground_discovery=cast(PlaygroundDiscoveryService, object()),
        playground_ui_state=playground_ui_state,
        playground_generator_settings=PlaygroundGeneratorSettingsService(
            playground_ui_state
        ),
        generation_service=cast(GenerationService, object()),
        generation_worker=cast(
            GenerationLifecycleWorker,
            _RecordingGenerationWorker(events),
        ),
        generation_queries=cast(GenerationQueryService, object()),
        generation_reconciliation=cast(
            GenerationReconciliationService,
            object(),
        ),
        prompt_catalog_service=cast(PromptCatalogService, object()),
        catalog_evidence=cast(CatalogEvidenceService, object()),
        prompt_renderer=PromptRenderer(),
        prompt_catalog_views=cast(PromptCatalogViewService, object()),
        prompt_labels=cast(PromptLabelService, object()),
        playground_service=cast(PlaygroundService, object()),
        playground_submission_service=cast(
            PlaygroundSubmissionService,
            object(),
        ),
        playground_generation_sweeps=cast(
            PlaygroundGenerationSweepPolicy,
            object(),
        ),
        playground_evidence=cast(PlaygroundEvidenceService, object()),
        workflow_defaults=cast(WorkflowDefaultsService, object()),
        review_service=cast(ReviewService, _RecordingReviewService()),
        review_history=cast(ReviewHistoryService, object()),
        arena_service=ArenaService(
            images=cast(ImageContextQueryService, object()),
            repository=_EmptyArenaRepository(),
        ),
        curation_service=CurationService(
            repository=_EmptyCurationRepository(),
            files=_EmptyCurationFiles(),
            allowed_set_keys=settings.curation_set_keys,
        ),
        workspace_preferences=cast(WorkspacePreferencesService, object()),
        runtime_diagnostics=cast(RuntimeDiagnosticsService, object()),
        lora_catalog=cast(LoraCatalogService, object()),
        lora_drafts=cast(LoraDraftSelectionService, object()),
        image_content_levels=cast(ImageContentLevelService, object()),
    )


def test_lifespan_prepares_only_the_canonical_runtime_schema(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    container = _container(tmp_path, events)
    application = create_app(container)

    assert application.state.container is container
    assert not container.settings.output_root.exists()
    assert not container.settings.data_directory.exists()

    with TestClient(application):
        assert events == ["canonical", "worker-start"]
        assert container.settings.trash_root.is_dir()
        assert container.settings.lora_export_root.is_dir()
        assert container.settings.workflows_directory.is_dir()
        assert container.settings.comfyui_checkpoints_directory.is_dir()

    assert events == ["canonical", "worker-start", "worker-stop"]


def test_lifespan_preserves_schema_order_when_application_body_fails(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    application = create_app(_container(tmp_path, events))

    with pytest.raises(RuntimeError, match="application failed"):
        with TestClient(application):
            raise RuntimeError("application failed")

    assert events == ["canonical", "worker-start", "worker-stop"]


def test_static_modules_require_browser_revalidation(tmp_path: Path) -> None:
    static_directory = tmp_path / "static"
    static_directory.mkdir()
    (static_directory / "module.js").write_text(
        "export const ready = true;\n", encoding="utf-8"
    )
    application = create_app(_container(tmp_path, []))

    with TestClient(application) as client:
        response = client.get("/static/module.js")

    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-cache, must-revalidate"


def test_entry_points_and_route_contract_remain_compatible() -> None:
    from app import app as root_app
    from main import app as main_app

    assert main_app is root_app


def test_default_container_wires_canonical_review_runtime(
    tmp_path: Path,
) -> None:
    settings = load_settings(base_directory=tmp_path, environ={})

    container = build_application_container(settings)

    assert isinstance(
        container.output_images,
        CanonicalOutputImageCatalog,
    )
    assert isinstance(container.file_urls, OutputFileUrlMapper)
    assert isinstance(container.workflow_defaults, WorkflowDefaultsService)
    assert isinstance(container.analytics_service, AnalyticsService)
    assert isinstance(container.analytics_reports, AnalyticsReportService)
    assert isinstance(container.analytics_pages, AnalyticsPageService)
    assert isinstance(
        container.playground_discovery,
        PlaygroundDiscoveryService,
    )
    assert isinstance(
        container.playground_ui_state,
        PlaygroundGeneratorStateRepository,
    )
    assert isinstance(container.generation_service, GenerationService)
    assert isinstance(container.generation_worker, GenerationLifecycleWorker)
    assert isinstance(
        container.generation_reconciliation,
        GenerationReconciliationService,
    )
    assert isinstance(container.review_service, ReviewService)
    assert isinstance(container.prompt_catalog_service, PromptCatalogService)
    assert isinstance(container.catalog_evidence, CatalogEvidenceService)
    assert isinstance(container.prompt_catalog_views, PromptCatalogViewService)
    assert isinstance(container.prompt_labels, PromptLabelService)
    assert isinstance(container.playground_service, PlaygroundService)
    assert isinstance(
        container.playground_submission_service,
        PlaygroundSubmissionService,
    )
    assert isinstance(container.arena_service, ArenaService)
    assert isinstance(container.curation_service, CurationService)
    assert isinstance(container.canonical_schema, CanonicalSchemaManager)
