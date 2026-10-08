"""Behavior tests for deterministic initial Card Battler trait selection."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_materialization import (
    LineageMechanicEligibility,
    MechanicAffinity,
    MechanicStructureDefinition,
    MechanicTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_trait_selection import (
    InitialTraitSelector,
)
from comfyreview.domain.card_battler import CardImprint


def _imprint() -> CardImprint:
    return CardImprint(
        world_style="world-a",
        card_class="class-a",
        combat_role="role-a",
        trait_lineage="lineage-a",
        source_image_uid="image-1",
        semantic_revision="semantic-v1",
        ruleset_key="prototype",
        ruleset_version=2,
        mapping_policy_key="mapping",
        mapping_policy_version=2,
        rng_policy_key="rng",
        rng_policy_version=2,
        rng_algorithm="sha256-counter-v1",
        explicit_seed=42,
    )


def _tier() -> TierBalanceProfile:
    return TierBalanceProfile(
        rarity_key="common",
        level=1,
        ordinal=1,
        stat_budget=3000,
        mechanic_budget_milli=1000,
        min_atk=600,
        max_atk=2400,
        min_def=600,
        max_def=2400,
        max_traits=1,
        parameter_scale_milli=1000,
    )


def _mechanic(key: str, weight: int = 1000) -> MechanicTemplateDefinition:
    return MechanicTemplateDefinition(
        key=key,
        internal_name=key.upper(),
        description=f"{key} mechanic",
        base_weight_milli=weight,
        default_trigger_key="on_play",
        default_usage_limit_key=None,
        usage_limits=(),
        rule_text_templates=(),
        structure=MechanicStructureDefinition((), (), (), ()),
    )


def _mechanics() -> tuple[MechanicTemplateDefinition, ...]:
    return (_mechanic("zeta", 900), _mechanic("alpha", 1100))


def _eligibility() -> tuple[LineageMechanicEligibility, ...]:
    return (
        LineageMechanicEligibility("lineage-a", "zeta", 1, None, 700),
        LineageMechanicEligibility("lineage-a", "alpha", 1, 2, 900),
        LineageMechanicEligibility("other", "alpha", 1, None, 1000),
    )


def _affinities() -> tuple[MechanicAffinity, ...]:
    return (
        MechanicAffinity("class", "class-a", "alpha", 900),
        MechanicAffinity("role", "role-a", "alpha", 300),
        MechanicAffinity("lineage", "lineage-a", "alpha", 300),
        MechanicAffinity("world_style", "world-a", "alpha", 100),
        MechanicAffinity("class", "class-a", "zeta", 400),
        MechanicAffinity("role", "role-a", "zeta", 800),
        MechanicAffinity("lineage", "lineage-a", "zeta", 300),
        MechanicAffinity("world_style", "world-a", "zeta", 200),
    )


def _random() -> DomainSeparatedCardRandom:
    return DomainSeparatedCardRandom(("image-1", "42"))


def test_initial_trait_selector_uses_world_only_after_primary_tie() -> None:
    selection = InitialTraitSelector().select(
        _imprint(),
        _tier(),
        _mechanics(),
        _eligibility(),
        _affinities(),
        _random(),
    )

    assert selection.mechanic.key == "zeta"
    assert selection.selected_candidate.primary_affinity_milli == 500
    assert selection.selected_candidate.world_style_affinity_milli == 200
    assert [candidate.mechanic_key for candidate in selection.candidates] == [
        "alpha",
        "zeta",
    ]
    assert selection == InitialTraitSelector().select(
        _imprint(),
        _tier(),
        tuple(reversed(_mechanics())),
        tuple(reversed(_eligibility())),
        tuple(reversed(_affinities())),
        _random(),
    )


def test_initial_trait_selector_keeps_primary_axes_authoritative() -> None:
    affinities = tuple(
        replace(fact, weight_milli=303)
        if fact.mechanic_key == "alpha" and fact.source == "lineage"
        else replace(fact, weight_milli=999)
        if fact.mechanic_key == "zeta" and fact.source == "world_style"
        else fact
        for fact in _affinities()
    )

    selection = InitialTraitSelector().select(
        _imprint(),
        _tier(),
        _mechanics(),
        _eligibility(),
        affinities,
        _random(),
    )

    assert selection.mechanic.key == "alpha"


def test_initial_trait_selector_uses_seeded_weight_for_final_tie() -> None:
    affinities = tuple(replace(fact, weight_milli=0) for fact in _affinities())

    selection = InitialTraitSelector().select(
        _imprint(),
        _tier(),
        _mechanics(),
        _eligibility(),
        affinities,
        _random(),
    )

    assert selection.mechanic.key == "zeta"
    assert selection.selected_candidate.seeded_weight == 630_000


@pytest.mark.parametrize(
    "mechanics, eligibility, affinities, message",
    (
        ((), (), (), "unique stable keys"),
        (
            (_mechanic("same"), _mechanic("same")),
            (),
            (),
            "unique stable keys",
        ),
        (
            _mechanics(),
            (LineageMechanicEligibility("lineage-a", "missing", 1, None, 1),),
            (),
            "unknown mechanic",
        ),
        (
            _mechanics(),
            _eligibility() + (_eligibility()[0],),
            (),
            "ambiguous",
        ),
        (
            _mechanics(),
            (),
            (),
            "no mechanic is legal",
        ),
        (
            _mechanics(),
            _eligibility(),
            (MechanicAffinity("class", "class-a", "missing", 1),),
            "unknown mechanic",
        ),
        (
            _mechanics(),
            _eligibility(),
            (
                MechanicAffinity("class", "class-a", "alpha", 1),
                MechanicAffinity("class", "class-a", "alpha", 2),
            ),
            "unique axis facts",
        ),
        (
            (_mechanic("alpha", 0),),
            (LineageMechanicEligibility("lineage-a", "alpha", 1, None, 1),),
            (),
            "weights must be positive",
        ),
    ),
)
def test_initial_trait_selector_rejects_invalid_model_facts(
    mechanics: tuple[MechanicTemplateDefinition, ...],
    eligibility: tuple[LineageMechanicEligibility, ...],
    affinities: tuple[MechanicAffinity, ...],
    message: str,
) -> None:
    with pytest.raises(CardBattlerModelInvalid, match=message):
        InitialTraitSelector().select(
            _imprint(),
            _tier(),
            mechanics,
            eligibility,
            affinities,
            _random(),
        )


def test_initial_trait_selector_honors_tier_interval() -> None:
    eligibility = (
        LineageMechanicEligibility("lineage-a", "alpha", 2, None, 1),
        LineageMechanicEligibility("lineage-a", "zeta", 1, 1, 1),
    )

    selection = InitialTraitSelector().select(
        _imprint(),
        _tier(),
        _mechanics(),
        eligibility,
        (),
        _random(),
    )

    assert selection.mechanic.key == "zeta"
