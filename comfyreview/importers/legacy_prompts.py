"""Audited import of legacy Playground items into the canonical catalog."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import uuid4

from comfyreview.application import (
    imported_prompt_component_uid,
    prompt_revision_identity,
)
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_AUDIT_FORMAT = 1
_SOURCE = "legacy_playground"


class LegacyPromptImportValidationError(ValueError):
    """Reject stale, manipulated or incompatible prompt import input."""


class LegacyPromptImportRecoveryError(RuntimeError):
    """Report an import failure whose backup recovery also failed."""


@dataclass(frozen=True, slots=True)
class LegacyPromptAuditResult:
    """Describe one immutable legacy prompt audit snapshot."""

    report_path: Path
    item_count: int


@dataclass(frozen=True, slots=True)
class LegacyPromptImportResult:
    """Describe one committed canonical prompt import."""

    created_components: int
    created_revisions: int
    updated_components: int
    backup_path: Path


class LegacyPromptAuditor:
    """Read legacy Playground items and write a hash-bound report."""

    def __init__(
        self,
        *,
        source_database_path: Path,
        canonical_database_path: Path,
    ) -> None:
        self._source_path = Path(source_database_path).resolve()
        self._canonical_path = Path(canonical_database_path).resolve()

    def audit(self, report_path: Path) -> LegacyPromptAuditResult:
        """Write a deterministic audit without mutating either database."""
        items = self._read_items()
        payload: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "source_database": str(self._source_path),
            "source_sha256": _file_sha256(self._source_path),
            "canonical_database": str(self._canonical_path),
            "canonical_sha256": _file_sha256(self._canonical_path),
            "summary": {"items": len(items)},
            "items": items,
        }
        payload["audit_sha256"] = _payload_sha256(payload)
        destination = Path(report_path).resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(
            f".{destination.name}.{uuid4().hex}.tmp"
        )
        try:
            temporary.write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)
        return LegacyPromptAuditResult(destination, len(items))

    def _read_items(self) -> list[dict[str, Any]]:
        connection = connect_read_only(self._source_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT id, kind, name, key, tags, pos, neg, notes,
                       created_at, updated_at
                FROM playground_items
                ORDER BY id
                """
            ).fetchall()
            return [{key: row[key] for key in row.keys()} for row in rows]
        finally:
            connection.close()


