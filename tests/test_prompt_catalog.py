"""Behavior and SQLite integration tests for the canonical prompt catalog."""

from __future__ import annotations

import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application import (
    CreatePromptComponentCommand,
    NewPromptComponent,
    PromptCatalogService,
    PromptCatalogValidationError,
    PromptComponent,
    PromptRevision,
    PromptRevisionDraft,
    RevisePromptComponentCommand,
    UpdatePromptComponentCommand,
    UpdatePromptComponentMetadataCommand,
    imported_prompt_component_uid,
    prompt_component_key,
    prompt_revision_identity,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqlitePromptCatalogRepository,
)


class _FixedIdentities:
    def new_component_uid(self) -> str:
        return "prompt-component-fixed"


class _CatalogRepository:
    def __init__(self) -> None:
        self.component: PromptComponent | None = None
        self.include_archived: bool | None = None

    def create(self, component: NewPromptComponent) -> PromptComponent:
        revision = PromptRevision(
            revision_uid=component.revision.revision_uid,
            revision_number=1,
            positive_text=component.revision.positive_text,
            negative_text=component.revision.negative_text,
            content_hash=component.revision.content_hash,
        )
        self.component = PromptComponent(
            component_uid=component.component_uid,
            kind=component.kind,
            component_key=component.component_key,
            name=component.name,
            tags=component.tags,
            notes=component.notes,
            archived=False,
            latest_revision=revision,
        )
        return self.component

    def add_revision(
        self,
        component_uid: str,
        revision: PromptRevisionDraft,
    ) -> PromptRevision:
        assert component_uid == "prompt-component-fixed"
        return PromptRevision(
            revision.revision_uid,
            2,
            revision.positive_text,
            revision.negative_text,
            revision.content_hash,
        )

    def update_metadata(
        self,
        command: UpdatePromptComponentMetadataCommand,
    ) -> PromptComponent:
        assert self.component is not None
        self.component = replace(
            self.component,
            name=command.name,
            tags=command.tags,
            notes=command.notes,
        )
        return self.component

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        assert self.component is not None
        assert component_uid == self.component.component_uid
        self.component = replace(self.component, archived=archived)
        return self.component

    def update_component(self, metadata, revision):
        assert self.component is not None
        self.component = replace(
            self.component,
            name=metadata.name,
            tags=metadata.tags,
            notes=metadata.notes,
            latest_revision=PromptRevision(
                revision.revision_uid,
                self.component.latest_revision.revision_number + 1,
                revision.positive_text,
                revision.negative_text,
                revision.content_hash,
            ),
        )
        return self.component

    def get_component(self, component_uid):
        assert self.component is not None
        assert component_uid == self.component.component_uid
        return self.component

    def list_components(
        self,
        *,
        include_archived: bool,
    ) -> tuple[PromptComponent, ...]:
        self.include_archived = include_archived
        return () if self.component is None else (self.component,)


def _service() -> tuple[PromptCatalogService, _CatalogRepository]:
    repository = _CatalogRepository()
    return (
        PromptCatalogService(
            repository=repository,
            identities=_FixedIdentities(),
        ),
        repository,
    )


def _create_command() -> CreatePromptComponentCommand:
    return CreatePromptComponentCommand(
        kind=" scene ",
        component_key=" rooftop_scene ",
        name=" Rooftop ",
        tags=(" night ", "", "night", "city"),
        notes=" reusable ",
        positive_text=" skyline ",
        negative_text=" blur ",
    )


def test_prompt_revision_identity_is_content_and_component_stable() -> None:
    first = prompt_revision_identity("component", "hero", "blur")
    repeated = prompt_revision_identity("component", "hero", "blur")
    changed_component = prompt_revision_identity("other", "hero", "blur")

    assert first == repeated
    assert first[0].startswith("prompt-revision-")
    assert changed_component[0] != first[0]
    assert changed_component[1] == first[1]


def test_imported_prompt_component_identity_is_stable_and_source_scoped() -> (
    None
):
    first = imported_prompt_component_uid("legacy_playground", "17")

    assert first == imported_prompt_component_uid("legacy_playground", "17")
    assert first != imported_prompt_component_uid("another_source", "17")
    with pytest.raises(
        PromptCatalogValidationError,
        match="requires source and source_key",
    ):
        imported_prompt_component_uid("", "17")


def test_prompt_catalog_service_creates_normalized_component() -> None:
    service, _repository = _service()

    component = service.create_component(_create_command())

    assert component.component_uid == "prompt-component-fixed"
    assert component.kind == "scene"
    assert component.component_key == "rooftop_scene"
    assert component.name == "Rooftop"
    assert component.tags == ("night", "city")
    assert component.notes == "reusable"
    assert component.latest_revision.positive_text == "skyline"

    generated = service.create_component(
        replace(_create_command(), component_key="")
    )
    assert generated.component_key.startswith("rooftop_scene_")


def test_prompt_component_key_is_readable_and_identity_scoped() -> None:
    first = prompt_component_key("scene", " Café Roof! ", "component-1")

    assert first.startswith("cafe_roof_scene_")
    assert first == prompt_component_key(
        "scene", " Café Roof! ", "component-1"
    )
    assert first != prompt_component_key("scene", "Café Roof!", "component-2")
    assert prompt_component_key("pose", "***", "component-1").startswith(
        "item_pose_"
    )


