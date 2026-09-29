"""Local filesystem implementation of the output-image catalog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Final

from comfyreview.application.output_images import OutputImageReadModel

_IGNORED_DIRECTORY_NAMES: Final = {"_lora_export", "_trash"}
_CHECKPOINT_LOADER_TYPES: Final = {
    "CheckpointLoaderSimple",
    "CheckpointLoader",
    "RandomLoadCheckpoint",
    "RandomLoadCheckpointSimple",
}


class LocalOutputImageCatalog:
    """Discover output images and normalize their sidecar metadata."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = output_root

    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        """Return safe PNG/JSON pairs beneath the configured output root."""
        if not self._output_root.is_dir():
            return ()

        resolved_root = self._output_root.resolve()
        images: list[OutputImageReadModel] = []
        for png_path in self._output_root.rglob("*.png"):
            if not png_path.is_file() or self._is_ignored(png_path):
                continue
            json_path = png_path.with_suffix(".json")
            if not json_path.exists():
                continue
            if not self._is_inside_root(png_path, resolved_root):
                continue
            if not self._is_inside_root(json_path, resolved_root):
                continue
            images.append(self._build_read_model(png_path, json_path))

        images.sort(key=lambda image: str(image.json_path))
        return tuple(images)

    def _is_ignored(self, path: Path) -> bool:
        return bool(
            _IGNORED_DIRECTORY_NAMES & {part.lower() for part in path.parts}
        )

    def _is_inside_root(self, path: Path, resolved_root: Path) -> bool:
        try:
            path.resolve().relative_to(resolved_root)
        except (OSError, ValueError):
            return False
        return True

    def _build_read_model(
        self,
        png_path: Path,
        json_path: Path,
    ) -> OutputImageReadModel:
        metadata = self._read_metadata(json_path)
        checkpoint = self._infer_checkpoint(metadata)
        return OutputImageReadModel(
            png_path=png_path,
            json_path=json_path,
            subdir=self._infer_subdir(png_path),
            model_branch=self._infer_model_branch(metadata, checkpoint),
            checkpoint=checkpoint,
            combo_key=self._infer_combo_key(metadata, checkpoint),
            meta=metadata,
        )

    def _read_metadata(self, json_path: Path) -> dict[str, Any]:
        for encoding in ("utf-8", "utf-8-sig"):
            try:
                payload = json.loads(json_path.read_text(encoding=encoding))
            except (OSError, UnicodeError, json.JSONDecodeError):
                continue
            return payload if isinstance(payload, dict) else {}
        return {}

    def _infer_subdir(self, png_path: Path) -> str:
        try:
            relative_directory = png_path.parent.relative_to(self._output_root)
        except ValueError:
            return png_path.parent.name

        parts = tuple(part for part in relative_directory.parts if part)
        if len(parts) >= 2 and parts[0].lower() == "playground":
            return f"playground/{parts[1]}"
        return relative_directory.as_posix()

    def _infer_checkpoint(self, metadata: dict[str, Any]) -> str:
        direct_value = (
            metadata.get("checkpoint")
            or metadata.get("ckpt_name")
            or metadata.get("ckpt")
        )
        if direct_value:
            return str(direct_value)

        graph = metadata.get("comfy_prompt_graph") or metadata.get(
            "prompt_graph"
        )
        if not isinstance(graph, dict):
            return "unknown"
        for node in graph.values():
            checkpoint = self._checkpoint_from_graph_node(node)
            if checkpoint:
                return checkpoint
        return "unknown"

    def _checkpoint_from_graph_node(self, node: object) -> str:
        if not isinstance(node, dict):
            return ""
        if node.get("class_type") not in _CHECKPOINT_LOADER_TYPES:
            return ""
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            return ""
        checkpoint = (
            inputs.get("ckpt_name")
            or inputs.get("checkpoint")
            or inputs.get("ckpt")
        )
        if not checkpoint or isinstance(checkpoint, list):
            return ""
        return str(checkpoint)

    def _infer_model_branch(
        self,
        metadata: dict[str, Any],
        checkpoint: str,
    ) -> str:
        direct_value = (
            metadata.get("model_branch")
            or metadata.get("model_base")
            or metadata.get("base_model")
            or metadata.get("model")
        )
        if direct_value:
            return str(direct_value)
        if checkpoint != "unknown":
            return Path(checkpoint).stem
        return "unknown"

    def _infer_combo_key(
        self,
        metadata: dict[str, Any],
        checkpoint: str,
    ) -> str:
        direct_value = metadata.get("combo_key")
        if direct_value:
            return str(direct_value)

        parameters = self._sampler_parameters(metadata)
        return (
            f"ckpt={checkpoint}"
            f"|sampler={parameters['sampler']}"
            f"|sched={parameters['scheduler']}"
            f"|steps={parameters['steps']}"
            f"|cfg={parameters['cfg']}"
            f"|denoise={parameters['denoise']}"
        )

    def _sampler_parameters(
        self,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        sampler_metadata = metadata.get("ksampler")
        source = sampler_metadata if isinstance(sampler_metadata, dict) else {}
        parameters = {
            "sampler": source.get("sampler") or metadata.get("sampler") or "",
            "scheduler": source.get("scheduler")
            or metadata.get("scheduler")
            or "",
            "steps": source.get("steps") or metadata.get("steps") or "",
            "cfg": source.get("cfg") or metadata.get("cfg") or "",
            "denoise": source.get("denoise") or metadata.get("denoise") or "",
        }
        self._fill_from_chosen_line(parameters, metadata.get("chosen_line"))
        self._fill_from_graph(parameters, metadata)
        return parameters

    def _fill_from_chosen_line(
        self,
        parameters: dict[str, Any],
        chosen_line: object,
    ) -> None:
        if not chosen_line:
            return
        parts = [part.strip() for part in str(chosen_line).split(",")]
        if len(parts) < 4:
            return
        for name, value in zip(
            ("sampler", "scheduler", "steps", "cfg"),
            parts,
            strict=False,
        ):
            parameters[name] = parameters[name] or value

    def _fill_from_graph(
        self,
        parameters: dict[str, Any],
        metadata: dict[str, Any],
    ) -> None:
        if all(parameters.values()):
            return
        graph = metadata.get("comfy_prompt_graph") or metadata.get(
            "prompt_graph"
        )
        if not isinstance(graph, dict):
            return
        for node in graph.values():
            if (
                not isinstance(node, dict)
                or node.get("class_type") != "KSampler"
            ):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                return
            graph_values = {
                "sampler": inputs.get("sampler_name") or "",
                "scheduler": inputs.get("scheduler") or "",
                "steps": inputs.get("steps") or "",
                "cfg": inputs.get("cfg") or "",
                "denoise": inputs.get("denoise") or "",
            }
            for name, value in graph_values.items():
                parameters[name] = parameters[name] or value
            return
