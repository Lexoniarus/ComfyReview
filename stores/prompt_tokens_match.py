# prompt_tokens_match.py
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


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


def fetch_best_match_preview(
    prompt_tokens_db_path: Path,
    ratings_db_path: Path,
    *,
    tokens: List[str],
    scope: str = "pos",
    min_hits: int = 1,
    model_branch: str = "",
    candidate_limit: int = 50,
) -> Optional[Dict[str, Any]]:
    """
    GLOBAL (A) IDF Matching:
    - Matching basiert auf Token overlap in prompt_tokens.sqlite3.
    - Statt nur hits zu zaehlen, berechnen wir einen gewichteten score:
        score = sum(log(total_docs / df(token))) ueber die gematchten tokens.
      Dadurch verlieren generische tokens (masterpiece, best quality, solo, ...) an Gewicht,
      und seltene identity tokens gewinnen Gewicht.
    - Finales Ranking:
        score DESC, avg_rating DESC, runs DESC, hits DESC

    Kompatibel zur bestehenden Signatur inklusive model_branch, damit Router nicht bricht.
    model_branch filtert Kandidaten optional in Schritt 1 und 2, IDF bleibt global.
    """
    toks = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    if not toks:
        return None

    scope = str(scope or "pos").strip()
    if scope not in {"pos", "neg"}:
        scope = "pos"

    min_hits = int(min_hits or 1)
    if min_hits < 1:
        min_hits = 1

    candidate_limit = int(candidate_limit or 50)
    if candidate_limit < 1:
        candidate_limit = 50

    con = sqlite3.connect(prompt_tokens_db_path)
    con.row_factory = sqlite3.Row

    qmarks = ",".join(["?"] * len(toks))

    # total_docs global (A): ohne model_branch filter
    total_row = con.execute(
        """
        SELECT COUNT(DISTINCT json_path) AS n
        FROM tokens
        WHERE deleted = 0 AND scope = ?
        """,
        (scope,),
    ).fetchone()

    total_docs = int(total_row["n"] or 0) if total_row else 0
    if total_docs <= 0:
        con.close()
        return None

    # df pro token global (A): ohne model_branch filter
    df_rows = con.execute(
        f"""
        SELECT token, COUNT(DISTINCT json_path) AS df
        FROM tokens
        WHERE deleted = 0
          AND scope = ?
          AND token IN ({qmarks})
        GROUP BY token
        """,
        [scope] + toks,
    ).fetchall()

    df_map: Dict[str, int] = {str(r["token"]): int(r["df"] or 0) for r in df_rows}

    idf: Dict[str, float] = {}
    for t in toks:
        d = int(df_map.get(t, 0) or 0)
        if d < 1:
            d = 1
        idf[t] = math.log(float(total_docs) / float(d))

    # --------------------------------------
    # 1) Kandidaten: hits aus prompt_tokens
    # --------------------------------------
    sql = f"""
        SELECT
          json_path,
          model_branch,
          COUNT(*) AS hits
        FROM tokens
        WHERE deleted = 0
          AND scope = ?
          AND token IN ({qmarks})
    """
    args: List[Any] = [scope] + toks

    if model_branch:
        sql += " AND model_branch = ?"
        args.append(model_branch)

    sql += """
        GROUP BY json_path, model_branch
        HAVING hits >= ?
        ORDER BY hits DESC
        LIMIT ?
    """
    args.append(min_hits)
    args.append(candidate_limit)

    rows = con.execute(sql, args).fetchall()
    if not rows:
        con.close()
        return None

    candidates: List[Dict[str, Any]] = []
    json_paths: List[str] = []
    for r in rows:
        jp = str(r["json_path"])
        json_paths.append(jp)
        candidates.append(
            {
                "json_path": jp,
                "model_branch": str(r["model_branch"] or ""),
                "hits": int(r["hits"] or 0),
            }
        )

    # --------------------------------------
    # 1b) fuer diese Kandidaten: distinct tokens holen, um score zu bauen
    # --------------------------------------
    in_json = ",".join(["?"] * len(json_paths))
    pair_rows = con.execute(
        f"""
        SELECT json_path, token
        FROM tokens
        WHERE deleted = 0
          AND scope = ?
          AND token IN ({qmarks})
          AND json_path IN ({in_json})
        GROUP BY json_path, token
        """,
        [scope] + toks + json_paths,
    ).fetchall()
    con.close()

    tok_by_json: Dict[str, List[str]] = {}
    for pr in pair_rows:
        jp = str(pr["json_path"])
        tk = str(pr["token"])
        tok_by_json.setdefault(jp, []).append(tk)

    for c in candidates:
        tlist = tok_by_json.get(c["json_path"], [])
        score = 0.0
        for tk in tlist:
            score += float(idf.get(tk, 0.0))
        c["score"] = float(score)

    # --------------------------------------
    # 2) Ranking via ratings.sqlite3 Durchschnitt
    # --------------------------------------
    con2 = sqlite3.connect(ratings_db_path)
    con2.row_factory = sqlite3.Row

    def _safe_avg(x: Optional[float]) -> float:
        return float(x) if x is not None else -1.0

    best: Optional[Dict[str, Any]] = None
    for c in candidates:
        avg_rating, runs, png_path = _rating_summary_for_json(
            con2,
            json_path=c["json_path"],
            model_branch=(model_branch or c["model_branch"] or ""),
        )

        cand = {
            "json_path": c["json_path"],
            "model_branch": (model_branch or c["model_branch"] or ""),
            "hits": int(c["hits"]),
            "score": float(c.get("score") or 0.0),
            "avg_rating": avg_rating,
            "runs": int(runs),
            "png_path": png_path,
        }

        if best is None:
            best = cand
            continue

        # Sort: score DESC, avg_rating DESC, runs DESC, hits DESC
        if cand["score"] > best["score"]:
            best = cand
        elif cand["score"] == best["score"]:
            if _safe_avg(cand["avg_rating"]) > _safe_avg(best["avg_rating"]):
                best = cand
            elif _safe_avg(cand["avg_rating"]) == _safe_avg(best["avg_rating"]):
                if cand["runs"] > best["runs"]:
                    best = cand
                elif cand["runs"] == best["runs"]:
                    if cand["hits"] > best["hits"]:
                        best = cand

    con2.close()
    return best