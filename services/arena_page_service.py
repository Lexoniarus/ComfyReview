from __future__ import annotations

from pathlib import Path
from typing import Any

from comfyreview.application import (
    ArenaQuery,
    ArenaService,
    RankingQuery,
    RankingService,
)
from services.context_filters import (
    GalleryContext,
    build_dropdown_lists,
    normalize_model,
)
from services.gallery_view_service import build_arena_side
from services.playground_label_service import get_playground_label_matcher


def build_arena_page_context(
    *,
    ranking_service: RankingService,
    arena_service: ArenaService,
    playground_db_path: Path,
    context: GalleryContext,
    min_runs: int,
    pool_limit: int,
) -> dict[str, Any]:
    """Build canonical template context for the Arena page."""
    inventory = ranking_service.list_images(
        RankingQuery(minimum_ratings=0, limit=1_000_000)
    )
    model_list, subdir_list, character_options = build_dropdown_lists(
        inventory
    )
    model = normalize_model(context.model)
    query = RankingQuery(
        model=model,
        subdir=context.subdir,
        set_key=context.set_key,
        mode=context.mode,
        minimum_ratings=min_runs,
        limit=pool_limit,
    )
    candidates = ranking_service.list_images(query)
    pair = arena_service.next_pair(ArenaQuery(query))
    base = {
        "model": model,
        "subdir": context.subdir,
        "model_list": model_list,
        "subdir_list": subdir_list,
        "mode": context.mode,
        "character_options": character_options,
        "set_key": context.set_key,
    }
    if len(candidates) < 2:
        return {
            **base,
            "left": None,
            "right": None,
            "message": (
                "Nicht genug Kandidaten. Du brauchst mindestens 2 Bilder "
                f"mit je mindestens {int(min_runs)} Bewertungen."
            ),
        }
    if pair is None:
        return {
            **base,
            "left": None,
            "right": None,
            "message": "Keine neuen Paarungen mehr offen für diesen Pool.",
        }

    matcher = get_playground_label_matcher(playground_db_path)
    return {
        **base,
        "left": build_arena_side(pair.left, matcher),
        "right": build_arena_side(pair.right, matcher),
        "message": "",
    }
