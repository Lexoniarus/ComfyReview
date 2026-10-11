"""Revision-safe Card Factory prototype HTTP adapter."""

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.api.card_battler_presenters import (
    CardFactorySessionResponseMapper,
)
from comfyreview.application import (
    CardSessionCapacityError,
    CardSessionConflictError,
    CardSessionDevelopmentLockedError,
    CardSessionNotFoundError,
    CardSourceEligibilityError,
    ContentLevel,
    ImageContextNotFoundError,
    ImageFilter,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
    LocalModelConnectionError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
    SemanticImageAnalysisError,
)
from comfyreview.application.card_battler_development import (
    CardDevelopmentPlanningError,
)
from comfyreview.application.card_battler_model import CardBattlerModelError
from routers.api_v2.common import error_response

router = APIRouter()


class CreateCardSessionRequest(BaseModel):
    """Select one canonical source image for initial analysis."""

    model_config = ConfigDict(extra="forbid")

    image_uid: str = Field(min_length=1)


class CardSessionMutationRequest(BaseModel):
    """Carry the exact revision expected by one mutation."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(gt=0)


@router.get("/card-factory/sources")
def list_card_sources(
    request: Request,
    offset: int = Query(0),
    limit: int = Query(48),
) -> JSONResponse:
    """Return live canonical STANDARD images using the shared SQL query."""
    container = get_application_container(request)
    try:
        page = container.image_contexts.list_images(
            ImageQuery(
                filters=ImageFilter(
                    effective_content_level=ContentLevel.STANDARD
                ),
                order=ImageOrder.RECENT,
                offset=offset,
                limit=limit,
            )
        )
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_card_source_query", str(error))
    return JSONResponse(
        {
            "items": [
                {
                    **container.image_responses.summary(item),
                    "image_url": container.image_responses.image_url(
                        item.image_uid
                    ),
                }
                for item in page.entries
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
        }
    )


@router.post("/card-factory/sessions")
def create_card_session(
    request: Request,
    payload: CreateCardSessionRequest,
) -> JSONResponse:
    """Analyze one source exactly once and persist its initial Card session."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        snapshot = services.prototype.create(payload.image_uid)
    except ImageContextNotFoundError as error:
        return error_response(404, "card_source_not_found", str(error))
    except CardSourceEligibilityError as error:
        return error_response(422, "card_source_ineligible", str(error))
    except CardSessionCapacityError as error:
        return error_response(409, "card_session_capacity", str(error))
    except (LocalModelConnectionError, LocalModelTimeoutError) as error:
        return error_response(503, "local_model_unavailable", str(error))
    except LocalModelUnavailableError as error:
        return error_response(503, "local_model_missing", str(error))
    except (
        LocalModelProtocolError,
        SemanticImageAnalysisError,
    ) as error:
        return error_response(502, "semantic_analysis_failed", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).snapshot(snapshot), 201
    )


@router.get("/card-factory/sessions/{session_id}")
def card_session(request: Request, session_id: str) -> JSONResponse:
    """Synchronize once and return all inspectable session artifacts."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        snapshot = services.prototype.get(session_id)
    except CardSessionNotFoundError as error:
        return error_response(404, "card_session_not_found", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).snapshot(snapshot)
    )


@router.post("/card-factory/sessions/{session_id}/develop")
def develop_card_session(
    request: Request,
    session_id: str,
    payload: CardSessionMutationRequest,
) -> JSONResponse:
    """Advance exactly one accepted tier using compare-and-swap."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        snapshot = services.prototype.develop(
            session_id,
            expected_revision=payload.expected_revision,
        )
    except CardSessionNotFoundError as error:
        return error_response(404, "card_session_not_found", str(error))
    except (
        CardDevelopmentPlanningError,
        CardSessionConflictError,
        CardSessionDevelopmentLockedError,
    ) as error:
        return error_response(409, "card_development_conflict", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).snapshot(snapshot)
    )


@router.post("/card-factory/sessions/{session_id}/candidates")
def generate_card_candidates(
    request: Request,
    session_id: str,
    payload: CardSessionMutationRequest,
) -> JSONResponse:
    """Reserve and submit four independently visible Card candidates."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        snapshot = services.prototype.generate_candidates(
            session_id,
            expected_revision=payload.expected_revision,
        )
    except KeyError as error:
        return error_response(404, "card_session_not_found", str(error))
    except CardSessionConflictError as error:
        return error_response(409, "card_generation_conflict", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).snapshot(snapshot),
        status_code=202,
    )


@router.post(
    "/card-factory/sessions/{session_id}/candidates/{candidate_id}/accept"
)
def accept_card_candidate(
    request: Request,
    session_id: str,
    candidate_id: str,
    payload: CardSessionMutationRequest,
) -> JSONResponse:
    """Accept one completed current slot using compare-and-swap."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        snapshot = services.prototype.accept_candidate(
            session_id,
            candidate_id,
            expected_revision=payload.expected_revision,
        )
    except KeyError as error:
        return error_response(404, "card_candidate_not_found", str(error))
    except CardSessionConflictError as error:
        return error_response(409, "card_candidate_conflict", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).snapshot(snapshot)
    )


def _mapper(container: Any, outputs: Any) -> CardFactorySessionResponseMapper:
    return CardFactorySessionResponseMapper(
        canonical_images=container.image_responses,
        card_outputs=outputs,
        file_urls=container.file_urls,
    )
