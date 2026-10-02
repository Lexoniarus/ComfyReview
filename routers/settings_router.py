"""Render the Frontend V2 settings shell."""

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from starlette.responses import Response

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/settings")
def settings(request: Request) -> Response:
    """Render the settings shell; browser behavior uses the V2 API."""
    return templates.TemplateResponse(
        request=request,
        name="settings.html",
        context={"request": request},
    )
