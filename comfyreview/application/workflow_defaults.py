"""Role-based defaults read from immutable workflow blueprints."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from comfyreview.application.workflow_compilation import (
    WorkflowBlueprint,
    WorkflowBlueprintRepository,
    WorkflowCompilationError,
)


@dataclass(frozen=True, slots=True)
class GenerationSamplerDefaults:
    """Hold editable defaults for one explicitly bound sampler role."""

    role: str
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


@dataclass(frozen=True, slots=True)
class GenerationDefaults:
    """Hold generation defaults exposed to a request preparation UI."""

    checkpoint: str
    sampler: GenerationSamplerDefaults


class WorkflowDefaultsService:
    """Read UI defaults through explicit blueprint role bindings."""

    def __init__(self, blueprints: WorkflowBlueprintRepository) -> None:
        self._blueprints = blueprints

    def load(
        self,
        blueprint_uid: str,
        version: int | None,
    ) -> GenerationDefaults:
        """Load checkpoint and base-sampler defaults without graph heuristics."""
        blueprint = self._blueprints.get(blueprint_uid, version)
        checkpoint = str(
            self._role_input(blueprint, "checkpoint", "ckpt_name")
        ).strip()
        sampler_inputs = self._role_inputs(blueprint, "base_sampler")
        try:
            sampler = GenerationSamplerDefaults(
                role="base_sampler",
                steps=int(sampler_inputs["steps"]),
                cfg=float(sampler_inputs["cfg"]),
                sampler=str(sampler_inputs["sampler_name"]),
                scheduler=str(sampler_inputs["scheduler"]),
                denoise=float(sampler_inputs["denoise"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise WorkflowCompilationError(
                "base_sampler defaults are incomplete"
            ) from error
        if not checkpoint or not sampler.sampler or not sampler.scheduler:
            raise WorkflowCompilationError(
                "workflow defaults contain empty required values"
            )
        return GenerationDefaults(checkpoint, sampler)

    @classmethod
    def _role_input(
        cls,
        blueprint: WorkflowBlueprint,
        role: str,
        expected_input: str,
    ) -> Any:
        binding = blueprint.role_bindings.get(role)
        if binding is None or binding.input_name != expected_input:
            raise WorkflowCompilationError(
                f"workflow default role is missing: {role}"
            )
        inputs = cls._role_inputs(blueprint, role)
        if expected_input not in inputs:
            raise WorkflowCompilationError(
                f"workflow default input is missing: {role}.{expected_input}"
            )
        return inputs[expected_input]

    @staticmethod
    def _role_inputs(
        blueprint: WorkflowBlueprint,
        role: str,
    ) -> dict[str, Any]:
        binding = blueprint.role_bindings.get(role)
        node = blueprint.graph.get(binding.node_id) if binding else None
        inputs = node.get("inputs") if isinstance(node, dict) else None
        if not isinstance(inputs, dict):
            raise WorkflowCompilationError(
                f"workflow default role is invalid: {role}"
            )
        return inputs
