"""Behavior tests for deterministic Card Battler stat materialization."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    CardStatMaterializer,
    StatProfileDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)


def _policy() -> CardBalancePolicy:
    return CardBalancePolicy(
        key="prototype_balance",
        version=2,
        stat_rounding_step=50,
        atk_def_minimum=0,
        no_negative_stats=True,
        trait_budget_is_milli=True,
        calibration_status="prototype",
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


def _random(seed: str = "42") -> DomainSeparatedCardRandom:
    return DomainSeparatedCardRandom(("image-1", seed))


def test_card_stats_follow_profile_grid_bounds_and_exact_budget() -> None:
    stats = CardStatMaterializer().materialize(
        _policy(),
        _tier(),
        StatProfileDefinition(
            "offensive", "Offensive", 650, 350, "ATK leaning"
        ),
        _random(),
    )

    assert (stats.attack, stats.defense, stats.budget) == (1950, 1050, 3000)
    assert stats.stat_profile_key == "offensive"
    assert stats.attack % _policy().stat_rounding_step == 0
    assert stats.attack + stats.defense == stats.budget


def test_card_stats_use_stats_domain_for_an_equal_distance_tie() -> None:
    tier = replace(_tier(), stat_budget=3050, max_def=2450)
    balanced = StatProfileDefinition(
        "balanced", "Balanced", 500, 500, "Even shares"
    )
    random = _random()

    stats = CardStatMaterializer().materialize(
        _policy(), tier, balanced, random
    )

    assert (stats.attack, stats.defense) == (1500, 1550)
    assert stats == CardStatMaterializer().materialize(
        _policy(), tier, balanced, _random()
    )
    assert random.integer(
        "initial-trait", modulo=1_000_000
    ) == _random().integer("initial-trait", modulo=1_000_000)


@pytest.mark.parametrize(
    "policy, tier, profile, message",
    (
        (
            replace(_policy(), stat_rounding_step=0),
            _tier(),
            StatProfileDefinition("balanced", "Balanced", 500, 500, ""),
            "rounding step",
        ),
        (
            _policy(),
            _tier(),
            StatProfileDefinition("", "Broken", 500, 500, ""),
            "positive total share",
        ),
        (
            _policy(),
            _tier(),
            StatProfileDefinition("broken", "Broken", -500, 500, ""),
            "positive total share",
        ),
        (
            _policy(),
            replace(_tier(), min_atk=2401),
            StatProfileDefinition("balanced", "Balanced", 500, 500, ""),
            "no legal ATK",
        ),
    ),
)
def test_card_stats_reject_invalid_or_impossible_model_facts(
    policy: CardBalancePolicy,
    tier: TierBalanceProfile,
    profile: StatProfileDefinition,
    message: str,
) -> None:
    with pytest.raises(CardBattlerModelInvalid, match=message):
        CardStatMaterializer().materialize(policy, tier, profile, _random())


def test_card_stats_enforce_non_negative_policy_minimum() -> None:
    tier = replace(
        _tier(),
        stat_budget=50,
        min_atk=-100,
        max_atk=100,
        min_def=-100,
        max_def=100,
    )
    stats = CardStatMaterializer().materialize(
        replace(_policy(), atk_def_minimum=-100),
        tier,
        StatProfileDefinition("balanced", "Balanced", 500, 500, ""),
        _random(),
    )

    assert (stats.attack, stats.defense) in ((0, 50), (50, 0))
