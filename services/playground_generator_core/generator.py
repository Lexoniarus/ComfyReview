from __future__ import annotations

import random
from typing import Any, Dict, Optional, Set

from config import PLAYGROUND_RULES_ENABLED
from services.playground_rules import DEFAULT_MAX_TRIES, explain_violations, validate_selection

from stores.playground_store import get_item_by_id

from .prompt_building import build_prompts
from .slot_picker import pick_slot
from .tags import effective_tags
from .types import SelectionDict


def _load_character_item(db_path, character_id: int) -> Dict[str, Any]:
    item = get_item_by_id(db_path, int(character_id))
    if not item:
        raise ValueError(f"character_id nicht gefunden: {character_id}")
    if str(item.get("kind", "")) != "character":
        raise ValueError(f"character_id ist kein character: id={character_id}")
    return item


def _final_validate(active_tags: Set[str]) -> Dict[str, Any]:
    if not PLAYGROUND_RULES_ENABLED:
        return {"ok": True, "violations": [], "violations_text": ""}

    violations = validate_selection(active_tags)
    if not violations:
        return {"ok": True, "violations": [], "violations_text": ""}

    return {
        "ok": False,
        "violations": [v.__dict__ for v in violations],
        "violations_text": explain_violations(violations),
    }


class PlaygroundGenerator:
    """Generate a valid Playground selection and build prompts.

    This is business logic (not UI).
    DB access is performed through the Playground store functions.
    """

    ORDER = ["character", "scene", "outfit", "pose", "expression", "lighting", "modifier"]

    def __init__(self, db_path):
        self.db_path = db_path

    def generate(
        self,
        *,
        character_id: int,
        manual_picks: Dict[str, Optional[int]],
        include_lighting: bool = True,
        include_modifier: bool = True,
        seed: Optional[int] = None,
        max_tries: int = DEFAULT_MAX_TRIES,
    ) -> Dict[str, Any]:
        rng = random.Random(seed)

        last_debug: Dict[str, Any] = {}

        for attempt in range(int(max_tries)):
            debug: Dict[str, Any] = {
                "attempt": attempt + 1,
                "max_tries": int(max_tries),
                "seed": seed,
                "rules_enabled": bool(PLAYGROUND_RULES_ENABLED),
                "reject_reason": "",
                "slot_debug": {},
                "violations_text": "",
            }

            selection: SelectionDict = {}
            char_item = _load_character_item(self.db_path, int(character_id))
            selection["character"] = char_item
            active_tags: Set[str] = set(effective_tags(char_item))

            # Slots 2..n
            for kind in self.ORDER[1:]:
                if kind == "lighting" and not include_lighting:
                    continue
                if kind == "modifier" and not include_modifier:
                    continue

                item, slot_info = pick_slot(
                    db_path=self.db_path,
                    rng=rng,
                    kind=kind,
                    manual_id=manual_picks.get(kind),
                    active_tags=active_tags,
                )

                debug["slot_debug"][kind] = slot_info

                if item is None:
                    debug["reject_reason"] = f"no_candidates_for_{kind}"
                    break

                selection[kind] = item
                active_tags |= effective_tags(item)

            if debug["reject_reason"]:
                last_debug = debug
                continue

            vres = _final_validate(active_tags)
            if not vres["ok"]:
                debug["reject_reason"] = "final_validation_failed"
                debug["violations"] = vres["violations"]
                debug["violations_text"] = vres["violations_text"]
                debug["active_tags"] = sorted(active_tags)
                last_debug = debug
                continue

            out = build_prompts(selection)
            debug["active_tags"] = sorted(active_tags)

            return {
                "selection": selection,
                "active_tags": sorted(active_tags),
                "positive": out["positive"],
                "negative": out["negative"],
                "notes": out["notes"],
                "debug": debug,
            }

        raise RuntimeError(
            "Keine gültige Kombination nach max_tries Versuchen gefunden. "
            f"Letzter Debug Stand: {last_debug}"
        )
