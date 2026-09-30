from fastapi import APIRouter, Query, Request
from fastapi.responses import HTMLResponse

from comfyreview.api import get_application_container
from db_store import DELETE_WEIGHT_DEFAULT, SUCCESS_THRESHOLD_DEFAULT

# Jinja Templates für die Analytics-Seiten
from templates import PARAM_HTML, PROMPT_HTML, RECO_HTML, STATS_HTML

# Router wird in app.py registriert
router = APIRouter()


# ===============================
# GET /stats
# ===============================
@router.get("/stats", response_class=HTMLResponse)
def stats(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(8),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: float = Query(DELETE_WEIGHT_DEFAULT),
):
    ctx = get_application_container(request).analytics_pages.stats_context(
        model=model,
        min_n=min_n,
        limit=limit,
        success_threshold=t,
        delete_weight=dw,
    )
    return STATS_HTML.render(**ctx)


# ===============================
# GET /recommendations
# ===============================
@router.get("/recommendations", response_class=HTMLResponse)
def recommendations(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(5),
    limit: int = Query(200),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
    min_lb: float = Query(0.5),
    approx_min_n: int = Query(8),
    approx_limit: int = Query(80),
):
    ctx = get_application_container(
        request
    ).analytics_pages.recommendations_context(
        model=model,
        min_n=min_n,
        limit=limit,
        success_threshold=t,
        delete_weight=dw,
        minimum_lower_bound=min_lb,
        approximate_minimum_samples=approx_min_n,
        approximate_limit=approx_limit,
    )
    return RECO_HTML.render(**ctx)


# ===============================
# GET /param_stats
# ===============================
@router.get("/param_stats", response_class=HTMLResponse)
def param_stats(
    request: Request,
    model: str = Query(""),
    min_n: int = Query(10),
    t: int = Query(SUCCESS_THRESHOLD_DEFAULT),
    dw: int = Query(DELETE_WEIGHT_DEFAULT),
):
    ctx = get_application_container(request).analytics_pages.parameter_context(
        model=model,
        min_n=min_n,
        success_threshold=t,
        delete_weight=dw,
    )
    return PARAM_HTML.render(**ctx)


# ===============================
# GET /prompt_tokens
# ===============================
@router.get("/prompt_tokens", response_class=HTMLResponse)
def prompt_tokens(
    request: Request,
    model: str = Query(""),
    scope: str = Query("pos"),
    min_n: int = Query(8),
    limit: int = Query(200),
):
    ctx = get_application_container(
        request
    ).analytics_pages.prompt_tokens_context(
        model=model, scope=scope, min_n=min_n, limit=limit
    )
    return PROMPT_HTML.render(**ctx)
