# routers/playground/generator.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from comfyreview.api.dependencies import get_application_container
from comfyreview.application import PlaygroundService
from config import (
    DEFAULT_MAX_TRIES,
)
from services.file_urls import file_url_exists, png_path_to_url
from services.playground_generator_ui_service import (
    build_form_from_state,
    build_head_state_from_post,
    character_name_from_id,
    clear_preview_state,
    generate_preview_drafts,
    load_head_state,
    load_playground_dropdown_items,
    load_preview_state,
    remove_draft,
    save_head_state,
    save_preview_state,
    submit_preview_drafts,
    update_draft,
    workflow_render_defaults,
)
from services.ui_state_service import safe_int

from ._shared import (
    GENERATOR_PREVIEW_STATE_PATH,
    GENERATOR_STATE_PATH,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/playground/generator/apply_combo")
def playground_generator_apply_combo(
    character_id: int = Form(...),
    scene_id: int = Form(...),
    outfit_id: str | None = Form(None),
) -> RedirectResponse:
    saved = load_head_state(GENERATOR_STATE_PATH)

    saved["character_id"] = str(int(character_id))
    saved["scene_id"] = str(int(scene_id))

    outfit_id_int: int | None = None
    try:
        s = str(outfit_id or "").strip()
        if s:
            outfit_id_int = int(float(s))
    except Exception:
        outfit_id_int = None

    saved["outfit_id"] = (
        str(int(outfit_id_int)) if outfit_id_int is not None else ""
    )

    save_head_state(GENERATOR_STATE_PATH, saved)
    return RedirectResponse(url="/playground/generator", status_code=303)


@router.get("/playground/generator")
def playground_generator_page(request: Request):
    dropdowns = load_playground_dropdown_items()

    discovery = get_application_container(
        request
    ).playground_discovery.discover()

    saved = load_head_state(GENERATOR_STATE_PATH)
    saved_char_id = (
        safe_int(str(saved.get("character_id", "")).strip()) if saved else None
    )

    char_name_for_defaults = character_name_from_id(
        dropdowns["characters"], saved_char_id
    )
    defaults = workflow_render_defaults(
        character_name=char_name_for_defaults, character_id=saved_char_id
    )

    form = build_form_from_state(saved=saved, defaults=defaults)

    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH)
    for draft in preview:
        if draft.get("best_img_url") and not file_url_exists(
            str(draft.get("best_img_url"))
        ):
            draft["best_img_url"] = ""
            draft["best_avg"] = None
            draft["best_runs"] = None
            draft["best_hits"] = None

    return templates.TemplateResponse(
        request=request,
        name="playground_generator.html",
        context={
            "request": request,
            "default_max_tries": DEFAULT_MAX_TRIES,
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
        },
    )


@router.get("/playground/generator/preview_draft_best")
def playground_generator_preview_draft_best(draft_id: str):
    """Lazy load per-draft best picture info.

    The generator page must render fast. Best picture matching can be slow because it hits
    prompt_tokens and ratings/images indices. This endpoint resolves one draft at a time.
    """
    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH) or []
    draft_id_s = str(draft_id or "").strip()
    if not draft_id_s:
        return JSONResponse(
            {"status": "error", "error": "missing draft_id"}, status_code=400
        )

    d = None
    for x in preview:
        if str((x or {}).get("draft_id") or "").strip() == draft_id_s:
            d = x
            break

    if d is None:
        return JSONResponse(
            {"status": "error", "error": "draft not found"}, status_code=404
        )

    # fast path if already resolved
    if file_url_exists(str((d or {}).get("best_img_url") or "")):
        return JSONResponse(
            {
                "status": "ok",
                "best_img_url": d.get("best_img_url") or "",
                "best_avg": d.get("best_avg"),
                "best_runs": d.get("best_runs"),
                "best_hits": d.get("best_hits"),
                "retry": False,
            }
        )

    from services.playground_generator_ui.best_pictures import (
        resolve_best_picture_for_draft,
    )

    res = resolve_best_picture_for_draft(d, png_to_url=png_path_to_url)

    # Persist into preview state if we got a definitive answer.
    if res.get("status") == "ok" and res.get("best_img_url"):
        for x in preview:
            if str((x or {}).get("draft_id") or "").strip() == draft_id_s:
                x["best_img_url"] = res.get("best_img_url") or ""
                x["best_avg"] = res.get("best_avg")
                x["best_runs"] = res.get("best_runs")
                x["best_hits"] = res.get("best_hits")
                break
        try:
            save_preview_state(GENERATOR_PREVIEW_STATE_PATH, preview)
        except Exception:
            pass

    return JSONResponse(res)


