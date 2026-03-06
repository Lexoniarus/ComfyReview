"""Backwards compatible scene resolver.

vNext label matching is centralized in `services.playground_label_service`.
Older call sites expect `resolve_scene_name(pos_prompt)`.
"""

from __future__ import annotations

from config import PLAYGROUND_DB_PATH
from services.playground_label_service import get_playground_label_matcher


def resolve_scene_name(pos_prompt: str) -> str:
    matcher = get_playground_label_matcher(PLAYGROUND_DB_PATH)
    out = matcher.resolve(str(pos_prompt or ""), include_lighting=False)
    return str(out.get("scene_name") or "")
