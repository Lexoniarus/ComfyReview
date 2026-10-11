"""Thin template routes for the Card Factory prototype surfaces."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/card-factory")
def card_factory_page(request: Request):
    """Render the canonical source selection shell."""
    return templates.TemplateResponse(
        request=request,
        name="card_factory.html",
        context={"request": request},
    )


@router.get("/card-workshop/{session_id}")
def card_workshop_page(request: Request, session_id: str):
    """Render one revision-safe Card workshop shell."""
    return templates.TemplateResponse(
        request=request,
        name="card_workshop.html",
        context={"request": request, "session_id": session_id},
    )
