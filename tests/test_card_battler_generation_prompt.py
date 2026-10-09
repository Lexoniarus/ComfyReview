"""Behavior tests for the Card Battler generation prompt handoff."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from typing import Literal

import pytest

from comfyreview.application.card_battler_generation_prompt import (
    CardEvolutionPromptAdapter,
    CardEvolutionPromptHandoff,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_visual_selection import (
    _VisualPromptSelectionPolicy,
)
from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptProvenance,
    VisualPromptRecipe,
)
from comfyreview.domain.prompts import (
    PromptAtomUsage,
    render_prompt_atom_usages,
)


def _atom(
    key: str, text: str, scope: Literal["positive", "negative"], weight: int
) -> VisualPromptAtom:
    return VisualPromptAtom(
        key=key,
        canonical_text=text,
        scope=scope,
        weight_milli=weight,
        required=False,
        priority=5,
        sources=(
            VisualPromptAtomSource("semantic", "source", "optional", 1000, 5),
        ),
    )


def _recipe() -> VisualPromptRecipe:
    return VisualPromptRecipe(
        tier_ordinal=3,
        positive_atoms=(
            _atom("z", "glowing freckles", "positive", 1137),
            _atom("a", "wide angle", "positive", 1000),
            _atom("m", "storm clouds", "positive", 875),
        ),
        negative_atoms=(
            _atom("x", "motion blur", "negative", 1250),
            _atom("b", "extra limbs", "negative", 1000),
        ),
        diagnostics=(),
        provenance=VisualPromptProvenance(
            "prototype",
            2,
            "weighted_atom_projection",
            3,
            42,
            "sha256-domain-v1",
            VISUAL_PROMPT_PROJECTION_REVISION,
        ),
    )


def test_card_prompt_adapter_preserves_scopes_weights_and_order() -> None:
    recipe = _recipe()

    actual = CardEvolutionPromptAdapter.adapt(recipe)

    assert actual == CardEvolutionPromptHandoff(
        positive_atoms=(
            PromptAtomUsage("glowing freckles", 1137),
            PromptAtomUsage("wide angle", 1000),
            PromptAtomUsage("storm clouds", 875),
        ),
        negative_atoms=(
            PromptAtomUsage("motion blur", 1250),
            PromptAtomUsage("extra limbs", 1000),
        ),
    )
    assert isinstance(actual.positive_atoms, tuple)
    assert isinstance(actual.negative_atoms, tuple)


def test_card_evolution_prompt_adapter_is_repeatable_and_nonmutating() -> None:
    recipe = _recipe()
    original = deepcopy(recipe)

    first = CardEvolutionPromptAdapter.adapt(recipe)
    second = CardEvolutionPromptAdapter.adapt(recipe)

    assert first == second
    assert recipe == original


def test_card_evolution_prompt_adapter_never_reselects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("prompt adapter must not invoke selection or RNG")

    monkeypatch.setattr(
        DomainSeparatedCardRandom, "weighted_choice", fail_if_called
    )
    monkeypatch.setattr(
        _VisualPromptSelectionPolicy, "_select", fail_if_called
    )

    assert len(CardEvolutionPromptAdapter.adapt(_recipe()).positive_atoms) == 3


def test_card_evolution_prompt_adapter_uses_generic_renderer_syntax() -> None:
    adapted = CardEvolutionPromptAdapter.adapt(_recipe())

    assert render_prompt_atom_usages(adapted.positive_atoms) == (
        "(glowing freckles:1.137), wide angle, (storm clouds:0.875)"
    )
    assert render_prompt_atom_usages(adapted.negative_atoms) == (
        "(motion blur:1.25), extra limbs"
    )


def test_card_evolution_prompt_adapter_preserves_empty_scopes() -> None:
    empty = replace(_recipe(), positive_atoms=(), negative_atoms=())

    result = CardEvolutionPromptAdapter.adapt(empty)

    assert result.positive_atoms == ()
    assert result.negative_atoms == ()
