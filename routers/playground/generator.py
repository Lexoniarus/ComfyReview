# routers/playground/generator.py
from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

from typing import Optional, Any

from config import (
    DEFAULT_MAX_TRIES,
)

from ._shared import (
    GENERATOR_STATE_PATH,
    GENERATOR_PREVIEW_STATE_PATH,
    COMFY_DISCOVERY_CACHE_PATH,
    png_path_to_url,
)

from services.ui_state_service import safe_int
from services.playground_generator_ui_service import (
    load_playground_dropdown_items,
    discover_comfy_lists,
    load_head_state,
    save_head_state,
    load_preview_state,
    save_preview_state,
    clear_preview_state,
    character_name_from_id,
    workflow_render_defaults,
    build_form_from_state,
    build_head_state_from_post,
    remove_draft,
    update_draft,
    enrich_preview_with_best_pictures,
    generate_preview_drafts,
    submit_preview_drafts,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/playground/generator/apply_combo")
def playground_generator_apply_combo(
    character_id: int = Form(...),
    scene_id: int = Form(...),
    outfit_id: Optional[str] = Form(None),
) -> RedirectResponse:
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
    return RedirectResponse(url="/playground/generator", status_code=303)


@router.get("/playground/generator")
def playground_generator_page(request: Request):
    dropdowns = load_playground_dropdown_items()

    discovery = discover_comfy_lists(cache_path=COMFY_DISCOVERY_CACHE_PATH)

    saved = load_head_state(GENERATOR_STATE_PATH)
    saved_char_id = safe_int(str(saved.get("character_id", "")).strip()) if saved else None

    char_name_for_defaults = character_name_from_id(dropdowns["characters"], saved_char_id)
    defaults = workflow_render_defaults(character_name=char_name_for_defaults, character_id=saved_char_id)

    form = build_form_from_state(saved=saved, defaults=defaults)

    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH)


    return templates.TemplateResponse(
        "playground_generator.html",
        {
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
        return JSONResponse({"status": "error", "error": "missing draft_id"}, status_code=400)

    d = None
    for x in preview:
        if str((x or {}).get("draft_id") or "").strip() == draft_id_s:
            d = x
            break

    if d is None:
        return JSONResponse({"status": "error", "error": "draft not found"}, status_code=404)

    # fast path if already resolved
    if str((d or {}).get("best_img_url") or "").strip():
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

    from services.playground_generator_ui.best_pictures import resolve_best_picture_for_draft

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

    character_id: Optional[int] = Form(None),
    scene_id: Optional[int] = Form(None),
    outfit_id: Optional[int] = Form(None),
    pose_id: Optional[int] = Form(None),
    expression_id: Optional[int] = Form(None),
    lighting_id: Optional[int] = Form(None),
    modifier_id: Optional[int] = Form(None),
    include_lighting: Optional[int] = Form(None),
    include_modifier: Optional[int] = Form(None),
    gen_seed: Optional[str] = Form(None),
    comfy_seed: Optional[str] = Form(None),
    max_tries: int = Form(DEFAULT_MAX_TRIES),
    batch_runs: Optional[int] = Form(None),
    checkpoint_name: Optional[str] = Form(None),
    sampler_name: Optional[str] = Form(None),
    scheduler_name: Optional[str] = Form(None),
    steps_min: Optional[str] = Form(None),
    steps_max: Optional[str] = Form(None),
    cfg_min: Optional[str] = Form(None),
    cfg_max: Optional[str] = Form(None),
    cfg_step: Optional[str] = Form(None),
    steps: Optional[str] = Form(None),
    cfg: Optional[str] = Form(None),
    denoise: Optional[str] = Form(None),

    draft_id: Optional[str] = Form(None),
    draft_seed: Optional[str] = Form(None),
    draft_steps: Optional[str] = Form(None),
    draft_cfg: Optional[str] = Form(None),
    draft_sampler: Optional[str] = Form(None),
    draft_scheduler: Optional[str] = Form(None),
    draft_denoise: Optional[str] = Form(None),
    draft_checkpoint: Optional[str] = Form(None),
    draft_pos: Optional[str] = Form(None),
    draft_neg: Optional[str] = Form(None),
):
    act = str(action or "").lower().strip()
    dropdowns = load_playground_dropdown_items()
    discovery = discover_comfy_lists(cache_path=COMFY_DISCOVERY_CACHE_PATH)
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
        return _handle_preview_generate(head_kwargs=head_kwargs, characters=dropdowns["characters"], discovery=discovery)

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
    character_id: Optional[int],
    scene_id: Optional[int],
    outfit_id: Optional[int],
    pose_id: Optional[int],
    expression_id: Optional[int],
    lighting_id: Optional[int],
    modifier_id: Optional[int],
    include_lighting: Optional[int],
    include_modifier: Optional[int],
    gen_seed: Optional[str],
    comfy_seed: Optional[str],
    max_tries: int,
    batch_runs: Optional[int],
    checkpoint_name: Optional[str],
    sampler_name: Optional[str],
    scheduler_name: Optional[str],
    steps_min: Optional[str],
    steps_max: Optional[str],
    cfg_min: Optional[str],
    cfg_max: Optional[str],
    cfg_step: Optional[str],
    steps: Optional[str],
    cfg: Optional[str],
    denoise: Optional[str],
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
    draft_seed: Optional[str],
    draft_steps: Optional[str],
    draft_cfg: Optional[str],
    draft_sampler: Optional[str],
    draft_scheduler: Optional[str],
    draft_denoise: Optional[str],
    draft_checkpoint: Optional[str],
    draft_pos: Optional[str],
    draft_neg: Optional[str],
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


def _handle_preview_generate(*, head_kwargs: dict, characters: list, discovery: Any) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    save_head_state(GENERATOR_STATE_PATH, head)

    drafts = generate_preview_drafts(head=head, characters=characters, discovery=discovery)
    save_preview_state(GENERATOR_PREVIEW_STATE_PATH, drafts)
    return _redirect_generator()


def _handle_submit_preview(*, request: Request, preview: list, dropdowns: dict, discovery: Any):
    if not preview:
        return _redirect_generator()

    enqueue_info, error = submit_preview_drafts(preview)
    clear_preview_state(GENERATOR_PREVIEW_STATE_PATH)

    form = _reload_form_from_head(dropdowns)

    return templates.TemplateResponse(
        "playground_generator.html",
        {
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
    saved_char_id = safe_int(str(saved.get("character_id", "")).strip()) if saved else None
    char_name_for_defaults = character_name_from_id(dropdowns["characters"], saved_char_id)
    defaults = workflow_render_defaults(character_name=char_name_for_defaults, character_id=saved_char_id)
    return build_form_from_state(saved=saved, defaults=defaults)
