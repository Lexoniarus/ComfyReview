"""Audit and recover explicit prompt content levels in a new database."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from comfyreview.application import ContentLevel, PromptContentLevelPolicy
from comfyreview.application.lora_effects import LoraGraphEffectPolicy
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_AUDIT_FORMAT = 2
_CURATION_FORMAT = 1
_LEVEL_ORDER = tuple(ContentLevel)


class ContentLevelRecoveryValidationError(ValueError):
    """Reject incomplete, stale, or inconsistent content-level evidence."""


@dataclass(frozen=True, slots=True)
class ContentLevelAuditResult:
    """Describe one read-only content-level recovery preview."""

    report_path: Path
    summary: dict[str, int]


@dataclass(frozen=True, slots=True)
class ContentLevelRecoveryResult:
    """Describe one validated recovered database."""

    output_path: Path
    updated_components: int
    reclassified_generations: int
    preserved_overrides: int
    removed_inactive_loras: int


class ContentLevelAuditor:
    """Bind a complete reviewed curation to one exact canonical database."""

    def __init__(self, database_path: Path, curation_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._curation_path = Path(curation_path).resolve()
        self._policy = PromptContentLevelPolicy()

    def audit(self, report_path: Path) -> ContentLevelAuditResult:
        """Validate all entries and write a hash-bound recovery preview."""
        CanonicalSchemaManager(self._database_path).validate()
        curation = self._load_curation()
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT component.component_uid, component.name, component.kind,
                       component.tags, revision.revision_uid,
                       revision.content_hash
                FROM prompt_components AS component
                JOIN prompt_revisions AS revision
                  ON revision.component_id = component.id
                WHERE revision.revision_number = (
                    SELECT MAX(candidate.revision_number)
                    FROM prompt_revisions AS candidate
                    WHERE candidate.component_id = component.id
                )
                ORDER BY component.component_uid
                """
            ).fetchall()
            curated = self._validate_curation(rows, curation)
            component_items = []
            old_component_levels: Counter[str] = Counter()
            new_component_levels: Counter[str] = Counter()
            for row in rows:
                uid = str(row["component_uid"])
                old_level = self._stored_level(row["tags"])
                new_level = curated[uid]
                old_component_levels[old_level.value] += 1
                new_component_levels[new_level.value] += 1
                component_items.append(
                    {
                        "component_uid": uid,
                        "old_content_level": old_level.value,
                        "new_content_level": new_level.value,
                    }
                )
            generation_items = self._generation_preview(connection, curated)
            override_count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM image_content_level_state"
                ).fetchone()[0]
            )
        finally:
            connection.close()

        old_generations = Counter(
            str(item["old_content_level"]) for item in generation_items
        )
        new_generations = Counter(
            str(item["new_content_level"]) for item in generation_items
        )
        summary = {
            "components": len(component_items),
            "changed_components": sum(
                item["old_content_level"] != item["new_content_level"]
                for item in component_items
            ),
            "generations": len(generation_items),
            "changed_generations": sum(
                item["old_content_level"] != item["new_content_level"]
                for item in generation_items
            ),
            "images": sum(
                int(item["image_count"]) for item in generation_items
            ),
            "manual_overrides": override_count,
            "inactive_lora_selections": sum(
                len(item["inactive_lora_positions"])
                for item in generation_items
            ),
        }
        payload: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "canonical_database": str(self._database_path),
            "canonical_sha256": _file_sha256(self._database_path),
            "curation": {
                "path": str(self._curation_path),
                "sha256": _file_sha256(self._curation_path),
            },
            "summary": summary,
            "component_counts": {
                "old": dict(sorted(old_component_levels.items())),
                "new": dict(sorted(new_component_levels.items())),
            },
            "generation_counts": {
                "old": dict(sorted(old_generations.items())),
                "new": dict(sorted(new_generations.items())),
            },
            "components": component_items,
            "generations": generation_items,
        }
        payload["audit_sha256"] = _payload_sha256(payload)
        destination = Path(report_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
        return ContentLevelAuditResult(destination, summary)

    def _load_curation(self) -> dict[str, Any]:
        try:
            payload = json.loads(
                self._curation_path.read_text(encoding="utf-8")
            )
        except (OSError, json.JSONDecodeError) as error:
            raise ContentLevelRecoveryValidationError(
                "Content-level curation is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("format_version") != _CURATION_FORMAT
            or not isinstance(payload.get("components"), list)
        ):
            raise ContentLevelRecoveryValidationError(
                "Unsupported content-level curation format"
            )
        return payload

    @staticmethod
    def _validate_curation(
        rows: list[sqlite3.Row], payload: dict[str, Any]
    ) -> dict[str, ContentLevel]:
        expected = {
            str(row["component_uid"]): (
                str(row["revision_uid"]),
                str(row["content_hash"]),
            )
            for row in rows
        }
        curated: dict[str, ContentLevel] = {}
        for raw in payload["components"]:
            if not isinstance(raw, dict):
                raise ContentLevelRecoveryValidationError(
                    "Content-level curation entry is invalid"
                )
            uid = str(raw.get("component_uid") or "").strip()
            if not uid or uid in curated:
                raise ContentLevelRecoveryValidationError(
                    "Content-level curation contains duplicate identities"
                )
            if uid not in expected:
                raise ContentLevelRecoveryValidationError(
                    f"Unknown curated component: {uid}"
                )
            revision_uid, content_hash = expected[uid]
            if (
                raw.get("revision_uid") != revision_uid
                or raw.get("content_hash") != content_hash
            ):
                raise ContentLevelRecoveryValidationError(
                    f"Stale curated component revision: {uid}"
                )
            try:
                curated[uid] = ContentLevel(str(raw.get("content_level")))
            except ValueError as error:
                raise ContentLevelRecoveryValidationError(
                    f"Invalid content level for component: {uid}"
                ) from error
        missing = sorted(set(expected) - set(curated))
        if missing:
            raise ContentLevelRecoveryValidationError(
                f"Content-level curation is incomplete: {len(missing)} missing"
            )
        return curated

    def _stored_level(self, payload: object) -> ContentLevel:
        try:
            raw = json.loads(str(payload or "[]"))
        except json.JSONDecodeError:
            raw = []
        tags = (
            tuple(str(item) for item in raw) if isinstance(raw, list) else ()
        )
        return self._policy.read(tags).content_level

    @staticmethod
    def _generation_preview(
        connection: sqlite3.Connection,
        curated: dict[str, ContentLevel],
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for row in connection.execute(
            """
            SELECT generation.id, generation.generation_uid,
                   generation.inferred_content_level,
                   generation.raw_metadata_json,
                   generation.workflow_json,
                   generation.loras_json,
                   COUNT(DISTINCT image.id) AS image_count
            FROM generations AS generation
            LEFT JOIN images AS image
              ON image.generation_id = generation.id
             AND image.deleted_at IS NULL
            GROUP BY generation.id
            ORDER BY generation.id
            """
        ):
            inactive_positions = _inactive_lora_positions(row)
            levels = [ContentLevel.STANDARD]
            levels.extend(
                curated[str(member[0])]
                for member in connection.execute(
                    """
                    SELECT component.component_uid
                    FROM prompt_composition_revisions AS membership
                    JOIN prompt_revisions AS revision
                      ON revision.id = membership.revision_id
                    JOIN prompt_components AS component
                      ON component.id = revision.component_id
                    JOIN generations AS generation
                      ON generation.prompt_composition_id = membership.composition_id
                    WHERE generation.id = ?
                    """,
                    (int(row["id"]),),
                )
            )
            lora_statement = (
                "SELECT content_level_snapshot FROM generation_loras "
                "WHERE generation_id = ? "
            )
            if inactive_positions:
                placeholders = ", ".join(
                    "?" for _position in inactive_positions
                )
                lora_statement += f"AND position NOT IN ({placeholders}) "
            lora_statement += "AND content_level_snapshot IS NOT NULL"
            levels.extend(
                ContentLevel(str(selection[0]))
                for selection in connection.execute(
                    lora_statement,
                    (int(row["id"]), *inactive_positions),
                )
            )
            level = max(levels, key=_LEVEL_ORDER.index)
            items.append(
                {
                    "generation_uid": str(row["generation_uid"]),
                    "old_content_level": str(row["inferred_content_level"]),
                    "new_content_level": level.value,
                    "image_count": int(row["image_count"]),
                    "inactive_lora_positions": list(inactive_positions),
                }
            )
        return items


class ContentLevelRecovery:
    """Apply an audited curation to a newly copied canonical database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._policy = PromptContentLevelPolicy()

    def recover(
        self, report_path: Path, output_path: Path
    ) -> ContentLevelRecoveryResult:
        """Create and validate an output database without mutating the source."""
        payload = self._load_report(report_path)
        destination = Path(output_path).resolve()
        if destination == self._database_path:
            raise ContentLevelRecoveryValidationError(
                "Recovery output must differ from the source database"
            )
        if destination.exists():
            raise ContentLevelRecoveryValidationError(
                "Recovery output database already exists"
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.tmp")
        source = connect_read_only(self._database_path)
        target = sqlite3.connect(temporary)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        try:
            connection = connect_existing(temporary, rows=True)
            try:
                connection.execute("BEGIN IMMEDIATE")
                updated = self._update_components(
                    connection, payload["components"]
                )
                changed, removed_loras = self._update_generations(
                    connection, payload["generations"]
                )
                overrides = int(
                    connection.execute(
                        "SELECT COUNT(*) FROM image_content_level_state"
                    ).fetchone()[0]
                )
                if overrides != int(payload["summary"]["manual_overrides"]):
                    raise ContentLevelRecoveryValidationError(
                        "Manual image overrides changed during recovery"
                    )
                connection.commit()
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            CanonicalSchemaManager(temporary).validate()
            os.replace(temporary, destination)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return ContentLevelRecoveryResult(
            destination, updated, changed, overrides, removed_loras
        )

    def _load_report(self, report_path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ContentLevelRecoveryValidationError(
                "Content-level audit is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("format_version") != _AUDIT_FORMAT
            or not isinstance(payload.get("components"), list)
            or not isinstance(payload.get("generations"), list)
        ):
            raise ContentLevelRecoveryValidationError(
                "Unsupported content-level audit format"
            )
        if payload.get("audit_sha256") != _payload_sha256(payload):
            raise ContentLevelRecoveryValidationError(
                "Content-level audit checksum mismatch"
            )
        if Path(str(payload.get("canonical_database") or "")).resolve() != (
            self._database_path
        ):
            raise ContentLevelRecoveryValidationError(
                "Content-level audit database mismatch"
            )
        if payload.get("canonical_sha256") != _file_sha256(
            self._database_path
        ):
            raise ContentLevelRecoveryValidationError(
                "Canonical database changed after content-level audit"
            )
        curation = payload.get("curation")
        if not isinstance(curation, dict):
            raise ContentLevelRecoveryValidationError(
                "Content-level audit curation binding is missing"
            )
        curation_path = Path(str(curation.get("path") or ""))
        if curation.get("sha256") != _file_sha256(curation_path):
            raise ContentLevelRecoveryValidationError(
                "Content-level curation changed after audit"
            )
        return payload

    def _update_components(
        self, connection: sqlite3.Connection, items: list[dict[str, Any]]
    ) -> int:
        updated = 0
        for item in items:
            row = connection.execute(
                "SELECT tags FROM prompt_components WHERE component_uid = ?",
                (str(item["component_uid"]),),
            ).fetchone()
            if row is None:
                raise ContentLevelRecoveryValidationError(
                    "Curated prompt component disappeared"
                )
            try:
                raw = json.loads(str(row["tags"] or "[]"))
            except json.JSONDecodeError:
                raw = []
            tags = (
                tuple(str(value) for value in raw)
                if isinstance(raw, list)
                else ()
            )
            stored = self._policy.write(
                tags, ContentLevel(str(item["new_content_level"]))
            )
            connection.execute(
                "UPDATE prompt_components SET tags = ?, "
                "updated_at = datetime('now') WHERE component_uid = ?",
                (
                    json.dumps(
                        stored, ensure_ascii=False, separators=(",", ":")
                    ),
                    str(item["component_uid"]),
                ),
            )
            updated += 1
        return updated

    @staticmethod
    def _update_generations(
        connection: sqlite3.Connection, items: list[dict[str, Any]]
    ) -> tuple[int, int]:
        changed = 0
        removed_loras = 0
        for item in items:
            old_level = str(item["old_content_level"])
            new_level = str(item["new_content_level"])
            if old_level != new_level:
                changed += 1
            cursor = connection.execute(
                "UPDATE generations SET inferred_content_level = ? "
                "WHERE generation_uid = ? AND inferred_content_level = ?",
                (new_level, str(item["generation_uid"]), old_level),
            )
            if cursor.rowcount != 1:
                raise ContentLevelRecoveryValidationError(
                    "Generation classification changed after audit"
                )
            positions = tuple(
                int(position)
                for position in item.get("inactive_lora_positions", [])
            )
            if positions:
                generation = connection.execute(
                    "SELECT id FROM generations WHERE generation_uid = ?",
                    (str(item["generation_uid"]),),
                ).fetchone()
                if generation is None:
                    raise ContentLevelRecoveryValidationError(
                        "Generation disappeared after audit"
                    )
                placeholders = ", ".join("?" for _position in positions)
                deleted = connection.execute(
                    "DELETE FROM generation_loras WHERE generation_id = ? "
                    f"AND position IN ({placeholders})",
                    (int(generation["id"]), *positions),
                )
                if deleted.rowcount != len(positions):
                    raise ContentLevelRecoveryValidationError(
                        "Effective LoRA usage changed after audit"
                    )
                removed_loras += deleted.rowcount
        return changed, removed_loras


def _inactive_lora_positions(row: sqlite3.Row) -> tuple[int, ...]:
    graph = _generation_graph(row)
    if graph is None:
        return ()
    effective_node_ids = {
        effect.node_id for effect in LoraGraphEffectPolicy().effects(graph)
    }
    try:
        selections = json.loads(str(row["loras_json"] or "[]"))
    except json.JSONDecodeError:
        return ()
    if not isinstance(selections, list):
        return ()
    inactive: list[int] = []
    for position, selection in enumerate(selections):
        if not isinstance(selection, dict):
            continue
        node_id = str(selection.get("node_id") or "").strip()
        if node_id and node_id not in effective_node_ids:
            inactive.append(position)
    return tuple(inactive)


def _generation_graph(row: sqlite3.Row) -> dict[str, Any] | None:
    try:
        metadata = json.loads(str(row["raw_metadata_json"] or "{}"))
    except json.JSONDecodeError:
        metadata = {}
    if isinstance(metadata, dict):
        graph = metadata.get("comfy_prompt_graph")
        if not isinstance(graph, dict):
            graph = metadata.get("prompt_graph")
        if isinstance(graph, dict):
            return graph
    try:
        graph = json.loads(str(row["workflow_json"] or "{}"))
    except json.JSONDecodeError:
        return None
    return graph if isinstance(graph, dict) else None


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: dict[str, Any]) -> str:
    normalized = {
        key: value for key, value in payload.items() if key != "audit_sha256"
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
