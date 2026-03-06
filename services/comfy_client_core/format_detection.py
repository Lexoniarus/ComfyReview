from __future__ import annotations

from typing import Any, Dict, Iterator, Tuple


def is_api_prompt_format(wf: Any) -> bool:
    """Detect ComfyUI API prompt dict format.

    Heuristik muss kompatibel bleiben:
    - dict
    - keine top-level keys nodes/links
    - values sind node dicts mit class_type + inputs
    """

    if not isinstance(wf, dict) or not wf:
        return False
    if "nodes" in wf or "links" in wf:
        return False

    hits = 0
    for v in wf.values():
        if not isinstance(v, dict):
            continue
        if "class_type" in v and isinstance(v.get("inputs"), dict):
            hits += 1
            if hits >= 2:
                return True
    return hits >= 1


def iter_nodes(wf: Dict[str, Any]) -> Iterator[Tuple[str, Dict[str, Any]]]:
    for node_id, node in wf.items():
        if isinstance(node, dict):
            yield node_id, node
