import sqlite3
from pathlib import Path

from comfyreview.repositories.sqlite import connect_existing

# Was tut es?
# SQLite Infrastruktur und Write API fuer ratings.
#
# Wo kommt es her?
# Router ruft insert_or_update_rating auf, Daten kommen aus:
# - JSON Metadaten Datei (steps cfg sampler scheduler denoise loras prompts)
# - UI Form (rating deleted)
# - Scanner Items (png_path json_path)
#
# Wo geht es hin?
# Alles geht in ratings.sqlite3, Tabelle ratings.


def db(path: Path) -> sqlite3.Connection:
    # Was tut es?
    # Connection oeffnen, row_factory setzen, Schema sicherstellen.
    #
    # Wo kommt es her?
    # path kommt aus config.DB_PATH.
    #
    # Wo geht es hin?
    # Connection wird an Caller zur Nutzung zurueckgegeben.
    return connect_existing(path, rows=True)


def insert_or_update_rating(
    db_path: Path,
    *,
    png_path: str,
    json_path: str,
    model_branch: str,
    checkpoint: str,
    combo_key: str,
    rating: int | None,
    deleted: int,
    steps: int | None,
    cfg: float | None,
    sampler: str | None,
    scheduler: str | None,
    denoise: float | None,
    loras_json: str,
    pos_prompt: str,
    neg_prompt: str,
) -> tuple[int, int]:
    # Was tut es?
    # Schreibt einen neuen Run in ratings.
    # run wird als MAX(run)+1 pro json_path gebildet.
    #
    # Wo kommt es her?
    # png_path json_path kommen aus Scanner oder UI Form.
    # model_branch checkpoint combo_key kommen aus JSON Meta oder UI Form.
    # rating deleted kommen aus UI.
    # steps cfg sampler scheduler denoise loras_json pos_prompt neg_prompt kommen aus JSON Meta.
    #
    # Wo geht es hin?
    # ratings.sqlite3 Tabelle ratings.
    con = db(db_path)
    try:
        row = con.execute(
            "SELECT COALESCE(MAX(run), 0) AS m FROM ratings WHERE json_path = ?",
            (json_path,),
        ).fetchone()
        next_run = int(row["m"] or 0) + 1
        rating_count = next_run

        cursor = con.execute(
            """
            INSERT INTO ratings(
                png_path, json_path, run, model_branch, checkpoint, combo_key,
                rating, deleted, rating_count,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                pos_prompt, neg_prompt
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                png_path,
                json_path,
                next_run,
                model_branch,
                checkpoint,
                combo_key,
                rating,
                int(deleted or 0),
                rating_count,
                steps,
                cfg,
                sampler,
                scheduler,
                denoise,
                loras_json,
                pos_prompt,
                neg_prompt,
            ),
        )
        rating_id = int(cursor.lastrowid or 0)
        con.commit()
        return rating_id, next_run
    finally:
        con.close()


def delete_rating_by_id(db_path: Path, *, rating_id: int) -> None:
    """Delete one rating event as compensation for a failed legacy workflow."""
    con = db(db_path)
    try:
        con.execute("DELETE FROM ratings WHERE id = ?", (int(rating_id),))
        con.commit()
    finally:
        con.close()


def get_rated_map(con: sqlite3.Connection) -> dict[str, int]:
    # Was tut es?
    # Liefert je json_path die Anzahl Runs.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # index view nutzt das fuer unrated filter und rated_count Anzeige.
    rows = con.execute(
        "SELECT json_path, COALESCE(MAX(run), 0) AS c FROM ratings GROUP BY json_path"
    ).fetchall()
    return {str(r["json_path"]): int(r["c"] or 0) for r in rows}


def list_models_from_db(db_path: Path) -> list[str]:
    # Was tut es?
    # Dropdown Werte fuer model_branch.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # Filter Dropdown in stats recommendations param_stats prompt_tokens.
    con = db(db_path)
    rows = con.execute(
        "SELECT DISTINCT model_branch FROM ratings ORDER BY model_branch"
    ).fetchall()
    con.close()
    return [str(r["model_branch"]) for r in rows if r["model_branch"]]
