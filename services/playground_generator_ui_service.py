"""Playground Generator UI service.

This module is a compatibility facade.

Historically, the generator router imported a long list of helpers from here.
For 0.0.5b we keep that public surface stable while splitting the
implementation into smaller, focused modules under services.playground_generator_ui.
"""

from __future__ import annotations

from services.playground_generator_ui.types import DiscoveryLists
from services.playground_generator_ui.state import (
    load_head_state,
    save_head_state,
    load_preview_state,
    save_preview_state,
    clear_preview_state,
)
from services.playground_generator_ui.dropdowns import load_playground_dropdown_items
from services.playground_generator_ui.discovery import discover_comfy_lists
from services.playground_generator_ui.head_form import (
    workflow_render_defaults,
    character_name_from_id,
    build_form_from_state,
    build_head_state_from_post,
)
from services.playground_generator_ui.drafts import remove_draft, update_draft
from services.playground_generator_ui.best_pictures import enrich_preview_with_best_pictures
from services.playground_generator_ui.generation import generate_preview_drafts, parse_sequence
from services.playground_generator_ui.submit import submit_preview_drafts

__all__ = [
    "DiscoveryLists",
    "load_head_state",
    "save_head_state",
    "load_preview_state",
    "save_preview_state",
    "clear_preview_state",
    "load_playground_dropdown_items",
    "discover_comfy_lists",
    "workflow_render_defaults",
    "character_name_from_id",
    "build_form_from_state",
    "build_head_state_from_post",
    "remove_draft",
    "update_draft",
    "enrich_preview_with_best_pictures",
    "generate_preview_drafts",
    "parse_sequence",
    "submit_preview_drafts",
]
