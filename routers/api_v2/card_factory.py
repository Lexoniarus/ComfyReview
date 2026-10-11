"""Revision-safe HTTP adapter for complete Card groups, pool, and deck."""

from typing import Any

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.api.card_battler_presenters import CardFactoryResponseMapper
from comfyreview.application import (
    ContentLevel,
    ImageContextNotFoundError,
    ImageFilter,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
)
from comfyreview.application.card_battler_candidate_group_service import (
    CardCandidateSourceEligibilityError,
)
from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupNotFoundError,
)
from comfyreview.application.card_battler_card_pool import (
    CardPoolConflictError,
    CardPoolNotFoundError,
)
from comfyreview.application.card_battler_deck import (
    CardDeckConflictError,
    CardDeckNotFoundError,
)
from comfyreview.application.card_battler_model import CardBattlerModelError
from routers.api_v2.common import error_response

router = APIRouter()


class CreateCardCandidateGroupRequest(BaseModel):
    """Select one canonical source for a new four-Card analysis."""

    model_config = ConfigDict(extra="forbid")

    image_uid: str = Field(min_length=1)


class CardMutationRequest(BaseModel):
    """Carry the exact aggregate revision expected by one mutation."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int = Field(gt=0)


class ReorderCardDeckRequest(CardMutationRequest):
    """Carry one complete ordered deck membership permutation."""

    card_ids: tuple[str, ...] = Field(max_length=40)


@router.get("/card-factory/sources")
def list_card_sources(
    request: Request,
    offset: int = Query(0),
    limit: int = Query(48),
) -> JSONResponse:
    """Return live canonical STANDARD images through the shared query."""
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


@router.get("/card-factory/candidate-groups")
def list_candidate_groups(request: Request) -> JSONResponse:
    """Return all persisted group summaries and current slot progress."""
    container = get_application_container(request)
    services = container.card_factory_runtime.get()
    mapper = _mapper(container, services.outputs)
    return JSONResponse(
        {
            "items": [
                mapper.group(group) for group in services.groups.list_groups()
            ]
        }
    )


@router.post("/card-factory/candidate-groups")
def create_candidate_group(
    request: Request,
    payload: CreateCardCandidateGroupRequest,
) -> JSONResponse:
    """Reserve one initial group; the owned worker performs external work."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        group = services.initial_groups.reserve(payload.image_uid)
    except ImageContextNotFoundError as error:
        return error_response(404, "card_source_not_found", str(error))
    except CardCandidateSourceEligibilityError as error:
        return error_response(422, "card_source_ineligible", str(error))
    except CardBattlerModelError as error:
        return error_response(503, "card_model_unavailable", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).group(group),
        status_code=202,
    )


@router.get("/card-factory/candidate-groups/{group_id}")
def candidate_group(request: Request, group_id: str) -> JSONResponse:
    """Return one complete Candidate group projection."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        group = services.groups.get(group_id)
    except CardCandidateGroupNotFoundError as error:
        return error_response(
            404, "card_candidate_group_not_found", str(error)
        )
    return JSONResponse(_mapper(container, services.outputs).group(group))


@router.post("/card-factory/candidate-groups/{group_id}/reject")
def reject_candidate_group(
    request: Request,
    group_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Reject one terminal group without changing a confirmed Card."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        group = services.groups.reject(
            group_id,
            expected_revision=payload.expected_revision,
        )
    except CardCandidateGroupNotFoundError as error:
        return error_response(
            404, "card_candidate_group_not_found", str(error)
        )
    except CardCandidateGroupConflictError as error:
        return error_response(409, "card_candidate_group_conflict", str(error))
    return JSONResponse(_mapper(container, services.outputs).group(group))


@router.post("/card-factory/candidate-groups/{group_id}/retry")
def retry_initial_candidate_group(
    request: Request,
    group_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Discard one initial set and reserve a fully new source analysis."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        group = services.groups.retry_initial(
            group_id,
            expected_revision=payload.expected_revision,
        )
    except CardCandidateGroupNotFoundError as error:
        return error_response(
            404, "card_candidate_group_not_found", str(error)
        )
    except CardCandidateGroupConflictError as error:
        return error_response(409, "card_candidate_group_conflict", str(error))
    except CardCandidateSourceEligibilityError as error:
        return error_response(422, "card_source_ineligible", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).group(group),
        status_code=202,
    )


@router.post(
    "/card-factory/candidate-groups/{group_id}/"
    "candidates/{candidate_id}/accept"
)
def accept_card_candidate(
    request: Request,
    group_id: str,
    candidate_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Accept a completed initial or development Candidate by CAS."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        card = services.acceptance.accept(
            group_id,
            candidate_id,
            expected_revision=payload.expected_revision,
        )
    except CardPoolNotFoundError as error:
        return error_response(404, "card_candidate_not_found", str(error))
    except CardPoolConflictError as error:
        return error_response(409, "card_candidate_conflict", str(error))
    return JSONResponse(_mapper(container, services.outputs).card(card))


@router.get("/card-factory/cards")
def list_pool_cards(request: Request) -> JSONResponse:
    """Return every current Card in the unbounded POC pool."""
    container = get_application_container(request)
    services = container.card_factory_runtime.get()
    mapper = _mapper(container, services.outputs)
    return JSONResponse(
        {"items": [mapper.card(card) for card in services.cards.list_cards()]}
    )


@router.get("/card-factory/cards/{card_id}")
def pool_card(request: Request, card_id: str) -> JSONResponse:
    """Return one current confirmed Card."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        card = services.cards.get(card_id)
    except CardPoolNotFoundError as error:
        return error_response(404, "card_not_found", str(error))
    return JSONResponse(_mapper(container, services.outputs).card(card))


