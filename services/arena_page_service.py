from __future__ import annotations

from typing import Any, Dict, List, Tuple

from arena_store import ensure_schema as ensure_arena_schema
from scanner import scan_output

from services.arena_service import pick_arena_pair
from services.context_filters import GalleryContext, build_dropdown_lists, normalize_model
from services.gallery_view_service import build_arena_side
from services.pool_service import build_ranked_pool
from services.playground_label_service import get_playground_label_matcher


def build_arena_page_context(
    *,
    arena_db_path,
    output_root,
    playground_db_path,
    context: GalleryContext,
    min_runs: int,
    pool_limit: int,
) -> Dict[str, Any]:
    """Build template context for /arena.

    Responsibilities
    - ensure arena schema
    - scan filesystem items
    - build dropdown lists
    - filter by model
    - build ranked pool according to vNext rules
    - pick next arena pair
    - resolve labels
    """

    ensure_arena_schema(arena_db_path)

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
        limit=pool_limit,
    )

    scored = [(x.it, x.avg, x.runs) for x in ranked]

    if len(scored) < 2:
        return {
            "left": None,
            "right": None,
            "message": f"Nicht genug Kandidaten. Du brauchst mindestens 2 Bilder mit je mindestens {int(min_runs)} Bewertungen.",
            "model": model,
            "subdir": context.subdir,
            "model_list": model_list,
            "subdir_list": subdir_list,
            "mode": context.mode,
            "character_options": character_options,
            "set_key": context.set_key,
        }

    left_it, right_it, left_avg, right_avg, left_runs, right_runs = pick_arena_pair(items, scored)

    if left_it is None or right_it is None:
        return {
            "left": None,
            "right": None,
            "message": "Keine neuen Paarungen mehr offen für diesen Pool.",
            "model": model,
            "subdir": context.subdir,
            "model_list": model_list,
            "subdir_list": subdir_list,
            "mode": context.mode,
            "character_options": character_options,
            "set_key": context.set_key,
        }

    matcher = get_playground_label_matcher(playground_db_path)

    return {
        "left": build_arena_side(it=left_it, avg=float(left_avg), runs=int(left_runs), matcher=matcher),
        "right": build_arena_side(it=right_it, avg=float(right_avg), runs=int(right_runs), matcher=matcher),
        "message": "",
        "model": model,
        "subdir": context.subdir,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "mode": context.mode,
        "character_options": character_options,
        "set_key": context.set_key,
    }
