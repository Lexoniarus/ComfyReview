# routers/playground/_shared.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from config import OUTPUT_ROOT

# Persistierter Generator Zustand
GENERATOR_STATE_PATH = Path("data/ui_state/playground_generator_last.json")

# Transient Preview Batch State
GENERATOR_PREVIEW_STATE_PATH = Path("data/ui_state/playground_generator_preview.json")

# Cache fuer Discovery Listen (Checkpoints, Samplers, Schedulers)
COMFY_DISCOVERY_CACHE_PATH = Path("data/ui_state/comfy_discovery_cache.json")



def load_json_file(path: Path) -> Dict[str, Any]:
    try:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_json_file(path: Path, data: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def safe_int(value: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def png_path_to_url(png_path: str) -> str:
    """Baut eine /files URL aus einem gespeicherten png_path.

    Erwartung
    app.py mountet /files auf OUTPUT_ROOT.
    png_path ist in ratings meistens ein absoluter Pfad.

    Strategie
    - wenn png_path relativ zu OUTPUT_ROOT ist, nutze den relativen Pfad
    - sonst fallback: ersetze Backslashes, gib /files/<path> zurueck
    """
    p_raw = str(png_path or "").strip()
    if not p_raw:
        return ""

    if p_raw.startswith("/files/"):
        return p_raw

    root_s = str(OUTPUT_ROOT).replace("/", "\\").rstrip("\\")
    p_s = p_raw.replace("/", "\\")

    # Windows case-insensitive prefix
    if p_s.lower().startswith((root_s + "\\").lower()):
        rel = p_s[len(root_s) + 1 :]
        rel = rel.replace("\\", "/")
        return f"/files/{rel}"

    # Vielleicht ist es schon relativ
    rel2 = p_s.replace("\\", "/")
    if rel2.startswith("./"):
        rel2 = rel2[2:]
    return f"/files/{rel2}"
