"""Integration tests for catalog-backed Playground preview drafts."""

from __future__ import annotations

from typing import Any

from comfyreview.application import (
    PlaygroundService,
    PromptComponent,
    PromptRenderer,
    PromptRevision,
    PromptSelectionPolicy,
    imported_prompt_component_uid,
)
from services.playground_generator_ui import generation
from services.playground_generator_ui.types import DiscoveryLists


class _Catalog:
    def __init__(self, components: tuple[PromptComponent, ...]) -> None:
        self._components = components

    def list_components(
        self,
        *,
        include_archived: bool = False,
    ) -> tuple[PromptComponent, ...]:
        assert include_archived is False
        return self._components


def _component(
    source_id: int,
    kind: str,
    positive: str,
    *,
    negative: str = "",
    tags: tuple[str, ...] = (),
) -> PromptComponent:
    uid = imported_prompt_component_uid("legacy_playground", str(source_id))
    return PromptComponent(
        component_uid=uid,
        kind=kind,
        component_key=f"{kind}_{source_id}",
        name=f"{kind}-{source_id}",
        tags=tags,
        notes="",
        archived=False,
        latest_revision=PromptRevision(
            revision_uid=f"revision-{source_id}",
            revision_number=1,
            positive_text=positive,
            negative_text=negative,
            content_hash=f"hash-{source_id}",
        ),
    )


def test_preview_generation_uses_catalog_revisions_and_keeps_legacy_submit_shape(
    monkeypatch,
) -> None:
    components = (
        _component(1, "character", "person", negative="bad anatomy"),
        _component(2, "scene", "city at night", tags=("night",)),
        _component(3, "outfit", "red skirt"),
        _component(4, "pose", "standing"),
        _component(5, "expression", "smile"),
        _component(6, "lighting", "soft light"),
        _component(7, "modifier", "wind", tags=("wind",)),
    )
    playground = PlaygroundService(
        catalog=_Catalog(components),
        selection_policy=PromptSelectionPolicy(),
        renderer=PromptRenderer(),
    )
    monkeypatch.setattr(
        generation,
        "workflow_render_defaults",
        lambda **_values: {
            "checkpoint_name": "model.safetensors",
            "sampler_name": "euler",
            "scheduler_name": "normal",
            "steps": "20",
            "cfg": "7",
            "denoise": "1",
        },
    )
    head: dict[str, Any] = {
        "character_id": 1,
        "scene_id": 2,
        "outfit_id": 3,
        "pose_id": 4,
        "expression_id": 5,
        "lighting_id": 6,
        "modifier_id": 7,
        "include_lighting": True,
        "include_modifier": True,
        "gen_seed": "13",
        "comfy_seed": "42",
        "max_tries": 5,
        "batch_runs": 1,
    }

    drafts = generation.generate_preview_drafts(
        head=head,
        characters=[{"id": 1, "name": "Aiko", "key": "aiko"}],
        discovery=DiscoveryLists([], [], []),
        playground_service=playground,
    )

    assert len(drafts) == 1
    assert drafts[0]["prompt_positive"] == (
        "person, city at night, red skirt, standing, smile, soft light, wind"
    )
    assert drafts[0]["prompt_negative"] == "bad anatomy"
    assert drafts[0]["selection"]["scene"]["component_uid"] == (
        imported_prompt_component_uid("legacy_playground", "2")
    )
    assert drafts[0]["selection"]["scene"]["revision_uid"] == "revision-2"
    assert drafts[0]["seed"] == 42
    assert drafts[0]["checkpoint"] == "model.safetensors"
    assert drafts[0]["subdir"] == "playground/Aiko"
