"""Behavior tests for explicit role-based workflow compilation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    CompiledOutputBinding,
    GenerationLoraSelection,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    WorkflowBlueprint,
    WorkflowCompilationError,
    WorkflowCompiler,
    WorkflowConnection,
    WorkflowInputBinding,
    WorkflowLoraChainBinding,
    WorkflowOutputBinding,
)


def _blueprint() -> WorkflowBlueprint:
    return WorkflowBlueprint(
        blueprint_uid="portrait",
        version=3,
        graph={
            "positive": {"inputs": {"text": "old"}},
            "negative": {"inputs": {"text": "old"}},
            "checkpoint": {"inputs": {"ckpt_name": "old.safetensors"}},
            "sampler": {
                "inputs": {
                    "seed": 1,
                    "steps": 1,
                    "cfg": 1.0,
                    "sampler_name": "old",
                    "scheduler": "old",
                    "denoise": 1.0,
                }
            },
            "reference": {"inputs": {"image": "old.png"}},
            "save": {
                "inputs": {
                    "images": ["sampler", 0],
                    "subfolder": "old",
                    "filename_prefix": "old",
                }
            },
        },
        role_bindings={
            "positive_prompt": WorkflowInputBinding("positive", "text"),
            "negative_prompt": WorkflowInputBinding("negative", "text"),
            "checkpoint": WorkflowInputBinding("checkpoint", "ckpt_name"),
            "base_sampler": WorkflowInputBinding("sampler", ""),
            "reference_image": WorkflowInputBinding("reference", "image"),
            "output_subdirectory": WorkflowInputBinding("save", "subfolder"),
            "filename_prefix": WorkflowInputBinding("save", "filename_prefix"),
            "save_image": WorkflowInputBinding("save", ""),
        },
        output_bindings=(WorkflowOutputBinding("primary", "save"),),
        sampler_roles=("base_sampler",),
        capability_requirements=("SaveImage",),
    )


def _request() -> GenerationRequest:
    return GenerationRequest(
        prompt=GenerationPromptSnapshot(
            positive_text="hero",
            negative_text="blur",
            revision_uids=("revision-1",),
        ),
        blueprint_uid="portrait",
        blueprint_version=3,
        model_branch="sdxl",
        combo_key="character:1|scene:2",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                role="base_sampler",
                seed=42,
                steps=24,
                cfg=6.5,
                sampler="euler",
                scheduler="normal",
                denoise=0.8,
            ),
        ),
        output_policy=GenerationOutputPolicy(
            output_subdirectory="playground/Hero",
            filename_prefix="hero_",
            expected_roles=("primary",),
        ),
        reference_image="reference.png",
    )


def _lora_blueprint() -> WorkflowBlueprint:
    blueprint = replace(
        _blueprint(),
        lora_chain_binding=WorkflowLoraChainBinding(
            model_source=WorkflowConnection("checkpoint", 0),
            clip_source=WorkflowConnection("checkpoint", 1),
            model_targets=(WorkflowInputBinding("sampler", "model"),),
            clip_targets=(WorkflowInputBinding("positive", "clip"),),
        ),
    )
    blueprint.graph["sampler"]["inputs"]["model"] = ["checkpoint", 0]
    blueprint.graph["positive"]["inputs"]["clip"] = ["checkpoint", 1]
    return blueprint


def _lora_binding() -> WorkflowLoraChainBinding:
    binding = _lora_blueprint().lora_chain_binding
    assert binding is not None
    return binding


def test_workflow_compiler_uses_only_explicit_roles_and_preserves_blueprint() -> (
    None
):
    blueprint = _blueprint()

    compiled = WorkflowCompiler().compile(blueprint, _request())

    assert compiled.graph["positive"]["inputs"]["text"] == "hero"
    assert compiled.graph["negative"]["inputs"]["text"] == "blur"
    assert (
        compiled.graph["checkpoint"]["inputs"]["ckpt_name"]
        == "model.safetensors"
    )
    assert compiled.graph["sampler"]["inputs"] == {
        "seed": 42,
        "steps": 24,
        "cfg": 6.5,
        "sampler_name": "euler",
        "scheduler": "normal",
        "denoise": 0.8,
    }
    assert compiled.graph["save"]["inputs"]["subfolder"] == "playground/Hero"
    assert compiled.graph["save"]["inputs"]["filename_prefix"] == "hero_"
    assert blueprint.graph["positive"]["inputs"]["text"] == "old"
    assert compiled.output_bindings == (
        CompiledOutputBinding("primary", "save"),
    )
    assert compiled.sampler_stages[0].node_id == "sampler"
    assert compiled.capability_requirements == ("SaveImage",)
    assert "save_image" not in compiled.resolved_roles


def test_workflow_compiler_hash_is_canonical_and_request_values_are_optional() -> (
    None
):
    compiler = WorkflowCompiler()
    blueprint = _blueprint()
    request = replace(_request(), checkpoint=None, reference_image=None)

    first = compiler.compile(blueprint, request)
    reordered = replace(
        blueprint,
        graph=dict(reversed(tuple(blueprint.graph.items()))),
    )
    second = compiler.compile(reordered, request)

    assert first.graph_hash == second.graph_hash
    assert "checkpoint" not in first.resolved_roles
    assert "reference_image" not in first.resolved_roles


def test_workflow_compiler_builds_explicit_ordered_lora_chain() -> None:
    blueprint = _lora_blueprint()
    request = replace(
        _request(),
        loras=(
            GenerationLoraSelection("first.safetensors", 800, 700, 0),
            GenerationLoraSelection("second.safetensors", 600, 500, 1),
        ),
    )

    compiled = WorkflowCompiler().compile(blueprint, request)

    assert compiled.graph["cr:lora:000"]["inputs"] == {
        "lora_name": "first.safetensors",
        "strength_model": 0.8,
        "strength_clip": 0.7,
        "model": ["checkpoint", 0],
        "clip": ["checkpoint", 1],
    }
    assert compiled.graph["cr:lora:001"]["inputs"]["model"] == [
        "cr:lora:000",
        0,
    ]
    assert compiled.graph["sampler"]["inputs"]["model"] == [
        "cr:lora:001",
        0,
    ]
    assert compiled.graph["positive"]["inputs"]["clip"] == [
        "cr:lora:001",
        1,
    ]
    assert "cr:lora:000" not in blueprint.graph


def test_workflow_compiler_rejects_loras_without_explicit_binding() -> None:
    request = replace(
        _request(),
        loras=(GenerationLoraSelection("style.safetensors", 1000, 1000, 0),),
    )

    with pytest.raises(WorkflowCompilationError, match="does not support"):
        WorkflowCompiler().compile(_blueprint(), request)


@pytest.mark.parametrize(
    ("blueprint", "message"),
    (
        (
            replace(
                _lora_blueprint(),
                graph={
                    **_lora_blueprint().graph,
                    "cr:lora:000": {"inputs": {}},
                },
            ),
            "reserves",
        ),
        (
            replace(
                _lora_blueprint(),
                lora_chain_binding=replace(
                    _lora_binding(),
                    model_source=WorkflowConnection("missing", 0),
                ),
            ),
            "invalid source",
        ),
        (
            replace(
                _lora_blueprint(),
                lora_chain_binding=replace(
                    _lora_binding(),
                    model_targets=(),
                ),
            ),
            "requires model",
        ),
        (
            replace(
                _lora_blueprint(),
                lora_chain_binding=replace(
                    _lora_binding(),
                    model_targets=(WorkflowInputBinding("missing", "model"),),
                ),
            ),
            "missing target",
        ),
        (
            replace(
                _lora_blueprint(),
                lora_chain_binding=replace(
                    _lora_binding(),
                    model_targets=(
                        WorkflowInputBinding("sampler", "missing"),
                    ),
                ),
            ),
            "missing target input",
        ),
    ),
)
def test_workflow_compiler_rejects_invalid_lora_bindings(
    blueprint: WorkflowBlueprint,
    message: str,
) -> None:
    request = replace(
        _request(),
        loras=(GenerationLoraSelection("style.safetensors", 1000, 1000, 0),),
    )

    with pytest.raises(WorkflowCompilationError, match=message):
        WorkflowCompiler().compile(blueprint, request)


@pytest.mark.parametrize(
    ("blueprint", "generation_request", "message"),
    (
        (
            replace(_blueprint(), blueprint_uid=""),
            _request(),
            "identity is invalid",
        ),
        (
            _blueprint(),
            replace(_request(), blueprint_uid="other"),
            "identity does not match",
        ),
        (
            _blueprint(),
            replace(_request(), blueprint_version=4),
            "version does not match",
        ),
        (
            replace(
                _blueprint(),
                role_bindings={"unknown": WorkflowInputBinding("save", "")},
            ),
            _request(),
            "unsupported workflow roles",
        ),
        (
            replace(
                _blueprint(),
                role_bindings={
                    **_blueprint().role_bindings,
                    "positive_prompt": WorkflowInputBinding("missing", "text"),
                },
            ),
            _request(),
            "missing node",
        ),
        (
            replace(
                _blueprint(),
                role_bindings={
                    **_blueprint().role_bindings,
                    "positive_prompt": WorkflowInputBinding(
                        "positive", "missing"
                    ),
                },
            ),
            _request(),
            "missing input",
        ),
        (
            replace(
                _blueprint(),
                output_bindings=(WorkflowOutputBinding("primary", "missing"),),
            ),
            _request(),
            "output role primary references missing node",
        ),
        (
            replace(
                _blueprint(),
                sampler_roles=("base_sampler", "base_sampler"),
            ),
            _request(),
            "sampler roles must be unique",
        ),
        (
            replace(_blueprint(), sampler_roles=("unknown",)),
            replace(
                _request(),
                sampler_stages=(
                    replace(_request().sampler_stages[0], role="unknown"),
                ),
            ),
            "unsupported sampler role",
        ),
    ),
)
def test_workflow_compiler_rejects_invalid_blueprints(
    blueprint: WorkflowBlueprint,
    generation_request: GenerationRequest,
    message: str,
) -> None:
    with pytest.raises(WorkflowCompilationError, match=message):
        WorkflowCompiler().compile(blueprint, generation_request)


def test_workflow_compiler_rejects_request_binding_mismatches() -> None:
    compiler = WorkflowCompiler()
    blueprint = _blueprint()

    with pytest.raises(
        WorkflowCompilationError, match="sampler roles must be unique"
    ):
        compiler.compile(
            blueprint,
            replace(
                _request(),
                sampler_stages=(_request().sampler_stages[0],) * 2,
            ),
        )
    with pytest.raises(
        WorkflowCompilationError, match="sampler roles do not match"
    ):
        compiler.compile(blueprint, replace(_request(), sampler_stages=()))
    with pytest.raises(
        WorkflowCompilationError, match="output roles do not match"
    ):
        compiler.compile(
            blueprint,
            replace(
                _request(),
                output_policy=replace(
                    _request().output_policy,
                    expected_roles=("secondary",),
                ),
            ),
        )
    duplicate_outputs = replace(
        blueprint,
        output_bindings=(
            WorkflowOutputBinding("primary", "save"),
            WorkflowOutputBinding("primary", "save"),
        ),
    )
    duplicate_policy = replace(
        _request().output_policy,
        expected_roles=("primary", "primary"),
    )
    with pytest.raises(
        WorkflowCompilationError, match="output roles must be unique"
    ):
        compiler.compile(
            duplicate_outputs,
            replace(_request(), output_policy=duplicate_policy),
        )


def test_workflow_compiler_rejects_non_json_graph_and_missing_required_role() -> (
    None
):
    compiler = WorkflowCompiler()
    blueprint = _blueprint()
    bad_graph = {**blueprint.graph, "bad": {"inputs": {"value": {1, 2}}}}

    with pytest.raises(WorkflowCompilationError, match="not canonical JSON"):
        compiler.compile(replace(blueprint, graph=bad_graph), _request())
    bindings = dict(blueprint.role_bindings)
    del bindings["positive_prompt"]
    with pytest.raises(WorkflowCompilationError, match="role is missing"):
        compiler.compile(
            replace(blueprint, role_bindings=bindings), _request()
        )
