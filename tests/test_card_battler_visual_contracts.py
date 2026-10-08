"""Behavior tests for immutable visual prompt recipe contracts."""

from __future__ import annotations

from collections.abc import Callable
from typing import Literal

import pytest

from comfyreview.application.card_battler_visuals import (
    VISUAL_PROMPT_PROJECTION_REVISION,
    VisualPromptAtom,
    VisualPromptAtomSource,
    VisualPromptDiagnostic,
    VisualPromptProvenance,
    VisualPromptRecipe,
)


def _source() -> VisualPromptAtomSource:
    return VisualPromptAtomSource("semantic", "focused", "required", 1100, 10)


def _atom(
    *, scope: Literal["positive", "negative"] = "positive"
) -> VisualPromptAtom:
    return VisualPromptAtom(
        key="focused_gaze",
        canonical_text="focused gaze",
        scope=scope,
        weight_milli=1100,
        required=True,
        priority=10,
        sources=(_source(),),
    )


def _provenance() -> VisualPromptProvenance:
    return VisualPromptProvenance(
        ruleset_key="prototype",
        ruleset_version=2,
        projection_policy_key="weighted_atom_projection",
        projection_policy_version=3,
        explicit_seed=42,
        rng_algorithm="sha256-domain-v1",
        visual_projection_algorithm_revision=VISUAL_PROMPT_PROJECTION_REVISION,
    )


def test_visual_recipe_freezes_complete_projection_provenance() -> None:
    diagnostic = VisualPromptDiagnostic(
        "info",
        "optional-atom-omitted",
        "Optional atom lost a deterministic group selection.",
        ("spare_atom",),
        ("semantic:calm",),
    )
    recipe = VisualPromptRecipe(
        1,
        (_atom(),),
        (_atom(scope="negative"),),
        (diagnostic,),
        _provenance(),
    )

    assert recipe.positive_atoms[0].sources == (_source(),)
    assert recipe.negative_atoms[0].scope == "negative"
    assert recipe.diagnostics[0].atom_keys == ("spare_atom",)
    assert recipe.provenance.visual_projection_algorithm_revision.endswith(
        "-v1"
    )
    assert isinstance(hash(recipe), int)


@pytest.mark.parametrize(
    "factory",
    (
        lambda: VisualPromptAtomSource("semantic", "", "optional", 1000, 0),
        lambda: VisualPromptAtomSource("semantic", "calm", "optional", 0, 0),
        lambda: VisualPromptAtom(
            "", "text", "positive", 1000, False, 0, (_source(),)
        ),
        lambda: VisualPromptAtom(
            "atom", "", "positive", 1000, False, 0, (_source(),)
        ),
        lambda: VisualPromptAtom(
            "atom", "text", "positive", 0, False, 0, (_source(),)
        ),
        lambda: VisualPromptAtom(
            "atom", "text", "positive", 1000, False, 0, ()
        ),
        lambda: VisualPromptAtom(
            "atom", "text", "positive", 1000, False, 0, (_source(), _source())
        ),
        lambda: VisualPromptDiagnostic("info", "", "message"),
        lambda: VisualPromptDiagnostic("warning", "code", ""),
        lambda: VisualPromptProvenance(
            "", 1, "policy", 1, 0, "rng", "revision"
        ),
        lambda: VisualPromptProvenance(
            "rules", 0, "policy", 1, 0, "rng", "revision"
        ),
        lambda: VisualPromptRecipe(0, (), (), (), _provenance()),
        lambda: VisualPromptRecipe(
            1, (_atom(scope="negative"),), (), (), _provenance()
        ),
        lambda: VisualPromptRecipe(1, (), (_atom(),), (), _provenance()),
        lambda: VisualPromptRecipe(
            1, (_atom(), _atom()), (), (), _provenance()
        ),
    ),
)
def test_visual_recipe_contracts_reject_invalid_facts(
    factory: Callable[[], object],
) -> None:
    with pytest.raises(ValueError):
        factory()
