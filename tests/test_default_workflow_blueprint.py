"""Regression tests for the native default SaveImage blueprint."""

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

import pytest

from comfyreview.application import (
    AspectFormat,
    CompiledLoraGraphPolicy,
    GenerationCanvas,
    GenerationGeometryPolicy,
    GenerationLoraSelection,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    LoraGraphValidationError,
    ResolutionClass,
    WorkflowCompiler,
)
from comfyreview.repositories.filesystem import JsonWorkflowBlueprintRepository


def test_default_blueprint_compiles_to_standard_save_image() -> None:
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    blueprint = repository.get("default-character", 1)
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=1,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero",
            "hero_",
            ("primary",),
        ),
    )

    compiled = WorkflowCompiler().compile(blueprint, request)

    assert compiled.graph["33"]["class_type"] == "SaveImage"
    assert compiled.graph["42"]["class_type"] == "CheckpointLoaderSimple"
    assert compiled.graph["42"]["inputs"] == {"ckpt_name": "model.safetensors"}
    assert all(
        node.get("class_type")
        not in {"name_meta_export", "RandomLoadCheckpoint"}
        for node in compiled.graph.values()
    )
    assert "CheckpointLoaderSimple" in compiled.capability_requirements
    assert compiled.graph["cr:output_subdir"]["inputs"]["value"] == (
        "playground/Hero"
    )
    assert compiled.graph["cr:filename_prefix"]["inputs"]["value"] == "hero_"
    assert compiled.output_bindings[0].node_id == "33"


def test_default_blueprint_v2_compiles_ordered_loras_without_custom_nodes() -> (
    None
):
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    blueprint = repository.get("default-character", 2)
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=2,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        loras=(GenerationLoraSelection("style.safetensors", 850, 650, 0),),
    )

    compiled = WorkflowCompiler().compile(blueprint, request)

    assert compiled.graph["cr:lora:000"]["class_type"] == "LoraLoader"
    assert compiled.graph["3"]["inputs"]["model"] == ["cr:lora:000", 0]
    assert compiled.graph["26:7"]["inputs"]["clip"] == ["cr:lora:000", 1]
    assert compiled.graph["25:7"]["inputs"]["clip"] == ["cr:lora:000", 1]
    assert all(
        node.get("class_type")
        not in {"name_meta_export", "RandomLoadCheckpoint"}
        for node in compiled.graph.values()
    )


def test_default_blueprint_v3_compiles_explicit_canvas_roles() -> None:
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    blueprint = repository.get("default-character", 3)
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=3,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        canvas=GenerationCanvas(768, 1152),
    )

    compiled = WorkflowCompiler().compile(blueprint, request)

    assert compiled.graph["13"]["inputs"] == {
        "width": 768,
        "height": 1152,
        "batch_size": 1,
    }
    assert {"image_width", "image_height"} <= set(compiled.resolved_roles)


def test_default_blueprint_v4_compiles_animesharp_and_exact_output() -> None:
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    blueprint = repository.get("default-character", 4)
    geometry = GenerationGeometryPolicy().resolve(
        AspectFormat.PORTRAIT_2_3, ResolutionClass.FULL_HD_1080
    )
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=4,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        canvas=GenerationCanvas(768, 1152),
        geometry=geometry,
    )

    compiled = WorkflowCompiler().compile(blueprint, request)

    assert compiled.graph["cr:upscale_model"]["inputs"]["model_name"] == (
        "4x-AnimeSharp.pth"
    )
    assert compiled.graph["cr:anime_upscale"]["inputs"]["image"] == ["8", 0]
    assert compiled.graph["cr:sharpen"]["inputs"] == {
        "image": ["cr:anime_upscale", 0],
        "sharpen_radius": 4,
        "sigma": 0.1,
        "alpha": 0.03,
    }
    assert compiled.graph["cr:final_scale"]["inputs"] == {
        "image": ["cr:sharpen", 0],
        "upscale_method": "lanczos",
        "width": 1080,
        "height": 1620,
        "crop": "disabled",
    }
    assert compiled.upscale_model_requirements == ("4x-AnimeSharp.pth",)
    assert CompiledLoraGraphPolicy().validate(compiled.graph, ()) == ()


