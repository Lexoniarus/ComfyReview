"""Thin template route for the ES-module Playground Generator."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground/generator")
def playground_generator_page(request: Request):
    """Render the canonical Generator shell without server-owned UI state."""
    return templates.TemplateResponse(
        request=request,
        name="playground_generator.html",
        context={"request": request},
    )
