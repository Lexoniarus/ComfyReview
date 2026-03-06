from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from stores.prompt_ratings_store import (
    init_prompt_ratings_db,
    clear_prompt_ratings,
    upsert_prompt_rating,
    upsert_prompt_ratings_bulk,
)


def rebuild_prompt_ratings(
    *,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
) -> Dict[str, Any]:
    """Rebuild prompt_ratings.sqlite3.

    Quelle
      prompt_tokens.sqlite3, Tabelle tokens
      (json_path, run, model_branch, scope, token, rating, deleted)

    Ziel
      Distinct Prompt Token Bewertung.
      Key: (scope, token, model_branch)

    Regeln
      Datenpunkt ist: rating IS NOT NULL oder deleted=1
      deleted wird nicht gefiltert und zaehlt negativ als rating 0

    Hinweis
      Neben den model_branch spezifischen Rows wird zusaetzlich eine Aggregation
      ueber ALLE model_branches geschrieben mit model_branch = ''.
      Das ist der Default, wenn UI keinen model_branch filtert.
    """
    init_prompt_ratings_db(prompt_ratings_db_path)
    clear_prompt_ratings(prompt_ratings_db_path)

    con = sqlite3.connect(prompt_tokens_db_path)
    con.row_factory = sqlite3.Row
    try:
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        written = 0

        # 1) model_branch spezifisch
        rows = con.execute(
            """
            SELECT
                scope,
                token,
                model_branch,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS avg_rating,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS mean_score,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) - 1.645 * (
                    CASE WHEN SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) > 1 THEN
                      sqrt(
                        AVG((CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * (CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END))
                        - AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END)
                      )
                    ELSE 0 END
                 ) / sqrt(SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END)) AS lb05,
                SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) AS runs
            FROM tokens
            GROUP BY scope, token, model_branch
            """
        ).fetchall()

        for r in rows:
            upsert_prompt_rating(
                prompt_ratings_db_path,
                {
                    "scope": str(r["scope"] or "pos"),
                    "token": str(r["token"] or ""),
                    "model_branch": str(r["model_branch"] or ""),
                    "avg_rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
                    "mean_score": float(r["mean_score"]) if r["mean_score"] is not None else None,
                    "lb05": float(r["lb05"]) if r["lb05"] is not None else None,
                    "runs": int(r["runs"] or 0),
                    "last_updated": now,
                },
            )
            written += 1

        # 2) Aggregation ueber alle Modelle (model_branch = '')
        rows_all = con.execute(
            """
            SELECT
                scope,
                token,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS avg_rating,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS mean_score,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) - 1.645 * (
                    CASE WHEN SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) > 1 THEN
                      sqrt(
                        AVG((CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * (CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END))
                        - AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END)
                      )
                    ELSE 0 END
                 ) / sqrt(SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END)) AS lb05,
                SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) AS runs
            FROM tokens
            GROUP BY scope, token
            """
        ).fetchall()

        for r in rows_all:
            upsert_prompt_rating(
                prompt_ratings_db_path,
                {
                    "scope": str(r["scope"] or "pos"),
                    "token": str(r["token"] or ""),
                    "model_branch": "",
                    "avg_rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
                    "mean_score": float(r["mean_score"]) if r["mean_score"] is not None else None,
                    "lb05": float(r["lb05"]) if r["lb05"] is not None else None,
                    "runs": int(r["runs"] or 0),
                    "last_updated": now,
                },
            )
            written += 1

        return {"written": int(written)}
    finally:
        con.close()

