"""Behavior tests for explicit workflow blueprint defaults."""

from __future__ import annotations

import pytest

from comfyreview.application import (
    WorkflowBlueprint,
    WorkflowCompilationError,
    WorkflowDefaultsService,
    WorkflowInputBinding,
)


class _Blueprints:
    def __init__(self, blueprint: WorkflowBlueprint) -> None:
        self.blueprint = blueprint

    def get(self, blueprint_uid, version):
        assert (blueprint_uid, version) == ("default-character", 1)
        return self.blueprint


def _blueprint() -> WorkflowBlueprint:
    return WorkflowBlueprint(
        "default-character",
        1,
        {
            "checkpoint": {"inputs": {"ckpt_name": "model.safetensors"}},
            "sampler": {
                "inputs": {
                    "steps": 30,
                    "cfg": 6.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1,
                }
            },
        },
        {
            "checkpoint": WorkflowInputBinding("checkpoint", "ckpt_name"),
            "base_sampler": WorkflowInputBinding("sampler", ""),
        },
        (),
        ("base_sampler",),
    )


def test_workflow_defaults_service_reads_explicit_roles() -> None:
    defaults = WorkflowDefaultsService(_Blueprints(_blueprint())).load(
        "default-character",
        1,
    )

    assert defaults.checkpoint == "model.safetensors"
    assert defaults.sampler.steps == 30
    assert defaults.sampler.cfg == 6.5
    assert defaults.sampler.sampler == "euler"


@pytest.mark.parametrize(
    "blueprint",
    (
        WorkflowBlueprint("default-character", 1, {}, {}, (), ()),
        WorkflowBlueprint(
            "default-character",
            1,
            {},
            {"checkpoint": WorkflowInputBinding("missing", "ckpt_name")},
            (),
            (),
        ),
        WorkflowBlueprint(
            "default-character",
            1,
            {"checkpoint": {"inputs": {}}, "sampler": {"inputs": {}}},
            {
                "checkpoint": WorkflowInputBinding("checkpoint", "ckpt_name"),
                "base_sampler": WorkflowInputBinding("sampler", ""),
            },
            (),
            ("base_sampler",),
        ),
        WorkflowBlueprint(
            "default-character",
            1,
            {
                "checkpoint": {"inputs": {"ckpt_name": "model.safetensors"}},
                "sampler": {
                    "inputs": {
                        "steps": "bad",
                        "cfg": 6,
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "denoise": 1,
                    }
                },
            },
            {
                "checkpoint": WorkflowInputBinding("checkpoint", "ckpt_name"),
                "base_sampler": WorkflowInputBinding("sampler", ""),
            },
            (),
            ("base_sampler",),
        ),
        WorkflowBlueprint(
            "default-character",
            1,
            {
                "checkpoint": {"inputs": {"ckpt_name": "model.safetensors"}},
                "sampler": {
                    "inputs": {
                        "steps": 30,
                        "cfg": 6,
                        "sampler_name": "",
                        "scheduler": "normal",
                        "denoise": 1,
                    }
                },
            },
            {
                "checkpoint": WorkflowInputBinding("checkpoint", "ckpt_name"),
                "base_sampler": WorkflowInputBinding("sampler", ""),
            },
            (),
            ("base_sampler",),
        ),
    ),
)
def test_workflow_defaults_service_rejects_missing_role_values(
    blueprint,
) -> None:
    with pytest.raises(WorkflowCompilationError):
        WorkflowDefaultsService(_Blueprints(blueprint)).load(
            "default-character",
            1,
        )
