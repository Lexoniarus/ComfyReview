"""Pure presentation mapping for normalized and historical image metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_PROMPT_WRAPPER_PATTERNS = (
    r"^You are an assistant designed to generate high quality anime images based on textual prompts\.?\s*",
    r"^You are an assistant designed to generate low-quality images based on textual prompts\.?\s*",
    r"^<\s*Prompt\s*Start\s*>\s*",
)
_CHECKPOINT_NODE_TYPES = {
    "CheckpointLoaderSimple",
    "CheckpointLoader",
    "RandomLoadCheckpoint",
    "RandomLoadCheckpointSimple",
}
_LATENT_NODE_TYPES = {"EmptyLatentImage", "EmptySD3LatentImage"}


@dataclass(frozen=True, slots=True)
class LoraView:
    """Describe one LoRA entry rendered in image metadata."""

    name: str
    strength_model: float | None = None
    strength_clip: float | None = None


def _graph(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return the first supported ComfyUI graph representation."""
    candidate = metadata.get("comfy_prompt_graph") or metadata.get(
        "prompt_graph"
    )
    return candidate if isinstance(candidate, dict) else {}


def _clean_prompt_text(text: str) -> str:
    """Remove known export wrappers from one prompt string."""
    cleaned = str(text or "").strip()
    for pattern in _PROMPT_WRAPPER_PATTERNS:
        cleaned = re.sub(
            pattern,
            "",
            cleaned,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    return re.sub(r"^\s*\n+", "", cleaned, flags=re.MULTILINE).strip()


def _node_inputs(node: object) -> dict[str, Any]:
    """Return a graph node's inputs when they have the expected shape."""
    if not isinstance(node, dict):
        return {}
    inputs = node.get("inputs")
    return inputs if isinstance(inputs, dict) else {}


def _first_node(
    graph: dict[str, Any],
    node_types: set[str],
) -> dict[str, Any]:
    """Return the first graph node with one of the requested class types."""
    for node in graph.values():
        if isinstance(node, dict) and node.get("class_type") in node_types:
            return node
    return {}


def _checkpoint(metadata: dict[str, Any], graph: dict[str, Any]) -> str:
    """Resolve a checkpoint from normalized fields or a historical graph."""
    for key in ("checkpoint", "ckpt_name", "ckpt"):
        if value := metadata.get(key):
            return str(value)
    inputs = _node_inputs(_first_node(graph, _CHECKPOINT_NODE_TYPES))
    return str(inputs.get("ckpt_name") or inputs.get("checkpoint") or "")


def _resolution(metadata: dict[str, Any], graph: dict[str, Any]) -> str:
    """Resolve the rendered image resolution."""
    width = metadata.get("width")
    height = metadata.get("height")
    if width and height:
        return f"{width}x{height}"
    inputs = _node_inputs(_first_node(graph, _LATENT_NODE_TYPES))
    width = inputs.get("width")
    height = inputs.get("height")
    return f"{width}x{height}" if width and height else ""


def _optional_float(value: object) -> float | None:
    """Convert a metadata scalar to float when possible."""
    if value is None:
        return None
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


def _loras(graph: dict[str, Any]) -> list[LoraView]:
    """Map graph LoRA loader nodes to presentation values."""
    output: list[LoraView] = []
    for node in graph.values():
        if (
            not isinstance(node, dict)
            or node.get("class_type") != "LoraLoader"
        ):
            continue
        inputs = _node_inputs(node)
        name = inputs.get("lora_name")
        if name:
            output.append(
                LoraView(
                    name=str(name),
                    strength_model=_optional_float(
                        inputs.get("strength_model")
                    ),
                    strength_clip=_optional_float(inputs.get("strength_clip")),
                )
            )
    return output


def _resolve_graph_text(
    graph: dict[str, Any],
    reference: object,
) -> str:
    """Resolve a ComfyUI node-output reference to its composed text."""
    if not isinstance(reference, list) or len(reference) < 2:
        return ""
    inputs = _node_inputs(graph.get(str(reference[0])))
    text = inputs.get("text")
    if isinstance(text, list):
        return _resolve_graph_text(graph, text)
    if "value" in inputs:
        return str(inputs.get("value") or "")
    if "string_a" in inputs and "string_b" in inputs:
        left = _resolve_graph_text(graph, inputs.get("string_a"))
        right = _resolve_graph_text(graph, inputs.get("string_b"))
        delimiter = str(inputs.get("delimiter") or "")
        return f"{left}{delimiter}{right}"
    return str(text) if isinstance(text, str) else ""


def _graph_prompts(graph: dict[str, Any]) -> tuple[str, str]:
    """Resolve positive and negative text attached to the first KSampler."""
    inputs = _node_inputs(_first_node(graph, {"KSampler"}))
    return (
        _clean_prompt_text(_resolve_graph_text(graph, inputs.get("positive"))),
        _clean_prompt_text(_resolve_graph_text(graph, inputs.get("negative"))),
    )


def extract_view(metadata: dict[str, Any]) -> dict[str, Any]:
    """Build the existing review template view from image metadata."""
    graph = _graph(metadata)
    sampler_inputs = _node_inputs(_first_node(graph, {"KSampler"}))
    if graph:
        positive_prompt, negative_prompt = _graph_prompts(graph)
    else:
        positive_prompt = _clean_prompt_text(
            str(metadata.get("pos_prompt") or "")
        )
        negative_prompt = _clean_prompt_text(
            str(metadata.get("neg_prompt") or "")
        )
    return {
        "checkpoint": _checkpoint(metadata, graph),
        "resolution": _resolution(metadata, graph),
        "seed": sampler_inputs.get("seed") or metadata.get("seed"),
        "steps": sampler_inputs.get("steps") or metadata.get("steps"),
        "cfg": sampler_inputs.get("cfg") or metadata.get("cfg"),
        "sampler": sampler_inputs.get("sampler_name")
        or metadata.get("sampler"),
        "scheduler": sampler_inputs.get("scheduler")
        or metadata.get("scheduler"),
        "denoise": sampler_inputs.get("denoise") or metadata.get("denoise"),
        "pos_prompt": positive_prompt,
        "neg_prompt": negative_prompt,
        "loras": _loras(graph),
    }


def preset_text_from_view(view: dict[str, Any]) -> str:
    """Render the legacy sampler, scheduler, and steps preset string."""
    sampler = str(view.get("sampler") or "")
    scheduler = str(view.get("scheduler") or "")
    steps = str(view.get("steps") or "")
    return f"{sampler},{scheduler},{steps}"


def extract_prompts(metadata: dict[str, Any]) -> tuple[str, str, str]:
    """Return prompt texts and the existing source hint for the review UI."""
    graph = _graph(metadata)
    if graph:
        positive, negative = _graph_prompts(graph)
        return (
            positive,
            negative,
            "Prompts filled from comfy_prompt_graph (server-side).",
        )
    positive = _clean_prompt_text(str(metadata.get("pos_prompt") or ""))
    negative = _clean_prompt_text(str(metadata.get("neg_prompt") or ""))
    return positive, negative, "Prompts filled from stored meta keys."
