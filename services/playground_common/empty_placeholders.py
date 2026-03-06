from __future__ import annotations

from typing import Any, Dict, List


def norm_name(value: str) -> str:
    """Normalize a name/key for comparisons (case-insensitive, whitespace-stable)."""
    return " ".join(str(value or "").strip().lower().replace("_", " ").split())


def is_empty_placeholder_value(value: str) -> bool:
    """Return True for explicit empty placeholders.

    Generator rule:
    - Items named exactly 'Empty' (case-insensitive) must never be picked randomly.

    Notes:
    - We intentionally do NOT treat 'Empty Scene' as a placeholder.
    - Manual picks are allowed elsewhere (filtering happens only for random pools).
    """
    n = norm_name(value)
    return n in {"empty", "none", "null"}


def is_empty_item(item: Dict[str, Any]) -> bool:
    name = str(item.get("name") or "")
    key = str(item.get("key") or "")
    return is_empty_placeholder_value(name) or is_empty_placeholder_value(key)


def filter_random_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter out empty placeholders from a random candidate list."""
    return [x for x in (items or []) if not is_empty_item(x)]
