"""Characterization tests for the legacy bootstrap boundary."""

from __future__ import annotations

import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

from arena_store import ensure_schema as ensure_arena_schema
from prompt_store import db as open_prompt_database
from services import mv_worker
from services.observability import RequestTracingMiddleware
from stores.combo_prompts_store import init_combo_prompts_db
from stores.curation_store import init_curation_db
from stores.db_core import db as open_ratings_database
from stores.images_store import init_images_db
from stores.mv_jobs_store import ensure_schema as ensure_jobs_schema
from stores.mv_state_store import ensure_schema as ensure_state_schema
from stores.playground.connection import db as open_playground_database
from stores.prompt_ratings_store import init_prompt_ratings_db


def _table_columns(database_path: Path) -> dict[str, tuple[str, ...]]:
    connection = sqlite3.connect(database_path)
    try:
        table_names = [
            str(row[0])
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
                ORDER BY name
                """
            )
        ]
        return {
            table_name: tuple(
                str(row[1])
                for row in connection.execute(
                    f"PRAGMA table_info({table_name})"
                )
            )
            for table_name in table_names
        }
    finally:
        connection.close()


def test_root_app_keeps_public_routes_and_request_tracing() -> None:
    from app import app

    def collect_paths(routes: list[Any]) -> set[str]:
        paths: set[str] = set()
        for route in routes:
            path = getattr(route, "path", None)
            if path:
                paths.add(str(path))
            nested_router = getattr(route, "original_router", None)
            if nested_router is not None:
                paths.update(collect_paths(list(nested_router.routes)))
        return paths

    route_paths = collect_paths(list(app.routes))

    assert {
        "/",
        "/arena",
        "/arena_result",
        "/assign_set",
        "/rate",
        "/top_delete",
        "/top_pictures",
    } <= route_paths
    assert any(
        middleware.cls is RequestTracingMiddleware
        for middleware in app.user_middleware
    )


def test_worker_thread_receives_every_legacy_database_path(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    captured: dict[str, Any] = {}

    class FakeThread:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)
            self.started = False

        def start(self) -> None:
            self.started = True

    monkeypatch.setattr(mv_worker.threading, "Thread", FakeThread)
    names = (
        "queue_db_path",
        "state_db_path",
        "ratings_db_path",
        "prompt_tokens_db_path",
        "prompt_ratings_db_path",
        "combo_db_path",
        "playground_db_path",
        "images_db_path",
    )
    paths = {name: tmp_path / f"{name}.sqlite3" for name in names}

    thread = mv_worker.start_worker_thread(**paths)

    assert isinstance(thread, FakeThread)
    assert thread.started is True
    assert captured["target"] is mv_worker.run_worker_loop
    assert captured["kwargs"] == paths
    assert captured["daemon"] is True
    assert captured["name"] == "mv_worker"


def test_legacy_initializers_produce_the_current_schema_contract(
    tmp_path: Path,
) -> None:
    initializers: dict[str, Callable[[Path], None]] = {
        "arena": ensure_arena_schema,
        "combo": init_combo_prompts_db,
        "curation": init_curation_db,
        "images": init_images_db,
        "prompt_ratings": init_prompt_ratings_db,
    }

    def initialize_ratings(path: Path) -> None:
        open_ratings_database(path).close()

    def initialize_prompt_tokens(path: Path) -> None:
        open_prompt_database(path).close()

    def initialize_playground(path: Path) -> None:
        open_playground_database(path).close()

    initializers.update(
        {
            "ratings": initialize_ratings,
            "prompt_tokens": initialize_prompt_tokens,
            "playground": initialize_playground,
        }
    )

    expected_tables = {
        "arena": {"arena_matches"},
        "combo": {"combo_best_images", "combo_prompts"},
        "curation": {"curation"},
        "images": {"images"},
        "playground": {"playground_items"},
        "prompt_ratings": {"prompt_ratings"},
        "prompt_tokens": {"tokens"},
        "ratings": {"ratings"},
    }
    for name, initializer in initializers.items():
        database_path = tmp_path / f"{name}.sqlite3"
        initializer(database_path)
        assert set(_table_columns(database_path)) == expected_tables[name]

    queue_path = tmp_path / "mv_queue.sqlite3"
    ensure_jobs_schema(queue_path)
    ensure_state_schema(queue_path)
    assert set(_table_columns(queue_path)) == {"mv_jobs", "mv_state"}
