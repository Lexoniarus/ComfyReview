from __future__ import annotations

from pathlib import Path
from typing import Any

from .connection import db
from .kinds import validate_kind
from .keys import slugify_key, unique_key


def create_item(
    db_path: Path,
    *,
    kind: str,
    name: str,
    tags: str = "",
    pos: str = "",
    neg: str = "",
    notes: str = "",
) -> int:
    con = db(db_path)

    kind = validate_kind(kind)
    name = str(name or "").strip()
    if not name:
        con.close()
        raise ValueError("name ist Pflicht")

    base_key = slugify_key(name, suffix=f"_{kind}")
    key = unique_key(con, base_key)

    con.execute(
        """
        INSERT INTO playground_items(kind, name, key, tags, pos, neg, notes)
        VALUES(?,?,?,?,?,?,?)
        """,
        (kind, name, key, tags or "", pos or "", neg or "", notes or ""),
    )
    con.commit()

    row = con.execute("SELECT last_insert_rowid() AS id").fetchone()
    con.close()
    return int(row["id"])


def update_item(
    db_path: Path,
    *,
    item_id: int,
    kind: str,
    name: str,
    tags: str = "",
    pos: str = "",
    neg: str = "",
    notes: str = "",
    regenerate_key_on_rename: bool = True,
) -> None:
    con = db(db_path)

    item_id = int(item_id)
    kind = validate_kind(kind)
    name = str(name or "").strip()
    if not name:
        con.close()
        raise ValueError("name ist Pflicht")

    current = con.execute(
        "SELECT id, key, name, kind FROM playground_items WHERE id = ?",
        (item_id,),
    ).fetchone()
    if not current:
        con.close()
        raise ValueError("item nicht gefunden")

    key = str(current["key"])
    if regenerate_key_on_rename and (str(current["name"]) != name or str(current["kind"]) != kind):
        base_key = slugify_key(name, suffix=f"_{kind}")
        key = unique_key(con, base_key)

    con.execute(
        """
        UPDATE playground_items
        SET kind = ?, name = ?, key = ?, tags = ?, pos = ?, neg = ?, notes = ?
        WHERE id = ?
        """,
        (kind, name, key, tags or "", pos or "", neg or "", notes or "", item_id),
    )
    con.commit()
    con.close()


def delete_item(db_path: Path, item_id: int) -> None:
    con = db(db_path)
    con.execute("DELETE FROM playground_items WHERE id = ?", (int(item_id),))
    con.commit()
    con.close()
