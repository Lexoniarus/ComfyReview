"""Canonical generation-intent V2 HTTP adapter."""

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from comfyreview.api import get_application_container
from comfyreview.application import (
    ConfirmPlaygroundDraftCommand,
    GenerationSamplerSettings,
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
