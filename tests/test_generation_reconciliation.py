"""Behavior tests for recovering ambiguous native generations."""

from __future__ import annotations

import pytest

from comfyreview.application import (
    ComfyUiConnectionError,
    ComfyUiJobStatus,
    GenerationMutationError,
    GenerationReconciliationRequired,
    GenerationReconciliationService,
    GenerationRecord,
    GenerationValidationError,
)


class _Generations:
    def __init__(
        self,
        events: list[str],
        *,
        status: str = "reconciliation_required",
        prompt_id: str | None = "prompt-1",
        fail_at: set[str] | None = None,
    ) -> None:
        self.events = events
        self.fail_at = set(fail_at or ())
        self.record = GenerationRecord("generation-1", status, prompt_id)

    def get(self, generation_uid):
        self.events.append("get")
        assert generation_uid == "generation-1"
        return self.record

    def prepare(self, generation):
        raise AssertionError(generation)

    def mark_submitting(self, generation_uid):
        raise AssertionError(generation_uid)

    def _set(self, event, status, prompt_id=None):
        self.events.append(event)
        if event in self.fail_at:
            raise OSError(event)
        self.record = GenerationRecord("generation-1", status, prompt_id)
        return self.record

    def mark_reconciliation_required(self, generation_uid, prompt_id, reason):
        assert generation_uid == "generation-1"
        assert reason
        return self._set("reconcile", "reconciliation_required", prompt_id)

    def mark_completed(self, generation_uid):
        assert generation_uid == "generation-1"
        return self._set("completed", "completed", self.record.prompt_id)

    def mark_failed(self, generation_uid, reason):
        assert generation_uid == "generation-1"
        assert reason
        return self._set("failed", "failed", self.record.prompt_id)

    def mark_running(self, generation_uid):
        assert generation_uid == "generation-1"
        return self._set("running", "running", self.record.prompt_id)

    def mark_submitted(self, generation_uid, prompt_id):
        assert generation_uid == "generation-1"
        return self._set("submitted", "submitted", prompt_id)


class _ComfyUi:
    def __init__(
        self,
        events: list[str],
        status: ComfyUiJobStatus | Exception,
    ) -> None:
        self.events = events
        self.status = status

    def get_status(self, prompt_id):
        self.events.append("history")
        assert prompt_id == "prompt-1"
        if isinstance(self.status, Exception):
            raise self.status
        return self.status

    def submit(self, compiled_graph):
        raise AssertionError(compiled_graph)

    def wait_or_watch(
        self, prompt_id, *, timeout_seconds, poll_interval_seconds=0.5
    ):
        raise AssertionError(
            (prompt_id, timeout_seconds, poll_interval_seconds)
        )

    def fetch_outputs(self, prompt_id):
        raise AssertionError(prompt_id)

    def discover_capabilities(self):
        raise AssertionError


class _Outputs:
    def __init__(
        self,
        events: list[str],
        *,
        complete: bool = False,
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.complete = complete
        self.error = error

    def outputs_complete(self, generation_uid):
        self.events.append("outputs_complete")
        assert generation_uid == "generation-1"
        return self.complete

    def collect(self, generation_uid, prompt_id):
        self.events.append("collect")
        assert (generation_uid, prompt_id) == ("generation-1", "prompt-1")
        if self.error is not None:
            raise self.error
        return ()


def _service(
    generations: _Generations,
    comfyui: _ComfyUi,
    outputs: _Outputs,
) -> GenerationReconciliationService:
    return GenerationReconciliationService(
        generations=generations,
        comfyui=comfyui,
        outputs=outputs,
    )


def test_reconciliation_completes_from_already_persisted_outputs() -> None:
    events: list[str] = []
    generations = _Generations(events)
    result = _service(
        generations,
        _ComfyUi(events, AssertionError("history must not be queried")),
        _Outputs(events, complete=True),
    ).reconcile("generation-1")

    assert result.status == "completed"
    assert events == ["get", "outputs_complete", "completed"]


@pytest.mark.parametrize(
    ("status", "transition", "expected"),
    (
        (
            ComfyUiJobStatus("prompt-1", "submitted", False, False),
            "submitted",
            "submitted",
        ),
        (
            ComfyUiJobStatus("prompt-1", "running", False, False),
            "running",
            "running",
        ),
        (
            ComfyUiJobStatus("prompt-1", "failed", False, True, "bad"),
            "failed",
            "failed",
        ),
    ),
)
def test_reconciliation_maps_known_external_states(
    status: ComfyUiJobStatus,
    transition: str,
    expected: str,
) -> None:
    events: list[str] = []
    generations = _Generations(events)

    result = _service(
        generations,
        _ComfyUi(events, status),
        _Outputs(events),
    ).reconcile("generation-1")

    assert result.status == expected
    assert events[-1] == transition


def test_reconciliation_collects_completed_external_outputs_idempotently() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)

    result = _service(
        generations,
        _ComfyUi(
            events,
            ComfyUiJobStatus("prompt-1", "completed", True, False),
        ),
        _Outputs(events),
    ).reconcile("generation-1")

    assert result.status == "completed"
    assert events[-3:] == ["history", "collect", "completed"]


