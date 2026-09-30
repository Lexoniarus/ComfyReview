from fastapi import APIRouter, Form, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from comfyreview.api import get_application_container
from comfyreview.application import (
    ArenaMutationError,
    ArenaValidationError,
    RecordArenaDecisionCommand,
)
from config import MIN_RUNS, PLAYGROUND_DB_PATH, POOL_LIMIT
from services.arena_page_service import build_arena_page_context
from services.context_filters import build_gallery_context
from templates import ARENA_HTML

router = APIRouter()


@router.get("/arena", response_class=HTMLResponse)
def arena(
    request: Request,
    model: str = Query(""),
    mode: str = Query("top"),
    set_key: str = Query(""),
    subdir: str = Query(""),
):
    ctx = build_gallery_context(
        model=model, subdir=subdir, set_key=set_key, mode=mode
    )

    vm = build_arena_page_context(
        ranking_service=get_application_container(request).ranking_service,
        arena_service=get_application_container(request).arena_service,
        playground_db_path=PLAYGROUND_DB_PATH,
        context=ctx,
        min_runs=MIN_RUNS,
        pool_limit=POOL_LIMIT,
    )

    return ARENA_HTML.render(
        left=vm["left"],
        right=vm["right"],
        message=vm["message"],
        model=vm["model"],
        subdir=vm["subdir"],
        model_list=vm["model_list"],
        subdir_list=vm["subdir_list"],
        mode=vm["mode"],
        character_options=vm["character_options"],
        set_key=vm["set_key"],
        pool_limit=POOL_LIMIT,
        min_runs=MIN_RUNS,
    )


@router.post("/arena_result")
def arena_result(
    request: Request,
    winner_side: str = Form(...),
    left_image_uid: str = Form(...),
    right_image_uid: str = Form(...),
    model: str = Form(""),
    subdir: str = Form(""),
    mode: str = Form("top"),
    set_key: str = Form(""),
):
    try:
        get_application_container(request).arena_service.record_decision(
            RecordArenaDecisionCommand(
                left_image_uid=left_image_uid,
                right_image_uid=right_image_uid,
                winner_side=winner_side,
            )
        )
    except ArenaValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ArenaMutationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RedirectResponse(
        url=f"/arena?model={model}&mode={mode}&subdir={subdir}&set_key={set_key}",
        status_code=303,
    )
