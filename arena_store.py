from pathlib import Path

from comfyreview.repositories.sqlite import connect_existing


def ensure_schema(db_path: Path) -> None:
    """Verify that the startup-managed Arena database still exists."""
    connect_existing(db_path).close()


def has_match(db_path: Path, left_json: str, right_json: str) -> bool:
    con = connect_existing(db_path)
    try:
        row = con.execute(
            """
            SELECT 1
            FROM arena_matches
            WHERE left_json = ? AND right_json = ?
            LIMIT 1
            """,
            (left_json, right_json),
        ).fetchone()
        return row is not None
    finally:
        con.close()


def insert_match(
    db_path: Path,
    left_json: str,
    right_json: str,
    winner_json: str,
    created_at: str,
    run: int | None = None,
) -> int:
    con = connect_existing(db_path)
    try:
        con.execute(
            """
            INSERT INTO arena_matches(left_json, right_json, winner_json, created_at, run)
            VALUES (?, ?, ?, ?, ?)
            """,
            (left_json, right_json, winner_json, created_at, run),
        )
        match_id = int(con.execute("SELECT last_insert_rowid()").fetchone()[0])
        con.commit()
        return match_id
    finally:
        con.close()


def delete_match(db_path: Path, *, match_id: int) -> None:
    """Delete one Arena match as compensation for a failed legacy workflow."""
    con = connect_existing(db_path)
    try:
        con.execute("DELETE FROM arena_matches WHERE id = ?", (int(match_id),))
        con.commit()
    finally:
        con.close()
