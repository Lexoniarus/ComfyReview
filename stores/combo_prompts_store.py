import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def _ensure_column(con: sqlite3.Connection, *, table: str, col: str, ddl: str) -> None:
    existing_cols = {r[1] for r in con.execute(f"PRAGMA table_info({table})").fetchall()}
    if col not in existing_cols:
        con.execute(ddl)


def _is_corrupt_db_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    needles = (
        "database disk image is malformed",
        "database schema is malformed",
        "file is not a database",
        "not a database",
    )
    return any(n in msg for n in needles)


def _quarantine_corrupt_db(db_path: Path) -> None:
    if not db_path.exists():
        return
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    target = db_path.with_name(f"{db_path.stem}.corrupt_{stamp}{db_path.suffix}")
    try:
        os.replace(str(db_path), str(target))
    except Exception:
        try:
            db_path.unlink()
        except Exception:
            pass


def _connect_combo_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        return sqlite3.connect(db_path)
    except sqlite3.DatabaseError as exc:
        if not _is_corrupt_db_error(exc):
            raise
        _quarantine_corrupt_db(db_path)
        return sqlite3.connect(db_path)


def init_combo_prompts_db(db_path: Path) -> None:
    """Init combo_prompts DB.

    combo_prompts
      Materialized View pro Kombination.

    combo_best_images
      Top 3 Bilder pro Kombination (rank 1..3).
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        con = _connect_combo_db(db_path)
        try:
            con.execute(
                """
                CREATE TABLE IF NOT EXISTS combo_prompts (
                    combo_key TEXT PRIMARY KEY,
                    combo_size INTEGER NOT NULL,

                    character_id INTEGER,
                    scene_id INTEGER,
                    outfit_id INTEGER,

                    label TEXT,

                    pos_tokens TEXT,
                    neg_tokens TEXT,

                    score REAL,
                    coverage REAL,
                    stability REAL,

                    best_json_path TEXT,
                    best_png_path TEXT,
                    best_avg_rating REAL,
                    best_runs INTEGER,
                    best_hits INTEGER,

                    combo_avg_rating REAL,
                    combo_image_count INTEGER,
                    combo_total_runs INTEGER,

                    -- SOLL: Prompt Ratings (pos + neg getrennt)
                    combo_pos_avg_rating REAL,
                    combo_pos_runs INTEGER,
                    combo_pos_total_tokens INTEGER,
                    combo_pos_rated_tokens INTEGER,
                    combo_pos_coverage REAL,

                    combo_neg_avg_rating REAL,
                    combo_neg_runs INTEGER,
                    combo_neg_total_tokens INTEGER,
                    combo_neg_rated_tokens INTEGER,
                    combo_neg_coverage REAL,

                    last_updated TEXT
                )
                """
            )

            _ensure_column(con, table="combo_prompts", col="combo_avg_rating", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_avg_rating REAL")
            _ensure_column(con, table="combo_prompts", col="combo_image_count", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_image_count INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_total_runs", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_total_runs INTEGER")

            _ensure_column(con, table="combo_prompts", col="combo_pos_avg_rating", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_pos_avg_rating REAL")
            _ensure_column(con, table="combo_prompts", col="combo_pos_runs", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_pos_runs INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_pos_total_tokens", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_pos_total_tokens INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_pos_rated_tokens", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_pos_rated_tokens INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_pos_coverage", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_pos_coverage REAL")

            _ensure_column(con, table="combo_prompts", col="combo_neg_avg_rating", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_neg_avg_rating REAL")
            _ensure_column(con, table="combo_prompts", col="combo_neg_runs", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_neg_runs INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_neg_total_tokens", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_neg_total_tokens INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_neg_rated_tokens", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_neg_rated_tokens INTEGER")
            _ensure_column(con, table="combo_prompts", col="combo_neg_coverage", ddl="ALTER TABLE combo_prompts ADD COLUMN combo_neg_coverage REAL")

            con.execute(
                """
                CREATE TABLE IF NOT EXISTS combo_best_images (
                    combo_key TEXT NOT NULL,
                    rank INTEGER NOT NULL,
                    png_path TEXT NOT NULL,
                    json_path TEXT,
                    avg_rating REAL,
                    runs INTEGER,
                    PRIMARY KEY(combo_key, rank)
                )
                """
            )

            con.execute("CREATE INDEX IF NOT EXISTS idx_combo_prompts_size_score ON combo_prompts(combo_size, score DESC)")
            con.execute("CREATE INDEX IF NOT EXISTS idx_combo_best_images_combo ON combo_best_images(combo_key)")
            con.commit()
        finally:
            con.close()
    except sqlite3.DatabaseError as exc:
        if not _is_corrupt_db_error(exc):
            raise
        _quarantine_corrupt_db(db_path)
        con = sqlite3.connect(db_path)
        try:
            con.close()
        finally:
            pass
        return init_combo_prompts_db(db_path)


def clear_combo_prompts(db_path: Path) -> None:
    init_combo_prompts_db(db_path)
    con = _connect_combo_db(db_path)
    try:
        con.execute("DELETE FROM combo_prompts")
        con.execute("DELETE FROM combo_best_images")
        con.commit()
    finally:
        con.close()


def upsert_combo_prompt(db_path: Path, row: Dict[str, Any]) -> None:
    init_combo_prompts_db(db_path)
    con = _connect_combo_db(db_path)
    try:
        con.execute(
            """
            INSERT INTO combo_prompts (
                combo_key, combo_size,
                character_id, scene_id, outfit_id,
                label,
                pos_tokens, neg_tokens,
                score, coverage, stability,
                best_json_path, best_png_path, best_avg_rating, best_runs, best_hits,
                combo_avg_rating, combo_image_count, combo_total_runs,

                combo_pos_avg_rating, combo_pos_runs, combo_pos_total_tokens, combo_pos_rated_tokens, combo_pos_coverage,
                combo_neg_avg_rating, combo_neg_runs, combo_neg_total_tokens, combo_neg_rated_tokens, combo_neg_coverage,

                last_updated
            ) VALUES (
                :combo_key, :combo_size,
                :character_id, :scene_id, :outfit_id,
                :label,
                :pos_tokens, :neg_tokens,
                :score, :coverage, :stability,
                :best_json_path, :best_png_path, :best_avg_rating, :best_runs, :best_hits,
                :combo_avg_rating, :combo_image_count, :combo_total_runs,

                :combo_pos_avg_rating, :combo_pos_runs, :combo_pos_total_tokens, :combo_pos_rated_tokens, :combo_pos_coverage,
                :combo_neg_avg_rating, :combo_neg_runs, :combo_neg_total_tokens, :combo_neg_rated_tokens, :combo_neg_coverage,

                :last_updated
            )
            ON CONFLICT(combo_key) DO UPDATE SET
                combo_size=excluded.combo_size,
                character_id=excluded.character_id,
                scene_id=excluded.scene_id,
                outfit_id=excluded.outfit_id,
                label=excluded.label,
                pos_tokens=excluded.pos_tokens,
                neg_tokens=excluded.neg_tokens,
                score=excluded.score,
                coverage=excluded.coverage,
                stability=excluded.stability,
                best_json_path=excluded.best_json_path,
                best_png_path=excluded.best_png_path,
                best_avg_rating=excluded.best_avg_rating,
                best_runs=excluded.best_runs,
                best_hits=excluded.best_hits,
                combo_avg_rating=excluded.combo_avg_rating,
                combo_image_count=excluded.combo_image_count,
                combo_total_runs=excluded.combo_total_runs,

                combo_pos_avg_rating=excluded.combo_pos_avg_rating,
                combo_pos_runs=excluded.combo_pos_runs,
                combo_pos_total_tokens=excluded.combo_pos_total_tokens,
                combo_pos_rated_tokens=excluded.combo_pos_rated_tokens,
                combo_pos_coverage=excluded.combo_pos_coverage,

                combo_neg_avg_rating=excluded.combo_neg_avg_rating,
                combo_neg_runs=excluded.combo_neg_runs,
                combo_neg_total_tokens=excluded.combo_neg_total_tokens,
                combo_neg_rated_tokens=excluded.combo_neg_rated_tokens,
                combo_neg_coverage=excluded.combo_neg_coverage,

                last_updated=excluded.last_updated
            """,
            row,
        )
        con.commit()
    finally:
        con.close()


def upsert_combo_best_image(db_path: Path, row: Dict[str, Any]) -> None:
    init_combo_prompts_db(db_path)
    con = _connect_combo_db(db_path)
    try:
        con.execute(
            """
            INSERT INTO combo_best_images (
                combo_key, rank,
                png_path, json_path,
                avg_rating, runs
            ) VALUES (
                :combo_key, :rank,
                :png_path, :json_path,
                :avg_rating, :runs
            )
            ON CONFLICT(combo_key, rank) DO UPDATE SET
                png_path=excluded.png_path,
                json_path=excluded.json_path,
                avg_rating=excluded.avg_rating,
                runs=excluded.runs
            """,
            row,
        )
        con.commit()
    finally:
        con.close()


def list_top_combo_prompts(db_path: Path, *, combo_size: int, limit: int = 3) -> List[Dict[str, Any]]:
    init_combo_prompts_db(db_path)
    con = _connect_combo_db(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT
                combo_key, combo_size,
                character_id, scene_id, outfit_id,
                label,
                score, coverage, stability,
                best_json_path, best_png_path, best_avg_rating, best_runs, best_hits,

                combo_avg_rating, combo_image_count, combo_total_runs,

                combo_pos_avg_rating, combo_pos_runs, combo_pos_total_tokens, combo_pos_rated_tokens, combo_pos_coverage,
                combo_neg_avg_rating, combo_neg_runs, combo_neg_total_tokens, combo_neg_rated_tokens, combo_neg_coverage,

                last_updated
            FROM combo_prompts
            WHERE combo_size = ?
            ORDER BY
                CASE WHEN combo_avg_rating IS NULL THEN 0 ELSE 1 END DESC,
                combo_avg_rating DESC,
                combo_total_runs DESC,
                combo_image_count DESC,
                CASE WHEN combo_pos_runs IS NULL OR combo_pos_runs = 0 THEN 0 ELSE 1 END DESC,
                combo_pos_avg_rating DESC,
                combo_pos_runs DESC,
                combo_pos_coverage DESC,
                last_updated DESC
            LIMIT ?
            """,
            (int(combo_size), int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def list_best_images_for_combo(db_path: Path, *, combo_key: str, limit: int = 3) -> List[Dict[str, Any]]:
    init_combo_prompts_db(db_path)
    con = _connect_combo_db(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT combo_key, rank, png_path, json_path, avg_rating, runs
            FROM combo_best_images
            WHERE combo_key = ?
            ORDER BY rank ASC
            LIMIT ?
            """,
            (str(combo_key), int(limit)),
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        con.close()


def list_top_combo_prompts_with_images(db_path: Path, *, combo_size: int, limit: int = 3) -> List[Dict[str, Any]]:
    combos = list_top_combo_prompts(db_path, combo_size=int(combo_size), limit=int(limit))
    out: List[Dict[str, Any]] = []
    for c in combos:
        c = dict(c)
        c["best_images"] = list_best_images_for_combo(db_path, combo_key=str(c.get("combo_key")), limit=3)
        out.append(c)
    return out
