from __future__ import annotations

import sqlite3
from pathlib import Path


def db(path: Path) -> sqlite3.Connection:
    """Open a sqlite connection and ensure the schema exists."""
    path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    ensure_schema(con)
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    """Ensure playground_items schema, indices and triggers exist."""
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS playground_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,

            tags TEXT NOT NULL DEFAULT '',

            pos TEXT NOT NULL DEFAULT '',
            neg TEXT NOT NULL DEFAULT '',

            notes TEXT NOT NULL DEFAULT '',

            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_kind ON playground_items(kind)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_key ON playground_items(key)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_pg_name ON playground_items(name)")

    con.execute(
        """
        CREATE TRIGGER IF NOT EXISTS trg_pg_updated
        AFTER UPDATE ON playground_items
        FOR EACH ROW
        BEGIN
            UPDATE playground_items SET updated_at = datetime('now') WHERE id = NEW.id;
        END
        """
    )
