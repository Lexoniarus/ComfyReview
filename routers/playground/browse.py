# routers/playground/browse.py
from __future__ import annotations

from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from config import PLAYGROUND_DB_PATH

from stores.playground_store import (
    list_items,
    create_item,
    update_item,
    delete_item,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground/browse")
def playground_browse(request: Request, kind: str = "", q: str = ""):
    rows = list_items(PLAYGROUND_DB_PATH, kind=kind, q=q, limit=200)

    return templates.TemplateResponse(
        "playground.html",
        {
            "request": request,
            "rows": rows,
            "kind": kind,
            "q": q,
        },
    )


@router.get("/playground/create")
def playground_create_page(request: Request, kind: str = "scene"):
    return templates.TemplateResponse(
        "playground.html",
        {
            "request": request,
            "rows": [],
            "kind": kind,
            "q": "",
        },
    )


@router.post("/playground/create")
def playground_create(
    request: Request,
    kind: str = Form(...),
    name: str = Form(...),
    tags: str = Form(""),
    pos: str = Form(""),
    neg: str = Form(""),
    notes: str = Form(""),
):
    create_item(PLAYGROUND_DB_PATH, kind=kind, name=name, tags=tags, pos=pos, neg=neg, notes=notes)
    return RedirectResponse(url="/playground/browse?kind=" + str(kind), status_code=303)


@router.post("/playground/update")
def playground_update(
    request: Request,
    item_id: int = Form(...),
    kind: str = Form(...),
    name: str = Form(...),
    tags: str = Form(""),
    pos: str = Form(""),
    neg: str = Form(""),
    notes: str = Form(""),
):
    update_item(
        PLAYGROUND_DB_PATH,
        item_id=int(item_id),
        kind=kind,
        name=name,
        tags=tags,
        pos=pos,
        neg=neg,
        notes=notes,
    )
    return RedirectResponse(url="/playground/browse?kind=" + str(kind), status_code=303)


@router.post("/playground/delete")
def playground_delete(request: Request, item_id: int = Form(...), kind: str = Form("")):
    delete_item(PLAYGROUND_DB_PATH, item_id=int(item_id))
    return RedirectResponse(url="/playground/browse?kind=" + str(kind), status_code=303)
