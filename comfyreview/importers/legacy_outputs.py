"""Read-only audit of historical PNG/custom-node sidecar outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from comfyreview.application.lora_effects import LoraGraphEffectPolicy
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteOutputImageRepository,
)

_IGNORED_DIRECTORIES = {"_lora_export", "_trash"}
_CHECKPOINT_LOADERS = {
    "checkpointloader",
    "checkpointloadersimple",
    "randomloadcheckpoint",
    "randomloadcheckpointsimple",
}
_PROMPT_TYPES = {"primitivestring", "primitivestringmultiline"}


@dataclass(frozen=True, slots=True)
class LegacyOutputAuditResult:
    """Describe one completed read-only legacy-output audit."""

    report_path: Path
    summary: dict[str, int]
    conflict_fields: dict[str, int]


class LegacyOutputAuditor:
    """Inspect legacy output pairs without mutating images or canonical data."""

    def __init__(
        self,
        *,
        output_root: Path,
        canonical_database_path: Path,
    ) -> None:
        self._output_root = Path(output_root).resolve()
        self._database_path = Path(canonical_database_path).resolve()

    def audit(self, report_path: Path) -> LegacyOutputAuditResult:
        """Scan legacy outputs and write a provenance/import-readiness report."""
        CanonicalSchemaManager(self._database_path).validate()
        canonical_by_path = self._canonical_images_by_path()

        summary: Counter[str] = Counter()
        conflict_fields: Counter[str] = Counter()
        generation_groups: set[str] = set()
        items: list[dict[str, Any]] = []

        if self._output_root.is_dir():
            for png_path in sorted(self._output_root.rglob("*.png")):
                summary["png_seen"] += 1
                if self._is_ignored(png_path):
                    summary["png_ignored"] += 1
                    continue
                item = self._audit_png(
                    png_path,
                    canonical_by_path=canonical_by_path,
                )
                items.append(item)
                self._update_summary(
                    summary,
                    conflict_fields,
                    generation_groups,
                    item,
                )

        summary["generation_groups"] = len(generation_groups)
        stable_summary = {
            key: int(summary.get(key, 0))
            for key in (
                "png_seen",
                "png_ignored",
                "png_without_sidecar",
                "sidecar_pairs",
                "valid_sidecars",
                "invalid_sidecars",
                "full_graph_pairs",
                "partial_no_graph_pairs",
                "already_canonical",
                "pairs_with_conflicts",
                "total_ksampler_stages",
                "unsupported_sampler_like_nodes",
                "generation_groups",
            )
        }

        target = Path(report_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "format": "comfyreview-legacy-output-audit-v1",
            "created_at_utc": datetime.now(UTC).isoformat(),
            "output_root": str(self._output_root),
            "canonical_database": str(self._database_path),
            "summary": stable_summary,
            "conflict_fields": dict(sorted(conflict_fields.items())),
            "items": items,
        }
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return LegacyOutputAuditResult(
            report_path=target,
            summary=stable_summary,
            conflict_fields=dict(sorted(conflict_fields.items())),
        )

    def _audit_png(
        self,
        png_path: Path,
        *,
        canonical_by_path: dict[Path, tuple[str, str]],
    ) -> dict[str, Any]:
        resolved_png = self._inside_output_root(png_path)
        relative_png = resolved_png.relative_to(self._output_root).as_posix()
        canonical = canonical_by_path.get(resolved_png)
        base: dict[str, Any] = {
            "png_path": relative_png,
            "png_sha256": self._sha256_file(resolved_png),
            "canonical_image_uid": canonical[0] if canonical else None,
            "canonical_generation_uid": canonical[1] if canonical else None,
        }

        json_path = resolved_png.with_suffix(".json")
        if not json_path.is_file():
            return {
                **base,
                "status": "png_without_sidecar",
                "json_path": None,
            }

        resolved_json = self._inside_output_root(json_path)
        raw_bytes = resolved_json.read_bytes()
        base.update(
            {
                "json_path": resolved_json.relative_to(
                    self._output_root
                ).as_posix(),
                "sidecar_sha256": hashlib.sha256(raw_bytes).hexdigest(),
            }
        )
        metadata = self._decode_sidecar(raw_bytes)
        if metadata is None:
            return {
                **base,
                "status": "invalid_sidecar",
            }

        graph = self._prompt_graph(metadata)
        graph_sha = self._json_sha256(graph) if graph is not None else None
        timestamp = self._text(metadata.get("timestamp"))
        group_key = self._generation_group_key(
            timestamp=timestamp,
            workflow_sha256=graph_sha,
            sidecar_sha256=str(base["sidecar_sha256"]),
        )
        graph_facts = self._graph_facts(graph)
        summary_facts = self._sidecar_summary(metadata)
        conflicts = self._conflicts(
            graph_facts=graph_facts,
            sidecar_facts=summary_facts,
        )

        return {
            **base,
            "status": (
                "full_graph" if graph is not None else "partial_no_graph"
            ),
            "timestamp": timestamp or None,
            "workflow_sha256": graph_sha,
            "candidate_generation_key": group_key,
            "graph": graph_facts,
            "sidecar_summary": summary_facts,
            "conflicts": conflicts,
        }

    def _canonical_images_by_path(self) -> dict[Path, tuple[str, str]]:
        records = SqliteOutputImageRepository(
            self._database_path
        ).list_live_images()
        return {
            self._resolve_stored_path(record.png_path): (
                record.image_uid,
                record.generation_uid,
            )
            for record in records
        }

    def _resolve_stored_path(self, path: Path) -> Path:
        candidate = path if path.is_absolute() else self._output_root / path
        return candidate.resolve(strict=False)

    def _inside_output_root(self, path: Path) -> Path:
        resolved = path.resolve(strict=False)
        resolved.relative_to(self._output_root)
        return resolved

    @staticmethod
    def _decode_sidecar(raw_bytes: bytes) -> dict[str, Any] | None:
        try:
            payload = json.loads(raw_bytes.decode("utf-8-sig"))
        except (UnicodeError, json.JSONDecodeError):
            return None
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _prompt_graph(metadata: dict[str, Any]) -> dict[str, Any] | None:
        graph = metadata.get("comfy_prompt_graph")
        if not isinstance(graph, dict):
            graph = metadata.get("prompt_graph")
        return graph if isinstance(graph, dict) else None

    def _graph_facts(
        self,
        graph: dict[str, Any] | None,
    ) -> dict[str, Any]:
        if graph is None:
            return {
                "checkpoint": None,
                "positive_prompt_sha256": None,
                "negative_prompt_sha256": None,
                "ksampler_stages": [],
                "loras": [],
                "unsupported_sampler_like_nodes": [],
            }

        positive, negative = self._prompt_strings(graph)
        return {
            "checkpoint": self._checkpoint(graph) or None,
            "positive_prompt_sha256": self._text_sha256(positive),
            "negative_prompt_sha256": self._text_sha256(negative),
            "ksampler_stages": self._ksampler_stages(graph),
            "loras": self._loras(graph),
            "unsupported_sampler_like_nodes": (
                self._unsupported_sampler_nodes(graph)
            ),
        }

    def _sidecar_summary(self, metadata: dict[str, Any]) -> dict[str, Any]:
        ksampler = metadata.get("ksampler")
        sampler_facts = (
            {
                "seed": self._scalar(ksampler.get("seed")),
                "steps": self._scalar(ksampler.get("steps")),
                "cfg": self._scalar(ksampler.get("cfg")),
                "sampler": self._scalar(ksampler.get("sampler")),
                "scheduler": self._scalar(ksampler.get("scheduler")),
                "denoise": self._scalar(ksampler.get("denoise")),
            }
            if isinstance(ksampler, dict)
            else {}
        )
        return {
            "checkpoint": self._text(metadata.get("checkpoint")) or None,
            "positive_prompt_sha256": self._text_sha256(
                self._text(metadata.get("pos_prompt"))
            ),
            "negative_prompt_sha256": self._text_sha256(
                self._text(metadata.get("neg_prompt"))
            ),
            "chosen_line": self._text(metadata.get("chosen_line")) or None,
            "ksampler": sampler_facts,
        }

    def _conflicts(
        self,
        *,
        graph_facts: dict[str, Any],
        sidecar_facts: dict[str, Any],
    ) -> list[dict[str, Any]]:
        conflicts: list[dict[str, Any]] = []
        self._compare(
            conflicts,
            "checkpoint",
            graph_facts.get("checkpoint"),
            sidecar_facts.get("checkpoint"),
        )
        self._compare(
            conflicts,
            "positive_prompt",
            graph_facts.get("positive_prompt_sha256"),
            sidecar_facts.get("positive_prompt_sha256"),
        )
        self._compare(
            conflicts,
            "negative_prompt",
            graph_facts.get("negative_prompt_sha256"),
            sidecar_facts.get("negative_prompt_sha256"),
        )

        stages = graph_facts.get("ksampler_stages")
        summary = sidecar_facts.get("ksampler")
        if (
            isinstance(stages, list)
            and stages
            and isinstance(summary, dict)
            and summary
        ):
            first = stages[0]
            if isinstance(first, dict):
                for name in (
                    "seed",
                    "steps",
                    "cfg",
                    "sampler",
                    "scheduler",
                    "denoise",
                ):
                    self._compare(
                        conflicts,
                        f"ksampler.{name}",
                        first.get(name),
                        summary.get(name),
                    )
        return conflicts

    @staticmethod
    def _compare(
        conflicts: list[dict[str, Any]],
        field: str,
        graph_value: Any,
        sidecar_value: Any,
    ) -> None:
        if graph_value in (None, "") or sidecar_value in (None, ""):
            return
        if LegacyOutputAuditor._same_value(graph_value, sidecar_value):
            return
        conflicts.append(
            {
                "field": field,
                "graph_value": graph_value,
                "sidecar_value": sidecar_value,
            }
        )

    @staticmethod
    def _same_value(left: Any, right: Any) -> bool:
        try:
            return abs(float(left) - float(right)) < 1e-9
        except (TypeError, ValueError):
            return str(left) == str(right)

    def _ksampler_stages(
        self,
        graph: dict[str, Any],
    ) -> list[dict[str, Any]]:
        stages: list[dict[str, Any]] = []
        for node_id, node in graph.items():
            if not isinstance(node, dict):
                continue
            class_type = self._text(node.get("class_type") or node.get("type"))
            if class_type.lower() != "ksampler":
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                inputs = {}
            stages.append(
                {
                    "node_id": str(node_id),
                    "stage_order": len(stages),
                    "class_type": class_type,
                    "seed": self._scalar(inputs.get("seed")),
                    "steps": self._scalar(inputs.get("steps")),
                    "cfg": self._scalar(inputs.get("cfg")),
                    "sampler": self._scalar(inputs.get("sampler_name")),
                    "scheduler": self._scalar(inputs.get("scheduler")),
                    "denoise": self._scalar(inputs.get("denoise")),
                }
            )
        return stages

    def _unsupported_sampler_nodes(
        self,
        graph: dict[str, Any],
    ) -> list[dict[str, str]]:
        nodes: list[dict[str, str]] = []
        for node_id, node in graph.items():
            if not isinstance(node, dict):
                continue
            class_type = self._text(node.get("class_type") or node.get("type"))
            lowered = class_type.lower()
            if "ksampler" in lowered and lowered != "ksampler":
                nodes.append(
                    {
                        "node_id": str(node_id),
                        "class_type": class_type,
                    }
                )
        return nodes

    def _checkpoint(self, graph: dict[str, Any]) -> str:
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            class_type = self._text(
                node.get("class_type") or node.get("type")
            ).lower()
            if class_type not in _CHECKPOINT_LOADERS:
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            for key in ("ckpt_name", "checkpoint", "ckpt"):
                value = inputs.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
        return ""

    def _prompt_strings(
        self,
        graph: dict[str, Any],
    ) -> tuple[str, str]:
        positive = ""
        negative = ""
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            class_type = self._text(
                node.get("class_type") or node.get("type")
            ).lower()
            if class_type not in _PROMPT_TYPES:
                continue
            meta = node.get("_meta")
            title = (
                self._text(meta.get("title")).lower()
                if isinstance(meta, dict)
                else ""
            )
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            value = inputs.get("value")
            if value is None:
                value = inputs.get("text")
            if not isinstance(value, str):
                continue
            if title == "prompt" and not positive:
                positive = value
            if title in {"negative prompt", "negativeprompt"} and not negative:
                negative = value

        if not positive:
            positive = self._fixed_prompt(graph, "26:24")
        if not negative:
            negative = self._fixed_prompt(graph, "25:24")
        return positive, negative

    @staticmethod
    def _fixed_prompt(graph: dict[str, Any], node_id: str) -> str:
        node = graph.get(node_id)
        if not isinstance(node, dict):
            return ""
        inputs = node.get("inputs")
        if not isinstance(inputs, dict):
            return ""
        value = inputs.get("value")
        if value is None:
            value = inputs.get("text")
        return value if isinstance(value, str) else ""

    def _loras(self, graph: dict[str, Any]) -> list[dict[str, Any]]:
        effective_node_ids = {
            effect.node_id for effect in LoraGraphEffectPolicy().effects(graph)
        }
        loras: list[dict[str, Any]] = []
        for node_id, node in graph.items():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            lora_name = inputs.get("lora_name")
            if not isinstance(lora_name, str) or not lora_name.strip():
                continue
            if str(node_id) not in effective_node_ids:
                continue
            loras.append(
                {
                    "node_id": str(node_id),
                    "class_type": self._text(
                        node.get("class_type") or node.get("type")
                    ),
                    "name": lora_name.strip(),
                    "strength_model": self._scalar(
                        inputs.get("strength_model")
                    ),
                    "strength_clip": self._scalar(inputs.get("strength_clip")),
                }
            )
        return loras

    @staticmethod
    def _generation_group_key(
        *,
        timestamp: str,
        workflow_sha256: str | None,
        sidecar_sha256: str,
    ) -> str:
        evidence = workflow_sha256 or sidecar_sha256
        time_key = timestamp or sidecar_sha256
        payload = f"legacy_sidecar\\0{time_key}\\0{evidence}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    @staticmethod
    def _json_sha256(payload: dict[str, Any]) -> str:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _text_sha256(value: str) -> str | None:
        if not value:
            return None
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256_file(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _text(value: object) -> str:
        return "" if value is None else str(value).strip()

    @staticmethod
    def _scalar(value: object) -> str | int | float | bool | None:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        return None

    @staticmethod
    def _is_ignored(path: Path) -> bool:
        return bool(
            _IGNORED_DIRECTORIES & {part.lower() for part in path.parts}
        )

    @staticmethod
    def _update_summary(
        summary: Counter[str],
        conflict_fields: Counter[str],
        generation_groups: set[str],
        item: dict[str, Any],
    ) -> None:
        status = str(item.get("status") or "")
        if status == "png_without_sidecar":
            summary["png_without_sidecar"] += 1
            return

        summary["sidecar_pairs"] += 1
        if status == "invalid_sidecar":
            summary["invalid_sidecars"] += 1
            return

        summary["valid_sidecars"] += 1
        if status == "full_graph":
            summary["full_graph_pairs"] += 1
        else:
            summary["partial_no_graph_pairs"] += 1

        if item.get("canonical_image_uid"):
            summary["already_canonical"] += 1

        group_key = item.get("candidate_generation_key")
        if isinstance(group_key, str) and group_key:
            generation_groups.add(group_key)

        graph = item.get("graph")
        if isinstance(graph, dict):
            stages = graph.get("ksampler_stages")
            if isinstance(stages, list):
                summary["total_ksampler_stages"] += len(stages)
            unsupported = graph.get("unsupported_sampler_like_nodes")
            if isinstance(unsupported, list):
                summary["unsupported_sampler_like_nodes"] += len(unsupported)

        conflicts = item.get("conflicts")
        if isinstance(conflicts, list) and conflicts:
            summary["pairs_with_conflicts"] += 1
            for conflict in conflicts:
                if not isinstance(conflict, dict):
                    continue
                field = conflict.get("field")
                if isinstance(field, str) and field:
                    conflict_fields[field] += 1
