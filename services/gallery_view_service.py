from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from meta_view import extract_view
from scanner import scan_output

from services.context_filters import (
    GalleryContext,
    build_dropdown_lists,
    extract_character_from_subdir,
    normalize_model,
)
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


def _card_from_scored_item(scored_item: Any, matcher: Any) -> Dict[str, Any]:
    it = scored_item.it
    view = extract_view(it.meta)
    labels = matcher.resolve(str(scored_item.pos_prompt or ""), include_lighting=True)

    return {
        "img_url": f"/files/{it.subdir}/{it.png_path.name}",
        "json_path": str(it.json_path),
        "png_path": str(it.png_path),
        "model_branch": str(getattr(it, "model_branch", "") or ""),
        "checkpoint": str(getattr(it, "checkpoint", "") or ""),
        "avg": float(scored_item.avg),
        "runs": int(scored_item.runs),
        "sampler": view.get("sampler"),
        "scheduler": view.get("scheduler"),
        "steps": view.get("steps"),
        "cfg": view.get("cfg"),
        "denoise": view.get("denoise"),
        "combo_key": str(getattr(it, "combo_key", "") or ""),
        "subdir": str(getattr(it, "subdir", "") or ""),
        "character_name": extract_character_from_subdir(str(getattr(it, "subdir", "") or "")),
        "scene_name": str(labels.get("scene_name") or ""),
        "outfit_name": str(labels.get("outfit_name") or ""),
        "pose_name": str(labels.get("pose_name") or ""),
        "expression_name": str(labels.get("expression_name") or ""),
        "modifiers": list(labels.get("modifiers") or []),
        "light_name": str(labels.get("light_name") or ""),
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

    ranked, _ = build_ranked_pool(
        items,
        mode=context.mode,
        set_key=context.set_key,
        subdir=context.subdir,
        min_runs=min_runs,
        limit=limit,
    )

    matcher = get_playground_label_matcher(playground_db_path)
    cards = [_card_from_scored_item(si, matcher) for si in ranked]

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
    labels = matcher.resolve(str(view.get("pos_prompt") or ""), include_lighting=True)

    return {
        "img_url": f"/files/{it.subdir}/{it.png_path.name}",
        "json_path": str(it.json_path),
        "model_branch": str(getattr(it, "model_branch", "") or ""),
        "checkpoint": str(getattr(it, "checkpoint", "") or ""),
        "avg": float(avg),
        "runs": int(runs),
        "view": view,
        "character_name": extract_character_from_subdir(str(getattr(it, "subdir", "") or "")),
        "scene_name": str(labels.get("scene_name") or ""),
        "outfit_name": str(labels.get("outfit_name") or ""),
        "pose_name": str(labels.get("pose_name") or ""),
        "expression_name": str(labels.get("expression_name") or ""),
        "modifiers": list(labels.get("modifiers") or []),
        "light_name": str(labels.get("light_name") or ""),
    }


def safe_json_dumps(value: Any, *, default: str = "[]") -> str:
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return default
