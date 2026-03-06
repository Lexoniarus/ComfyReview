from __future__ import annotations

"""POST action dispatcher for the Playground Generator."""

from typing import Any, Dict, Optional

from fastapi import Request
from fastapi.responses import RedirectResponse

from routers.playground._shared import (
    GENERATOR_STATE_PATH,
    GENERATOR_PREVIEW_STATE_PATH,
    COMFY_DISCOVERY_CACHE_PATH,
)

from services.playground_generator_ui_service import (
    load_playground_dropdown_items,
    discover_comfy_lists,
    load_head_state,
    save_head_state,
    load_preview_state,
    save_preview_state,
    clear_preview_state,
    build_head_state_from_post,
    remove_draft,
    update_draft,
    generate_preview_drafts,
    submit_preview_drafts,
)

from routers.playground.generator_controller.page_context import build_generator_page_context
from routers.playground.generator_controller.post_parsing import (
    head_kwargs_from_post,
    draft_update_kwargs_from_post,
)


def apply_combo_to_head_state(*, character_id: int, scene_id: int, outfit_id: Optional[str]) -> None:
    """Apply a scene+outfit combo into the generator head state."""

    saved = load_head_state(GENERATOR_STATE_PATH)
    saved["character_id"] = str(int(character_id))
    saved["scene_id"] = str(int(scene_id))

    outfit_id_int: Optional[int] = None
    try:
        s = str(outfit_id or "").strip()
        if s:
            outfit_id_int = int(float(s))
    except Exception:
        outfit_id_int = None

    saved["outfit_id"] = str(int(outfit_id_int)) if outfit_id_int is not None else ""
    save_head_state(GENERATOR_STATE_PATH, saved)


def dispatch_generator_action(
    *,
    request: Request,
    templates: Any,
    default_max_tries: int,
    post: Dict[str, Any],
):
    """Dispatch generator POST actions.

    Returns either a RedirectResponse or a TemplateResponse.
    """

    act = str(post.get("action") or "").lower().strip()
    dropdowns = load_playground_dropdown_items()
    discovery = discover_comfy_lists(cache_path=COMFY_DISCOVERY_CACHE_PATH)
    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    head_kwargs = head_kwargs_from_post(post)

    if act == "draft_remove":
        return _handle_draft_remove(preview, str(post.get("draft_id") or ""))

    if act == "draft_update":
        return _handle_draft_update(preview=preview, head_kwargs=head_kwargs, post=post)

    if act == "head_save":
        return _handle_head_save(head_kwargs)

    if act == "preview_generate":
        return _handle_preview_generate(head_kwargs=head_kwargs, characters=dropdowns["characters"], discovery=discovery)

    if act == "submit_preview":
        return _handle_submit_preview(
            request=request,
            templates=templates,
            default_max_tries=default_max_tries,
            preview=preview or [],
        )

    return _redirect_generator()


def _redirect_generator() -> RedirectResponse:
    return RedirectResponse(url="/playground/generator", status_code=303)


def _handle_draft_remove(preview: list, draft_id: str) -> RedirectResponse:
    updated = remove_draft(preview or [], str(draft_id or ""))
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, updated)
    return _redirect_generator()


def _handle_draft_update(*, preview: list, head_kwargs: dict, post: Dict[str, Any]) -> RedirectResponse:
    args = draft_update_kwargs_from_post(post)
    draft_id = args.pop("draft_id", "")

    if not str(draft_id or "").strip():
        # Same behavior as before: without a draft_id this is effectively a head save.
        return _handle_head_save(head_kwargs)

    updated = update_draft(preview or [], draft_id=draft_id, **args)
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, updated)
    return _redirect_generator()


def _handle_head_save(head_kwargs: dict) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    save_head_state(GENERATOR_STATE_PATH, head)
    return _redirect_generator()


def _handle_preview_generate(*, head_kwargs: dict, characters: list, discovery: Any) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    save_head_state(GENERATOR_STATE_PATH, head)

    drafts = generate_preview_drafts(head=head, characters=characters, discovery=discovery)
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, drafts)
    return _redirect_generator()


def _handle_submit_preview(
    *,
    request: Request,
    templates: Any,
    default_max_tries: int,
    preview: list,
):
    if not preview:
        return _redirect_generator()

    enqueue_info, error = submit_preview_drafts(preview)
    clear_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    # Render fresh page state with head preserved.
    ctx = build_generator_page_context(default_max_tries=default_max_tries)
    ctx["request"] = request
    ctx["error"] = error
    ctx["enqueue"] = enqueue_info
    ctx["preview"] = []

    return templates.TemplateResponse("playground_generator.html", ctx)
