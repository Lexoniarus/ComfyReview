from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse

from config import (
    CURATION_DB_PATH,
    CURATION_SET_KEYS,
    DB_PATH,
    DEFAULT_UNRATED_ONLY,
    MV_QUEUE_DB_PATH,
    OUTPUT_ROOT,
    PLAYGROUND_DB_PATH,
    PROMPT_TOKENS_DB_PATH,
    SOFT_DELETE_TO_TRASH,
    TRASH_ROOT,
)
from services.context_filters import (
    normalize_model,
    normalize_set_key,
    normalize_subdir,
    normalize_unrated_flag,
)
from services.output_file_service import (
    InvalidOutputPathError,
    OutputMutationError,
    OutputPairNotFoundError,
)
from services.rating_submission_service import (
    ReviewValidationError,
    submit_rating,
)
from services.review_page_service import build_review_page_context
from templates import INDEX_HTML

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
def index(
    unrated: int = Query(1 if DEFAULT_UNRATED_ONLY else 0),
    model: str = Query(""),
    subdir: str = Query(""),
    set_key: str = Query(""),
):
    ctx = build_review_page_context(
        output_root=OUTPUT_ROOT,
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
    try:
        submit_rating(
            ratings_db_path=DB_PATH,
            prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
            mv_queue_db_path=MV_QUEUE_DB_PATH,
            output_root=OUTPUT_ROOT,
            trash_root=TRASH_ROOT,
            soft_delete_to_trash=bool(SOFT_DELETE_TO_TRASH),
            rating=rating,
            deleted=deleted,
            delete=delete,
            combo_key=combo_key,
            model_branch=model_branch,
            checkpoint=checkpoint,
            json_path=json_path,
            png_path=png_path,
            sampler=sampler,
            scheduler=scheduler,
            steps=steps,
            cfg=cfg,
            denoise=denoise,
            loras_json=loras_json,
        )
    except (InvalidOutputPathError, ReviewValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OutputPairNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except OutputMutationError as exc:
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