class LegacyPromptImporter:
    """Validate an audit and import all items in one canonical transaction."""

    def __init__(
        self,
        *,
        source_database_path: Path,
        canonical_database_path: Path,
    ) -> None:
        self._source_path = Path(source_database_path).resolve()
        self._canonical_path = Path(canonical_database_path).resolve()

    def import_report(
        self,
        report_path: Path,
        *,
        backup_directory: Path | None = None,
    ) -> LegacyPromptImportResult:
        """Import a current audit after creating a canonical backup."""
        payload = self._load_and_validate_report(report_path)
        items = payload["items"]
        backup_path = self._create_backup(backup_directory)
        connection = connect_existing(self._canonical_path, rows=True)
        commit_attempted = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            counts = [0, 0, 0]
            for item in items:
                self._import_item(connection, item, counts)
            commit_attempted = True
            connection.commit()
        except Exception as error:
            connection.rollback()
            connection.close()
            if commit_attempted or not self._canonical_is_valid():
                self._restore_after_failure(backup_path, error)
            raise
        else:
            connection.close()
        try:
            CanonicalSchemaManager(self._canonical_path).validate()
        except Exception as error:
            self._restore_after_failure(backup_path, error)
            raise
        return LegacyPromptImportResult(
            created_components=counts[0],
            created_revisions=counts[1],
            updated_components=counts[2],
            backup_path=backup_path,
        )

    def _canonical_is_valid(self) -> bool:
        try:
            CanonicalSchemaManager(self._canonical_path).validate()
        except Exception:
            return False
        return True

    def _restore_after_failure(
        self,
        backup_path: Path,
        original_error: Exception,
    ) -> None:
        try:
            shutil.copy2(backup_path, self._canonical_path)
            CanonicalSchemaManager(self._canonical_path).validate()
        except Exception as recovery_error:
            raise LegacyPromptImportRecoveryError(
                "Legacy prompt import failed and backup recovery did not "
                f"restore a valid canonical database: {recovery_error}"
            ) from original_error

    def _load_and_validate_report(self, report_path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LegacyPromptImportValidationError(
                "Legacy prompt audit is unreadable"
            ) from error
        if not isinstance(payload, dict) or payload.get("format_version") != 1:
            raise LegacyPromptImportValidationError(
                "Unsupported legacy prompt audit format"
            )
        expected_checksum = str(payload.get("audit_sha256") or "")
        if expected_checksum != _payload_sha256(payload):
            raise LegacyPromptImportValidationError(
                "Legacy prompt audit checksum mismatch"
            )
        expected_paths = {
            "source_database": self._source_path,
            "canonical_database": self._canonical_path,
        }
        for field, expected in expected_paths.items():
            if Path(str(payload.get(field) or "")).resolve() != expected:
                raise LegacyPromptImportValidationError(
                    f"Legacy prompt audit {field} mismatch"
                )
        if payload.get("source_sha256") != _file_sha256(self._source_path):
            raise LegacyPromptImportValidationError(
                "Legacy prompt source changed after audit"
            )
        if payload.get("canonical_sha256") != _file_sha256(
            self._canonical_path
        ):
            raise LegacyPromptImportValidationError(
                "Canonical database changed after prompt audit"
            )
        items = payload.get("items")
        summary = payload.get("summary")
        if (
            not isinstance(items, list)
            or not isinstance(summary, dict)
            or summary.get("items") != len(items)
            or any(not isinstance(item, dict) for item in items)
        ):
            raise LegacyPromptImportValidationError(
                "Legacy prompt audit item summary mismatch"
            )
        return payload

    def _import_item(
        self,
        connection: sqlite3.Connection,
        item: dict[str, Any],
        counts: list[int],
    ) -> None:
        source_key = str(int(item["id"]))
        component_uid = imported_prompt_component_uid(_SOURCE, source_key)
        positive_text = str(item.get("pos") or "").strip()
        negative_text = str(item.get("neg") or "").strip()
        if not positive_text and not negative_text:
            raise LegacyPromptImportValidationError(
                f"Legacy prompt item {source_key} has no prompt content"
            )
        mapped = connection.execute(
            """
            SELECT component.component_uid
            FROM legacy_prompt_component_sources AS source
            JOIN prompt_components AS component
                ON component.id = source.component_id
            WHERE source.source = ? AND source.source_key = ?
            """,
            (_SOURCE, source_key),
        ).fetchone()
        if (
            mapped is not None
            and str(mapped["component_uid"]) != component_uid
        ):
            raise LegacyPromptImportValidationError(
                f"Legacy prompt identity conflict for item {source_key}"
            )
        component_id = self._upsert_component(
            connection,
            item,
            component_uid=component_uid,
            source_key=source_key,
            exists=mapped is not None,
        )
        counts[2 if mapped is not None else 0] += 1
        if self._insert_revision(
            connection,
            component_id=component_id,
            component_uid=component_uid,
            positive_text=positive_text,
            negative_text=negative_text,
            created_at=str(
                item.get("updated_at") or item.get("created_at") or ""
            ),
        ):
            counts[1] += 1

    @staticmethod
    def _upsert_component(
        connection: sqlite3.Connection,
        item: dict[str, Any],
        *,
        component_uid: str,
        source_key: str,
        exists: bool,
    ) -> int:
        tags = _legacy_tags(str(item.get("tags") or ""))
        values = (
            str(item.get("kind") or "").strip(),
            str(item.get("key") or "").strip(),
            str(item.get("name") or "").strip(),
            json.dumps(tags, ensure_ascii=False, separators=(",", ":")),
            str(item.get("notes") or "").strip(),
        )
        if exists:
            connection.execute(
                """
                UPDATE prompt_components
                SET kind = ?, component_key = ?, name = ?, tags = ?, notes = ?,
                    updated_at = datetime('now')
                WHERE component_uid = ?
                """,
                (*values, component_uid),
            )
        else:
            connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    component_uid,
                    *values,
                    str(item.get("created_at") or ""),
                    str(item.get("updated_at") or ""),
                ),
            )
        row = connection.execute(
            "SELECT id FROM prompt_components WHERE component_uid = ?",
            (component_uid,),
        ).fetchone()
        if row is None:
            raise LegacyPromptImportValidationError(
                f"Could not persist legacy prompt item {source_key}"
            )
        component_id = int(row["id"])
        connection.execute(
            """
            INSERT OR IGNORE INTO legacy_prompt_component_sources(
                component_id, source, source_key
            ) VALUES (?, ?, ?)
            """,
            (component_id, _SOURCE, source_key),
        )
        return component_id

    @staticmethod
    def _insert_revision(
        connection: sqlite3.Connection,
        *,
        component_id: int,
        component_uid: str,
        positive_text: str,
        negative_text: str,
        created_at: str,
    ) -> bool:
        revision_uid, content_hash = prompt_revision_identity(
            component_uid,
            positive_text,
            negative_text,
        )
        existing = connection.execute(
            "SELECT 1 FROM prompt_revisions "
            "WHERE component_id = ? AND content_hash = ?",
            (component_id, content_hash),
        ).fetchone()
        if existing is not None:
            return False
        number = int(
            connection.execute(
                "SELECT COALESCE(MAX(revision_number), 0) + 1 "
                "FROM prompt_revisions WHERE component_id = ?",
                (component_id,),
            ).fetchone()[0]
        )
        cursor = connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                revision_uid,
                component_id,
                number,
                positive_text,
                negative_text,
                content_hash,
                created_at,
            ),
        )
        revision_id = int(cursor.lastrowid or 0)
        for scope, snapshot in (
            ("pos", positive_text),
            ("neg", negative_text),
        ):
            for position, usage in enumerate(
                prompt_atom_usages_from_text(snapshot)
            ):
                connection.execute(
                    "INSERT OR IGNORE INTO prompt_atoms(canonical_text) "
                    "VALUES (?)",
                    (usage.text,),
                )
                atom = connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (usage.text,),
                ).fetchone()
                connection.execute(
                    """
                    INSERT INTO prompt_revision_atom_usages(
                        revision_id, atom_id, scope, position, weight_milli
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        revision_id,
                        int(atom[0]),
                        scope,
                        position,
                        usage.weight_milli,
                    ),
                )
        return True

    def _create_backup(self, backup_directory: Path | None) -> Path:
        root = (
            Path(backup_directory).resolve()
            if backup_directory is not None
            else self._canonical_path.parent / "backups"
        )
        root.mkdir(parents=True, exist_ok=True)
        destination = root / (
            f"{self._canonical_path.stem}.legacy-prompts.{uuid4().hex}.sqlite3"
        )
        source = connect_read_only(self._canonical_path)
        target = sqlite3.connect(destination)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        return destination


def _legacy_tags(value: str) -> tuple[str, ...]:
    normalized = value.replace(";", ",")
    return tuple(
        dict.fromkeys(
            tag
            for raw_tag in normalized.split(",")
            if (tag := raw_tag.strip())
        )
    )


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _payload_sha256(payload: dict[str, Any]) -> str:
    canonical = dict(payload)
    canonical.pop("audit_sha256", None)
    encoded = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(encoded).hexdigest()
