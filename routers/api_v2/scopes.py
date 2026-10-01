"""Canonical scope-facet V2 HTTP adapter."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from comfyreview.api import get_application_container
from comfyreview.application import ImageQueryValidationError
from routers.api_v2.common import build_image_filter, error_response

router = APIRouter()


@router.get("/scopes/facets")
def scope_facets(
    request: Request,
    scope: Annotated[list[str] | None, Query()] = None,
    classification: str = Query("all"),
    model: str = Query(""),
    checkpoint: str = Query(""),
    set_key: str = Query(""),
) -> JSONResponse:
    """Return contextual canonical scope counts."""
    container = get_application_container(request)
    try:
        filters = build_image_filter(
            scope or [], classification, model, checkpoint, set_key
        )
        facets = container.scope_facets.list_facets(filters)
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_image_filter", str(error))
    return JSONResponse(
        {"facets": [container.image_responses.facet(item) for item in facets]}
    )