@router.post("/playground/generator")
def playground_generator_run(
    request: Request,
    action: str = Form("preview_generate"),
    character_id: int | None = Form(None),
    scene_id: int | None = Form(None),
    outfit_id: int | None = Form(None),
    pose_id: int | None = Form(None),
    expression_id: int | None = Form(None),
    lighting_id: int | None = Form(None),
    modifier_id: int | None = Form(None),
    include_lighting: int | None = Form(None),
    include_modifier: int | None = Form(None),
    gen_seed: str | None = Form(None),
    comfy_seed: str | None = Form(None),
    max_tries: int = Form(DEFAULT_MAX_TRIES),
    batch_runs: int | None = Form(None),
    checkpoint_name: str | None = Form(None),
    sampler_name: str | None = Form(None),
    scheduler_name: str | None = Form(None),
    steps_min: str | None = Form(None),
    steps_max: str | None = Form(None),
    cfg_min: str | None = Form(None),
    cfg_max: str | None = Form(None),
    cfg_step: str | None = Form(None),
    steps: str | None = Form(None),
    cfg: str | None = Form(None),
    denoise: str | None = Form(None),
    draft_id: str | None = Form(None),
    draft_seed: str | None = Form(None),
    draft_steps: str | None = Form(None),
    draft_cfg: str | None = Form(None),
    draft_sampler: str | None = Form(None),
    draft_scheduler: str | None = Form(None),
    draft_denoise: str | None = Form(None),
    draft_checkpoint: str | None = Form(None),
    draft_pos: str | None = Form(None),
    draft_neg: str | None = Form(None),
):
    act = str(action or "").lower().strip()
    dropdowns = load_playground_dropdown_items()
    discovery = get_application_container(
        request
    ).playground_discovery.discover()
    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    head_kwargs = _head_kwargs_from_post(
        character_id=character_id,
        scene_id=scene_id,
        outfit_id=outfit_id,
        pose_id=pose_id,
        expression_id=expression_id,
        lighting_id=lighting_id,
        modifier_id=modifier_id,
        include_lighting=include_lighting,
        include_modifier=include_modifier,
        gen_seed=gen_seed,
        comfy_seed=comfy_seed,
        max_tries=max_tries,
        batch_runs=batch_runs,
        checkpoint_name=checkpoint_name,
        sampler_name=sampler_name,
        scheduler_name=scheduler_name,
        steps_min=steps_min,
        steps_max=steps_max,
        cfg_min=cfg_min,
        cfg_max=cfg_max,
        cfg_step=cfg_step,
        steps=steps,
        cfg=cfg,
        denoise=denoise,
    )

    if act == "draft_remove":
        return _handle_draft_remove(preview, str(draft_id or ""))

    if act == "draft_update":
        return _handle_draft_update(
            preview=preview,
            draft_id=str(draft_id or "").strip(),
            head_kwargs=head_kwargs,
            draft_seed=draft_seed,
            draft_steps=draft_steps,
            draft_cfg=draft_cfg,
            draft_sampler=draft_sampler,
            draft_scheduler=draft_scheduler,
            draft_denoise=draft_denoise,
            draft_checkpoint=draft_checkpoint,
            draft_pos=draft_pos,
            draft_neg=draft_neg,
        )

    if act == "head_save":
        return _handle_head_save(head_kwargs)

    if act == "preview_generate":
        return _handle_preview_generate(
            head_kwargs=head_kwargs,
            characters=dropdowns["characters"],
            discovery=discovery,
            playground_service=(
                get_application_container(request).playground_service
            ),
        )

    if act == "submit_preview":
        return _handle_submit_preview(
            request=request,
            preview=preview,
            dropdowns=dropdowns,
            discovery=discovery,
        )

    return _redirect_generator()


def _redirect_generator() -> RedirectResponse:
    return RedirectResponse(url="/playground/generator", status_code=303)


