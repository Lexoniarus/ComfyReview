from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from prompt_store import db as prompt_tokens_db
from prompt_store import tokenize

from stores.images_store import init_images_db, upsert_image, delete_image
from stores.prompt_ratings_store import init_prompt_ratings_db, upsert_prompt_rating

from services.combo_prompts_service import rebuild_combo_prompts


def _max_run_for_json(ratings_db_path: Path, json_path: str) -> int:
    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute(
            "SELECT COALESCE(MAX(run), 0) AS m FROM ratings WHERE json_path = ?",
            (str(json_path),),
        ).fetchone()
        return int(row["m"] or 0)
    finally:
        con.close()


def _update_prompt_tokens_for_run(
    *,
    prompt_tokens_db_path: Path,
    json_path: str,
    run: int,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating: Optional[int],
    deleted: int,
) -> Dict[str, Any]:
    con = prompt_tokens_db(prompt_tokens_db_path)
    try:
        con.execute(
            "DELETE FROM tokens WHERE json_path = ? AND run = ?",
            (str(json_path), int(run)),
        )

        pos_tokens = tokenize(pos_prompt or "")
        neg_tokens = tokenize(neg_prompt or "")

        for tok in pos_tokens:
            con.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (str(json_path), int(run), str(model_branch or ""), "pos", str(tok), rating, int(deleted or 0)),
            )
        for tok in neg_tokens:
            con.execute(
                "INSERT INTO tokens(json_path, run, model_branch, scope, token, rating, deleted) VALUES(?,?,?,?,?,?,?)",
                (str(json_path), int(run), str(model_branch or ""), "neg", str(tok), rating, int(deleted or 0)),
            )

        con.commit()
        return {"pos_tokens": int(len(pos_tokens)), "neg_tokens": int(len(neg_tokens))}
    finally:
        con.close()


def _fetch_prompt_stats(
    *,
    prompt_tokens_db_path: Path,
    scope: str,
    tokens: List[str],
    model_branch: Optional[str],
) -> Dict[str, Dict[str, Any]]:
    toks = [str(t).strip() for t in (tokens or []) if str(t).strip()]
    if not toks:
        return {}

    con = sqlite3.connect(prompt_tokens_db_path)
    con.row_factory = sqlite3.Row
    try:
        qmarks = ",".join(["?"] * len(toks))
        sql = f"""
            SELECT token,
                   AVG(CASE WHEN rating IS NOT NULL THEN rating END) AS avg_rating,
                   SUM(CASE WHEN rating IS NOT NULL THEN 1 ELSE 0 END) AS runs
            FROM tokens
            WHERE scope = ?
              AND token IN ({qmarks})
        """
        args: List[Any] = [str(scope)] + toks
        if model_branch is not None:
            sql += " AND model_branch = ?"
            args.append(str(model_branch))
        sql += " GROUP BY token"

        rows = con.execute(sql, args).fetchall()
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            out[str(r["token"])] = {
                "avg_rating": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
                "runs": int(r["runs"] or 0),
            }
        return out
    finally:
        con.close()


def _update_prompt_ratings_for_tokens(
    *,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    model_branch: str,
    pos_tokens: List[str],
    neg_tokens: List[str],
) -> Dict[str, Any]:
    init_prompt_ratings_db(prompt_ratings_db_path)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    written = 0
    # model_branch spezifisch
    for scope, toks in (("pos", pos_tokens), ("neg", neg_tokens)):
        stats = _fetch_prompt_stats(
            prompt_tokens_db_path=prompt_tokens_db_path,
            scope=scope,
            tokens=toks,
            model_branch=str(model_branch or ""),
        )
        for token, d in stats.items():
            upsert_prompt_rating(
                prompt_ratings_db_path,
                {
                    "scope": scope,
                    "token": token,
                    "model_branch": str(model_branch or ""),
                    "avg_rating": d.get("avg_rating"),
                    "runs": int(d.get("runs") or 0),
                    "last_updated": now,
                },
            )
            written += 1

        # Aggregation ueber alle model_branches (model_branch='')
        stats_all = _fetch_prompt_stats(
            prompt_tokens_db_path=prompt_tokens_db_path,
            scope=scope,
            tokens=toks,
            model_branch=None,
        )
        for token, d in stats_all.items():
            upsert_prompt_rating(
                prompt_ratings_db_path,
                {
                    "scope": scope,
                    "token": token,
                    "model_branch": "",
                    "avg_rating": d.get("avg_rating"),
                    "runs": int(d.get("runs") or 0),
                    "last_updated": now,
                },
            )
            written += 1

    return {"written": int(written)}