@router.post("/card-factory/cards/{card_id}/development-groups")
def create_development_group(
    request: Request,
    card_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Reserve four one-tier development Candidates for a current Card."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        group = services.development_groups.reserve(
            card_id,
            expected_revision=payload.expected_revision,
        )
    except CardPoolNotFoundError as error:
        return error_response(404, "card_not_found", str(error))
    except CardPoolConflictError as error:
        return error_response(409, "card_development_conflict", str(error))
    return JSONResponse(
        _mapper(container, services.outputs).group(group),
        status_code=202,
    )


@router.get("/card-factory/deck")
def card_deck(request: Request) -> JSONResponse:
    """Return the one POC deck together with the available Card pool."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        deck = services.deck.get()
        cards = services.cards.list_cards()
    except CardDeckNotFoundError as error:
        return error_response(404, "card_deck_not_found", str(error))
    mapper = _mapper(container, services.outputs)
    return JSONResponse(
        {
            "deck": mapper.deck(deck, cards),
            "pool": [mapper.card(card) for card in cards],
        }
    )


@router.post("/card-factory/deck/cards/{card_id}")
def add_deck_card(
    request: Request,
    card_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Append one unique pool Card to the POC deck by CAS."""
    return _mutate_deck(request, "add", card_id, payload.expected_revision)


@router.delete("/card-factory/deck/cards/{card_id}")
def remove_deck_card(
    request: Request,
    card_id: str,
    payload: CardMutationRequest,
) -> JSONResponse:
    """Remove one Card from the POC deck by CAS."""
    return _mutate_deck(request, "remove", card_id, payload.expected_revision)


@router.put("/card-factory/deck/order")
def reorder_card_deck(
    request: Request,
    payload: ReorderCardDeckRequest,
) -> JSONResponse:
    """Replace the complete POC deck order by CAS."""
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        deck = services.deck.reorder(
            payload.card_ids,
            expected_revision=payload.expected_revision,
        )
        cards = services.cards.list_cards()
    except CardDeckNotFoundError as error:
        return error_response(404, "card_deck_not_found", str(error))
    except CardDeckConflictError as error:
        return error_response(409, "card_deck_conflict", str(error))
    return JSONResponse(_mapper(container, services.outputs).deck(deck, cards))


def _mutate_deck(
    request: Request,
    operation: str,
    card_id: str,
    expected_revision: int,
) -> JSONResponse:
    container = get_application_container(request)
    try:
        services = container.card_factory_runtime.get()
        command = (
            services.deck.add if operation == "add" else services.deck.remove
        )
        deck = command(card_id, expected_revision=expected_revision)
        cards = services.cards.list_cards()
    except CardDeckNotFoundError as error:
        return error_response(404, "card_or_deck_not_found", str(error))
    except CardDeckConflictError as error:
        return error_response(409, "card_deck_conflict", str(error))
    return JSONResponse(_mapper(container, services.outputs).deck(deck, cards))


def _mapper(container: Any, outputs: Any) -> CardFactoryResponseMapper:
    return CardFactoryResponseMapper(
        canonical_images=container.image_responses,
        card_outputs=outputs,
        file_urls=container.file_urls,
    )
