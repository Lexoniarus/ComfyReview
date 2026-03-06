from __future__ import annotations

"""Build template context for the Playground Generator page."""

from typing import Any, Dict

from routers.playground._shared import (
    GENERATOR_STATE_PATH,
    GENERATOR_PREVIEW_STATE_PATH,
    COMFY_DISCOVERY_CACHE_PATH,
)

from services.ui_state_service import safe_int
from services.playground_generator_ui_service import (
    load_playground_dropdown_items,
    discover_comfy_lists,
    load_head_state,
    load_preview_state,
    character_name_from_id,
    workflow_render_defaults,
    build_form_from_state,
)


def build_generator_page_context(*, default_max_tries: int) -> Dict[str, Any]:
    """Return a dict suitable for rendering ``playground_generator.html``.

    Note: this function intentionally does **not** resolve best pictures.
    Best picture matching is loaded lazily per draft.
    """

    dropdowns = load_playground_dropdown_items()
    discovery = discover_comfy_lists(cache_path=COMFY_DISCOVERY_CACHE_PATH)

    saved = load_head_state(GENERATOR_STATE_PATH)
    saved_char_id = safe_int(str(saved.get("character_id", "")).strip()) if saved else None
    char_name = character_name_from_id(dropdowns["characters"], saved_char_id)
    defaults = workflow_render_defaults(character_name=char_name, character_id=saved_char_id)
    form = build_form_from_state(saved=saved, defaults=defaults)

    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    return {
        "default_max_tries": default_max_tries,
        "form": form,
        "error": None,
        "enqueue": None,
        "characters": dropdowns["characters"],
        "scenes": dropdowns["scenes"],
        "outfits": dropdowns["outfits"],
        "poses": dropdowns["poses"],
        "expressions": dropdowns["expressions"],
        "lightings": dropdowns["lightings"],
        "modifiers": dropdowns["modifiers"],
        "checkpoints": discovery.checkpoints,
        "samplers": discovery.samplers,
        "schedulers": discovery.schedulers,
        "preview": preview,
    }
