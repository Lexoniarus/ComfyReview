from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from stores.playground_store import list_items


def _norm_space(s: str) -> str:
    """Normalize whitespace without touching punctuation."""
    return " ".join(str(s or "").strip().split())


def _safe_len(s: str) -> int:
    return len(str(s or ""))


@dataclass(frozen=True)
class LabelHit:
    kind: str
    name: str
    key: str
    pos: str


class PlaygroundLabelMatcher:
    """Resolve labels from a pos_prompt by substring matching.

    Matching rule (vNext):
    - A playground item matches if its pos block is a substring of pos_prompt.
    - If multiple items match for a kind, the *longest* pos block wins.
    - Modifier can return multiple hits (stacked modifiers).
    """

    def __init__(self, items_by_kind: Dict[str, List[Dict[str, Any]]]):
        self._items_by_kind: Dict[str, List[Dict[str, Any]]] = items_by_kind

        # Precompute normalized pos blocks for faster per-prompt matching.
        norm: Dict[str, List[Tuple[str, Dict[str, Any]]]] = {}
        for kind, items in (items_by_kind or {}).items():
            pairs: List[Tuple[str, Dict[str, Any]]] = []
            for it in items:
                pos = str(it.get("pos") or "").strip()
                if not pos:
                    continue
                pairs.append((_norm_space(pos), it))
            # Longest-first helps early winner selection.
            pairs.sort(key=lambda x: _safe_len(x[0]), reverse=True)
            norm[str(kind)] = pairs

        self._norm_by_kind = norm

    def _best_single(self, kind: str, prompt_norm: str) -> Optional[LabelHit]:
        for pos_norm, it in self._norm_by_kind.get(str(kind), []):
            if pos_norm and pos_norm in prompt_norm:
                return LabelHit(
                    kind=str(kind),
                    name=str(it.get("name") or "").strip(),
                    key=str(it.get("key") or "").strip(),
                    pos=str(it.get("pos") or "").strip(),
                )
        return None

    def _multi(self, kind: str, prompt_norm: str, *, limit: int = 8) -> List[LabelHit]:
        hits: List[LabelHit] = []
        for pos_norm, it in self._norm_by_kind.get(str(kind), []):
            if pos_norm and pos_norm in prompt_norm:
                hits.append(
                    LabelHit(
                        kind=str(kind),
                        name=str(it.get("name") or "").strip(),
                        key=str(it.get("key") or "").strip(),
                        pos=str(it.get("pos") or "").strip(),
                    )
                )
                if len(hits) >= int(limit):
                    break
        return hits

    def resolve(self, pos_prompt: str, *, include_lighting: bool = True) -> Dict[str, Any]:
        """Resolve labels for a positive prompt.

        Returns keys
        - scene_name, outfit_name, pose_name, expression_name
        - modifiers (list[str])
        - light_name (optional)
        """
        prompt_norm = _norm_space(pos_prompt)

        scene = self._best_single("scene", prompt_norm)
        outfit = self._best_single("outfit", prompt_norm)
        pose = self._best_single("pose", prompt_norm)
        expr = self._best_single("expression", prompt_norm)
        mods = self._multi("modifier", prompt_norm, limit=12)

        light = None
        if include_lighting:
            light = self._best_single("lighting", prompt_norm)

        return {
            "scene_name": (scene.name if scene else ""),
            "outfit_name": (outfit.name if outfit else ""),
            "pose_name": (pose.name if pose else ""),
            "expression_name": (expr.name if expr else ""),
            "modifiers": [m.name for m in mods if m.name],
            "light_name": (light.name if light else ""),
        }


_CACHE: Dict[str, Any] = {
    "db_path": "",
    "mtime": 0.0,
    "matcher": None,
}


def _db_mtime(db_path: Path) -> float:
    try:
        return float(os.path.getmtime(str(db_path)))
    except Exception:
        return 0.0


def get_playground_label_matcher(db_path: Path) -> PlaygroundLabelMatcher:
    """Return a cached matcher for the current playground DB state."""
    p = Path(db_path)
    mtime = _db_mtime(p)
    if (
        _CACHE.get("matcher") is not None
        and str(_CACHE.get("db_path")) == str(p)
        and float(_CACHE.get("mtime") or 0.0) == float(mtime)
    ):
        return _CACHE["matcher"]

    items_by_kind: Dict[str, List[Dict[str, Any]]] = {}
    for kind in ["scene", "outfit", "pose", "expression", "modifier", "lighting"]:
        try:
            items_by_kind[kind] = list_items(p, kind=kind, limit=5000)
        except Exception:
            items_by_kind[kind] = []

    matcher = PlaygroundLabelMatcher(items_by_kind)
    _CACHE["db_path"] = str(p)
    _CACHE["mtime"] = float(mtime)
    _CACHE["matcher"] = matcher
    return matcher
