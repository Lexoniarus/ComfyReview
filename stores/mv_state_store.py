from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(db_path: Path) -> None:
    """Ensure that the legacy projection-state schema exists."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS mv_state (
                aggregator_name TEXT PRIMARY KEY,
                last_processed_rating_id INTEGER NOT NULL DEFAULT 0,
                last_run_at TEXT,
                last_error TEXT
            )
            """
        )
        con.commit()
    finally:
        con.close()


def get_state(db_path: Path, *, aggregator_name: str) -> dict[str, Any]:
    """Return an aggregator state, creating its initial row when absent."""
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT * FROM mv_state WHERE aggregator_name=?",
            (str(aggregator_name),),
        ).fetchone()
        if not row:
            # create default
            con.execute(
                "INSERT INTO mv_state(aggregator_name, last_processed_rating_id, last_run_at, last_error) VALUES(?,?,NULL,NULL)",
                (str(aggregator_name), 0),
            )
            con.commit()
            return {
                "aggregator_name": str(aggregator_name),
                "last_processed_rating_id": 0,
                "last_run_at": None,
                "last_error": None,
            }
        return dict(row)
    finally:
        con.close()


def upsert_state(
    db_path: Path,
    *,
    aggregator_name: str,
    last_processed_rating_id: int,
    last_run_at: str | None = None,
    last_error: str | None = None,
) -> None:
    """Insert or update one legacy aggregator state."""
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO mv_state(aggregator_name, last_processed_rating_id, last_run_at, last_error)
            VALUES(?,?,?,?)
            ON CONFLICT(aggregator_name) DO UPDATE SET
                last_processed_rating_id=excluded.last_processed_rating_id,
                last_run_at=excluded.last_run_at,
                last_error=excluded.last_error
            """,
            (
                str(aggregator_name),
                int(last_processed_rating_id),
                str(last_run_at) if last_run_at else _utc_now(),
                str(last_error) if last_error else None,
            ),
        )
        con.commit()
    finally:
        con.close()


def list_states(db_path: Path) -> list[dict[str, Any]]:
    """List all legacy aggregator states in stable name order."""
    ensure_schema(db_path)
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT aggregator_name, last_processed_rating_id, last_run_at, last_error FROM mv_state ORDER BY aggregator_name ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
