from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(db_path: Path) -> None:
    """Verify that the startup-managed job database still exists."""
    connect_existing(db_path).close()


def enqueue_job(db_path: Path, *, job_type: str = "catchup") -> int:
    """Enqueue a projection job or coalesce an existing catchup job."""
    con = connect_existing(db_path)
    try:
        now = _utc_now()

        # Debounce/coalesce catchup jobs:
        # - If a queued catchup job already exists, we only "touch" it.
        # - The MV worker will wait for a quiet window after the last touch.
        if str(job_type) == "catchup":
            row = con.execute(
                """
                SELECT id
                FROM mv_jobs
                WHERE job_type = 'catchup'
                  AND status = 'queued'
                ORDER BY id ASC
                LIMIT 1
                """
            ).fetchone()
            if row and row[0]:
                job_id = int(row[0])
                con.execute(
                    "UPDATE mv_jobs SET touched_at = ? WHERE id = ?",
                    (now, job_id),
                )
                con.commit()
                return job_id

        cur = con.execute(
            "INSERT INTO mv_jobs(job_type, created_at, touched_at, status, error) VALUES(?,?,?,?,NULL)",
            (str(job_type), now, now, "queued"),
        )
        con.commit()
        return int(cur.lastrowid or 0)
    finally:
        con.close()


def fetch_next_queued(db_path: Path) -> dict[str, Any] | None:
    """Return the oldest queued projection job, if one exists."""
    con = connect_existing(db_path, rows=True)
    try:
        row = con.execute(
            """
            SELECT id, job_type, created_at, touched_at, status, error
            FROM mv_jobs
            WHERE status = 'queued'
            ORDER BY id ASC
            LIMIT 1
            """
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def fetch_job(db_path: Path, *, job_id: int) -> dict[str, Any] | None:
    """Read a single job row by id."""
    con = connect_existing(db_path, rows=True)
    try:
        row = con.execute(
            """
            SELECT id, job_type, created_at, touched_at, status, error
            FROM mv_jobs
            WHERE id = ?
            LIMIT 1
            """,
            (int(job_id),),
        ).fetchone()
        return dict(row) if row else None
    finally:
        con.close()


def mark_running(db_path: Path, job_id: int) -> None:
    """Mark one projection job as running."""
    con = connect_existing(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='running', error=NULL WHERE id=?",
            (int(job_id),),
        )
        con.commit()
    finally:
        con.close()


def mark_done(db_path: Path, job_id: int) -> None:
    """Mark one projection job as completed."""
    con = connect_existing(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='done', error=NULL WHERE id=?",
            (int(job_id),),
        )
        con.commit()
    finally:
        con.close()


def mark_failed(db_path: Path, job_id: int, error: str) -> None:
    """Mark one projection job as failed with bounded error details."""
    con = connect_existing(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='failed', error=? WHERE id=?",
            (str(error), int(job_id)),
        )
        con.commit()
    finally:
        con.close()


def mark_all_queued_done(db_path: Path, *, up_to_job_id: int) -> None:
    """Complete queued jobs through an ID after catchup coalescing."""
    con = connect_existing(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='done', error=NULL WHERE status='queued' AND id <= ?",
            (int(up_to_job_id),),
        )
        con.commit()
    finally:
        con.close()


def recover_abandoned_running_jobs(db_path: Path) -> int:
    """Mark jobs left running by a previous process as failed."""
    con = connect_existing(db_path)
    try:
        cursor = con.execute(
            """
            UPDATE mv_jobs
            SET status = 'failed',
                error = 'abandoned during previous process; recovered at startup'
            WHERE status = 'running'
            """
        )
        con.commit()
        return int(cursor.rowcount or 0)
    finally:
        con.close()
