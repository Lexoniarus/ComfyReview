"""Canonical generation-intent V2 HTTP adapter."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.api.v2_presenters import ImageResponseMapper
from comfyreview.application import (
    ConfirmPlaygroundDraftCommand,
    GenerationDetail,
    GenerationLoraSelection,
    GenerationMutationError,
    GenerationNotFoundError,
    GenerationQueryValidationError,
    GenerationSamplerSettings,
    GenerationSummary,
    GenerationValidationError,
    PlaygroundGenerationDraft,
    PlaygroundGenerationSweep,
    PromptCatalogValidationError,
    PromptSelectionError,
)
from routers.api_v2.catalog import PromptAtomRequest, atom_usages
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
    batch_runs: int = 1
    randomize_seed: bool = False
    steps_max: int | None = None
    cfg_max: float | None = None
    cfg_step: float = 0.1


class GenerationLoraRequest(BaseModel):
    """Carry one ordered LoRA selection without workflow semantics."""

    model_config = ConfigDict(extra="forbid")

    name: str
    model_strength: float = 1.0
    clip_strength: float = 1.0


class PlaygroundGenerationRequest(BaseModel):
    """Submit reviewed domain intent without workflow graph semantics."""

    model_config = ConfigDict(extra="forbid")

    draft_uid: str
    component_uids: list[str]
    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]
    checkpoint: str
    blueprint_uid: str = "default-character"
    blueprint_version: int = 3
    image_width: int = 1024
    image_height: int = 1024
    sampler: PlaygroundSamplerRequest
    loras: list[GenerationLoraRequest] = Field(default_factory=list)


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
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
            )
        )
        character = next(
            component
            for component in confirmed.selection.components
            if component.kind == "character"
        )
        draft = PlaygroundGenerationDraft(
            draft_uid=payload.draft_uid,
            character_name=character.name,
            prompt=confirmed.prompt,
            checkpoint=payload.checkpoint,
            blueprint_uid=payload.blueprint_uid,
            blueprint_version=payload.blueprint_version,
            image_width=payload.image_width,
            image_height=payload.image_height,
            sampler=GenerationSamplerSettings(
                role="base_sampler",
                seed=payload.sampler.seed,
                steps=payload.sampler.steps,
                cfg=payload.sampler.cfg,
                sampler=payload.sampler.sampler,
                scheduler=payload.sampler.scheduler,
                denoise=payload.sampler.denoise,
            ),
            output_subdirectory=f"playground/{character.component_key}",
            loras=tuple(
                GenerationLoraSelection(
                    name=item.name,
                    model_strength_milli=round(item.model_strength * 1000),
                    clip_strength_milli=round(item.clip_strength * 1000),
                    position=position,
                )
                for position, item in enumerate(payload.loras)
            ),
        )
        drafts = container.playground_generation_sweeps.expand(
            draft,
            PlaygroundGenerationSweep(
                batch_runs=payload.sampler.batch_runs,
                randomize_seed=payload.sampler.randomize_seed,
                steps_max=payload.sampler.steps_max or payload.sampler.steps,
                cfg_max=(
                    payload.sampler.cfg
                    if payload.sampler.cfg_max is None
                    else payload.sampler.cfg_max
                ),
                cfg_step=payload.sampler.cfg_step,
            ),
        )
        batch = container.playground_submission_service.submit(drafts)
    except (
        GenerationValidationError,
        KeyError,
        PromptSelectionError,
        PromptCatalogValidationError,
        StopIteration,
    ) as error:
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
            "submissions": [
                {
                    "generation_uid": item.generation_uid,
                    "status": item.status,
                    "prompt_id": item.prompt_id,
                }
                for item in batch.submissions
            ],
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
