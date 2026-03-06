from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from config import PLAYGROUND_DB_PATH
from stores.playground_store import list_items


def load_playground_dropdown_items(db_path: Path = PLAYGROUND_DB_PATH) -> Dict[str, List[Dict[str, Any]]]:
    """Load all dropdown item lists for the generator page."""

    return {
        "characters": list_items(db_path, kind="character", q="", limit=2000),
        "scenes": list_items(db_path, kind="scene", q="", limit=2000),
        "outfits": list_items(db_path, kind="outfit", q="", limit=2000),
        "poses": list_items(db_path, kind="pose", q="", limit=2000),
        "expressions": list_items(db_path, kind="expression", q="", limit=2000),
        "lightings": list_items(db_path, kind="lighting", q="", limit=2000),
        "modifiers": list_items(db_path, kind="modifier", q="", limit=2000),
    }
