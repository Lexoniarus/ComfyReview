"""Behavior tests for deterministic next-tier development planning."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    CardDevelopmentPolicy,
    DevelopmentPlanner,
    DevelopmentTierModel,
    TierDevelopmentActionWeight,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
)
from comfyreview.domain.card_battler import (
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    StructuredCardSpec,
)
from tests.test_card_battler_development_domain import _card_spec


class _ModelRepository:
    def resolve_ruleset(
        self, *, key: str, version: int
    ) -> CardBattlerRulesetRef:
        assert (key, version) == ("prototype", 2)
        return _ruleset()


class _DevelopmentRepository:
    def __init__(
        self,
        *,
        ladder: tuple[DevelopmentTierModel, ...] | None = None,
        policy: CardDevelopmentPolicy | None = None,
        weights: tuple[TierDevelopmentActionWeight, ...] | None = None,
    ) -> None:
        self.ladder = ladder or _ladder()
        self.policy = policy or _policy()
        self.weights = weights or _weights()

    def development_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardDevelopmentPolicy:
        assert ruleset == _ruleset()
        assert key is None and version is None
        return self.policy

    def development_ladder(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        balance_policy_key: str | None = None,
        balance_policy_version: int | None = None,
    ) -> tuple[DevelopmentTierModel, ...]:
        assert ruleset == _ruleset()
        assert (balance_policy_key, balance_policy_version) == (
            "prototype_balance",
            2,
        )
        return self.ladder

    def development_action_weights(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[TierDevelopmentActionWeight, ...]:
        assert ruleset == _ruleset()
        return self.weights


def _planner(repository: _DevelopmentRepository) -> DevelopmentPlanner:
    return DevelopmentPlanner(
        cast(CardBattlerModelRepository, _ModelRepository()),
        cast(CardDevelopmentModelRepository, repository),
    )


def _ruleset() -> CardBattlerRulesetRef:
    return CardBattlerRulesetRef(
        key="prototype",
        version=2,
        name="Prototype",
        status="active",
        description="Fixture",
        semantic_vocabulary_key="visual-semantics",
        semantic_vocabulary_version=1,
    )


def _policy(
    *, primary_trait_actions: tuple[str, ...] | None = None
) -> CardDevelopmentPolicy:
    return CardDevelopmentPolicy(
        key="lineage-preserving",
        version=2,
        cross_lineage_requires_compatibility=True,
        immutable_imprint_dimensions=(
            "world_style",
            "card_class",
            "combat_role",
            "trait_lineage",
        ),
        legendary_locked_in_prototype=True,
        prefer_existing_lineage=True,
        primary_trait_actions=primary_trait_actions
        or (
            "add_first_trait",
            "improve_existing_trait",
            "add_compatible_trait",
        ),
    )


def _tier(
    ordinal: int,
    *,
    rarity_key: str = "common",
    level: int | None = None,
    next_ordinal: int | None = None,
    locked: bool = False,
    stat_budget: int | None = None,
    trait_cap: int = 2,
) -> DevelopmentTierModel:
    return DevelopmentTierModel(
        rarity_key=rarity_key,
        rarity_name=rarity_key.title(),
        rarity_ordinal=1,
        level=level or ordinal,
        ordinal=ordinal,
        next_ordinal=next_ordinal,
        development_locked=locked,
        balance_policy_key="prototype_balance",
        balance_policy_version=2,
        stat_budget=stat_budget or (2800 + ordinal * 200),
        mechanic_budget_milli=1000 + ordinal * 250,
        trait_cap=trait_cap,
        parameter_scale_milli=900 + ordinal * 100,
    )


def _ladder() -> tuple[DevelopmentTierModel, ...]:
    return (
        _tier(1, next_ordinal=2, trait_cap=1),
        _tier(2, next_ordinal=3),
        _tier(3),
    )


def _weight(
    action: str,
    weight: int,
    *,
    enabled: bool = True,
    tier: int = 2,
) -> TierDevelopmentActionWeight:
    return TierDevelopmentActionWeight(
        tier_ordinal=tier,
        action_key=action,
        action_name=action,
        action_description=action,
        weight_milli=weight,
        enabled=enabled,
    )


def _weights() -> tuple[TierDevelopmentActionWeight, ...]:
    return (
        _weight("improve_existing_trait", 800),
        _weight("add_first_trait", 50),
        _weight("add_compatible_trait", 350),
    )


def test_development_planner_builds_the_exact_next_tier_golden_plan() -> None:
    repository = _DevelopmentRepository()

    plan = _planner(repository).plan(_card_spec())

    assert (plan.current_tier.rarity_key, plan.current_tier.level) == (
        "common",
        1,
    )
    assert (plan.next_tier.ordinal, plan.next_tier.level) == (2, 2)
    assert (
        plan.stat_budget,
        plan.mechanic_budget_milli,
        plan.trait_cap,
        plan.parameter_scale_milli,
    ) == (3200, 1500, 2, 1100)
    assert plan.primary_trait_action == "improve_existing_trait"
    assert plan.provenance.development_policy_key == "lineage-preserving"
    assert (
        plan.provenance.development_algorithm_revision
        == CARD_DEVELOPMENT_ALGORITHM_REVISION
    )


def test_development_planner_is_input_order_independent() -> None:
    forward = _DevelopmentRepository()
    reversed_repository = _DevelopmentRepository(
        ladder=tuple(reversed(_ladder())),
        weights=tuple(reversed(_weights())),
    )

    assert _planner(forward).plan(_card_spec()) == _planner(
        reversed_repository
    ).plan(_card_spec())


def test_development_planner_uses_first_trait_action_for_an_empty_card() -> (
    None
):
    card = replace(_card_spec(), traits=())

    plan = _planner(_DevelopmentRepository()).plan(card)

    assert plan.primary_trait_action == "add_first_trait"


@pytest.mark.parametrize(
    ("card", "ladder", "message"),
    (
        (replace(_card_spec(), level=2), _ladder(), "does not match"),
        (
            replace(
                _card_spec(),
                stats=replace(_card_spec().stats, attack=1500),
            ),
            _ladder(),
            "stats do not match",
        ),
        (
            replace(
                _card_spec(),
                traits=(_card_spec().traits[0], _card_spec().traits[0]),
            ),
            _ladder(),
            "trait cap",
        ),
        (
            _card_spec(),
            (replace(_ladder()[0], development_locked=True),),
            "locked",
        ),
        (_card_spec(), (replace(_ladder()[0], next_ordinal=None),), "locked"),
        (
            _card_spec(),
            (_ladder()[0], replace(_ladder()[1], development_locked=True)),
            "next tier is locked",
        ),
    ),
)
def test_development_planner_rejects_cards_without_an_available_next_tier(
    card: StructuredCardSpec,
    ladder: tuple[DevelopmentTierModel, ...],
    message: str,
) -> None:
    with pytest.raises(CardDevelopmentPlanningError, match=message):
        _planner(_DevelopmentRepository(ladder=ladder)).plan(card)


def test_development_planner_rejects_non_consecutive_model_tiers() -> None:
    ladder = (
        replace(_ladder()[0], next_ordinal=3),
        _ladder()[2],
    )

    with pytest.raises(CardBattlerModelInvalid, match="exact next tier"):
        _planner(_DevelopmentRepository(ladder=ladder)).plan(_card_spec())


def test_development_planner_enforces_the_legendary_policy_lock() -> None:
    ladder = (
        _ladder()[0],
        replace(_ladder()[1], rarity_key="legendary"),
    )

    with pytest.raises(
        CardDevelopmentPlanningError, match="next tier is locked"
    ):
        _planner(_DevelopmentRepository(ladder=ladder)).plan(_card_spec())


def test_development_planner_rejects_unknown_or_unavailable_actions() -> None:
    with pytest.raises(
        CardBattlerModelInvalid, match="unknown primary action"
    ):
        _planner(
            _DevelopmentRepository(
                policy=_policy(primary_trait_actions=("invent_rules",))
            )
        ).plan(_card_spec())

    with pytest.raises(CardDevelopmentPlanningError, match="no legal"):
        _planner(
            _DevelopmentRepository(
                weights=(
                    _weight("improve_existing_trait", 0),
                    _weight("add_compatible_trait", 100, enabled=False),
                    _weight("add_first_trait", 100, tier=3),
                )
            )
        ).plan(_card_spec())


def test_development_planner_rejects_a_non_conserving_stat_total() -> None:
    card = replace(
        _card_spec(),
        stats=replace(_card_spec().stats, defense=1300, budget=3000),
    )

    with pytest.raises(
        CardDevelopmentPlanningError, match="stats do not match"
    ):
        _planner(_DevelopmentRepository()).plan(card)
