"""Audited import of legacy review, Arena, and curation facts."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
)
from comfyreview.repositories.sqlite.connection import connect_read_only

_AUDIT_FORMAT = "comfyreview-legacy-feature-audit-v1"


class LegacyFeatureImportValidationError(ValueError):
    """Reject a stale, ambiguous, or internally inconsistent audit."""


class LegacyFeatureImportRecoveryError(RuntimeError):
    """Report an import failure followed by a failed backup restore."""


class LegacyFeatureImportObserver(Protocol):
    """Observe durable safety milestones of a legacy feature import."""

    def backup_created(self, backup_path: Path) -> None:
        """Report the backup before the canonical write transaction."""
        ...


@dataclass(frozen=True, slots=True)
class LegacyFeatureAuditResult:
    """Summarize a persisted legacy feature audit snapshot."""

    report_path: Path
    summary: dict[str, int]


@dataclass(frozen=True, slots=True)
class LegacyFeatureImportResult:
    """Summarize one atomic canonical feature import."""

    backup_path: Path
    rating_events: int
    deduplicated_ratings: int
    arena_matches: int
    curation_assignments: int
    orphan_ratings: int
    orphan_arena_matches: int
    orphan_curation_assignments: int


class SqliteLegacyFeatureMigration:
    """Audit immutable legacy facts for canonical feature import."""

    def __init__(
        self,
        *,
        canonical_database_path: Path,
        ratings_database_path: Path,
        arena_database_path: Path,
        curation_database_path: Path,
        images_projection_database_path: Path,
        observer: LegacyFeatureImportObserver | None = None,
    ) -> None:
        self._canonical_path = Path(canonical_database_path).resolve()
        self._ratings_path = Path(ratings_database_path).resolve()
        self._arena_path = Path(arena_database_path).resolve()
        self._curation_path = Path(curation_database_path).resolve()
        self._images_projection_path = Path(
            images_projection_database_path
        ).resolve()
        self._observer = observer

    def audit(self, report_path: Path) -> LegacyFeatureAuditResult:
        """Create a read-only, source-hash-bound migration snapshot."""
        CanonicalSchemaManager(self._canonical_path).validate()
        source_paths = self._source_paths()
        before_hashes = {
            name: self._sha256_file(path)
            for name, path in source_paths.items()
        }
        canonical = self._canonical_snapshot()
        ratings = self._audit_ratings(canonical)
        arena = self._audit_arena(canonical)
        curation = self._audit_curation(canonical)
        parity = self._rating_parity(ratings["mapped"], canonical)
        after_hashes = {
            name: self._sha256_file(path)
            for name, path in source_paths.items()
        }
        if before_hashes != after_hashes:
            raise LegacyFeatureImportValidationError(
                "A legacy source changed while it was being audited"
            )

        conflicts = [
            *ratings["conflicts"],
            *arena["conflicts"],
            *curation["conflicts"],
            *parity["conflicts"],
        ]
        summary = {
            "rating_rows": ratings["total"],
            "mapped_rating_rows": len(ratings["mapped"]),
            "orphan_rating_rows": len(ratings["orphan_ids"]),
            "deduplicated_rating_rows": len(ratings["deduplications"]),
            "arena_rows": arena["total"],
            "mapped_arena_rows": len(arena["mapped"]),
            "orphan_arena_rows": len(arena["orphan_ids"]),
            "curation_rows": curation["total"],
            "mapped_curation_rows": len(curation["mapped"]),
            "orphan_curation_rows": len(curation["orphan_keys"]),
            "parity_checked_images": parity["checked_images"],
            "conflicts": len(conflicts),
        }
        payload = {
            "format": _AUDIT_FORMAT,
            "created_at_utc": datetime.now(UTC).isoformat(),
            "canonical_database": str(self._canonical_path),
            "sources": {
                name: {"path": str(path), "sha256": before_hashes[name]}
                for name, path in source_paths.items()
            },
            "summary": summary,
            "canonical_events": canonical["events"],
            "ratings": ratings,
            "arena": arena,
            "curation": curation,
            "parity": parity,
            "conflicts": conflicts,
        }
        target = Path(report_path).resolve()
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return LegacyFeatureAuditResult(report_path=target, summary=summary)

    def import_audit(
        self,
        report_path: Path,
        *,
        backup_directory: Path | None = None,
    ) -> LegacyFeatureImportResult:
        """Revalidate and atomically import one audit snapshot."""
        payload = self._load_report(report_path)
        self._validate_snapshot(payload)
        if payload["conflicts"]:
            raise LegacyFeatureImportValidationError(
                "Legacy feature audit contains blocking conflicts"
            )
        backup_path = self._create_backup(backup_directory)
        if self._observer is not None:
            self._observer.backup_created(backup_path)

        connection = self._open_canonical_write()
        commit_attempted = False
        try:
            connection.execute("BEGIN IMMEDIATE")
            result = self._write_import(connection, payload, backup_path)
            commit_attempted = True
            connection.commit()
        except Exception as error:
            connection.rollback()
            connection.close()
            if commit_attempted or not self._canonical_is_valid():
                try:
                    self._restore_backup(backup_path)
                except Exception as recovery_error:
                    raise LegacyFeatureImportRecoveryError(
                        "Legacy feature import failed and backup restore "
                        f"also failed: {recovery_error}"
                    ) from error
            raise
        else:
            connection.close()
        try:
            CanonicalSchemaManager(self._canonical_path).validate()
        except Exception as error:
            try:
                self._restore_backup(backup_path)
            except Exception as recovery_error:
                raise LegacyFeatureImportRecoveryError(
                    "Legacy feature import committed an invalid database and "
                    f"backup restore also failed: {recovery_error}"
                ) from error
            raise
        return result

    def _canonical_snapshot(self) -> dict[str, Any]:
        connection = connect_read_only(self._canonical_path, rows=True)
        try:
            images = connection.execute(
                "SELECT id, image_uid, png_path, json_path FROM images"
            ).fetchall()
            events = connection.execute(
                """
                SELECT event.event_uid, image.image_uid, event.event_type,
                       event.rating, event.source, event.source_key,
                       event.sequence
                FROM review_events AS event
                JOIN images AS image ON image.id = event.image_id
                ORDER BY event.sequence
                """
            ).fetchall()
        finally:
            connection.close()
        by_json: dict[str, dict[str, object]] = {}
        by_png: dict[str, dict[str, object]] = {}
        for image in images:
            record = {
                "id": int(image["id"]),
                "image_uid": str(image["image_uid"]),
            }
            by_png[self._path_key(image["png_path"])] = record
            if image["json_path"] is not None:
                by_json[self._path_key(image["json_path"])] = record
        return {
            "by_json": by_json,
            "by_png": by_png,
            "events": [
                {
                    "event_uid": str(row["event_uid"]),
                    "image_uid": str(row["image_uid"]),
                    "event_type": str(row["event_type"]),
                    "rating": row["rating"],
                    "source": str(row["source"]),
                    "source_key": str(row["source_key"]),
                    "sequence": int(row["sequence"]),
                }
                for row in events
            ],
        }

    def _audit_ratings(self, canonical: dict[str, Any]) -> dict[str, Any]:
        connection = self._open_source(self._ratings_path)
        try:
            self._require_columns(
                connection,
                "ratings",
                {"id", "json_path", "run", "rating", "deleted"},
            )
            rows = connection.execute(
                """
                SELECT id, json_path, run, rating, deleted
                FROM ratings
                ORDER BY id
                """
            ).fetchall()
        finally:
            connection.close()

        mapped: list[dict[str, object]] = []
        orphan_ids: list[int] = []
        by_image_rating: dict[tuple[str, int], list[int]] = defaultdict(list)
        for row in rows:
            image = canonical["by_json"].get(self._path_key(row["json_path"]))
            if image is None:
                orphan_ids.append(int(row["id"]))
                continue
            deleted = bool(row["deleted"])
            rating = None if deleted else self._rating(row["rating"])
            item = {
                "source_id": int(row["id"]),
                "image_uid": str(image["image_uid"]),
                "event_type": "delete" if deleted else "rating",
                "rating": rating,
                "run": int(row["run"]),
            }
            mapped.append(item)
            if rating is not None:
                by_image_rating[(str(image["image_uid"]), rating)].append(
                    int(row["id"])
                )

        deduplications: list[dict[str, object]] = []
        conflicts: list[dict[str, object]] = []
        for event in canonical["events"]:
            if event["source"] != "canonical_v3":
                continue
            if event["event_type"] != "rating" or event["rating"] is None:
                continue
            key = (str(event["image_uid"]), int(event["rating"]))
            candidates = by_image_rating.get(key, [])
            if len(candidates) == 1:
                deduplications.append(
                    {
                        "source_id": candidates[0],
                        "event_uid": str(event["event_uid"]),
                    }
                )
            elif len(candidates) > 1:
                conflicts.append(
                    {
                        "code": "ambiguous_review_deduplication",
                        "event_uid": str(event["event_uid"]),
                        "source_ids": candidates,
                    }
                )
        return {
            "total": len(rows),
            "mapped": mapped,
            "orphan_ids": orphan_ids,
            "deduplications": deduplications,
            "conflicts": conflicts,
        }

    def _audit_arena(self, canonical: dict[str, Any]) -> dict[str, Any]:
        connection = self._open_source(self._arena_path)
        try:
            self._require_columns(
                connection,
                "arena_matches",
                {
                    "id",
                    "left_json",
                    "right_json",
                    "winner_json",
                    "created_at",
                    "run",
                },
            )
            rows = connection.execute(
                "SELECT * FROM arena_matches ORDER BY id"
            ).fetchall()
        finally:
            connection.close()
        mapped: list[dict[str, object]] = []
        orphan_ids: list[int] = []
        conflicts: list[dict[str, object]] = []
        for row in rows:
            left = canonical["by_json"].get(self._path_key(row["left_json"]))
            right = canonical["by_json"].get(self._path_key(row["right_json"]))
            if left is None or right is None:
                orphan_ids.append(int(row["id"]))
                continue
            winner_key = self._path_key(row["winner_json"])
            if winner_key == self._path_key(row["left_json"]):
                winner = left
                decision = "left"
            elif winner_key == self._path_key(row["right_json"]):
                winner = right
                decision = "right"
            else:
                conflicts.append(
                    {
                        "code": "invalid_arena_winner",
                        "source_id": int(row["id"]),
                    }
                )
                continue
            mapped.append(
                {
                    "source_id": int(row["id"]),
                    "left_image_uid": str(left["image_uid"]),
                    "right_image_uid": str(right["image_uid"]),
                    "winner_image_uid": str(winner["image_uid"]),
                    "decision": decision,
                    "created_at": str(row["created_at"]),
                    "run": row["run"],
                }
            )
        return {
            "total": len(rows),
            "mapped": mapped,
            "orphan_ids": orphan_ids,
            "conflicts": conflicts,
        }

    def _audit_curation(self, canonical: dict[str, Any]) -> dict[str, Any]:
        connection = self._open_source(self._curation_path)
        try:
            self._require_columns(
                connection,
                "curation",
                {"png_path", "set_key"},
            )
            rows = connection.execute(
                "SELECT png_path, set_key FROM curation ORDER BY png_path"
            ).fetchall()
        finally:
            connection.close()
        mapped: list[dict[str, object]] = []
        orphan_keys: list[str] = []
        assignments: dict[str, str] = {}
        conflicts: list[dict[str, object]] = []
        for row in rows:
            path_key = self._path_key(row["png_path"])
            source_key = hashlib.sha256(
                f"{path_key}\0{row['set_key']}".encode()
            ).hexdigest()
            image = canonical["by_png"].get(path_key)
            if image is None:
                orphan_keys.append(source_key)
                continue
            image_uid = str(image["image_uid"])
            set_key = str(row["set_key"])
            previous = assignments.setdefault(image_uid, set_key)
            if previous != set_key:
                conflicts.append(
                    {
                        "code": "conflicting_curation_assignment",
                        "image_uid": image_uid,
                    }
                )
                continue
            mapped.append(
                {
                    "source_key": source_key,
                    "image_uid": image_uid,
                    "set_key": set_key,
                }
            )
        return {
            "total": len(rows),
            "mapped": mapped,
            "orphan_keys": orphan_keys,
            "conflicts": conflicts,
        }

    def _rating_parity(
        self,
        mapped_ratings: list[dict[str, object]],
        canonical: dict[str, Any],
    ) -> dict[str, Any]:
        grouped: dict[str, list[int]] = defaultdict(list)
        for item in mapped_ratings:
            if item["event_type"] == "rating":
                grouped[str(item["image_uid"])].append(
                    int(str(item["rating"]))
                )
        connection = self._open_source(self._images_projection_path)
        try:
            self._require_columns(
                connection,
                "images",
                {"json_path", "avg_rating", "rating_count"},
            )
            projection = {
                self._path_key(row["json_path"]): row
                for row in connection.execute(
                    "SELECT json_path, avg_rating, rating_count FROM images"
                )
                if row["json_path"] is not None
            }
        finally:
            connection.close()
        path_by_uid = {
            str(record["image_uid"]): path
            for path, record in canonical["by_json"].items()
        }
        conflicts: list[dict[str, object]] = []
        checked = 0
        canonical_overrides = 0
        aggregates: list[dict[str, object]] = []
        current_canonical_ratings = {
            str(event["image_uid"]): int(event["rating"])
            for event in canonical["events"]
            if event["event_type"] == "rating" and event["rating"] is not None
        }
        for image_uid, ratings in sorted(grouped.items()):
            expected_count = len(ratings)
            expected_average = sum(ratings) / expected_count
            aggregates.append(
                {
                    "image_uid": image_uid,
                    "rating_count": expected_count,
                    "rating_sum": sum(ratings),
                }
            )
            row = projection.get(path_by_uid[image_uid])
            if row is None:
                continue
            checked += 1
            legacy_matches = (
                int(row["rating_count"] or 0) == expected_count
                and abs(float(row["avg_rating"] or 0.0) - expected_average)
                <= 1e-9
            )
            current_rating = current_canonical_ratings.get(image_uid)
            canonical_matches = (
                current_rating is not None
                and int(row["rating_count"] or 0) == 1
                and abs(float(row["avg_rating"] or 0.0) - current_rating)
                <= 1e-9
            )
            if canonical_matches and not legacy_matches:
                canonical_overrides += 1
            elif not legacy_matches:
                conflicts.append(
                    {
                        "code": "rating_projection_mismatch",
                        "image_uid": image_uid,
                    }
                )
        return {
            "checked_images": checked,
            "canonical_override_images": canonical_overrides,
            "aggregates": aggregates,
            "conflicts": conflicts,
        }

    def _validate_snapshot(self, payload: dict[str, Any]) -> None:
        if payload.get("format") != _AUDIT_FORMAT:
            raise LegacyFeatureImportValidationError(
                "Unsupported legacy feature audit format"
            )
        if Path(str(payload.get("canonical_database"))).resolve() != (
            self._canonical_path
        ):
            raise LegacyFeatureImportValidationError(
                "Audit belongs to a different canonical database"
            )
        expected_sources = self._source_paths()
        sources = payload.get("sources")
        if not isinstance(sources, dict):
            raise LegacyFeatureImportValidationError(
                "Audit source fingerprints are missing"
            )
        for name, path in expected_sources.items():
            source = sources.get(name)
            if not isinstance(source, dict):
                raise LegacyFeatureImportValidationError(
                    f"Audit source is missing: {name}"
                )
            if Path(str(source.get("path"))).resolve() != path:
                raise LegacyFeatureImportValidationError(
                    f"Audit source path changed: {name}"
                )
            if str(source.get("sha256")) != self._sha256_file(path):
                raise LegacyFeatureImportValidationError(
                    f"Audit source hash changed: {name}"
                )
        CanonicalSchemaManager(self._canonical_path).validate()
        current = self._canonical_snapshot()
        expected_events = payload.get("canonical_events")
        imported = {
            (str(event["source"]), str(event["source_key"]))
            for event in current["events"]
            if event["source"]
            in {
                "legacy_ratings",
                "legacy_arena",
                "legacy_curation",
            }
        }
        if not imported and current["events"] != expected_events:
            raise LegacyFeatureImportValidationError(
                "Canonical review events changed since the audit"
            )
        fresh_ratings = self._audit_ratings(current)
        fresh_arena = self._audit_arena(current)
        fresh_curation = self._audit_curation(current)
        fresh_parity = self._rating_parity(fresh_ratings["mapped"], current)
        for name, keys, fresh in (
            (
                "ratings",
                ("total", "mapped", "orphan_ids", "conflicts"),
                fresh_ratings,
            ),
            (
                "arena",
                ("total", "mapped", "orphan_ids", "conflicts"),
                fresh_arena,
            ),
            (
                "curation",
                ("total", "mapped", "orphan_keys", "conflicts"),
                fresh_curation,
            ),
            (
                "parity",
                ("checked_images", "aggregates", "conflicts"),
                fresh_parity,
            ),
        ):
            section = payload.get(name)
            if not isinstance(section, dict) or any(
                section.get(key) != fresh[key] for key in keys
            ):
                raise LegacyFeatureImportValidationError(
                    f"Audit section was modified or became stale: {name}"
                )
        if (
            not imported
            and payload["ratings"].get("deduplications")
            != (fresh_ratings["deduplications"])
        ):
            raise LegacyFeatureImportValidationError(
                "Audit rating deduplication was modified or became stale"
            )
        self._validate_item_mappings(payload, current)

    @staticmethod
    def _validate_item_mappings(
        payload: dict[str, Any],
        canonical: dict[str, Any],
    ) -> None:
        known_uids = {
            str(record["image_uid"]) for record in canonical["by_png"].values()
        }
        referenced: set[str] = set()
        for item in payload["ratings"]["mapped"]:
            referenced.add(str(item["image_uid"]))
        for item in payload["arena"]["mapped"]:
            referenced.update(
                {
                    str(item["left_image_uid"]),
                    str(item["right_image_uid"]),
                    str(item["winner_image_uid"]),
                }
            )
        for item in payload["curation"]["mapped"]:
            referenced.add(str(item["image_uid"]))
        missing = referenced - known_uids
        if missing:
            raise LegacyFeatureImportValidationError(
                "Canonical image mappings changed since the audit"
            )

    def _write_import(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
        backup_path: Path,
    ) -> LegacyFeatureImportResult:
        existing_rating_keys = {
            str(row[0])
            for row in connection.execute(
                "SELECT source_key FROM review_events "
                "WHERE source = 'legacy_ratings'"
            )
        }
        rating_items = payload["ratings"]["mapped"]
        expected_rating_keys = {
            f"rating:{int(item['source_id'])}" for item in rating_items
        }
        if existing_rating_keys:
            if existing_rating_keys != expected_rating_keys:
                raise LegacyFeatureImportValidationError(
                    "Canonical legacy rating import is partial or stale"
                )
            rating_count = 0
            deduplicated_count = 0
        else:
            rating_count, deduplicated_count = self._write_ratings(
                connection,
                payload,
            )
        arena_count = self._write_arena(connection, payload)
        curation_count = self._write_curation(connection, payload)
        self._validate_imported_aggregates(connection, payload)
        return LegacyFeatureImportResult(
            backup_path=backup_path,
            rating_events=rating_count,
            deduplicated_ratings=deduplicated_count,
            arena_matches=arena_count,
            curation_assignments=curation_count,
            orphan_ratings=len(payload["ratings"]["orphan_ids"]),
            orphan_arena_matches=len(payload["arena"]["orphan_ids"]),
            orphan_curation_assignments=len(
                payload["curation"]["orphan_keys"]
            ),
        )

    def _write_ratings(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
    ) -> tuple[int, int]:
        image_ids = self._image_ids(connection)
        dedupe = {
            int(item["source_id"]): str(item["event_uid"])
            for item in payload["ratings"]["deduplications"]
        }
        captured_uids = {
            str(item["event_uid"]) for item in payload["canonical_events"]
        }
        offset = len(payload["ratings"]["mapped"]) * 2 + len(captured_uids)
        connection.execute(
            "UPDATE review_events SET sequence = sequence + ?",
            (offset,),
        )
        sequence = 0
        imported = 0
        states: dict[str, str] = {}
        deduplicated_uids: set[str] = set()
        for item in payload["ratings"]["mapped"]:
            source_id = int(item["source_id"])
            image_uid = str(item["image_uid"])
            image_id = image_ids[image_uid]
            event_type = str(item["event_type"])
            if event_type == "rating" and states.get(image_uid) == "delete":
                sequence += 1
                self._insert_import_event(
                    connection,
                    event_uid=f"legacy-rating-{source_id}-restore",
                    image_id=image_id,
                    event_type="restore",
                    rating=None,
                    source_key=f"rating:{source_id}:restore",
                    sequence=sequence,
                )
                states[image_uid] = "restore"
            sequence += 1
            source_key = f"rating:{source_id}"
            if source_id in dedupe:
                event_uid = dedupe[source_id]
                cursor = connection.execute(
                    """
                    UPDATE review_events
                    SET source = 'legacy_ratings',
                        source_key = ?,
                        sequence = ?
                    WHERE event_uid = ? AND source = 'canonical_v3'
                    """,
                    (source_key, sequence, event_uid),
                )
                if cursor.rowcount != 1:
                    raise LegacyFeatureImportValidationError(
                        "Canonical review deduplication changed since audit"
                    )
                deduplicated_uids.add(event_uid)
            else:
                self._insert_import_event(
                    connection,
                    event_uid=f"legacy-rating-{source_id}",
                    image_id=image_id,
                    event_type=event_type,
                    rating=item["rating"],
                    source_key=source_key,
                    sequence=sequence,
                )
                imported += 1
            states[image_uid] = event_type

        remaining = [
            event
            for event in payload["canonical_events"]
            if event["event_uid"] not in deduplicated_uids
        ]
        for event in sorted(remaining, key=lambda item: int(item["sequence"])):
            sequence += 1
            cursor = connection.execute(
                "UPDATE review_events SET sequence = ? WHERE event_uid = ?",
                (sequence, str(event["event_uid"])),
            )
            if cursor.rowcount != 1:
                raise LegacyFeatureImportValidationError(
                    "Canonical review event changed during import"
                )
        connection.execute(
            "UPDATE review_clock SET value = ? WHERE singleton_id = 1",
            (sequence,),
        )
        self._rebuild_deleted_at(connection)
        return imported, len(deduplicated_uids)

    @staticmethod
    def _insert_import_event(
        connection: sqlite3.Connection,
        *,
        event_uid: str,
        image_id: int,
        event_type: str,
        rating: object,
        source_key: str,
        sequence: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating, source,
                source_key, sequence
            )
            VALUES (?, ?, ?, ?, 'legacy_ratings', ?, ?)
            """,
            (
                event_uid,
                image_id,
                event_type,
                rating,
                source_key,
                sequence,
            ),
        )

    def _write_arena(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
    ) -> int:
        image_ids = self._image_ids(connection)
        inserted = 0
        source_hash = str(payload["sources"]["arena"]["sha256"])
        for item in payload["arena"]["mapped"]:
            source_id = int(item["source_id"])
            match_uid = (
                "legacy-arena-"
                + hashlib.sha256(
                    f"{source_hash}:{source_id}".encode()
                ).hexdigest()
            )
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO arena_matches(
                    match_uid, left_image_id, right_image_id,
                    winner_image_id, decision, source, source_key,
                    source_created_at, created_at
                )
                VALUES (?, ?, ?, ?, ?, 'legacy_arena', ?, ?, ?)
                """,
                (
                    match_uid,
                    image_ids[str(item["left_image_uid"])],
                    image_ids[str(item["right_image_uid"])],
                    image_ids[str(item["winner_image_uid"])],
                    str(item["decision"]),
                    f"match:{source_id}",
                    str(item["created_at"]),
                    str(item["created_at"]),
                ),
            )
            inserted += max(cursor.rowcount, 0)
        return inserted

    def _write_curation(
        self,
        connection: sqlite3.Connection,
        payload: dict[str, Any],
    ) -> int:
        image_ids = self._image_ids(connection)
        inserted = 0
        for item in payload["curation"]["mapped"]:
            cursor = connection.execute(
                """
                INSERT OR IGNORE INTO curation_assignments(
                    image_id, set_key, source, source_key
                )
                VALUES (?, ?, 'legacy_curation', ?)
                """,
                (
                    image_ids[str(item["image_uid"])],
                    str(item["set_key"]),
                    str(item["source_key"]),
                ),
            )
            inserted += max(cursor.rowcount, 0)
        return inserted

    @staticmethod
    def _validate_imported_aggregates(
        connection: sqlite3.Connection,
        payload: dict[str, Any],
    ) -> None:
        for expected in payload["parity"]["aggregates"]:
            row = connection.execute(
                """
                SELECT COUNT(*), COALESCE(SUM(event.rating), 0)
                FROM review_events AS event
                JOIN images AS image ON image.id = event.image_id
                WHERE image.image_uid = ?
                  AND event.event_type = 'rating'
                  AND event.source = 'legacy_ratings'
                """,
                (str(expected["image_uid"]),),
            ).fetchone()
            if row != (
                int(expected["rating_count"]),
                int(expected["rating_sum"]),
            ):
                raise LegacyFeatureImportValidationError(
                    "Imported rating aggregate parity failed"
                )

    @staticmethod
    def _rebuild_deleted_at(connection: sqlite3.Connection) -> None:
        connection.execute("UPDATE images SET deleted_at = NULL")
        connection.execute(
            """
            UPDATE images
            SET deleted_at = (
                SELECT COALESCE(event.source_created_at, event.created_at)
                FROM review_events AS event
                WHERE event.image_id = images.id
                  AND event.event_type IN ('delete', 'restore')
                ORDER BY event.sequence DESC
                LIMIT 1
            )
            WHERE (
                SELECT event.event_type
                FROM review_events AS event
                WHERE event.image_id = images.id
                  AND event.event_type IN ('delete', 'restore')
                ORDER BY event.sequence DESC
                LIMIT 1
            ) = 'delete'
            """
        )

    @staticmethod
    def _image_ids(connection: sqlite3.Connection) -> dict[str, int]:
        return {
            str(row[1]): int(row[0])
            for row in connection.execute("SELECT id, image_uid FROM images")
        }

    def _load_report(self, report_path: Path) -> dict[str, Any]:
        payload = json.loads(Path(report_path).read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise LegacyFeatureImportValidationError(
                "Legacy feature audit must contain a JSON object"
            )
        return payload

    def _source_paths(self) -> dict[str, Path]:
        return {
            "ratings": self._ratings_path,
            "arena": self._arena_path,
            "curation": self._curation_path,
            "images_projection": self._images_projection_path,
        }

    @staticmethod
    def _open_source(path: Path) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                f"{path.as_uri()}?mode=ro",
                uri=True,
            )
        except sqlite3.Error as error:
            raise LegacyFeatureImportValidationError(
                f"Cannot open legacy source read-only: {path}"
            ) from error
        connection.row_factory = sqlite3.Row
        return connection

    def _open_canonical_write(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            f"{self._canonical_path.as_uri()}?mode=rw",
            uri=True,
        )
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    @staticmethod
    def _require_columns(
        connection: sqlite3.Connection,
        table: str,
        required: set[str],
    ) -> None:
        columns = {
            str(row[1])
            for row in connection.execute(
                f'PRAGMA table_info("{table}")'
            ).fetchall()
        }
        missing = sorted(required - columns)
        if missing:
            raise LegacyFeatureImportValidationError(
                f"Legacy source table {table} is missing: "
                + ", ".join(missing)
            )

    @staticmethod
    def _rating(value: object) -> int:
        try:
            rating = int(str(value))
        except (TypeError, ValueError) as error:
            raise LegacyFeatureImportValidationError(
                "Legacy rating is not an integer"
            ) from error
        if not 1 <= rating <= 10:
            raise LegacyFeatureImportValidationError(
                "Legacy rating is outside 1..10"
            )
        return rating

    @staticmethod
    def _path_key(value: object) -> str:
        return os.path.normcase(str(Path(str(value)).resolve(strict=False)))

    @staticmethod
    def _sha256_file(path: Path) -> str:
        if not path.is_file():
            raise LegacyFeatureImportValidationError(
                f"Legacy source does not exist: {path}"
            )
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while chunk := handle.read(1024 * 1024):
                digest.update(chunk)
        return digest.hexdigest()

    def _create_backup(self, backup_directory: Path | None) -> Path:
        backup_root = Path(
            backup_directory
            if backup_directory is not None
            else self._canonical_path.parent / "backups"
        )
        run_directory = backup_root / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
            + f"_{uuid4().hex[:8]}"
        )
        backup_path = run_directory / self._canonical_path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)
        source = connect_read_only(self._canonical_path)
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        return backup_path

    def _canonical_is_valid(self) -> bool:
        try:
            CanonicalSchemaManager(self._canonical_path).validate()
        except (OSError, sqlite3.DatabaseError, RuntimeError):
            return False
        return True

    def _restore_backup(self, backup_path: Path) -> None:
        for suffix in ("-wal", "-shm"):
            Path(f"{self._canonical_path}{suffix}").unlink(missing_ok=True)
        shutil.copy2(backup_path, self._canonical_path)
