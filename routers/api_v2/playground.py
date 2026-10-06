"""Catalog-backed Playground draft V2 HTTP adapters."""

import secrets
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    AspectFormat,
    ContentClassificationError,
    GenerationLoraSelection,
    ImageContextNotFoundError,
    ManualPromptSelection,
    PlaygroundEvidenceQuery,
    PromptCatalogValidationError,
    PromptDraftOverrides,
    PromptSelectionCommand,
    PromptSelectionError,
    RenderSettings,
    ResolutionClass,
)
from routers.api_v2.catalog import (
    PromptAtomRequest,
    atom_response,
    atom_usages,
    component_response,
    lora_response,
)
from routers.api_v2.common import PromptKind, error_response
from routers.api_v2.render_guidance import guidance_response

router = APIRouter()


class PlaygroundSelectionIntent(BaseModel):
    """Describe one explicit fixed, random or disabled prompt role."""

    kind: PromptKind
    mode: Literal["fixed", "random", "off"]
    component_uid: str | None = None
    revision_uid: str | None = None


class PlaygroundDraftRequest(BaseModel):
    """Request one catalog-backed prompt draft without persistence."""

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    max_attempts: int = 200
    generation: "PlaygroundDraftGenerationSettings"
    positive_atoms: list[PromptAtomRequest] | None = None
    negative_atoms: list[PromptAtomRequest] | None = None
    prompt_source: "PlaygroundPromptSource | None" = None
    loras: list["PlaygroundDraftLora"] = Field(default_factory=list)


class PlaygroundPromptSource(BaseModel):
    """Select exactly one authoritative prompt source mode."""

    mode: Literal["selection", "revisions", "composition", "image_snapshot"]
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    image_uid: str | None = None


class PlaygroundDraftLora(BaseModel):
    """Select one stable LoRA revision and explicit strengths."""

    lora_uid: str
    revision_uid: str | None = None
    model_strength: float = 1.0
    clip_strength: float = 1.0


class PlaygroundDraftGenerationSettings(BaseModel):
    """Carry explicit generator settings required to reproduce a draft."""

    checkpoint: str
    sampler: str
    scheduler: str
    seed: int | None = None
    randomize_seed: bool = False
    steps: int
    cfg: float
    denoise: float
    aspect_format: AspectFormat
    resolution_class: ResolutionClass


class PromptRenderPreviewRequest(BaseModel):
    """Carry one structured draft to the authoritative renderer."""

    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]


class PlaygroundEvidenceRequest(PlaygroundDraftGenerationSettings):
    """Compare the current reviewed atoms with visible history."""

    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]


class PlaygroundRenderGuidanceRequest(BaseModel):
    """Carry the concrete optimizer-controlled Generator settings."""

    checkpoint: str
    sampler: str
    scheduler: str
    steps: int = Field(ge=1, le=100)
    cfg: float = Field(gt=0, le=30)
    denoise: float = Field(ge=0, le=1)


class PlaygroundGeneratorSettingsPayload(BaseModel):
    """Carry the complete user-owned Playground control state."""

    model_config = ConfigDict(extra="forbid")

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    loras: list[PlaygroundDraftLora] = Field(default_factory=list)
    checkpoint: str
    sampler: str
    scheduler: str
    seed_mode: Literal["fixed", "random"]
    seed: int
    steps_min: int = Field(ge=1, le=100)
    steps_max: int = Field(ge=1, le=100)
    cfg_min: float = Field(gt=0, le=30)
    cfg_max: float = Field(gt=0, le=30)
    cfg_step: float = Field(gt=0, le=30)
    denoise: float = Field(ge=0, le=1)
    batch_runs: int = Field(ge=1)
    aspect_format: AspectFormat
    resolution_class: ResolutionClass


@router.get("/playground/generator-state")
def playground_generator_state(request: Request) -> JSONResponse:
    """Return the last explicit generator settings snapshot."""
    settings = get_application_container(
        request
    ).playground_generator_settings.load()
    return JSONResponse(settings)


@router.put("/playground/generator-state")
def save_playground_generator_state(
    request: Request,
    payload: PlaygroundGeneratorSettingsPayload,
) -> JSONResponse:
    """Persist the complete generator state after an explicit UI change."""
    settings = payload.model_dump(mode="json")
    get_application_container(request).playground_generator_settings.save(
        settings
    )
    return JSONResponse(settings)


