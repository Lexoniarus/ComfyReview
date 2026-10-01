"""Behavior tests for catalog-backed Playground preparation."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application import (
    ConfirmPlaygroundDraftCommand,
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
            ManualPromptSelection("pose", "pose-a"),
            ManualPromptSelection("expression", "expression-a"),
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


def test_prompt_selection_policy_supports_random_character_and_disabled_kinds() -> (
    None
):
    command = PromptSelectionCommand(
        character_component_uid="",
        disabled_kinds=("outfit", "lighting", "modifier"),
        seed=9,
    )

    selection = PromptSelectionPolicy().select(_catalog(), command)

    assert tuple(component.kind for component in selection.components) == (
        "character",
        "scene",
        "pose",
        "expression",
    )
    assert selection.components[0].component_uid == "character-a"


def test_prompt_selection_policy_confirms_exact_components_in_domain_order() -> (
    None
):
    selection = PromptSelectionPolicy().confirm(
        _catalog(),
        ("outfit-red", "character-a", "scene-night"),
    )

    assert tuple(
        component.component_uid for component in selection.components
    ) == (
        "character-a",
        "scene-night",
        "outfit-red",
    )


@pytest.mark.parametrize(
    ("component_uids", "message"),
    (
        ((), "required"),
        (("character-a", "character-a"), "duplicate prompt component"),
        (("missing",), "unknown active prompt component"),
        (("scene-night",), "character component is required"),
        (("character-a", "scene-night", "scene-archived"), "unknown active"),
    ),
)
def test_prompt_selection_policy_rejects_invalid_exact_confirmation(
    component_uids: tuple[str, ...],
    message: str,
) -> None:
    active_catalog = tuple(
        component for component in _catalog() if not component.archived
    )
    with pytest.raises(PromptSelectionError, match=message):
        PromptSelectionPolicy().confirm(active_catalog, component_uids)


@pytest.mark.parametrize(
    ("catalog", "component_uids", "message"),
    (
        (
            (
                _component("character-a", "character"),
                _component("odd", "unknown"),
            ),
            ("character-a", "odd"),
            "unsupported prompt component kind",
        ),
        (
            (
                _component("character-a", "character"),
                _component("scene-a", "scene"),
                _component("scene-b", "scene"),
            ),
            ("character-a", "scene-a", "scene-b"),
            "duplicate prompt component kind",
        ),
        (
            (
                _component("character-a", "character", tags=("adult",)),
                _component("modifier-wind", "modifier", tags=("wind",)),
            ),
            ("character-a", "modifier-wind"),
            "incompatible prompt component",
        ),
        (
            (_component("character-mystery", "character", tags=("mystery",)),),
            ("character-mystery",),
            "incompatible prompt selection",
        ),
    ),
)
def test_prompt_selection_policy_rejects_invalid_confirmed_semantics(
    catalog: tuple[PromptComponent, ...],
    component_uids: tuple[str, ...],
    message: str,
) -> None:
    with pytest.raises(PromptSelectionError, match=message):
        PromptSelectionPolicy().confirm(catalog, component_uids)


@pytest.mark.parametrize(
    ("command", "message"),
    (
        (
            PromptSelectionCommand(
                "character-a",
                disabled_kinds=("character",),
            ),
            "character selection cannot be disabled",
        ),
        (
            PromptSelectionCommand(
                "character-a",
                disabled_kinds=("unknown",),
            ),
            "unsupported disabled prompt kind",
        ),
        (
            PromptSelectionCommand(
                "character-a",
                manual_selections=(
                    ManualPromptSelection("scene", "scene-night"),
                ),
                disabled_kinds=("scene",),
            ),
            "disabled prompt kinds cannot have manual selections",
        ),
    ),
)
def test_prompt_selection_policy_rejects_invalid_disabled_kinds(
    command: PromptSelectionCommand,
    message: str,
) -> None:
    with pytest.raises(PromptSelectionError, match=message):
        PromptSelectionPolicy().select(_catalog(), command)


def test_prompt_selection_policy_requires_an_active_character() -> None:
    catalog = tuple(
        component for component in _catalog() if component.kind != "character"
    )

    with pytest.raises(PromptSelectionError, match="no active character"):
        PromptSelectionPolicy().select(
            catalog,
            PromptSelectionCommand("", seed=1),
        )


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


def test_prompt_selection_policy_applies_gates_to_random_candidates() -> None:
    catalog = tuple(
        replace(component, tags=())
        if component.component_uid == "character-a"
        else replace(component, tags=("lewd",))
        if component.component_uid == "outfit-red"
        else component
        for component in _catalog()
    )

    with pytest.raises(PromptSelectionError, match="no compatible"):
        PromptSelectionPolicy().select(
            catalog,
            PromptSelectionCommand(
                "character-a",
                include_lighting=False,
                include_modifier=False,
                max_attempts=1,
            ),
        )


def test_prompt_selection_policy_validates_manual_excludes_and_requirements() -> (
    None
):
    school_catalog = tuple(
        replace(component, tags=("school",))
        if component.component_uid == "scene-night"
        else replace(component, tags=("lewd",))
        if component.component_uid == "outfit-red"
        else component
        for component in _catalog()
    )
    excludes = PromptSelectionCommand(
        "character-a",
        manual_selections=(
            ManualPromptSelection("scene", "scene-night"),
            ManualPromptSelection("outfit", "outfit-red"),
            ManualPromptSelection("pose", "pose-a"),
            ManualPromptSelection("expression", "expression-a"),
        ),
        include_lighting=False,
        include_modifier=False,
        max_attempts=1,
    )
    no_skirt_catalog = tuple(
        replace(
            component,
            latest_revision=replace(
                component.latest_revision,
                positive_text="red coat",
            ),
        )
        if component.component_uid == "outfit-red"
        else component
        for component in _catalog()
    )
    requirement = PromptSelectionCommand(
        "character-a",
        manual_selections=(ManualPromptSelection("modifier", "modifier-a"),),
        include_lighting=False,
        max_attempts=1,
    )

    with pytest.raises(PromptSelectionError, match="no compatible"):
        PromptSelectionPolicy().select(school_catalog, excludes)
    with pytest.raises(PromptSelectionError, match="no compatible"):
        PromptSelectionPolicy().select(no_skirt_catalog, requirement)


def test_prompt_selection_policy_derives_catalog_compatibility_tags() -> None:
    catalog = tuple(
        replace(
            component,
            latest_revision=replace(
                component.latest_revision,
                positive_text="character must be adult",
            ),
        )
        if component.component_uid == "character-a"
        else replace(
            component,
            latest_revision=replace(
                component.latest_revision,
                positive_text="lewd pool beach outfit",
            ),
        )
        if component.component_uid == "outfit-red"
        else component
        for component in _catalog()
    )

    selection = PromptSelectionPolicy().select(
        catalog,
        PromptSelectionCommand(
            "character-a",
            include_lighting=False,
            include_modifier=False,
            max_attempts=1,
        ),
    )

    assert selection.components[2].component_uid == "outfit-red"


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
    assert renderer.render_blocks(
        (" person ", "city"), ("bad anatomy", "")
    ) == (
        "person, city",
        "bad anatomy",
    )


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


def test_playground_service_revalidates_confirmed_draft_and_derives_revisions() -> (
    None
):
    catalog = _CatalogService(
        tuple(component for component in _catalog() if not component.archived)
    )
    service = PlaygroundService(
        catalog=catalog,
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
    )

    draft = service.confirm_draft(
        ConfirmPlaygroundDraftCommand(
            component_uids=("character-a", "scene-night"),
            positive_prompt="person, city, manual emphasis",
            negative_prompt="bad anatomy",
        )
    )

    assert draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-night",
    )
    assert draft.prompt.positive_text == "person, city, manual emphasis"
    assert draft.prompt.draft_overridden is True
    assert catalog.calls == [False]
