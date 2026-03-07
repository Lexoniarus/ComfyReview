from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from db_store import db, get_rated_map
from meta_view import extract_prompts, extract_view, preset_text_from_view
from scanner import scan_output

from services.context_filters import (
    build_dropdown_lists,
    extract_character_from_subdir,
    matches_character_scope,
    matches_set_filter,
    normalize_model,
    normalize_set_key,
    normalize_scope_subdir,
    normalize_unrated_flag,
)
from services.file_urls import png_path_to_url
from services.playground_label_service import get_playground_label_matcher
from services.rating_service import rating_avg_and_runs_for_json
from stores.curation_store import fetch_set_map


def _filter_items_for_review(
    *,
    items: List[Any],
    rated_map: Dict[str, int],
    set_map: Dict[str, Optional[str]],
    model: str,
    subdir: str,
    set_key: str,
    unrated_only: int,
) -> List[Any]:
    filtered: List[Any] = []
    for it in items:
        if model and getattr(it, "model_branch", "") != model:
            continue
        if not matches_character_scope(item_subdir=str(getattr(it, "subdir", "") or ""), selected_subdir=subdir):
            continue

        assigned = set_map.get(str(it.png_path))
        if not matches_set_filter(
            selected_set_key=set_key,
            assigned_set_key=assigned,
            png_path=str(it.png_path),
        ):
            continue

        rated_count = int(rated_map.get(str(it.json_path), 0) or 0)
        rated = 1 if rated_count > 0 else 0
        if unrated_only == 1 and rated == 1:
            continue

        filtered.append(it)

    return filtered


def build_review_page_context(
    *,
    output_root: Path,
    ratings_db_path: Path,
    playground_db_path: Path,
    curation_db_path: Path,
    unrated: int,
    model: str,
    subdir: str,
    set_key: str,
) -> Dict[str, Any]:
    """Build template context for the main review page (/).

    Responsibilities
    - scan filesystem items
    - apply filters (model, subdir, set_key, unrated)
    - select next item
    - resolve labels via playground DB
    - compute rating stats (avg, runs, last_rating, trend)
    """

    unrated_flag = normalize_unrated_flag(unrated)
    model_n = normalize_model(model)
    subdir_n = normalize_scope_subdir(subdir)
    set_key_n = normalize_set_key(set_key)

    items, total, model_list, subdir_list, character_options = _load_review_items(output_root)
    set_map = _load_set_map_safe(curation_db_path, items)

    con = db(ratings_db_path)
    try:
        rated_map = get_rated_map(con)
        filtered = _filter_items_for_review(
            items=items,
            rated_map=rated_map,
            set_map=set_map,
            model=model_n,
            subdir=subdir_n,
            set_key=set_key_n,
            unrated_only=unrated_flag,
        )

        if unrated_flag == 0:
            _sort_items_for_review_all(filtered, rated_map)

        if not filtered:
            return _empty_review_context(
                total=total,
                unrated_flag=unrated_flag,
                model_n=model_n,
                subdir_n=subdir_n,
                set_key_n=set_key_n,
                model_list=model_list,
                subdir_list=subdir_list,
                character_options=character_options,
            )

        it = filtered[0]
        rated_count = int(rated_map.get(str(it.json_path), 0) or 0)

        rating_avg, rating_runs = rating_avg_and_runs_for_json(con, str(it.json_path))
        last_rating, trend_delta = _fetch_last_and_trend(con, str(it.json_path), int(rating_runs or 0))
    finally:
        con.close()

    view = extract_view(it.meta)
    labels = _resolve_labels(playground_db_path, str(view.get("pos_prompt") or ""))

    return _build_review_context(
        it=it,
        total=total,
        unrated_flag=unrated_flag,
        model_n=model_n,
        subdir_n=subdir_n,
        set_key_n=set_key_n,
        model_list=model_list,
        subdir_list=subdir_list,
        character_options=character_options,
        view=view,
        labels=labels,
        rated_count=rated_count,
        rating_avg=rating_avg,
        rating_runs=rating_runs,
        trend_delta=trend_delta,
        last_rating=last_rating,
    )


def _load_review_items(output_root: Path):
    items = scan_output(output_root)
    total = len(items)
    model_list, subdir_list, character_options = build_dropdown_lists(items)
    return items, total, model_list, subdir_list, character_options


def _load_set_map_safe(curation_db_path: Path, items: List[Any]) -> Dict[str, Optional[str]]:
    try:
        return fetch_set_map(curation_db_path, [str(it.png_path) for it in items])
    except Exception:
        return {}


