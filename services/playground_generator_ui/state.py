from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from services.ui_state_service import load_json_state, save_json_state


def load_head_state(state_path: Path) -> Dict[str, Any]:
    """Load generator head state from disk."""
    return dict(load_json_state(state_path) or {})


def save_head_state(state_path: Path, state: Dict[str, Any]) -> None:
    """Persist generator head state to disk."""
    save_json_state(state_path, dict(state or {}))


def load_preview_state(preview_path: Path) -> List[Dict[str, Any]]:
    """Load preview drafts list from disk."""
    d = load_json_state(preview_path) or {}
    drafts = d.get("drafts")
    if isinstance(drafts, list):
        return [dict(x) for x in drafts]
    return []


def save_preview_state(preview_path: Path, drafts: List[Dict[str, Any]]) -> None:
    """Persist preview drafts list to disk."""
    save_json_state(preview_path, {"drafts": [dict(x) for x in (drafts or [])]})


def clear_preview_state(preview_path: Path) -> None:
    """Clear preview drafts list on disk."""
    save_json_state(preview_path, {"drafts": []})
