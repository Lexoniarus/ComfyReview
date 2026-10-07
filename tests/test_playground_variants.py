"""Behavior tests for transient Playground variant preparation."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pytest

from comfyreview.application import (
    GenerationValidationError,
    PlaygroundDraft,
    PlaygroundVariantDiversityPolicy,
    PlaygroundVariantPreparationService,
    PlaygroundVariantSpecification,
    PromptComponent,
    PromptRevision,
    PromptSelection,
    PromptSelectionCommand,
    RenderedPrompt,
    SecurePlaygroundVariantEntropySource,
    SelectedPromptComponent,
    UuidPlaygroundVariantIdentitySource,
)


class _Entropy:
    def next_seed(self) -> int:
        return 9173


class _Identities:
    def __init__(self) -> None:
        self.value = 0

    def new_draft_uid(self) -> str:
        self.value += 1
        return f"draft-{self.value}"


class _Playground:
    def __init__(self, character_count: int) -> None:
        self.character_count = character_count
        self.selection_seeds: list[int] = []

    def prepare_draft(self, command, *, overrides=None):
        assert overrides is None
        selection_seed = int(command.seed)
        self.selection_seeds.append(selection_seed)
        index = selection_seed % self.character_count
        component = _component(index)
        selected = SelectedPromptComponent(
            component,
            component.latest_revision,
        )
        return PlaygroundDraft(
            PromptSelection((selected,)),
            RenderedPrompt(
                positive_text=component.latest_revision.positive_text,
                negative_text="",
                notes="",
                revision_uids=(component.latest_revision.revision_uid,),
                draft_overridden=False,
            ),
        )


def _component(index: int) -> PromptComponent:
    return PromptComponent(
        component_uid=f"character-{index}",
        kind="character",
        component_key=f"character_{index}",
        name=f"Character {index}",
        tags=(),
        notes="",
        archived=False,
        latest_revision=PromptRevision(
            revision_uid=f"revision-character-{index}",
            revision_number=1,
            positive_text=f"character {index}",
            negative_text="",
            content_hash=f"hash-{index}",
        ),
    )


def _service(
    character_count: int,
) -> tuple[PlaygroundVariantPreparationService, _Playground]:
    playground = _Playground(character_count)
    service = PlaygroundVariantPreparationService(
        playground=cast(Any, playground),
        diversity=PlaygroundVariantDiversityPolicy(),
        entropy=_Entropy(),
        identities=_Identities(),
    )
    return service, playground


def _specification(**changes: Any) -> PlaygroundVariantSpecification:
    specification = PlaygroundVariantSpecification(
        variant_count=4,
        generation_seed=42,
        randomize_seed=False,
        steps_min=28,
        steps_max=28,
        cfg_min=6.5,
        cfg_max=6.5,
        cfg_step=0.1,
    )
    return replace(specification, **changes)


def test_variant_preparation_separates_selection_entropy_from_fixed_seed() -> (
    None
):
    service, playground = _service(4)

    result = service.prepare(PromptSelectionCommand(""), _specification())

    assert len(result.variants) == 4
    assert result.unique_count == 4
    assert result.repeated_count == 0
    assert not result.diversity_exhausted
    assert {item.seed for item in result.variants} == {42}
    assert (
        len(
            {
                item.draft.selection.components[0].component.component_uid
                for item in result.variants
            }
        )
        == 4
    )
    assert len(set(playground.selection_seeds)) > 1


def test_variant_preparation_reports_exhausted_diversity() -> None:
    service, _playground = _service(1)

    result = service.prepare(PromptSelectionCommand(""), _specification())

    assert len(result.variants) == 4
    assert result.unique_count == 1
    assert result.repeated_count == 3
    assert result.diversity_exhausted
    assert len({item.draft_uid for item in result.variants}) == 4


def test_variant_preparation_varies_a_static_prompt_without_reselection() -> (
    None
):
    service, _playground = _service(1)
    component = _component(0)
    draft = PlaygroundDraft(
        PromptSelection(
            (SelectedPromptComponent(component, component.latest_revision),)
        ),
        RenderedPrompt("prompt", "", "", ("revision-character-0",), False),
    )

    result = service.prepare_static(
        draft,
        _specification(steps_max=31),
    )

    assert len(result.variants) == 4
    assert {item.steps for item in result.variants} == {28, 29, 30, 31}
    assert all(item.draft is draft for item in result.variants)


def test_variant_preparation_includes_non_aligned_cfg_maximum() -> None:
    service, _playground = _service(1)

    result = service.prepare(
        PromptSelectionCommand(""),
        _specification(variant_count=2, cfg_max=6.55, cfg_step=0.1),
    )

    assert {item.cfg for item in result.variants} == {6.5, 6.55}


@pytest.mark.parametrize(
    ("changes", "message"),
    (
        ({"variant_count": 0}, "variant_count"),
        ({"variant_count": 13}, "variant_count"),
        ({"steps_min": 0}, "steps"),
        ({"steps_max": 101}, "steps"),
        ({"cfg_min": 0}, "cfg range"),
        ({"cfg_max": 31}, "cfg range"),
        ({"cfg_step": 0}, "cfg_step"),
    ),
)
def test_variant_preparation_rejects_invalid_bounds(
    changes: dict[str, Any],
    message: str,
) -> None:
    service, _playground = _service(1)

    with pytest.raises(GenerationValidationError, match=message):
        service.prepare(
            PromptSelectionCommand(""),
            _specification(**changes),
        )


def test_variant_diversity_signature_ignores_transient_draft_identity() -> (
    None
):
    service, _playground = _service(1)
    result = service.prepare(
        PromptSelectionCommand(""),
        _specification(variant_count=1),
    )
    variant = result.variants[0]

    assert PlaygroundVariantDiversityPolicy().signature(variant) == (
        PlaygroundVariantDiversityPolicy().signature(
            replace(variant, draft_uid="another-draft")
        )
    )


def test_default_variant_sources_return_bounded_opaque_values() -> None:
    seed = SecurePlaygroundVariantEntropySource().next_seed()
    identities = UuidPlaygroundVariantIdentitySource()
    first = identities.new_draft_uid()
    second = identities.new_draft_uid()

    assert 0 <= seed < 2**63
    assert first.startswith("draft-")
    assert first != second
