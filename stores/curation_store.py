import sqlite3
from pathlib import Path
from typing import Dict, Iterable, Optional


def init_curation_db(db_path: Path) -> None:
    """Create curation DB schema if needed.

    vNext rule:
    - single label per image (png_path -> set_key)
    - set_key NULL means "unsorted"
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS curation (
              png_path TEXT PRIMARY KEY,
              set_key  TEXT
            )
            """
        )
        con.commit()
    finally:
        con.close()


def fetch_set_map(db_path: Path, png_paths: Iterable[str]) -> Dict[str, Optional[str]]:
    """Bulk fetch mapping for many png_paths."""
    init_curation_db(db_path)
    paths = [str(p) for p in (png_paths or []) if str(p).strip()]
    if not paths:
        return {}

    out: Dict[str, Optional[str]] = {}
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        # chunk to avoid SQLite parameter limits
        chunk_size = 900
        for i in range(0, len(paths), chunk_size):
            chunk = paths[i : i + chunk_size]
            qmarks = ",".join(["?"] * len(chunk))
            rows = con.execute(
                f"SELECT png_path, set_key FROM curation WHERE png_path IN ({qmarks})",
                chunk,
            ).fetchall()
            for r in rows:
                out[str(r["png_path"])] = (str(r["set_key"]) if r["set_key"] is not None else None)
        return out
    finally:
        con.close()


def upsert_set_key(db_path: Path, *, png_path: str, set_key: Optional[str]) -> None:
    """Set or clear set_key for an image."""
    init_curation_db(db_path)
    p = str(png_path or "").strip()
    if not p:
        return

    con = sqlite3.connect(db_path)
    try:
        if set_key is None or str(set_key).strip() == "":
            con.execute("DELETE FROM curation WHERE png_path = ?", [p])
        else:
            con.execute(
                """
                INSERT INTO curation(png_path, set_key)
                VALUES(?, ?)
                ON CONFLICT(png_path) DO UPDATE SET set_key=excluded.set_key
                """,
                [p, str(set_key)],
            )
        con.commit()
    finally:
        con.close()
