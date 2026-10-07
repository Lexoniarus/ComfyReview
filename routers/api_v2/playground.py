"""Catalog-backed Playground draft V2 HTTP adapters."""

import secrets
from collections.abc import Callable
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
    GenerationValidationError,
    GeneratorStateValidationError,
    ImageContextNotFoundError,
    ManualPromptSelection,
    MaterializePromptCandidateCommand,
    PlaygroundDraft,
    PlaygroundEvidenceQuery,
    PlaygroundVariantSpecification,
    PreparedPlaygroundVariant,
    PromptCatalogValidationError,
    PromptComponentDraftOverride,
    PromptDraftOverrides,
    PromptGuidanceRevisionConflict,
    PromptSelectionCommand,
    PromptSelectionError,
    PromptVariantRecommendation,
    RenderSettings,
    ResolutionClass,
    SelectedPromptComponent,
)
from comfyreview.domain import PromptAtomUsage
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

    model_config = ConfigDict(extra="forbid")

    kind: PromptKind
    mode: Literal["fixed", "random", "off"]
    component_uid: str | None = None
    revision_uid: str | None = None
    candidate_uid: str | None = None


class PlaygroundDraftRequest(BaseModel):
    """Request one catalog-backed prompt draft without persistence."""

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    max_attempts: int = 200
    generation: "PlaygroundDraftGenerationSettings"
    positive_atoms: list[PromptAtomRequest] | None = None
    negative_atoms: list[PromptAtomRequest] | None = None
    component_overrides: list["PlaygroundComponentOverrideRequest"] = Field(
        default_factory=list
    )
    prompt_source: "PlaygroundPromptSource | None" = None
    loras: list["PlaygroundDraftLora"] = Field(default_factory=list)


class PlaygroundPromptSource(BaseModel):
    """Select exactly one authoritative prompt source mode."""

    mode: Literal[
        "selection",
        "revisions",
        "composition",
        "image_snapshot",
        "image_adapted",
    ]
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    image_uid: str | None = None


class PlaygroundComponentOverrideRequest(BaseModel):
    """Override one exact fixed prompt source for this experiment only."""

    model_config = ConfigDict(extra="forbid")

    kind: PromptKind
    component_uid: str
    revision_uid: str
    candidate_uid: str | None = None
    positive_atoms: list[PromptAtomRequest] = Field(default_factory=list)
    negative_atoms: list[PromptAtomRequest] = Field(default_factory=list)


class PlaygroundDraftLora(BaseModel):
    """Select one stable LoRA revision and explicit strengths."""

    lora_uid: str
    revision_uid: str | None = None
    model_strength: float = 1.0
    clip_strength: float = 1.0


class PlaygroundGeneratorStateLora(BaseModel):
    """Persist one stable LoRA revision with exact UI strengths."""

    model_config = ConfigDict(extra="forbid")

    lora_uid: str
    revision_uid: str
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


class PlaygroundVariantGenerationSettings(PlaygroundDraftGenerationSettings):
    """Carry bounded sampler variation used while preparing variants."""

    steps_max: int = Field(ge=1, le=100)
    cfg_max: float = Field(gt=0, le=30)
    cfg_step: float = Field(gt=0, le=30)


class PlaygroundVariantBatchRequest(BaseModel):
    """Request a bounded transient batch of concrete Playground drafts."""

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    max_attempts: int = 200
    positive_atoms: list[PromptAtomRequest] | None = None
    negative_atoms: list[PromptAtomRequest] | None = None
    component_overrides: list[PlaygroundComponentOverrideRequest] = Field(
        default_factory=list
    )
    prompt_source: PlaygroundPromptSource | None = None
    loras: list[PlaygroundDraftLora] = Field(default_factory=list)
    variant_count: int = Field(default=4, ge=1, le=12)
    generation: PlaygroundVariantGenerationSettings


class PromptRenderPreviewRequest(BaseModel):
    """Carry one structured draft to the authoritative renderer."""

    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]
    loras: list[PlaygroundDraftLora] = Field(default_factory=list)


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


class PlaygroundPromptGuidanceRequest(BaseModel):
    """Evaluate one component's expected current stable revision."""

    component_uid: str
    source_revision_uid: str


class PlaygroundPromptCandidateRequest(BaseModel):
    """Explicitly materialize one selected prompt recipe."""

    component_uid: str
    source_revision_uid: str
    candidate_type: Literal["manual", "calculated", "next_test"]
    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]