def test_reconciliation_keeps_unknown_or_unavailable_external_state() -> None:
    events: list[str] = []
    generations = _Generations(events, prompt_id=None)
    service = _service(
        generations,
        _ComfyUi(events, ComfyUiConnectionError("offline")),
        _Outputs(events),
    )

    assert service.reconcile("generation-1").status == (
        "reconciliation_required"
    )
    assert events == ["get", "outputs_complete"]

    generations.record = GenerationRecord(
        "generation-1", "reconciliation_required", "prompt-1"
    )
    assert service.reconcile("generation-1").status == (
        "reconciliation_required"
    )
    assert events[-1] == "history"


def test_reconciliation_accepts_explicit_operator_prompt_identity() -> None:
    events: list[str] = []
    generations = _Generations(events, prompt_id=None)

    result = _service(
        generations,
        _ComfyUi(
            events,
            ComfyUiJobStatus("prompt-1", "completed", True, False),
        ),
        _Outputs(events),
    ).reconcile("generation-1", prompt_id=" prompt-1 ")

    assert result.status == "completed"
    assert events == [
        "get",
        "reconcile",
        "outputs_complete",
        "history",
        "collect",
        "completed",
    ]

    events.clear()
    generations.record = GenerationRecord(
        "generation-1", "reconciliation_required", "prompt-1"
    )
    _service(
        generations,
        _ComfyUi(
            events,
            ComfyUiJobStatus("prompt-1", "running", False, False),
        ),
        _Outputs(events),
    ).reconcile("generation-1", prompt_id="prompt-1")
    assert "reconcile" not in events


def test_reconciliation_reports_prompt_assignment_persistence_failure() -> (
    None
):
    events: list[str] = []
    generations = _Generations(
        events,
        prompt_id=None,
        fail_at={"reconcile"},
    )

    with pytest.raises(GenerationMutationError, match="prompt_id"):
        _service(
            generations,
            _ComfyUi(events, ComfyUiConnectionError("unused")),
            _Outputs(events),
        ).reconcile("generation-1", prompt_id="prompt-1")


def test_reconciliation_rejects_invalid_requests() -> None:
    events: list[str] = []
    with pytest.raises(GenerationValidationError, match="generation_uid"):
        _service(
            _Generations(events),
            _ComfyUi(events, ComfyUiConnectionError("unused")),
            _Outputs(events),
        ).reconcile(" ")
    with pytest.raises(GenerationValidationError, match="not awaiting"):
        _service(
            _Generations(events, status="completed"),
            _ComfyUi(events, ComfyUiConnectionError("unused")),
            _Outputs(events),
        ).reconcile("generation-1")
    with pytest.raises(GenerationValidationError, match="conflicts"):
        _service(
            _Generations(events),
            _ComfyUi(events, ComfyUiConnectionError("unused")),
            _Outputs(events),
        ).reconcile("generation-1", prompt_id="different")


def test_reconciliation_preserves_ambiguity_when_completion_fails() -> None:
    events: list[str] = []
    generations = _Generations(events)
    service = _service(
        generations,
        _ComfyUi(
            events,
            ComfyUiJobStatus("prompt-1", "completed", True, False),
        ),
        _Outputs(events, error=OSError("missing")),
    )

    with pytest.raises(GenerationReconciliationRequired, match="still"):
        service.reconcile("generation-1")
    assert events[-2:] == ["collect", "reconcile"]

    events.clear()
    generations.fail_at = {"completed"}
    with pytest.raises(GenerationMutationError, match="persist reconciled"):
        _service(
            generations,
            _ComfyUi(events, ComfyUiConnectionError("unused")),
            _Outputs(events, complete=True),
        ).reconcile("generation-1")
    assert events[-2:] == ["completed", "reconcile"]

    events.clear()
    generations.fail_at = {"reconcile"}
    with pytest.raises(GenerationMutationError, match="preserve"):
        _service(
            generations,
            _ComfyUi(
                events,
                ComfyUiJobStatus("prompt-1", "completed", True, False),
            ),
            _Outputs(events, error=OSError("missing")),
        ).reconcile("generation-1")
