"""Audited completion of historical canonical prompt compositions."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from comfyreview.application import (
    PromptComponent,
    PromptCompositionMembership,
    PromptRenderer,
    PromptRevision,
    PromptSelection,
    prompt_composition_identity,
)
from comfyreview.domain import parse_prompt_atoms
from comfyreview.repositories.sqlite import CanonicalSchemaManager
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)

_AUDIT_FORMAT = 2
_LEGACY_SOURCE = "legacy_playground"
_SLOT_ORDER = (
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
)
_CLASSIFICATIONS = (
    "already_exact",
    "exactly_reconstructable",
    "reconstructable_with_draft_override",
    "ambiguous",
    "insufficient_evidence",
    "conflict",
)


class LegacyCompositionValidationError(ValueError):
    """Reject stale, manipulated or inconsistent composition evidence."""


class LegacyCompositionRecoveryError(RuntimeError):
    """Report an import failure whose backup recovery also failed."""


@dataclass(frozen=True, slots=True)
class LegacyCompositionAuditResult:
    """Describe one immutable historical-composition audit snapshot."""

    report_path: Path
    summary: dict[str, int]


@dataclass(frozen=True, slots=True)
class LegacyCompositionImportResult:
    """Describe one committed historical-composition completion."""

    linked_generations: int
    already_exact: int
    backup_path: Path


@dataclass(frozen=True, slots=True)
class _GenerationEvidence:
    generation_uid: str
    positive_text: str
    negative_text: str
    raw_metadata_json: str | None
    composition_id: int | None


@dataclass(frozen=True, slots=True)
class _StoredComposition:
    composition_uid: str
    components: tuple[PromptComponent, ...]
    memberships: tuple[PromptCompositionMembership, ...]


@dataclass(frozen=True, slots=True)
class _Reconstruction:
    components: tuple[PromptComponent, ...]
    ambiguous_slot: str | None = None


class HistoricalCompositionReconstructor:
    """Find uniquely evidenced catalog memberships in old prompt snapshots."""

    def __init__(
        self,
        *,
        renderer: PromptRenderer,
        components: tuple[PromptComponent, ...],
    ) -> None:
        self._renderer = renderer
        grouped: dict[str, list[PromptComponent]] = {}
        for component in components:
            grouped.setdefault(component.kind, []).append(component)
        self._components_by_kind = {
            kind: tuple(
                sorted(
                    values,
                    key=lambda component: (
                        component.component_uid,
                        component.latest_revision.revision_uid,
                    ),
                )
            )
            for kind, values in grouped.items()
        }

    def reconstruct(
        self,
        positive_text: str,
        negative_text: str,
    ) -> _Reconstruction:
        """Return ordered unique memberships and any ambiguous slot."""
        selected: list[PromptComponent] = []
        for kind in _SLOT_ORDER:
            matches = tuple(
                component
                for component in self._components_by_kind.get(kind, ())
                if _component_matches_snapshots(
                    component,
                    positive_text=positive_text,
                    negative_text=negative_text,
                )
            )
            if len(matches) > 1:
                return _Reconstruction((), ambiguous_slot=kind)
            if matches:
                selected.append(matches[0])
        return _Reconstruction(tuple(selected))

    def has_draft_override(
        self,
        components: tuple[PromptComponent, ...],
        positive_text: str,
        negative_text: str,
    ) -> bool:
        """Return whether snapshots contain content beyond the memberships."""
        rendered = self._renderer.render(PromptSelection(components))
        return (
            rendered.positive_text != positive_text
            or rendered.negative_text != negative_text
        )


class LegacyCompositionAuditor:
    """Classify historical generations using immutable canonical revisions."""

    def __init__(
        self,
        *,
        source_database_path: Path,
        canonical_database_path: Path,
        renderer: PromptRenderer | None = None,
    ) -> None:
        self._source_path = Path(source_database_path).resolve()
        self._canonical_path = Path(canonical_database_path).resolve()
        self._renderer = renderer or PromptRenderer()

    def audit(self, report_path: Path) -> LegacyCompositionAuditResult:
        """Write a deterministic, hash-bound reconstruction audit."""
        CanonicalSchemaManager(self._canonical_path).validate()
        connection = connect_read_only(self._canonical_path, rows=True)
        try:
            components = _read_components(connection)
            self._validate_legacy_catalog(connection, components)
            compositions = self._read_compositions(connection, components)
            reconstructor = HistoricalCompositionReconstructor(
                renderer=self._renderer,
                components=components,
            )
            items = [
                self._classify_generation(
                    generation,
                    compositions,
                    reconstructor,
                )
                for generation in self._read_generations(connection)
            ]
        finally:
            connection.close()
        summary = {classification: 0 for classification in _CLASSIFICATIONS}
        summary["generations"] = len(items)
        for item in items:
            summary[str(item["classification"])] += 1
        payload: dict[str, Any] = {
            "format_version": _AUDIT_FORMAT,
            "source_database": str(self._source_path),
            "source_sha256": _file_sha256(self._source_path),
            "canonical_database": str(self._canonical_path),
            "canonical_sha256": _file_sha256(self._canonical_path),
            "summary": summary,
            "items": items,
        }
        payload["audit_sha256"] = _payload_sha256(payload)
        destination = _write_report(report_path, payload)
        return LegacyCompositionAuditResult(destination, summary)

    def _validate_legacy_catalog(
        self,
        connection: sqlite3.Connection,
        components: tuple[PromptComponent, ...],
    ) -> None:
        source_connection = connect_read_only(self._source_path, rows=True)
        try:
            source_rows = source_connection.execute(
                """
                SELECT id, kind, key, pos, neg
                FROM playground_items
                ORDER BY id
                """
            ).fetchall()
        finally:
            source_connection.close()
        canonical_by_source = {
            str(row["source_key"]): (
                str(row["component_uid"]),
                str(row["kind"]),
                str(row["component_key"]),
            )
            for row in connection.execute(
                """
                SELECT source.source_key, component.component_uid,
                       component.kind, component.component_key
                FROM legacy_prompt_component_sources AS source
                JOIN prompt_components AS component
                    ON component.id = source.component_id
                WHERE source.source = ?
                """,
                (_LEGACY_SOURCE,),
            )
        }
        component_by_uid = {
            component.component_uid: component for component in components
        }
        for row in source_rows:
            source_key = str(int(row["id"]))
            mapped = canonical_by_source.get(source_key)
            if mapped is None:
                raise LegacyCompositionValidationError(
                    f"Legacy prompt item {source_key} has no canonical mapping"
                )
            component = component_by_uid.get(mapped[0])
            if component is None or mapped[1:] != (
                str(row["kind"]),
                str(row["key"]),
            ):
                raise LegacyCompositionValidationError(
                    f"Legacy prompt item {source_key} mapping conflicts"
                )
            matching_revision = any(
                str(revision["positive_text"]) == str(row["pos"] or "").strip()
                and str(revision["negative_text"])
                == str(row["neg"] or "").strip()
                for revision in connection.execute(
                    """
                    SELECT positive_text, negative_text
                    FROM prompt_revisions
                    WHERE component_id = (
                        SELECT id FROM prompt_components
                        WHERE component_uid = ?
                    )
                    """,
                    (component.component_uid,),
                )
            )
            if not matching_revision:
                raise LegacyCompositionValidationError(
                    f"Legacy prompt item {source_key} content is not preserved"
                )
        if len(canonical_by_source) != len(source_rows):
            raise LegacyCompositionValidationError(
                "Canonical legacy prompt mappings do not match the source"
            )

    @staticmethod
    def _read_generations(
        connection: sqlite3.Connection,
    ) -> tuple[_GenerationEvidence, ...]:
        rows = connection.execute(
            """
            SELECT generation.generation_uid,
                   positive.text AS positive_text,
                   negative.text AS negative_text,
                   generation.raw_metadata_json,
                   generation.prompt_composition_id
            FROM generations AS generation
            JOIN prompts AS positive
                ON positive.id = generation.positive_prompt_id
            JOIN prompts AS negative
                ON negative.id = generation.negative_prompt_id
            ORDER BY generation.generation_uid
            """
        ).fetchall()
        return tuple(
            _GenerationEvidence(
                generation_uid=str(row["generation_uid"]),
                positive_text=str(row["positive_text"]),
                negative_text=str(row["negative_text"]),
                raw_metadata_json=(
                    str(row["raw_metadata_json"])
                    if row["raw_metadata_json"] is not None
                    else None
                ),
                composition_id=(
                    int(row["prompt_composition_id"])
                    if row["prompt_composition_id"] is not None
                    else None
                ),
            )
            for row in rows
        )

    @staticmethod
    def _read_compositions(
        connection: sqlite3.Connection,
        components: tuple[PromptComponent, ...],
    ) -> dict[int, _StoredComposition]:
        by_revision = {
            component.latest_revision.revision_uid: component
            for component in components
        }
        compositions: dict[int, _StoredComposition] = {}
        for row in connection.execute(
            "SELECT id, composition_uid FROM prompt_compositions ORDER BY id"
        ):
            composition_id = int(row["id"])
            memberships = tuple(
                PromptCompositionMembership(
                    slot=str(member["slot"]),
                    position=int(member["position"]),
                    revision_uid=str(member["revision_uid"]),
                )
                for member in connection.execute(
                    """
                    SELECT revision.revision_uid, membership.slot,
                           membership.position
                    FROM prompt_composition_revisions AS membership
                    JOIN prompt_revisions AS revision
                        ON revision.id = membership.revision_id
                    WHERE membership.composition_id = ?
                    ORDER BY membership.position
                    """,
                    (composition_id,),
                )
            )
            selected = tuple(
                by_revision[membership.revision_uid]
                for membership in memberships
                if membership.revision_uid in by_revision
            )
            compositions[composition_id] = _StoredComposition(
                composition_uid=str(row["composition_uid"]),
                components=selected,
                memberships=memberships,
            )
        return compositions

    def _classify_generation(
        self,
        generation: _GenerationEvidence,
        compositions: dict[int, _StoredComposition],
        reconstructor: HistoricalCompositionReconstructor,
    ) -> dict[str, Any]:
        conflict = _prompt_provenance_conflict(generation)
        if conflict is not None:
            return _audit_item(generation, "conflict", conflict)
        if generation.composition_id is not None:
            composition = compositions.get(generation.composition_id)
            if composition is None:
                return _audit_item(
                    generation,
                    "conflict",
                    "missing_composition",
                )
            if not _stored_composition_is_consistent(
                composition,
                generation,
            ):
                return _audit_item(
                    generation,
                    "conflict",
                    "stored_composition_mismatch",
                )
            return _audit_item(
                generation,
                "already_exact",
                "stored_composition_roundtrip",
                composition=composition,
            )
        if not generation.positive_text and not generation.negative_text:
            return _audit_item(
                generation,
                "insufficient_evidence",
                "missing_prompt_snapshot",
            )
        reconstruction = reconstructor.reconstruct(
            generation.positive_text,
            generation.negative_text,
        )
        if reconstruction.ambiguous_slot is not None:
            return _audit_item(
                generation,
                "ambiguous",
                "multiple_revision_candidates_for_slot",
                ambiguous_slot=reconstruction.ambiguous_slot,
            )
        if not reconstruction.components:
            return _audit_item(
                generation,
                "insufficient_evidence",
                "no_unique_revision_membership",
            )
        composition = _composition_from_components(reconstruction.components)
        draft_override = reconstructor.has_draft_override(
            reconstruction.components,
            generation.positive_text,
            generation.negative_text,
        )
        if draft_override:
            return _audit_item(
                generation,
                "reconstructable_with_draft_override",
                "unique_memberships_with_draft_override",
                composition=composition,
                draft_override=True,
            )
        return _audit_item(
            generation,
            "exactly_reconstructable",
            "unique_memberships_exact_snapshot",
            composition=composition,
            draft_override=False,
        )


class LegacyCompositionImporter:
    """Apply only audited exact composition links in one transaction."""

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
    ) -> LegacyCompositionImportResult:
        """Link exact generations after validation and a full backup."""
        payload = self._load_and_validate_report(report_path)
        exact_items = [
            item
            for item in payload["items"]
            if item["classification"]
            in {
                "exactly_reconstructable",
                "reconstructable_with_draft_override",
            }
        ]
        self._prevalidate_exact_items(exact_items)
        backup_path = self._create_backup(backup_directory)
        connection = connect_existing(self._canonical_path, rows=True)
        commit_attempted = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            linked = 0
            for item in exact_items:
                self._link_generation(connection, item)
                linked += 1
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
        return LegacyCompositionImportResult(
            linked_generations=linked,
            already_exact=int(payload["summary"]["already_exact"]),
            backup_path=backup_path,
        )

    def _load_and_validate_report(self, report_path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise LegacyCompositionValidationError(
                "Legacy composition audit is unreadable"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("format_version") != _AUDIT_FORMAT
        ):
            raise LegacyCompositionValidationError(
                "Unsupported legacy composition audit format"
            )
        if str(payload.get("audit_sha256") or "") != _payload_sha256(payload):
            raise LegacyCompositionValidationError(
                "Legacy composition audit checksum mismatch"
            )
        expected_paths = {
            "source_database": self._source_path,
            "canonical_database": self._canonical_path,
        }
        for field, expected in expected_paths.items():
            if Path(str(payload.get(field) or "")).resolve() != expected:
                raise LegacyCompositionValidationError(
                    f"Legacy composition audit {field} mismatch"
                )
        if payload.get("source_sha256") != _file_sha256(self._source_path):
            raise LegacyCompositionValidationError(
                "Legacy prompt source changed after composition audit"
            )
        if payload.get("canonical_sha256") != _file_sha256(
            self._canonical_path
        ):
            raise LegacyCompositionValidationError(
                "Canonical database changed after composition audit"
            )
        items = payload.get("items")
        summary = payload.get("summary")
        if not isinstance(items, list) or not isinstance(summary, dict):
            raise LegacyCompositionValidationError(
                "Legacy composition audit structure is invalid"
            )
        measured = {classification: 0 for classification in _CLASSIFICATIONS}
        measured["generations"] = len(items)
        for item in items:
            if (
                not isinstance(item, dict)
                or item.get("classification") not in _CLASSIFICATIONS
            ):
                raise LegacyCompositionValidationError(
                    "Legacy composition audit item is invalid"
                )
            measured[str(item["classification"])] += 1
        if summary != measured:
            raise LegacyCompositionValidationError(
                "Legacy composition audit summary mismatch"
            )
        if measured["conflict"]:
            raise LegacyCompositionValidationError(
                "Legacy composition audit contains conflicts"
            )
        return payload

    def _prevalidate_exact_items(self, items: list[dict[str, Any]]) -> None:
        connection = connect_read_only(self._canonical_path, rows=True)
        try:
            reconstructor = HistoricalCompositionReconstructor(
                renderer=PromptRenderer(),
                components=_read_components(connection),
            )
            for item in items:
                generation = connection.execute(
                    """
                    SELECT generation.prompt_composition_id,
                           positive.text AS positive_text,
                           negative.text AS negative_text
                    FROM generations AS generation
                    JOIN prompts AS positive
                        ON positive.id = generation.positive_prompt_id
                    JOIN prompts AS negative
                        ON negative.id = generation.negative_prompt_id
                    WHERE generation.generation_uid = ?
                    """,
                    (str(item.get("generation_uid") or ""),),
                ).fetchone()
                if (
                    generation is None
                    or generation["prompt_composition_id"] is not None
                ):
                    raise LegacyCompositionValidationError(
                        "Generation composition state changed after audit"
                    )
                components = self._components_for_item(connection, item)
                positive_text = str(generation["positive_text"])
                negative_text = str(generation["negative_text"])
                reconstruction = reconstructor.reconstruct(
                    positive_text,
                    negative_text,
                )
                if reconstruction.ambiguous_slot is not None or tuple(
                    component.latest_revision.revision_uid
                    for component in reconstruction.components
                ) != tuple(
                    component.latest_revision.revision_uid
                    for component in components
                ):
                    raise LegacyCompositionValidationError(
                        "Composition membership evidence changed after audit"
                    )
                draft_override = reconstructor.has_draft_override(
                    components,
                    positive_text,
                    negative_text,
                )
                expected_classification = (
                    "reconstructable_with_draft_override"
                    if draft_override
                    else "exactly_reconstructable"
                )
                if (
                    item.get("classification") != expected_classification
                    or item.get("draft_override") is not draft_override
                ):
                    raise LegacyCompositionValidationError(
                        "Composition override state changed after audit"
                    )
                memberships = _memberships_from_item(item)
                if prompt_composition_identity(memberships) != str(
                    item.get("composition_uid") or ""
                ):
                    raise LegacyCompositionValidationError(
                        "Composition identity does not match its memberships"
                    )
        finally:
            connection.close()

    @staticmethod
    def _components_for_item(
        connection: sqlite3.Connection,
        item: dict[str, Any],
    ) -> tuple[PromptComponent, ...]:
        components: list[PromptComponent] = []
        for membership in _memberships_from_item(item):
            row = connection.execute(
                """
                SELECT component.component_uid, component.kind,
                       component.component_key, component.name,
                       component.tags, component.notes,
                       component.archived_at, revision.revision_uid,
                       revision.revision_number, revision.positive_text,
                       revision.negative_text, revision.content_hash
                FROM prompt_revisions AS revision
                JOIN prompt_components AS component
                    ON component.id = revision.component_id
                WHERE revision.revision_uid = ?
                """,
                (membership.revision_uid,),
            ).fetchone()
            if row is None or str(row["kind"]) != membership.slot:
                raise LegacyCompositionValidationError(
                    "Composition references an unknown or mismatched revision"
                )
            tags = json.loads(str(row["tags"] or "[]"))
            components.append(
                PromptComponent(
                    component_uid=str(row["component_uid"]),
                    kind=str(row["kind"]),
                    component_key=str(row["component_key"]),
                    name=str(row["name"]),
                    tags=tuple(str(tag) for tag in tags),
                    notes=str(row["notes"] or ""),
                    archived=row["archived_at"] is not None,
                    latest_revision=PromptRevision(
                        revision_uid=str(row["revision_uid"]),
                        revision_number=int(row["revision_number"]),
                        positive_text=str(row["positive_text"]),
                        negative_text=str(row["negative_text"]),
                        content_hash=str(row["content_hash"]),
                    ),
                )
            )
        return tuple(components)

    @staticmethod
    def _link_generation(
        connection: sqlite3.Connection,
        item: dict[str, Any],
    ) -> None:
        memberships = _memberships_from_item(item)
        composition_uid = str(item["composition_uid"])
        connection.execute(
            "INSERT OR IGNORE INTO prompt_compositions(composition_uid) "
            "VALUES (?)",
            (composition_uid,),
        )
        composition_row = connection.execute(
            "SELECT id FROM prompt_compositions WHERE composition_uid = ?",
            (composition_uid,),
        ).fetchone()
        if composition_row is None:
            raise RuntimeError("Prompt composition could not be persisted")
        composition_id = int(composition_row["id"])
        observed = tuple(
            (
                str(row["revision_uid"]),
                str(row["slot"]),
                int(row["position"]),
            )
            for row in connection.execute(
                """
                SELECT revision.revision_uid, membership.slot,
                       membership.position
                FROM prompt_composition_revisions AS membership
                JOIN prompt_revisions AS revision
                    ON revision.id = membership.revision_id
                WHERE membership.composition_id = ?
                ORDER BY membership.position
                """,
                (composition_id,),
            )
        )
        expected = tuple(
            (membership.revision_uid, membership.slot, membership.position)
            for membership in memberships
        )
        if observed and observed != expected:
            raise LegacyCompositionValidationError(
                "Prompt composition identity collision"
            )
        if not observed:
            for membership in memberships:
                revision = connection.execute(
                    "SELECT id FROM prompt_revisions WHERE revision_uid = ?",
                    (membership.revision_uid,),
                ).fetchone()
                if revision is None:
                    raise LegacyCompositionValidationError(
                        "Prompt composition revision disappeared"
                    )
                connection.execute(
                    """
                    INSERT INTO prompt_composition_revisions(
                        composition_id, revision_id, slot, position
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        composition_id,
                        int(revision["id"]),
                        membership.slot,
                        membership.position,
                    ),
                )
        updated = connection.execute(
            """
            UPDATE generations
            SET prompt_composition_id = ?
            WHERE generation_uid = ? AND prompt_composition_id IS NULL
            """,
            (composition_id, str(item["generation_uid"])),
        )
        if updated.rowcount != 1:
            raise LegacyCompositionValidationError(
                "Generation composition state changed during import"
            )

    def _create_backup(self, backup_directory: Path | None) -> Path:
        destination = (
            Path(backup_directory).resolve()
            if backup_directory is not None
            else self._canonical_path.parent / "backups"
        )
        destination.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        backup_path = destination / (
            f"{self._canonical_path.stem}.legacy-compositions."
            f"{timestamp}.{uuid4().hex}.sqlite3"
        )
        temporary = backup_path.with_name(f".{backup_path.name}.tmp")
        source = connect_read_only(self._canonical_path)
        target = sqlite3.connect(temporary)
        try:
            source.backup(target)
        finally:
            target.close()
            source.close()
        os.replace(temporary, backup_path)
        return backup_path

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
            raise LegacyCompositionRecoveryError(
                "Legacy composition import failed and backup recovery did "
                f"not restore a valid canonical database: {recovery_error}"
            ) from original_error


