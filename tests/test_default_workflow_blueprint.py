"""Regression tests for the native default SaveImage blueprint."""

from pathlib import Path

from comfyreview.application import (
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
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
    assert all(
        node.get("class_type") != "name_meta_export"
        for node in compiled.graph.values()
    )
    assert compiled.graph["cr:output_subdir"]["inputs"]["value"] == (
        "playground/Hero"
    )
    assert compiled.graph["cr:filename_prefix"]["inputs"]["value"] == "hero_"
    assert compiled.output_bindings[0].node_id == "33"
