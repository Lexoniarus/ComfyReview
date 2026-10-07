"""Canonical review and image-delete V2 HTTP adapters."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    ImageQueryValidationError,
    InvalidOutputPathError,
    OutputImageReference,
    OutputPairNotFoundError,
    ReviewHistoryNotFoundError,
    ReviewMutationError,
    ReviewValidationError,
    SubmitReviewCommand,
)
from routers.api_v2.common import build_image_filter, error_response

router = APIRouter()


class ReviewRequest(BaseModel):
    """Accept one UID-only V2 review mutation."""

    image_uid: str
    rating: int


@router.get("/images/{image_uid}/reviews")
def review_history(request: Request, image_uid: str) -> JSONResponse:
    """Return append-only canonical review events for one image."""
    container = get_application_container(request)
    try:
        entries = container.review_history.list_for_image(image_uid)
    except ReviewValidationError as error:
        return error_response(400, "invalid_image_uid", str(error))
    except ReviewHistoryNotFoundError as error:
        return error_response(404, "image_not_found", str(error))
    return JSONResponse(
        {
            "image_uid": image_uid,
            "events": [
                {
                    "event_uid": entry.event_uid,
                    "event_type": entry.event_type,
                    "rating": entry.rating,
                    "sequence": entry.sequence,
                    "reviewed_at": entry.reviewed_at,
                }
                for entry in entries
            ],
        }
    )


@router.get("/review/candidate")
def review_candidate(
    request: Request,
    scope: Annotated[list[str] | None, Query()] = None,
    classification: str = Query("all"),
    model: str = Query(""),
    checkpoint: str = Query(""),
    set_key: str = Query(""),
) -> Response:
    """Return the next review candidate in one canonical scope."""
    container = get_application_container(request)
    try:
        filters = build_image_filter(
            scope or [], classification, model, checkpoint, set_key
        )
        image = container.review_candidates.next_candidate(filters)
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_image_filter", str(error))
    if image is None:
        return Response(status_code=204)
    return JSONResponse(container.image_responses.context(image))


@router.post("/reviews")
def submit_review(request: Request, payload: ReviewRequest) -> JSONResponse:
    """Submit one rating by canonical image UID."""
    container = get_application_container(request)
    try:
        result = container.review_service.submit(
            SubmitReviewCommand(
                image=OutputImageReference.from_client_uid(payload.image_uid),
                rating=payload.rating,
                delete=False,
            )
        )
    except (InvalidOutputPathError, ReviewValidationError) as error:
        return error_response(400, "invalid_review", str(error))
    except OutputPairNotFoundError as error:
        return error_response(404, "image_not_found", str(error))
    except ReviewMutationError as error:
        return error_response(500, "review_failed", str(error))
    return JSONResponse(
        {
            "review_id": result.review_id,
            "run": result.run,
            "deleted": result.deleted,
            "promotion_pending": result.promotion_pending,
        }
    )


@router.post("/images/{image_uid}/delete")
def delete_image(request: Request, image_uid: str) -> JSONResponse:
    """Delete one image through the canonical review lifecycle."""
    container = get_application_container(request)
    try:
        result = container.review_service.submit(
            SubmitReviewCommand(
                image=OutputImageReference.from_client_uid(image_uid),
                rating=None,
                delete=True,
            )
        )
    except (InvalidOutputPathError, ReviewValidationError) as error:
        return error_response(400, "invalid_delete", str(error))
    except OutputPairNotFoundError as error:
        return error_response(404, "image_not_found", str(error))
    except ReviewMutationError as error:
        return error_response(500, "delete_failed", str(error))
    return JSONResponse(
        {
            "review_id": result.review_id,
            "run": result.run,
            "deleted": result.deleted,
            "promotion_pending": result.promotion_pending,
        }
    )
