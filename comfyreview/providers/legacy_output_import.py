"""Filesystem provider for audited legacy custom-node outputs."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from comfyreview.importers.legacy_models import (
    LegacyImageImport,
    LegacyOutputImportValidationError,
    LegacySamplerStageImport,
)


class LocalLegacyOutputImportSource:
    """Verify an audit snapshot and materialize import records."""

    def __init__(self, expected_database_path: Path) -> None:
        self._database_path = Path(expected_database_path).resolve()

    def load(
        self,
        report_path: Path,
    ) -> tuple[tuple[LegacyImageImport, ...], int]:
        """Return verified records and the excluded sidecarless count."""
        report_file = Path(report_path).resolve()
        payload = json.loads(report_file.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise LegacyOutputImportValidationError(
                "Audit report must contain a JSON object"
            )
        self._validate_report(payload)

        output_root = Path(str(payload["output_root"])).resolve()
        items = payload.get("items")
        if not isinstance(items, list):
            raise LegacyOutputImportValidationError(
                "Audit report has no item list"
            )

        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        excluded_without_sidecar = 0
        for item in items:
            if not isinstance(item, dict):
                raise LegacyOutputImportValidationError(
                    "Audit report contains a malformed item"
                )
            status = item.get("status")
            if status == "png_without_sidecar":
                self._verify_sidecarless_item(output_root, item)
                excluded_without_sidecar += 1
                continue
            if status != "full_graph":
                raise LegacyOutputImportValidationError(
                    f"Audit item is not importable: {status}"
                )
            group_key = item.get("candidate_generation_key")
            if not isinstance(group_key, str) or not group_key:
                raise LegacyOutputImportValidationError(
                    "Audited full-graph item has no generation key"
                )
            grouped[group_key].append(item)

        records: list[LegacyImageImport] = []
        for group_key in sorted(grouped):
            group = sorted(
                grouped[group_key],
                key=lambda item: (
                    0 if item.get("canonical_image_uid") else 1,
                    str(item.get("png_path") or ""),
                ),
            )
            generation_uid = self._generation_uid(group_key, group)
            for output_index, item in enumerate(group):
                records.append(
                    self._record(
                        output_root=output_root,
                        item=item,
                        generation_uid=generation_uid,
                        output_index=output_index,
                    )
                )
        self._validate_record_identities(records)
        return tuple(records), excluded_without_sidecar

    def _validate_report(self, payload: dict[str, Any]) -> None:
        if payload.get("format") != "comfyreview-legacy-output-audit-v1":
            raise LegacyOutputImportValidationError(
                "Unsupported legacy-output audit format"
            )
        report_database = Path(str(payload.get("canonical_database") or ""))
        if report_database.resolve() != self._database_path:
            raise LegacyOutputImportValidationError(
                "Audit report belongs to a different canonical database"
            )
        summary = payload.get("summary")
        conflicts = payload.get("conflict_fields")
        items = payload.get("items")
        if not isinstance(summary, dict) or not isinstance(conflicts, dict):
            raise LegacyOutputImportValidationError(
                "Audit report summary is malformed"
            )
        if not isinstance(items, list):
            raise LegacyOutputImportValidationError(
                "Audit report has no item list"
            )
        try:
            ignored_count = int(summary.get("png_ignored", 0))
        except (TypeError, ValueError) as error:
            raise LegacyOutputImportValidationError(
                "Audit summary value is invalid: png_ignored"
            ) from error
        calculated_summary, calculated_conflicts = self._summarize(
            items,
            ignored_count=ignored_count,
        )
        for name, calculated in calculated_summary.items():
            try:
                reported = int(summary.get(name, -1))
            except (TypeError, ValueError) as error:
                raise LegacyOutputImportValidationError(
                    f"Audit summary value is invalid: {name}"
                ) from error
            if reported != calculated:
                raise LegacyOutputImportValidationError(
                    f"Audit summary does not match items: {name}"
                )
        try:
            normalized_conflicts = {
                str(name): int(count) for name, count in conflicts.items()
            }
        except (TypeError, ValueError) as error:
            raise LegacyOutputImportValidationError(
                "Audit conflict summary is malformed"
            ) from error
        if normalized_conflicts != calculated_conflicts:
            raise LegacyOutputImportValidationError(
                "Audit conflict summary does not match items"
            )
        if int(summary.get("invalid_sidecars", 0)) != 0:
            raise LegacyOutputImportValidationError(
                "Audit contains invalid sidecars"
            )
        if int(summary.get("partial_no_graph_pairs", 0)) != 0:
            raise LegacyOutputImportValidationError(
                "Audit contains sidecars without full workflow graphs"
            )
        if int(summary.get("pairs_with_conflicts", 0)) != 0 or conflicts:
            raise LegacyOutputImportValidationError(
                "Audit contains graph/sidecar conflicts"
            )
        if int(summary.get("unsupported_sampler_like_nodes", 0)) != 0:
            raise LegacyOutputImportValidationError(
                "Audit contains unsupported sampler-like nodes"
            )

    @staticmethod
    def _summarize(
        items: list[object],
        *,
        ignored_count: int,
    ) -> tuple[dict[str, int], dict[str, int]]:
        summary: Counter[str] = Counter()
        summary["png_ignored"] = ignored_count
        summary["png_seen"] = ignored_count
        conflict_fields: Counter[str] = Counter()
        generation_groups: set[str] = set()
        for value in items:
            if not isinstance(value, dict):
                raise LegacyOutputImportValidationError(
                    "Audit report contains a malformed item"
                )
            summary["png_seen"] += 1
            status = value.get("status")
            if status == "png_without_sidecar":
                summary["png_without_sidecar"] += 1
                continue
            summary["sidecar_pairs"] += 1
            if status == "invalid_sidecar":
                summary["invalid_sidecars"] += 1
                continue
            if status not in {"full_graph", "partial_no_graph"}:
                raise LegacyOutputImportValidationError(
                    f"Audit report contains an unknown status: {status}"
                )
            summary["valid_sidecars"] += 1
            summary[
                "full_graph_pairs"
                if status == "full_graph"
                else "partial_no_graph_pairs"
            ] += 1
            if value.get("canonical_image_uid"):
                summary["already_canonical"] += 1
            group_key = value.get("candidate_generation_key")
            if isinstance(group_key, str) and group_key:
                generation_groups.add(group_key)
            graph = value.get("graph")
            if isinstance(graph, dict):
                stages = graph.get("ksampler_stages")
                if isinstance(stages, list):
                    summary["total_ksampler_stages"] += len(stages)
                unsupported = graph.get("unsupported_sampler_like_nodes")
                if isinstance(unsupported, list):
                    summary["unsupported_sampler_like_nodes"] += len(
                        unsupported
                    )
            item_conflicts = value.get("conflicts")
            if isinstance(item_conflicts, list) and item_conflicts:
                summary["pairs_with_conflicts"] += 1
                for conflict in item_conflicts:
                    if not isinstance(conflict, dict):
                        raise LegacyOutputImportValidationError(
                            "Audit report contains a malformed conflict"
                        )
                    field = conflict.get("field")
                    if isinstance(field, str) and field:
                        conflict_fields[field] += 1
        summary["generation_groups"] = len(generation_groups)
        stable_names = (
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
        stable = {name: int(summary.get(name, 0)) for name in stable_names}
        return stable, dict(sorted(conflict_fields.items()))

    def _verify_sidecarless_item(
        self,
        output_root: Path,
        item: dict[str, Any],
    ) -> None:
        png_path = self._resolve_source(
            output_root,
            item.get("png_path"),
            ".png",
        )
        self._verify_hash(png_path, str(item.get("png_sha256") or ""))
        if (
            item.get("json_path") is not None
            or png_path.with_suffix(".json").exists()
        ):
            raise LegacyOutputImportValidationError(
                "Sidecarless audit item changed since audit"
            )

    @staticmethod
    def _validate_record_identities(
        records: list[LegacyImageImport],
    ) -> None:
        seen_images: dict[str, Path] = {}
        generation_hashes: dict[str, str] = {}
        for record in records:
            previous_path = seen_images.setdefault(
                record.image_uid,
                record.png_path,
            )
            if previous_path != record.png_path:
                raise LegacyOutputImportValidationError(
                    "Audited images produce a duplicate canonical identity"
                )
            previous_hash = generation_hashes.setdefault(
                record.generation_uid,
                record.workflow_hash,
            )
            if previous_hash != record.workflow_hash:
                raise LegacyOutputImportValidationError(
                    "Audited generation group contains conflicting workflows"
                )

    def _record(
        self,
        *,
        output_root: Path,
        item: dict[str, Any],
        generation_uid: str,
        output_index: int,
    ) -> LegacyImageImport:
        png_path = self._resolve_source(
            output_root,
            item.get("png_path"),
            ".png",
        )
        json_path = self._resolve_source(
            output_root,
            item.get("json_path"),
            ".json",
        )
        content_hash = str(item.get("png_sha256") or "")
        self._verify_hash(png_path, content_hash)
        self._verify_hash(json_path, str(item.get("sidecar_sha256") or ""))

        raw_metadata_json = json_path.read_text(encoding="utf-8-sig")
        metadata = json.loads(raw_metadata_json)
        if not isinstance(metadata, dict):
            raise LegacyOutputImportValidationError(
                f"Sidecar is no longer an object: {json_path}"
            )
        graph = metadata.get("comfy_prompt_graph")
        if not isinstance(graph, dict):
            graph = metadata.get("prompt_graph")
        if not isinstance(graph, dict):
            raise LegacyOutputImportValidationError(
                f"Workflow graph disappeared from {json_path}"
            )

        workflow_hash = self._json_sha256(graph)
        expected_workflow_hash = str(item.get("workflow_sha256") or "")
        if workflow_hash != expected_workflow_hash:
            raise LegacyOutputImportValidationError(
                f"Workflow hash changed since audit: {json_path}"
            )

        graph_facts = item.get("graph")
        if not isinstance(graph_facts, dict):
            raise LegacyOutputImportValidationError(
                "Audited graph facts are missing"
            )
        positive_prompt, negative_prompt = self._prompt_strings(graph)
        if not positive_prompt:
            positive_prompt = str(metadata.get("pos_prompt") or "")
        if not negative_prompt:
            negative_prompt = str(metadata.get("neg_prompt") or "")
        checkpoint = self._checkpoint(graph_facts, graph, metadata)
        stages = self._sampler_stages(graph_facts)
        first = stages[0] if stages else None
        loras = self._normalized_loras(graph_facts)

        existing_image_uid = self._optional_text(
            item.get("canonical_image_uid")
        )
        existing_generation_uid = self._optional_text(
            item.get("canonical_generation_uid")
        )
        image_uid = existing_image_uid or self._image_uid(
            png_sha256=str(item["png_sha256"]),
            generation_uid=generation_uid,
            output_index=output_index,
        )

        return LegacyImageImport(
            image_uid=image_uid,
            generation_uid=generation_uid,
            png_path=png_path,
            json_path=json_path,
            content_hash=content_hash,
            output_index=output_index,
            model_branch=self._model_branch(metadata, checkpoint),
            checkpoint=checkpoint,
            combo_key=self._combo_key(checkpoint, first),
            seed=first.seed if first else None,
            steps=first.steps if first else None,
            cfg=first.cfg if first else None,
            sampler=first.sampler if first else None,
            scheduler=first.scheduler if first else None,
            denoise=first.denoise if first else None,
            loras_json=json.dumps(
                loras,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            positive_prompt=positive_prompt,
            negative_prompt=negative_prompt,
            raw_metadata_json=raw_metadata_json,
            workflow_json=json.dumps(
                graph,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ),
            workflow_hash=workflow_hash,
            sampler_stages=stages,
            existing_image_uid=existing_image_uid,
            existing_generation_uid=existing_generation_uid,
        )

    @staticmethod
    def _generation_uid(
        group_key: str,
        group: list[dict[str, Any]],
    ) -> str:
        existing = {
            str(item["canonical_generation_uid"])
            for item in group
            if item.get("canonical_generation_uid")
        }
        if len(existing) > 1:
            raise LegacyOutputImportValidationError(
                "One audited generation group maps to multiple canonical "
                "generations"
            )
        return next(iter(existing), f"legacy-generation-{group_key}")

    @staticmethod
    def _image_uid(
        *,
        png_sha256: str,
        generation_uid: str,
        output_index: int,
    ) -> str:
        evidence = (
            f"{png_sha256}\0{generation_uid}\0legacy_sidecar\0{output_index}"
        )
        digest = hashlib.sha256(evidence.encode("utf-8")).hexdigest()
        return f"legacy-image-{digest}"

    @staticmethod
    def _resolve_source(
        output_root: Path,
        relative_value: object,
        suffix: str,
    ) -> Path:
        if not isinstance(relative_value, str) or not relative_value:
            raise LegacyOutputImportValidationError(
                "Audited source path is missing"
            )
        candidate = (output_root / relative_value).resolve(strict=False)
        try:
            candidate.relative_to(output_root)
        except ValueError as error:
            raise LegacyOutputImportValidationError(
                "Audited source escaped the output root"
            ) from error
        if candidate.suffix.lower() != suffix or not candidate.is_file():
            raise LegacyOutputImportValidationError(
                f"Audited source no longer exists: {candidate}"
            )
        return candidate

    @staticmethod
    def _verify_hash(path: Path, expected: str) -> None:
        if not expected:
            raise LegacyOutputImportValidationError(
                f"Audit hash missing for {path}"
            )
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        if digest.hexdigest() != expected:
            raise LegacyOutputImportValidationError(
                f"Source changed since audit: {path}"
            )

    @staticmethod
    def _json_sha256(graph: dict[str, Any]) -> str:
        encoded = json.dumps(
            graph,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    @staticmethod
    def _prompt_strings(graph: dict[str, Any]) -> tuple[str, str]:
        positive = ""
        negative = ""
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            class_type = (
                str(node.get("class_type") or node.get("type") or "")
                .strip()
                .lower()
            )
            if class_type not in {
                "primitivestring",
                "primitivestringmultiline",
            }:
                continue
            meta = node.get("_meta")
            title = (
                str(meta.get("title") or "").strip().lower()
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
            positive = LocalLegacyOutputImportSource._fixed_prompt(
                graph,
                "26:24",
            )
        if not negative:
            negative = LocalLegacyOutputImportSource._fixed_prompt(
                graph,
                "25:24",
            )
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

    @staticmethod
    def _checkpoint(
        graph_facts: dict[str, Any],
        graph: dict[str, Any],
        metadata: dict[str, Any],
    ) -> str:
        audited = graph_facts.get("checkpoint")
        if isinstance(audited, str) and audited:
            return audited
        for node in graph.values():
            if not isinstance(node, dict):
                continue
            inputs = node.get("inputs")
            if not isinstance(inputs, dict):
                continue
            value = inputs.get("ckpt_name")
            if isinstance(value, str) and value.strip():
                return value.strip()
        sidecar_checkpoint = metadata.get("checkpoint")
        if isinstance(sidecar_checkpoint, str) and sidecar_checkpoint.strip():
            return sidecar_checkpoint.strip()
        return "unknown"

    @staticmethod
    def _sampler_stages(
        graph_facts: dict[str, Any],
    ) -> tuple[LegacySamplerStageImport, ...]:
        raw = graph_facts.get("ksampler_stages")
        if not isinstance(raw, list):
            return ()
        stages: list[LegacySamplerStageImport] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            stages.append(
                LegacySamplerStageImport(
                    node_id=str(value.get("node_id") or ""),
                    stage_order=int(value.get("stage_order") or 0),
                    seed=LocalLegacyOutputImportSource._optional_int(
                        value.get("seed")
                    ),
                    steps=LocalLegacyOutputImportSource._optional_int(
                        value.get("steps")
                    ),
                    cfg=LocalLegacyOutputImportSource._optional_float(
                        value.get("cfg")
                    ),
                    sampler=LocalLegacyOutputImportSource._optional_text(
                        value.get("sampler")
                    ),
                    scheduler=LocalLegacyOutputImportSource._optional_text(
                        value.get("scheduler")
                    ),
                    denoise=LocalLegacyOutputImportSource._optional_float(
                        value.get("denoise")
                    ),
                )
            )
        return tuple(stages)

    @staticmethod
    def _normalized_loras(
        graph_facts: dict[str, Any],
    ) -> list[dict[str, Any]]:
        raw = graph_facts.get("loras")
        if not isinstance(raw, list):
            return []
        normalized: list[dict[str, Any]] = []
        for value in raw:
            if not isinstance(value, dict):
                continue
            normalized.append(
                {
                    "name": str(value.get("name") or ""),
                    "sm": value.get("strength_model"),
                    "sc": value.get("strength_clip"),
                    "node_id": str(value.get("node_id") or ""),
                    "class_type": str(value.get("class_type") or ""),
                }
            )
        return normalized

    @staticmethod
    def _model_branch(metadata: dict[str, Any], checkpoint: str) -> str:
        for key in (
            "model_branch",
            "model_base",
            "base_model",
            "model",
        ):
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        return Path(checkpoint).stem if checkpoint != "unknown" else "unknown"

    @staticmethod
    def _combo_key(
        checkpoint: str,
        first: LegacySamplerStageImport | None,
    ) -> str:
        if first is None:
            return f"ckpt={checkpoint}|legacy_graph"
        return (
            f"ckpt={checkpoint}"
            f"|sampler={first.sampler or ''}"
            f"|sched={first.scheduler or ''}"
            f"|steps={first.steps if first.steps is not None else ''}"
            f"|cfg={first.cfg if first.cfg is not None else ''}"
            f"|denoise={first.denoise if first.denoise is not None else ''}"
        )

    @staticmethod
    def _optional_text(value: object) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None or value == "":
            return None
        if not isinstance(value, (str, int, float)):
            raise LegacyOutputImportValidationError(
                "Sampler integer value is malformed"
            )
        return int(value)

    @staticmethod
    def _optional_float(value: object) -> float | None:
        if value is None or value == "":
            return None
        if not isinstance(value, (str, int, float)):
            raise LegacyOutputImportValidationError(
                "Sampler numeric value is malformed"
            )
        return float(value)
