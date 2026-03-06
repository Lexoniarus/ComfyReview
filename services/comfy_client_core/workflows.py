from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict


def get_or_create_workflow_path(
    *,
    workflows_dir: Path,
    character_name: str,
    default_workflow_path: Path,
) -> Path:
    """Return workflow path for character, copying default if missing."""

    base = Path(workflows_dir)
    base.mkdir(parents=True, exist_ok=True)

    safe_name = (character_name or "").strip() or "output"
    dst = base / f"{safe_name}.json"

    if dst.exists():
        return dst

    default_path = Path(default_workflow_path)
    if not default_path.exists():
        raise FileNotFoundError(f"default workflow fehlt: {default_path}")

    shutil.copyfile(str(default_path), str(dst))
    return dst


def load_workflow(path: Path) -> Dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"workflow nicht gefunden: {p}")
    return json.loads(p.read_text(encoding="utf-8"))
