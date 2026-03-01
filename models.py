# models.py
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class RatedItem:
    png_path: Path
    json_path: Path
    subdir: str
    model_branch: str
    checkpoint: str
    combo_key: str
    meta: Dict[str, Any]
    rated: int = 0
    rating: Optional[int] = None
    deleted: int = 0
    steps: Optional[int] = None
    cfg: Optional[float] = None
    sampler: Optional[str] = None
    scheduler: Optional[str] = None
    denoise: Optional[float] = None
    loras_json: str = "[]"
    pos_prompt: str = ""
    neg_prompt: str = ""