class PlaygroundGeneratorSettingsPayload(BaseModel):
    """Carry the complete user-owned Playground control state."""

    model_config = ConfigDict(extra="forbid")

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    loras: list[PlaygroundGeneratorStateLora] = Field(default_factory=list)
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
    try:
        saved = get_application_container(
            request
        ).playground_generator_settings.save(settings)
    except GeneratorStateValidationError as error:
        return error_response(400, "invalid_generator_state", str(error))
    return JSONResponse(saved)


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
                if item.latest_revision is not None
                and (
                    item.latest_revision.positive_atoms
                    or item.latest_revision.negative_atoms
                )
                and not item.archived
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
    """Return generator-selectable active and historical components."""
    components = get_application_container(
        request
    ).playground_service.list_generator_components()
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


@router.post("/playground/prompt-guidance")
def playground_prompt_guidance(
    request: Request,
    payload: PlaygroundPromptGuidanceRequest,
) -> JSONResponse:
    """Return stable, observed, Weight-only, and discovery guidance."""
    try:
        container = get_application_container(request)
        guidance = container.prompt_variant_guidance.build(
            payload.component_uid,
            expected_revision_uid=payload.source_revision_uid,
        )
    except PromptGuidanceRevisionConflict as error:
        return error_response(409, "stale_prompt_revision", str(error))
    except (KeyError, ValueError) as error:
        return error_response(400, "invalid_prompt_guidance", str(error))
    return JSONResponse(
        {
            "component_uid": payload.component_uid,
            "model_version": guidance.model_version,
            "current_provisional": guidance.current_provisional,
            "current_standard": prompt_recommendation_response(
                guidance.current_standard,
                container.image_responses.image_url,
            ),
            "best_observed": prompt_recommendation_response(
                guidance.best_observed,
                container.image_responses.image_url,
            ),
            "optimized": prompt_recommendation_response(
                guidance.optimized,
                container.image_responses.image_url,
            ),
            "next_test": prompt_recommendation_response(
                guidance.next_test,
                container.image_responses.image_url,
            ),
            "coverage": {
                "image_count": guidance.coverage.image_count,
                "review_count": guidance.coverage.review_count,
                "observed_variant_count": (
                    guidance.coverage.observed_variant_count
                ),
                "stable_variant_count": guidance.coverage.stable_variant_count,
                "modeled_atom_count": guidance.coverage.modeled_atom_count,
                "atom_count": guidance.coverage.atom_count,
            },
        }
    )


