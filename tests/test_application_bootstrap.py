"""Tests for the FastAPI composition root and owned lifespan."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path
from typing import cast

import pytest
from fastapi.testclient import TestClient

from comfyreview.application import (
    AnalyticsService,
    ArenaService,
    CanonicalSchemaReport,
    CurationImage,
    CurationService,
    GenerationService,
    LegacySchemaReport,
    OutputImageReadModel,
    PlaygroundService,
    PromptCatalogService,
    RankingService,
    ReviewResult,
    ReviewService,
    SubmitReviewCommand,
)
from comfyreview.bootstrap import (
    ApplicationContainer,
    build_application_container,
    create_app,
)
from comfyreview.providers import CanonicalOutputImageCatalog
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.settings import Settings, load_settings
from services.analytics_page_service import AnalyticsPageService
from services.playground_hub_service import PlaygroundHubService


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


class _RecordingSchemaLifecycle:
    def __init__(self, settings: Settings, events: list[str]) -> None:
        self._settings = settings
        self._events = events

    def prepare_startup(self) -> LegacySchemaReport:
        assert self._settings.output_root.is_dir()
        assert self._settings.data_directory.is_dir()
        self._events.append("schema")
        return LegacySchemaReport()

    def validate(
        self,
        database_names: Collection[str] | None = None,
    ) -> LegacySchemaReport:
        del database_names
        return LegacySchemaReport()

    def upgrade(
        self,
        database_names: Collection[str] | None = None,
        backup_directory: Path | None = None,
    ) -> LegacySchemaReport:
        del database_names, backup_directory
        return LegacySchemaReport()


class _EmptyOutputImageCatalog:
    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        return ()


class _RecordingReviewService:
    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        del command
        return ReviewResult(review_id=1, run=1, deleted=False)


class _EmptyRankingRepository:
    def list_ranked_images(self):
        return ()


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
    rankings = RankingService(_EmptyRankingRepository())
    return ApplicationContainer(
        settings=settings,
        canonical_schema=_RecordingCanonicalSchema(settings, events),
        schema_lifecycle=_RecordingSchemaLifecycle(settings, events),
        output_images=_EmptyOutputImageCatalog(),
        analytics_service=cast(AnalyticsService, object()),
        analytics_pages=cast(AnalyticsPageService, object()),
        playground_hub=cast(PlaygroundHubService, object()),
        generation_service=cast(GenerationService, object()),
        prompt_catalog_service=cast(PromptCatalogService, object()),
        playground_service=cast(PlaygroundService, object()),
        review_service=cast(ReviewService, _RecordingReviewService()),
        ranking_service=rankings,
        arena_service=ArenaService(
            rankings=rankings,
            repository=_EmptyArenaRepository(),
        ),
        curation_service=CurationService(
            repository=_EmptyCurationRepository(),
            files=_EmptyCurationFiles(),
            allowed_set_keys=settings.curation_set_keys,
        ),
    )


def test_lifespan_prepares_canonical_and_required_legacy_schemas(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    container = _container(tmp_path, events)
    application = create_app(container)

    assert application.state.container is container
    assert not container.settings.output_root.exists()
    assert not container.settings.data_directory.exists()

    with TestClient(application):
        assert events == ["canonical", "schema"]
        assert container.settings.trash_root.is_dir()
        assert container.settings.lora_export_root.is_dir()
        assert container.settings.workflows_directory.is_dir()
        assert container.settings.comfyui_checkpoints_directory.is_dir()

    assert events == ["canonical", "schema"]


def test_lifespan_preserves_schema_order_when_application_body_fails(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    application = create_app(_container(tmp_path, events))

    with pytest.raises(RuntimeError, match="application failed"):
        with TestClient(application):
            raise RuntimeError("application failed")

    assert events == ["canonical", "schema"]


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
    assert isinstance(container.analytics_service, AnalyticsService)
    assert isinstance(container.analytics_pages, AnalyticsPageService)
    assert isinstance(container.playground_hub, PlaygroundHubService)
    assert isinstance(container.generation_service, GenerationService)
    assert isinstance(container.review_service, ReviewService)
    assert isinstance(container.prompt_catalog_service, PromptCatalogService)
    assert isinstance(container.playground_service, PlaygroundService)
    assert isinstance(container.ranking_service, RankingService)
    assert isinstance(container.arena_service, ArenaService)
    assert isinstance(container.curation_service, CurationService)
    assert isinstance(container.canonical_schema, CanonicalSchemaManager)
