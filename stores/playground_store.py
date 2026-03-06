"""Playground DB store (backwards compatible facade).

This module intentionally keeps the original import surface:

    from stores.playground_store import list_items, create_item, ...

Implementation is split into focused modules under stores.playground/.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from .playground.connection import db
from .playground.kinds import ALLOWED_KINDS, validate_kind
from .playground.keys import slugify_key
from .playground.items import (
    list_recent_items,
    list_items,
    get_item,
    get_item_by_id,
    get_items_by_kind,
    get_items_by_ids,
)
from .playground.mutations import create_item, update_item, delete_item
from .playground.token_stats import fetch_token_stats_for_tokens


# Preserve previous internal helper name for compatibility with older call-sites.
# New code should use validate_kind.

def _validate_kind(kind: str) -> str:
    return validate_kind(kind)


__all__ = [
    "ALLOWED_KINDS",
    "db",
    "list_recent_items",
    "list_items",
    "get_item",
    "create_item",
    "update_item",
    "delete_item",
    "fetch_token_stats_for_tokens",
    "get_item_by_id",
    "get_items_by_kind",
    "get_items_by_ids",
    "slugify_key",
]