def _read_components(
    connection: sqlite3.Connection,
) -> tuple[PromptComponent, ...]:
    rows = connection.execute(
        """
        SELECT component.component_uid, component.kind,
               component.component_key, component.name, component.tags,
               component.notes, component.archived_at,
               revision.revision_uid, revision.revision_number,
               revision.positive_text, revision.negative_text,
               revision.content_hash
        FROM prompt_components AS component
        JOIN prompt_revisions AS revision
            ON revision.component_id = component.id
        ORDER BY component.component_uid, revision.revision_number
        """
    ).fetchall()
    components: list[PromptComponent] = []
    for row in rows:
        raw_tags = json.loads(str(row["tags"] or "[]"))
        if not isinstance(raw_tags, list):
            raise LegacyCompositionValidationError(
                "Canonical prompt component tags are invalid"
            )
        components.append(
            PromptComponent(
                component_uid=str(row["component_uid"]),
                kind=str(row["kind"]),
                component_key=str(row["component_key"]),
                name=str(row["name"]),
                tags=tuple(str(tag) for tag in raw_tags),
                notes=str(row["notes"] or ""),
                archived=row["archived_at"] is not None,
                latest_revision=PromptRevision(
                    revision_uid=str(row["revision_uid"]),
                    revision_number=int(row["revision_number"]),
                    positive_text=str(row["positive_text"]),
                    negative_text=str(row["negative_text"]),
                    content_hash=str(row["content_hash"]),
                ),
            )
        )
    return tuple(components)


