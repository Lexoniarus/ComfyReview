import sqlite3
from pathlib import Path
from typing import Any, Dict, Optional, List, Iterable, Tuple


def init_images_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)

    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS images (
                png_path TEXT PRIMARY KEY,
                json_path TEXT,
                avg_rating REAL,
                runs INTEGER NOT NULL,
                rating_count INTEGER,
                last_run INTEGER NOT NULL,
                model_branch TEXT,
                checkpoint TEXT,
                combo_key TEXT,
                steps INTEGER,
                cfg REAL,
                sampler TEXT,
                scheduler TEXT,
                denoise REAL,
                loras_json TEXT,
                pos_prompt TEXT,
                neg_prompt TEXT,
                last_updated TEXT
            )
            """
        )
        # Lightweight schema migration (add new columns if table already existed)
        # NOTE: older installs may have created a much smaller images table.
        existing_cols = {r[1] for r in con.execute("PRAGMA table_info(images)").fetchall()}

        def _add(col: str, ddl: str) -> None:
            if col not in existing_cols:
                con.execute(ddl)
                existing_cols.add(col)

        _add("json_path", "ALTER TABLE images ADD COLUMN json_path TEXT")
        _add("avg_rating", "ALTER TABLE images ADD COLUMN avg_rating REAL")
        _add("runs", "ALTER TABLE images ADD COLUMN runs INTEGER")
        _add("rating_count", "ALTER TABLE images ADD COLUMN rating_count INTEGER")
        _add("last_run", "ALTER TABLE images ADD COLUMN last_run INTEGER")
        _add("model_branch", "ALTER TABLE images ADD COLUMN model_branch TEXT")
        _add("checkpoint", "ALTER TABLE images ADD COLUMN checkpoint TEXT")
        _add("combo_key", "ALTER TABLE images ADD COLUMN combo_key TEXT")
        _add("steps", "ALTER TABLE images ADD COLUMN steps INTEGER")
        _add("cfg", "ALTER TABLE images ADD COLUMN cfg REAL")
        _add("sampler", "ALTER TABLE images ADD COLUMN sampler TEXT")
        _add("scheduler", "ALTER TABLE images ADD COLUMN scheduler TEXT")
        _add("denoise", "ALTER TABLE images ADD COLUMN denoise REAL")
        _add("loras_json", "ALTER TABLE images ADD COLUMN loras_json TEXT")
        _add("pos_prompt", "ALTER TABLE images ADD COLUMN pos_prompt TEXT")
        _add("neg_prompt", "ALTER TABLE images ADD COLUMN neg_prompt TEXT")
        _add("last_updated", "ALTER TABLE images ADD COLUMN last_updated TEXT")
        con.commit()
    finally:
        con.close()


def delete_image(db_path: Path, *, png_path: str) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute("DELETE FROM images WHERE png_path = ?", [png_path])
        con.commit()
    finally:
        con.close()


def upsert_image(db_path: Path, row: Dict[str, Any]) -> None:
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            INSERT INTO images (
                png_path, json_path, avg_rating, runs, rating_count, last_run,
                model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise,
                loras_json, pos_prompt, neg_prompt, last_updated
            )
            VALUES (
                :png_path, :json_path, :avg_rating, :runs, :rating_count, :last_run,
                :model_branch, :checkpoint, :combo_key,
                :steps, :cfg, :sampler, :scheduler, :denoise,
                :loras_json, :pos_prompt, :neg_prompt, :last_updated
            )
            ON CONFLICT(png_path) DO UPDATE SET
                json_path=excluded.json_path,
                avg_rating=excluded.avg_rating,
                runs=excluded.runs,
                rating_count=excluded.rating_count,
                last_run=excluded.last_run,
                model_branch=excluded.model_branch,
                checkpoint=excluded.checkpoint,
                combo_key=excluded.combo_key,
                steps=excluded.steps,
                cfg=excluded.cfg,
                sampler=excluded.sampler,
                scheduler=excluded.scheduler,
                denoise=excluded.denoise,
                loras_json=excluded.loras_json,
                pos_prompt=excluded.pos_prompt,
                neg_prompt=excluded.neg_prompt,
                last_updated=excluded.last_updated
            """,
            row,
        )
        con.commit()
    finally:
        con.close()


def fetch_best_images_by_combo_keys(
    db_path: Path,
    combo_keys: List[str],
    *,
    model_branch: str = "",
    limit_per: int = 3,
) -> Dict[str, List[Dict[str, Any]]]:
    """Batch: pro combo_key Top-N Images nach avg_rating/runs."""
    # Ensure schema is up to date (older DBs may miss columns like 'combo_key').
    init_images_db(db_path)
    if not combo_keys:
        return {}

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        placeholders = ",".join(["?"] * len(combo_keys))
        where = f"WHERE combo_key IN ({placeholders})"
        args: List[Any] = list(combo_keys)
        if model_branch:
            where += " AND model_branch = ?"
            args.append(model_branch)

        rows = con.execute(
            f"""
            SELECT combo_key, png_path, json_path, avg_rating, runs
            FROM (
              SELECT
                combo_key, png_path, json_path, avg_rating, runs,
                ROW_NUMBER() OVER (PARTITION BY combo_key ORDER BY avg_rating DESC, runs DESC) AS rn
              FROM images
              {where}
            )
            WHERE rn <= ?
            ORDER BY combo_key, rn
            """,
            (*args, int(limit_per)),
        ).fetchall()

        out: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(str(r["combo_key"] or ""), []).append(dict(r))
        return out
    finally:
        con.close()


def fetch_best_images_by_param_values(
    db_path: Path,
    *,
    feat: str,
    values: List[Any],
    model_branch: str = "",
    limit_per: int = 3,
) -> Dict[str, List[Dict[str, Any]]]:
    """Batch: pro Parameterwert (checkpoint/steps/cfg/sampler/scheduler) Top-N Images."""
    # Ensure schema is up to date (older DBs may miss columns like 'checkpoint').
    init_images_db(db_path)
    allowed = {"checkpoint", "steps", "cfg", "sampler", "scheduler"}
    if feat not in allowed or not values:
        return {}

    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        placeholders = ",".join(["?"] * len(values))
        where = f"WHERE {feat} IN ({placeholders})"
        args: List[Any] = list(values)
        if model_branch:
            where += " AND model_branch = ?"
            args.append(model_branch)

        try:
            rows = con.execute(
                f"""
                SELECT {feat} AS value, png_path, json_path, avg_rating, runs
                FROM (
                  SELECT
                    {feat} AS value, png_path, json_path, avg_rating, runs,
                    ROW_NUMBER() OVER (PARTITION BY {feat} ORDER BY avg_rating DESC, runs DESC) AS rn
                  FROM images
                  {where}
                )
                WHERE rn <= ?
                ORDER BY value, rn
                """,
                (*args, int(limit_per)),
            ).fetchall()
        except sqlite3.OperationalError:
            # If a column is missing despite migrations (custom forks), fail closed.
            return {}

        out: Dict[str, List[Dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(str(r["value"]), []).append(dict(r))
        return out
    finally:
        con.close()
