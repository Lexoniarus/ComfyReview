"""Tests for the FastAPI composition root and owned lifespan."""

from __future__ import annotations

from collections.abc import Collection
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from comfyreview.application import LegacySchemaReport
from comfyreview.bootstrap import ApplicationContainer, create_app
from comfyreview.settings import Settings, load_settings


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


class _RecordingWorker:
    def __init__(self, events: list[str]) -> None:
        self._events = events

    def start(self) -> None:
        self._events.append("start")

    def stop(self, timeout_seconds: float) -> None:
        self._events.append(f"stop:{timeout_seconds:g}")


def _container(tmp_path: Path, events: list[str]) -> ApplicationContainer:
    settings = load_settings(base_directory=tmp_path, environ={})
    return ApplicationContainer(
        settings=settings,
        schema_lifecycle=_RecordingSchemaLifecycle(settings, events),
        worker=_RecordingWorker(events),
    )


def test_lifespan_prepares_schema_then_owns_worker(tmp_path: Path) -> None:
    events: list[str] = []
    container = _container(tmp_path, events)
    application = create_app(container)

    assert not container.settings.output_root.exists()
    assert not container.settings.data_directory.exists()

    with TestClient(application):
        assert events == ["schema", "start"]
        assert container.settings.trash_root.is_dir()
        assert container.settings.lora_export_root.is_dir()
        assert container.settings.workflows_directory.is_dir()
        assert container.settings.comfyui_checkpoints_directory.is_dir()

    assert events == ["schema", "start", "stop:30"]


def test_lifespan_stops_worker_when_application_body_fails(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    application = create_app(_container(tmp_path, events))

    with pytest.raises(RuntimeError, match="application failed"):
        with TestClient(application):
            raise RuntimeError("application failed")

    assert events == ["schema", "start", "stop:30"]


def test_entry_points_and_route_contract_remain_compatible() -> None:
    from app import app as root_app
    from main import app as main_app

    assert main_app is root_app