def _composition_from_components(
    components: tuple[PromptComponent, ...],
) -> _StoredComposition:
    memberships = tuple(
        PromptCompositionMembership(
            slot=component.kind,
            position=position,
            revision_uid=component.latest_revision.revision_uid,
        )
        for position, component in enumerate(components)
    )
    return _StoredComposition(
        composition_uid=prompt_composition_identity(memberships),
        components=components,
        memberships=memberships,
    )


def _stored_composition_is_consistent(
    composition: _StoredComposition,
    generation: _GenerationEvidence,
) -> bool:
    if not composition.memberships or len(composition.memberships) != len(
        composition.components
    ):
        return False
    if any(
        membership.position != position
        or membership.slot != component.kind
        or membership.revision_uid != component.latest_revision.revision_uid
        for position, (membership, component) in enumerate(
            zip(composition.memberships, composition.components, strict=True)
        )
    ):
        return False
    if (
        prompt_composition_identity(composition.memberships)
        != composition.composition_uid
    ):
        return False
    return all(
        _component_matches_snapshots(
            component,
            positive_text=generation.positive_text,
            negative_text=generation.negative_text,
        )
        for component in composition.components
    )


def _prompt_provenance_conflict(
    generation: _GenerationEvidence,
) -> str | None:
    if generation.raw_metadata_json is None:
        return None
    try:
        raw_metadata = json.loads(generation.raw_metadata_json)
    except json.JSONDecodeError:
        return "invalid_raw_metadata"
    if not isinstance(raw_metadata, dict):
        return "invalid_raw_metadata"
    snapshots = (
        ("pos_prompt", generation.positive_text),
        ("neg_prompt", generation.negative_text),
    )
    for key, expected in snapshots:
        if key in raw_metadata and str(raw_metadata[key] or "") != expected:
            return f"{key}_conflict"
    return None


