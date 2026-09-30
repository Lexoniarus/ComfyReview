# routers/playground/hub.py
from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

from comfyreview.api import get_application_container

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground")
def playground_home(request: Request):
    ctx = get_application_container(request).playground_hub.build_context()

    return templates.TemplateResponse(
        request=request,
        name="playground_dashboard.html",
        context={"request": request, **ctx},
    )
