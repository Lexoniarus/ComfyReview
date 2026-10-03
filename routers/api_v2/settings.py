"""Typed V2 adapters for workspace settings and generation profiles."""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    ContentLevel,
    GenerationLoraSelection,
    GenerationProfile,
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
    default_generation_profile_uid: str | None = None
    review_unrated_only: bool
    review_max_attempts: int
    default_curation_set_key: str | None = None
    curation_set_order: list[str] = Field(default_factory=list)
    enabled_content_levels: list[ContentLevel] = Field(
        default_factory=lambda: [ContentLevel.STANDARD]
    )


class ProfileLoraRequest(BaseModel):
    """Carry one ordered LoRA in a generation profile."""

    model_config = ConfigDict(extra="forbid")

    name: str
    model_strength: float
    clip_strength: float


class GenerationProfileRequest(BaseModel):
    """Carry editable generation defaults without workflow graph data."""

    model_config = ConfigDict(extra="forbid")

    name: str
    blueprint_uid: str = "default-character"
    blueprint_version: int = 3
    checkpoint: str
    sampler: str
    scheduler: str
    seed_mode: str
    fixed_seed: int | None = None
    steps_min: int
    steps_max: int
    cfg_min: float
    cfg_max: float
    denoise: float
    batch_size: int
    image_width: int = 1024
    image_height: int = 1024
    loras: list[ProfileLoraRequest] = Field(default_factory=list)


class ArchiveProfileRequest(BaseModel):
    """Change one profile lifecycle flag."""

    archived: bool


@router.get("/settings")
def settings(request: Request) -> JSONResponse:
    """Return preferences, profiles and safe read-only runtime diagnostics."""
    container = get_application_container(request)
    diagnostics = container.runtime_diagnostics.snapshot()
    return JSONResponse(
        {
            "preferences": preferences_response(
                container.workspace_preferences.get()
            ),
            "generation_profiles": [
                profile_response(profile)
                for profile in container.generation_profiles.list_profiles()
            ],
            "curation_set_keys": list(container.settings.curation_set_keys),
            "runtime": diagnostics_response(diagnostics),
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
                default_generation_profile_uid=(
                    payload.default_generation_profile_uid
                ),
                review_unrated_only=payload.review_unrated_only,
                review_max_attempts=payload.review_max_attempts,
                default_curation_set_key=payload.default_curation_set_key,
                curation_set_order=tuple(payload.curation_set_order),
                enabled_content_levels=tuple(payload.enabled_content_levels),
            )
        )
    except (WorkspaceSettingsValidationError, KeyError) as error:
        return error_response(400, "invalid_preferences", str(error))
    return JSONResponse(preferences_response(preferences))


@router.get("/settings/generation-profiles")
def list_generation_profiles(request: Request) -> JSONResponse:
    """Return every active and archived generation profile."""
    profiles = get_application_container(
        request
    ).generation_profiles.list_profiles()
    return JSONResponse(
        {"items": [profile_response(item) for item in profiles]}
    )


@router.post("/settings/generation-profiles", status_code=201)
def create_generation_profile(
    request: Request,
    payload: GenerationProfileRequest,
) -> JSONResponse:
    """Create one server-identified generation profile."""
    try:
        profile = get_application_container(
            request
        ).generation_profiles.create(profile_value("", payload))
    except WorkspaceSettingsValidationError as error:
        return error_response(400, "invalid_generation_profile", str(error))
    return JSONResponse(profile_response(profile), status_code=201)


@router.put("/settings/generation-profiles/{profile_uid}")
def update_generation_profile(
    request: Request,
    profile_uid: str,
    payload: GenerationProfileRequest,
) -> JSONResponse:
    """Update one stable generation profile."""
    try:
        profile = get_application_container(
            request
        ).generation_profiles.update(profile_value(profile_uid, payload))
    except WorkspaceSettingsValidationError as error:
        return error_response(400, "invalid_generation_profile", str(error))
    except KeyError as error:
        return error_response(404, "generation_profile_not_found", str(error))
    return JSONResponse(profile_response(profile))


