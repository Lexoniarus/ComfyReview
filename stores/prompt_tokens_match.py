# prompt_tokens_match.py
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from config import MIN_RUNS, POOL_LIMIT


def _split_tokens_csv(text: str) -> List[str]:
    if not text:
        return []
    return [t.strip() for t in str(text).split(",") if t.strip()]


def _detect_ratings_table(con: sqlite3.Connection) -> Tuple[bool, List[str]]:
    row = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='ratings' LIMIT 1"
    ).fetchone()
    if not row:
        return False, []
    cols = [r[1] for r in con.execute("PRAGMA table_info(ratings)").fetchall()]
    return True, cols


def _rating_summary_for_json(
    con: sqlite3.Connection,
    *,
    json_path: str,
    model_branch: str = "",
) -> Tuple[Optional[float], int, Optional[str]]:
    """
    Liefert (avg_rating, runs, png_path) fuer ein json_path.
    avg_rating und runs kommen aus ratings.sqlite3 (nicht prompt_tokens).
    png_path ist fuer Preview (letzter nicht-geloeschter Eintrag).
    """
    ok, cols = _detect_ratings_table(con)
    if not ok:
        return None, 0, None

    has_deleted = "deleted" in cols
    has_rating = "rating" in cols
    has_png = "png_path" in cols
    has_run = "run" in cols
    has_model = "model_branch" in cols

    # Latest-state guard (vNext): if the newest row for this json_path is deleted=1,
    # the image must be treated as deleted even if older rating rows exist.
    if has_deleted:
        where_latest = "WHERE json_path = ?"
        args_latest: List[Any] = [json_path]
        if model_branch and has_model:
            where_latest += " AND model_branch = ?"
            args_latest.append(model_branch)

        row_latest = con.execute(
            f"SELECT COALESCE(deleted,0) AS deleted FROM ratings {where_latest} ORDER BY id DESC LIMIT 1",
            args_latest,
        ).fetchone()

        if row_latest and int(row_latest["deleted"] or 0) == 1:
            return None, 0, None

    if not has_rating:
        return None, 0, None

    where = "WHERE json_path = ?"
    args: List[Any] = [json_path]

    if has_deleted:
        where += " AND deleted = 0"

    if model_branch and has_model:
        where += " AND model_branch = ?"
        args.append(model_branch)

    row = con.execute(
        f"""
        SELECT
          AVG(CASE WHEN rating IS NOT NULL THEN rating END) AS avg_rating,
          SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) AS runs
        FROM ratings
        {where}
        """,
        args,
    ).fetchone()

    avg_rating = None
    runs = 0
    if row:
        if row["avg_rating"] is not None:
            try:
                avg_rating = float(row["avg_rating"])
            except Exception:
                avg_rating = None
        try:
            runs = int(row["runs"] or 0)
        except Exception:
            runs = 0

    png_path = None
    if has_png:
        order = "ORDER BY run DESC" if has_run else "ORDER BY rowid DESC"
        row2 = con.execute(
            f"""
            SELECT png_path
            FROM ratings
            {where}
              AND png_path IS NOT NULL
              AND png_path != ''
            {order}
            LIMIT 1
            """,
            args,
        ).fetchone()
        if row2 and row2["png_path"]:
            png_path = str(row2["png_path"])

    return avg_rating, runs, png_path

def _rating_avg_and_runs_for_json(
    ratings_db_path: Path,
    json_path: str,
    model_branch: str = "",
) -> Tuple[Optional[float], int, Optional[str]]:
    """
    Backward compatible wrapper.

    fetch_best_match_preview ruft aktuell _rating_avg_and_runs_for_json auf,
    aber die Datei implementiert _rating_summary_for_json (mit Connection).

    Diese Funktion glueht die beiden zusammen, ohne bestehende Logik zu aendern.
    """
    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        return _rating_summary_for_json(con, json_path=json_path, model_branch=model_branch)
    finally:
        con.close()

def _normalize_best_match_args(
    *,
    tokens: List[str],
    scope: str,
    min_hits: int,
    model_branch: str,
    candidate_limit: int,
    min_runs: int,
) -> Tuple[List[str], str, int, str, int, int]:
    """Normalize and validate inputs for best match preview."""
    toks = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    scope_n = str(scope or "pos").strip()
    if scope_n not in {"pos", "neg"}:
        scope_n = "pos"

    mh = int(min_hits or 1)
    if mh < 1:
        mh = 1

    cl = int(candidate_limit or int(POOL_LIMIT))
    if cl < 1:
        cl = int(POOL_LIMIT)
    if cl > int(POOL_LIMIT):
        cl = int(POOL_LIMIT)

    mr = int(min_runs or int(MIN_RUNS))
    if mr < int(MIN_RUNS):
        mr = int(MIN_RUNS)

    return toks, scope_n, mh, str(model_branch or ""), cl, mr


