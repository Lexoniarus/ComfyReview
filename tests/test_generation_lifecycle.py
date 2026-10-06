"""Behavior tests for the owned asynchronous generation lifecycle."""

from __future__ import annotations

import logging
from threading import Event

from comfyreview.application import (
    GenerationLifecycleCoordinator,
    GenerationLifecycleWorker,
    GenerationRecord,
    GenerationSubmission,
)


class _Generations:
    def __init__(self, records: tuple[GenerationRecord, ...]) -> None:
        self.records = records
        self.requested_limits: list[int] = []
        self.transitions: list[tuple[str, str, str | None]] = []

    def list_active(self, limit: int) -> tuple[GenerationRecord, ...]:
        self.requested_limits.append(limit)
        return self.records[:limit]

    def mark_failed(
        self, generation_uid: str, reason: str
    ) -> GenerationRecord:
        self.transitions.append((generation_uid, "failed", reason))
        return GenerationRecord(generation_uid, "failed", None)

    def mark_reconciliation_required(
        self,
        generation_uid: str,
        prompt_id: str | None,
        reason: str,
    ) -> GenerationRecord:
        self.transitions.append(
            (generation_uid, "reconciliation_required", reason)
        )
        return GenerationRecord(
            generation_uid,
            "reconciliation_required",
            prompt_id,
        )


class _Observer:
    def __init__(self, failing_uid: str | None = None) -> None:
        self.failing_uid = failing_uid
        self.observed: list[str] = []

    def observe(self, generation_uid: str) -> GenerationSubmission:
        self.observed.append(generation_uid)
        if generation_uid == self.failing_uid:
            raise RuntimeError("provider unavailable")
        return GenerationSubmission(generation_uid, "running", "prompt-1")


class _SignallingCoordinator:
    def __init__(self) -> None:
        self.called = Event()
        self.calls = 0

    def run_once(self) -> tuple[GenerationSubmission, ...]:
        self.calls += 1
        self.called.set()
        return ()


class _FailingOnceCoordinator:
    def __init__(self) -> None:
        self.calls = 0
        self.recovered = Event()

    def run_once(self) -> tuple[GenerationSubmission, ...]:
        self.calls += 1
        if self.calls == 1:
            raise RuntimeError("one failed pass")
        self.recovered.set()
        return ()


class _BlockingCoordinator:
    def __init__(self) -> None:
        self.entered = Event()
        self.release = Event()

    def run_once(self) -> tuple[GenerationSubmission, ...]:
        self.entered.set()
        self.release.wait(timeout=2)
        return ()


def test_lifecycle_coordinator_recovers_local_interrupted_states(
    caplog,
) -> None:
    caplog.set_level(logging.INFO, logger="comfyreview.generation")
    generations = _Generations(
        (
            GenerationRecord("prepared", "prepared", None),
            GenerationRecord("submitting", "submitting", None),
            GenerationRecord("submitted", "submitted", "prompt-1"),
            GenerationRecord("running", "running", "prompt-2"),
        )
    )
    observer = _Observer()

    results = GenerationLifecycleCoordinator(
        generations=generations,
        observer=observer,
        batch_limit=3,
    ).run_once()

    assert generations.requested_limits == [3]
    assert generations.transitions == [
        ("prepared", "failed", "startup_incomplete_preparation"),
        (
            "submitting",
            "reconciliation_required",
            "startup_ambiguous_submission",
        ),
    ]
    assert observer.observed == ["submitted"]
    assert [result.status for result in results] == [
        "failed",
        "reconciliation_required",
        "running",
    ]
    transitions = [
        record
        for record in caplog.records
        if record.message == "generation.lifecycle_transition_observed"
    ]
    assert [record.status for record in transitions] == [
        "failed",
        "reconciliation_required",
        "running",
    ]


def test_lifecycle_coordinator_isolates_one_observation_failure() -> None:
    generations = _Generations(
        (
            GenerationRecord("broken", "submitted", "prompt-a"),
            GenerationRecord("healthy", "running", "prompt-b"),
        )
    )
    observer = _Observer(failing_uid="broken")

    results = GenerationLifecycleCoordinator(
        generations=generations,
        observer=observer,
    ).run_once()

    assert observer.observed == ["broken", "healthy"]
    assert [result.generation_uid for result in results] == ["healthy"]


def test_lifecycle_worker_owns_one_thread_and_stops_cleanly() -> None:
    coordinator = _SignallingCoordinator()
    worker = GenerationLifecycleWorker(
        coordinator,
        poll_interval_seconds=60,
    )

    worker.start()
    assert coordinator.called.wait(timeout=1)
    worker.start()
    assert coordinator.calls == 1
    assert worker.stop(timeout_seconds=1) is True
    assert worker.stop(timeout_seconds=1) is True


def test_lifecycle_worker_survives_a_failed_polling_pass() -> None:
    coordinator = _FailingOnceCoordinator()
    worker = GenerationLifecycleWorker(
        coordinator,
        poll_interval_seconds=0.05,
    )

    worker.start()

    assert coordinator.recovered.wait(timeout=1)
    assert coordinator.calls >= 2
    assert worker.stop(timeout_seconds=1) is True


def test_lifecycle_worker_reports_a_bounded_shutdown_timeout() -> None:
    coordinator = _BlockingCoordinator()
    worker = GenerationLifecycleWorker(coordinator)
    worker.start()
    assert coordinator.entered.wait(timeout=1)

    assert worker.stop(timeout_seconds=0) is False

    coordinator.release.set()
    assert worker.stop(timeout_seconds=1) is True