def _audit_item(
    generation: _GenerationEvidence,
    classification: str,
    reason: str,
    *,
    composition: _StoredComposition | None = None,
    draft_override: bool | None = None,
    ambiguous_slot: str | None = None,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "generation_uid": generation.generation_uid,
        "classification": classification,
        "reason": reason,
    }
    if composition is not None:
        item["composition_uid"] = composition.composition_uid
        item["memberships"] = [
            {
                "slot": membership.slot,
                "position": membership.position,
                "revision_uid": membership.revision_uid,
            }
            for membership in composition.memberships
        ]
    if draft_override is not None:
        item["draft_override"] = draft_override
    if ambiguous_slot is not None:
        item["ambiguous_slot"] = ambiguous_slot
    return item


def _memberships_from_item(
    item: dict[str, Any],
) -> tuple[PromptCompositionMembership, ...]:
    raw_memberships = item.get("memberships")
    if not isinstance(raw_memberships, list) or not raw_memberships:
        raise LegacyCompositionValidationError(
            "Exact composition has no memberships"
        )
    try:
        memberships = tuple(
            PromptCompositionMembership(
                slot=str(raw["slot"]),
                position=int(raw["position"]),
                revision_uid=str(raw["revision_uid"]),
            )
            for raw in raw_memberships
            if isinstance(raw, dict)
        )
    except (KeyError, TypeError, ValueError) as error:
        raise LegacyCompositionValidationError(
            "Exact composition memberships are invalid"
        ) from error
    if len(memberships) != len(raw_memberships) or tuple(
        membership.position for membership in memberships
    ) != tuple(range(len(memberships))):
        raise LegacyCompositionValidationError(
            "Exact composition membership order is invalid"
        )
    return memberships


