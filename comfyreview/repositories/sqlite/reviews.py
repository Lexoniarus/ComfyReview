"""SQLite adapters for canonical review persistence and legacy projections."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from comfyreview.application import (
    PromptProjection,
    ReviewRecord,
    StoredReview,
)
from comfyreview.repositories.sqlite.connection import connect_existing
from stores.mv_jobs_store import enqueue_job


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

    def delete(self, review_id: int) -> None:
        """Reject deletion because canonical review history is append-only."""
        del review_id
        raise RuntimeError("Canonical review events are append-only")

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
                rating=0,
                deleted=True,
                delta=-1,
            )
        if previous is not None:
            self._apply_learning_delta(
                connection,
                generation_id=generation_id,
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
                denoise,
                positive_prompt_id,
                negative_prompt_id
            FROM generations
            WHERE id = ?
            """,
            (generation_id,),
        ).fetchone()
        if generation is None:
            raise RuntimeError("Generation missing during learning update")
        score = 0 if deleted else int(rating)
        for scope, prompt_id in (
            ("pos", int(generation["positive_prompt_id"])),
            ("neg", int(generation["negative_prompt_id"])),
        ):
            memberships = connection.execute(
                """
                SELECT atom_id, weight_milli
                FROM prompt_memberships
                WHERE prompt_id = ?
                """,
                (prompt_id,),
            ).fetchall()
            for membership in memberships:
                self._update_atom_stat(
                    connection,
                    atom_id=int(membership["atom_id"]),
                    scope=scope,
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


class SqlitePromptRepository:
    """Compatibility adapter for old token tables and canonical token views."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def save(self, projection: PromptProjection) -> None:
        """Write only to a physical legacy token table."""
        connection = connect_existing(self._database_path)
        try:
            if self._tokens_object_type(connection) != "table":
                return
            self._delete_rows(connection, projection.json_path, projection.run)
            for scope, prompt in (
                ("pos", projection.positive_prompt),
                ("neg", projection.negative_prompt),
            ):
                for token in self._legacy_tokenize(prompt):
                    connection.execute(
                        """
                        INSERT INTO tokens(
                            json_path, run, model_branch, scope, token,
                            rating, deleted
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(projection.json_path),
                            projection.run,
                            projection.model_branch,
                            scope,
                            token,
                            projection.rating,
                            int(projection.deleted),
                        ),
                    )
            connection.commit()
        finally:
            connection.close()

    def delete(self, json_path: Path, run: int) -> None:
        """Delete only physical legacy token rows."""
        connection = connect_existing(self._database_path)
        try:
            if self._tokens_object_type(connection) != "table":
                return
            self._delete_rows(connection, json_path, run)
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _tokens_object_type(connection: sqlite3.Connection) -> str:
        row = connection.execute(
            "SELECT type FROM sqlite_master WHERE name = 'tokens'"
        ).fetchone()
        return str(row[0]) if row else ""

    @staticmethod
    def _delete_rows(
        connection: sqlite3.Connection,
        json_path: Path,
        run: int,
    ) -> None:
        connection.execute(
            "DELETE FROM tokens WHERE json_path = ? AND run = ?",
            (str(json_path), int(run)),
        )

    @staticmethod
    def _legacy_tokenize(prompt: str) -> tuple[str, ...]:
        normalized = str(prompt or "").replace("\n", " ")
        return tuple(
            part.strip() for part in normalized.split(",") if part.strip()
        )


class LegacyProjectionJobQueue:
    """Adapt the existing coalescing projection queue to the review port."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def request_catchup(self) -> int:
        """Request one queued or coalesced catchup job."""
        return enqueue_job(self._database_path, job_type="catchup")
