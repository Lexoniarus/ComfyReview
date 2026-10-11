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


@router.get("/card-candidate-groups")
def card_candidate_groups_page(request: Request):
    """Render the persistent four-Card group overview shell."""
    return templates.TemplateResponse(
        request=request,
        name="card_candidate_groups.html",
        context={"request": request},
    )


@router.get("/card-candidate-groups/{group_id}")
def card_candidate_group_page(request: Request, group_id: str):
    """Render one four-Card comparison shell."""
    return templates.TemplateResponse(
        request=request,
        name="card_candidate_group.html",
        context={"request": request, "group_id": group_id},
    )


@router.get("/card-deck")
def card_deck_page(request: Request):
    """Render the confirmed Card pool and bounded POC deck shell."""
    return templates.TemplateResponse(
        request=request,
        name="card_deck.html",
        context={"request": request},
    )
