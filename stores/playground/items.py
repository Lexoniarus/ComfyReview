from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .connection import db
from .kinds import validate_kind


def list_recent_items(db_path: Path, *, kind: str, limit: int = 10) -> List[Dict[str, Any]]:
    k = validate_kind(kind)
    con = db(db_path)
    rows = con.execute(
        "SELECT * FROM playground_items WHERE kind = ? ORDER BY updated_at DESC, id DESC LIMIT ?",
        (k, int(limit)),
    ).fetchall()
    con.close()
    return [dict(r) for r in rows]


def list_items(
    db_path: Path,
    *,
    kind: str = "",
    q: str = "",
    limit: int = 500,
    offset: int = 0,
) -> List[Dict[str, Any]]:
    """List items with optional kind and query filters."""
    con = db(db_path)

    where = "WHERE 1=1"
    args: List[Any] = []
    if kind:
        where += " AND kind = ?"
        args.append(validate_kind(kind))
    if q:
        where += " AND (name LIKE ? OR key LIKE ? OR tags LIKE ?)"
        like = f"%{q}%"
        args.extend([like, like, like])

    rows = con.execute(
        f"""
        SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
        FROM playground_items
        {where}
        ORDER BY kind ASC, name ASC
        LIMIT ?
        OFFSET ?
        """,
        args + [int(limit), int(offset)],
    ).fetchall()

    con.close()
    return [dict(r) for r in rows]


def get_item(db_path: Path, item_id: int) -> Optional[Dict[str, Any]]:
    con = db(db_path)
    row = con.execute(
        """
        SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
        FROM playground_items
        WHERE id = ?
        """,
        (int(item_id),),
    ).fetchone()
    con.close()
    return dict(row) if row else None


def get_items_by_ids(db_path: Path, item_ids: List[int]) -> Dict[int, Dict[str, Any]]:
    ids = [int(x) for x in (item_ids or [])]
    if not ids:
        return {}

    con = db(db_path)
    try:
        qmarks = ",".join(["?"] * len(ids))
        rows = con.execute(
            f"""
            SELECT id, kind, name, key, tags, pos, neg, notes, created_at, updated_at
            FROM playground_items
            WHERE id IN ({qmarks})
            """,
            ids,
        ).fetchall()
        return {int(r["id"]): dict(r) for r in rows}
    finally:
        con.close()


# Backwards-compatible naming (used by Generator and existing routers)

def get_item_by_id(db_path: Path, item_id: int) -> Optional[Dict[str, Any]]:
    return get_item(db_path, item_id)


def get_items_by_kind(db_path: Path, kind: str, *, limit: int = 500) -> List[Dict[str, Any]]:
    return list_items(db_path, kind=validate_kind(kind), limit=int(limit))