@router.patch("/settings/generation-profiles/{profile_uid}/archive")
def archive_generation_profile(
    request: Request,
    profile_uid: str,
    payload: ArchiveProfileRequest,
) -> JSONResponse:
    """Archive or restore one profile without deleting history."""
    try:
        profile = get_application_container(
            request
        ).generation_profiles.set_archived(profile_uid, payload.archived)
    except WorkspaceSettingsValidationError as error:
        return error_response(400, "invalid_generation_profile", str(error))
    except KeyError as error:
        return error_response(404, "generation_profile_not_found", str(error))
    return JSONResponse(profile_response(profile))


@router.put("/settings/generation-profiles/{profile_uid}/default")
def default_generation_profile(
    request: Request,
    profile_uid: str,
) -> JSONResponse:
    """Select one active generation profile as the default."""
    try:
        preferences = get_application_container(
            request
        ).workspace_preferences.set_default_profile(profile_uid)
    except WorkspaceSettingsValidationError as error:
        return error_response(400, "invalid_generation_profile", str(error))
    except KeyError as error:
        return error_response(404, "generation_profile_not_found", str(error))
    return JSONResponse(preferences_response(preferences))


@router.post("/settings/comfyui/check")
def check_comfyui(request: Request) -> JSONResponse:
    """Run one explicit bounded ComfyUI connection check."""
    diagnostics = get_application_container(
        request
    ).runtime_diagnostics.inspect()
    return JSONResponse(diagnostics_response(diagnostics))


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
        }
    )


def profile_value(
    profile_uid: str,
    payload: GenerationProfileRequest,
) -> GenerationProfile:
    """Translate one HTTP DTO into a typed application value."""
    return GenerationProfile(
        profile_uid=profile_uid,
        name=payload.name,
        blueprint_uid=payload.blueprint_uid,
        blueprint_version=payload.blueprint_version,
        checkpoint=payload.checkpoint,
        sampler=payload.sampler,
        scheduler=payload.scheduler,
        seed_mode=payload.seed_mode,
        fixed_seed=payload.fixed_seed,
        steps_min=payload.steps_min,
        steps_max=payload.steps_max,
        cfg_min_milli=round(payload.cfg_min * 1000),
        cfg_max_milli=round(payload.cfg_max * 1000),
        denoise_milli=round(payload.denoise * 1000),
        batch_size=payload.batch_size,
        image_width=payload.image_width,
        image_height=payload.image_height,
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


def profile_response(profile: GenerationProfile) -> dict[str, object]:
    """Map one generation profile to snake-case JSON."""
    return {
        "profile_uid": profile.profile_uid,
        "name": profile.name,
        "blueprint_uid": profile.blueprint_uid,
        "blueprint_version": profile.blueprint_version,
        "checkpoint": profile.checkpoint,
        "sampler": profile.sampler,
        "scheduler": profile.scheduler,
        "seed_mode": profile.seed_mode,
        "fixed_seed": profile.fixed_seed,
        "steps_min": profile.steps_min,
        "steps_max": profile.steps_max,
        "cfg_min": profile.cfg_min_milli / 1000,
        "cfg_max": profile.cfg_max_milli / 1000,
        "denoise": profile.denoise_milli / 1000,
        "batch_size": profile.batch_size,
        "image_width": profile.image_width,
        "image_height": profile.image_height,
        "archived": profile.archived,
        "is_default": profile.is_default,
        "loras": [
            {
                "name": item.name,
                "model_strength": item.model_strength_milli / 1000,
                "clip_strength": item.clip_strength_milli / 1000,
                "position": item.position,
            }
            for item in profile.loras
        ],
    }


def preferences_response(
    preferences: WorkspacePreferences,
) -> dict[str, object]:
    """Map workspace preferences to snake-case JSON."""
    return {
        "density": preferences.density,
        "motion": preferences.motion,
        "analytics_page_size": preferences.analytics_page_size,
        "default_generation_profile_uid": (
            preferences.default_generation_profile_uid
        ),
        "review_unrated_only": preferences.review_unrated_only,
        "review_max_attempts": preferences.review_max_attempts,
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
