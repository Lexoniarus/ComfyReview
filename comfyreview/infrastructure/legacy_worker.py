"""Owned thread lifecycle for the legacy projection worker."""

from __future__ import annotations

import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from services.mv_worker_core.engine import run_worker_loop

ThreadFactory = Callable[..., threading.Thread]


class WorkerShutdownTimeoutError(RuntimeError):
    """Signal that the projection worker did not stop within its deadline."""


class LegacyWorkerRuntime:
    """Own one legacy projection-worker thread and its stop signal."""

    def __init__(
        self,
        *,
        queue_database_path: Path,
        state_database_path: Path,
        ratings_database_path: Path,
        prompt_tokens_database_path: Path,
        prompt_ratings_database_path: Path,
        combo_database_path: Path,
        playground_database_path: Path,
        images_database_path: Path,
        debounce_seconds: int,
        poll_seconds: float = 0.75,
        thread_factory: ThreadFactory = threading.Thread,
    ) -> None:
        self._worker_arguments: dict[str, Any] = {
            "queue_db_path": Path(queue_database_path),
            "state_db_path": Path(state_database_path),
            "ratings_db_path": Path(ratings_database_path),
            "prompt_tokens_db_path": Path(prompt_tokens_database_path),
            "prompt_ratings_db_path": Path(prompt_ratings_database_path),
            "combo_db_path": Path(combo_database_path),
            "playground_db_path": Path(playground_database_path),
            "images_db_path": Path(images_database_path),
            "debounce_seconds": int(debounce_seconds),
            "poll_seconds": float(poll_seconds),
        }
        self._thread_factory = thread_factory
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._lifecycle_lock = threading.Lock()

    def start(self) -> None:
        """Start the worker once and keep ownership of its thread."""
        with self._lifecycle_lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            thread = self._thread_factory(
                target=run_worker_loop,
                kwargs={
                    **self._worker_arguments,
                    "stop_event": self._stop_event,
                },
                daemon=True,
                name="mv_worker",
            )
            self._thread = thread
            try:
                thread.start()
            except Exception:
                self._thread = None
                raise

    def stop(self, timeout_seconds: float) -> None:
        """Signal the worker and wait for its bounded orderly shutdown."""
        with self._lifecycle_lock:
            thread = self._thread
            if thread is None:
                return
            self._stop_event.set()
        thread.join(timeout=max(float(timeout_seconds), 0.0))
        if thread.is_alive():
            raise WorkerShutdownTimeoutError(
                "Projection worker did not stop within "
                f"{float(timeout_seconds):g} seconds"
            )
        with self._lifecycle_lock:
            if self._thread is thread:
                self._thread = None
