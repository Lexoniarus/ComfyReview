from __future__ import annotations

from fastapi import APIRouter, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from config import (
    CURATION_DB_PATH,
    CURATION_SET_KEYS,
    COMBO_PROMPTS_DB_PATH,
    DB_PATH,
    ARENA_DB_PATH,
    IMAGES_DB_PATH,
    LORA_EXPORT_ROOT,
    MIN_RUNS,
    MV_QUEUE_DB_PATH,
    OUTPUT_ROOT,
    PLAYGROUND_DB_PATH,
    POOL_LIMIT,
    PROMPT_TOKENS_DB_PATH,
    SOFT_DELETE_TO_TRASH,
    TRASH_ROOT,
)

from services.context_filters import build_gallery_context
from services.curation_assignment_service import assign_image_to_set
from services.gallery_view_service import build_top_pictures_page
from services.rating_submission_service import submit_rating

from templates import TOP_PICTURES_HTML

router = APIRouter()


@router.get("/top_pictures", response_class=HTMLResponse)
def top_pictures(
    model: str = Query(""),
    mode: str = Query("top"),
    set_key: str = Query(""),
    subdir: str = Query(""),
):
    ctx = build_gallery_context(model=model, subdir=subdir, set_key=set_key, mode=mode)

    vm = build_top_pictures_page(
        output_root=OUTPUT_ROOT,
        playground_db_path=PLAYGROUND_DB_PATH,
        context=ctx,
        min_runs=MIN_RUNS,
        limit=POOL_LIMIT,
    )

    return TOP_PICTURES_HTML.render(
        cards=vm["cards"],
        model=vm["model"],
        subdir=vm["subdir"],
        model_list=vm["model_list"],
        subdir_list=vm["subdir_list"],
        mode=vm["mode"],
        character_options=vm["character_options"],
        set_key=vm["set_key"],
        set_keys=CURATION_SET_KEYS,
        pool_limit=POOL_LIMIT,
        min_runs=MIN_RUNS,
    )


@router.post("/assign_set")
def assign_set(
    png_path: str = Form(...),
    json_path: str = Form(...),
    set_key: str = Form(""),
    model: str = Form(""),
    mode: str = Form("top"),
    subdir: str = Form(""),
    view_set_key: str = Form(""),
):
    assign_image_to_set(
        curation_db_path=CURATION_DB_PATH,
        output_root=OUTPUT_ROOT,
        lora_export_root=LORA_EXPORT_ROOT,
        allowed_set_keys=CURATION_SET_KEYS,
        ratings_db_path=DB_PATH,
        prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
        images_db_path=IMAGES_DB_PATH,
        combo_prompts_db_path=COMBO_PROMPTS_DB_PATH,
        arena_db_path=ARENA_DB_PATH,
        png_path=str(png_path),
        json_path=str(json_path),
        set_key=str(set_key),
    )

    return RedirectResponse(
        url=f"/top_pictures?model={model}&mode={mode}&subdir={subdir}&set_key={view_set_key}",
        status_code=303,
    )


@router.post("/top_delete")
def top_delete(
    json_path: str = Form(...),
    png_path: str = Form(...),
    combo_key: str = Form(""),
    model_branch: str = Form(""),
    checkpoint: str = Form(""),
    filter_model: str = Form(""),
    filter_subdir: str = Form(""),
    filter_mode: str = Form("top"),
    filter_set_key: str = Form(""),
):
    # unify delete behavior with /rate submission logic
    submit_rating(
        ratings_db_path=DB_PATH,
        prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
        mv_queue_db_path=MV_QUEUE_DB_PATH,
        output_root=OUTPUT_ROOT,
        trash_root=TRASH_ROOT,
        soft_delete_to_trash=bool(SOFT_DELETE_TO_TRASH),
        rating=None,
        deleted=1,
        delete=1,
        combo_key=str(combo_key or ""),
        model_branch=str(model_branch or ""),
        checkpoint=str(checkpoint or ""),
        json_path=str(json_path),
        png_path=str(png_path),
        sampler=None,
        scheduler=None,
        steps=None,
        cfg=None,
        denoise=None,
        loras_json=None,
    )

    return RedirectResponse(
        url=(
            f"/top_pictures?model={filter_model}"
            f"&mode={filter_mode}"
            f"&subdir={filter_subdir}"
            f"&set_key={filter_set_key}"
        ),
        status_code=303,
    )
