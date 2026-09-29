from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.repositories.sqlite import connect_existing


def db(path: Path) -> sqlite3.Connection:
    """Open an existing playground database without changing its schema."""
    return connect_existing(path, rows=True)
