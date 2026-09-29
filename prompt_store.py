import sqlite3
from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def db(path: Path) -> sqlite3.Connection:
    return connect_existing(path, rows=True)


def tokenize(text: str) -> list[str]:
    """
    Tokenisierung ausschließlich per Komma.
    Es wird NICHTS am Inhalt verändert.
    Gewichte und Klammern bleiben exakt erhalten.
    """

    if not text:
        return []

    # Nur Newlines in Spaces umwandeln
    t = str(text).replace("\n", " ")

    # Ausschließlich Komma als Trennzeichen
    parts = [p.strip() for p in t.split(",")]

    # Leere Einträge entfernen
    return [p for p in parts if p]


def rebuild_prompt_db(ratings_db_path: Path, prompt_db_path: Path) -> None:
    con_out = db(prompt_db_path)
    con_out.execute("DELETE FROM tokens")
    con_out.commit()

    con_in = connect_existing(ratings_db_path, rows=True)

    rows = con_in.execute(
        """
        SELECT json_path, run, model_branch, rating, deleted, pos_prompt, neg_prompt
        FROM ratings
        """
    ).fetchall()

    for r in rows:
        json_path = str(r["json_path"])
        run = int(r["run"] or 0)
        model_branch = str(r["model_branch"])
        rating = r["rating"]
        deleted = int(r["deleted"] or 0)
        pos = str(r["pos_prompt"] or "")
        neg = str(r["neg_prompt"] or "")

        for tok in tokenize(pos):
            con_out.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (json_path, run, model_branch, "pos", tok, rating, deleted),
            )
        for tok in tokenize(neg):
            con_out.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (json_path, run, model_branch, "neg", tok, rating, deleted),
            )

    con_out.commit()
    con_out.close()
    con_in.close()


def fetch_token_stats(
    prompt_db_path: Path,
    *,
    model: str = "",
    scope: str = "pos",
    min_n: int = 8,
    limit: int = 200,
) -> list[dict[str, Any]]:
    con = db(prompt_db_path)

    where = "WHERE scope = ?"
    args: list[Any] = [scope]
    if model:
        where += " AND model_branch = ?"
        args.append(model)

    rows = con.execute(
        f"""
        SELECT token,
               SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) as n,
               AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) as mean_score,
               AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) - 1.645 * (
                    CASE WHEN SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END) > 1 THEN
                      sqrt(
                        AVG((CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * (CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END))
                        - AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END) * AVG(CASE WHEN deleted=1 THEN 0 WHEN rating IS NOT NULL THEN rating END)
                      )
                    ELSE 0 END
                 ) / sqrt(SUM(CASE WHEN deleted=1 OR rating IS NOT NULL THEN 1 ELSE 0 END)) as lb05
        FROM tokens
        {where}
        GROUP BY token
        HAVING n >= ?
        ORDER BY lb05 DESC, mean_score DESC, n DESC
        LIMIT ?
        """,
        args + [min_n, limit],
    ).fetchall()

    out: list[dict[str, Any]] = []
    for r in rows:
        out.append(
            {
                "token": str(r["token"]),
                "n": int(r["n"] or 0),
                "mean_score": float(r["mean_score"] or 0.0),
                "lb05": float(r["lb05"] or 0.0),
            }
        )

    con.close()
    return out
