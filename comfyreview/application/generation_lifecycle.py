"""Owned runtime coordination for asynchronous native generations."""

from __future__ import annotations

import logging
from threading import Event, Lock, Thread
from typing import Protocol

from comfyreview.application.generation import (
    GenerationRecord,
    GenerationSubmission,
)


class GenerationObserver(Protocol):
    """Observe one already-submitted generation without resubmitting it."""

    def observe(self, generation_uid: str) -> GenerationSubmission:
        """Return the state observed during one bounded provider request."""
        ...


class ActiveGenerationRepository(Protocol):
    """Expose only lifecycle operations needed by the background owner."""

    def list_active(self, limit: int) -> tuple[GenerationRecord, ...]: ...

    def mark_failed(
        self, generation_uid: str, reason: str
    ) -> GenerationRecord: ...

    def mark_reconciliation_required(
        self,
        generation_uid: str,
        prompt_id: str | None,
        reason: str,
    ) -> GenerationRecord: ...


class GenerationLifecyclePass(Protocol):
    """Run one bounded background lifecycle pass."""

    def run_once(self) -> tuple[GenerationSubmission, ...]: ...


class GenerationLifecycleCoordinator:
    """Recover incomplete state and observe a bounded active generation set."""

    def __init__(
        self,
        *,
        generations: ActiveGenerationRepository,
        observer: GenerationObserver,
        batch_limit: int = 50,
    ) -> None:
        self._generations = generations
        self._observer = observer
        self._batch_limit = max(1, int(batch_limit))
        self._logger = logging.getLogger("comfyreview.generation")

    def run_once(self) -> tuple[GenerationSubmission, ...]:
        """Process one bounded pass without holding external transactions."""
        results: list[GenerationSubmission] = []
        for record in self._generations.list_active(self._batch_limit):
            try:
                result = self._process(record)
            except Exception as error:  # keep unrelated jobs observable
                self._logger.exception(
                    "generation.lifecycle_observation_failed",
                    extra={
                        "generation_id": record.generation_uid,
                        "prompt_id": record.prompt_id,
                        "error_type": type(error).__name__,
                    },
                )
                continue
            if result.status != record.status:
                self._logger.info(
                    "generation.lifecycle_transition_observed",
                    extra={
                        "generation_id": result.generation_uid,
                        "prompt_id": result.prompt_id,
                        "previous_status": record.status,
                        "status": result.status,
                    },
                )
            results.append(result)
        return tuple(results)

    def _process(self, record: GenerationRecord) -> GenerationSubmission:
        if record.status == "prepared":
            updated = self._generations.mark_failed(
                record.generation_uid,
                "startup_incomplete_preparation",
            )
            return self._submission(updated)
        if record.status == "submitting":
            updated = self._generations.mark_reconciliation_required(
                record.generation_uid,
                record.prompt_id,
                "startup_ambiguous_submission",
            )
            return self._submission(updated)
        return self._observer.observe(record.generation_uid)

    @staticmethod
    def _submission(record: GenerationRecord) -> GenerationSubmission:
        return GenerationSubmission(
            generation_uid=record.generation_uid,
            status=record.status,
            prompt_id=record.prompt_id,
        )


class GenerationLifecycleWorker:
    """Own one background thread polling the lifecycle coordinator."""

    def __init__(
        self,
        coordinator: GenerationLifecyclePass,
        *,
        poll_interval_seconds: float = 2.0,
    ) -> None:
        self._coordinator = coordinator
        self._poll_interval_seconds = max(0.05, float(poll_interval_seconds))
        self._stop_event = Event()
        self._lock = Lock()
        self._thread: Thread | None = None
        self._logger = logging.getLogger("comfyreview.generation")

    def start(self) -> None:
        """Start exactly one owned polling thread."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return
            self._stop_event.clear()
            self._thread = Thread(
                target=self._run,
                name="comfyreview-generation-lifecycle",
                daemon=True,
            )
            self._thread.start()

    def stop(self, *, timeout_seconds: float = 35.0) -> bool:
        """Request shutdown and report whether the worker stopped in time."""
        with self._lock:
            thread = self._thread
            self._stop_event.set()
        if thread is None:
            return True
        thread.join(timeout=max(0.0, float(timeout_seconds)))
        stopped = not thread.is_alive()
        if stopped:
            with self._lock:
                if self._thread is thread:
                    self._thread = None
        else:
            self._logger.warning(
                "generation.lifecycle_shutdown_timeout",
                extra={"error_type": "GenerationLifecycleShutdownTimeout"},
            )
        return stopped

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._coordinator.run_once()
            except Exception as error:  # keep the owned resource alive
                self._logger.exception(
                    "generation.lifecycle_pass_failed",
                    extra={"error_type": type(error).__name__},
                )
            self._stop_event.wait(self._poll_interval_seconds)
