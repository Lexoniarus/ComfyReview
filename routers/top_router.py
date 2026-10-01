from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from comfyreview.api import get_application_container
from comfyreview.application import (
    AssignCurationCommand,
    CurationMutationError,
    CurationValidationError,
    InvalidOutputPathError,
    OutputImageReference,
    OutputPairNotFoundError,
    ReviewMutationError,
    ReviewValidationError,
    SubmitReviewCommand,
)
from services.output_file_service import OutputMutationError
from templates import TOP_PICTURES_HTML

router = APIRouter()


@router.get("/top_pictures", response_class=HTMLResponse)
def top_pictures(request: Request):
    del request
    return TOP_PICTURES_HTML.render()


@router.post("/assign_set")
def assign_set(
    request: Request,
    image_uid: str = Form(...),
    set_key: str = Form(""),
    model: str = Form(""),
    mode: str = Form("top"),
    subdir: str = Form(""),
    view_set_key: str = Form(""),
):
    try:
        get_application_container(request).curation_service.assign(
            AssignCurationCommand(
                image_uid=image_uid,
                set_key=set_key,
            )
        )
    except (CurationValidationError, InvalidOutputPathError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OutputPairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (CurationMutationError, OutputMutationError) as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RedirectResponse(
        url=f"/top_pictures?model={model}&mode={mode}&subdir={subdir}&set_key={view_set_key}",
        status_code=303,
    )


@router.post("/top_delete")
def top_delete(
    request: Request,
    image_uid: str = Form(...),
    json_path: str = Form(""),
    png_path: str = Form(""),
    combo_key: str = Form(""),
    model_branch: str = Form(""),
    checkpoint: str = Form(""),
    filter_model: str = Form(""),
    filter_subdir: str = Form(""),
    filter_mode: str = Form("top"),
    filter_set_key: str = Form(""),
):
    del combo_key, model_branch, checkpoint, json_path, png_path
    try:
        command = SubmitReviewCommand(
            image=OutputImageReference.from_client_uid(image_uid),
            rating=None,
            delete=True,
        )
        get_application_container(request).review_service.submit(command)
    except (InvalidOutputPathError, ReviewValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OutputPairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewMutationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return RedirectResponse(
        url=(
            f"/top_pictures?model={filter_model}"
            f"&mode={filter_mode}"
            f"&subdir={filter_subdir}"
            f"&set_key={filter_set_key}"
        ),
        status_code=303,
    )
