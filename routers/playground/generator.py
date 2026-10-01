# routers/playground/generator.py
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Form, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from comfyreview.api.dependencies import get_application_container
from comfyreview.application import GenerationDefaults, PlaygroundService
from services.playground_generator_ui.drafts import remove_draft, update_draft
from services.playground_generator_ui.generation import generate_preview_drafts
from services.playground_generator_ui.head_form import (
    build_form_from_state,
    build_head_state_from_post,
)
from services.playground_generator_ui.ports import PlaygroundGeneratorState
from services.playground_generator_ui.submit import (
    submit_preview_drafts,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.post("/playground/generator/apply_combo")
def playground_generator_apply_combo(
    request: Request,
    character_id: str = Form(...),
    scene_id: str = Form(...),
    outfit_id: str | None = Form(None),
) -> RedirectResponse:
    state = get_application_container(request).playground_ui_state
    saved = state.load_head()

    saved["character_id"] = str(character_id).strip()
    saved["scene_id"] = str(scene_id).strip()
    saved["outfit_id"] = str(outfit_id or "").strip()

    state.save_head(saved)
    return RedirectResponse(url="/playground/generator", status_code=303)


@router.get("/playground/generator")
def playground_generator_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="playground_generator.html",
        context={"request": request},
    )


@router.get("/playground/generator/preview_draft_best")
def playground_generator_preview_draft_best(request: Request, draft_id: str):
    """Lazy load per-draft best picture info.

    The generator page must render fast. Best picture matching can be slow because it hits
    prompt_tokens and ratings/images indices. This endpoint resolves one draft at a time.
    """
    preview = get_application_container(
        request
    ).playground_ui_state.load_preview()
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
    if get_application_container(request).file_urls.url_exists(
        str((d or {}).get("best_img_url") or "")
    ):
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

    container = get_application_container(request)
    res = resolve_best_picture_for_draft(
        d,
        analytics=container.analytics_service,
        minimum_ratings=container.settings.minimum_runs,
        candidate_limit=container.settings.pool_limit,
        image_url=container.file_urls.to_url,
    )

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
            container.playground_ui_state.save_preview(preview)
        except Exception:
            pass

    return JSONResponse(res)


@router.post("/playground/generator")
def playground_generator_run(
    request: Request,
    action: str = Form("preview_generate"),
    character_id: str | None = Form(None),
    scene_id: str | None = Form(None),
    outfit_id: str | None = Form(None),
    pose_id: str | None = Form(None),
    expression_id: str | None = Form(None),
    lighting_id: str | None = Form(None),
    modifier_id: str | None = Form(None),
    include_lighting: int | None = Form(None),
    include_modifier: int | None = Form(None),
    gen_seed: str | None = Form(None),
    comfy_seed: str | None = Form(None),
    max_tries: int | None = Form(None),
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
    dropdowns = get_application_container(
        request
    ).prompt_catalog_views.dropdown_items()
    discovery = get_application_container(
        request
    ).playground_discovery.discover()
    state = get_application_container(request).playground_ui_state
    preview = state.load_preview()

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
        max_tries=(
            get_application_container(request).settings.default_max_tries
            if max_tries is None
            else max_tries
        ),
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
        return _handle_draft_remove(
            preview,
            str(draft_id or ""),
            state=state,
        )

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
            state=state,
        )

    if act == "head_save":
        return _handle_head_save(head_kwargs, state=state)

    if act == "preview_generate":
        return _handle_preview_generate(
            head_kwargs=head_kwargs,
            characters=dropdowns["characters"],
            discovery=discovery,
            playground_service=(
                get_application_container(request).playground_service
            ),
            default_max_attempts=get_application_container(
                request
            ).settings.default_max_tries,
            render_defaults=_render_defaults(
                get_application_container(request).workflow_defaults.load(
                    "default-character",
                    1,
                )
            ),
            state=state,
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
    character_id: str | None,
    scene_id: str | None,
    outfit_id: str | None,
    pose_id: str | None,
    expression_id: str | None,
    lighting_id: str | None,
    modifier_id: str | None,
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


def _handle_draft_remove(
    preview: list,
    did: str,
    *,
    state: PlaygroundGeneratorState,
) -> RedirectResponse:
    updated = remove_draft(preview, did)
    state.save_preview(updated)
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
    state: PlaygroundGeneratorState,
) -> RedirectResponse:
    if not draft_id:
        head = build_head_state_from_post(**head_kwargs)
        state.save_head(head)
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
    state.save_preview(updated)
    return _redirect_generator()


def _handle_head_save(
    head_kwargs: dict,
    *,
    state: PlaygroundGeneratorState,
) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    state.save_head(head)
    return _redirect_generator()


def _handle_preview_generate(
    *,
    head_kwargs: dict,
    characters: list,
    discovery: Any,
    playground_service: PlaygroundService,
    default_max_attempts: int,
    render_defaults: dict[str, str],
    state: PlaygroundGeneratorState,
) -> RedirectResponse:
    head = build_head_state_from_post(**head_kwargs)
    state.save_head(head)

    drafts = generate_preview_drafts(
        head=head,
        characters=characters,
        discovery=discovery,
        playground_service=playground_service,
        render_defaults=render_defaults,
        default_max_attempts=default_max_attempts,
    )
    state.save_preview(drafts)
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
    state = get_application_container(request).playground_ui_state
    state.clear_preview()

    default_max_attempts = get_application_container(
        request
    ).settings.default_max_tries
    form = _reload_form_from_head(
        _render_defaults(
            get_application_container(request).workflow_defaults.load(
                "default-character",
                1,
            )
        ),
        default_max_attempts=default_max_attempts,
        state=state,
    )

    return templates.TemplateResponse(
        request=request,
        name="playground_generator.html",
        context={
            "request": request,
            "default_max_tries": default_max_attempts,
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


def _reload_form_from_head(
    defaults: dict[str, str],
    *,
    default_max_attempts: int,
    state: PlaygroundGeneratorState,
) -> dict:
    saved = state.load_head()
    return build_form_from_state(
        saved=saved,
        defaults=defaults,
        default_max_attempts=default_max_attempts,
    )


def _render_defaults(defaults: GenerationDefaults) -> dict[str, str]:
    return {
        "checkpoint_name": defaults.checkpoint,
        "sampler_name": defaults.sampler.sampler,
        "scheduler_name": defaults.sampler.scheduler,
        "steps": str(defaults.sampler.steps),
        "cfg": str(defaults.sampler.cfg),
        "denoise": str(defaults.sampler.denoise),
    }
