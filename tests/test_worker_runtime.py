"""Lifecycle tests for the owned legacy projection worker."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

import comfyreview.infrastructure.legacy_worker as worker_module
from comfyreview.infrastructure import (
    LegacyWorkerRuntime,
    WorkerShutdownTimeoutError,
)


def _runtime(
    tmp_path: Path,
    *,
    thread_factory: Callable[..., threading.Thread] = threading.Thread,
) -> LegacyWorkerRuntime:
    return LegacyWorkerRuntime(
        queue_database_path=tmp_path / "queue.sqlite3",
        state_database_path=tmp_path / "state.sqlite3",
        ratings_database_path=tmp_path / "ratings.sqlite3",
        prompt_tokens_database_path=tmp_path / "tokens.sqlite3",
        prompt_ratings_database_path=tmp_path / "prompt-ratings.sqlite3",
        combo_database_path=tmp_path / "combo.sqlite3",
        playground_database_path=tmp_path / "playground.sqlite3",
        images_database_path=tmp_path / "images.sqlite3",
        debounce_seconds=17,
        poll_seconds=0.25,
        thread_factory=thread_factory,
    )


def test_worker_runtime_starts_once_and_stops_with_injected_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    started = threading.Event()
    calls: list[dict[str, Any]] = []

    def worker_loop(**arguments: Any) -> None:
        calls.append(arguments)
        started.set()
        arguments["stop_event"].wait(1)

    monkeypatch.setattr(worker_module, "run_worker_loop", worker_loop)
    runtime = _runtime(tmp_path)

    runtime.start()
    assert started.wait(1)
    runtime.start()
    runtime.stop(1)

    assert len(calls) == 1
    assert calls[0]["queue_db_path"] == tmp_path / "queue.sqlite3"
    assert calls[0]["debounce_seconds"] == 17
    assert calls[0]["poll_seconds"] == 0.25
    assert calls[0]["stop_event"].is_set()


def test_worker_runtime_stop_before_start_is_safe(tmp_path: Path) -> None:
    _runtime(tmp_path).stop(0)


def test_worker_runtime_can_retry_after_thread_start_failure(
    tmp_path: Path,
) -> None:
    attempts = 0

    class StartControlledThread:
        def __init__(self) -> None:
            self.alive = False

        def start(self) -> None:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("start failed")
            self.alive = True

        def is_alive(self) -> bool:
            return self.alive

        def join(self, timeout: float | None = None) -> None:
            del timeout
            self.alive = False

    def thread_factory(**_arguments: Any) -> Any:
        return StartControlledThread()

    runtime = _runtime(tmp_path, thread_factory=thread_factory)

    with pytest.raises(RuntimeError, match="start failed"):
        runtime.start()
    runtime.start()
    runtime.stop(1)

    assert attempts == 2


def test_worker_runtime_reports_shutdown_timeout(tmp_path: Path) -> None:
    class StuckThread:
        def start(self) -> None:
            return None

        def is_alive(self) -> bool:
            return True

        def join(self, timeout: float | None = None) -> None:
            assert timeout == 0.5

    def thread_factory(**_arguments: Any) -> Any:
        return StuckThread()

    runtime = _runtime(tmp_path, thread_factory=thread_factory)
    runtime.start()

    with pytest.raises(WorkerShutdownTimeoutError, match="0.5 seconds"):
        runtime.stop(0.5)
