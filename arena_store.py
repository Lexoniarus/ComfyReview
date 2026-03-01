import sqlite3
from pathlib import Path
from typing import Optional


def ensure_schema(db_path: Path) -> None:
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS arena_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                left_json TEXT NOT NULL,
                right_json TEXT NOT NULL,
                winner_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                run INTEGER
            )
            """
        )
        con.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS ux_arena_left_right
            ON arena_matches(left_json, right_json)
            """
        )
        con.commit()
    finally:
        con.close()


def has_match(db_path: Path, left_json: str, right_json: str) -> bool:
    con = sqlite3.connect(str(db_path))
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
    run: Optional[int] = None,
) -> None:
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            """
            INSERT INTO arena_matches(left_json, right_json, winner_json, created_at, run)
            VALUES (?, ?, ?, ?, ?)
            """,
            (left_json, right_json, winner_json, created_at, run),
        )
        con.commit()
    finally:
        con.close()