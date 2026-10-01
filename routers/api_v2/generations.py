"""Canonical generation-intent V2 HTTP adapter."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from comfyreview.api import get_application_container
from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    ConfirmPlaygroundDraftCommand,
    GenerationDetail,
    GenerationMutationError,
    GenerationNotFoundError,
    GenerationQueryValidationError,
    GenerationSamplerSettings,
    GenerationSummary,
    GenerationValidationError,
    PlaygroundGenerationDraft,
    PromptSelectionError,
)
from routers.api_v2.common import error_response

router = APIRouter()


class PlaygroundSamplerRequest(BaseModel):
    """Carry one explicit native sampler configuration."""

    model_config = ConfigDict(extra="forbid")

    seed: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


class PlaygroundGenerationRequest(BaseModel):
    """Submit reviewed domain intent without workflow graph semantics."""

    model_config = ConfigDict(extra="forbid")

    draft_uid: str
    component_uids: list[str]
    positive_prompt: str
    negative_prompt: str
    checkpoint: str
    sampler: PlaygroundSamplerRequest


class GenerationReconcileRequest(BaseModel):
    """Supply an optional externally recovered ComfyUI prompt identity."""

    prompt_id: str | None = None


@router.get("/generations")
def list_generations(
    request: Request,
    status: str = "",
    offset: int = 0,
    limit: int = 48,
) -> JSONResponse:
    """Return persisted generation lifecycle entries, not queue jobs."""
    container = get_application_container(request)
    try:
        page = container.generation_queries.list_generations(
            status=status,
            offset=offset,
            limit=limit,
        )
    except GenerationQueryValidationError as error:
        return error_response(400, "invalid_generation_query", str(error))
    return JSONResponse(
        {
            "items": [summary_response(item) for item in page.entries],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
        }
    )


@router.get("/generations/{generation_uid}")
def generation_detail(
    request: Request,
    generation_uid: str,
) -> JSONResponse:
    """Return one reproducible generation and every canonical output."""
    container = get_application_container(request)
    try:
        generation = container.generation_queries.get_generation(
            generation_uid
        )
    except GenerationQueryValidationError as error:
        return error_response(400, "invalid_generation_uid", str(error))
    except GenerationNotFoundError as error:
        return error_response(404, "generation_not_found", str(error))
    return JSONResponse(detail_response(generation, container.image_responses))


@router.post("/generations/{generation_uid}/reconcile")
def reconcile_generation(
    request: Request,
    generation_uid: str,
    payload: GenerationReconcileRequest,
) -> JSONResponse:
    """Reconcile existing lifecycle state without resubmitting work."""
    try:
        result = get_application_container(
            request
        ).generation_reconciliation.reconcile(
            generation_uid,
            prompt_id=payload.prompt_id,
        )
    except (GenerationValidationError, KeyError) as error:
        return error_response(400, "invalid_reconciliation", str(error))
    except GenerationMutationError as error:
        return error_response(500, "reconciliation_failed", str(error))
    return JSONResponse(
        {
            "generation_uid": result.generation_uid,
            "status": result.status,
            "prompt_id": result.prompt_id,
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
        confirmed = container.playground_service.confirm_draft(
            ConfirmPlaygroundDraftCommand(
                component_uids=tuple(payload.component_uids),
                positive_prompt=payload.positive_prompt,
                negative_prompt=payload.negative_prompt,
            )
        )
        character = next(
            component
            for component in confirmed.selection.components
            if component.kind == "character"
        )
        batch = container.playground_submission_service.submit(
            (
                PlaygroundGenerationDraft(
                    draft_uid=payload.draft_uid,
                    character_name=character.name,
                    prompt=confirmed.prompt,
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
    except (KeyError, PromptSelectionError, StopIteration) as error:
        return error_response(400, "invalid_generation", str(error))
    if batch.failures:
        return error_response(
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


def summary_response(generation: GenerationSummary) -> dict[str, object]:
    """Map one canonical lifecycle summary to snake-case JSON."""
    return {
        "generation_uid": generation.generation_uid,
        "status": generation.status,
        "prompt_id": generation.prompt_id,
        "source": generation.source,
        "model": generation.model,
        "checkpoint": generation.checkpoint,
        "blueprint_uid": generation.blueprint_uid,
        "blueprint_version": generation.blueprint_version,
        "graph_hash": generation.graph_hash,
        "created_at": generation.created_at,
        "submitted_at": generation.submitted_at,
        "started_at": generation.started_at,
        "completed_at": generation.completed_at,
        "output_count": generation.output_count,
    }


def detail_response(
    generation: GenerationDetail,
    image_responses: ImageResponseMapper,
) -> dict[str, object]:
    """Map generation provenance and add output URLs at the HTTP boundary."""
    return {
        **summary_response(generation.summary),
        "positive_prompt": generation.positive_prompt,
        "negative_prompt": generation.negative_prompt,
        "revision_uids": generation.revision_uids,
        "sampler_stages": [
            {
                "role": stage.role,
                "node_id": stage.node_id,
                "order": stage.order,
                "seed": stage.seed,
                "steps": stage.steps,
                "cfg": stage.cfg,
                "sampler": stage.sampler,
                "scheduler": stage.scheduler,
                "denoise": stage.denoise,
            }
            for stage in generation.sampler_stages
        ],
        "outputs": [
            {
                "image_uid": output.image_uid,
                "role": output.role,
                "node_id": output.node_id,
                "output_index": output.output_index,
                "content_hash": output.content_hash,
                "image_url": image_responses.image_url(output.image_uid),
            }
            for output in generation.outputs
        ],
    }
