"""Behavior tests for catalog-backed Playground preparation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    ManualPromptSelection,
    PlaygroundService,
    PromptComponent,
    PromptDraftOverrides,
    PromptRenderer,
    PromptRevision,
    PromptSelectionCommand,
    PromptSelectionError,
    PromptSelectionPolicy,
)


def _component(
    uid: str,
    kind: str,
    *,
    positive: str = "",
    negative: str = "",
    tags: tuple[str, ...] = (),
    name: str | None = None,
    notes: str = "",
    archived: bool = False,
) -> PromptComponent:
    return PromptComponent(
        component_uid=uid,
        kind=kind,
        component_key=f"{uid}_key",
        name=name or uid,
        tags=tags,
        notes=notes,
        archived=archived,
        latest_revision=PromptRevision(
            revision_uid=f"revision-{uid}",
            revision_number=1,
            positive_text=positive,
            negative_text=negative,
            content_hash=f"hash-{uid}",
        ),
    )


def _catalog() -> tuple[PromptComponent, ...]:
    return (
        _component(
            "character-a",
            "character",
            positive="person",
            negative="bad anatomy",
            tags=("adult",),
            notes="character note",
        ),
        _component("scene-night", "scene", positive="city", tags=("night",)),
        _component("outfit-red", "outfit", positive="red skirt"),
        _component("pose-a", "pose", positive="standing"),
        _component("expression-a", "expression", positive="smile"),
        _component(
            "lighting-a",
            "lighting",
            positive="dramatic light",
            tags=("dramatic",),
        ),
        _component("modifier-a", "modifier", positive="wind", tags=("wind",)),
        _component("modifier-empty", "modifier", name="Empty"),
        _component("scene-archived", "scene", archived=True),
    )


def test_prompt_selection_policy_selects_reproducible_compatible_revisions() -> (
    None
):
    command = PromptSelectionCommand(
        character_component_uid="character-a",
        manual_selections=(
            ManualPromptSelection("scene", "scene-night"),
            ManualPromptSelection("outfit", "outfit-red"),
        ),
        seed=17,
    )
    policy = PromptSelectionPolicy()

    first = policy.select(_catalog(), command)
    second = policy.select(_catalog(), command)

    assert first == second
    assert tuple(component.kind for component in first.components) == (
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
        "lighting",
        "modifier",
    )
    assert first.components[-1].component_uid == "modifier-a"


@pytest.mark.parametrize(
    ("command", "message"),
    (
        (
            PromptSelectionCommand("missing"),
            "unknown active prompt component",
        ),
        (
            PromptSelectionCommand("scene-night"),
            "is not character",
        ),
        (
            PromptSelectionCommand(
                "character-a",
                manual_selections=(
                    ManualPromptSelection("unsupported", "pose-a"),
                ),
            ),
            "unsupported manual selection kind",
        ),
        (
            PromptSelectionCommand(
                "character-a",
                manual_selections=(
                    ManualPromptSelection("pose", "pose-a"),
                    ManualPromptSelection("pose", "pose-a"),
                ),
            ),
            "duplicate manual selection kind",
        ),
        (
            PromptSelectionCommand("character-a", max_attempts=0),
            "max_attempts must be positive",
        ),
    ),
)
def test_prompt_selection_policy_rejects_invalid_commands(
    command: PromptSelectionCommand,
    message: str,
) -> None:
    with pytest.raises(PromptSelectionError, match=message):
        PromptSelectionPolicy().select(_catalog(), command)


def test_prompt_selection_policy_reports_incompatible_catalog() -> None:
    catalog = tuple(
        replace(component, tags=("lewd",))
        if component.component_uid == "outfit-red"
        else component
        for component in _catalog()
        if component.component_uid != "scene-night"
    ) + (_component("scene-school", "scene", tags=("school",)),)

    with pytest.raises(PromptSelectionError, match="no compatible"):
        PromptSelectionPolicy().select(
            catalog,
            PromptSelectionCommand("character-a", seed=2, max_attempts=2),
        )


def test_prompt_renderer_keeps_revision_snapshot_and_draft_override_separate() -> (
    None
):
    selection = PromptSelectionPolicy().select(
        _catalog(),
        PromptSelectionCommand("character-a", seed=4),
    )
    renderer = PromptRenderer()

    rendered = renderer.render(selection)
    overridden = renderer.render(
        selection,
        PromptDraftOverrides(
            positive_text="draft positive",
            negative_text="draft negative",
        ),
    )

    assert rendered.positive_text == (
        "person, city, red skirt, standing, smile, dramatic light, wind"
    )
    assert rendered.negative_text == "bad anatomy"
    assert rendered.notes == "character note"
    assert rendered.revision_uids[0] == "revision-character-a"
    assert rendered.draft_overridden is False
    assert overridden.positive_text == "draft positive"
    assert overridden.negative_text == "draft negative"
    assert overridden.revision_uids == rendered.revision_uids
    assert overridden.draft_overridden is True


class _CatalogService:
    def __init__(self, components: tuple[PromptComponent, ...]) -> None:
        self.components = components
        self.calls: list[bool] = []

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        self.calls.append(include_archived)
        return self.components


def test_playground_service_prepares_draft_without_generation_submission() -> (
    None
):
    catalog = _CatalogService(_catalog())
    service = PlaygroundService(
        catalog=catalog,
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
    )

    draft = service.prepare_draft(
        PromptSelectionCommand(
            "character-a",
            include_lighting=False,
            include_modifier=False,
            seed=3,
        )
    )

    assert catalog.calls == [False]
    assert draft.prompt.positive_text == (
        "person, city, red skirt, standing, smile"
    )
    assert tuple(
        component.kind for component in draft.selection.components
    ) == (
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
    )
