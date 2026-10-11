"""Contract tests for the dedicated Card evolution workflow and staging."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from comfyreview.application import (
    CardSourceImage,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    WorkflowCompiler,
)
from comfyreview.providers import (
    ComfyUiCardReferenceImageStager,
    MultipartUploadResponse,
)
from comfyreview.repositories.filesystem import JsonWorkflowBlueprintRepository


def _request() -> GenerationRequest:
    return GenerationRequest(
        prompt=GenerationPromptSnapshot("positive", "negative", ()),
        blueprint_uid="card-evolution",
        blueprint_version=1,
        model_branch="card-evolution",
        combo_key="session-1:tier-1:candidate-0",
        checkpoint="card-model.safetensors",
        sampler_stages=(
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
        output_policy=GenerationOutputPolicy(
            "card-battler",
            "session-1-0",
            ("primary",),
        ),
        reference_image="comfyreview/card-battler/reference.png",
    )


def test_card_evolution_blueprint_binds_reference_and_img2img_defaults() -> (
    None
):
    root = Path(__file__).resolve().parents[1] / "data" / "workflows"
    blueprint = JsonWorkflowBlueprintRepository(root).get("card-evolution", 1)

    compiled = WorkflowCompiler().compile(blueprint, _request())

    assert compiled.graph["reference"]["inputs"]["image"] == (
        "comfyreview/card-battler/reference.png"
    )
    assert compiled.graph["sampler"]["inputs"] == {
        "seed": 42,
        "steps": 32,
        "cfg": 6.0,
        "sampler_name": "sa_solver",
        "scheduler": "simple",
        "denoise": 0.55,
        "model": ["checkpoint", 0],
        "positive": ["positive", 0],
        "negative": ["negative", 0],
        "latent_image": ["encode", 0],
    }
    assert compiled.graph["input-scale"]["inputs"]["width"] == 1024
    assert compiled.graph["output-scale"]["inputs"]["width"] == 1080
    assert compiled.output_bindings[0].role == "primary"
    assert "LoadImage" in compiled.capability_requirements
    assert "VAEEncode" in compiled.capability_requirements


class _UploadTransport:
    def __init__(self, response: MultipartUploadResponse) -> None:
        self.response = response
        self.calls = []

    def upload(self, path, **kwargs):
        self.calls.append((path, kwargs))
        return self.response


def _image() -> CardSourceImage:
    content = b"\x89PNG\r\n\x1a\nupload"
    return CardSourceImage(
        "image-1",
        "image/png",
        content,
        hashlib.sha256(content).hexdigest(),
    )


def test_card_reference_stager_uploads_content_addressed_png() -> None:
    image = _image()
    filename = f"{image.content_hash}.png"
    transport = _UploadTransport(
        MultipartUploadResponse(
            200,
            {
                "name": filename,
                "subfolder": "comfyreview/card-battler",
                "type": "input",
            },
        )
    )

    staged = ComfyUiCardReferenceImageStager(transport).stage(image)

    assert staged.relative_name == f"comfyreview/card-battler/{filename}"
    path, request = transport.calls[0]
    assert path == "/upload/image"
    assert request["content"] == image.content
    assert request["fields"] == {
        "overwrite": "true",
        "subfolder": "comfyreview/card-battler",
        "type": "input",
    }


@pytest.mark.parametrize(
    ("response", "error"),
    [
        (MultipartUploadResponse(500, {}), ComfyUiRejectionError),
        (MultipartUploadResponse(200, []), ComfyUiProtocolError),
        (
            MultipartUploadResponse(
                200,
                {"name": "other.png", "subfolder": "", "type": "output"},
            ),
            ComfyUiProtocolError,
        ),
    ],
)
def test_card_reference_stager_rejects_failed_or_mismatched_upload(
    response,
    error,
) -> None:
    with pytest.raises(error):
        ComfyUiCardReferenceImageStager(_UploadTransport(response)).stage(
            _image()
        )