def test_default_blueprint_v4_wires_ordered_loras_through_model_and_clip() -> (
    None
):
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    geometry = GenerationGeometryPolicy().resolve(
        AspectFormat.LANDSCAPE_16_9, ResolutionClass.HD_720
    )
    loras = (
        GenerationLoraSelection("first.safetensors", 800, 650, 0),
        GenerationLoraSelection("second.safetensors", 0, 1200, 1),
    )
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=4,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        canvas=GenerationCanvas(geometry.source_width, geometry.source_height),
        geometry=geometry,
        loras=loras,
    )

    compiled = WorkflowCompiler().compile(
        repository.get("default-character", 4), request
    )
    effects = CompiledLoraGraphPolicy().validate(compiled.graph, loras)

    assert compiled.graph["cr:lora:000"]["inputs"]["model"] == ["42", 0]
    assert compiled.graph["cr:lora:001"]["inputs"]["model"] == [
        "cr:lora:000",
        0,
    ]
    assert compiled.graph["cr:lora:001"]["inputs"]["clip"] == [
        "cr:lora:000",
        1,
    ]
    assert compiled.graph["3"]["inputs"]["model"] == ["cr:lora:001", 0]
    assert compiled.graph["26:7"]["inputs"]["clip"] == [
        "cr:lora:001",
        1,
    ]
    assert compiled.graph["25:7"]["inputs"]["clip"] == [
        "cr:lora:001",
        1,
    ]
    assert tuple(item.node_id for item in effects) == (
        "cr:lora:000",
        "cr:lora:001",
    )

    broken = {key: dict(value) for key, value in compiled.graph.items()}
    broken["25:7"] = {
        **broken["25:7"],
        "inputs": {**broken["25:7"]["inputs"], "clip": ["42", 1]},
    }
    with pytest.raises(LoraGraphValidationError, match="both encoders"):
        CompiledLoraGraphPolicy().validate(broken, loras)

    invalid_graphs = []
    extra = deepcopy(compiled.graph)
    extra["cr:lora:999"] = deepcopy(extra["cr:lora:000"])
    invalid_graphs.append((extra, loras, "count or order"))
    missing_encoder = deepcopy(compiled.graph)
    del missing_encoder["25:7"]
    invalid_graphs.append((missing_encoder, loras, "both CLIP encoders"))
    invalid_graphs.append(
        (
            compiled.graph,
            (
                replace(
                    loras[0],
                    model_strength_milli=0,
                    clip_strength_milli=0,
                ),
                loras[1],
            ),
            "must affect",
        )
    )
    wrong_class = deepcopy(compiled.graph)
    wrong_class["cr:lora:000"]["class_type"] = "SaveImage"
    invalid_graphs.append((wrong_class, loras, "wrong class"))
    missing_inputs = deepcopy(compiled.graph)
    missing_inputs["cr:lora:000"]["inputs"] = None
    invalid_graphs.append((missing_inputs, loras, "no inputs"))
    wrong_name = deepcopy(compiled.graph)
    wrong_name["cr:lora:000"]["inputs"]["lora_name"] = "wrong.safetensors"
    invalid_graphs.append((wrong_name, loras, "filename"))
    invalid_strength = deepcopy(compiled.graph)
    invalid_strength["cr:lora:000"]["inputs"]["strength_model"] = []
    invalid_graphs.append((invalid_strength, loras, "strength is invalid"))
    wrong_strength = deepcopy(compiled.graph)
    wrong_strength["cr:lora:000"]["inputs"]["strength_model"] = 0.7
    invalid_graphs.append((wrong_strength, loras, "does not match"))
    broken_model = deepcopy(compiled.graph)
    broken_model["cr:lora:000"]["inputs"]["model"] = ["42"]
    invalid_graphs.append((broken_model, loras, "model chain is disconnected"))
    broken_clip = deepcopy(compiled.graph)
    broken_clip["cr:lora:000"]["inputs"]["clip"] = ["42", "bad"]
    invalid_graphs.append((broken_clip, loras, "CLIP chain is disconnected"))
    broken_sampler = deepcopy(compiled.graph)
    broken_sampler["3"]["inputs"]["model"] = ["42", 0]
    invalid_graphs.append((broken_sampler, loras, "does not reach KSampler"))
    no_checkpoint = deepcopy(compiled.graph)
    no_checkpoint["42"]["class_type"] = "Other"
    invalid_graphs.append((no_checkpoint, loras, "exactly one Checkpoint"))
    two_samplers = deepcopy(compiled.graph)
    two_samplers["sampler-copy"] = deepcopy(two_samplers["3"])
    invalid_graphs.append((two_samplers, loras, "exactly one KSampler"))
    for graph, selections, message in invalid_graphs:
        with pytest.raises(LoraGraphValidationError, match=message):
            CompiledLoraGraphPolicy().validate(graph, selections)

    class MissingEffects:
        def __init__(self, model, positive, negative):
            self.branches = (model, positive, negative)

        def active_branches(self, graph):
            return self.branches

        def effects(self, graph):
            return ()

    all_nodes = {"cr:lora:000", "cr:lora:001"}
    with pytest.raises(LoraGraphValidationError, match="sampler model"):
        CompiledLoraGraphPolicy(
            cast(Any, MissingEffects(set(), all_nodes, all_nodes))
        ).validate(compiled.graph, loras)
    with pytest.raises(LoraGraphValidationError, match="both CLIP"):
        CompiledLoraGraphPolicy(
            cast(Any, MissingEffects(all_nodes, set(), all_nodes))
        ).validate(compiled.graph, loras)


