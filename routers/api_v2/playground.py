"""Catalog-backed Playground draft V2 HTTP adapters."""

from typing import Literal

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from comfyreview.api import get_application_container
from comfyreview.application import (
    ManualPromptSelection,
    PromptDraftOverrides,
    PromptSelectionCommand,
    PromptSelectionError,
)
from routers.api_v2.catalog import component_response
from routers.api_v2.common import PromptKind, error_response

router = APIRouter()


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
        command = selection_command(payload)
        overrides = draft_overrides(payload)
        draft = get_application_container(
            request
        ).playground_service.prepare_draft(
            command,
            overrides=overrides,
        )
    except PromptSelectionError as error:
        return error_response(400, "invalid_playground_selection", str(error))
    return JSONResponse(
        {
            "components": [
                component_response(component)
                for component in draft.selection.components
            ],
            "positive_prompt": draft.prompt.positive_text,
            "negative_prompt": draft.prompt.negative_text,
            "revision_uids": draft.prompt.revision_uids,
            "draft_overridden": draft.prompt.draft_overridden,
        }
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
    if payload.positive_override is None and payload.negative_override is None:
        return None
    return PromptDraftOverrides(
        positive_text=payload.positive_override,
        negative_text=payload.negative_override,
    )
