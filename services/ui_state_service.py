from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional


def load_json_state(path: Path) -> Dict[str, Any]:
    """Load a small UI state JSON file.

    Returns an empty dict if the file does not exist or is invalid.
    """
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json_state(path: Path, data: Dict[str, Any]) -> None:
    """Persist a small UI state JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_int(value: Optional[str]) -> Optional[int]:
    """Parse user input into int, supports floats like "3.0"."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None
