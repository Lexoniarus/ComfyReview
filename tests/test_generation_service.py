"""Behavior tests for canonical generation orchestration."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ComfyUiJobStatus,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    ComfyUiSubmission,
    ComfyUiTimeoutError,
    GenerationMutationError,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationReconciliationRequired,
    GenerationRecord,
    GenerationRequest,
    GenerationService,
    GenerationValidationError,
    WorkflowBlueprint,
    WorkflowCompiler,
    WorkflowInputBinding,
    WorkflowOutputBinding,
)


def _blueprint() -> WorkflowBlueprint:
    return WorkflowBlueprint(
        blueprint_uid="portrait",
        version=1,
        graph={
            "positive": {"inputs": {"text": ""}},
            "negative": {"inputs": {"text": ""}},
            "save": {"inputs": {"subfolder": "", "prefix": ""}},
        },
        role_bindings={
            "positive_prompt": WorkflowInputBinding("positive", "text"),
            "negative_prompt": WorkflowInputBinding("negative", "text"),
            "output_subdirectory": WorkflowInputBinding("save", "subfolder"),
            "filename_prefix": WorkflowInputBinding("save", "prefix"),
        },
        output_bindings=(WorkflowOutputBinding("primary", "save"),),
        sampler_roles=(),
        capability_requirements=("SaveImage",),
    )


def _request() -> GenerationRequest:
    return GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="portrait",
        blueprint_version=1,
        model_branch="sdxl",
        combo_key="",
        checkpoint=None,
        sampler_stages=(),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
    )


class _Blueprints:
    def __init__(
        self,
        events: list[str],
        requirements: tuple[str, ...] = ("SaveImage",),
    ) -> None:
        self.events = events
        self.requirements = requirements

    def get(self, blueprint_uid, version):
        self.events.append("blueprint")
        assert (blueprint_uid, version) == ("portrait", 1)
        return replace(
            _blueprint(),
            capability_requirements=self.requirements,
        )


class _Identities:
    def new_generation_uid(self):
        return "generation-1"


class _Generations:
    def __init__(
        self, events: list[str], fail_at: set[str] | None = None
    ) -> None:
        self.events = events
        self.fail_at = set(fail_at or ())
        self.record = GenerationRecord("generation-1", "prepared", None)

    def _set(self, event, status, prompt_id=None):
        self.events.append(event)
        if event in self.fail_at:
            raise OSError(event)
        self.record = GenerationRecord("generation-1", status, prompt_id)
        return self.record

    def prepare(self, generation):
        assert generation.generation_uid == "generation-1"
        return self._set("prepare", "prepared")

    def get(self, generation_uid):
        self.events.append("get")
        assert generation_uid == "generation-1"
        return self.record

    def mark_submitting(self, generation_uid):
        return self._set("submitting", "submitting")

    def mark_submitted(self, generation_uid, prompt_id):
        return self._set("submitted", "submitted", prompt_id)

    def mark_running(self, generation_uid):
        return self._set("running", "running", self.record.prompt_id)

    def mark_completed(self, generation_uid):
        return self._set("completed", "completed", self.record.prompt_id)

    def mark_failed(self, generation_uid, reason):
        assert reason
        return self._set("failed", "failed", self.record.prompt_id)

    def mark_reconciliation_required(self, generation_uid, prompt_id, reason):
        assert reason
        return self._set("reconcile", "reconciliation_required", prompt_id)


class _ComfyUi:
    def __init__(
        self,
        events: list[str],
        *,
        submit_error: Exception | None = None,
        wait_result: ComfyUiJobStatus | Exception | None = None,
        capabilities: tuple[str, ...] = ("SaveImage",),
    ) -> None:
        self.events = events
        self.submit_error = submit_error
        self.wait_result = wait_result
        self.capabilities = capabilities

    def discover_capabilities(self):
        self.events.append("capabilities")
        return ComfyUiCapabilities(self.capabilities, (), (), ())

    def submit(self, compiled_graph):
        self.events.append("external_submit")
        assert compiled_graph["positive"]["inputs"]["text"] == "hero"
        if self.submit_error is not None:
            raise self.submit_error
        return ComfyUiSubmission("prompt-1")

    def wait_or_watch(
        self, prompt_id, *, timeout_seconds, poll_interval_seconds=0.5
    ):
        self.events.append("external_wait")
        assert prompt_id == "prompt-1"
        assert timeout_seconds >= 0
        if isinstance(self.wait_result, Exception):
            raise self.wait_result
        assert self.wait_result is not None
        return self.wait_result

    def get_status(self, prompt_id):
        raise AssertionError(prompt_id)

    def fetch_outputs(self, prompt_id):
        raise AssertionError(prompt_id)


def _service(
    *,
    generations: _Generations,
    comfyui: _ComfyUi,
    events: list[str],
    requirements: tuple[str, ...] = ("SaveImage",),
) -> GenerationService:
    return GenerationService(
        blueprints=_Blueprints(events, requirements),
        compiler=WorkflowCompiler(),
        generations=generations,
        comfyui=comfyui,
        identities=_Identities(),
    )


def test_generation_service_submits_without_open_external_transaction() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events),
        events=events,
    )

    result = service.submit(_request())

    assert (result.generation_uid, result.status, result.prompt_id) == (
        "generation-1",
        "submitted",
        "prompt-1",
    )
    assert events == [
        "blueprint",
        "capabilities",
        "prepare",
        "submitting",
        "external_submit",
        "submitted",
    ]


@pytest.mark.parametrize(
    ("generation_request", "message"),
    (
        (replace(_request(), blueprint_uid=""), "blueprint_uid"),
        (replace(_request(), model_branch=""), "model_branch"),
        (
            replace(
                _request(),
                prompt=replace(_request().prompt, positive_text=""),
            ),
            "positive prompt",
        ),
        (
            replace(
                _request(),
                prompt=replace(_request().prompt, negative_text=""),
            ),
            "negative prompt",
        ),
    ),
)
def test_generation_service_validates_before_dependencies(
    generation_request, message
) -> None:
    events: list[str] = []
    with pytest.raises(GenerationValidationError, match=message):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events),
            events=events,
        ).submit(generation_request)
    assert events == []


def test_generation_service_requires_blueprint_capabilities() -> None:
    events: list[str] = []
    with pytest.raises(GenerationValidationError, match="SaveImage"):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events, capabilities=()),
            events=events,
        ).submit(_request())
    assert events == ["blueprint", "capabilities"]


def test_generation_service_skips_discovery_without_capability_requirements() -> (
    None
):
    events: list[str] = []
    result = _service(
        generations=_Generations(events),
        comfyui=_ComfyUi(events),
        events=events,
        requirements=(),
    ).submit(_request())

    assert result.status == "submitted"
    assert "capabilities" not in events


@pytest.mark.parametrize(
    "external_error",
    (ComfyUiTimeoutError("timeout"), ComfyUiConnectionError("offline")),
)
def test_generation_service_marks_ambiguous_submit_for_reconciliation(
    external_error,
) -> None:
    events: list[str] = []
    with pytest.raises(GenerationReconciliationRequired):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events, submit_error=external_error),
            events=events,
        ).submit(_request())
    assert events[-2:] == ["external_submit", "reconcile"]


def test_generation_service_marks_definitive_rejection_failed() -> None:
    events: list[str] = []
    with pytest.raises(GenerationMutationError, match="rejected"):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(
                events, submit_error=ComfyUiRejectionError("bad")
            ),
            events=events,
        ).submit(_request())
    assert events[-2:] == ["external_submit", "failed"]


def test_generation_service_handles_persistence_and_compensation_failures() -> (
    None
):
    events: list[str] = []
    with pytest.raises(GenerationMutationError, match="persist prepared"):
        _service(
            generations=_Generations(events, {"prepare"}),
            comfyui=_ComfyUi(events),
            events=events,
        ).submit(_request())

    events = []
    with pytest.raises(GenerationReconciliationRequired, match="confirmation"):
        _service(
            generations=_Generations(events, {"submitted"}),
            comfyui=_ComfyUi(events),
            events=events,
        ).submit(_request())
    assert events[-2:] == ["submitted", "reconcile"]

    events = []
    with pytest.raises(GenerationMutationError, match="could not be marked"):
        _service(
            generations=_Generations(events, {"reconcile"}),
            comfyui=_ComfyUi(
                events, submit_error=ComfyUiTimeoutError("timeout")
            ),
            events=events,
        ).submit(_request())

    events = []
    with pytest.raises(
        GenerationMutationError, match="could not be persisted"
    ):
        _service(
            generations=_Generations(events, {"failed"}),
            comfyui=_ComfyUi(events, submit_error=ComfyUiProtocolError("bad")),
            events=events,
        ).submit(_request())


@pytest.mark.parametrize(
    ("wait_result", "expected_status", "transition"),
    (
        (
            ComfyUiJobStatus("prompt-1", "running", False, False),
            "running",
            "running",
        ),
        (
            ComfyUiJobStatus("prompt-1", "completed", True, False),
            "completed",
            "completed",
        ),
        (
            ComfyUiJobStatus("prompt-1", "failed", False, True, "bad"),
            "failed",
            "failed",
        ),
        (ComfyUiTimeoutError("wait"), "submitted", None),
        (ComfyUiRejectionError("failed"), "failed", "failed"),
        (
            ComfyUiProtocolError("ambiguous"),
            "reconciliation_required",
            "reconcile",
        ),
    ),
)
def test_generation_service_wait_maps_external_state(
    wait_result,
    expected_status,
    transition,
) -> None:
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord(
        "generation-1", "submitted", "prompt-1"
    )
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events, wait_result=wait_result),
        events=events,
    )

    result = service.wait("generation-1", timeout_seconds=-1)

    assert result.status == expected_status
    if transition is not None:
        assert events[-1] == transition


def test_generation_service_wait_requires_generation_and_prompt_identity() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events),
        events=events,
    )
    with pytest.raises(GenerationValidationError, match="generation_uid"):
        service.wait(" ", timeout_seconds=1)
    with pytest.raises(GenerationValidationError, match="no external"):
        service.wait("generation-1", timeout_seconds=1)