def _sort_items_for_review_all(items: List[Any], rated_map: Dict[str, int]) -> None:
    items.sort(
        key=lambda it2: (
            int(rated_map.get(str(it2.json_path), 0) or 0),
            str(it2.json_path),
        )
    )


def _empty_review_context(
    *,
    total: int,
    unrated_flag: int,
    model_n: str,
    subdir_n: str,
    set_key_n: str,
    model_list: List[str],
    subdir_list: List[str],
    character_options: List[Dict[str, str]],
) -> Dict[str, Any]:
    return {
        "total": total,
        "idx": 0,
        "status": "all",
        "unrated": unrated_flag,
        "model": model_n,
        "subdir": subdir_n,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "character_options": character_options,
        "set_key": set_key_n,
        "it": None,
        "img_url": "",
        "meta_pre": "",
        "view": {},
        "scene_name": "",
        "outfit_name": "",
        "pose_name": "",
        "expression_name": "",
        "modifiers": [],
        "light_name": "",
        "character_name": "",
        "preset_text": "",
        "prompt_hint": "",
        "loras_json": "[]",
        "rated_count": 0,
        "rating_avg": None,
        "rating_runs": 0,
        "trend_delta": None,
        "last_rating": None,
    }


def _fetch_last_and_trend(con, json_path: str, rating_runs: int):
    last_row = con.execute(
        """
        SELECT rating
        FROM ratings
        WHERE json_path = ?
          AND rating IS NOT NULL
          AND (deleted IS NULL OR deleted = 0)
        ORDER BY run DESC
        LIMIT 1
        """,
        (json_path,),
    ).fetchone()

    last_rating = int(last_row[0]) if last_row and last_row[0] is not None else None

    trend_delta = None
    if rating_runs >= 2:
        prev_row = con.execute(
            """
            SELECT rating
            FROM ratings
            WHERE json_path = ?
              AND rating IS NOT NULL
              AND (deleted IS NULL OR deleted = 0)
            ORDER BY run DESC
            LIMIT 1 OFFSET 1
            """,
            (json_path,),
        ).fetchone()

        prev_rating = int(prev_row[0]) if prev_row and prev_row[0] is not None else None
        if prev_rating is not None and last_rating is not None:
            trend_delta = int(last_rating) - int(prev_rating)

    return last_rating, trend_delta


def _resolve_labels(playground_db_path: Path, pos_prompt: str) -> Dict[str, Any]:
    matcher = get_playground_label_matcher(playground_db_path)
    return matcher.resolve(str(pos_prompt or ""), include_lighting=True)


def _build_review_context(
    *,
    it: Any,
    total: int,
    unrated_flag: int,
    model_n: str,
    subdir_n: str,
    set_key_n: str,
    model_list: List[str],
    subdir_list: List[str],
    character_options: List[Dict[str, str]],
    view: Dict[str, Any],
    labels: Dict[str, Any],
    rated_count: int,
    rating_avg: Any,
    rating_runs: Any,
    trend_delta: Any,
    last_rating: Any,
) -> Dict[str, Any]:
    img_url = png_path_to_url(str(it.png_path))
    meta_pre = json.dumps(it.meta, indent=2, ensure_ascii=False)

    character_name = extract_character_from_subdir(str(getattr(it, "subdir", "") or ""))
    preset_text = preset_text_from_view(view)
    _, _, prompt_hint = extract_prompts(it.meta)

    try:
        loras_json = json.dumps(view.get("loras", []), ensure_ascii=False)
    except Exception:
        loras_json = "[]"

    return {
        "total": total,
        "idx": 0,
        "status": "unrated" if unrated_flag == 1 else "all",
        "unrated": unrated_flag,
        "model": model_n,
        "subdir": subdir_n,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "character_options": character_options,
        "set_key": set_key_n,
        "it": it,
        "img_url": img_url,
        "meta_pre": meta_pre,
        "view": view,
        "scene_name": str(labels.get("scene_name") or ""),
        "outfit_name": str(labels.get("outfit_name") or ""),
        "pose_name": str(labels.get("pose_name") or ""),
        "expression_name": str(labels.get("expression_name") or ""),
        "modifiers": list(labels.get("modifiers") or []),
        "light_name": str(labels.get("light_name") or ""),
        "character_name": character_name,
        "preset_text": preset_text,
        "prompt_hint": prompt_hint,
        "loras_json": loras_json,
        "rated_count": rated_count,
        "rating_avg": rating_avg,
        "rating_runs": rating_runs,
        "trend_delta": trend_delta,
        "last_rating": last_rating,
    }