@pytest.mark.parametrize(
    ("aspect", "resolution", "expected"),
    [
        (aspect, resolution, dimensions)
        for aspect, row in {
            AspectFormat.PORTRAIT_2_3: {
                ResolutionClass.HD_720: (720, 1080),
                ResolutionClass.FULL_HD_1080: (1080, 1620),
                ResolutionClass.UHD_2160: (2160, 3240),
            },
            AspectFormat.LANDSCAPE_3_2: {
                ResolutionClass.HD_720: (1080, 720),
                ResolutionClass.FULL_HD_1080: (1620, 1080),
                ResolutionClass.UHD_2160: (3240, 2160),
            },
            AspectFormat.LANDSCAPE_16_9: {
                ResolutionClass.HD_720: (1280, 720),
                ResolutionClass.FULL_HD_1080: (1920, 1080),
                ResolutionClass.UHD_2160: (3840, 2160),
            },
            AspectFormat.PORTRAIT_9_16: {
                ResolutionClass.HD_720: (720, 1280),
                ResolutionClass.FULL_HD_1080: (1080, 1920),
                ResolutionClass.UHD_2160: (2160, 3840),
            },
            AspectFormat.SQUARE_1_1: {
                ResolutionClass.HD_720: (720, 720),
                ResolutionClass.FULL_HD_1080: (1080, 1080),
                ResolutionClass.UHD_2160: (2160, 2160),
            },
        }.items()
        for resolution, dimensions in row.items()
    ],
)
def test_default_blueprint_v4_compiles_every_output_matrix_cell(
    aspect: AspectFormat,
    resolution: ResolutionClass,
    expected: tuple[int, int],
) -> None:
    repository = JsonWorkflowBlueprintRepository(
        Path(__file__).resolve().parents[1] / "data" / "workflows"
    )
    geometry = GenerationGeometryPolicy().resolve(aspect, resolution)
    request = GenerationRequest(
        prompt=GenerationPromptSnapshot("hero", "blur", ()),
        blueprint_uid="default-character",
        blueprint_version=4,
        model_branch="sdxl",
        combo_key="",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        canvas=GenerationCanvas(geometry.source_width, geometry.source_height),
        geometry=geometry,
    )

    compiled = WorkflowCompiler().compile(
        repository.get("default-character", 4), request
    )

    assert (
        compiled.graph["cr:final_scale"]["inputs"]["width"],
        compiled.graph["cr:final_scale"]["inputs"]["height"],
    ) == expected
