from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from db_store import DELETE_WEIGHT_DEFAULT, SUCCESS_THRESHOLD_DEFAULT

from services.analytics_page_service import (
    build_param_stats_page_context,
    build_prompt_tokens_page_context,
    build_recommendations_page_context,
    build_stats_page_context,
)
# Jinja Templates für die Analytics-Seiten
from templates import PARAM_HTML, PROMPT_HTML, RECO_HTML, STATS_HTML

# Router wird in app.py registriert
router = APIRouter()


# ===============================
# GET /stats
# ===============================
@router.get("/stats", response_class=HTMLResponse)
def stats(
    model: str = Query(""),
    min_n: int = Query(8),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: float = Query(DELETE_WEIGHT_DEFAULT),
):
    ctx = build_stats_page_context(model=model, min_n=min_n, limit=limit, t=t, dw=dw)
    return STATS_HTML.render(**ctx)


# ===============================
# GET /recommendations
# ===============================
@router.get("/recommendations", response_class=HTMLResponse)
def recommendations(
    model: str = Query(""),
    min_n: int = Query(5),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
    min_lb: float = Query(0.5),
    approx_min_n: int = Query(8),
    approx_limit: int = Query(80),
):
    ctx = build_recommendations_page_context(
        model=model,
        min_n=min_n,
        limit=limit,
        t=t,
        dw=dw,
        min_lb=min_lb,
        approx_min_n=approx_min_n,
        approx_limit=approx_limit,
    )
    return RECO_HTML.render(**ctx)


# ===============================
# GET /param_stats
# ===============================
@router.get("/param_stats", response_class=HTMLResponse)
def param_stats(
    model: str = Query(""),
    min_n: int = Query(10),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
):
    ctx = build_param_stats_page_context(model=model, min_n=min_n, t=t, dw=dw)
    return PARAM_HTML.render(**ctx)


# ===============================
# GET /prompt_tokens
# ===============================
@router.get("/prompt_tokens", response_class=HTMLResponse)
def prompt_tokens(
    model: str = Query(""),
    scope: str = Query("pos"),
    min_n: int = Query(8),
    limit: int = Query(200),
):
    ctx = build_prompt_tokens_page_context(model=model, scope=scope, min_n=min_n, limit=limit)
    return PROMPT_HTML.render(**ctx)

