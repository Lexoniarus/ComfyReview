from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from comfyreview.api import get_application_container
from comfyreview.application import (
    InvalidOutputPathError,
    OutputImageReference,
    OutputPairNotFoundError,
    ReviewMutationError,
    ReviewValidationError,
    SubmitReviewCommand,
)
from services.context_filters import (
    normalize_model,
    normalize_set_key,
    normalize_subdir,
    normalize_unrated_flag,
)
from templates import INDEX_HTML

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(request: Request):
    del request
    return INDEX_HTML.render()


@router.post("/rate")
def rate(
    request: Request,
    rating: int | None = Form(None),
    deleted: int | None = Form(None),
    delete: int | None = Form(None),
    combo_key: str = Form(...),
    model_branch: str = Form(...),
    checkpoint: str = Form(...),
    image_uid: str | None = Form(None),
    json_path: str = Form(""),
    png_path: str = Form(""),
    sampler: str | None = Form(None),
    scheduler: str | None = Form(None),
    steps: str | None = Form(None),
    cfg: str | None = Form(None),
    denoise: str | None = Form(None),
    loras_json: str | None = Form(None),
    filter_unrated: str | None = Form(None),
    filter_model: str | None = Form(None),
    filter_subdir: str | None = Form(None),
    filter_scope: str | None = Form(None),
    filter_character: str | None = Form(None),
    filter_set_key: str | None = Form(None),
):
    del (
        combo_key,
        model_branch,
        checkpoint,
        sampler,
        scheduler,
        steps,
        cfg,
        denoise,
        loras_json,
        filter_scope,
        filter_character,
        json_path,
        png_path,
    )
    try:
        command = SubmitReviewCommand(
            image=OutputImageReference.from_client_uid(str(image_uid or "")),
            rating=rating,
            delete=bool(deleted or delete),
        )
        get_application_container(request).review_service.submit(command)
    except (InvalidOutputPathError, ReviewValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OutputPairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ReviewMutationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    q_unrated = (
        "1" if normalize_unrated_flag(filter_unrated, default=1) == 1 else "0"
    )
    q_model = normalize_model(str(filter_model or ""))
    q_subdir = normalize_subdir(str(filter_subdir or ""))
    q_set_key = normalize_set_key(str(filter_set_key or ""))

    return RedirectResponse(
        url=f"/?unrated={q_unrated}&model={q_model}&subdir={q_subdir}&set_key={q_set_key}",
        status_code=303,
    )
