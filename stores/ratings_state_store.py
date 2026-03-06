from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _chunks(xs: List[str], size: int = 900) -> Iterable[List[str]]:
    for i in range(0, len(xs), size):
        yield xs[i : i + size]


def fetch_latest_deleted_by_png_paths(
    ratings_db_path: Path,
    png_paths: List[str],
    *,
    model_branch: str = "",
) -> Dict[str, int]:
    """Return latest deleted flag per png_path.

    Regeln
    - Latest = MAX(id) (AUTOINCREMENT) for the given png_path.
    - deleted=1 means the image is logically deleted, even if older rating rows exist.

    Why MAX(id) instead of run
    - run is domain-specific and may not be strictly monotonic across edge-cases.
    - id is monotonic for inserts.

    Returns
    - dict[png_path] = 0 or 1 (missing -> 0)
    """
    paths = [str(p).strip() for p in (png_paths or []) if str(p).strip()]
    if not paths:
        return {}

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        out: Dict[str, int] = {}
        for chunk in _chunks(paths):
            qmarks = ",".join(["?"] * len(chunk))
            args: List[Any] = list(chunk)
            extra = ""
            if model_branch:
                extra = " AND model_branch = ?"
                args.append(str(model_branch))

            rows = con.execute(
                f"""
                SELECT r.png_path, COALESCE(r.deleted, 0) AS deleted
                FROM ratings r
                JOIN (
                  SELECT png_path, MAX(id) AS max_id
                  FROM ratings
                  WHERE png_path IN ({qmarks}){extra}
                  GROUP BY png_path
                ) m
                  ON r.png_path = m.png_path AND r.id = m.max_id
                """,
                args,
            ).fetchall()

            for r in rows:
                out[str(r["png_path"])] = 1 if int(r["deleted"] or 0) == 1 else 0
        return out
    finally:
        con.close()


def fetch_latest_deleted_by_json_paths(
    ratings_db_path: Path,
    json_paths: List[str],
    *,
    model_branch: str = "",
) -> Dict[str, int]:
    """Return latest deleted flag per json_path (same semantics as png_path)."""
    paths = [str(p).strip() for p in (json_paths or []) if str(p).strip()]
    if not paths:
        return {}

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        out: Dict[str, int] = {}
        for chunk in _chunks(paths):
            qmarks = ",".join(["?"] * len(chunk))
            args: List[Any] = list(chunk)
            extra = ""
            if model_branch:
                extra = " AND model_branch = ?"
                args.append(str(model_branch))

            rows = con.execute(
                f"""
                SELECT r.json_path, COALESCE(r.deleted, 0) AS deleted
                FROM ratings r
                JOIN (
                  SELECT json_path, MAX(id) AS max_id
                  FROM ratings
                  WHERE json_path IN ({qmarks}){extra}
                  GROUP BY json_path
                ) m
                  ON r.json_path = m.json_path AND r.id = m.max_id
                """,
                args,
            ).fetchall()

            for r in rows:
                out[str(r["json_path"])] = 1 if int(r["deleted"] or 0) == 1 else 0
        return out
    finally:
        con.close()
