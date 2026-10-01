"""Canonical image-context and ranking V2 HTTP adapters."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse

from comfyreview.api import get_application_container
from comfyreview.application import (
    ImageContextNotFoundError,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
)
from routers.api_v2.common import build_image_filter, error_response

router = APIRouter()


@router.get("/rankings")
def rankings(
    request: Request,
    scope: Annotated[list[str] | None, Query()] = None,
    classification: str = Query("all"),
    model: str = Query(""),
    checkpoint: str = Query(""),
    set_key: str = Query(""),
    mode: str = Query("top"),
    offset: int = Query(0),
    limit: int = Query(48),
) -> JSONResponse:
    """Return one SQL-ranked canonical image page."""
    container = get_application_container(request)
    try:
        order = ImageOrder(mode)
        if order not in {ImageOrder.TOP, ImageOrder.WORST}:
            raise ValueError(mode)
        filters = build_image_filter(
            scope or [],
            classification,
            model,
            checkpoint,
            set_key,
            minimum_rating_count=container.settings.minimum_runs,
        )
        page = container.image_contexts.list_images(
            ImageQuery(
                filters=filters, order=order, offset=offset, limit=limit
            )
        )
    except (ImageQueryValidationError, ValueError) as error:
        return error_response(400, "invalid_ranking_query", str(error))
    return JSONResponse(
        {
            "items": [
                {
                    **container.image_responses.summary(item),
                    "image_url": container.image_responses.context(item)[
                        "image_url"
                    ],
                }
                for item in page.entries
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "mode": order.value,
        }
    )


@router.get("/images/{image_uid}")
def image_context(request: Request, image_uid: str) -> JSONResponse:
    """Return one complete canonical image context."""
    container = get_application_container(request)
    try:
        image = container.image_contexts.get_image(image_uid)
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_image_uid", str(error))
    except ImageContextNotFoundError as error:
        return error_response(404, "image_not_found", str(error))
    return JSONResponse(container.image_responses.context(image))
