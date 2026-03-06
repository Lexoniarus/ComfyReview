from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from services.playground_rules_engine.rules import EXCLUDES


def build_exclude_index(excludes: Sequence[Tuple[str, str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Baut ein Lookup:
    tag -> Liste von (other_tag, grund)
    Symmetrisch.
    """
    idx: Dict[str, List[Tuple[str, str]]] = {}
    for a, b, reason in excludes:
        idx.setdefault(a, []).append((b, reason))
        idx.setdefault(b, []).append((a, reason))
    return idx


EXCLUDE_INDEX: Dict[str, List[Tuple[str, str]]] = build_exclude_index(EXCLUDES)
