"""Behavior tests for catalog-backed Playground preparation."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

import pytest

from comfyreview.application import (
    ConfirmPlaygroundDraftCommand,
    ContentLevel,
    ManualPromptSelection,
    PlaygroundService,
    PromptComponent,
    PromptContentPolicy,
    PromptDraftOverrides,
    PromptRenderer,
    PromptRevision,
    PromptRevisionSelection,
    PromptSelection,
    PromptSelectionCommand,
    PromptSelectionError,
    PromptSelectionPolicy,
    WorkspacePreferences,
)
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqlitePromptCatalogRepository,
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
    content_level: ContentLevel = ContentLevel.STANDARD,
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
            positive_atoms=prompt_atom_usages_from_text(positive),
            negative_atoms=prompt_atom_usages_from_text(negative),
        ),
        content_level=content_level,
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
    assert tuple(selected.component.kind for selected in first.components) == (
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
        "lighting",
        "modifier",
    )
    assert first.components[-1].component.component_uid == "modifier-a"


def test_playground_fixed_revision_uses_exact_revision_projection() -> None:
    latest_component = _component(
        "character-a", "character", positive="latest character prompt"
    )
    exact_revision = PromptRevision(
        revision_uid="revision-character-a-old",
        revision_number=1,
        positive_text="historical character prompt",
        negative_text="historical negative",
        content_hash="historical-hash",
        positive_atoms=prompt_atom_usages_from_text(
            "historical character prompt"
        ),
        negative_atoms=prompt_atom_usages_from_text("historical negative"),
    )
    exact_projection = replace(
        latest_component,
        latest_revision=exact_revision,
    )
    catalog = _CatalogService(
        (latest_component,),
        exact_revisions=(exact_projection,),
    )

    draft = _service(catalog).prepare_draft(
        PromptSelectionCommand(
            "character-a",
            disabled_kinds=(
                "scene",
                "outfit",
                "pose",
                "expression",
                "lighting",
                "modifier",
            ),
            character_revision_uid="revision-character-a-old",
        )
    )

    assert draft.prompt.revision_uids == ("revision-character-a-old",)
    assert draft.prompt.positive_text == "historical character prompt"
    assert draft.prompt.negative_text == "historical negative"
    assert draft.prompt.positive_atoms == exact_revision.positive_atoms
    assert catalog.components[0].latest_revision.revision_uid == (
        "revision-character-a"
    )


def test_historical_revision_content_drives_selection_compatibility() -> None:
    character = _component(
        "character-a",
        "character",
        positive="school character",
        tags=("school",),
    )
    latest_outfit = _component("outfit-a", "outfit", positive="red coat")
    historical_outfit = replace(
        latest_outfit,
        latest_revision=replace(
            latest_outfit.latest_revision,
            revision_uid="revision-outfit-old",
            positive_text="lewd outfit",
            positive_atoms=prompt_atom_usages_from_text("lewd outfit"),
        ),
    )
    catalog = _CatalogService(
        (character, latest_outfit),
        exact_revisions=(historical_outfit,),
    )

    with pytest.raises(PromptSelectionError, match="no compatible"):
        _service(catalog).prepare_draft(
            PromptSelectionCommand(
                "character-a",
                manual_selections=(
                    ManualPromptSelection(
                        "outfit",
                        "outfit-a",
                        "revision-outfit-old",
                    ),
                ),
                disabled_kinds=("scene", "pose", "expression"),
                include_lighting=False,
                include_modifier=False,
                max_attempts=1,
            )
        )


def test_playground_fixed_manual_selection_uses_exact_revision() -> None:
    character = _component("character-a", "character")
    latest_scene = _component("scene-a", "scene", positive="latest scene")
    exact_scene = replace(
        latest_scene,
        latest_revision=replace(
            latest_scene.latest_revision,
            revision_uid="revision-scene-old",
            positive_text="historical scene",
            positive_atoms=prompt_atom_usages_from_text("historical scene"),
        ),
    )
    catalog = _CatalogService(
        (character, latest_scene),
        exact_revisions=(exact_scene,),
    )

    draft = _service(catalog).prepare_draft(
        PromptSelectionCommand(
            "character-a",
            manual_selections=(
                ManualPromptSelection(
                    "scene",
                    "scene-a",
                    "revision-scene-old",
                ),
            ),
            disabled_kinds=(
                "outfit",
                "pose",
                "expression",
                "lighting",
                "modifier",
            ),
        )
    )

    assert draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-old",
    )
    assert draft.prompt.positive_text == "historical scene"
    selected_scene = draft.selection.components[1]
    assert (
        selected_scene.component.latest_revision.revision_uid
        == "revision-scene-a"
    )
    assert selected_scene.revision.revision_uid == "revision-scene-old"
    assert (
        selected_scene.revision.positive_atoms
        == prompt_atom_usages_from_text("historical scene")
    )


def test_playground_fixed_revision_rejects_revision_kind_mismatch() -> None:
    character = _component("character-a", "character")
    scene = _component("scene-a", "scene")
    scene_projection = replace(
        scene,
        latest_revision=replace(
            scene.latest_revision,
            revision_uid="revision-scene",
        ),
    )
    catalog = _CatalogService(
        (character, scene),
        exact_revisions=(scene_projection,),
    )

    with pytest.raises(
        PromptSelectionError, match="revision component is not"
    ):
        _service(catalog).prepare_draft(
            PromptSelectionCommand(
                "scene-a",
                disabled_kinds=(
                    "scene",
                    "outfit",
                    "pose",
                    "expression",
                    "lighting",
                    "modifier",
                ),
                character_revision_uid="revision-scene",
            )
        )


@pytest.mark.parametrize(
    ("component_uid", "revision_uid", "message"),
    (
        ("", "revision-character-a", "requires component_uid"),
        ("character-a", " ", "requires revision_uid"),
    ),
)
def test_playground_fixed_revision_rejects_missing_identity_parts(
    component_uid: str,
    revision_uid: str,
    message: str,
) -> None:
    with pytest.raises(PromptSelectionError, match=message):
        _service(_CatalogService(_catalog())).prepare_draft(
            PromptSelectionCommand(
                component_uid,
                character_revision_uid=revision_uid,
            )
        )


@pytest.mark.parametrize(
    ("component_uid", "revision_uid", "message"),
    (
        (
            "character-a",
            "revision-scene",
            "does not belong to component",
        ),
        ("character-a", "missing-revision", "unknown prompt revision"),
    ),
)
def test_playground_fixed_revision_rejects_invalid_revision_binding(
    component_uid: str,
    revision_uid: str,
    message: str,
) -> None:
    character = _component("character-a", "character")
    scene = _component("scene-a", "scene")
    archived_projection = replace(
        character,
        latest_revision=replace(
            character.latest_revision,
            revision_uid="revision-character-archived",
        ),
    )
    catalog = _CatalogService(
        (character, scene),
        exact_revisions=(
            replace(
                scene,
                latest_revision=replace(
                    scene.latest_revision,
                    revision_uid="revision-scene",
                ),
            ),
            archived_projection,
        ),
    )

    with pytest.raises(PromptSelectionError, match=message):
        _service(catalog).prepare_draft(
            PromptSelectionCommand(
                component_uid,
                disabled_kinds=(
                    "scene",
                    "outfit",
                    "pose",
                    "expression",
                    "lighting",
                    "modifier",
                ),
                character_revision_uid=revision_uid,
            )
        )


def test_playground_fixed_revision_accepts_archived_historical_component() -> (
    None
):
    character = _component(
        "character-a",
        "character",
        positive="historical character",
        archived=True,
    )
    historical = replace(
        character,
        latest_revision=replace(
            character.latest_revision,
            revision_uid="revision-character-archived",
        ),
    )
    catalog = _CatalogService(
        (character,),
        exact_revisions=(historical,),
    )

    draft = _service(catalog).prepare_draft(
        PromptSelectionCommand(
            "character-a",
            disabled_kinds=(
                "scene",
                "outfit",
                "pose",
                "expression",
                "lighting",
                "modifier",
            ),
            character_revision_uid="revision-character-archived",
        )
    )

    assert draft.prompt.positive_text == "historical character"
    assert draft.selection.components[0].component.archived is True


def test_playground_fixed_revision_requires_current_component_identity() -> (
    None
):
    orphaned = _component("character-orphaned", "character")
    catalog = _CatalogService((), exact_revisions=(orphaned,))

    with pytest.raises(PromptSelectionError, match="unknown prompt component"):
        _service(catalog).prepare_draft(
            PromptSelectionCommand(
                "character-orphaned",
                disabled_kinds=(
                    "scene",
                    "outfit",
                    "pose",
                    "expression",
                    "lighting",
                    "modifier",
                ),
                character_revision_uid=(orphaned.latest_revision.revision_uid),
            )
        )


def test_playground_generator_catalog_includes_archived_components() -> None:
    service = _service(_CatalogService(_catalog()))

    available = service.list_available_components()
    generator = service.list_generator_components()

    assert "scene-archived" not in {
        component.component_uid for component in available
    }
    assert "scene-archived" in {
        component.component_uid for component in generator
    }


def test_playground_random_character_keeps_latest_catalog_revision() -> None:
    latest_component = _component(
        "character-a", "character", positive="latest prompt"
    )
    old_projection = replace(
        latest_component,
        latest_revision=replace(
            latest_component.latest_revision,
            revision_uid="revision-character-a-old",
            positive_text="historical prompt",
            positive_atoms=prompt_atom_usages_from_text("historical prompt"),
        ),
    )
    catalog = _CatalogService(
        (latest_component,),
        exact_revisions=(old_projection,),
    )

    draft = _service(catalog).prepare_draft(
        PromptSelectionCommand(
            "",
            disabled_kinds=(
                "scene",
                "outfit",
                "pose",
                "expression",
                "lighting",
                "modifier",
            ),
            seed=17,
        )
    )

    assert draft.prompt.revision_uids == ("revision-character-a",)
    assert draft.prompt.positive_text == "latest prompt"


def test_playground_exact_revision_does_not_bypass_content_policy() -> None:
    restricted_component = _component(
        "character-a",
        "character",
        positive="restricted prompt",
        content_level=ContentLevel.SEXY,
    )
    catalog = _CatalogService(
        (restricted_component,),
        exact_revisions=(restricted_component,),
    )

    with pytest.raises(
        PromptSelectionError,
        match="disabled content level",
    ):
        _service(catalog).prepare_draft(
            PromptSelectionCommand(
                "character-a",
                disabled_kinds=(
                    "scene",
                    "outfit",
                    "pose",
                    "expression",
                    "lighting",
                    "modifier",
                ),
                character_revision_uid="revision-character-a",
            )
        )


def test_playground_sqlite_fixed_revision_is_exact_without_changing_latest(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        component_id = int(
            connection.execute(
                """
                INSERT INTO prompt_components(
                    component_uid, kind, component_key, name, tags, notes
                ) VALUES ('character-a', 'character', 'character_a',
                          'Character A', '[]', '')
                RETURNING id
                """
            ).fetchone()[0]
        )
        revision_ids: dict[str, int] = {}
        for uid, number, text in (
            ("revision-character-a-v1", 1, "older atoms"),
            ("revision-character-a-v2", 2, "latest atoms"),
        ):
            revision_ids[uid] = int(
                connection.execute(
                    """
                    INSERT INTO prompt_revisions(
                        revision_uid, component_id, revision_number,
                        positive_text, negative_text, content_hash
                    ) VALUES (?, ?, ?, ?, '', ?)
                    RETURNING id
                    """,
                    (uid, component_id, number, text, f"hash-{number}"),
                ).fetchone()[0]
            )
            connection.execute(
                "INSERT INTO prompt_atoms(canonical_text) VALUES (?)",
                (text,),
            )
            atom_id = int(
                connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (text,),
                ).fetchone()[0]
            )
            connection.execute(
                """
                INSERT INTO prompt_revision_atom_usages(
                    revision_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, 'pos', 0, 1000)
                """,
                (revision_ids[uid], atom_id),
            )

    catalog = SqlitePromptCatalogRepository(database_path)
    playground = PlaygroundService(
        catalog=catalog,
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
        preferences=_Preferences(),
        content_policy=PromptContentPolicy(),
    )
    disabled_kinds = (
        "scene",
        "outfit",
        "pose",
        "expression",
        "lighting",
        "modifier",
    )

    fixed_old = playground.prepare_draft(
        PromptSelectionCommand(
            "character-a",
            disabled_kinds=disabled_kinds,
            character_revision_uid="revision-character-a-v1",
        )
    )
    fixed_latest = playground.prepare_draft(
        PromptSelectionCommand(
            "character-a",
            disabled_kinds=disabled_kinds,
        )
    )
    random_character = playground.prepare_draft(
        PromptSelectionCommand(
            "",
            disabled_kinds=disabled_kinds,
            seed=17,
        )
    )

    assert fixed_old.prompt.revision_uids == ("revision-character-a-v1",)
    assert fixed_old.prompt.positive_text == "older atoms"
    assert fixed_old.prompt.positive_atoms == prompt_atom_usages_from_text(
        "older atoms"
    )
    fixed_old_selection = fixed_old.selection.components[0]
    assert (
        fixed_old_selection.component.latest_revision.revision_uid
        == "revision-character-a-v2"
    )
    assert (
        fixed_old_selection.revision.revision_uid == "revision-character-a-v1"
    )
    assert fixed_latest.prompt.revision_uids == ("revision-character-a-v2",)
    assert fixed_latest.prompt.positive_text == "latest atoms"
    fixed_latest_selection = fixed_latest.selection.components[0]
    assert (
        fixed_latest_selection.component.latest_revision
        == fixed_latest_selection.revision
    )
    assert random_character.prompt.revision_uids == (
        "revision-character-a-v2",
    )
    random_selection = random_character.selection.components[0]
    assert (
        random_selection.revision == random_selection.component.latest_revision
    )
    [current] = catalog.list_components(include_archived=False)
    assert current.latest_revision.revision_uid == "revision-character-a-v2"


def test_prompt_selection_policy_supports_random_character_and_disabled_kinds() -> (
    None
):
    command = PromptSelectionCommand(
        character_component_uid="",
        disabled_kinds=("outfit", "lighting", "modifier"),
        seed=9,
    )

    selection = PromptSelectionPolicy().select(_catalog(), command)

    assert tuple(
        selected.component.kind for selected in selection.components
    ) == (
        "character",
        "scene",
        "pose",
        "expression",
    )
    assert selection.components[0].component.component_uid == "character-a"
    assert all(
        selected.component.latest_revision == selected.revision
        for selected in selection.components
    )
    with pytest.raises(
        PromptSelectionError,
        match="fixed character revision was not resolved",
    ):
        PromptSelectionPolicy().select(
            _catalog(),
            PromptSelectionCommand(
                "character-a",
                character_revision_uid="revision-character-old",
            ),
        )


def test_prompt_selection_policy_confirms_exact_components_in_domain_order() -> (
    None
):
    selection = PromptSelectionPolicy().confirm(
        _catalog(),
        ("outfit-red", "character-a", "scene-night"),
    )

    assert tuple(
        selected.component.component_uid for selected in selection.components
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

    assert selection.components[2].component.component_uid == "outfit-red"


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
            positive_atoms=prompt_atom_usages_from_text("draft positive"),
            negative_atoms=prompt_atom_usages_from_text("draft negative"),
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
    def __init__(
        self,
        components: tuple[PromptComponent, ...],
        exact_revisions: tuple[PromptComponent, ...] = (),
    ) -> None:
        self.components = components
        self.exact_revisions = exact_revisions
        self.calls: list[bool] = []

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        self.calls.append(include_archived)
        if include_archived:
            return self.components
        return tuple(
            component
            for component in self.components
            if not component.archived
        )

    def list_components_for_revisions(
        self,
        revision_uids: tuple[str, ...],
    ) -> tuple[PromptComponent, ...]:
        by_revision = {
            component.latest_revision.revision_uid: component
            for component in self.components
        }
        by_revision.update(
            {
                component.latest_revision.revision_uid: component
                for component in self.exact_revisions
            }
        )
        return tuple(
            by_revision[uid] for uid in revision_uids if uid in by_revision
        )

    def list_composition_components(
        self,
        composition_uid: str,
    ) -> tuple[PromptComponent, ...]:
        if composition_uid != "composition-a":
            return ()
        return self.components[:2]


class _Preferences:
    def __init__(self, value: WorkspacePreferences | None = None) -> None:
        self.value = value or WorkspacePreferences()

    def get(self) -> WorkspacePreferences:
        return self.value

    def save(self, preferences: WorkspacePreferences) -> WorkspacePreferences:
        self.value = preferences
        return preferences


def _service(catalog: _CatalogService) -> PlaygroundService:
    return PlaygroundService(
        catalog=catalog,
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
        preferences=_Preferences(),
        content_policy=PromptContentPolicy(),
    )


def test_revision_draft_rejects_mismatched_repository_revision() -> None:
    character = _component("character-a", "character")
    mismatched_projection = replace(
        character,
        latest_revision=replace(
            character.latest_revision,
            revision_uid="revision-returned",
        ),
    )

    class _MismatchedRevisionCatalog(_CatalogService):
        def list_components_for_revisions(
            self,
            revision_uids: tuple[str, ...],
        ) -> tuple[PromptComponent, ...]:
            return (mismatched_projection,)

    with pytest.raises(PromptSelectionError, match="do not match"):
        _service(
            _MismatchedRevisionCatalog((character,))
        ).prepare_revision_draft(("revision-requested",))


def test_revision_draft_rejects_missing_current_component_metadata() -> None:
    character = _component("character-a", "character")
    missing_component_projection = _component(
        "missing-character",
        "character",
    )

    class _MissingCurrentComponentCatalog(_CatalogService):
        def list_components_for_revisions(
            self,
            revision_uids: tuple[str, ...],
        ) -> tuple[PromptComponent, ...]:
            return (missing_component_projection,)

    with pytest.raises(PromptSelectionError, match="unknown prompt component"):
        _service(
            _MissingCurrentComponentCatalog((character,))
        ).prepare_revision_draft(("revision-missing-character",))


def test_playground_content_policy_filters_explicit_levels() -> None:
    components = (
        _component("character-a", "character", tags=("adult",)),
        _component(
            "pose-lewd",
            "pose",
            tags=("lewd",),
            content_level=ContentLevel.LEWD,
        ),
        _component(
            "modifier-nude",
            "modifier",
            tags=("nsfw_level_nude",),
            content_level=ContentLevel.NUDE,
        ),
    )
    policy = PromptContentPolicy()

    standard = policy.filter(components, (ContentLevel.STANDARD,))
    nude = policy.filter(
        components,
        (ContentLevel.STANDARD, ContentLevel.NUDE),
    )

    assert tuple(component.component_uid for component in standard) == (
        "character-a",
    )
    assert tuple(component.component_uid for component in nude) == (
        "character-a",
        "modifier-nude",
    )
    lewd = policy.filter(
        components,
        (ContentLevel.STANDARD, ContentLevel.LEWD),
    )
    assert tuple(component.component_uid for component in lewd) == (
        "character-a",
        "pose-lewd",
    )


def test_playground_content_policy_uses_typed_level_not_descriptive_tags() -> (
    None
):
    component = _component(
        "modifier-conflict",
        "modifier",
        tags=("nsfw_level_suggestive", "nsfw_level_nude"),
        content_level=ContentLevel.SEXY,
    )

    assert PromptContentPolicy().filter(
        (component,), (ContentLevel.SEXY,)
    ) == (component,)


def test_playground_service_prepares_draft_without_generation_submission() -> (
    None
):
    catalog = _CatalogService(_catalog())
    service = _service(catalog)

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
        selected.component.kind for selected in draft.selection.components
    ) == (
        "character",
        "scene",
        "outfit",
        "pose",
        "expression",
    )


def test_playground_service_confirms_exact_historical_and_archived_revisions() -> (
    None
):
    character = _component("character-a", "character", positive="person")
    scene = _component("scene-night", "scene", positive="current city")
    historical_scene = replace(
        scene,
        latest_revision=replace(
            scene.latest_revision,
            revision_uid="revision-scene-night-old",
            positive_text="historic city",
            positive_atoms=prompt_atom_usages_from_text("historic city"),
        ),
    )
    legacy_lighting = _component(
        "lighting-legacy",
        "lighting",
        positive="dim ambient background",
        archived=True,
    )
    catalog = _CatalogService(
        (character, scene, legacy_lighting),
        exact_revisions=(historical_scene,),
    )
    service = _service(catalog)

    draft = service.confirm_draft(
        ConfirmPlaygroundDraftCommand(
            prompt_selections=(
                PromptRevisionSelection(
                    "character",
                    "character-a",
                    "revision-character-a",
                ),
                PromptRevisionSelection(
                    "scene",
                    "scene-night",
                    "revision-scene-night-old",
                ),
                PromptRevisionSelection(
                    "lighting",
                    "lighting-legacy",
                    "revision-lighting-legacy",
                ),
            ),
            positive_atoms=prompt_atom_usages_from_text(
                "person, historic city, dim ambient background, manual emphasis"
            ),
            negative_atoms=(),
        )
    )

    assert draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-night-old",
        "revision-lighting-legacy",
    )
    assert tuple(
        selected.component.archived for selected in draft.selection.components
    ) == (False, False, True)
    assert draft.prompt.positive_text == (
        "person, historic city, dim ambient background, manual emphasis"
    )
    assert draft.prompt.draft_overridden is True
    assert catalog.calls == [True]


def test_playground_service_rejects_invalid_exact_confirmation_bindings() -> (
    None
):
    service = _service(_CatalogService(_catalog()))
    character = PromptRevisionSelection(
        "character",
        "character-a",
        "revision-character-a",
    )
    scene = PromptRevisionSelection(
        "scene",
        "scene-night",
        "revision-scene-night",
    )

    def confirm(*selections: PromptRevisionSelection) -> None:
        service.confirm_draft(
            ConfirmPlaygroundDraftCommand(
                prompt_selections=selections,
                positive_atoms=(),
                negative_atoms=(),
            )
        )

    with pytest.raises(PromptSelectionError, match="prompt_selections"):
        confirm()
    with pytest.raises(PromptSelectionError, match="kind is required"):
        confirm(replace(character, kind=""))
    with pytest.raises(
        PromptSelectionError, match="component_uid is required"
    ):
        confirm(replace(character, component_uid=""))
    with pytest.raises(PromptSelectionError, match="revision_uid is required"):
        confirm(replace(character, revision_uid=""))
    with pytest.raises(
        PromptSelectionError, match="duplicate prompt component"
    ):
        confirm(character, replace(character, revision_uid="revision-other"))
    with pytest.raises(PromptSelectionError, match="unknown prompt revision"):
        confirm(
            PromptRevisionSelection(
                "character",
                "character-a",
                "revision-missing",
            )
        )
    with pytest.raises(PromptSelectionError, match="does not belong"):
        confirm(
            PromptRevisionSelection(
                "character",
                "scene-night",
                "revision-character-a",
            )
        )
    with pytest.raises(PromptSelectionError, match="is not scene"):
        confirm(
            PromptRevisionSelection(
                "scene",
                "character-a",
                "revision-character-a",
            )
        )
    with pytest.raises(
        PromptSelectionError, match="duplicate prompt revision"
    ):
        confirm(
            character,
            replace(character, kind="scene", component_uid="scene-night"),
        )
    with pytest.raises(PromptSelectionError, match="character revision"):
        confirm(scene)
    with pytest.raises(
        PromptSelectionError, match="duplicate prompt component kind"
    ):
        confirm(
            character,
            scene,
            PromptRevisionSelection(
                "scene",
                "scene-archived",
                "revision-scene-archived",
            ),
        )


def test_playground_service_rejects_repository_revision_order_mismatch() -> (
    None
):
    character = _component("character-a", "character", positive="person")
    mismatched_projection = replace(
        character,
        latest_revision=replace(
            character.latest_revision,
            revision_uid="revision-returned",
        ),
    )

    class _MismatchedConfirmationCatalog(_CatalogService):
        def list_components_for_revisions(
            self,
            revision_uids: tuple[str, ...],
        ) -> tuple[PromptComponent, ...]:
            return (mismatched_projection,)

    service = _service(_MismatchedConfirmationCatalog((character,)))

    with pytest.raises(PromptSelectionError, match="do not match"):
        service.confirm_draft(
            ConfirmPlaygroundDraftCommand(
                prompt_selections=(
                    PromptRevisionSelection(
                        "character",
                        "character-a",
                        "revision-requested",
                    ),
                ),
                positive_atoms=(),
                negative_atoms=(),
            )
        )


def test_playground_service_rechecks_content_level_for_exact_confirmation() -> (
    None
):
    character = _component("character-a", "character", positive="person")
    lewd_pose = _component(
        "pose-lewd",
        "pose",
        positive="explicit pose",
        content_level=ContentLevel.LEWD,
    )
    service = PlaygroundService(
        catalog=_CatalogService((character, lewd_pose)),
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
        preferences=_Preferences(
            WorkspacePreferences(
                enabled_content_levels=(ContentLevel.STANDARD,)
            )
        ),
        content_policy=PromptContentPolicy(),
    )

    with pytest.raises(PromptSelectionError, match="disabled content level"):
        service.confirm_draft(
            ConfirmPlaygroundDraftCommand(
                prompt_selections=(
                    PromptRevisionSelection(
                        "character",
                        "character-a",
                        "revision-character-a",
                    ),
                    PromptRevisionSelection(
                        "pose",
                        "pose-lewd",
                        "revision-pose-lewd",
                    ),
                ),
                positive_atoms=(),
                negative_atoms=(),
            )
        )


def test_playground_service_restores_exact_revisions_and_compositions() -> (
    None
):
    catalog = _CatalogService(_catalog())
    service = _service(catalog)

    revision_draft = service.prepare_revision_draft(
        ("revision-character-a", "revision-scene-night")
    )
    composition_draft = service.prepare_composition_draft("composition-a")

    assert revision_draft.prompt.revision_uids == (
        "revision-character-a",
        "revision-scene-night",
    )
    assert (
        composition_draft.prompt.revision_uids
        == revision_draft.prompt.revision_uids
    )


def test_composition_draft_uses_the_shared_selection_resolver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _service(_CatalogService(_catalog()))
    resolve = service.resolve_composition_selection
    resolved_selections: list[PromptSelection] = []

    def resolve_and_capture(composition_uid: str) -> PromptSelection:
        selection = resolve(composition_uid)
        resolved_selections.append(selection)
        return selection

    monkeypatch.setattr(
        service, "resolve_composition_selection", resolve_and_capture
    )

    draft = service.prepare_composition_draft("composition-a")

    assert len(resolved_selections) == 1
    assert draft.selection is resolved_selections[0]


def test_playground_service_resolves_ordered_exact_composition_selections() -> (
    None
):
    components = _catalog()
    historical_projections = (
        replace(
            components[0],
            latest_revision=replace(
                components[0].latest_revision,
                revision_uid="character-historical",
            ),
        ),
        replace(
            components[1],
            latest_revision=replace(
                components[1].latest_revision,
                revision_uid="scene-historical",
            ),
        ),
        replace(
            components[2],
            latest_revision=replace(
                components[2].latest_revision,
                revision_uid="outfit-historical",
            ),
        ),
        replace(
            components[6],
            latest_revision=replace(
                components[6].latest_revision,
                revision_uid="modifier-historical",
            ),
        ),
    )

    class _HistoricalCompositionCatalog(_CatalogService):
        def list_composition_components(
            self,
            composition_uid: str,
        ) -> tuple[PromptComponent, ...]:
            assert composition_uid == "composition-historical"
            return historical_projections

    service = _service(_HistoricalCompositionCatalog(components))
    selected = service.resolve_composition_selection("composition-historical")
    draft = service.prepare_composition_draft("composition-historical")

    assert tuple(item.component.kind for item in selected.components) == (
        "character",
        "scene",
        "outfit",
        "modifier",
    )
    assert tuple(
        item.component.component_uid for item in selected.components
    ) == (
        "character-a",
        "scene-night",
        "outfit-red",
        "modifier-a",
    )
    expected_revisions = (
        "character-historical",
        "scene-historical",
        "outfit-historical",
        "modifier-historical",
    )
    assert (
        tuple(item.revision.revision_uid for item in selected.components)
        == expected_revisions
    )
    assert (
        tuple(
            item.revision.revision_uid for item in draft.selection.components
        )
        == expected_revisions
    )


def test_playground_service_rejects_compositions_without_character() -> None:
    class _NoCharacterCompositionCatalog(_CatalogService):
        def list_composition_components(
            self,
            composition_uid: str,
        ) -> tuple[PromptComponent, ...]:
            return self.components[1:2]

    for prepare in (
        lambda service: service.resolve_composition_selection(
            "composition-no-character"
        ),
        lambda service: service.prepare_composition_draft(
            "composition-no-character"
        ),
    ):
        with pytest.raises(PromptSelectionError, match="character revision"):
            prepare(_service(_NoCharacterCompositionCatalog(_catalog())))


def test_playground_service_rejects_duplicate_composition_kinds() -> None:
    components = _catalog()

    class _DuplicateCompositionCatalog(_CatalogService):
        def _duplicate(self) -> PromptComponent:
            return replace(
                components[0],
                component_uid="character-b",
                component_key="character_b_key",
                latest_revision=replace(
                    components[0].latest_revision,
                    revision_uid="character-b-revision",
                ),
            )

        def list_components(
            self,
            *,
            include_archived: bool = False,
        ) -> tuple[PromptComponent, ...]:
            return (*self.components, self._duplicate())

        def list_composition_components(
            self,
            composition_uid: str,
        ) -> tuple[PromptComponent, ...]:
            return components[0], self._duplicate()

    for prepare in (
        lambda service: service.resolve_composition_selection(
            "composition-duplicate"
        ),
        lambda service: service.prepare_composition_draft(
            "composition-duplicate"
        ),
    ):
        with pytest.raises(PromptSelectionError, match="duplicate prompt"):
            prepare(_service(_DuplicateCompositionCatalog(components)))


def test_playground_service_rejects_archived_composition_components() -> None:
    class _ArchivedCompositionCatalog(_CatalogService):
        def list_composition_components(
            self,
            composition_uid: str,
        ) -> tuple[PromptComponent, ...]:
            return self.components[0], self.components[8]

    for prepare in (
        lambda service: service.resolve_composition_selection(
            "composition-archived"
        ),
        lambda service: service.prepare_composition_draft(
            "composition-archived"
        ),
    ):
        with pytest.raises(
            PromptSelectionError, match="inactive prompt component"
        ):
            prepare(_service(_ArchivedCompositionCatalog(_catalog())))


def test_playground_service_rejects_policy_disallowed_compositions() -> None:
    components = _catalog()
    lewd = _component(
        "pose-lewd",
        "pose",
        content_level=ContentLevel.LEWD,
    )

    class _PolicyDisallowedCompositionCatalog(_CatalogService):
        def list_composition_components(
            self,
            composition_uid: str,
        ) -> tuple[PromptComponent, ...]:
            return self.components[0], lewd

        def list_components(
            self,
            *,
            include_archived: bool = False,
        ) -> tuple[PromptComponent, ...]:
            return (*self.components, lewd)

    for prepare in (
        lambda service: service.resolve_composition_selection(
            "composition-policy-disallowed"
        ),
        lambda service: service.prepare_composition_draft(
            "composition-policy-disallowed"
        ),
    ):
        with pytest.raises(
            PromptSelectionError, match="disabled content level"
        ):
            prepare(_service(_PolicyDisallowedCompositionCatalog(components)))


def test_playground_service_requires_a_composition_identity() -> None:
    with pytest.raises(PromptSelectionError, match="composition_uid"):
        _service(_CatalogService(_catalog())).resolve_composition_selection(
            " "
        )


def test_playground_service_uses_authoritative_image_snapshot() -> None:
    service = _service(_CatalogService(_catalog()))
    image = SimpleNamespace(
        scopes=(),
        prompt_snapshot=SimpleNamespace(
            positive="historic style, character",
            negative="historic blur",
            draft_overridden=True,
        ),
    )

    draft = service.prepare_image_snapshot(cast(Any, image))

    assert draft.selection.components == ()
    assert draft.prompt.positive_text == "historic style, character"
    assert draft.prompt.negative_text == "historic blur"
    assert draft.prompt.revision_uids == ()
    assert draft.prompt.draft_overridden is True

    grouped_image = SimpleNamespace(
        scopes=(SimpleNamespace(revision_uid="revision-character-a"),),
        prompt_snapshot=SimpleNamespace(
            positive="historic style, character",
            negative="historic blur",
            draft_overridden=False,
        ),
    )
    overridden = service.prepare_image_snapshot(
        cast(Any, grouped_image),
        overrides=PromptDraftOverrides(
            positive_atoms=prompt_atom_usages_from_text("manual positive"),
            negative_atoms=prompt_atom_usages_from_text("manual negative"),
        ),
    )
    assert (
        overridden.selection.components[0].component.component_uid
        == "character-a"
    )
    assert overridden.prompt.positive_text == "manual positive"
    assert overridden.prompt.negative_text == "manual negative"


def test_playground_service_rejects_disabled_exact_revision_handoff() -> None:
    catalog = _CatalogService(
        (
            _component("character-a", "character"),
            _component(
                "modifier-nude",
                "modifier",
                tags=("nsfw_level_nude",),
                content_level=ContentLevel.NUDE,
            ),
        )
    )

    with pytest.raises(PromptSelectionError, match="disabled content level"):
        _service(catalog).prepare_revision_draft(
            ("revision-character-a", "revision-modifier-nude")
        )


@pytest.mark.parametrize(
    ("revision_uids", "message"),
    (
        ((), "required"),
        (("",), "required"),
        (("revision-character-a", "revision-character-a"), "duplicate"),
        (("missing",), "unknown"),
        (("revision-scene-night",), "character"),
    ),
)
def test_playground_service_rejects_invalid_revision_handoffs(
    revision_uids: tuple[str, ...],
    message: str,
) -> None:
    service = _service(_CatalogService(_catalog()))

    with pytest.raises(PromptSelectionError, match=message):
        service.prepare_revision_draft(revision_uids)
    with pytest.raises(PromptSelectionError, match="composition_uid"):
        service.prepare_composition_draft("")


def test_playground_service_rejects_duplicate_kinds_in_exact_handoff() -> None:
    catalog = _CatalogService(
        (
            _component("character-a", "character"),
            _component("character-b", "character"),
        )
    )
    service = _service(catalog)

    with pytest.raises(
        PromptSelectionError, match="duplicate prompt component kind"
    ):
        service.prepare_revision_draft(
            ("revision-character-a", "revision-character-b")
        )
