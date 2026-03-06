import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

def _ensure_columns(con: sqlite3.Connection) -> None:
    cols = {row[1] for row in con.execute("PRAGMA table_info(prompt_ratings)").fetchall()}
    # Neue Spalten für UI-Kompatibilität (Prompt Tokens Seite) und lb05 Ranking
    if "mean_score" not in cols:
        con.execute("ALTER TABLE prompt_ratings ADD COLUMN mean_score REAL")
    if "lb05" not in cols:
        con.execute("ALTER TABLE prompt_ratings ADD COLUMN lb05 REAL")


def init_prompt_ratings_db(db_path: Path) -> None:
    """Init prompt_ratings DB.

    Dieses DB File ist eine Materialized View, abgeleitet aus prompt_tokens.sqlite3.

    Key
      (scope, token, model_branch)

    Wichtig
      Delete spielt hier KEINE Rolle als Filter.
      Datenpunkt ist: rating IS NOT NULL oder deleted=1. deleted zaehlt negativ als rating 0.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS prompt_ratings (
                scope TEXT NOT NULL,         -- pos|neg
                token TEXT NOT NULL,         -- exakt wie in prompt_store.tokenize
                model_branch TEXT NOT NULL,  -- zB model name oder '' fuer all

                avg_rating REAL,
                runs INTEGER NOT NULL,

                last_updated TEXT,

                PRIMARY KEY(scope, token, model_branch)
            )
            """
        )
        con.execute("CREATE INDEX IF NOT EXISTS idx_pr_scope ON prompt_ratings(scope)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_pr_token ON prompt_ratings(token)")
        con.execute("CREATE INDEX IF NOT EXISTS idx_pr_model ON prompt_ratings(model_branch)")
        _ensure_columns(con)
        con.commit()
    finally:
        con.close()


def clear_prompt_ratings(db_path: Path) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM prompt_ratings")
        con.commit()
    finally:
        con.close()


def upsert_prompt_rating(db_path: Path, row: Dict[str, Any]) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO prompt_ratings(
                scope, token, model_branch,
                avg_rating, mean_score, lb05, runs,
                last_updated
            ) VALUES (
                :scope, :token, :model_branch,
                :avg_rating, :mean_score, :lb05, :runs,
                :last_updated
            )
            ON CONFLICT(scope, token, model_branch) DO UPDATE SET
                avg_rating=excluded.avg_rating,
                mean_score=excluded.mean_score,
                lb05=excluded.lb05,
                runs=excluded.runs,
                last_updated=excluded.last_updated
            """,
            row,
        )
        con.commit()
    finally:
        con.close()



# Shared UPSERT statement for single-row and bulk writes.
_UPSERT_PROMPT_RATING_SQL = """
    INSERT INTO prompt_ratings(
        scope, token, model_branch,
        avg_rating, mean_score, lb05, runs,
        last_updated
    ) VALUES (
        :scope, :token, :model_branch,
        :avg_rating, :mean_score, :lb05, :runs,
        :last_updated
    )
    ON CONFLICT(scope, token, model_branch) DO UPDATE SET
        avg_rating=excluded.avg_rating,
        mean_score=excluded.mean_score,
        lb05=excluded.lb05,
        runs=excluded.runs,
        last_updated=excluded.last_updated
"""


def upsert_prompt_ratings_bulk(db_path: Path, rows: List[Dict[str, Any]]) -> int:
    """Bulk upsert for prompt_ratings.

    Used by the MV worker to update many tokens efficiently.
    Semantics are identical to upsert_prompt_rating().
    """
    if not rows:
        return 0

    con = sqlite3.connect(db_path)
    try:
        con.executemany(_UPSERT_PROMPT_RATING_SQL, rows)
        con.commit()
        return int(len(rows))
    finally:
        con.close()


def fetch_prompt_rating_map(
    db_path: Path,
    *,
    scope: str,
    model_branch: str = "",
    tokens: Optional[List[str]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return mapping token -> {avg_rating, runs}."""
    scope = str(scope or "pos").strip()
    if scope not in {"pos", "neg"}:
        scope = "pos"

    # IMPORTANT:
    # model_branch ist bei euch de-facto der Checkpoint Name.
    # Wenn kein model_branch uebergeben wird, muessen wir deterministisch
    # NUR die aggregierten Rows mit model_branch='' nehmen.
    # Sonst werden mehrere Branches geladen und im Dict ueber-schrieben.
    mb = str(model_branch or "")

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        where = "WHERE scope = ? AND model_branch = ?"
        args: List[Any] = [scope, mb]

        if tokens:
            toks = [str(t).strip() for t in tokens if str(t).strip()]
            if toks:
                qmarks = ",".join(["?"] * len(toks))
                where += f" AND token IN ({qmarks})"
                args.extend(toks)

        rows = con.execute(
            f"""
            SELECT token, avg_rating, runs
            FROM prompt_ratings
            {where}
            """,
            args,
        ).fetchall()

        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            out[str(r["token"])] = {
                "avg_rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
                "runs": int(r["runs"] or 0),
            }
        return out
    finally:
        con.close()


def fetch_prompt_ratings_stats(
    db_path: Path,
    *,
    model: str = "",
    scope: str = "pos",
    min_n: int = 8,
    limit: int = 200,
) -> List[Dict[str, Any]]:
    """Liest Prompt Ratings (Aggregat) für die Prompt Tokens UI.

    Liefert kompatibel zu prompt_store.fetch_token_stats():
      token, n, mean_score, lb05
    """
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        where = "WHERE scope = ?"
        args: List[Any] = [scope]
        if model:
            where += " AND model_branch = ?"
            args.append(model)

        rows = con.execute(
            f"""
            SELECT
              token,
              runs AS n,
              COALESCE(mean_score, avg_rating) AS mean_score,
              lb05
            FROM prompt_ratings
            {where}
              AND runs >= ?
            ORDER BY lb05 DESC, runs DESC
            LIMIT ?
            """,
            (*args, int(min_n), int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()
