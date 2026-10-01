"""Canonical prompt-catalog V2 HTTP adapters."""

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    CreatePromptComponentCommand,
    PromptCatalogValidationError,
    PromptComponent,
    PromptRevision,
    UpdatePromptComponentCommand,
)
from routers.api_v2.common import PromptKind, error_response

router = APIRouter()


class PromptComponentWriteRequest(BaseModel):
    """Create or update catalog metadata and immutable prompt content."""

    kind: PromptKind
    name: str
    tags: list[str] = Field(default_factory=list)
    notes: str = ""
    positive_text: str = ""
    negative_text: str = ""


class PromptArchiveRequest(BaseModel):
    """Set reversible component archive state."""

    archived: bool


@router.get("/catalog/components")
def catalog_components(
    request: Request,
    include_archived: bool = Query(False),
) -> JSONResponse:
    """Return canonical prompt components with their latest revisions."""
    components = get_application_container(
        request
    ).prompt_catalog_service.list_components(include_archived=include_archived)
    return JSONResponse(
        {"components": [component_response(item) for item in components]}
    )


@router.get("/catalog/components/{component_uid}")
def catalog_component(request: Request, component_uid: str) -> JSONResponse:
    """Return one canonical prompt component."""
    try:
        component = get_application_container(
            request
        ).prompt_catalog_service.get_component(component_uid)
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(component_response(component))


@router.get("/catalog/components/{component_uid}/revisions")
def catalog_component_revisions(
    request: Request,
    component_uid: str,
) -> JSONResponse:
    """Return immutable revision history for one component."""
    try:
        revisions = get_application_container(
            request
        ).prompt_catalog_service.list_revisions(component_uid)
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(
        {"revisions": [revision_response(item) for item in revisions]}
    )


@router.post("/catalog/components")
def create_catalog_component(
    request: Request,
    payload: PromptComponentWriteRequest,
) -> JSONResponse:
    """Create one component and immutable revision one."""
    try:
        component = get_application_container(
            request
        ).prompt_catalog_service.create_component(
            CreatePromptComponentCommand(
                kind=payload.kind,
                component_key="",
                name=payload.name,
                tags=tuple(payload.tags),
                notes=payload.notes,
                positive_text=payload.positive_text,
                negative_text=payload.negative_text,
            )
        )
    except PromptCatalogValidationError as error:
        return error_response(400, "invalid_catalog_component", str(error))
    return JSONResponse(component_response(component), status_code=201)


@router.put("/catalog/components/{component_uid}")
def update_catalog_component(
    request: Request,
    component_uid: str,
    payload: PromptComponentWriteRequest,
) -> JSONResponse:
    """Update metadata and append changed prompt content atomically."""
    try:
        current = get_application_container(
            request
        ).prompt_catalog_service.get_component(component_uid)
        if payload.kind != current.kind:
            raise PromptCatalogValidationError(
                "component kind cannot be changed"
            )
        component = get_application_container(
            request
        ).prompt_catalog_service.update_component(
            UpdatePromptComponentCommand(
                component_uid=component_uid,
                name=payload.name,
                tags=tuple(payload.tags),
                notes=payload.notes,
                positive_text=payload.positive_text,
                negative_text=payload.negative_text,
            )
        )
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(component_response(component))


@router.patch("/catalog/components/{component_uid}")
def archive_catalog_component(
    request: Request,
    component_uid: str,
    payload: PromptArchiveRequest,
) -> JSONResponse:
    """Archive or restore one component without deleting revisions."""
    try:
        component = get_application_container(
            request
        ).prompt_catalog_service.set_archived(
            component_uid,
            archived=payload.archived,
        )
    except (KeyError, PromptCatalogValidationError) as error:
        return catalog_error(error)
    return JSONResponse(component_response(component))


def component_response(component: PromptComponent) -> dict[str, object]:
    """Map one canonical prompt component to its V2 response."""
    return {
        "component_uid": component.component_uid,
        "kind": component.kind,
        "component_key": component.component_key,
        "name": component.name,
        "tags": component.tags,
        "notes": component.notes,
        "archived": component.archived,
        "latest_revision": {
            "revision_uid": component.latest_revision.revision_uid,
            "revision_number": component.latest_revision.revision_number,
            "positive_text": component.latest_revision.positive_text,
            "negative_text": component.latest_revision.negative_text,
        },
    }


def revision_response(revision: PromptRevision) -> dict[str, object]:
    """Map one immutable prompt revision to its V2 response."""
    return {
        "revision_uid": revision.revision_uid,
        "revision_number": revision.revision_number,
        "positive_text": revision.positive_text,
        "negative_text": revision.negative_text,
        "content_hash": revision.content_hash,
    }


def catalog_error(error: Exception) -> JSONResponse:
    """Normalize catalog lookup and validation failures."""
    if isinstance(error, KeyError):
        message = error.args[0] if error.args else str(error)
        return error_response(404, "catalog_component_not_found", str(message))
    return error_response(400, "invalid_catalog_component", str(error))
