from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def max_rating_id(ratings_db_path: Path) -> int:
    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT COALESCE(MAX(id), 0) AS m FROM ratings").fetchone()
        return int(row["m"] or 0)
    finally:
        con.close()


def max_queued_job_id(queue_db_path: Path) -> int:
    con = sqlite3.connect(queue_db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT COALESCE(MAX(id), 0) AS m FROM mv_jobs WHERE status='queued'"
        ).fetchone()
        return int(row["m"] or 0)
    finally:
        con.close()


def fetch_ratings_rows(
    ratings_db_path: Path,
    *,
    start_id_exclusive: int,
    end_id_inclusive: int,
) -> List[Dict[str, Any]]:
    """Fetch rating rows within an id range (exclusive/inclusive)."""
    if int(end_id_inclusive) <= int(start_id_exclusive):
        return []

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT id, png_path, json_path, run, model_branch, pos_prompt, neg_prompt, rating, deleted
            FROM ratings
            WHERE id > ?
              AND id <= ?
            ORDER BY id ASC
            """,
            (int(start_id_exclusive), int(end_id_inclusive)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
