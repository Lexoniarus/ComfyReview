"""JSON-only HTTP adapters for the ComfyReview V2 frontend."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    ArenaMutationError,
    ArenaQuery,
    ArenaValidationError,
    AssignCurationCommand,
    CurationMutationError,
    CurationValidationError,
    GenerationSamplerSettings,
    ImageClassification,
    ImageContextNotFoundError,
    ImageFilter,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
    InvalidOutputPathError,
    ManualPromptSelection,
    OutputImageReference,
    OutputPairNotFoundError,
    PlaygroundGenerationDraft,
    PromptComponent,
    PromptDraftOverrides,
    PromptSelectionCommand,
    PromptSelectionError,
    RecordArenaDecisionCommand,
    RenderedPrompt,
    ReviewMutationError,
    ReviewValidationError,
    ScopeSelection,
    SubmitReviewCommand,
)
from comfyreview.observability import get_trace_id
from services.output_file_service import OutputMutationError

router = APIRouter(prefix="/api/v2")
PromptKind = Literal[
    "character",
    "scene",
    "outfit",
    "pose",
    "expression",
    "lighting",
    "modifier",
]


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


class PlaygroundSelectionIntent(BaseModel):
    """Describe one explicit fixed, random or disabled prompt role."""

    kind: PromptKind
    mode: Literal["fixed", "random", "off"]
    component_uid: str | None = None


class PlaygroundDraftRequest(BaseModel):
    """Request one catalog-backed prompt draft without persistence."""

    selections: list[PlaygroundSelectionIntent]
    seed: int | None = None
    max_attempts: int = 200
    positive_override: str | None = None
    negative_override: str | None = None


class PlaygroundSamplerRequest(BaseModel):
    """Carry one explicit native sampler configuration."""

    seed: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


class PlaygroundGenerationRequest(BaseModel):
    """Submit one reviewed Playground draft by canonical revision IDs."""

    draft_uid: str
    character_component_uid: str
    positive_prompt: str
    negative_prompt: str
    revision_uids: list[str]
    draft_overridden: bool = False
    checkpoint: str
    sampler: PlaygroundSamplerRequest


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
        filters = _image_filter(
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
        return _error(400, "invalid_arena_query", str(error))
    if pair is None:
        return Response(status_code=204)
    return JSONResponse(
        {
            "left": container.image_responses.context(pair.left),
            "right": container.image_responses.context(pair.right),
        }
    )


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
        {"components": [_component_response(item) for item in components]}
    )


@router.get("/playground/capabilities")
def playground_capabilities(request: Request) -> JSONResponse:
    """Return cached-or-live native ComfyUI enum capabilities."""
    container = get_application_container(request)
    discovery = container.playground_discovery.discover()
    defaults = container.workflow_defaults.load("default-character", 1)
    return JSONResponse(
        {
            "checkpoints": discovery.checkpoints,
            "samplers": discovery.samplers,
            "schedulers": discovery.schedulers,
            "defaults": {
                "checkpoint": defaults.checkpoint,
                "seed": 1,
                "steps": defaults.sampler.steps,
                "cfg": defaults.sampler.cfg,
                "sampler": defaults.sampler.sampler,
                "scheduler": defaults.sampler.scheduler,
                "denoise": defaults.sampler.denoise,
            },
        }
    )


@router.post("/playground/drafts")
def prepare_playground_draft(
    request: Request,
    payload: PlaygroundDraftRequest,
) -> JSONResponse:
    """Prepare one reproducible draft from catalog selection intent."""
    try:
        command = _selection_command(payload)
        overrides = _draft_overrides(payload)
        draft = get_application_container(
            request
        ).playground_service.prepare_draft(
            command,
            overrides=overrides,
        )
    except PromptSelectionError as error:
        return _error(400, "invalid_playground_selection", str(error))
    return JSONResponse(
        {
            "components": [
                _component_response(component)
                for component in draft.selection.components
            ],
            "positive_prompt": draft.prompt.positive_text,
            "negative_prompt": draft.prompt.negative_text,
            "revision_uids": draft.prompt.revision_uids,
            "draft_overridden": draft.prompt.draft_overridden,
        }
    )


@router.post("/generations")
def submit_generation(
    request: Request,
    payload: PlaygroundGenerationRequest,
) -> JSONResponse:
    """Submit one reviewed Playground draft through GenerationService."""
    container = get_application_container(request)
    try:
        character = container.prompt_catalog_service.get_component(
            payload.character_component_uid
        )
        if character.kind != "character":
            raise PromptSelectionError(
                "character_component_uid must identify a character"
            )
        batch = container.playground_submission_service.submit(
            (
                PlaygroundGenerationDraft(
                    draft_uid=payload.draft_uid,
                    character_name=character.name,
                    prompt=RenderedPrompt(
                        positive_text=payload.positive_prompt,
                        negative_text=payload.negative_prompt,
                        notes="",
                        revision_uids=tuple(payload.revision_uids),
                        draft_overridden=payload.draft_overridden,
                    ),
                    checkpoint=payload.checkpoint,
                    sampler=GenerationSamplerSettings(
                        role="base_sampler",
                        seed=payload.sampler.seed,
                        steps=payload.sampler.steps,
                        cfg=payload.sampler.cfg,
                        sampler=payload.sampler.sampler,
                        scheduler=payload.sampler.scheduler,
                        denoise=payload.sampler.denoise,
                    ),
                    output_subdirectory=(
                        f"playground/{character.component_key}"
                    ),
                ),
            )
        )
    except (KeyError, PromptSelectionError) as error:
        return _error(400, "invalid_generation", str(error))
    if batch.failures:
        return _error(
            500,
            "generation_failed",
            batch.failures[0].message,
        )
    submission = batch.submissions[0]
    return JSONResponse(
        {
            "generation_uid": submission.generation_uid,
            "status": submission.status,
            "prompt_id": submission.prompt_id,
        },
        status_code=202,
    )


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


def _selection_command(
    payload: PlaygroundDraftRequest,
) -> PromptSelectionCommand:
    expected: tuple[PromptKind, ...] = (
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
        "lighting",
        "modifier",
    )
    by_kind = {selection.kind: selection for selection in payload.selections}
    if len(by_kind) != len(payload.selections) or set(by_kind) != set(
        expected
    ):
        raise PromptSelectionError(
            "selections must contain every prompt kind exactly once"
        )
    manual: list[ManualPromptSelection] = []
    disabled: list[str] = []
    character_uid = ""
    for kind in expected:
        selection = by_kind[kind]
        component_uid = str(selection.component_uid or "").strip()
        if selection.mode == "off":
            if kind == "character":
                raise PromptSelectionError(
                    "character selection cannot be disabled"
                )
            disabled.append(kind)
        elif selection.mode == "fixed":
            if not component_uid:
                raise PromptSelectionError(
                    f"fixed {kind} selection requires component_uid"
                )
            if kind == "character":
                character_uid = component_uid
            else:
                manual.append(ManualPromptSelection(kind, component_uid))
    return PromptSelectionCommand(
        character_component_uid=character_uid,
        manual_selections=tuple(manual),
        disabled_kinds=tuple(disabled),
        seed=payload.seed,
        max_attempts=payload.max_attempts,
    )


def _draft_overrides(
    payload: PlaygroundDraftRequest,
) -> PromptDraftOverrides | None:
    if payload.positive_override is None and payload.negative_override is None:
        return None
    return PromptDraftOverrides(
        positive_text=payload.positive_override,
        negative_text=payload.negative_override,
    )


def _component_response(component: PromptComponent) -> dict[str, object]:
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
