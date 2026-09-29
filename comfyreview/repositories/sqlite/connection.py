"""SQLite connection helpers that never create database files."""

from __future__ import annotations

import sqlite3
from pathlib import Path


def connect_existing(
    database_path: Path,
    *,
    rows: bool = False,
) -> sqlite3.Connection:
    """Open an existing SQLite database in read-write mode."""
    path = Path(database_path).resolve()
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database does not exist: {path}")
    connection = sqlite3.connect(f"{path.as_uri()}?mode=rw", uri=True)
    if rows:
        connection.row_factory = sqlite3.Row
    return connection
