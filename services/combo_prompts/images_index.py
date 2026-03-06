from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Set

from config import DB_PATH, MIN_RUNS

from stores.images_store import init_images_db
from stores.ratings_state_store import fetch_latest_deleted_by_png_paths

from .token_utils import dedup_keep_order, norm_token_keep_case, split_tokens_csv_keep_case


def build_images_token_index(*, images_db_path: Path, model_branch: str = "") -> Dict[str, Any]:
    """Build an in memory token index from images.sqlite3.

    Index
    pos_index[token] -> set(png_path)
    neg_index[token] -> set(png_path)
    images_by_png[png_path] -> image row

    Filters
    deleted latest state must be 0
    png and json must exist
    avg_rating not null
    runs >= MIN_RUNS
    """

    init_images_db(images_db_path)

    con = sqlite3.connect(images_db_path)
    con.row_factory = sqlite3.Row
    try:
        sql = """
            SELECT png_path, json_path, avg_rating, runs, pos_prompt, neg_prompt, model_branch
            FROM images
        """
        args: List[Any] = []
        if model_branch:
            sql += " WHERE model_branch = ?"
            args.append(str(model_branch))

        rows = con.execute(sql, args).fetchall()

        deleted_map = fetch_latest_deleted_by_png_paths(
            DB_PATH,
            [str(rr["png_path"] or "") for rr in rows],
            model_branch=str(model_branch or ""),
        )

        pos_index: Dict[str, Set[str]] = {}
        neg_index: Dict[str, Set[str]] = {}
        images_by_png: Dict[str, Dict[str, Any]] = {}

        for r in rows:
            png = str(r["png_path"] or "").strip()
            if not png:
                continue

            if int(deleted_map.get(png, 0) or 0) == 1:
                continue

            try:
                if not Path(png).exists():
                    continue
            except Exception:
                continue

            img = {
                "png_path": png,
                "json_path": str(r["json_path"] or ""),
                "avg_rating": r["avg_rating"],
                "runs": int(r["runs"] or 0),
                "pos_prompt": str(r["pos_prompt"] or ""),
                "neg_prompt": str(r["neg_prompt"] or ""),
                "model_branch": str(r["model_branch"] or ""),
            }

            if img["avg_rating"] is None:
                continue
            if int(img.get("runs") or 0) < int(MIN_RUNS):
                continue

            jp = str(img.get("json_path") or "").strip()
            if jp:
                try:
                    if not Path(jp).exists():
                        continue
                except Exception:
                    continue

            images_by_png[png] = img

            pos_tokens = dedup_keep_order(split_tokens_csv_keep_case(img["pos_prompt"]))
            neg_tokens = dedup_keep_order(split_tokens_csv_keep_case(img["neg_prompt"]))

            for t in pos_tokens:
                pos_index.setdefault(t, set()).add(png)
            for t in neg_tokens:
                neg_index.setdefault(t, set()).add(png)

        return {
            "pos_index": pos_index,
            "neg_index": neg_index,
            "images_by_png": images_by_png,
            "image_count": int(len(images_by_png)),
        }
    finally:
        con.close()


def match_pngs_for_combo(
    *,
    pos_index: Dict[str, Set[str]],
    neg_index: Dict[str, Set[str]],
    pos_tokens: List[str],
    neg_tokens: List[str],
) -> Set[str]:
    """Hard match on image level."""

    pos_tokens = dedup_keep_order([norm_token_keep_case(t) for t in (pos_tokens or []) if norm_token_keep_case(t)])
    neg_tokens = dedup_keep_order([norm_token_keep_case(t) for t in (neg_tokens or []) if norm_token_keep_case(t)])

    if not pos_tokens:
        return set()

    sets: List[Set[str]] = []
    for t in pos_tokens:
        s = pos_index.get(t)
        if not s:
            return set()
        sets.append(s)

    sets.sort(key=len)
    matched = set(sets[0])
    for s in sets[1:]:
        matched.intersection_update(s)
        if not matched:
            return set()

    if neg_tokens:
        nsets: List[Set[str]] = []
        for t in neg_tokens:
            s = neg_index.get(t)
            if not s:
                return set()
            nsets.append(s)

        nsets.sort(key=len)
        for s in nsets:
            matched.intersection_update(s)
            if not matched:
                return set()

    return matched


def combo_images_for_tokens(
    *,
    pos_index: Dict[str, Set[str]],
    neg_index: Dict[str, Set[str]],
    images_by_png: Dict[str, Dict[str, Any]],
    pos_tokens: List[str],
    neg_tokens: List[str],
) -> Dict[str, Any]:
    """Compute combo image metrics and best images using the in memory image index."""

    matched = match_pngs_for_combo(
        pos_index=pos_index,
        neg_index=neg_index,
        pos_tokens=pos_tokens,
        neg_tokens=neg_tokens,
    )

    rows: List[Dict[str, Any]] = []
    for png in matched:
        img = images_by_png.get(png)
        if img:
            rows.append(img)

    total_runs = sum(int(r.get("runs") or 0) for r in rows)
    combo_avg = (
        sum(float(r.get("avg_rating") or 0.0) * float(int(r.get("runs") or 0)) for r in rows) / float(total_runs)
        if total_runs > 0
        else None
    )

    rows.sort(key=lambda x: (float(x.get("avg_rating") or -1.0), int(x.get("runs") or 0)), reverse=True)
    best3 = rows[:3]

    return {
        "combo_avg_rating": combo_avg,
        "combo_total_runs": int(total_runs),
        "combo_image_count": int(len(rows)),
        "best3": best3,
    }
