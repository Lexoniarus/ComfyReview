from __future__ import annotations

from typing import Set


ALLOWED_KINDS: Set[str] = {
    "character",
    "scene",
    "outfit",
    "modifier",
    "pose",
    "expression",
    "lighting",
}


def validate_kind(kind: str) -> str:
    """Validate kind against the supported playground kinds."""
    k = str(kind or "").strip().lower()
    if k not in ALLOWED_KINDS:
        raise ValueError(f"ungueltiger kind: {k}")
    return k
