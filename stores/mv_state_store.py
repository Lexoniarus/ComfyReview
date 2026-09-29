from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def _utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S")


def ensure_schema(db_path: Path) -> None:
    """Verify that the startup-managed state database still exists."""
    connect_existing(db_path).close()


def get_state(db_path: Path, *, aggregator_name: str) -> dict[str, Any]:
    """Return an aggregator state, creating its initial row when absent."""
    con = connect_existing(db_path, rows=True)
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
    con = connect_existing(db_path)
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
    con = connect_existing(db_path, rows=True)
    try:
        rows = con.execute(
            "SELECT aggregator_name, last_processed_rating_id, last_run_at, last_error FROM mv_state ORDER BY aggregator_name ASC"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
