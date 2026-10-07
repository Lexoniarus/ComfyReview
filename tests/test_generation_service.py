"""Behavior tests for canonical generation orchestration."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ComfyUiError,
    ComfyUiJobStatus,
    ComfyUiNotFoundError,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    ComfyUiSubmission,
    ComfyUiTimeoutError,
    GenerationCanvas,
    GenerationLoraSelection,
    GenerationMutationError,
    GenerationOutputPolicy,
    GenerationPromptGroup,
    GenerationPromptSnapshot,
    GenerationReconciliationRequired,
    GenerationRecord,
    GenerationRequest,
    GenerationService,
    GenerationValidationError,
    WorkflowBlueprint,
    WorkflowCompiler,
    WorkflowConnection,
    WorkflowInputBinding,
    WorkflowLoraChainBinding,
    WorkflowOutputBinding,
)


def _blueprint() -> WorkflowBlueprint:
    return WorkflowBlueprint(
        blueprint_uid="portrait",
        version=1,
        graph={
            "model": {"inputs": {}},
            "positive": {"inputs": {"text": "", "clip": ["model", 1]}},
            "negative": {"inputs": {"text": ""}},
            "save": {
                "inputs": {
                    "subfolder": "",
                    "prefix": "",
                    "model": ["model", 0],
                }
            },
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
        lora_chain_binding=WorkflowLoraChainBinding(
            model_source=WorkflowConnection("model", 0),
            clip_source=WorkflowConnection("model", 1),
            model_targets=(WorkflowInputBinding("save", "model"),),
            clip_targets=(WorkflowInputBinding("positive", "clip"),),
        ),
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
        upscale_models: tuple[str, ...] = (),
    ) -> None:
        self.events = events
        self.requirements = requirements
        self.upscale_models = upscale_models

    def get(self, blueprint_uid, version):
        self.events.append("blueprint")
        assert (blueprint_uid, version) == ("portrait", 1)
        return replace(
            _blueprint(),
            capability_requirements=self.requirements,
            upscale_model_requirements=self.upscale_models,
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

    def list_active(self, limit):
        del limit
        return (self.record,)

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
        observe_result: ComfyUiJobStatus | Exception | None = None,
        capabilities: tuple[str, ...] = ("SaveImage",),
        loras: tuple[str, ...] = (),
        upscale_models: tuple[str, ...] = (),
    ) -> None:
        self.events = events
        self.submit_error = submit_error
        self.wait_result = wait_result
        self.observe_result = observe_result
        self.capabilities = capabilities
        self.loras = loras
        self.upscale_models = upscale_models

    def discover_capabilities(self):
        self.events.append("capabilities")
        return ComfyUiCapabilities(
            self.capabilities,
            (),
            (),
            (),
            self.loras,
            self.upscale_models,
        )

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
        self.events.append("external_status")
        assert prompt_id == "prompt-1"
        if isinstance(self.observe_result, Exception):
            raise self.observe_result
        assert self.observe_result is not None
        return self.observe_result

    def fetch_outputs(self, prompt_id):
        raise AssertionError(prompt_id)


class _Outputs:
    def __init__(
        self,
        events: list[str],
        error: Exception | None = None,
    ) -> None:
        self.events = events
        self.error = error

    def collect(self, generation_uid, prompt_id):
        self.events.append("collect")
        assert (generation_uid, prompt_id) == ("generation-1", "prompt-1")
        if self.error is not None:
            raise self.error
        return ()

    def outputs_complete(self, generation_uid):
        assert generation_uid == "generation-1"
        return False


class _LoraContent:
    def __init__(self) -> None:
        self.called = False

    def apply(self, selections):
        self.called = True
        return tuple(
            replace(
                item,
                position=position,
                lora_uid="lora-style",
                content_level="sexy",
            )
            for position, item in enumerate(selections)
        )


def _service(
    *,
    generations: _Generations,
    comfyui: _ComfyUi,
    events: list[str],
    requirements: tuple[str, ...] = ("SaveImage",),
    upscale_models: tuple[str, ...] = (),
    output_error: Exception | None = None,
    lora_content=None,
    lora_triggers=None,
    lora_graph_policy=None,
) -> GenerationService:
    return GenerationService(
        blueprints=_Blueprints(events, requirements, upscale_models),
        compiler=WorkflowCompiler(),
        generations=generations,
        comfyui=comfyui,
        outputs=_Outputs(events, output_error),
        identities=_Identities(),
        lora_content=lora_content,
        lora_triggers=lora_triggers,
        lora_graph_policy=lora_graph_policy,
    )


class _InvalidLoraGraph:
    def validate(self, graph, selections):
        from comfyreview.application import LoraGraphValidationError

        raise LoraGraphValidationError("disconnected")


class _MissingLoraTrigger:
    def validate(self, selections, positive_atoms, negative_atoms):
        del selections, positive_atoms, negative_atoms
        raise ValueError("lora_trigger_required: style trigger")


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


def test_generation_service_resolves_lora_content_before_compilation() -> None:
    events: list[str] = []
    policy = _LoraContent()
    result = _service(
        generations=_Generations(events),
        comfyui=_ComfyUi(events, loras=("style.safetensors",)),
        events=events,
        lora_content=policy,
    ).submit(
        replace(
            _request(),
            loras=(
                GenerationLoraSelection("style.safetensors", 1000, 1000, 0),
            ),
        )
    )

    assert policy.called is True
    assert result.status == "submitted"


def test_generation_service_rejects_invalid_lora_graph_before_persistence() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events, loras=("style.safetensors",)),
        events=events,
        lora_graph_policy=_InvalidLoraGraph(),
    )
    request = replace(
        _request(),
        loras=(GenerationLoraSelection("style.safetensors", 1000, 1000, 0),),
    )

    with pytest.raises(GenerationValidationError, match="lora_graph_invalid"):
        service.submit(request)

    assert "prepare" not in events
    assert "external_submit" not in events


def test_generation_service_rejects_missing_lora_trigger_before_persistence() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events, loras=("style.safetensors",)),
        events=events,
        lora_triggers=_MissingLoraTrigger(),
    )
    request = replace(
        _request(),
        loras=(GenerationLoraSelection("style.safetensors", 1000, 1000, 0),),
    )

    with pytest.raises(
        GenerationValidationError, match="lora_trigger_required"
    ):
        service.submit(request)

    assert "prepare" not in events
    assert "external_submit" not in events


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
        (
            replace(
                _request(),
                loras=(GenerationLoraSelection("style", 1000, 1000, 1),),
            ),
            "positions",
        ),
        (
            replace(
                _request(),
                loras=(GenerationLoraSelection("", 1000, 1000, 0),),
            ),
            "name",
        ),
        (
            replace(_request(), canvas=GenerationCanvas(65, 1024)),
            "image dimensions",
        ),
        (
            replace(
                _request(),
                prompt=replace(
                    _request().prompt,
                    prompt_groups=(
                        GenerationPromptGroup(
                            kind="character",
                            component_uid="character-a",
                            revision_uid="revision-a",
                            position=1,
                        ),
                    ),
                ),
            ),
            "prompt group positions",
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


def test_generation_service_rejects_unavailable_and_duplicate_loras() -> None:
    events: list[str] = []
    unavailable = replace(
        _request(),
        loras=(GenerationLoraSelection("missing.safetensors", 1000, 1000, 0),),
    )
    with pytest.raises(GenerationValidationError, match="missing requested"):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events, loras=("available.safetensors",)),
            events=events,
        ).submit(unavailable)
    assert events == ["blueprint", "capabilities"]

    events.clear()
    duplicate = replace(
        _request(),
        loras=(
            GenerationLoraSelection("same.safetensors", 1000, 1000, 0),
            GenerationLoraSelection("same.safetensors", 500, 500, 1),
        ),
    )
    with pytest.raises(GenerationValidationError, match="unique"):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events, loras=("same.safetensors",)),
            events=events,
        ).submit(duplicate)


def test_generation_service_requires_blueprint_capabilities() -> None:
    events: list[str] = []
    with pytest.raises(GenerationValidationError, match="SaveImage"):
        _service(
            generations=_Generations(events),
            comfyui=_ComfyUi(events, capabilities=()),
            events=events,
        ).submit(_request())
    assert events == ["blueprint", "capabilities"]


def test_generation_service_requires_blueprint_upscale_model() -> None:
    events: list[str] = []
    with pytest.raises(GenerationValidationError, match="upscale models"):
        _service(
            events=events,
            generations=_Generations(events),
            comfyui=_ComfyUi(events, upscale_models=()),
            upscale_models=("example-upscaler.pth",),
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


def test_generation_service_collects_outputs_before_marking_complete() -> None:
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord(
        "generation-1", "submitted", "prompt-1"
    )
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(
            events,
            wait_result=ComfyUiJobStatus("prompt-1", "completed", True, False),
        ),
        events=events,
    )

    result = service.wait("generation-1", timeout_seconds=1)

    assert result.status == "completed"
    assert events[-2:] == ["collect", "completed"]


@pytest.mark.parametrize(
    ("observed", "expected_status", "last_event"),
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
        (ComfyUiConnectionError("offline"), "submitted", "external_status"),
        (ComfyUiTimeoutError("timeout"), "submitted", "external_status"),
        (
            ComfyUiNotFoundError("unknown"),
            "reconciliation_required",
            "reconcile",
        ),
        (
            ComfyUiError("unexpected"),
            "reconciliation_required",
            "reconcile",
        ),
    ),
)
def test_generation_service_observes_without_resubmitting(
    observed,
    expected_status,
    last_event,
) -> None:
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord(
        "generation-1", "submitted", "prompt-1"
    )
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events, observe_result=observed),
        events=events,
    )

    result = service.observe("generation-1")

    assert result.status == expected_status
    assert events[-1] == last_event
    assert "external_submit" not in events


def test_generation_service_rejects_observation_without_prompt_identity() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord("generation-1", "submitted", None)
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(events),
        events=events,
    )

    with pytest.raises(GenerationValidationError):
        service.observe("generation-1")


def test_generation_service_keeps_an_already_running_observation_stable() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord(
        "generation-1", "running", "prompt-1"
    )
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(
            events,
            observe_result=ComfyUiJobStatus(
                "prompt-1", "running", False, False
            ),
        ),
        events=events,
    )

    result = service.observe("generation-1")

    assert result.status == "running"
    assert events[-1] == "external_status"


def test_generation_service_marks_failed_collection_for_reconciliation() -> (
    None
):
    events: list[str] = []
    generations = _Generations(events)
    generations.record = GenerationRecord(
        "generation-1", "submitted", "prompt-1"
    )
    service = _service(
        generations=generations,
        comfyui=_ComfyUi(
            events,
            wait_result=ComfyUiJobStatus("prompt-1", "completed", True, False),
        ),
        events=events,
        output_error=OSError("missing output"),
    )

    with pytest.raises(
        GenerationReconciliationRequired,
        match="outputs could not be confirmed",
    ):
        service.wait("generation-1", timeout_seconds=1)

    assert events[-2:] == ["collect", "reconcile"]
