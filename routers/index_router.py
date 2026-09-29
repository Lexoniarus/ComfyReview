from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Query, Request
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
from config import (
    CURATION_DB_PATH,
    CURATION_SET_KEYS,
    DB_PATH,
    DEFAULT_UNRATED_ONLY,
    PLAYGROUND_DB_PATH,
)
from services.context_filters import (
    normalize_model,
    normalize_set_key,
    normalize_subdir,
    normalize_unrated_flag,
)
from services.review_page_service import build_review_page_context
from templates import INDEX_HTML

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    request: Request,
    unrated: int = Query(1 if DEFAULT_UNRATED_ONLY else 0),
    model: str = Query(""),
    subdir: str = Query(""),
    set_key: str = Query(""),
):
    ctx = build_review_page_context(
        output_images=get_application_container(request).output_images,
        ratings_db_path=DB_PATH,
        playground_db_path=PLAYGROUND_DB_PATH,
        curation_db_path=CURATION_DB_PATH,
        unrated=unrated,
        model=model,
        subdir=subdir,
        set_key=set_key,
    )

    return INDEX_HTML.render(
        **ctx,
        set_key_list=["", "unsorted", *list(CURATION_SET_KEYS)],
    )


@router.post("/rate")
def rate(
    request: Request,
    rating: int | None = Form(None),
    deleted: int | None = Form(None),
    delete: int | None = Form(None),
    combo_key: str = Form(...),
    model_branch: str = Form(...),
    checkpoint: str = Form(...),
    json_path: str = Form(...),
    png_path: str = Form(...),
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
    )
    try:
        command = SubmitReviewCommand(
            image=OutputImageReference.from_client_paths(
                png_path=png_path,
                json_path=json_path,
            ),
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
