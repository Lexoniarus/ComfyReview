import sqlite3
from pathlib import Path
from typing import Dict, List, Optional

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
    con = sqlite3.connect(path)
    con.row_factory = sqlite3.Row
    _ensure_schema(con)
    return con


def _ensure_schema(con: sqlite3.Connection) -> None:
    # Was tut es?
    # Tabelle ratings und Indexe erstellen.
    # Migrationen fuer fehlende Spalten nachziehen.
    #
    # Wo kommt es her?
    # con ist SQLite Connection.
    #
    # Wo geht es hin?
    # Persistiert in ratings.sqlite3.
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            png_path TEXT NOT NULL,
            json_path TEXT NOT NULL,
            run INTEGER NOT NULL DEFAULT 1,
            model_branch TEXT NOT NULL,
            checkpoint TEXT NOT NULL,
            combo_key TEXT NOT NULL,
            rating INTEGER,
            deleted INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 1,

            steps INTEGER,
            cfg REAL,
            sampler TEXT,
            scheduler TEXT,
            denoise REAL,
            loras_json TEXT DEFAULT '',

            pos_prompt TEXT DEFAULT '',
            neg_prompt TEXT DEFAULT ''
        )
        """
    )

    con.execute("CREATE INDEX IF NOT EXISTS idx_ratings_json_run ON ratings(json_path, run)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ratings_model ON ratings(model_branch)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ratings_combo ON ratings(model_branch, combo_key)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ratings_deleted ON ratings(deleted)")
    con.execute("CREATE INDEX IF NOT EXISTS idx_ratings_rating ON ratings(rating)")

    # Migrationen fuer alte DBs
    cols = {row["name"] for row in con.execute("PRAGMA table_info(ratings)").fetchall()}
    if "steps" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN steps INTEGER")
    if "cfg" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN cfg REAL")
    if "sampler" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN sampler TEXT")
    if "scheduler" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN scheduler TEXT")
    if "denoise" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN denoise REAL")
    if "loras_json" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN loras_json TEXT DEFAULT ''")
    if "pos_prompt" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN pos_prompt TEXT DEFAULT ''")
    if "neg_prompt" not in cols:
        con.execute("ALTER TABLE ratings ADD COLUMN neg_prompt TEXT DEFAULT ''")


def insert_or_update_rating(
    db_path: Path,
    *,
    png_path: str,
    json_path: str,
    model_branch: str,
    checkpoint: str,
    combo_key: str,
    rating: Optional[int],
    deleted: int,
    steps: Optional[int],
    cfg: Optional[float],
    sampler: Optional[str],
    scheduler: Optional[str],
    denoise: Optional[float],
    loras_json: str,
    pos_prompt: str,
    neg_prompt: str,
) -> None:
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

    row = con.execute(
        "SELECT COALESCE(MAX(run), 0) AS m FROM ratings WHERE json_path = ?",
        (json_path,),
    ).fetchone()
    next_run = int(row["m"] or 0) + 1
    rating_count = next_run

    con.execute(
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
    con.commit()
    con.close()


def get_rated_map(con: sqlite3.Connection) -> Dict[str, int]:
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


def list_models_from_db(db_path: Path) -> List[str]:
    # Was tut es?
    # Dropdown Werte fuer model_branch.
    #
    # Wo kommt es her?
    # ratings.sqlite3 Tabelle ratings.
    #
    # Wo geht es hin?
    # Filter Dropdown in stats recommendations param_stats prompt_tokens.
    con = db(db_path)
    rows = con.execute("SELECT DISTINCT model_branch FROM ratings ORDER BY model_branch").fetchall()
    con.close()
    return [str(r["model_branch"]) for r in rows if r["model_branch"]]