"""SQLite adapters for current legacy review persistence boundaries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import (
    PromptProjection,
    ReviewRecord,
    StoredReview,
)
from comfyreview.repositories.sqlite.connection import connect_existing
from stores.mv_jobs_store import enqueue_job


def _tokenize(prompt: str) -> tuple[str, ...]:
    normalized = str(prompt or "").replace("\n", " ")
    return tuple(
        part.strip() for part in normalized.split(",") if part.strip()
    )


class SqliteReviewRepository:
    """Persist review events in the existing legacy ratings database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def append(self, record: ReviewRecord) -> StoredReview:
        """Append one review event and return its exact ID and run."""
        image = record.image
        connection = connect_existing(self._database_path, rows=True)
        try:
            row = connection.execute(
                """
                SELECT COALESCE(MAX(run), 0) AS maximum_run
                FROM ratings
                WHERE json_path = ?
                """,
                (str(image.pair.json_path),),
            ).fetchone()
            run = int(row["maximum_run"] or 0) + 1
            cursor = connection.execute(
                """
                INSERT INTO ratings(
                    png_path, json_path, run, model_branch, checkpoint,
                    combo_key, rating, deleted, rating_count, steps, cfg,
                    sampler, scheduler, denoise, loras_json, pos_prompt,
                    neg_prompt
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(image.pair.png_path),
                    str(image.pair.json_path),
                    run,
                    image.model_branch,
                    image.checkpoint,
                    image.combo_key,
                    record.rating,
                    int(record.deleted),
                    run,
                    image.steps,
                    image.cfg,
                    image.sampler,
                    image.scheduler,
                    image.denoise,
                    image.loras_json,
                    image.positive_prompt,
                    image.negative_prompt,
                ),
            )
            review_id = int(cursor.lastrowid or 0)
            connection.commit()
            return StoredReview(review_id=review_id, run=run)
        finally:
            connection.close()

    def delete(self, review_id: int) -> None:
        """Delete one review event as legacy workflow compensation."""
        connection = connect_existing(self._database_path)
        try:
            connection.execute(
                "DELETE FROM ratings WHERE id = ?",
                (int(review_id),),
            )
            connection.commit()
        finally:
            connection.close()


class SqlitePromptRepository:
    """Persist raw prompt tokens in the current projection database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def save(self, projection: PromptProjection) -> None:
        """Replace prompt tokens for one exact review run."""
        connection = connect_existing(self._database_path)
        try:
            self._delete_rows(
                connection,
                projection.json_path,
                projection.run,
            )
            self._insert_tokens(
                connection,
                projection,
                "pos",
                _tokenize(projection.positive_prompt),
            )
            self._insert_tokens(
                connection,
                projection,
                "neg",
                _tokenize(projection.negative_prompt),
            )
            connection.commit()
        finally:
            connection.close()

    def delete(self, json_path: Path, run: int) -> None:
        """Delete prompt rows for one compensated review run."""
        connection = connect_existing(self._database_path)
        try:
            self._delete_rows(connection, json_path, run)
            connection.commit()
        finally:
            connection.close()

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
    def _insert_tokens(
        connection: sqlite3.Connection,
        projection: PromptProjection,
        scope: str,
        tokens: tuple[str, ...],
    ) -> None:
        for token in tokens:
            connection.execute(
                """
                INSERT INTO tokens(
                    json_path, run, model_branch, scope, token, rating, deleted
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


class LegacyProjectionJobQueue:
    """Adapt the existing coalescing projection queue to the review port."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def request_catchup(self) -> int:
        """Request one queued or coalesced legacy catchup job."""
        return enqueue_job(self._database_path, job_type="catchup")
