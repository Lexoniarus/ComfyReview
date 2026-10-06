"""Determine which LoRA nodes can influence a compiled workflow result."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from comfyreview.application.generation import GenerationLoraSelection


@dataclass(frozen=True, slots=True)
class LoraGraphEffect:
    """Describe the graph branches through which one LoRA can take effect."""

    node_id: str
    model_active: bool
    clip_active: bool


class LoraGraphEffectPolicy:
    """Trace sampler inputs back to effective LoRA loader outputs."""

    def effects(
        self, graph: Mapping[str, object]
    ) -> tuple[LoraGraphEffect, ...]:
        """Return effective LoRA nodes in stable graph order."""
        normalized = {
            str(node_id): node
            for node_id, node in graph.items()
            if isinstance(node, Mapping)
        }
        model_nodes: set[str] = set()
        clip_nodes: set[str] = set()
        for node in normalized.values():
            class_type = str(node.get("class_type") or node.get("type") or "")
            if not self._is_sampler(class_type):
                continue
            inputs = self._inputs(node)
            self._trace_branch(
                normalized,
                self._reference(inputs.get("model")),
                "model",
                model_nodes,
                set(),
            )
            for name in ("positive", "negative"):
                self._trace_conditioning(
                    normalized,
                    self._reference(inputs.get(name)),
                    clip_nodes,
                    set(),
                )
        return tuple(
            LoraGraphEffect(
                node_id=node_id,
                model_active=node_id in model_nodes,
                clip_active=node_id in clip_nodes,
            )
            for node_id in sorted(model_nodes | clip_nodes)
        )

    def active_branches(
        self, graph: Mapping[str, object]
    ) -> tuple[set[str], set[str], set[str]]:
        """Return active model, positive-CLIP and negative-CLIP nodes."""
        normalized = {
            str(node_id): node
            for node_id, node in graph.items()
            if isinstance(node, Mapping)
        }
        model_nodes: set[str] = set()
        positive_nodes: set[str] = set()
        negative_nodes: set[str] = set()
        for node in normalized.values():
            class_type = str(node.get("class_type") or node.get("type") or "")
            if not self._is_sampler(class_type):
                continue
            inputs = self._inputs(node)
            self._trace_branch(
                normalized,
                self._reference(inputs.get("model")),
                "model",
                model_nodes,
                set(),
            )
            self._trace_conditioning(
                normalized,
                self._reference(inputs.get("positive")),
                positive_nodes,
                set(),
            )
            self._trace_conditioning(
                normalized,
                self._reference(inputs.get("negative")),
                negative_nodes,
                set(),
            )
        return model_nodes, positive_nodes, negative_nodes

    @staticmethod
    def _is_sampler(class_type: str) -> bool:
        return class_type == "KSampler" or class_type.endswith("Sampler")

    def _trace_conditioning(
        self,
        graph: Mapping[str, Mapping[str, Any]],
        reference: tuple[str, int] | None,
        active: set[str],
        visited: set[tuple[str, int]],
    ) -> None:
        if reference is None or reference in visited:
            return
        visited.add(reference)
        node_id, output_index = reference
        node = graph.get(node_id)
        if node is None:
            return
        if self._is_lora(node):
            channel = "clip" if output_index == 1 else "model"
            self._trace_branch(
                graph,
                reference,
                channel,
                active,
                set(),
            )
            return
        for name, value in self._inputs(node).items():
            child = self._reference(value)
            if child is None:
                continue
            if name == "clip":
                self._trace_branch(
                    graph,
                    child,
                    "clip",
                    active,
                    set(),
                )
            else:
                self._trace_conditioning(graph, child, active, visited)

    def _trace_branch(
        self,
        graph: Mapping[str, Mapping[str, Any]],
        reference: tuple[str, int] | None,
        channel: str,
        active: set[str],
        visited: set[tuple[str, str]],
    ) -> None:
        if reference is None:
            return
        node_id, _output_index = reference
        visit = (node_id, channel)
        if visit in visited:
            return
        visited.add(visit)
        node = graph.get(node_id)
        if node is None:
            return
        inputs = self._inputs(node)
        if self._is_lora(node):
            strength = inputs.get(f"strength_{channel}")
            if self._has_effect(strength):
                active.add(node_id)
            self._trace_branch(
                graph,
                self._reference(inputs.get(channel)),
                channel,
                active,
                visited,
            )
            return
        self._trace_branch(
            graph,
            self._reference(inputs.get(channel)),
            channel,
            active,
            visited,
        )

    @staticmethod
    def _is_lora(node: Mapping[str, Any]) -> bool:
        return str(node.get("class_type") or node.get("type") or "") == (
            "LoraLoader"
        )

    @staticmethod
    def _inputs(node: Mapping[str, Any]) -> Mapping[str, Any]:
        inputs = node.get("inputs")
        return inputs if isinstance(inputs, Mapping) else {}

    @staticmethod
    def _reference(value: object) -> tuple[str, int] | None:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            return None
        try:
            return str(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _has_effect(value: object) -> bool:
        if value is None:
            return True
        if not isinstance(value, (int, float, str)):
            return True
        try:
            return float(value) != 0.0
        except (TypeError, ValueError):
            return True


class LoraGraphValidationError(ValueError):
    """Reject compiled graphs that do not apply every selected LoRA."""


class CompiledLoraGraphPolicy:
    """Validate exact ordered LoRA nodes and their effective graph paths."""

    def __init__(self, effects: LoraGraphEffectPolicy | None = None) -> None:
        self._effects = effects or LoraGraphEffectPolicy()

    def validate(
        self,
        graph: Mapping[str, object],
        selections: tuple[GenerationLoraSelection, ...],
    ) -> tuple[LoraGraphEffect, ...]:
        """Return effects or raise before generation persistence/submission."""
        expected_ids = tuple(
            f"cr:lora:{position:03d}" for position in range(len(selections))
        )
        generated_ids = tuple(
            sorted(
                str(node_id)
                for node_id in graph
                if str(node_id).startswith("cr:lora:")
            )
        )
        if generated_ids != expected_ids:
            raise LoraGraphValidationError(
                "compiled LoRA node count or order does not match selection"
            )
        checkpoint_id = self._single_node(graph, "CheckpointLoaderSimple")
        sampler_id = self._single_node(graph, "KSampler")
        encoder_ids = self._node_ids(graph, "CLIPTextEncode")
        if len(encoder_ids) < 2:
            raise LoraGraphValidationError(
                "compiled graph must contain both CLIP encoders"
            )
        expected_model = (checkpoint_id, 0)
        expected_clip = (checkpoint_id, 1)
        for position, selection in enumerate(selections):
            if (
                selection.model_strength_milli == 0
                and selection.clip_strength_milli == 0
            ):
                raise LoraGraphValidationError(
                    "selected LoRA must affect model or CLIP"
                )
            node = graph.get(expected_ids[position])
            if (
                not isinstance(node, Mapping)
                or str(node.get("class_type") or "") != "LoraLoader"
            ):
                raise LoraGraphValidationError(
                    "compiled LoRA node has the wrong class"
                )
            inputs = node.get("inputs")
            if not isinstance(inputs, Mapping):
                raise LoraGraphValidationError(
                    "compiled LoRA node has no inputs"
                )
            if str(inputs.get("lora_name") or "") != selection.name:
                raise LoraGraphValidationError(
                    "compiled LoRA provider filename does not match selection"
                )
            self._strength(
                inputs.get("strength_model"),
                selection.model_strength_milli,
                "model",
            )
            self._strength(
                inputs.get("strength_clip"),
                selection.clip_strength_milli,
                "CLIP",
            )
            if position:
                previous = expected_ids[position - 1]
                expected_model = (previous, 0)
                expected_clip = (previous, 1)
            if self._reference(inputs.get("model")) != expected_model:
                raise LoraGraphValidationError(
                    "compiled LoRA model chain is disconnected"
                )
            if self._reference(inputs.get("clip")) != expected_clip:
                raise LoraGraphValidationError(
                    "compiled LoRA CLIP chain is disconnected"
                )
        terminal_model = (
            (expected_ids[-1], 0) if expected_ids else (checkpoint_id, 0)
        )
        terminal_clip = (
            (expected_ids[-1], 1) if expected_ids else (checkpoint_id, 1)
        )
        sampler = graph.get(sampler_id)
        sampler_inputs = (
            sampler.get("inputs") if isinstance(sampler, Mapping) else None
        )
        if (
            not isinstance(sampler_inputs, Mapping)
            or self._reference(sampler_inputs.get("model")) != terminal_model
        ):
            raise LoraGraphValidationError(
                "compiled LoRA model chain does not reach KSampler"
            )
        for encoder_id in encoder_ids:
            encoder = graph.get(encoder_id)
            encoder_inputs = (
                encoder.get("inputs") if isinstance(encoder, Mapping) else None
            )
            if (
                not isinstance(encoder_inputs, Mapping)
                or self._reference(encoder_inputs.get("clip")) != terminal_clip
            ):
                raise LoraGraphValidationError(
                    "compiled LoRA CLIP chain does not reach both encoders"
                )
        model, positive, negative = self._effects.active_branches(graph)
        for position, selection in enumerate(selections):
            node_id = expected_ids[position]
            if selection.model_strength_milli and node_id not in model:
                raise LoraGraphValidationError(
                    "selected LoRA does not reach a sampler model input"
                )
            if selection.clip_strength_milli and (
                node_id not in positive or node_id not in negative
            ):
                raise LoraGraphValidationError(
                    "selected LoRA does not reach both CLIP conditioning inputs"
                )
        return self._effects.effects(graph)

    @classmethod
    def _single_node(cls, graph: Mapping[str, object], class_type: str) -> str:
        matches = cls._node_ids(graph, class_type)
        if len(matches) != 1:
            raise LoraGraphValidationError(
                f"compiled graph requires exactly one {class_type}"
            )
        return matches[0]

    @staticmethod
    def _node_ids(
        graph: Mapping[str, object], class_type: str
    ) -> tuple[str, ...]:
        return tuple(
            sorted(
                str(node_id)
                for node_id, node in graph.items()
                if isinstance(node, Mapping)
                and str(node.get("class_type") or "") == class_type
            )
        )

    @staticmethod
    def _strength(value: object, expected_milli: int, channel: str) -> None:
        try:
            actual_milli = round(float(str(value)) * 1000)
        except (TypeError, ValueError) as error:
            raise LoraGraphValidationError(
                f"compiled LoRA {channel} strength is invalid"
            ) from error
        if actual_milli != expected_milli:
            raise LoraGraphValidationError(
                f"compiled LoRA {channel} strength does not match selection"
            )

    @staticmethod
    def _reference(value: object) -> tuple[str, int] | None:
        if not isinstance(value, (list, tuple)) or len(value) < 2:
            return None
        try:
            return str(value[0]), int(value[1])
        except (TypeError, ValueError):
            return None
