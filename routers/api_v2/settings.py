"""Typed V2 adapters for workspace settings and runtime diagnostics."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    ContentClassificationError,
    ContentLevel,
    LoraDefinition,
    LoraReclassificationImpact,
    RuntimeDiagnostics,
    WorkspacePreferences,
    WorkspaceSettingsValidationError,
)
from routers.api_v2.common import error_response

router = APIRouter()


class WorkspacePreferencesRequest(BaseModel):
    """Replace mutable browser-facing workspace preferences."""

    model_config = ConfigDict(extra="forbid")

    density: str
    motion: str
    analytics_page_size: int
    review_prioritize_unrated: bool
    default_curation_set_key: str | None = None
    curation_set_order: list[str] = Field(default_factory=list)
    enabled_content_levels: list[ContentLevel] = Field(
        default_factory=lambda: [ContentLevel.STANDARD]
    )


class LoraClassificationRequest(BaseModel):
    """Assign a workspace-wide content level to one ComfyUI LoRA."""

    model_config = ConfigDict(extra="forbid")

    provider_name: str
    content_level: ContentLevel


class LoraReclassificationRequest(BaseModel):
    """Apply one previously previewed LoRA revision to history."""

    model_config = ConfigDict(extra="forbid")

    expected_revision: int


@router.get("/settings")
def settings(request: Request) -> JSONResponse:
    """Return preferences and safe read-only runtime diagnostics."""
    container = get_application_container(request)
    diagnostics = container.runtime_diagnostics.snapshot()
    lora_catalog = getattr(container, "lora_catalog", None)
    return JSONResponse(
        {
            "preferences": preferences_response(
                container.workspace_preferences.get()
            ),
            "curation_set_keys": list(container.settings.curation_set_keys),
            "runtime": diagnostics_response(diagnostics),
            "lora_definitions": [
                lora_definition_response(item)
                for item in (
                    lora_catalog.list_definitions() if lora_catalog else ()
                )
            ],
        }
    )


@router.put("/settings/preferences")
def update_preferences(
    request: Request,
    payload: WorkspacePreferencesRequest,
) -> JSONResponse:
    """Validate and replace workspace preferences."""
    try:
        preferences = get_application_container(
            request
        ).workspace_preferences.update(
            WorkspacePreferences(
                density=payload.density,
                motion=payload.motion,
                analytics_page_size=payload.analytics_page_size,
                default_generation_profile_uid=None,
                review_prioritize_unrated=(payload.review_prioritize_unrated),
                default_curation_set_key=payload.default_curation_set_key,
                curation_set_order=tuple(payload.curation_set_order),
                enabled_content_levels=tuple(payload.enabled_content_levels),
            )
        )
    except (WorkspaceSettingsValidationError, KeyError) as error:
        return error_response(400, "invalid_preferences", str(error))
    return JSONResponse(preferences_response(preferences))


@router.post("/settings/comfyui/check")
def check_comfyui(request: Request) -> JSONResponse:
    """Run one explicit bounded ComfyUI connection check."""
    diagnostics = get_application_container(
        request
    ).runtime_diagnostics.inspect()
    return JSONResponse(diagnostics_response(diagnostics))


@router.post("/settings/loras/classify")
def classify_lora(
    request: Request, payload: LoraClassificationRequest
) -> JSONResponse:
    """Create or revise one canonical LoRA content policy."""
    try:
        definition = get_application_container(request).lora_catalog.classify(
            payload.provider_name, payload.content_level
        )
    except ContentClassificationError as error:
        return error_response(400, "invalid_lora_classification", str(error))
    return JSONResponse(lora_definition_response(definition))


@router.get("/settings/loras/{lora_uid}/reclassification-impact")
def lora_reclassification_impact(
    request: Request, lora_uid: str
) -> JSONResponse:
    """Preview the historical rows affected by one LoRA policy."""
    try:
        impact = get_application_container(request).lora_catalog.preview(
            lora_uid
        )
    except ContentClassificationError as error:
        return error_response(404, "lora_not_found", str(error))
    return JSONResponse(lora_impact_response(impact))


@router.post("/settings/loras/{lora_uid}/reclassify")
def reclassify_lora_history(
    request: Request,
    lora_uid: str,
    payload: LoraReclassificationRequest,
) -> JSONResponse:
    """Explicitly apply a previewed LoRA revision to historical snapshots."""
    try:
        impact = get_application_container(request).lora_catalog.reclassify(
            lora_uid, payload.expected_revision
        )
    except ContentClassificationError as error:
        return error_response(409, "stale_lora_reclassification", str(error))
    return JSONResponse(lora_impact_response(impact))


@router.get("/generation-capabilities")
def generation_capabilities(request: Request) -> JSONResponse:
    """Return native enum capabilities for generation editors."""
    diagnostics = get_application_container(
        request
    ).runtime_diagnostics.inspect()
    return JSONResponse(
        {
            "connected": diagnostics.connected,
            "checkpoints": list(diagnostics.checkpoints),
            "samplers": list(diagnostics.samplers),
            "schedulers": list(diagnostics.schedulers),
            "loras": list(diagnostics.loras),
            "upscale_models": list(diagnostics.upscale_models),
        }
    )


def preferences_response(
    preferences: WorkspacePreferences,
) -> dict[str, object]:
    """Map workspace preferences to snake-case JSON."""
    return {
        "density": preferences.density,
        "motion": preferences.motion,
        "analytics_page_size": preferences.analytics_page_size,
        "review_prioritize_unrated": (preferences.review_prioritize_unrated),
        "default_curation_set_key": preferences.default_curation_set_key,
        "curation_set_order": list(preferences.curation_set_order),
        "enabled_content_levels": [
            level.value for level in preferences.enabled_content_levels
        ],
    }


def diagnostics_response(diagnostics: RuntimeDiagnostics) -> dict[str, object]:
    """Map typed runtime diagnostics without exposing writable secrets."""
    configuration = diagnostics.configuration
    return {
        "connected": diagnostics.connected,
        "message": diagnostics.message,
        "node_classes": list(diagnostics.node_classes),
        "checkpoints": list(diagnostics.checkpoints),
        "samplers": list(diagnostics.samplers),
        "schedulers": list(diagnostics.schedulers),
        "loras": list(diagnostics.loras),
        "upscale_models": list(diagnostics.upscale_models),
        "configuration": {
            "comfyui_base_url": configuration.comfyui_base_url,
            "output_root": configuration.output_root,
            "workflows_directory": configuration.workflows_directory,
            "canonical_database_path": configuration.canonical_database_path,
            "schema_version": configuration.schema_version,
            "runtime_mode": configuration.runtime_mode,
            "environment_variables": list(configuration.environment_variables),
        },
    }


def lora_definition_response(
    definition: LoraDefinition,
) -> dict[str, object]:
    """Map one typed LoRA definition without exposing persistence details."""
    return {
        "lora_uid": definition.lora_uid,
        "provider_name": definition.provider_name,
        "content_level": (
            definition.content_level.value
            if definition.content_level is not None
            else None
        ),
        "revision": definition.revision,
    }


def lora_impact_response(
    impact: LoraReclassificationImpact,
) -> dict[str, object]:
    """Map one historical reclassification preview/result."""
    return {
        "lora_uid": impact.lora_uid,
        "revision": impact.revision,
        "generation_count": impact.generation_count,
        "image_count": impact.image_count,
        "manual_override_count": impact.manual_override_count,
    }
