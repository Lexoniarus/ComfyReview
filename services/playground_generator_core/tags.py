from __future__ import annotations

from services.playground_rules import get_effective_tags

from .types import ItemDict, TagSet


def effective_tags(item: ItemDict) -> TagSet:
    """Return effective tags for an item dict.

    The playground rules engine now exposes ``get_effective_tags`` as a
    keyword-only function, so this adapter normalizes the DB item dict into the
    expected argument shape.
    """
    item = dict(item or {})
    return set(
        get_effective_tags(
            kind=str(item.get("kind") or ""),
            key=str(item.get("key") or ""),
            name=str(item.get("name") or ""),
            tags=str(item.get("tags") or ""),
            pos=str(item.get("pos") or ""),
            neg=str(item.get("neg") or ""),
            notes=str(item.get("notes") or ""),
        )
    )
