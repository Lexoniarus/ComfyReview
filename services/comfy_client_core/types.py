from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class ComfyResponse:
    ok: bool
    status_code: int
    response_json: Dict[str, Any]
    error: str = ""
