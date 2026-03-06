from __future__ import annotations

import random
from typing import Any, Dict, Optional, Set, Tuple

from config import PLAYGROUND_RULES_ENABLED
from services.playground_common.empty_placeholders import filter_random_items
from services.playground_rules import filter_candidates

from stores.playground_store import get_item_by_id, get_items_by_kind

from .tags import effective_tags
from .types import ItemDict


def pick_slot(
    *,
    db_path,
    rng: random.Random,
    kind: str,
    manual_id: Optional[int],
    active_tags: Set[str],
) -> Tuple[Optional[ItemDict], Dict[str, Any]]:
    """Pick a single slot item.

    Manual picks:
      - load the exact item by id
      - do NOT pre-filter by gates/excludes (UI should see violations)

    Random picks:
      - load all candidates for the kind
      - remove placeholder items from the random roster (Empty/empty)
      - apply rules layer filter_candidates (gates + excludes)
      - choose uniformly random from allowed
    """
    slot_debug: Dict[str, Any] = {
        "kind": kind,
        "manual": bool(manual_id),
        "manual_id": int(manual_id) if manual_id else None,
        "candidates_total": 0,
        "candidates_allowed": 0,
        "chosen_id": None,
        "chosen_name": None,
        "filtered_reasons_sample": [],
    }

    if manual_id:
        item = get_item_by_id(db_path, int(manual_id))
        if not item:
            raise ValueError(f"manual pick nicht gefunden: kind={kind} id={manual_id}")

        if str(item.get("kind", "")) != kind:
            raise ValueError(
                f"manual pick kind mismatch: slot={kind} item.kind={item.get('kind')} id={manual_id}"
            )

        slot_debug["chosen_id"] = int(item.get("id"))
        slot_debug["chosen_name"] = str(item.get("name", "") or "")
        return item, slot_debug

    candidates = get_items_by_kind(db_path, kind)
    candidates = filter_random_items(list(candidates))
    slot_debug["candidates_total"] = len(candidates)

    if PLAYGROUND_RULES_ENABLED:
        allowed, reasons = filter_candidates(
            kind=kind,
            candidates=candidates,
            get_tags=lambda it: effective_tags(it),
            active_tags=active_tags,
        )
    else:
        allowed = list(candidates)
        reasons = []

    slot_debug["candidates_allowed"] = len(allowed)

    if reasons:
        slot_debug["filtered_reasons_sample"] = [r.__dict__ for r in reasons[:10]]

    if not allowed:
        return None, slot_debug

    chosen = rng.choice(allowed)
    slot_debug["chosen_id"] = int(chosen.get("id"))
    slot_debug["chosen_name"] = str(chosen.get("name", "") or "")

    return chosen, slot_debug