def _update_image_row_for_png(
    *,
    images_db_path: Path,
    ratings_db_path: Path,
    png_path: str,
) -> Dict[str, Any]:
    init_images_db(images_db_path)

    con = sqlite3.connect(ratings_db_path)
    con.row_factory = sqlite3.Row
    try:
        deleted_any = con.execute(
            "SELECT 1 FROM ratings WHERE png_path = ? AND deleted = 1 LIMIT 1",
            (str(png_path),),
        ).fetchone()
        if deleted_any:
            delete_image(images_db_path, png_path=str(png_path))
            return {"deleted": True}

        latest = con.execute(
            "SELECT * FROM ratings WHERE png_path = ? ORDER BY run DESC LIMIT 1",
            (str(png_path),),
        ).fetchone()
        if not latest:
            return {"deleted": False, "updated": False}

        avg_row = con.execute(
            """
            SELECT AVG(rating) AS avg_rating,
                   COUNT(*) AS runs
            FROM ratings
            WHERE png_path = ?
              AND deleted = 0
              AND rating IS NOT NULL
            """,
            (str(png_path),),
        ).fetchone()

        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        row = {
            "png_path": str(png_path),
            "json_path": str(latest["json_path"]),
            "avg_rating": float(avg_row["avg_rating"]) if avg_row["avg_rating"] is not None else None,
            "runs": int(avg_row["runs"] or 0),
            "rating_count": int(latest["rating_count"] or 0),
            "last_run": int(latest["run"] or 0),
            "model_branch": str(latest["model_branch"] or ""),
            "checkpoint": str(latest["checkpoint"] or ""),
            "combo_key": str(latest["combo_key"] or ""),
            "steps": latest["steps"],
            "cfg": latest["cfg"],
            "sampler": latest["sampler"],
            "scheduler": latest["scheduler"],
            "denoise": latest["denoise"],
            "loras_json": str(latest["loras_json"] or "[]"),
            "pos_prompt": str(latest["pos_prompt"] or ""),
            "neg_prompt": str(latest["neg_prompt"] or ""),
            "last_updated": now,
        }
        upsert_image(images_db_path, row)
        return {"deleted": False, "updated": True}
    finally:
        con.close()


def update_after_rating_save(
    *,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    images_db_path: Path,
    combo_db_path: Path,
    playground_db_path: Path,
    json_path: str,
    png_path: str,
    model_branch: str,
    pos_prompt: str,
    neg_prompt: str,
    rating: Optional[int],
    deleted: int,
    max_combos_3: int = 200000,
    rebuild_combos: bool = True,
) -> Dict[str, Any]:
    """Update materialized views after a single rating write.

    Ziel
    - prompt_tokens: Journal pro Run
    - prompt_ratings: MV pro Token (pos|neg), runs-gewichtete Mittel
    - images: MV pro Bild (delete -> komplett raus)
    - combo_prompts: MV pro Kombi (Scores aus prompt_ratings, Bilder aus images)
    """

    run = _max_run_for_json(ratings_db_path, json_path)

    t_res = _update_prompt_tokens_for_run(
        prompt_tokens_db_path=prompt_tokens_db_path,
        json_path=json_path,
        run=run,
        model_branch=model_branch,
        pos_prompt=pos_prompt,
        neg_prompt=neg_prompt,
        rating=rating,
        deleted=deleted,
    )

    pos_tokens = tokenize(pos_prompt or "")
    neg_tokens = tokenize(neg_prompt or "")

    pr_res = _update_prompt_ratings_for_tokens(
        prompt_tokens_db_path=prompt_tokens_db_path,
        prompt_ratings_db_path=prompt_ratings_db_path,
        model_branch=model_branch,
        pos_tokens=pos_tokens,
        neg_tokens=neg_tokens,
    )

    img_res = _update_image_row_for_png(
        images_db_path=images_db_path,
        ratings_db_path=ratings_db_path,
        png_path=png_path,
    )

    # Combo Rebuild: aktuell global, aber im gleichen Request.
    # Wenn das zu langsam wird, ist der naechste Schritt Dirty-Flag + Rebuild beim Playground-Load.
    combo_res = None
    if rebuild_combos:
        combo_res = rebuild_combo_prompts(
            combo_db_path=combo_db_path,
            playground_db_path=playground_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            images_db_path=images_db_path,
            model_branch=str(model_branch or ""),
            max_combos_3=int(max_combos_3),
        )

    return {
        "run": int(run),
        "prompt_tokens": t_res,
        "prompt_ratings": pr_res,
        "images": img_res,
        "combo_prompts": combo_res,
    }
