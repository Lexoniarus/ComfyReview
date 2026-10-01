from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


# ===============================
# GET /stats
# ===============================
@router.get("/stats")
def stats(request: Request):
    """Render the analytics shell with combinations selected."""
    return _analytics_page(request, "combinations")


# ===============================
# GET /recommendations
# ===============================
@router.get("/recommendations")
def recommendations(request: Request):
    """Render the analytics shell with overview selected."""
    return _analytics_page(request, "overview")


# ===============================
# GET /param_stats
# ===============================
@router.get("/param_stats")
def param_stats(request: Request):
    """Render the analytics shell with parameters selected."""
    return _analytics_page(request, "parameters")


# ===============================
# GET /prompt_tokens
# ===============================
@router.get("/prompt_tokens")
def prompt_tokens(request: Request):
    """Render the analytics shell with prompt scopes selected."""
    return _analytics_page(request, "scopes")


def _analytics_page(request: Request, initial_section: str):
    return templates.TemplateResponse(
        request=request,
        name="analytics.html",
        context={"request": request, "initial_section": initial_section},
    )
