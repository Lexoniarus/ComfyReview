from __future__ import annotations

import re
import sqlite3
import unicodedata


def slugify_key(name: str, *, suffix: str = "") -> str:
    """Convert a user name into a stable key."""
    s = str(name or "").strip().lower()
    if not s:
        s = "item"

    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))

    s = re.sub(r"[^a-z0-9]+", "_", s)
    s = re.sub(r"_+", "_", s).strip("_")

    if suffix:
        s = f"{s}{suffix}"
    return s


def unique_key(con: sqlite3.Connection, base_key: str) -> str:
    """Ensure key is unique in playground_items by appending _2, _3, ..."""
    k = base_key
    i = 2
    while True:
        row = con.execute("SELECT 1 FROM playground_items WHERE key = ? LIMIT 1", (k,)).fetchone()
        if not row:
            return k
        k = f"{base_key}_{i}"
        i += 1