def _query_token_hit_candidates(
    con: sqlite3.Connection,
    *,
    toks: List[str],
    scope: str,
    min_hits: int,
    model_branch: str,
    candidate_limit: int,
) -> List[sqlite3.Row]:
    """Return candidate json_paths with token hit counts."""
    if not toks:
        return []

    qmarks = ",".join(["?"] * len(toks))
    sql = f"""
        SELECT json_path, COUNT(DISTINCT token) AS hits
        FROM tokens
        WHERE deleted = 0
          AND scope = ?
          AND token IN ({qmarks})
          AND json_path IS NOT NULL
          AND json_path != ''
    """
    args: List[Any] = [scope] + toks

    if model_branch:
        sql += " AND model_branch = ?"
        args.append(model_branch)

    sql += """
        GROUP BY json_path
        HAVING hits >= ?
        ORDER BY hits DESC
        LIMIT ?
    """
    args.extend([min_hits, candidate_limit])
    return con.execute(sql, args).fetchall()


def _safe_float(v: Any, *, default: float = float("-inf")) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def _pick_best_candidate(
    ratings_con: sqlite3.Connection,
    *,
    rows: List[sqlite3.Row],
    model_branch: str,
    min_runs: int,
) -> Optional[Dict[str, Any]]:
    """Rank candidates by hits DESC, avg_rating DESC, runs DESC."""
    best: Optional[Dict[str, Any]] = None

    for r in rows:
        json_path = str(r["json_path"])
        hits = int(r["hits"] or 0)

        avg_rating, runs, png_path = _rating_summary_for_json(
            ratings_con,
            json_path=json_path,
            model_branch=model_branch,
        )

        runs_n = int(runs or 0)
        if min_runs and runs_n < int(min_runs):
            continue

        if png_path:
            try:
                if not Path(str(png_path)).exists():
                    continue
            except Exception:
                continue

        candidate = {
            "json_path": json_path,
            "png_path": png_path or "",
            "hits": int(hits),
            "avg_rating": avg_rating,
            "runs": int(runs_n),
        }

        if best is None:
            best = candidate
            continue

        b_hits = int(best.get("hits") or 0)
        b_avg = best.get("avg_rating")
        b_runs = int(best.get("runs") or 0)

        c_hits = int(candidate.get("hits") or 0)
        c_avg = candidate.get("avg_rating")
        c_runs = int(candidate.get("runs") or 0)

        if c_hits > b_hits:
            best = candidate
            continue

        if c_hits == b_hits:
            if _safe_float(c_avg) > _safe_float(b_avg):
                best = candidate
                continue
            if _safe_float(c_avg) == _safe_float(b_avg) and c_runs > b_runs:
                best = candidate
                continue

    return best


def fetch_best_match_preview(
    prompt_tokens_db_path: Path,
    ratings_db_path: Path,
    *,
    tokens: List[str],
    scope: str = "pos",
    min_hits: int = 1,
    model_branch: str = "",
    candidate_limit: int = POOL_LIMIT,
    min_runs: int = MIN_RUNS,
) -> Optional[Dict[str, Any]]:
    """
    Best Picture Matching nach deiner Hub Logik:

    Kandidaten
    - prompt_tokens.sqlite3: json_path Kandidaten via Token Overlap (hits)
    - ratings.sqlite3: latest-state guard fuer deleted (siehe _rating_summary_for_json)
    - min_runs Gate

    Ranking
    - hits DESC
    - avg_rating DESC
    - runs DESC

    Rueckgabe
    - dict mit json_path, png_path, hits, avg_rating, runs
    """
    toks, scope_n, mh, mb, cl, mr = _normalize_best_match_args(
        tokens=tokens,
        scope=scope,
        min_hits=min_hits,
        model_branch=model_branch,
        candidate_limit=candidate_limit,
        min_runs=min_runs,
    )
    if not toks:
        return None

    con = sqlite3.connect(prompt_tokens_db_path)
    con.row_factory = sqlite3.Row
    ratings_con = sqlite3.connect(ratings_db_path)
    ratings_con.row_factory = sqlite3.Row
    try:
        rows = _query_token_hit_candidates(
            con,
            toks=toks,
            scope=scope_n,
            min_hits=mh,
            model_branch=mb,
            candidate_limit=cl,
        )
        if not rows:
            return None
        return _pick_best_candidate(
            ratings_con,
            rows=rows,
            model_branch=mb,
            min_runs=mr,
        )
    finally:
        try:
            con.close()
        except Exception:
            pass
        try:
            ratings_con.close()
        except Exception:
            pass
