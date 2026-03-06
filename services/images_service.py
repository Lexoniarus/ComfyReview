from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from stores.images_store import init_images_db, upsert_image, delete_image


def rebuild_images(
    *,
    images_db_path: Path,
    ratings_db_path: Path,
) -> Dict[str, Any]:

    init_images_db(images_db_path)

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row

    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(ratings)").fetchall()}
        has_run = "run" in cols
        order = "ORDER BY run DESC" if has_run else "ORDER BY rowid DESC"

        png_paths = [r["png_path"] for r in con.execute("SELECT DISTINCT png_path FROM ratings").fetchall()]

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        for png_path in png_paths:

            # Existenzcheck: images MV fuehrt nur existierende Dateien
            try:
                if not Path(str(png_path)).exists():
                    delete_image(images_db_path, png_path=str(png_path))
                    continue
            except Exception:
                pass

            latest = con.execute(
                f"""
                SELECT *
                FROM ratings
                WHERE png_path = ?
                {order}
                LIMIT 1
                """,
                [png_path],
            ).fetchone()

            if not latest:
                continue

            deleted_any = con.execute(
                """
                SELECT 1
                FROM ratings
                WHERE png_path = ?
                  AND deleted = 1
                LIMIT 1
                """,
                [png_path],
            ).fetchone()

            if deleted_any:
                delete_image(images_db_path, png_path=png_path)
                continue

            avg_row = con.execute(
                """
                SELECT AVG(rating) AS avg_rating,
                       COUNT(*) AS runs
                FROM ratings
                WHERE png_path = ?
                  AND deleted = 0
                  AND rating IS NOT NULL
                """,
                [png_path],
            ).fetchone()

            row = {
                "png_path": png_path,
                "json_path": latest["json_path"],
                "avg_rating": avg_row["avg_rating"],
                "runs": int(avg_row["runs"] or 0),
                "rating_count": int(latest["rating_count"] or 0),
                "last_run": int(latest["run"] or 0),
                "model_branch": latest["model_branch"],
                "checkpoint": latest["checkpoint"],
                "combo_key": latest["combo_key"],
                "steps": latest["steps"],
                "cfg": latest["cfg"],
                "sampler": latest["sampler"],
                "scheduler": latest["scheduler"],
                "denoise": latest["denoise"],
                "loras_json": latest["loras_json"],
                "pos_prompt": latest["pos_prompt"],
                "neg_prompt": latest["neg_prompt"],
                "last_updated": now,
            }

            upsert_image(images_db_path, row)

        return {"png_paths": len(png_paths)}

    finally:
        con.close()


def update_image_for_png(
    *,
    images_db_path: Path,
    ratings_db_path: Path,
    png_path: str,
) -> Dict[str, Any]:

    init_images_db(images_db_path)

    pp = str(png_path or "").strip()
    if not pp:
        return {"updated": False}

    # Existenzcheck: images MV fuehrt nur existierende Dateien
    try:
        if not Path(pp).exists():
            delete_image(images_db_path, png_path=pp)
            return {"deleted": True, "reason": "file_missing"}
    except Exception:
        return {"updated": False, "reason": "exists_check_failed"}

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row

    try:
        cols = {r["name"] for r in con.execute("PRAGMA table_info(ratings)").fetchall()}
        has_run = "run" in cols
        order = "ORDER BY run DESC" if has_run else "ORDER BY rowid DESC"

        deleted_any = con.execute(
            """
            SELECT 1
            FROM ratings
            WHERE png_path = ?
              AND deleted = 1
            LIMIT 1
            """,
            [pp],
        ).fetchone()

        if deleted_any:
            delete_image(images_db_path, png_path=pp)
            return {"deleted": True, "reason": "deleted_any"}

        latest = con.execute(
            f"""
            SELECT *
            FROM ratings
            WHERE png_path = ?
            {order}
            LIMIT 1
            """,
            [pp],
        ).fetchone()

        if not latest:
            delete_image(images_db_path, png_path=pp)
            return {"deleted": True, "reason": "no_ratings"}

        avg_row = con.execute(
            """
            SELECT AVG(rating) AS avg_rating,
                   COUNT(*) AS runs
            FROM ratings
            WHERE png_path = ?
              AND deleted = 0
              AND rating IS NOT NULL
            """,
            [pp],
        ).fetchone()

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        row = {
            "png_path": pp,
            "json_path": latest["json_path"],
            "avg_rating": avg_row["avg_rating"],
            "runs": int(avg_row["runs"] or 0),
            "rating_count": int(latest["rating_count"] or 0),
            "last_run": int(latest["run"] or 0),
            "model_branch": latest["model_branch"],
            "checkpoint": latest["checkpoint"],
            "combo_key": latest["combo_key"],
            "steps": latest["steps"],
            "cfg": latest["cfg"],
            "sampler": latest["sampler"],
            "scheduler": latest["scheduler"],
            "denoise": latest["denoise"],
            "loras_json": latest["loras_json"],
            "pos_prompt": latest["pos_prompt"],
            "neg_prompt": latest["neg_prompt"],
            "last_updated": now,
        }

        upsert_image(images_db_path, row)
        return {"updated": True}

    finally:
        con.close()
