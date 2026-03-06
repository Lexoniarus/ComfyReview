from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Form, Query
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
from services.rating_submission_service import submit_rating
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
    rating: Optional[int] = Form(None),
    deleted: Optional[int] = Form(None),
    delete: Optional[int] = Form(None),
    combo_key: str = Form(...),
    model_branch: str = Form(...),
    checkpoint: str = Form(...),
    json_path: str = Form(...),
    png_path: str = Form(...),
    sampler: Optional[str] = Form(None),
    scheduler: Optional[str] = Form(None),
    steps: Optional[str] = Form(None),
    cfg: Optional[str] = Form(None),
    denoise: Optional[str] = Form(None),
    loras_json: Optional[str] = Form(None),
    filter_unrated: Optional[str] = Form(None),
    filter_model: Optional[str] = Form(None),
    filter_subdir: Optional[str] = Form(None),
    filter_scope: Optional[str] = Form(None),
    filter_character: Optional[str] = Form(None),
    filter_set_key: Optional[str] = Form(None),
):
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

    q_unrated = "1" if normalize_unrated_flag(filter_unrated, default=1) == 1 else "0"
    q_model = normalize_model(str(filter_model or ""))
    q_subdir = normalize_subdir(str(filter_subdir or ""))
    q_set_key = normalize_set_key(str(filter_set_key or ""))

    return RedirectResponse(
        url=f"/?unrated={q_unrated}&model={q_model}&subdir={q_subdir}&set_key={q_set_key}",
        status_code=303,
    )
