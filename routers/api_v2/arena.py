"""Canonical Arena V2 HTTP adapters."""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    ArenaMutationError,
    ArenaQuery,
    ArenaValidationError,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
    RecordArenaDecisionCommand,
)
from routers.api_v2.common import build_image_filter, error_response

router = APIRouter()


class ArenaDecisionRequest(BaseModel):
    """Accept one UID-only V2 Arena decision."""

    left_image_uid: str
    right_image_uid: str
    winner_side: Literal["left", "right"]


@router.get("/arena/pair")
def arena_pair(
    request: Request,
    scope: Annotated[list[str] | None, Query()] = None,
    classification: str = Query("all"),
    model: str = Query(""),
    checkpoint: str = Query(""),
    set_key: str = Query(""),
) -> Response:
    """Return the next UID-based Arena pair in one canonical scope."""
    container = get_application_container(request)
    try:
        filters = build_image_filter(
            scope or [],
            classification,
            model,
            checkpoint,
            set_key,
            minimum_rating_count=container.settings.minimum_runs,
        )
        pair = container.arena_service.next_pair(
            ArenaQuery(
                ImageQuery(
                    filters=filters,
                    order=ImageOrder.TOP,
                    limit=min(100, container.settings.pool_limit),
                )
            )
        )
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_arena_query", str(error))
    if pair is None:
        return Response(status_code=204)
    return JSONResponse(
        {
            "left": container.image_responses.context(pair.left),
            "right": container.image_responses.context(pair.right),
        }
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
        return error_response(400, "invalid_arena_decision", str(error))
    except ArenaMutationError as error:
        return error_response(500, "arena_decision_failed", str(error))
    return JSONResponse(
        {
            "match_uid": result.match_uid,
            "winner_image_uid": result.winner_image_uid,
            "winner_rating": result.winner_rating,
            "loser_rating": result.loser_rating,
            "promotion_pending": result.promotion_pending,
        }
    )