def _head_kwargs_from_post(
    *,
    character_id: int | None,
    scene_id: int | None,
    outfit_id: int | None,
    pose_id: int | None,
    expression_id: int | None,
    lighting_id: int | None,
    modifier_id: int | None,
    include_lighting: int | None,
    include_modifier: int | None,
    gen_seed: str | None,
    comfy_seed: str | None,
    max_tries: int,
    batch_runs: int | None,
    checkpoint_name: str | None,
    sampler_name: str | None,
    scheduler_name: str | None,
    steps_min: str | None,
    steps_max: str | None,
    cfg_min: str | None,
    cfg_max: str | None,
    cfg_step: str | None,
    steps: str | None,
    cfg: str | None,
    denoise: str | None,
) -> dict:
    return {
        "character_id": character_id,
        "scene_id": scene_id,
        "outfit_id": outfit_id,
        "pose_id": pose_id,
        "expression_id": expression_id,
        "lighting_id": lighting_id,
        "modifier_id": modifier_id,
        "include_lighting": include_lighting,
        "include_modifier": include_modifier,
        "gen_seed": gen_seed,
        "comfy_seed": comfy_seed,
        "max_tries": max_tries,
        "batch_runs": batch_runs,
        "checkpoint_name": checkpoint_name,
        "sampler_name": sampler_name,
        "scheduler_name": scheduler_name,
        "steps_min": steps_min,
        "steps_max": steps_max,
        "cfg_min": cfg_min,
        "cfg_max": cfg_max,
        "cfg_step": cfg_step,
        "steps": steps,
        "cfg": cfg,
        "denoise": denoise,
    }


def _handle_draft_remove(preview: list, did: str) -> RedirectResponse:
    updated = remove_draft(preview, did)
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, updated)
    return _redirect_generator()


def _handle_draft_update(
    *,
    preview: list,
    draft_id: str,
    head_kwargs: dict,
    draft_seed: str | None,
    draft_steps: str | None,
    draft_cfg: str | None,
    draft_sampler: str | None,
    draft_scheduler: str | None,
    draft_denoise: str | None,
    draft_checkpoint: str | None,
    draft_pos: str | None,
    draft_neg: str | None,
) -> RedirectResponse:
    if not draft_id:
        head = build_head_state_from_post(**head_kwargs)
        save_head_state(GENERATOR_STATE_PATH, head)
        return _redirect_generator()

    updated = update_draft(
        preview,
        draft_id=draft_id,
        seed=draft_seed,
        steps=draft_steps,
        cfg=draft_cfg,
        sampler=draft_sampler,
        scheduler=draft_scheduler,
        denoise=draft_denoise,
        checkpoint=draft_checkpoint,
        pos=draft_pos,
        neg=draft_neg,
    )
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, updated)
    return _redirect_generator()


def _handle_head_save(head_kwargs: dict) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    save_head_state(GENERATOR_STATE_PATH, head)
    return _redirect_generator()


def _handle_preview_generate(
    *,
    head_kwargs: dict,
    characters: list,
    discovery: Any,
    playground_service: PlaygroundService,
) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    save_head_state(GENERATOR_STATE_PATH, head)

    drafts = generate_preview_drafts(
        head=head,
        characters=characters,
        discovery=discovery,
        playground_service=playground_service,
        default_max_attempts=DEFAULT_MAX_TRIES,
    )
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, drafts)
    return _redirect_generator()


def _handle_submit_preview(
    *, request: Request, preview: list, dropdowns: dict, discovery: Any
):
    if not preview:
        return _redirect_generator()

    enqueue_info, error = submit_preview_drafts(
        preview,
        service=(
            get_application_container(request).playground_submission_service
        ),
    )
    clear_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    form = _reload_form_from_head(dropdowns)

    return templates.TemplateResponse(
        request=request,
        name="playground_generator.html",
        context={
            "request": request,
            "default_max_tries": DEFAULT_MAX_TRIES,
            "form": form,
            "error": error,
            "enqueue": enqueue_info,
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
            "preview": [],
        },
    )


def _reload_form_from_head(dropdowns: dict) -> dict:
    saved = load_head_state(GENERATOR_STATE_PATH)
    saved_char_id = (
        safe_int(str(saved.get("character_id", "")).strip()) if saved else None
    )
    char_name_for_defaults = character_name_from_id(
        dropdowns["characters"], saved_char_id
    )
    defaults = workflow_render_defaults(
        character_name=char_name_for_defaults, character_id=saved_char_id
    )
    return build_form_from_state(saved=saved, defaults=defaults)
