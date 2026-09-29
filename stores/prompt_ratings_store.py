from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def init_prompt_ratings_db(db_path: Path) -> None:
    """Verify that the startup-managed prompt-rating database exists."""
    connect_existing(db_path).close()


def clear_prompt_ratings(db_path: Path) -> None:
    con = connect_existing(db_path)
    try:
        con.execute("DELETE FROM prompt_ratings")
        con.commit()
    finally:
        con.close()


def upsert_prompt_rating(db_path: Path, row: dict[str, Any]) -> None:
    con = connect_existing(db_path)
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


def upsert_prompt_ratings_bulk(
    db_path: Path, rows: list[dict[str, Any]]
) -> int:
    """Bulk upsert for prompt_ratings.

    Used by the MV worker to update many tokens efficiently.
    Semantics are identical to upsert_prompt_rating().
    """
    if not rows:
        return 0

    con = connect_existing(db_path)
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
    tokens: list[str] | None = None,
) -> dict[str, dict[str, Any]]:
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

    con = connect_existing(db_path, rows=True)
    try:
        where = "WHERE scope = ? AND model_branch = ?"
        args: list[Any] = [scope, mb]

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

        out: dict[str, dict[str, Any]] = {}
        for r in rows:
            out[str(r["token"])] = {
                "avg_rating": float(r["avg_rating"])
                if r["avg_rating"] is not None
                else None,
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
) -> list[dict[str, Any]]:
    """Liest Prompt Ratings (Aggregat) für die Prompt Tokens UI.

    Liefert kompatibel zu prompt_store.fetch_token_stats():
      token, n, mean_score, lb05
    """
    con = connect_existing(db_path, rows=True)
    try:
        where = "WHERE scope = ?"
        args: list[Any] = [scope]
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
