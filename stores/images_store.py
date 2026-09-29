import sqlite3
from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def init_images_db(db_path: Path) -> None:
    """Verify that the startup-managed image database still exists."""
    connect_existing(db_path).close()


def delete_image(db_path: Path, *, png_path: str) -> None:
    con = connect_existing(db_path)
    try:
        con.execute("DELETE FROM images WHERE png_path = ?", [png_path])
        con.commit()
    finally:
        con.close()


def upsert_image(db_path: Path, row: dict[str, Any]) -> None:
    con = connect_existing(db_path)
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
    combo_keys: list[str],
    *,
    model_branch: str = "",
    limit_per: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Batch: pro combo_key Top-N Images nach avg_rating/runs."""
    # Ensure schema is up to date (older DBs may miss columns like 'combo_key').
    if not combo_keys:
        return {}

    con = connect_existing(db_path, rows=True)
    try:
        placeholders = ",".join(["?"] * len(combo_keys))
        where = f"WHERE combo_key IN ({placeholders})"
        args: list[Any] = list(combo_keys)
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

        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(str(r["combo_key"] or ""), []).append(dict(r))
        return out
    finally:
        con.close()


def fetch_best_images_by_param_values(
    db_path: Path,
    *,
    feat: str,
    values: list[Any],
    model_branch: str = "",
    limit_per: int = 3,
) -> dict[str, list[dict[str, Any]]]:
    """Batch: pro Parameterwert (checkpoint/steps/cfg/sampler/scheduler) Top-N Images."""
    # Ensure schema is up to date (older DBs may miss columns like 'checkpoint').
    allowed = {"checkpoint", "steps", "cfg", "sampler", "scheduler"}
    if feat not in allowed or not values:
        return {}

    con = connect_existing(db_path, rows=True)
    try:
        placeholders = ",".join(["?"] * len(values))
        where = f"WHERE {feat} IN ({placeholders})"
        args: list[Any] = list(values)
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

        out: dict[str, list[dict[str, Any]]] = {}
        for r in rows:
            out.setdefault(str(r["value"]), []).append(dict(r))
        return out
    finally:
        con.close()
