from __future__ import annotations

from typing import Dict, List

from .types import SelectionDict


def _join_prompt_blocks(blocks: List[str]) -> str:
    """Join prompt blocks into a single string.

    We treat each item.pos / item.neg as a full block and join by comma,
    because tokens are authored that way in the Playground DB.
    """
    cleaned = [str(b).strip() for b in (blocks or []) if str(b).strip()]
    return ", ".join(cleaned)


def build_prompts(selection: SelectionDict) -> Dict[str, str]:
    """Build final positive/negative prompt strings and notes from a selection."""
    order = ["character", "scene", "outfit", "pose", "expression", "lighting", "modifier"]

    pos_blocks: List[str] = []
    neg_blocks: List[str] = []
    notes_blocks: List[str] = []

    for kind in order:
        item = selection.get(kind)
        if not item:
            continue

        pos = str(item.get("pos", "") or "").strip()
        neg = str(item.get("neg", "") or "").strip()
        notes = str(item.get("notes", "") or "").strip()

        if pos:
            pos_blocks.append(pos)
        if neg:
            neg_blocks.append(neg)
        if notes:
            notes_blocks.append(notes)

    return {
        "positive": _join_prompt_blocks(pos_blocks),
        "negative": _join_prompt_blocks(neg_blocks),
        "notes": " | ".join([n for n in notes_blocks if n]),
    }
