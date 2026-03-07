from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from meta_view import extract_view
from scanner import scan_output

from services.context_filters import (
    GalleryContext,
    build_dropdown_lists,
    extract_character_from_subdir,
    normalize_model,
    resolve_assigned_set_key,
)
from services.file_urls import png_path_to_url
from services.playground_label_service import get_playground_label_matcher
from services.pool_service import build_ranked_pool


@dataclass(frozen=True)
class RankedCard:
    img_url: str
    json_path: str
    png_path: str
    model_branch: str
    checkpoint: str
    avg: float
    runs: int
    sampler: str
    scheduler: str
    steps: Any
    cfg: Any
    denoise: Any
    combo_key: str
    subdir: str
    character_name: str
    scene_name: str
    outfit_name: str
    pose_name: str
    expression_name: str
    modifiers: List[str]
    light_name: str
    assigned_set_key: str


def _resolve_card_labels(*, matcher: Any, prompt_text: str) -> Dict[str, Any]:
    return matcher.resolve(str(prompt_text or ""), include_lighting=True)


def _build_labeled_image_fields(*, it: Any, labels: Dict[str, Any]) -> Dict[str, Any]:
    subdir = str(getattr(it, "subdir", "") or "")
    return {
        "img_url": png_path_to_url(str(it.png_path)),
        "json_path": str(it.json_path),
        "png_path": str(it.png_path),
        "model_branch": str(getattr(it, "model_branch", "") or ""),
        "checkpoint": str(getattr(it, "checkpoint", "") or ""),
        "subdir": subdir,
        "character_name": extract_character_from_subdir(subdir),
        "scene_name": str(labels.get("scene_name") or ""),
        "outfit_name": str(labels.get("outfit_name") or ""),
        "pose_name": str(labels.get("pose_name") or ""),
        "expression_name": str(labels.get("expression_name") or ""),
        "modifiers": list(labels.get("modifiers") or []),
        "light_name": str(labels.get("light_name") or ""),
    }


def _card_from_scored_item(scored_item: Any, matcher: Any, *, assigned_set_key: Optional[str]) -> Dict[str, Any]:
    it = scored_item.it
    view = extract_view(it.meta)
    labels = _resolve_card_labels(matcher=matcher, prompt_text=str(scored_item.pos_prompt or ""))

    return {
        **_build_labeled_image_fields(it=it, labels=labels),
        "avg": float(scored_item.avg),
        "runs": int(scored_item.runs),
        "sampler": view.get("sampler"),
        "scheduler": view.get("scheduler"),
        "steps": view.get("steps"),
        "cfg": view.get("cfg"),
        "denoise": view.get("denoise"),
        "combo_key": str(getattr(it, "combo_key", "") or ""),
        "assigned_set_key": str(
            resolve_assigned_set_key(
                png_path=str(it.png_path),
                assigned_set_key=assigned_set_key,
            )
            or "unsorted"
        ),
    }


def build_top_pictures_page(
    *,
    output_root,
    playground_db_path,
    context: GalleryContext,
    min_runs: int,
    limit: int,
) -> Dict[str, Any]:
    """Build view data for Top/Worst ranked gallery page."""

    items_all = scan_output(output_root)
    model_list, subdir_list, character_options = build_dropdown_lists(items_all)

    items = items_all
    model = normalize_model(context.model)
    if model:
        items = [it for it in items if getattr(it, "model_branch", "") == model]

    ranked, curation_map = build_ranked_pool(
        items,
        mode=context.mode,
        set_key=context.set_key,
        subdir=context.subdir,
        min_runs=min_runs,
        limit=limit,
    )

    matcher = get_playground_label_matcher(playground_db_path)
    cards = [
        _card_from_scored_item(
            si,
            matcher,
            assigned_set_key=curation_map.get(str(si.it.png_path)),
        )
        for si in ranked
    ]

    return {
        "cards": cards,
        "model": model,
        "subdir": context.subdir,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "mode": context.mode,
        "character_options": character_options,
        "set_key": context.set_key,
    }


def build_arena_side(*, it: Any, avg: float, runs: int, matcher: Any) -> Dict[str, Any]:
    view = extract_view(it.meta)
    labels = _resolve_card_labels(matcher=matcher, prompt_text=str(view.get("pos_prompt") or ""))

    return {
        **_build_labeled_image_fields(it=it, labels=labels),
        "avg": float(avg),
        "runs": int(runs),
        "view": view,
    }


def safe_json_dumps(value: Any, *, default: str = "[]") -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return default
