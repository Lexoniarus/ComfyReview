# routers/playground/hub.py
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground")
def playground_home(request: Request):
    """Render the Playground combination overview."""
    return templates.TemplateResponse(
        request=request,
        name="playground_overview.html",
        context={"request": request},
    )


@router.get("/generations")
def generations_page(request: Request):
    """Render the canonical generation lifecycle shell."""
    return templates.TemplateResponse(
        request=request,
        name="generations.html",
        context={"request": request},
    )