@router.post("/playground/prompt-candidates")
def materialize_playground_prompt_candidate(
    request: Request,
    payload: PlaygroundPromptCandidateRequest,
) -> JSONResponse:
    """Persist one calculated or manually accepted recipe on explicit choice."""
    try:
        candidate = get_application_container(
            request
        ).prompt_catalog_service.materialize_candidate(
            MaterializePromptCandidateCommand(
                component_uid=payload.component_uid,
                source_revision_uid=payload.source_revision_uid,
                candidate_type=payload.candidate_type,
                positive_atoms=atom_usages(payload.positive_atoms),
                negative_atoms=atom_usages(payload.negative_atoms),
            )
        )
    except (KeyError, PromptCatalogValidationError, ValueError) as error:
        return error_response(400, "invalid_prompt_candidate", str(error))
    return JSONResponse(
        {
            "candidate_uid": candidate.candidate_uid,
            "component_uid": candidate.component_uid,
            "source_revision_uid": candidate.source_revision_uid,
            "candidate_type": candidate.candidate_type,
            "positive_atoms": atom_response(candidate.positive_atoms),
            "negative_atoms": atom_response(candidate.negative_atoms),
        }
    )


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
        elif source_mode == "image_adapted":
            if source_revisions or source_composition:
                raise PromptSelectionError(
                    "adapted image cannot include another prompt source"
                )
            image_uid = (
                payload.prompt_source.image_uid
                if payload.prompt_source is not None
                else None
            )
            if not image_uid:
                raise PromptSelectionError("image_uid is required")
            source_handoff = container.image_generator_handoffs.get(image_uid)
            if source_handoff.prompt_setup.availability != "complete":
                raise PromptSelectionError(
                    "source image prompt attribution is incomplete"
                )
            draft = service.prepare_draft(
                selection_command(payload, concrete_seed),
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
        if source_mode != "image_snapshot" and not whole_draft_overridden(
            overrides
        ):
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
            "prompt_selections": [
                {
                    "kind": selected.component.kind,
                    "component_uid": selected.component.component_uid,
                    "revision_uid": selected.revision.revision_uid,
                }
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
                    prompt_group_response(draft, selected)
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
            "prompt_groups": [
                prompt_group_response(draft, selected)
                for selected in draft.selection.components
            ],
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
                and source_mode == "image_snapshot"
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


@router.post("/playground/variant-batches")
def prepare_playground_variant_batch(
    request: Request,
    payload: PlaygroundVariantBatchRequest,
) -> JSONResponse:
    """Prepare concrete, preferably diverse, transient Playground drafts."""
    try:
        overrides = draft_overrides(payload)
        container = get_application_container(request)
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
        static_draft = None
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
            static_draft = container.playground_service.prepare_image_snapshot(
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
            static_draft = (
                container.playground_service.prepare_composition_draft(
                    source_composition
                )
            )
        elif source_mode == "revisions":
            if not source_revisions:
                raise PromptSelectionError("revision_uids are required")
            if payload.selections or overrides:
                raise PromptSelectionError(
                    "revision handoff cannot include draft selections"
                )
            static_draft = container.playground_service.prepare_revision_draft(
                tuple(source_revisions)
            )
        elif source_mode == "image_adapted":
            if source_revisions or source_composition:
                raise PromptSelectionError(
                    "adapted image cannot include another prompt source"
                )
            image_uid = (
                payload.prompt_source.image_uid
                if payload.prompt_source is not None
                else None
            )
            if not image_uid:
                raise PromptSelectionError("image_uid is required")
            source_handoff = container.image_generator_handoffs.get(image_uid)
            if source_handoff.prompt_setup.availability != "complete":
                raise PromptSelectionError(
                    "source image prompt attribution is incomplete"
                )

        generation = payload.generation
        specification = PlaygroundVariantSpecification(
            variant_count=payload.variant_count,
            generation_seed=(
                generation.seed if generation.seed is not None else 0
            ),
            randomize_seed=generation.randomize_seed,
            steps_min=generation.steps,
            steps_max=generation.steps_max,
            cfg_min=generation.cfg,
            cfg_max=generation.cfg_max,
            cfg_step=generation.cfg_step,
        )
        batch = (
            container.playground_variant_preparation.prepare_static(
                static_draft,
                specification,
            )
            if static_draft is not None
            else container.playground_variant_preparation.prepare(
                selection_command(payload, 0),
                specification,
                overrides=overrides,
            )
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
        loras: list[dict[str, object]] = (
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
            if source_handoff is not None and source_mode == "image_snapshot"
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
        )
        lora_prompt_groups: list[dict[str, object]] = [
            {
                "component_uid": group.selection.lora_uid,
                "revision_uid": group.revision.revision_uid,
                "kind": "lora",
                "name": group.display_name,
                "positive_atoms": atom_response(group.revision.positive_atoms),
                "negative_atoms": atom_response(group.revision.negative_atoms),
                "model_strength": (
                    group.selection.model_strength_milli / 1000
                ),
                "clip_strength": (group.selection.clip_strength_milli / 1000),
            }
            for group in lora_groups
        ]
        variants = []
        for variant in batch.variants:
            positive_atoms = variant.draft.prompt.positive_atoms
            negative_atoms = variant.draft.prompt.negative_atoms
            if source_mode != "image_snapshot" and not whole_draft_overridden(
                overrides
            ):
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
            variants.append(
                prepared_variant_response(
                    variant,
                    positive_atoms=positive_atoms,
                    negative_atoms=negative_atoms,
                    positive_prompt=positive_prompt,
                    negative_prompt=negative_prompt,
                    checkpoint=generation.checkpoint,
                    sampler=generation.sampler,
                    scheduler=generation.scheduler,
                    denoise=generation.denoise,
                    aspect_format=generation.aspect_format,
                    resolution_class=generation.resolution_class,
                    loras=loras,
                    lora_prompt_groups=lora_prompt_groups,
                    source_image_uid=(
                        payload.prompt_source.image_uid
                        if payload.prompt_source is not None
                        and source_mode == "image_snapshot"
                        else None
                    ),
                )
            )
    except (
        ContentClassificationError,
        GenerationValidationError,
        ImageContextNotFoundError,
        PromptSelectionError,
        PromptCatalogValidationError,
    ) as error:
        return error_response(400, "invalid_playground_variants", str(error))
    return JSONResponse(
        {
            "requested_count": payload.variant_count,
            "unique_count": batch.unique_count,
            "repeated_count": batch.repeated_count,
            "diversity_exhausted": batch.diversity_exhausted,
            "notice": (
                "Der verfügbare Auswahlraum ist ausgeschöpft; "
                "einige Varianten wiederholen sich."
                if batch.diversity_exhausted
                else None
            ),
            "variants": variants,
        }
    )


@router.post("/playground/render-preview")
def render_playground_preview(
    request: Request,
    payload: PromptRenderPreviewRequest,
) -> JSONResponse:
    """Render draft atoms without persisting or submitting a generation."""
    try:
        container = get_application_container(request)
        positive_atoms = atom_usages(payload.positive_atoms)
        negative_atoms = atom_usages(payload.negative_atoms)
        resolved = container.lora_drafts.resolve(
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
        if resolved:
            container.lora_triggers.validate(
                tuple(item.selection for item in resolved),
                positive_atoms,
                negative_atoms,
            )
        positive, negative = container.prompt_renderer.render_atoms(
            positive_atoms,
            negative_atoms,
        )
    except (ContentClassificationError, PromptCatalogValidationError) as error:
        code = (
            "lora_trigger_required"
            if str(error).startswith("lora_trigger_required")
            else "invalid_prompt_atoms"
        )
        return error_response(400, code, str(error))
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


def prompt_recommendation_response(
    recommendation: PromptVariantRecommendation | None,
    image_url: Callable[[str], str],
) -> dict[str, object] | None:
    """Map one prompt recommendation without leaking persistence details."""
    if recommendation is None:
        return None
    score = recommendation.score
    return {
        "revision_uid": recommendation.revision_uid,
        "candidate_uid": recommendation.candidate_uid,
        "positive_atoms": atom_response(recommendation.recipe.positive_atoms),
        "negative_atoms": atom_response(recommendation.recipe.negative_atoms),
        "score": {
            "lower_bound": score.lower_bound,
            "expected_success_rate": score.expected_success_rate,
            "average_rating": score.average_rating,
            "image_count": score.image_count,
            "review_count": score.review_count,
            "deleted_count": score.deleted_count,
            "standard_deviation": score.standard_deviation,
            "sufficiently_observed": score.sufficiently_observed,
        },
        "example_images": [
            {"image_uid": uid, "image_url": image_url(uid)}
            for uid in recommendation.image_uids
        ],
    }


def selection_atoms(
    selection: SelectedPromptComponent,
    *,
    positive: bool,
) -> tuple[PromptAtomUsage, ...]:
    """Return candidate atoms or the exact source revision atoms."""
    if selection.candidate is not None:
        return (
            selection.candidate.positive_atoms
            if positive
            else selection.candidate.negative_atoms
        )
    return (
        selection.revision.positive_atoms
        if positive
        else selection.revision.negative_atoms
    )


def prompt_group_response(
    draft: PlaygroundDraft,
    selection: SelectedPromptComponent,
) -> dict[str, object]:
    """Serialize one exact editable prompt group from a prepared draft."""
    candidate_uid = (
        selection.candidate.candidate_uid
        if selection.candidate is not None
        else None
    )
    group = next(
        (
            item
            for item in draft.prompt.component_groups
            if item.component_uid == selection.component.component_uid
            and item.revision_uid == selection.revision.revision_uid
            and item.candidate_uid == candidate_uid
        ),
        None,
    )
    return {
        "component_uid": selection.component.component_uid,
        "revision_uid": selection.revision.revision_uid,
        "candidate_uid": candidate_uid,
        "kind": selection.component.kind,
        "name": selection.component.name,
        "positive_atoms": atom_response(
            group.positive_atoms
            if group is not None
            else selection_atoms(selection, positive=True)
        ),
        "negative_atoms": atom_response(
            group.negative_atoms
            if group is not None
            else selection_atoms(selection, positive=False)
        ),
    }


def whole_draft_overridden(overrides: PromptDraftOverrides | None) -> bool:
    """Return whether flat atoms replace the complete rendered prompt."""
    return overrides is not None and (
        overrides.positive_atoms is not None
        or overrides.negative_atoms is not None
    )


def prepared_variant_response(
    variant: PreparedPlaygroundVariant,
    *,
    positive_atoms: tuple[PromptAtomUsage, ...],
    negative_atoms: tuple[PromptAtomUsage, ...],
    positive_prompt: str,
    negative_prompt: str,
    checkpoint: str,
    sampler: str,
    scheduler: str,
    denoise: float,
    aspect_format: AspectFormat,
    resolution_class: ResolutionClass,
    loras: list[dict[str, object]],
    lora_prompt_groups: list[dict[str, object]],
    source_image_uid: str | None,
) -> dict[str, object]:
    """Serialize one concrete variant without leaking workflow semantics."""
    draft = variant.draft
    prompt_groups = [
        prompt_group_response(draft, selected)
        for selected in draft.selection.components
    ]
    return {
        "draft_uid": variant.draft_uid,
        "source_image_uid": source_image_uid,
        "seed": variant.seed,
        "generation": {
            "checkpoint": checkpoint,
            "sampler": sampler,
            "scheduler": scheduler,
            "seed": variant.seed,
            "steps": variant.steps,
            "cfg": variant.cfg,
            "denoise": denoise,
            "aspect_format": aspect_format,
            "resolution_class": resolution_class,
        },
        "components": [
            component_response(selected.component)
            for selected in draft.selection.components
        ],
        "prompt_selections": [
            {
                "kind": selected.component.kind,
                "component_uid": selected.component.component_uid,
                "revision_uid": selected.revision.revision_uid,
            }
            for selected in draft.selection.components
        ],
        "positive_prompt": positive_prompt,
        "negative_prompt": negative_prompt,
        "positive_atoms": atom_response(positive_atoms),
        "negative_atoms": atom_response(negative_atoms),
        "revision_uids": draft.prompt.revision_uids,
        "draft_overridden": draft.prompt.draft_overridden,
        "groups": [*prompt_groups, *lora_prompt_groups],
        "prompt_groups": prompt_groups,
        "loras": loras,
    }


def selection_command(
    payload: PlaygroundDraftRequest | PlaygroundVariantBatchRequest,
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
    character_candidate_uid: str | None = None
    for kind in expected:
        selection = by_kind[kind]
        component_uid = str(selection.component_uid or "").strip()
        revision_uid = (
            str(selection.revision_uid).strip()
            if selection.revision_uid is not None
            else None
        )
        candidate_uid = (
            str(selection.candidate_uid).strip()
            if selection.candidate_uid is not None
            else None
        )
        if selection.mode != "fixed" and (
            revision_uid is not None or candidate_uid is not None
        ):
            raise PromptSelectionError(
                f"{selection.mode} {kind} selection cannot include prompt IDs"
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
            if candidate_uid is not None and revision_uid is None:
                raise PromptSelectionError(
                    f"fixed {kind} candidate requires revision_uid"
                )
            if kind == "character":
                character_uid = component_uid
                character_revision_uid = revision_uid
                character_candidate_uid = candidate_uid
            else:
                manual.append(
                    ManualPromptSelection(
                        kind,
                        component_uid,
                        revision_uid,
                        candidate_uid,
                    )
                )
    return PromptSelectionCommand(
        character_component_uid=character_uid,
        manual_selections=tuple(manual),
        disabled_kinds=tuple(disabled),
        seed=concrete_seed,
        max_attempts=payload.max_attempts,
        character_revision_uid=character_revision_uid,
        character_candidate_uid=character_candidate_uid,
    )


def draft_overrides(
    payload: PlaygroundDraftRequest | PlaygroundVariantBatchRequest,
) -> PromptDraftOverrides | None:
    """Translate optional draft text without mutating catalog revisions."""
    if payload.component_overrides and (
        payload.positive_atoms is not None
        or payload.negative_atoms is not None
    ):
        raise PromptSelectionError(
            "component overrides cannot be combined with whole-draft overrides"
        )
    fixed_identities = {
        (
            selection.kind,
            str(selection.component_uid or "").strip(),
            str(selection.revision_uid or "").strip(),
            str(selection.candidate_uid or "").strip() or None,
        )
        for selection in payload.selections
        if selection.mode == "fixed" and selection.revision_uid is not None
    }
    component_overrides = tuple(
        PromptComponentDraftOverride(
            kind=item.kind,
            component_uid=item.component_uid,
            revision_uid=item.revision_uid,
            candidate_uid=item.candidate_uid,
            positive_atoms=atom_usages(item.positive_atoms),
            negative_atoms=atom_usages(item.negative_atoms),
        )
        for item in payload.component_overrides
    )
    override_identities = {
        (
            item.kind,
            item.component_uid.strip(),
            item.revision_uid.strip(),
            str(item.candidate_uid or "").strip() or None,
        )
        for item in component_overrides
    }
    if len(override_identities) != len(component_overrides):
        raise PromptSelectionError("duplicate prompt component override")
    if not override_identities <= fixed_identities:
        raise PromptSelectionError(
            "prompt component overrides require an exact fixed selection"
        )
    if (
        payload.positive_atoms is None
        and payload.negative_atoms is None
        and not component_overrides
    ):
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
        component_overrides=component_overrides,
    )
