"""Behavior tests for Card-runtime adapters of the shared generation service."""

from __future__ import annotations

from pathlib import Path

import pytest

from comfyreview.application import (
    ComfyUiCapabilities,
    ComfyUiSubmission,
    GenerationOutput,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    GenerationService,
    GenerationValidationError,
    WorkflowCompiler,
)
from comfyreview.repositories.filesystem import JsonWorkflowBlueprintRepository
from comfyreview.repositories.sqlite import (
    CardBattlerRuntimeSchemaManager,
    SqliteCardGenerationOutputRepository,
    SqliteCardGenerationRepository,
)

_CAPABILITIES = (
    "CheckpointLoaderSimple",
    "CLIPTextEncode",
    "LoadImage",
    "ImageScale",
    "VAEEncode",
    "KSampler",
    "VAEDecode",
    "PrimitiveString",
    "StringConcatenate",
    "SaveImage",
)


class _ComfyUi:
    def __init__(self, capabilities=_CAPABILITIES) -> None:
        self.capabilities = capabilities
        self.graphs = []

    def discover_capabilities(self):
        return ComfyUiCapabilities(
            self.capabilities,
            ("sa_solver",),
            ("simple",),
            ("card-model.safetensors",),
        )

    def submit(self, compiled_graph):
        self.graphs.append(compiled_graph)
        return ComfyUiSubmission("prompt-1")

    def get_status(self, prompt_id):
        raise AssertionError(prompt_id)

    def wait_or_watch(
        self, prompt_id, *, timeout_seconds, poll_interval_seconds=0.5
    ):
        raise AssertionError(
            (prompt_id, timeout_seconds, poll_interval_seconds)
        )

    def fetch_outputs(self, prompt_id):
        raise AssertionError(prompt_id)


class _Outputs:
    def collect(self, generation_uid, prompt_id):
        raise AssertionError((generation_uid, prompt_id))

    def outputs_complete(self, generation_uid):
        return False


class _Identities:
    def new_generation_uid(self):
        return "card-generation-1"


def _request() -> GenerationRequest:
    return GenerationRequest(
        GenerationPromptSnapshot("(hero:1.00)", "(blur:1.00)", ()),
        "card-evolution",
        1,
        "card-evolution",
        "session-1:tier-1:candidate-0",
        "card-model.safetensors",
        (
            GenerationSamplerSettings(
                "base_sampler",
                42,
                32,
                6.0,
                "sa_solver",
                "simple",
                0.55,
            ),
        ),
        GenerationOutputPolicy("card-battler", "session-1-0", ("primary",)),
        reference_image="comfyreview/card-battler/reference.png",
    )


def _service(path: Path, comfyui: _ComfyUi) -> GenerationService:
    root = Path(__file__).resolve().parents[1] / "data" / "workflows"
    return GenerationService(
        blueprints=JsonWorkflowBlueprintRepository(root),
        compiler=WorkflowCompiler(),
        generations=SqliteCardGenerationRepository(path),
        comfyui=comfyui,
        outputs=_Outputs(),
        identities=_Identities(),
    )


def test_shared_generation_service_persists_only_card_runtime_lifecycle(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(runtime).prepare_startup()
    canonical = tmp_path / "comfyreview.sqlite3"
    canonical.write_bytes(b"canonical")
    comfyui = _ComfyUi()

    submission = _service(runtime, comfyui).submit(_request())

    assert submission.generation_uid == "card-generation-1"
    assert submission.status == "submitted"
    assert submission.prompt_id == "prompt-1"
    assert canonical.read_bytes() == b"canonical"
    stored = SqliteCardGenerationRepository(runtime).get("card-generation-1")
    assert (
        stored.generation_uid,
        stored.status,
        stored.prompt_id,
    ) == (
        submission.generation_uid,
        submission.status,
        submission.prompt_id,
    )
    assert comfyui.graphs[0]["reference"]["inputs"]["image"].endswith(
        "reference.png"
    )


def test_card_output_repository_keeps_reserved_relative_paths(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "card-runtime.sqlite3"
    output_root = tmp_path / "output"
    output = output_root / "card-battler" / "candidate.png"
    output.parent.mkdir(parents=True)
    output.write_bytes(b"png")
    CardBattlerRuntimeSchemaManager(runtime).prepare_startup()
    _service(runtime, _ComfyUi()).submit(_request())
    repository = SqliteCardGenerationOutputRepository(runtime, output_root)
    generated = GenerationOutput(
        "image-card-1",
        "primary",
        "save",
        0,
        output,
        "hash-1",
    )

    assert repository.save_outputs("card-generation-1", (generated,)) == (
        generated,
    )
    assert repository.outputs_complete("card-generation-1") is True
    assert repository.primary_output("card-generation-1") == generated
    assert repository.recovery_plan(
        "card-generation-1"
    ).output_subdirectory == ("card-battler")
    repository.save_outputs("card-generation-1", (generated,))
    with pytest.raises(RuntimeError, match="conflicts"):
        repository.save_outputs(
            "card-generation-1",
            (
                GenerationOutput(
                    "other", "primary", "save", 0, output, "hash-2"
                ),
            ),
        )


def test_generation_service_rejects_missing_img2img_capability_before_write(
    tmp_path: Path,
) -> None:
    runtime = tmp_path / "card-runtime.sqlite3"
    CardBattlerRuntimeSchemaManager(runtime).prepare_startup()
    comfyui = _ComfyUi(
        tuple(item for item in _CAPABILITIES if item != "VAEEncode")
    )

    with pytest.raises(GenerationValidationError, match="VAEEncode"):
        _service(runtime, comfyui).submit(_request())

    assert SqliteCardGenerationRepository(runtime).list_active(10) == ()
