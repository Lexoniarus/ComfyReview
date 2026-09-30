"""Behavior contracts for canonical prompt-catalog HTTP view models."""

from __future__ import annotations

from typing import cast

from comfyreview.application import (
    CreatePromptComponentCommand,
    PromptCatalogService,
    PromptComponent,
    PromptRevision,
    UpdatePromptComponentCommand,
)
from services.prompt_catalog_view_service import PromptCatalogViewService


def _component(
    uid: str,
    kind: str,
    *,
    name: str | None = None,
    tags: tuple[str, ...] = (),
    archived: bool = False,
) -> PromptComponent:
    return PromptComponent(
        component_uid=uid,
        kind=kind,
        component_key=f"key-{uid}",
        name=name or uid,
        tags=tags,
        notes=f"notes-{uid}",
        archived=archived,
        latest_revision=PromptRevision(
            revision_uid=f"revision-{uid}",
            revision_number=2,
            positive_text=f"positive-{uid}",
            negative_text=f"negative-{uid}",
            content_hash=f"hash-{uid}",
        ),
    )


class _Catalog:
    def __init__(self) -> None:
        self.components = (
            _component("character-a", "character", tags=("hero",)),
            _component("scene-a", "scene", name="Moon City"),
            _component("scene-old", "scene", archived=True),
        )
        self.created: CreatePromptComponentCommand | None = None
        self.updated: UpdatePromptComponentCommand | None = None
        self.archive_call: tuple[str, bool] | None = None

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        if include_archived:
            return self.components
        return tuple(item for item in self.components if not item.archived)

    def create_component(
        self,
        command: CreatePromptComponentCommand,
    ) -> PromptComponent:
        self.created = command
        return self.components[1]

    def update_component(
        self,
        command: UpdatePromptComponentCommand,
    ) -> PromptComponent:
        self.updated = command
        return self.components[1]

    def set_archived(
        self,
        component_uid: str,
        *,
        archived: bool,
    ) -> PromptComponent:
        self.archive_call = (component_uid, archived)
        return self.components[1]

    def get_component(self, component_uid: str) -> PromptComponent:
        return next(
            item
            for item in self.components
            if item.component_uid == component_uid
        )


def _service(catalog: _Catalog) -> PromptCatalogViewService:
    return PromptCatalogViewService(cast(PromptCatalogService, catalog))


def test_catalog_view_lists_filters_and_maps_latest_revision() -> None:
    catalog = _Catalog()
    service = _service(catalog)

    rows = service.list_items(kind="scene", query="moon")

    assert rows == [
        {
            "id": "scene-a",
            "kind": "scene",
            "name": "Moon City",
            "key": "key-scene-a",
            "tags": "",
            "pos": "positive-scene-a",
            "neg": "negative-scene-a",
            "notes": "notes-scene-a",
            "archived": False,
            "revision_uid": "revision-scene-a",
        }
    ]
    assert service.list_items(query="missing") == []


def test_catalog_view_groups_only_active_dropdown_components() -> None:
    grouped = _service(_Catalog()).dropdown_items()

    assert [item["id"] for item in grouped["characters"]] == ["character-a"]
    assert [item["id"] for item in grouped["scenes"]] == ["scene-a"]
    assert grouped["outfits"] == []


def test_catalog_view_translates_create_and_atomic_update_commands() -> None:
    catalog = _Catalog()
    service = _service(catalog)

    created = service.create(
        kind=" scene ",
        name=" Moon City ",
        tags="night, city, night",
        positive_text="moon",
        negative_text="day",
        notes="note",
    )
    updated = service.update(
        component_uid="scene-a",
        name="New Moon",
        tags="night, blue",
        positive_text="new moon",
        negative_text="sun",
        notes="new note",
    )

    assert created.component_uid == "scene-a"
    assert updated.component_uid == "scene-a"
    assert catalog.created == CreatePromptComponentCommand(
        kind=" scene ",
        component_key="",
        name=" Moon City ",
        tags=("night", "city", "night"),
        notes="note",
        positive_text="moon",
        negative_text="day",
    )
    assert catalog.updated == UpdatePromptComponentCommand(
        component_uid="scene-a",
        name="New Moon",
        tags=("night", "blue"),
        notes="new note",
        positive_text="new moon",
        negative_text="sun",
    )


def test_catalog_view_archives_and_restores_by_stable_uid() -> None:
    catalog = _Catalog()
    service = _service(catalog)

    service.set_archived("scene-a", archived=True)
    assert catalog.archive_call == ("scene-a", True)

    service.set_archived("scene-a", archived=False)
    assert catalog.archive_call == ("scene-a", False)


def test_catalog_view_reads_prompt_tokens_by_uid_and_scope() -> None:
    service = _service(_Catalog())

    assert service.prompt_tokens("scene-a", scope="pos") == [
        "positive-scene-a"
    ]
    assert service.prompt_tokens("scene-a", scope="neg") == [
        "negative-scene-a"
    ]

    import pytest

    with pytest.raises(ValueError, match="scope must be pos or neg"):
        service.prompt_tokens("scene-a", scope="unsupported")
