"""Canonical prompt-catalog browser routes."""

from __future__ import annotations

from collections.abc import Callable

from fastapi import APIRouter, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from comfyreview.api import get_application_container
from comfyreview.application import (
    PromptCatalogValidationError,
    PromptComponent,
)

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/playground/browse")
def playground_browse(
    request: Request,
    kind: str = "",
    q: str = "",
):
    """Render the API-backed canonical catalog shell."""
    del kind, q
    return templates.TemplateResponse(
        request=request,
        name="playground.html",
        context={"request": request},
    )


@router.get("/playground/create")
def playground_create_page(request: Request, kind: str = "scene"):
    """Render the canonical catalog shell for legacy create URLs."""
    del kind
    return templates.TemplateResponse(
        request=request,
        name="playground.html",
        context={"request": request},
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
) -> RedirectResponse:
    """Create one canonical component and its first revision."""
    _run_catalog_mutation(
        lambda: get_application_container(request).prompt_catalog_views.create(
            kind=kind,
            name=name,
            tags=tags,
            positive_text=pos,
            negative_text=neg,
            notes=notes,
        )
    )
    return _browse_redirect(kind)


@router.post("/playground/update")
def playground_update(
    request: Request,
    item_id: str = Form(...),
    kind: str = Form(...),
    name: str = Form(...),
    tags: str = Form(""),
    pos: str = Form(""),
    neg: str = Form(""),
    notes: str = Form(""),
) -> RedirectResponse:
    """Atomically update metadata and append changed prompt content."""
    _run_catalog_mutation(
        lambda: get_application_container(request).prompt_catalog_views.update(
            component_uid=item_id,
            name=name,
            tags=tags,
            positive_text=pos,
            negative_text=neg,
            notes=notes,
        )
    )
    return _browse_redirect(kind)


@router.post("/playground/delete")
def playground_delete(
    request: Request,
    item_id: str = Form(...),
    kind: str = Form(""),
) -> RedirectResponse:
    """Archive a component without deleting authored revisions."""
    _run_catalog_mutation(
        lambda: get_application_container(
            request
        ).prompt_catalog_views.set_archived(
            item_id,
            archived=True,
        )
    )
    return _browse_redirect(kind)


@router.post("/playground/restore")
def playground_restore(
    request: Request,
    item_id: str = Form(...),
    kind: str = Form(""),
) -> RedirectResponse:
    """Restore one archived component."""
    _run_catalog_mutation(
        lambda: get_application_container(
            request
        ).prompt_catalog_views.set_archived(
            item_id,
            archived=False,
        )
    )
    return _browse_redirect(kind)


def _browse_redirect(kind: str) -> RedirectResponse:
    return RedirectResponse(
        url="/playground/browse?kind=" + str(kind),
        status_code=303,
    )


def _run_catalog_mutation(
    operation: Callable[[], PromptComponent],
) -> PromptComponent:
    try:
        return operation()
    except PromptCatalogValidationError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except KeyError as error:
        detail = error.args[0] if error.args else str(error)
        raise HTTPException(status_code=404, detail=detail) from error
