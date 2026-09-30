"""Behavior tests for canonical prompt-label presentation."""

from __future__ import annotations

from typing import cast

from comfyreview.application import (
    PromptCatalogService,
    PromptComponent,
    PromptRevision,
)
from services.playground_label_service import PromptLabels, PromptLabelService


def _component(
    uid: str,
    kind: str,
    positive: str,
    *,
    name: str | None = None,
    archived: bool = False,
) -> PromptComponent:
    return PromptComponent(
        component_uid=uid,
        kind=kind,
        component_key=f"key-{uid}",
        name=name or uid,
        tags=(),
        notes="",
        archived=archived,
        latest_revision=PromptRevision(
            revision_uid=f"revision-{uid}",
            revision_number=1,
            positive_text=positive,
            negative_text="",
            content_hash=f"hash-{uid}",
        ),
    )


class _Catalog:
    def __init__(self, components: tuple[PromptComponent, ...]) -> None:
        self._components = components

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        assert not include_archived
        return tuple(item for item in self._components if not item.archived)


def _service(*components: PromptComponent) -> PromptLabelService:
    catalog = cast(PromptCatalogService, _Catalog(tuple(components)))
    return PromptLabelService(catalog)


def test_prompt_labels_use_longest_active_revision_matches() -> None:
    service = _service(
        _component("scene-short", "scene", "city", name="City"),
        _component(
            "scene-long",
            "scene",
            "moon   city",
            name="Moon City",
        ),
        _component("outfit", "outfit", "red dress", name="Red Dress"),
        _component("pose", "pose", "standing", name="Standing"),
        _component("expression", "expression", "smile", name="Smile"),
        _component("lighting", "lighting", "soft light", name="Soft"),
        _component("modifier-a", "modifier", "wind", name="Wind"),
        _component("modifier-b", "modifier", "rain", name="Rain"),
        _component("empty", "scene", ""),
        _component("archived", "scene", "secret", archived=True),
    )

    labels = service.resolve(
        "moon city, red dress, standing, smile, soft light, wind, rain"
    )

    assert labels == PromptLabels(
        scene_name="Moon City",
        outfit_name="Red Dress",
        pose_name="Standing",
        expression_name="Smile",
        modifiers=("Wind", "Rain"),
        light_name="Soft",
    )


def test_prompt_labels_can_omit_lighting_and_limit_modifiers() -> None:
    modifiers = tuple(
        _component(f"modifier-{index}", "modifier", f"m{index}")
        for index in range(15)
    )
    service = _service(
        _component("lighting", "lighting", "bright", name="Bright"),
        *modifiers,
    )

    labels = service.resolve(
        "bright, " + ", ".join(f"m{index}" for index in range(15)),
        include_lighting=False,
    )

    assert labels.light_name == ""
    assert len(labels.modifiers) == 12
