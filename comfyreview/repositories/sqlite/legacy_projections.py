"""SQLite adapters retained for legacy projection processing."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import PromptProjection
from comfyreview.repositories.sqlite.connection import connect_existing
from stores.mv_jobs_store import enqueue_job


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
