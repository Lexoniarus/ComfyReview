from __future__ import annotations

import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List


def _lb05_from_ratings(ratings: List[float]) -> Dict[str, float]:
    n = len(ratings)
    if n == 0:
        return {"n": 0, "mean": 0.0, "lb05": 0.0}

    mean = sum(ratings) / n
    if n == 1:
        return {"n": 1, "mean": float(mean), "lb05": float(mean)}

    var = sum((x - mean) ** 2 for x in ratings) / (n - 1)
    sd = math.sqrt(var)
    se = sd / math.sqrt(n)

    lb05 = mean - 1.645 * se
    return {"n": int(n), "mean": float(mean), "lb05": float(lb05)}


def fetch_token_stats_for_tokens(
    prompt_db_path: Path,
    *,
    tokens: List[str],
    scope: str,
    model_branch: str = "",
) -> Dict[str, Dict[str, Any]]:
    tokens = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    if not tokens:
        return {}

    scope = str(scope or "").strip()
    if scope not in {"pos", "neg"}:
        scope = "pos"

    con = sqlite3.connect(prompt_db_path)
    con.row_factory = sqlite3.Row

    qmarks = ",".join(["?"] * len(tokens))

    sql = f"""
        SELECT token, rating
        FROM tokens
        WHERE deleted = 0
          AND rating IS NOT NULL
          AND scope = ?
          AND token IN ({qmarks})
    """
    args: List[Any] = [scope] + tokens

    if model_branch:
        sql += " AND model_branch = ?"
        args.append(model_branch)

    rows = con.execute(sql, args).fetchall()
    con.close()

    bucket: Dict[str, List[float]] = {}
    for r in rows:
        t = str(r["token"])
        try:
            val = float(r["rating"])
        except Exception:
            continue
        bucket.setdefault(t, []).append(val)

    out: Dict[str, Dict[str, Any]] = {}
    for t in tokens:
        stats = _lb05_from_ratings(bucket.get(t, []))
        out[t] = {
            "n": int(stats["n"]),
            "mean": float(stats["mean"]),
            "lb05": float(stats["lb05"]),
        }

    return out
