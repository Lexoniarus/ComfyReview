"""Canonical image-context and ranking V2 HTTP adapters."""

from typing import Annotated

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict

from comfyreview.api import get_application_container
from comfyreview.application import (
    ContentClassificationError,
    ContentLevel,
    ImageContextNotFoundError,
    ImageLoraSnapshot,
    ImageOrder,
    ImageQuery,
    ImageQueryValidationError,
)
from routers.api_v2.common import build_image_filter, error_response

router = APIRouter()


class ImageContentLevelRequest(BaseModel):
    """Set one explicit content level or return to inferred policy."""

    model_config = ConfigDict(extra="forbid")

    content_level: ContentLevel | None


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
            minimum_rating_count=1,
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


@router.get("/images/{image_uid}/generator-handoff")
def image_generator_handoff(request: Request, image_uid: str) -> JSONResponse:
    """Return independently stageable prompt and render facts."""
    try:
        handoff = get_application_container(
            request
        ).image_generator_handoffs.get(image_uid)
    except ImageQueryValidationError as error:
        return error_response(400, "invalid_image_uid", str(error))
    except (ImageContextNotFoundError, LookupError) as error:
        return error_response(404, "image_handoff_not_found", str(error))
    prompt = handoff.prompt_setup
    render = handoff.render_setup
    return JSONResponse(
        {
            "image_uid": handoff.image_uid,
            "generation_uid": handoff.generation_uid,
            "prompt_setup": {
                "source_image_uid": prompt.source_image_uid,
                "availability": prompt.availability,
                "component_uids": prompt.component_uids,
                "revision_uids": prompt.revision_uids,
                "positive_atoms": [
                    {"text": atom.text, "weight": atom.weight}
                    for atom in prompt.positive_atoms
                ],
                "negative_atoms": [
                    {"text": atom.text, "weight": atom.weight}
                    for atom in prompt.negative_atoms
                ],
                "draft_overridden": prompt.draft_overridden,
                "loras": [_lora_handoff(item) for item in prompt.loras],
                "issues": prompt.issues,
            },
            "render_setup": {
                "applicable": render.applicable,
                "checkpoint": render.checkpoint,
                "sampler_stages": [
                    {
                        "role": stage.role,
                        "order": stage.order,
                        "seed": stage.seed,
                        "steps": stage.steps,
                        "cfg": stage.cfg,
                        "sampler": stage.sampler,
                        "scheduler": stage.scheduler,
                        "denoise": stage.denoise,
                    }
                    for stage in render.sampler_stages
                ],
                "seed": render.seed,
                "aspect_format": render.aspect_format,
                "resolution_class": render.resolution_class,
                "actual_width": render.actual_width,
                "actual_height": render.actual_height,
                "target_width": render.target_width,
                "target_height": render.target_height,
                "geometry_match": render.geometry_match,
                "issues": render.issues,
            },
        }
    )


def _lora_handoff(item: ImageLoraSnapshot) -> dict[str, object]:
    return {
        "lora_uid": item.lora_uid,
        "revision_uid": item.revision_uid,
        "provider_name": item.provider_name,
        "position": item.position,
        "model_strength": item.model_strength_milli / 1000,
        "clip_strength": item.clip_strength_milli / 1000,
        "content_level": item.content_level,
        "model_effective": item.model_effective,
        "clip_effective": item.clip_effective,
    }


@router.put("/images/{image_uid}/content-level")
def set_image_content_level(
    request: Request,
    image_uid: str,
    payload: ImageContentLevelRequest,
) -> JSONResponse:
    """Append one manual image classification and update its projection."""
    try:
        result = get_application_container(
            request
        ).image_content_levels.set_level(image_uid, payload.content_level)
    except ContentClassificationError as error:
        return error_response(404, "image_not_found", str(error))
    return JSONResponse(
        {
            "inferred_level": result.inferred_level.value,
            "effective_level": result.effective_level.value,
            "override_level": (
                result.override_level.value
                if result.override_level is not None
                else None
            ),
        }
    )
