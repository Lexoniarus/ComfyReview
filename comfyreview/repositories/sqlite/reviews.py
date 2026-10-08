"""SQLite adapters for canonical review persistence and legacy projections."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from comfyreview.application import (
    ReviewHistoryEntry,
    ReviewRecord,
    StoredReview,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteReviewHistoryRepository:
    """Read append-only review events from canonical SQLite facts."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_for_image(
        self, image_uid: str
    ) -> tuple[ReviewHistoryEntry, ...] | None:
        """Return ordered review events or None for an unknown image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            image = connection.execute(
                "SELECT id FROM images WHERE image_uid = ?",
                (image_uid,),
            ).fetchone()
            if image is None:
                return None
            rows = connection.execute(
                """
                SELECT
                    event_uid,
                    event_type,
                    rating,
                    sequence,
                    COALESCE(source_created_at, created_at) AS reviewed_at
                FROM review_events
                WHERE image_id = ?
                ORDER BY sequence DESC, id DESC
                """,
                (int(image["id"]),),
            ).fetchall()
            return tuple(
                ReviewHistoryEntry(
                    event_uid=str(row["event_uid"]),
                    event_type=str(row["event_type"]),
                    rating=(
                        int(row["rating"])
                        if row["rating"] is not None
                        else None
                    ),
                    sequence=int(row["sequence"]),
                    reviewed_at=str(row["reviewed_at"]),
                )
                for row in rows
            )
        finally:
            connection.close()


class SqliteReviewRepository:
    """Persist current reviews, generations, atoms, and learning aggregates."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def append(self, record: ReviewRecord) -> StoredReview:
        """Atomically apply one rating replacement or delete observation."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            self._require_canonical_schema(connection)
            connection.execute("BEGIN IMMEDIATE")
            image_id, generation_id = self._resolve_image_identity(
                connection,
                record,
            )
            return self._append_canonical_event(
                connection,
                record,
                generation_id=generation_id,
                image_id=image_id,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _resolve_image_identity(
        connection: sqlite3.Connection,
        record: ReviewRecord,
    ) -> tuple[int, int]:
        row = connection.execute(
            """
            SELECT image.id AS image_id, generation.id AS generation_id
            FROM images AS image
            JOIN generations AS generation
                ON generation.id = image.generation_id
            WHERE image.image_uid = ?
              AND generation.generation_uid = ?
            """,
            (record.image.image_uid, record.image.generation_uid),
        ).fetchone()
        if row is None:
            raise RuntimeError(
                "Canonical review image identity is unavailable"
            )
        return int(row["image_id"]), int(row["generation_id"])

    def _append_canonical_event(
        self,
        connection: sqlite3.Connection,
        record: ReviewRecord,
        *,
        generation_id: int,
        image_id: int,
    ) -> StoredReview:
        state = connection.execute(
            "SELECT deleted_at FROM images WHERE id = ?",
            (image_id,),
        ).fetchone()
        if state is None:
            raise RuntimeError("Canonical image state is unavailable")
        prior_deleted = state["deleted_at"] is not None
        previous = connection.execute(
            "SELECT id, rating FROM image_reviews WHERE image_id = ?",
            (image_id,),
        ).fetchone()
        if prior_deleted:
            self._apply_learning_delta(
                connection,
                generation_id=generation_id,
                image_id=image_id,
                rating=0,
                deleted=True,
                delta=-1,
            )
        if previous is not None:
            self._apply_learning_delta(
                connection,
                generation_id=generation_id,
                image_id=image_id,
                rating=int(previous["rating"]),
                deleted=False,
                delta=-1,
            )

        if record.deleted:
            version = self._next_version(connection)
            review_id = self._insert_review_event(
                connection,
                image_id=image_id,
                event_type="delete",
                rating=None,
                sequence=version,
            )
            connection.execute(
                "UPDATE images SET deleted_at = datetime('now') WHERE id = ?",
                (image_id,),
            )
            self._apply_learning_delta(
                connection,
                generation_id=generation_id,
                image_id=image_id,
                rating=0,
                deleted=True,
                delta=1,
            )
        else:
            if prior_deleted:
                restore_sequence = self._next_version(connection)
                self._insert_review_event(
                    connection,
                    image_id=image_id,
                    event_type="restore",
                    rating=None,
                    sequence=restore_sequence,
                )
            connection.execute(
                "UPDATE images SET deleted_at = NULL WHERE id = ?",
                (image_id,),
            )
            version = self._next_version(connection)
            rating = int(record.rating or 0)
            review_id = self._insert_review_event(
                connection,
                image_id=image_id,
                event_type="rating",
                rating=rating,
                sequence=version,
            )
            self._apply_learning_delta(
                connection,
                generation_id=generation_id,
                image_id=image_id,
                rating=rating,
                deleted=False,
                delta=1,
            )
        connection.commit()
        return StoredReview(review_id=review_id, run=version)

    @staticmethod
    def _insert_review_event(
        connection: sqlite3.Connection,
        *,
        image_id: int,
        event_type: str,
        rating: int | None,
        sequence: int,
    ) -> int:
        event_uid = f"runtime-{uuid4()}"
        cursor = connection.execute(
            """
            INSERT INTO review_events(
                event_uid,
                image_id,
                event_type,
                rating,
                source,
                source_key,
                sequence
            )
            VALUES (?, ?, ?, ?, 'runtime', ?, ?)
            """,
            (
                event_uid,
                image_id,
                event_type,
                rating,
                event_uid,
                sequence,
            ),
        )
        return int(cursor.lastrowid or 0)

    @staticmethod
    def _require_canonical_schema(
        connection: sqlite3.Connection,
    ) -> None:
        rows = dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE name IN ('schema_metadata', 'review_events', "
                "'image_reviews')"
            ).fetchall()
        )
        if rows != {
            "schema_metadata": "table",
            "review_events": "table",
            "image_reviews": "view",
        }:
            raise RuntimeError("Canonical schema v4 is required for reviews")

    def _next_version(self, connection: sqlite3.Connection) -> int:
        connection.execute(
            "UPDATE review_clock SET value = value + 1 WHERE singleton_id = 1"
        )
        row = connection.execute(
            "SELECT value FROM review_clock WHERE singleton_id = 1"
        ).fetchone()
        if row is None:
            raise RuntimeError("Review clock is unavailable")
        return int(row["value"])

    def _apply_learning_delta(
        self,
        connection: sqlite3.Connection,
        *,
        generation_id: int,
        image_id: int,
        rating: int,
        deleted: bool,
        delta: int,
    ) -> None:
        generation = connection.execute(
            """
            SELECT
                model_branch,
                checkpoint,
                sampler,
                scheduler,
                steps,
                cfg,
                denoise
            FROM generations
            WHERE id = ?
            """,
            (generation_id,),
        ).fetchone()
        if generation is None:
            raise RuntimeError("Generation missing during learning update")
        score = 0 if deleted else int(rating)
        memberships = connection.execute(
            """
            SELECT usage.atom_id, usage.scope, usage.weight_milli
            FROM current_image_catalog_compositions AS current_catalog
            JOIN image_catalog_composition_revisions AS membership
              ON membership.composition_id = current_catalog.composition_id
            JOIN prompt_revision_atom_usages AS usage
              ON usage.revision_id = membership.revision_id
            WHERE current_catalog.image_id = ?
            ORDER BY membership.position, usage.scope, usage.position
            """,
            (image_id,),
        ).fetchall()
        if not memberships:
            raise RuntimeError(
                "Current catalog composition is unavailable for review"
            )
        for membership in memberships:
            self._update_atom_stat(
                connection,
                atom_id=int(membership["atom_id"]),
                scope=str(membership["scope"]),
                model_branch=str(generation["model_branch"] or ""),
                weight_milli=int(membership["weight_milli"]),
                score=score,
                deleted=deleted,
                delta=delta,
            )
        self._update_render_stat(
            connection,
            generation=generation,
            score=score,
            deleted=deleted,
            delta=delta,
        )

    def _update_atom_stat(
        self,
        connection: sqlite3.Connection,
        *,
        atom_id: int,
        scope: str,
        model_branch: str,
        weight_milli: int,
        score: int,
        deleted: bool,
        delta: int,
    ) -> None:
        connection.execute(
            """
            INSERT INTO atom_learning_stats(
                atom_id,
                scope,
                model_branch,
                weight_milli,
                sample_count,
                rating_sum,
                rating_sq_sum,
                deleted_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(atom_id, scope, model_branch, weight_milli)
            DO UPDATE SET
                sample_count = sample_count + excluded.sample_count,
                rating_sum = rating_sum + excluded.rating_sum,
                rating_sq_sum = rating_sq_sum + excluded.rating_sq_sum,
                deleted_count = deleted_count + excluded.deleted_count
            """,
            (
                atom_id,
                scope,
                model_branch,
                weight_milli,
                delta,
                delta * score,
                delta * score * score,
                delta if deleted else 0,
            ),
        )
        connection.execute(
            """
            DELETE FROM atom_learning_stats
            WHERE atom_id = ?
              AND scope = ?
              AND model_branch = ?
              AND weight_milli = ?
              AND sample_count <= 0
            """,
            (atom_id, scope, model_branch, weight_milli),
        )

    def _update_render_stat(
        self,
        connection: sqlite3.Connection,
        *,
        generation: sqlite3.Row,
        score: int,
        deleted: bool,
        delta: int,
    ) -> None:
        sampler = str(generation["sampler"] or "")
        scheduler = str(generation["scheduler"] or "")
        steps = int(generation["steps"] or -1)
        cfg_milli = self._to_milli(generation["cfg"])
        denoise_milli = self._to_milli(generation["denoise"])
        key: tuple[str, str, str, str, int, int, int] = (
            str(generation["model_branch"] or ""),
            str(generation["checkpoint"] or ""),
            sampler,
            scheduler,
            steps,
            cfg_milli,
            denoise_milli,
        )
        connection.execute(
            """
            INSERT INTO render_learning_stats(
                model_branch,
                checkpoint,
                sampler,
                scheduler,
                steps,
                cfg_milli,
                denoise_milli,
                sample_count,
                rating_sum,
                rating_sq_sum,
                deleted_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(
                model_branch,
                checkpoint,
                sampler,
                scheduler,
                steps,
                cfg_milli,
                denoise_milli
            ) DO UPDATE SET
                sample_count = sample_count + excluded.sample_count,
                rating_sum = rating_sum + excluded.rating_sum,
                rating_sq_sum = rating_sq_sum + excluded.rating_sq_sum,
                deleted_count = deleted_count + excluded.deleted_count
            """,
            (
                *key,
                delta,
                delta * score,
                delta * score * score,
                delta if deleted else 0,
            ),
        )
        connection.execute(
            """
            DELETE FROM render_learning_stats
            WHERE model_branch = ?
              AND checkpoint = ?
              AND sampler = ?
              AND scheduler = ?
              AND steps = ?
              AND cfg_milli = ?
              AND denoise_milli = ?
              AND sample_count <= 0
            """,
            key,
        )

    @staticmethod
    def _to_milli(value: object) -> int:
        if value is None:
            return -1
        text = str(value).strip()
        if not text:
            return -1
        return round(float(text) * 1000)