@router.get("/playground/capabilities")
def playground_capabilities(request: Request) -> JSONResponse:
    """Return cached-or-live native ComfyUI enum capabilities."""
    container = get_application_container(request)
    discovery = container.playground_discovery.discover()
    defaults = container.workflow_defaults.load("default-character", 4)
    definitions = container.lora_catalog.list_definitions()
    return JSONResponse(
        {
            "checkpoints": discovery.checkpoints,
            "samplers": discovery.samplers,
            "schedulers": discovery.schedulers,
            "loras": discovery.loras,
            "lora_definitions": [
                {
                    **lora_response(item),
                    "available": item.provider_name in discovery.loras,
                }
                for item in definitions
                if item.content_level is not None and not item.archived
            ],
            "upscale_models": discovery.upscale_models,
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


@router.get("/playground/components")
def playground_components(request: Request) -> JSONResponse:
    """Return active components allowed by workspace content policy."""
    components = get_application_container(
        request
    ).playground_service.list_available_components()
    return JSONResponse(
        {"components": [component_response(item) for item in components]}
    )


@router.get("/playground/compositions/{composition_uid}/prompt-selections")
def playground_composition_prompt_selections(
    composition_uid: str,
    request: Request,
) -> JSONResponse:
    """Return the exact prompt selections in a persisted composition."""
    container = get_application_container(request)
    try:
        selections = (
            container.playground_service.resolve_composition_selection(
                composition_uid
            )
        )
    except (
        ContentClassificationError,
        PromptSelectionError,
        PromptCatalogValidationError,
    ) as error:
        return error_response(400, "invalid_playground_selection", str(error))
    return JSONResponse(
        {
            "selections": [
                {
                    "kind": selected.component.kind,
                    "component_uid": selected.component.component_uid,
                    "revision_uid": selected.revision.revision_uid,
                }
                for selected in selections.components
            ]
        }
    )


@router.get("/playground/top-combinations")
def playground_top_combinations(request: Request) -> JSONResponse:
    """Return top canonical two- and three-component examples."""
    context = get_application_container(
        request
    ).analytics_pages.playground_combinations_context(limit=8)
    return JSONResponse(context)


@router.post("/playground/render-guidance")
def playground_render_guidance(
    request: Request,
    payload: PlaygroundRenderGuidanceRequest,
) -> JSONResponse:
    """Return capability-filtered evidence for the current render setup."""
    settings = RenderSettings(
        checkpoint=payload.checkpoint.strip(),
        sampler=payload.sampler.strip(),
        scheduler=payload.scheduler.strip(),
        steps=payload.steps,
        cfg=payload.cfg,
        denoise=payload.denoise,
    )
    guidance = get_application_container(
        request
    ).playground_render_guidance.build(settings)
    return JSONResponse(guidance_response(guidance))


@router.post("/playground/drafts")
def prepare_playground_draft(
    request: Request,
    payload: PlaygroundDraftRequest,
) -> JSONResponse:
    """Prepare one reproducible draft from catalog selection intent."""
    try:
        concrete_seed = (
            secrets.randbelow(2**63)
            if payload.generation.randomize_seed
            or payload.generation.seed is None
            else payload.generation.seed
        )
        overrides = draft_overrides(payload)
        container = get_application_container(request)
        service = container.playground_service
        source_mode = (
            payload.prompt_source.mode
            if payload.prompt_source is not None
            else "composition"
            if payload.composition_uid
            else "revisions"
            if payload.revision_uids
            else "selection"
        )
        source_revisions = (
            payload.prompt_source.revision_uids
            if payload.prompt_source is not None
            else payload.revision_uids
        )
        source_composition = (
            payload.prompt_source.composition_uid
            if payload.prompt_source is not None
            else payload.composition_uid
        )
        source_handoff = None
        if source_mode == "image_snapshot":
            if payload.selections or source_revisions or source_composition:
                raise PromptSelectionError(
                    "image snapshot cannot include another prompt source"
                )
            image_uid = (
                payload.prompt_source.image_uid
                if payload.prompt_source is not None
                else None
            )
            if not image_uid:
                raise PromptSelectionError("image_uid is required")
            source_handoff = container.image_generator_handoffs.get(image_uid)
            draft = service.prepare_image_snapshot(
                container.image_contexts.get_image(image_uid),
                overrides=overrides,
            )
        elif source_mode == "composition":
            if not source_composition:
                raise PromptSelectionError("composition_uid is required")
            if payload.selections or source_revisions or overrides:
                raise PromptSelectionError(
                    "composition handoff cannot include draft selections"
                )
            draft = service.prepare_composition_draft(source_composition)
        elif source_mode == "revisions":
            if not source_revisions:
                raise PromptSelectionError("revision_uids are required")
            if payload.selections or overrides:
                raise PromptSelectionError(
                    "revision handoff cannot include draft selections"
                )
            draft = service.prepare_revision_draft(tuple(source_revisions))
        else:
            draft = service.prepare_draft(
                selection_command(payload, concrete_seed),
                overrides=overrides,
            )
        lora_groups = (
            container.lora_drafts.resolve(
                tuple(
                    GenerationLoraSelection(
                        name="",
                        model_strength_milli=round(item.model_strength * 1000),
                        clip_strength_milli=round(item.clip_strength * 1000),
                        position=position,
                        lora_uid=item.lora_uid,
                        revision_uid=item.revision_uid,
                    )
                    for position, item in enumerate(payload.loras)
                )
            )
            if payload.loras and source_mode != "image_snapshot"
            else ()
        )
        positive_atoms = draft.prompt.positive_atoms
        negative_atoms = draft.prompt.negative_atoms
        if source_mode != "image_snapshot" and overrides is None:
            positive_atoms += tuple(
                atom
                for group in lora_groups
                for atom in group.revision.positive_atoms
            )
            negative_atoms += tuple(
                atom
                for group in lora_groups
                for atom in group.revision.negative_atoms
            )
        positive_prompt, negative_prompt = (
            container.prompt_renderer.render_atoms(
                positive_atoms, negative_atoms
            )
        )
    except (
        ContentClassificationError,
        ImageContextNotFoundError,
        PromptSelectionError,
        PromptCatalogValidationError,
    ) as error:
        return error_response(400, "invalid_playground_selection", str(error))
    return JSONResponse(
        {
            "draft_uid": f"draft-{uuid4().hex}",
            "source_image_uid": (
                payload.prompt_source.image_uid
                if payload.prompt_source is not None
                and source_mode == "image_snapshot"
                else None
            ),
            "seed": concrete_seed,
            "components": [
                component_response(selected.component)
                for selected in draft.selection.components
            ],
            "positive_prompt": positive_prompt,
            "negative_prompt": negative_prompt,
            "positive_atoms": atom_response(positive_atoms),
            "negative_atoms": atom_response(negative_atoms),
            "revision_uids": draft.prompt.revision_uids,
            "draft_overridden": draft.prompt.draft_overridden,
            "groups": (
                [
                    {
                        "component_uid": None,
                        "revision_uid": None,
                        "kind": "image_snapshot",
                        "name": "Historischer Prompt-Snapshot",
                        "positive_atoms": atom_response(positive_atoms),
                        "negative_atoms": atom_response(negative_atoms),
                    }
                ]
                if source_mode == "image_snapshot"
                else [
                    {
                        "component_uid": selected.component.component_uid,
                        "revision_uid": selected.revision.revision_uid,
                        "kind": selected.component.kind,
                        "name": selected.component.name,
                        "positive_atoms": atom_response(
                            selected.revision.positive_atoms
                        ),
                        "negative_atoms": atom_response(
                            selected.revision.negative_atoms
                        ),
                    }
                    for selected in draft.selection.components
                ]
                + [
                    {
                        "component_uid": group.selection.lora_uid,
                        "revision_uid": group.revision.revision_uid,
                        "kind": "lora",
                        "name": group.display_name,
                        "positive_atoms": atom_response(
                            group.revision.positive_atoms
                        ),
                        "negative_atoms": atom_response(
                            group.revision.negative_atoms
                        ),
                        "model_strength": (
                            group.selection.model_strength_milli / 1000
                        ),
                        "clip_strength": (
                            group.selection.clip_strength_milli / 1000
                        ),
                    }
                    for group in lora_groups
                ]
            ),
            "loras": (
                [
                    {
                        "lora_uid": item.lora_uid,
                        "revision_uid": item.revision_uid,
                        "provider_name": item.provider_name,
                        "display_name": item.provider_name,
                        "position": item.position,
                        "model_strength": item.model_strength_milli / 1000,
                        "clip_strength": item.clip_strength_milli / 1000,
                    }
                    for item in source_handoff.prompt_setup.loras
                ]
                if source_handoff is not None
                else [
                    {
                        "lora_uid": group.selection.lora_uid,
                        "revision_uid": group.revision.revision_uid,
                        "provider_name": group.selection.name,
                        "display_name": group.display_name,
                        "position": group.selection.position,
                        "model_strength": (
                            group.selection.model_strength_milli / 1000
                        ),
                        "clip_strength": (
                            group.selection.clip_strength_milli / 1000
                        ),
                    }
                    for group in lora_groups
                ]
            ),
        }
    )


@router.post("/playground/render-preview")
def render_playground_preview(
    request: Request,
    payload: PromptRenderPreviewRequest,
) -> JSONResponse:
    """Render draft atoms without persisting or submitting a generation."""
    try:
        positive, negative = get_application_container(
            request
        ).prompt_renderer.render_atoms(
            atom_usages(payload.positive_atoms),
            atom_usages(payload.negative_atoms),
        )
    except PromptCatalogValidationError as error:
        return error_response(400, "invalid_prompt_atoms", str(error))
    return JSONResponse(
        {"positive_prompt": positive, "negative_prompt": negative}
    )


@router.post("/playground/evidence")
def playground_evidence(
    request: Request,
    payload: PlaygroundEvidenceRequest,
) -> JSONResponse:
    """Return independently ranked prompt and sampler image evidence."""
    evidence = get_application_container(request).playground_evidence.find(
        PlaygroundEvidenceQuery(
            positive_atoms=atom_usages(payload.positive_atoms),
            negative_atoms=atom_usages(payload.negative_atoms),
            checkpoint=payload.checkpoint,
            sampler=payload.sampler,
            scheduler=payload.scheduler,
            steps=payload.steps,
            cfg=payload.cfg,
            denoise=payload.denoise,
            aspect_format=payload.aspect_format,
            resolution_class=payload.resolution_class,
        )
    )
    container = get_application_container(request)

    def response(item):
        if item is None:
            return None
        return {
            "image_uid": item.image_uid,
            "image_url": container.image_responses.image_url(item.image_uid),
            "average_rating": item.average_rating,
            "rating_count": item.rating_count,
        }

    return JSONResponse(
        {
            "prompt_match": response(evidence.prompt_match),
            "sampler_match": response(evidence.sampler_match),
            "prompt_matches": [
                response(item) for item in evidence.prompt_matches
            ],
            "sampler_matches": [
                response(item) for item in evidence.sampler_matches
            ],
        }
    )


def selection_command(
    payload: PlaygroundDraftRequest,
    concrete_seed: int,
) -> PromptSelectionCommand:
    """Translate complete V2 mode intent into a selection command."""
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
    character_revision_uid: str | None = None
    for kind in expected:
        selection = by_kind[kind]
        component_uid = str(selection.component_uid or "").strip()
        revision_uid = (
            str(selection.revision_uid).strip()
            if selection.revision_uid is not None
            else None
        )
        if selection.mode != "fixed" and revision_uid is not None:
            raise PromptSelectionError(
                f"{selection.mode} {kind} selection cannot include revision_uid"
            )
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
                character_revision_uid = revision_uid
            else:
                manual.append(
                    ManualPromptSelection(
                        kind,
                        component_uid,
                        revision_uid,
                    )
                )
    return PromptSelectionCommand(
        character_component_uid=character_uid,
        manual_selections=tuple(manual),
        disabled_kinds=tuple(disabled),
        seed=concrete_seed,
        max_attempts=payload.max_attempts,
        character_revision_uid=character_revision_uid,
    )


def draft_overrides(
    payload: PlaygroundDraftRequest,
) -> PromptDraftOverrides | None:
    """Translate optional draft text without mutating catalog revisions."""
    if payload.positive_atoms is None and payload.negative_atoms is None:
        return None
    return PromptDraftOverrides(
        positive_atoms=(
            atom_usages(payload.positive_atoms)
            if payload.positive_atoms is not None
            else None
        ),
        negative_atoms=(
            atom_usages(payload.negative_atoms)
            if payload.negative_atoms is not None
            else None
        ),
    )