@pytest.mark.parametrize(
    ("field", "command"),
    [
        ("kind", replace(_create_command(), kind="")),
        ("name", replace(_create_command(), name="")),
        (
            "prompt revision",
            replace(_create_command(), positive_text="", negative_text=""),
        ),
    ],
)
def test_prompt_catalog_service_rejects_invalid_component(
    field: str,
    command: CreatePromptComponentCommand,
) -> None:
    service, _repository = _service()

    with pytest.raises(PromptCatalogValidationError, match=field):
        service.create_component(command)


def test_prompt_catalog_service_appends_immutable_revision() -> None:
    service, _repository = _service()

    revision = service.add_revision(
        RevisePromptComponentCommand(
            component_uid=" prompt-component-fixed ",
            positive_text=" hero:1.2 ",
            negative_text=" blur ",
        )
    )

    assert revision.revision_number == 2
    assert revision.positive_text == "hero:1.2"

    with pytest.raises(PromptCatalogValidationError, match="prompt revision"):
        service.add_revision(
            RevisePromptComponentCommand(
                component_uid="prompt-component-fixed",
                positive_text="",
                negative_text="",
            )
        )


def test_prompt_catalog_service_updates_only_mutable_metadata() -> None:
    service, _repository = _service()
    original = service.create_component(_create_command())

    updated = service.update_metadata(
        UpdatePromptComponentMetadataCommand(
            component_uid=original.component_uid,
            name=" Rooftop Night ",
            tags=("night", "night", "urban"),
            notes=" edited ",
        )
    )

    assert updated.name == "Rooftop Night"
    assert updated.tags == ("night", "urban")
    assert updated.notes == "edited"
    assert updated.latest_revision == original.latest_revision

    with pytest.raises(PromptCatalogValidationError, match="name"):
        service.update_metadata(
            UpdatePromptComponentMetadataCommand(
                component_uid=original.component_uid,
                name="",
                tags=(),
                notes="",
            )
        )


def test_prompt_catalog_service_updates_metadata_and_revision_atomically() -> (
    None
):
    service, _repository = _service()
    original = service.create_component(_create_command())

    updated = service.update_component(
        UpdatePromptComponentCommand(
            component_uid=original.component_uid,
            name=" Rainy Rooftop ",
            tags=(" rain ", "rain"),
            notes=" changed ",
            positive_text=" skyline, rain ",
            negative_text=" blur ",
        )
    )

    assert updated.name == "Rainy Rooftop"
    assert updated.tags == ("rain",)
    assert updated.latest_revision.revision_number == 2
    assert service.get_component(original.component_uid) == updated

    with pytest.raises(PromptCatalogValidationError, match="prompt revision"):
        service.update_component(
            UpdatePromptComponentCommand(
                original.component_uid,
                "name",
                (),
                "",
                "",
                "",
            )
        )


def test_prompt_catalog_service_archives_restores_and_lists() -> None:
    service, repository = _service()
    component = service.create_component(_create_command())

    archived = service.set_archived(component.component_uid, archived=True)
    restored = service.set_archived(component.component_uid, archived=False)
    listed = service.list_components(include_archived=True)

    assert archived.archived is True
    assert restored.archived is False
    assert listed == (restored,)
    assert repository.include_archived is True

    with pytest.raises(PromptCatalogValidationError, match="component_uid"):
        service.set_archived("", archived=True)


def test_sqlite_prompt_catalog_preserves_revisions_and_archive_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    service = PromptCatalogService(
        repository=SqlitePromptCatalogRepository(database_path),
        identities=_FixedIdentities(),
    )

    created = service.create_component(_create_command())
    revision = service.add_revision(
        RevisePromptComponentCommand(
            component_uid=created.component_uid,
            positive_text="skyline, rain",
            negative_text="blur",
        )
    )
    repeated = service.add_revision(
        RevisePromptComponentCommand(
            component_uid=created.component_uid,
            positive_text="skyline, rain",
            negative_text="blur",
        )
    )
    renamed = service.update_metadata(
        UpdatePromptComponentMetadataCommand(
            component_uid=created.component_uid,
            name="Rainy Rooftop",
            tags=("rain",),
            notes="catalog metadata",
        )
    )
    service.set_archived(created.component_uid, archived=True)

    assert revision == repeated
    assert revision.revision_number == 2
    assert renamed.latest_revision == revision
    assert service.list_components() == ()
    [archived] = service.list_components(include_archived=True)
    assert archived.archived is True
    assert archived.name == "Rainy Rooftop"
    updated = service.update_component(
        UpdatePromptComponentCommand(
            component_uid=created.component_uid,
            name="Storm Rooftop",
            tags=("storm",),
            notes="atomic",
            positive_text="skyline, storm",
            negative_text="blur",
        )
    )
    assert updated.latest_revision.revision_number == 3
    assert service.get_component(created.component_uid) == updated
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_components"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_revisions"
        ).fetchone() == (3,)
