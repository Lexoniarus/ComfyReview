"""Audit and rebuild the normalized prompt catalog in a new database."""

from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import tempfile
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import CanonicalSchemaManager

_AUDIT_FORMAT = 1
_MAPPING_FORMAT = 1
_TARGET_KINDS = (
    "character",
    "scene",
    "atmosphere",
    "lighting",
    "outfit",
    "accessory",
    "pose",
    "expression",
    "framing",
    "camera_angle",
    "optical_effect",
)
_CONTENT_LEVELS = ("standard", "sexy", "lewd", "nude", "explicit")


class CatalogNormalizationValidationError(ValueError):
    """Reject incomplete, stale, or inconsistent normalization inputs."""


@dataclass(frozen=True, slots=True)
class CatalogNormalizationAuditResult:
    """Describe one source-bound catalog audit and mapping draft."""

    report_path: Path
    mapping_path: Path
    summary: dict[str, int]


class CatalogNormalizationAuditor:
    """Inventory catalog and image prompt facts without mutating the source."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def audit(
        self,
        report_path: Path,
        mapping_path: Path,
    ) -> CatalogNormalizationAuditResult:
        """Write an immutable audit report and an editable mapping draft."""
        report_destination = Path(report_path).resolve()
        mapping_destination = Path(mapping_path).resolve()
        if mapping_destination.exists():
            raise CatalogNormalizationValidationError(
                "Catalog normalization mapping already exists"
            )
        source_hash = logical_database_sha256(self._database_path)
        with upgraded_snapshot(self._database_path) as snapshot:
            connection = _open_read_only(snapshot)
            try:
                components = self._component_inventory(connection)
                images = self._image_inventory(connection)
                summary = self._summary(connection, components, images)
                character_fingerprint = self._character_fingerprint(connection)
            finally:
                connection.close()

        report: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "source_database": str(self._database_path),
            "source_database_sha256": source_hash,
            "summary": summary,
            "character_fingerprint": character_fingerprint,
            "components": components,
            "images": images,
        }
        report["audit_sha256"] = payload_sha256(report, "audit_sha256")
        mapping = self._mapping_draft(report)
        _write_json_atomic(report_destination, report)
        _write_json_atomic(mapping_destination, mapping)
        return CatalogNormalizationAuditResult(
            report_destination,
            mapping_destination,
            summary,
        )

    @staticmethod
    def _component_inventory(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        components: list[dict[str, Any]] = []
        rows = connection.execute(
            """
            SELECT id, component_uid, kind, component_key, name,
                   tags, notes, archived_at
            FROM prompt_components
            ORDER BY CASE kind WHEN 'character' THEN 0 ELSE 1 END,
                     kind, name, component_uid
            """
        ).fetchall()
        for row in rows:
            revisions: list[dict[str, Any]] = []
            for revision in connection.execute(
                """
                SELECT id, revision_uid, revision_number,
                       positive_text, negative_text, content_hash
                FROM prompt_revisions
                WHERE component_id = ?
                ORDER BY revision_number
                """,
                (int(row["id"]),),
            ):
                atoms = [
                    {
                        "scope": str(atom["scope"]),
                        "position": int(atom["position"]),
                        "text": str(atom["canonical_text"]),
                        "weight_milli": int(atom["weight_milli"]),
                    }
                    for atom in connection.execute(
                        """
                        SELECT usage.scope, usage.position,
                               atom.canonical_text, usage.weight_milli
                        FROM prompt_revision_atom_usages AS usage
                        JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                        WHERE usage.revision_id = ?
                        ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                                 usage.position
                        """,
                        (int(revision["id"]),),
                    )
                ]
                revisions.append(
                    {
                        "revision_uid": str(revision["revision_uid"]),
                        "revision_number": int(revision["revision_number"]),
                        "positive_text": str(revision["positive_text"]),
                        "negative_text": str(revision["negative_text"]),
                        "content_hash": str(revision["content_hash"]),
                        "atoms": atoms,
                    }
                )
            components.append(
                {
                    "component_uid": str(row["component_uid"]),
                    "kind": str(row["kind"]),
                    "component_key": str(row["component_key"]),
                    "name": str(row["name"]),
                    "tags": _json_list(row["tags"]),
                    "notes": str(row["notes"] or ""),
                    "archived": row["archived_at"] is not None,
                    "revisions": revisions,
                }
            )
        return components

    @staticmethod
    def _image_inventory(
        connection: sqlite3.Connection,
    ) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        rows = connection.execute(
            """
            SELECT image.id, image.image_uid, image.png_path,
                   image.deleted_at, generation.generation_uid,
                   positive.text AS positive_prompt,
                   negative.text AS negative_prompt
            FROM images AS image
            JOIN generations AS generation ON generation.id = image.generation_id
            JOIN prompts AS positive ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative ON negative.id = generation.negative_prompt_id
            ORDER BY image.id
            """
        ).fetchall()
        for row in rows:
            revision_rows = connection.execute(
                """
                SELECT revision.revision_uid, component.kind,
                       component.component_uid
                FROM current_image_catalog_compositions AS current_catalog
                JOIN image_catalog_composition_revisions AS membership
                  ON membership.composition_id = current_catalog.composition_id
                JOIN prompt_revisions AS revision
                  ON revision.id = membership.revision_id
                JOIN prompt_components AS component
                  ON component.id = revision.component_id
                WHERE current_catalog.image_id = ?
                ORDER BY membership.position
                """,
                (int(row["id"]),),
            ).fetchall()
            items.append(
                {
                    "image_uid": str(row["image_uid"]),
                    "generation_uid": str(row["generation_uid"]),
                    "png_path": str(row["png_path"]),
                    "deleted": row["deleted_at"] is not None,
                    "positive_prompt": str(row["positive_prompt"]),
                    "negative_prompt": str(row["negative_prompt"]),
                    "current_composition": [
                        {
                            "revision_uid": str(item["revision_uid"]),
                            "component_uid": str(item["component_uid"]),
                            "kind": str(item["kind"]),
                        }
                        for item in revision_rows
                    ],
                }
            )
        return items

    @staticmethod
    def _summary(
        connection: sqlite3.Connection,
        components: list[dict[str, Any]],
        images: list[dict[str, Any]],
    ) -> dict[str, int]:
        kinds = Counter(str(item["kind"]) for item in components)
        live_images = [item for item in images if not bool(item["deleted"])]
        unresolved_images = sum(
            not item["current_composition"]
            or any(
                member["kind"] not in _TARGET_KINDS
                for member in item["current_composition"]
            )
            for item in live_images
        )
        return {
            "components": len(components),
            "character_components": kinds["character"],
            "non_character_components": len(components) - kinds["character"],
            "modifier_components": kinds["modifier"],
            "live_images": len(live_images),
            "deleted_images": len(images) - len(live_images),
            "unresolved_live_images": unresolved_images,
            "review_events": int(
                connection.execute(
                    "SELECT COUNT(*) FROM review_events"
                ).fetchone()[0]
            ),
            "arena_matches": int(
                connection.execute(
                    "SELECT COUNT(*) FROM arena_matches"
                ).fetchone()[0]
            ),
            "curation_assignments": int(
                connection.execute(
                    "SELECT COUNT(*) FROM curation_assignments"
                ).fetchone()[0]
            ),
        }

    @staticmethod
    def _character_fingerprint(
        connection: sqlite3.Connection,
    ) -> dict[str, Any]:
        payload = CatalogNormalizationAuditor._component_inventory(connection)
        characters = [item for item in payload if item["kind"] == "character"]
        selected = {
            str(row["component_uid"]): str(row["revision_uid"])
            for row in connection.execute(
                """
                SELECT component.component_uid, revision.revision_uid
                FROM prompt_components AS component
                JOIN prompt_component_promotions AS promotion
                  ON promotion.id = (
                      SELECT candidate.id
                      FROM prompt_component_promotions AS candidate
                      WHERE candidate.component_id = component.id
                      ORDER BY candidate.id DESC LIMIT 1
                  )
                JOIN prompt_revisions AS revision
                  ON revision.id = promotion.revision_id
                WHERE component.kind = 'character'
                ORDER BY component.component_uid
                """
            )
        }
        aiko_revision_counts = {
            str(item["component_uid"]): len(item["revisions"])
            for item in characters
            if "aiko" in str(item["name"]).casefold()
            or "aiko" in str(item["component_key"]).casefold()
        }
        normalized = json.dumps(
            {"components": characters, "selected_revisions": selected},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            "sha256": hashlib.sha256(normalized).hexdigest(),
            "component_count": len(characters),
            "revision_count": sum(
                len(item["revisions"]) for item in characters
            ),
            "selected_revisions": selected,
            "aiko_revision_counts": aiko_revision_counts,
        }

    @staticmethod
    def _mapping_draft(report: dict[str, Any]) -> dict[str, Any]:
        source_components = []
        revision_kinds: dict[str, str] = {}
        for component in report["components"]:
            kind = str(component["kind"])
            for revision in component["revisions"]:
                revision_kinds[str(revision["revision_uid"])] = kind
            if kind == "character":
                continue
            ready = kind in _TARGET_KINDS
            source_components.append(
                {
                    "source_component_uid": component["component_uid"],
                    "action": "keep" if ready else "review",
                    "target_component_uids": (
                        [component["component_uid"]] if ready else []
                    ),
                    "reviewed": False,
                }
            )
        image_compositions = []
        for image in report["images"]:
            if image["deleted"]:
                continue
            revision_uids = [
                str(item["revision_uid"])
                for item in image["current_composition"]
                if revision_kinds.get(str(item["revision_uid"]))
                in _TARGET_KINDS
            ]
            image_compositions.append(
                {
                    "image_uid": image["image_uid"],
                    "revision_uids": revision_uids,
                    "reviewed": False,
                }
            )
        policies = [
            {
                "policy_uid": "global-quality-v1",
                "policy_key": "quality",
                "policy_type": "quality",
                "revision_number": 1,
                "name": "Global quality",
                "content_level": None,
                "atoms": [],
            }
        ]
        policies.extend(
            {
                "policy_uid": f"content-profile-{level}-v1",
                "policy_key": f"content-profile-{level}",
                "policy_type": "content_profile",
                "revision_number": 1,
                "name": f"Content profile {level}",
                "content_level": level,
                "atoms": [],
            }
            for level in _CONTENT_LEVELS
        )
        mapping: dict[str, Any] = {
            "format_version": _MAPPING_FORMAT,
            "audit_sha256": report["audit_sha256"],
            "source_database_sha256": report["source_database_sha256"],
            "complete": False,
            "source_components": source_components,
            "target_components": [],
            "image_compositions": image_compositions,
            "global_policies": policies,
        }
        mapping["mapping_sha256"] = payload_sha256(mapping, "mapping_sha256")
        return mapping


def logical_database_sha256(database_path: Path) -> str:
    """Hash one transactionally consistent logical SQLite snapshot."""
    connection = _open_read_only(Path(database_path).resolve())
    try:
        connection.execute("BEGIN")
        digest = hashlib.sha256()
        for statement in connection.iterdump():
            digest.update(statement.encode("utf-8"))
            digest.update(b"\n")
        connection.rollback()
        return digest.hexdigest()
    finally:
        connection.close()


@contextmanager
def upgraded_snapshot(database_path: Path) -> Iterator[Path]:
    """Yield a current-schema temporary copy without creating a backup."""
    source_path = Path(database_path).resolve()
    if not source_path.is_file():
        raise CatalogNormalizationValidationError(
            f"Canonical database does not exist: {source_path}"
        )
    with tempfile.TemporaryDirectory(
        prefix="comfyreview-catalog-audit-"
    ) as raw:
        snapshot = Path(raw) / "catalog-audit.sqlite3"
        source = _open_read_only(source_path)
        target = sqlite3.connect(snapshot)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        CanonicalSchemaManager(snapshot).upgrade(create_backup=False)
        CanonicalSchemaManager(snapshot).validate()
        yield snapshot


def payload_sha256(payload: dict[str, Any], checksum_key: str) -> str:
    """Hash a JSON payload while excluding its own checksum field."""
    normalized = {
        key: value for key, value in payload.items() if key != checksum_key
    }
    encoded = json.dumps(
        normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _json_list(value: object) -> list[str]:
    try:
        payload = json.loads(str(value or "[]"))
    except json.JSONDecodeError:
        return []
    return [str(item) for item in payload] if isinstance(payload, list) else []


def _open_read_only(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    os.replace(temporary, path)