def _component_matches_snapshots(
    component: PromptComponent,
    *,
    positive_text: str,
    negative_text: str,
) -> bool:
    revision = component.latest_revision
    positive_atoms = _prompt_atom_sequence(revision.positive_text)
    negative_atoms = _prompt_atom_sequence(revision.negative_text)
    if not positive_atoms and not negative_atoms:
        return False
    return _contains_atom_sequence(
        _prompt_atom_sequence(positive_text),
        positive_atoms,
    ) and _contains_atom_sequence(
        _prompt_atom_sequence(negative_text),
        negative_atoms,
    )


def _prompt_atom_sequence(value: str) -> tuple[tuple[str, int], ...]:
    return tuple(
        (atom.text, atom.weight_milli) for atom in parse_prompt_atoms(value)
    )


def _contains_atom_sequence(
    prompt_atoms: tuple[tuple[str, int], ...],
    component_atoms: tuple[tuple[str, int], ...],
) -> bool:
    if not component_atoms:
        return True
    last_start = len(prompt_atoms) - len(component_atoms)
    return any(
        prompt_atoms[start : start + len(component_atoms)] == component_atoms
        for start in range(last_start + 1)
    )


def _write_report(report_path: Path, payload: dict[str, Any]) -> Path:
    destination = Path(report_path).resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.{uuid4().hex}.tmp")
    try:
        temporary.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    return destination


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _payload_sha256(payload: dict[str, Any]) -> str:
    hashed = dict(payload)
    hashed.pop("audit_sha256", None)
    rendered = json.dumps(
        hashed,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(rendered.encode()).hexdigest()
