"""JSON-only HTTP adapters for the ComfyReview V2 frontend."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    ArenaMutationError,
    ArenaValidationError,
    AssignCurationCommand,
    CurationMutationError,
    CurationValidationError,
    ImageClassification,
    ImageContextNotFoundError,
    ImageFilter,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
    InvalidOutputPathError,
    OutputImageReference,
    OutputPairNotFoundError,
    RecordArenaDecisionCommand,
    ReviewMutationError,
    ReviewValidationError,
    ScopeSelection,
    SubmitReviewCommand,
)
from comfyreview.observability import get_trace_id
from services.output_file_service import OutputMutationError

router = APIRouter(prefix="/api/v2")


class ReviewRequest(BaseModel):
    """Accept one UID-only V2 review mutation."""

    image_uid: str
    rating: int


class CurationRequest(BaseModel):
    """Accept one UID-only V2 curation mutation."""

    set_key: str


class ArenaDecisionRequest(BaseModel):
    """Accept one UID-only V2 Arena decision."""

    left_image_uid: str
    right_image_uid: str
    winner_side: Literal["left", "right"]


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
        filters = _image_filter(
            scope or [],
            classification,
            model,
            checkpoint,
            set_key,
        )
        facets = container.scope_facets.list_facets(filters)
    except ImageQueryValidationError as error:
        return _error(400, "invalid_image_filter", str(error))
    return JSONResponse(
        {"facets": [container.image_responses.facet(item) for item in facets]}
    )


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
        filters = _image_filter(
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
        return _error(400, "invalid_ranking_query", str(error))
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
        return _error(400, "invalid_image_uid", str(error))
    except ImageContextNotFoundError as error:
        return _error(404, "image_not_found", str(error))
    return JSONResponse(container.image_responses.context(image))


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
        filters = _image_filter(
            scope or [],
            classification,
            model,
            checkpoint,
            set_key,
        )
        image = container.review_candidates.next_candidate(filters)
    except ImageQueryValidationError as error:
        return _error(400, "invalid_image_filter", str(error))
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
        return _error(400, "invalid_review", str(error))
    except OutputPairNotFoundError as error:
        return _error(404, "image_not_found", str(error))
    except ReviewMutationError as error:
        return _error(500, "review_failed", str(error))
    return JSONResponse(
        {
            "review_id": result.review_id,
            "run": result.run,
            "deleted": result.deleted,
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
        return _error(400, "invalid_delete", str(error))
    except OutputPairNotFoundError as error:
        return _error(404, "image_not_found", str(error))
    except ReviewMutationError as error:
        return _error(500, "delete_failed", str(error))
    return JSONResponse(
        {
            "review_id": result.review_id,
            "run": result.run,
            "deleted": result.deleted,
        }
    )


@router.put("/images/{image_uid}/curation")
def assign_curation(
    request: Request,
    image_uid: str,
    payload: CurationRequest,
) -> JSONResponse:
    """Assign one canonical image to a curation set."""
    container = get_application_container(request)
    try:
        result = container.curation_service.assign(
            AssignCurationCommand(image_uid=image_uid, set_key=payload.set_key)
        )
    except (CurationValidationError, InvalidOutputPathError) as error:
        return _error(400, "invalid_curation", str(error))
    except OutputPairNotFoundError as error:
        return _error(404, "image_not_found", str(error))
    except (CurationMutationError, OutputMutationError) as error:
        return _error(500, "curation_failed", str(error))
    return JSONResponse(
        {"image_uid": result.image_uid, "set_key": result.set_key}
    )


@router.post("/arena/decisions")
def record_arena_decision(
    request: Request,
    payload: ArenaDecisionRequest,
) -> JSONResponse:
    """Record one canonical UID-based Arena decision."""
    container = get_application_container(request)
    try:
        result = container.arena_service.record_decision(
            RecordArenaDecisionCommand(
                left_image_uid=payload.left_image_uid,
                right_image_uid=payload.right_image_uid,
                winner_side=payload.winner_side,
            )
        )
    except ArenaValidationError as error:
        return _error(400, "invalid_arena_decision", str(error))
    except ArenaMutationError as error:
        return _error(500, "arena_decision_failed", str(error))
    return JSONResponse(
        {
            "match_uid": result.match_uid,
            "winner_image_uid": result.winner_image_uid,
            "winner_rating": result.winner_rating,
            "loser_rating": result.loser_rating,
        }
    )


def _image_filter(
    scope: list[str],
    classification: str,
    model: str,
    checkpoint: str,
    set_key: str,
    *,
    minimum_rating_count: int = 0,
) -> ImageFilter:
    try:
        selected_classification = ImageClassification(classification)
    except ValueError as error:
        raise ImageQueryValidationError(
            f"unknown classification: {classification}"
        ) from error
    return ImageFilter(
        scopes=ScopeSelection(tuple(scope)),
        classification=selected_classification,
        model=model,
        checkpoint=checkpoint,
        set_key=set_key,
        minimum_rating_count=minimum_rating_count,
    )


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "trace_id": get_trace_id(),
            }
        },
    )
