from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from stores.prompt_ratings_store import fetch_prompt_rating_map

from .token_utils import dedup_keep_order


def score_token_block(*, prompt_ratings_db_path: Path, scope: str, tokens: List[str], model_branch: str = "") -> Dict[str, Any]:
    """Score a token block using prompt_ratings.sqlite3.

    Returns
    avg weighted by runs
    runs total token runs
    total_tokens
    rated_tokens
    coverage
    """

    toks = dedup_keep_order([str(t).strip() for t in (tokens or []) if str(t).strip()])
    total = int(len(toks))
    if total <= 0:
        return {"avg": None, "runs": 0, "total_tokens": 0, "rated_tokens": 0, "coverage": 0.0}

    m = fetch_prompt_rating_map(
        prompt_ratings_db_path,
        scope=str(scope or "pos"),
        model_branch=str(model_branch or ""),
        tokens=toks,
    )

    rated = 0
    num = 0.0
    den = 0
    for t in toks:
        d = m.get(t)
        if not d:
            continue
        a = d.get("avg_rating")
        r = int(d.get("runs") or 0)
        if a is None or r <= 0:
            continue
        rated += 1
        num += float(a) * float(r)
        den += int(r)

    avg = (num / float(den)) if den > 0 else None
    cov = (float(rated) / float(total)) if total > 0 else 0.0
    return {
        "avg": avg,
        "runs": int(den),
        "total_tokens": int(total),
        "rated_tokens": int(rated),
        "coverage": float(cov),
    }


def score_combo_tokens(
    *,
    prompt_ratings_db_path: Path,
    model_branch: str,
    pos_tokens: List[str],
    neg_tokens: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Score a combo using token ratings from prompt_ratings.sqlite3."""

    pos = score_token_block(
        prompt_ratings_db_path=prompt_ratings_db_path,
        scope="pos",
        tokens=list(pos_tokens or []),
        model_branch=str(model_branch or ""),
    )
    neg = score_token_block(
        prompt_ratings_db_path=prompt_ratings_db_path,
        scope="neg",
        tokens=list(neg_tokens or []),
        model_branch=str(model_branch or ""),
    )

    return {
        "pos_avg": pos.get("avg"),
        "pos_runs": int(pos.get("runs") or 0),
        "pos_coverage": float(pos.get("coverage") or 0.0),
        "neg_avg": neg.get("avg"),
        "neg_runs": int(neg.get("runs") or 0),
        "neg_coverage": float(neg.get("coverage") or 0.0),
    }
