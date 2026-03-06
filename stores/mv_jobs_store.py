from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


def _utc_now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS mv_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_type TEXT NOT NULL,
                created_at TEXT NOT NULL,
                touched_at TEXT,
                status TEXT NOT NULL,
                error TEXT
            )
            """
        )
        # Lightweight in-place migration for older DBs.
        cols = {r[1] for r in con.execute("PRAGMA table_info(mv_jobs)").fetchall()}
        if "touched_at" not in cols:
            con.execute("ALTER TABLE mv_jobs ADD COLUMN touched_at TEXT")
            con.execute("UPDATE mv_jobs SET touched_at = created_at WHERE touched_at IS NULL")
        con.execute("CREATE INDEX IF NOT EXISTS idx_mv_jobs_status ON mv_jobs(status)")
        con.commit()
    finally:
        con.close()


def enqueue_job(db_path: Path, *, job_type: str = "catchup") -> int:
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
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


def fetch_next_queued(db_path: Path) -> Optional[Dict[str, Any]]:
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
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


def fetch_job(db_path: Path, *, job_id: int) -> Optional[Dict[str, Any]]:
    """Read a single job row by id."""
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
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
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='running', error=NULL WHERE id=?",
            (int(job_id),),
        )
        con.commit()
    finally:
        con.close()


def mark_done(db_path: Path, job_id: int) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='done', error=NULL WHERE id=?",
            (int(job_id),),
        )
        con.commit()
    finally:
        con.close()


def mark_failed(db_path: Path, job_id: int, error: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='failed', error=? WHERE id=?",
            (str(error), int(job_id)),
        )
        con.commit()
    finally:
        con.close()


def mark_all_queued_done(db_path: Path, *, up_to_job_id: int) -> None:
    """Mark queued jobs up to a given id as done (coalesce redundant catchup jobs)."""
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            "UPDATE mv_jobs SET status='done', error=NULL WHERE status='queued' AND id <= ?",
            (int(up_to_job_id),),
        )
        con.commit()
    finally:
        con.close()
