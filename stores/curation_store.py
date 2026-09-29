from collections.abc import Iterable
from pathlib import Path

from comfyreview.repositories.sqlite import connect_existing


def init_curation_db(db_path: Path) -> None:
    """Verify that the startup-managed curation database still exists."""
    connect_existing(db_path).close()


def fetch_set_map(
    db_path: Path, png_paths: Iterable[str]
) -> dict[str, str | None]:
    """Bulk fetch mapping for many png_paths."""
    paths = [str(p) for p in (png_paths or []) if str(p).strip()]
    if not paths:
        return {}

    out: dict[str, str | None] = {}
    con = connect_existing(db_path, rows=True)
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
                out[str(r["png_path"])] = (
                    str(r["set_key"]) if r["set_key"] is not None else None
                )
        return out
    finally:
        con.close()


def upsert_set_key(
    db_path: Path, *, png_path: str, set_key: str | None
) -> None:
    """Set or clear set_key for an image."""
    p = str(png_path or "").strip()
    if not p:
        return

    con = connect_existing(db_path)
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
