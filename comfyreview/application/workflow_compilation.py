"""Deterministic compilation of semantic generation requests into API graphs."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

if TYPE_CHECKING:
    from comfyreview.application.generation import GenerationRequest

_PROMPT_ROLES = {"positive_prompt", "negative_prompt"}
_SAMPLER_ROLES = {"base_sampler", "refiner_sampler", "detail_sampler"}
_POLICY_ROLES = {"output_subdirectory", "filename_prefix"}
_DIRECT_ROLES = {"checkpoint", "reference_image"}
_SUPPORTED_ROLES = (
    _PROMPT_ROLES
    | _SAMPLER_ROLES
    | _POLICY_ROLES
    | _DIRECT_ROLES
    | {"save_image"}
)


class WorkflowCompilationError(ValueError):
    """Reject an invalid blueprint or incompatible generation request."""


@dataclass(frozen=True, slots=True)
class WorkflowInputBinding:
    """Map one semantic role to one explicit graph input."""

    node_id: str
    input_name: str


@dataclass(frozen=True, slots=True)
class WorkflowOutputBinding:
    """Declare one expected output role and its graph node."""

    role: str
    node_id: str


@dataclass(frozen=True, slots=True)
class WorkflowBlueprint:
    """Hold one immutable versioned API graph template and explicit mappings."""

    blueprint_uid: str
    version: int
    graph: dict[str, Any]
    role_bindings: dict[str, WorkflowInputBinding]
    output_bindings: tuple[WorkflowOutputBinding, ...]
    sampler_roles: tuple[str, ...]
    capability_requirements: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompiledOutputBinding:
    """Identify an expected output role without predicting its batch index."""

    role: str
    node_id: str


@dataclass(frozen=True, slots=True)
class CompiledSamplerStage:
    """Record normalized sampler settings applied to one explicit role."""

    role: str
    node_id: str
    seed: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


@dataclass(frozen=True, slots=True)
class CompiledWorkflow:
    """Contain a canonical graph and the provenance needed to reproduce it."""

    graph: dict[str, Any]
    graph_hash: str
    blueprint_uid: str
    blueprint_version: int
    resolved_roles: tuple[str, ...]
    output_bindings: tuple[CompiledOutputBinding, ...]
    sampler_stages: tuple[CompiledSamplerStage, ...]
    capability_requirements: tuple[str, ...]


class WorkflowBlueprintRepository(Protocol):
    """Load immutable workflow blueprints by stable identity and version."""

    def get(
        self, blueprint_uid: str, version: int | None
    ) -> WorkflowBlueprint:
        """Return the selected blueprint or raise when it does not exist."""
        ...


class WorkflowCompiler:
    """Compile explicit semantic bindings without transport or naming policy."""

    def compile(
        self,
        blueprint: WorkflowBlueprint,
        request: GenerationRequest,
    ) -> CompiledWorkflow:
        """Validate and compile one request into a canonical ComfyUI graph."""
        self._validate_identity(blueprint, request)
        self._validate_blueprint(blueprint)
        graph = deepcopy(blueprint.graph)
        resolved_roles: list[str] = []

        self._write_required_role(
            graph,
            blueprint,
            "positive_prompt",
            request.prompt.positive_text,
            resolved_roles,
        )
        self._write_required_role(
            graph,
            blueprint,
            "negative_prompt",
            request.prompt.negative_text,
            resolved_roles,
        )
        if request.checkpoint is not None:
            self._write_required_role(
                graph,
                blueprint,
                "checkpoint",
                request.checkpoint,
                resolved_roles,
            )
        if request.reference_image is not None:
            self._write_required_role(
                graph,
                blueprint,
                "reference_image",
                request.reference_image,
                resolved_roles,
            )

        stages = self._compile_sampler_stages(
            graph,
            blueprint,
            request,
            resolved_roles,
        )
        self._write_required_role(
            graph,
            blueprint,
            "output_subdirectory",
            request.output_policy.output_subdirectory,
            resolved_roles,
        )
        self._write_required_role(
            graph,
            blueprint,
            "filename_prefix",
            request.output_policy.filename_prefix,
            resolved_roles,
        )
        outputs = self._compile_output_bindings(blueprint, request)
        canonical_graph = self._canonical_graph(graph)
        return CompiledWorkflow(
            graph=graph,
            graph_hash=hashlib.sha256(canonical_graph.encode()).hexdigest(),
            blueprint_uid=blueprint.blueprint_uid,
            blueprint_version=blueprint.version,
            resolved_roles=tuple(resolved_roles),
            output_bindings=outputs,
            sampler_stages=stages,
            capability_requirements=tuple(blueprint.capability_requirements),
        )

    @staticmethod
    def _validate_identity(
        blueprint: WorkflowBlueprint,
        request: GenerationRequest,
    ) -> None:
        if not blueprint.blueprint_uid or blueprint.version < 1:
            raise WorkflowCompilationError("blueprint identity is invalid")
        if request.blueprint_uid != blueprint.blueprint_uid:
            raise WorkflowCompilationError(
                "request blueprint identity does not match"
            )
        if (
            request.blueprint_version is not None
            and request.blueprint_version != blueprint.version
        ):
            raise WorkflowCompilationError(
                "request blueprint version does not match"
            )

    @staticmethod
    def _validate_blueprint(blueprint: WorkflowBlueprint) -> None:
        unknown = set(blueprint.role_bindings) - _SUPPORTED_ROLES
        if unknown:
            raise WorkflowCompilationError(
                "unsupported workflow roles: " + ", ".join(sorted(unknown))
            )
        for role, binding in blueprint.role_bindings.items():
            node = blueprint.graph.get(binding.node_id)
            if not isinstance(node, dict):
                raise WorkflowCompilationError(
                    f"role {role} references missing node {binding.node_id}"
                )
            inputs = node.get("inputs")
            if not isinstance(inputs, dict) or (
                binding.input_name and binding.input_name not in inputs
            ):
                raise WorkflowCompilationError(
                    f"role {role} references missing input {binding.input_name}"
                )
        for output in blueprint.output_bindings:
            if output.node_id not in blueprint.graph:
                raise WorkflowCompilationError(
                    f"output role {output.role} references missing node {output.node_id}"
                )
        if len(set(blueprint.sampler_roles)) != len(blueprint.sampler_roles):
            raise WorkflowCompilationError("sampler roles must be unique")
        if any(role not in _SAMPLER_ROLES for role in blueprint.sampler_roles):
            raise WorkflowCompilationError(
                "blueprint has unsupported sampler role"
            )

    def _compile_sampler_stages(
        self,
        graph: dict[str, Any],
        blueprint: WorkflowBlueprint,
        request: GenerationRequest,
        resolved_roles: list[str],
    ) -> tuple[CompiledSamplerStage, ...]:
        requested = {stage.role: stage for stage in request.sampler_stages}
        if len(requested) != len(request.sampler_stages):
            raise WorkflowCompilationError(
                "request sampler roles must be unique"
            )
        if set(requested) != set(blueprint.sampler_roles):
            raise WorkflowCompilationError(
                "request sampler roles do not match blueprint sampler roles"
            )
        compiled: list[CompiledSamplerStage] = []
        for role in blueprint.sampler_roles:
            stage = requested[role]
            binding = self._binding(blueprint, role)
            node = self._node_inputs(graph, binding.node_id)
            sampler_values = {
                "seed": int(stage.seed),
                "steps": int(stage.steps),
                "cfg": float(stage.cfg),
                "sampler_name": str(stage.sampler),
                "scheduler": str(stage.scheduler),
                "denoise": float(stage.denoise),
            }
            node.update(sampler_values)
            resolved_roles.append(role)
            compiled.append(
                CompiledSamplerStage(
                    role=role,
                    node_id=binding.node_id,
                    seed=int(stage.seed),
                    steps=int(stage.steps),
                    cfg=float(stage.cfg),
                    sampler=str(stage.sampler),
                    scheduler=str(stage.scheduler),
                    denoise=float(stage.denoise),
                )
            )
        return tuple(compiled)

    def _compile_output_bindings(
        self,
        blueprint: WorkflowBlueprint,
        request: GenerationRequest,
    ) -> tuple[CompiledOutputBinding, ...]:
        outputs = tuple(
            CompiledOutputBinding(binding.role, binding.node_id)
            for binding in blueprint.output_bindings
        )
        actual_roles = tuple(output.role for output in outputs)
        if actual_roles != request.output_policy.expected_roles:
            raise WorkflowCompilationError(
                "expected output roles do not match blueprint outputs"
            )
        if len(set(actual_roles)) != len(actual_roles):
            raise WorkflowCompilationError("output roles must be unique")
        return outputs

    def _write_required_role(
        self,
        graph: dict[str, Any],
        blueprint: WorkflowBlueprint,
        role: str,
        value: object,
        resolved_roles: list[str],
    ) -> None:
        binding = self._binding(blueprint, role)
        self._node_inputs(graph, binding.node_id)[binding.input_name] = value
        resolved_roles.append(role)

    @staticmethod
    def _binding(
        blueprint: WorkflowBlueprint,
        role: str,
    ) -> WorkflowInputBinding:
        binding = blueprint.role_bindings.get(role)
        if binding is None:
            raise WorkflowCompilationError(
                f"blueprint role is missing: {role}"
            )
        return binding

    @staticmethod
    def _node_inputs(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
        node = cast(dict[str, Any], graph[node_id])
        return cast(dict[str, Any], node["inputs"])

    @staticmethod
    def _canonical_graph(graph: dict[str, Any]) -> str:
        try:
            return json.dumps(
                graph,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as error:
            raise WorkflowCompilationError(
                "compiled graph is not canonical JSON"
            ) from error
