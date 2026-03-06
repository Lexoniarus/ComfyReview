from __future__ import annotations

from typing import Any, Dict, List, Tuple


def norm_token_keep_case(t: str) -> str:
    s = str(t or "").strip()
    return " ".join(s.split())


def split_tokens_csv_keep_case(s: str) -> List[str]:
    toks: List[str] = []
    for raw in (s or "").split(","):
        t = norm_token_keep_case(raw)
        if t:
            toks.append(t)
    return toks


def dedup_keep_order(xs: List[str]) -> List[str]:
    return list(dict.fromkeys(xs))


def combo_item_tokens(item: Dict[str, Any]) -> Tuple[List[str], List[str]]:
    """Return (pos_tokens, neg_tokens) for a playground item."""

    pos = split_tokens_csv_keep_case(str(item.get("pos") or ""))
    neg = split_tokens_csv_keep_case(str(item.get("neg") or ""))
    return pos, neg
