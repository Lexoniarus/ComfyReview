# routers/playground/hub.py
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from config import COMBO_PROMPTS_DB_PATH, DEFAULT_MAX_TRIES, MV_QUEUE_DB_PATH
from services.playground_hub_service import build_playground_dashboard_context

from ._shared import png_path_to_url

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground")
def playground_home(request: Request):
    ctx = build_playground_dashboard_context(
        combo_db_path=COMBO_PROMPTS_DB_PATH,
        mv_queue_db_path=MV_QUEUE_DB_PATH,
        default_max_tries=DEFAULT_MAX_TRIES,
        png_to_url=png_path_to_url,
    )

    return templates.TemplateResponse(
        "playground_dashboard.html",
        {"request": request, **ctx},
    )
