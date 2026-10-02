"""Tests for the FastAPI composition root and owned lifespan."""

from __future__ import annotations

from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    AnalyticsReportService,
    AnalyticsService,
    ArenaService,
    CanonicalSchemaReport,
    CurationImage,
    CurationService,
    GenerationQueryService,
    GenerationReconciliationService,
    GenerationService,
    ImageContextQueryService,
    OutputImageReadModel,
    PlaygroundGenerationSweepPolicy,
    PlaygroundService,
    PlaygroundSubmissionService,
    PromptCatalogService,
    ReviewCandidateService,
    ReviewHistoryService,
    ReviewResult,
    ReviewService,
    ScopeFacetService,
    SubmitReviewCommand,
    WorkflowDefaultsService,
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
from services.playground_label_service import PromptLabelService
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
    def list_played_directions(self, image_uids):
        del image_uids
        return frozenset()

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


def _container(tmp_path: Path, events: list[str]) -> ApplicationContainer:
    settings = load_settings(base_directory=tmp_path, environ={})
    return ApplicationContainer(
        settings=settings,
        canonical_schema=_RecordingCanonicalSchema(settings, events),
        output_images=_EmptyOutputImageCatalog(),
        file_urls=OutputFileUrlMapper(settings.output_root),
        image_contexts=cast(ImageContextQueryService, object()),
        scope_facets=cast(ScopeFacetService, object()),
        review_candidates=cast(ReviewCandidateService, object()),
        image_responses=cast(ImageResponseMapper, object()),
        analytics_service=cast(AnalyticsService, object()),
        analytics_reports=cast(AnalyticsReportService, object()),
        analytics_pages=cast(AnalyticsPageService, object()),
        playground_discovery=cast(PlaygroundDiscoveryService, object()),
        playground_ui_state=PlaygroundGeneratorStateRepository(
            head_path=tmp_path / "head.json",
            preview_path=tmp_path / "preview.json",
        ),
        generation_service=cast(GenerationService, object()),
        generation_queries=cast(GenerationQueryService, object()),
        generation_reconciliation=cast(
            GenerationReconciliationService,
            object(),
        ),
        prompt_catalog_service=cast(PromptCatalogService, object()),
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
        assert events == ["canonical"]
        assert container.settings.trash_root.is_dir()
        assert container.settings.lora_export_root.is_dir()
        assert container.settings.workflows_directory.is_dir()
        assert container.settings.comfyui_checkpoints_directory.is_dir()

    assert events == ["canonical"]


def test_lifespan_preserves_schema_order_when_application_body_fails(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    application = create_app(_container(tmp_path, events))

    with pytest.raises(RuntimeError, match="application failed"):
        with TestClient(application):
            raise RuntimeError("application failed")

    assert events == ["canonical"]


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
    assert isinstance(
        container.generation_reconciliation,
        GenerationReconciliationService,
    )
    assert isinstance(container.review_service, ReviewService)
    assert isinstance(container.prompt_catalog_service, PromptCatalogService)
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
