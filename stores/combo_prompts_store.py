from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite import connect_existing


def init_combo_prompts_db(db_path: Path) -> None:
    """Verify that the startup-managed combo database still exists."""
    connect_existing(db_path).close()


def clear_combo_prompts(db_path: Path) -> None:
    con = connect_existing(db_path)
    try:
        con.execute("DELETE FROM combo_prompts")
        con.execute("DELETE FROM combo_best_images")
        con.commit()
    finally:
        con.close()


def upsert_combo_prompt(db_path: Path, row: dict[str, Any]) -> None:
    con = connect_existing(db_path)
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
                combo_pos_avg_rating, combo_pos_runs, combo_pos_total_tokens,
                combo_pos_rated_tokens, combo_pos_coverage,
                combo_neg_avg_rating, combo_neg_runs, combo_neg_total_tokens,
                combo_neg_rated_tokens, combo_neg_coverage,
                last_updated
            ) VALUES (
                :combo_key, :combo_size,
                :character_id, :scene_id, :outfit_id,
                :label,
                :pos_tokens, :neg_tokens,
                :score, :coverage, :stability,
                :best_json_path, :best_png_path, :best_avg_rating, :best_runs,
                :best_hits,
                :combo_avg_rating, :combo_image_count, :combo_total_runs,
                :combo_pos_avg_rating, :combo_pos_runs, :combo_pos_total_tokens,
                :combo_pos_rated_tokens, :combo_pos_coverage,
                :combo_neg_avg_rating, :combo_neg_runs, :combo_neg_total_tokens,
                :combo_neg_rated_tokens, :combo_neg_coverage,
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


def upsert_combo_best_image(db_path: Path, row: dict[str, Any]) -> None:
    con = connect_existing(db_path)
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


def list_top_combo_prompts(
    db_path: Path, *, combo_size: int, limit: int = 3
) -> list[dict[str, Any]]:
    con = connect_existing(db_path, rows=True)
    try:
        rows = con.execute(
            """
            SELECT
                combo_key, combo_size,
                character_id, scene_id, outfit_id,
                label,
                score, coverage, stability,
                best_json_path, best_png_path, best_avg_rating, best_runs,
                best_hits,
                combo_avg_rating, combo_image_count, combo_total_runs,
                combo_pos_avg_rating, combo_pos_runs, combo_pos_total_tokens,
                combo_pos_rated_tokens, combo_pos_coverage,
                combo_neg_avg_rating, combo_neg_runs, combo_neg_total_tokens,
                combo_neg_rated_tokens, combo_neg_coverage,
                last_updated
            FROM combo_prompts
            WHERE combo_size = ?
            ORDER BY
                CASE WHEN combo_avg_rating IS NULL THEN 0 ELSE 1 END DESC,
                combo_avg_rating DESC,
                combo_total_runs DESC,
                combo_image_count DESC,
                CASE WHEN combo_pos_runs IS NULL OR combo_pos_runs = 0
                    THEN 0 ELSE 1 END DESC,
                combo_pos_avg_rating DESC,
                combo_pos_runs DESC,
                combo_pos_coverage DESC,
                last_updated DESC
            LIMIT ?
            """,
            (int(combo_size), int(limit)),
        ).fetchall()
        return [dict(row) for row in rows]
    finally:
        con.close()


def list_best_images_for_combo(
    db_path: Path, *, combo_key: str, limit: int = 3
) -> list[dict[str, Any]]:
    con = connect_existing(db_path, rows=True)
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
        return [dict(row) for row in rows]
    finally:
        con.close()


def list_top_combo_prompts_with_images(
    db_path: Path, *, combo_size: int, limit: int = 3
) -> list[dict[str, Any]]:
    combos = list_top_combo_prompts(
        db_path,
        combo_size=int(combo_size),
        limit=int(limit),
    )
    output: list[dict[str, Any]] = []
    for combo in combos:
        item = dict(combo)
        item["best_images"] = list_best_images_for_combo(
            db_path,
            combo_key=str(item.get("combo_key")),
            limit=3,
        )
        output.append(item)
    return output
