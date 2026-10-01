from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from comfyreview.api import get_application_container
from comfyreview.application import (
    ArenaMutationError,
    ArenaValidationError,
    RecordArenaDecisionCommand,
)
from templates import ARENA_HTML

router = APIRouter()


@router.get("/arena", response_class=HTMLResponse)
def arena(request: Request):
    del request
    return ARENA_HTML.render()


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
