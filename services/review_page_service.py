from __future__ import annotations

import json
from typing import Any

from comfyreview.application import OutputImageCatalog, OutputImageReadModel
from meta_view import extract_prompts, extract_view, preset_text_from_view
from services.context_filters import (
    build_dropdown_lists,
    extract_character_from_subdir,
    matches_character_scope,
    matches_set_filter,
    normalize_model,
    normalize_scope_subdir,
    normalize_set_key,
    normalize_unrated_flag,
)
from services.file_urls import png_path_to_url
from services.playground_label_service import PromptLabels, PromptLabelService


def _filter_items_for_review(
    *,
    items: list[OutputImageReadModel],
    model: str,
    subdir: str,
    set_key: str,
    unrated_only: int,
) -> list[OutputImageReadModel]:
    filtered: list[OutputImageReadModel] = []
    for it in items:
        if model and getattr(it, "model_branch", "") != model:
            continue
        if not matches_character_scope(
            item_subdir=str(getattr(it, "subdir", "") or ""),
            selected_subdir=subdir,
        ):
            continue

        if not matches_set_filter(
            selected_set_key=set_key,
            assigned_set_key=it.assigned_set_key,
            png_path=str(it.png_path),
        ):
            continue

        rated_count = _rated_count(it)
        rated = 1 if rated_count > 0 else 0
        if unrated_only == 1 and rated == 1:
            continue

        filtered.append(it)

    return filtered


def build_review_page_context(
    *,
    output_images: OutputImageCatalog,
    prompt_labels: PromptLabelService,
    unrated: int,
    model: str,
    subdir: str,
    set_key: str,
) -> dict[str, Any]:
    """Build template context for the main review page (/).

    Responsibilities
    - scan filesystem items
    - apply filters (model, subdir, set_key, unrated)
    - select next item
    - resolve labels via the canonical prompt catalog
    - compute rating stats (avg, runs, last_rating, trend)
    """

    unrated_flag = normalize_unrated_flag(unrated)
    model_n = normalize_model(model)
    subdir_n = normalize_scope_subdir(subdir)
    set_key_n = normalize_set_key(set_key)

    items, total, model_list, subdir_list, character_options = (
        _load_review_items(output_images)
    )
    filtered = _filter_items_for_review(
        items=items,
        model=model_n,
        subdir=subdir_n,
        set_key=set_key_n,
        unrated_only=unrated_flag,
    )
    if unrated_flag == 0:
        _sort_items_for_review_all(filtered)
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
    rated_count = _rated_count(it)
    rating_avg = it.average_rating
    rating_runs = it.rating_count
    last_rating = it.current_rating
    trend_delta = None

    view = extract_view(it.meta)
    labels = prompt_labels.resolve(
        str(view.get("pos_prompt") or ""),
        include_lighting=True,
    )

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


def _load_review_items(
    output_images: OutputImageCatalog,
) -> tuple[
    list[OutputImageReadModel],
    int,
    list[str],
    list[str],
    list[dict[str, str]],
]:
    items = [
        item
        for item in output_images.list_images()
        if item.image_uid is not None
    ]
    total = len(items)
    model_list, subdir_list, character_options = build_dropdown_lists(items)
    return items, total, model_list, subdir_list, character_options


def _rated_count(item: OutputImageReadModel) -> int:
    return int(item.rating_count)


def _sort_items_for_review_all(
    items: list[Any],
) -> None:
    items.sort(
        key=lambda item: (
            _rated_count(item),
            str(
                getattr(item, "image_uid", None)
                or getattr(item, "json_path", None)
                or item.png_path
            ),
        )
    )


def _empty_review_context(
    *,
    total: int,
    unrated_flag: int,
    model_n: str,
    subdir_n: str,
    set_key_n: str,
    model_list: list[str],
    subdir_list: list[str],
    character_options: list[dict[str, str]],
) -> dict[str, Any]:
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


def _build_review_context(
    *,
    it: Any,
    total: int,
    unrated_flag: int,
    model_n: str,
    subdir_n: str,
    set_key_n: str,
    model_list: list[str],
    subdir_list: list[str],
    character_options: list[dict[str, str]],
    view: dict[str, Any],
    labels: PromptLabels,
    rated_count: int,
    rating_avg: Any,
    rating_runs: Any,
    trend_delta: Any,
    last_rating: Any,
) -> dict[str, Any]:
    img_url = png_path_to_url(str(it.png_path))
    meta_pre = json.dumps(it.meta, indent=2, ensure_ascii=False)

    character_name = extract_character_from_subdir(
        str(getattr(it, "subdir", "") or "")
    )
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
        "scene_name": labels.scene_name,
        "outfit_name": labels.outfit_name,
        "pose_name": labels.pose_name,
        "expression_name": labels.expression_name,
        "modifiers": list(labels.modifiers),
        "light_name": labels.light_name,
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
