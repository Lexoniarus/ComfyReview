"""Catalog-backed Playground draft V2 HTTP adapters."""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from comfyreview.api import get_application_container
from comfyreview.application import (
    ManualPromptSelection,
    PromptCatalogValidationError,
    PromptDraftOverrides,
    PromptSelectionCommand,
    PromptSelectionError,
)
from routers.api_v2.catalog import (
    PromptAtomRequest,
    atom_response,
    atom_usages,
    component_response,
)
from routers.api_v2.common import PromptKind, error_response

router = APIRouter()


class PlaygroundSelectionIntent(BaseModel):
    """Describe one explicit fixed, random or disabled prompt role."""

    kind: PromptKind
    mode: Literal["fixed", "random", "off"]
    component_uid: str | None = None


class PlaygroundDraftRequest(BaseModel):
    """Request one catalog-backed prompt draft without persistence."""

    selections: list[PlaygroundSelectionIntent] = Field(default_factory=list)
    revision_uids: list[str] = Field(default_factory=list)
    composition_uid: str | None = None
    seed: int | None = None
    max_attempts: int = 200
    positive_atoms: list[PromptAtomRequest] | None = None
    negative_atoms: list[PromptAtomRequest] | None = None


class PromptRenderPreviewRequest(BaseModel):
    """Carry one structured draft to the authoritative renderer."""

    positive_atoms: list[PromptAtomRequest]
    negative_atoms: list[PromptAtomRequest]


@router.get("/playground/capabilities")
def playground_capabilities(request: Request) -> JSONResponse:
    """Return cached-or-live native ComfyUI enum capabilities."""
    container = get_application_container(request)
    discovery = container.playground_discovery.discover()
    defaults = container.workflow_defaults.load("default-character", 3)
    return JSONResponse(
        {
            "checkpoints": discovery.checkpoints,
            "samplers": discovery.samplers,
            "schedulers": discovery.schedulers,
            "loras": discovery.loras,
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


@router.get("/playground/top-combinations")
def playground_top_combinations(request: Request) -> JSONResponse:
    """Return top canonical two- and three-component examples."""
    context = get_application_container(
        request
    ).analytics_pages.playground_combinations_context(limit=8)
    return JSONResponse(context)


@router.post("/playground/drafts")
def prepare_playground_draft(
    request: Request,
    payload: PlaygroundDraftRequest,
) -> JSONResponse:
    """Prepare one reproducible draft from catalog selection intent."""
    try:
        overrides = draft_overrides(payload)
        service = get_application_container(request).playground_service
        if payload.composition_uid:
            if payload.selections or payload.revision_uids or overrides:
                raise PromptSelectionError(
                    "composition handoff cannot include draft selections"
                )
            draft = service.prepare_composition_draft(payload.composition_uid)
        elif payload.revision_uids:
            if payload.selections or overrides:
                raise PromptSelectionError(
                    "revision handoff cannot include draft selections"
                )
            draft = service.prepare_revision_draft(
                tuple(payload.revision_uids)
            )
        else:
            draft = service.prepare_draft(
                selection_command(payload),
                overrides=overrides,
            )
    except (PromptSelectionError, PromptCatalogValidationError) as error:
        return error_response(400, "invalid_playground_selection", str(error))
    return JSONResponse(
        {
            "components": [
                component_response(component)
                for component in draft.selection.components
            ],
            "positive_prompt": draft.prompt.positive_text,
            "negative_prompt": draft.prompt.negative_text,
            "positive_atoms": atom_response(draft.prompt.positive_atoms),
            "negative_atoms": atom_response(draft.prompt.negative_atoms),
            "revision_uids": draft.prompt.revision_uids,
            "draft_overridden": draft.prompt.draft_overridden,
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


def selection_command(
    payload: PlaygroundDraftRequest,
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