def update_prompt_ratings_for_runs(
    *,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    runs: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Incrementally update prompt_ratings for affected tokens.

    runs
      Liste von dicts mit keys json_path, run, model_branch.

    Semantik
      deleted wird nicht gefiltert und zaehlt negativ als rating 0.
      Datenpunkt ist rating IS NOT NULL oder deleted=1.
    """
    init_prompt_ratings_db(prompt_ratings_db_path)

    def _chunk_list(xs: List[str], n: int = 400) -> List[List[str]]:
        return [xs[i : i + n] for i in range(0, len(xs), n)]

    def _collect_touched_tokens() -> tuple[Dict[str, Dict[str, set]], Dict[str, set]]:
        """Return tokens touched by the provided (json_path, run) list.

        Output
          touched_by_branch[model_branch][scope] -> set(token)
          touched_global[scope] -> set(token)
        """
        touched_by_branch: Dict[str, Dict[str, set]] = {}
        touched_global: Dict[str, set] = {"pos": set(), "neg": set()}

        con = sqlite3.connect(prompt_tokens_db_path)
        con.row_factory = sqlite3.Row
        try:
            for r in runs or []:
                jp = str(r.get("json_path") or "").strip()
                rn = int(r.get("run") or 0)
                mb = str(r.get("model_branch") or "").strip()
                if not jp or rn <= 0:
                    continue

                rows = con.execute(
                    "SELECT scope, token FROM tokens WHERE json_path=? AND run=?",
                    (jp, rn),
                ).fetchall()

                if mb not in touched_by_branch:
                    touched_by_branch[mb] = {"pos": set(), "neg": set()}

                for row in rows:
                    scope = str(row["scope"] or "pos").strip()
                    if scope not in {"pos", "neg"}:
                        continue
                    tok = str(row["token"] or "").strip()
                    if not tok:
                        continue
                    touched_by_branch[mb][scope].add(tok)
                    touched_global[scope].add(tok)

            return touched_by_branch, touched_global
        finally:
            con.close()

    def _fetch_stats_rows(
        con: sqlite3.Connection,
        *,
        scope: str,
        tokens: List[str],
        model_branch: Optional[str],
    ) -> list[sqlite3.Row]:
        if not tokens:
            return []

        qmarks = ",".join(["?"] * len(tokens))
        sql = f"""
            SELECT
                token,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS avg_rating,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) AS mean_score,
                AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) - 1.645 * (
                    CASE WHEN SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) > 1 THEN
                      sqrt(
                        AVG((CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * (CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END))
                        - AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END)
                      )
                    ELSE 0 END
                 ) / sqrt(SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END)) AS lb05,
                SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) AS runs
            FROM tokens
            WHERE scope = ?
              AND token IN ({qmarks})
        """
        args: List[Any] = [scope] + list(tokens)

        if model_branch is not None:
            sql += " AND model_branch = ?"
            args.append(str(model_branch))

        sql += " GROUP BY token"
        return con.execute(sql, args).fetchall()

    touched_by_branch, touched_global = _collect_touched_tokens()

    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    written = 0

    con_stats = sqlite3.connect(prompt_tokens_db_path)
    con_stats.row_factory = sqlite3.Row
    try:
        # 1) model_branch spezifisch
        for mb, scopes in (touched_by_branch or {}).items():
            for scope in ("pos", "neg"):
                toks = sorted(list(scopes.get(scope) or []))
                for chunk in _chunk_list(toks):
                    rows = _fetch_stats_rows(
                        con_stats,
                        scope=scope,
                        tokens=chunk,
                        model_branch=str(mb or ""),
                    )
                    payload: List[Dict[str, Any]] = []
                    for row in rows:
                        payload.append(
                            {
                                "scope": scope,
                                "token": str(row["token"] or ""),
                                "model_branch": str(mb or ""),
                                "avg_rating": float(row["avg_rating"])
                                if row["avg_rating"] is not None
                                else None,
                                "mean_score": float(row["mean_score"])
                                if row["mean_score"] is not None
                                else None,
                                "lb05": float(row["lb05"]) if row["lb05"] is not None else None,
                                "runs": int(row["runs"] or 0),
                                "last_updated": now,
                            }
                        )
                    written += upsert_prompt_ratings_bulk(prompt_ratings_db_path, payload)

        # 2) Aggregation ueber alle Modelle (model_branch = '')
        for scope in ("pos", "neg"):
            toks = sorted(list(touched_global.get(scope) or []))
            for chunk in _chunk_list(toks):
                rows = _fetch_stats_rows(
                    con_stats,
                    scope=scope,
                    tokens=chunk,
                    model_branch=None,
                )
                payload2: List[Dict[str, Any]] = []
                for row in rows:
                    payload2.append(
                        {
                            "scope": scope,
                            "token": str(row["token"] or ""),
                            "model_branch": "",
                            "avg_rating": float(row["avg_rating"])
                            if row["avg_rating"] is not None
                            else None,
                            "mean_score": float(row["mean_score"])
                            if row["mean_score"] is not None
                            else None,
                            "lb05": float(row["lb05"]) if row["lb05"] is not None else None,
                            "runs": int(row["runs"] or 0),
                            "last_updated": now,
                        }
                    )
                written += upsert_prompt_ratings_bulk(prompt_ratings_db_path, payload2)

    finally:
        con_stats.close()

    return {"written": int(written)}
