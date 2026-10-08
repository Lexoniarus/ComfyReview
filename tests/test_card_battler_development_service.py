"""Behavior tests for atomic one-tier card development."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentPlanningError,
    DevelopmentPlanner,
)
from comfyreview.application.card_battler_development_addition import (
    CompatibleTraitAdditionPolicy,
)
from comfyreview.application.card_battler_development_improvement import (
    ExistingTraitImprovementPolicy,
)
from comfyreview.application.card_battler_development_service import (
    CardDevelopmentService,
)
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    CardStatMaterializer,
    StatProfileDefinition,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentPlan,
    CardStats,
    TraitDevelopmentAction,
)
from tests.test_card_battler_development_domain import _card_spec
from tests.test_card_battler_development_traits import (
    _MaterializationRepository as _BaseMaterializationRepository,
)
from tests.test_card_battler_development_traits import (
    _ModelRepository,
    _plan,
    _tier,
)


class _Planner:
    def __init__(
        self,
        plan: CardDevelopmentPlan | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = plan or _plan()
        self.error = error

    def plan(self, card: object) -> CardDevelopmentPlan:
        del card
        if self.error is not None:
            raise self.error
        return self.result


class _Improvement:
    def __init__(self, action: TraitDevelopmentAction) -> None:
        self.action = action
        self.calls = 0

    def improve(self, card: object, plan: object) -> TraitDevelopmentAction:
        del card, plan
        self.calls += 1
        return self.action


class _Addition:
    def __init__(self, action: TraitDevelopmentAction) -> None:
        self.action = action
        self.calls = 0

    def add(self, card: object, plan: object) -> TraitDevelopmentAction:
        del card, plan
        self.calls += 1
        return self.action


class _ServiceMaterializationRepository(_BaseMaterializationRepository):
    def __init__(
        self,
        *,
        profiles: tuple[StatProfileDefinition, ...] | None = None,
        tier=None,
    ) -> None:
        super().__init__(tier=tier or _tier())
        self.profiles = profiles or (_profile(),)

    def stat_profiles(
        self, ruleset: object = None
    ) -> tuple[StatProfileDefinition, ...]:
        del ruleset
        return self.profiles


class _WrongProfileStats:
    def materialize(self, *args: object) -> CardStats:
        del args
        return CardStats(1600, 1600, 3200, "changed")


def _profile(key: str = "balanced") -> StatProfileDefinition:
    return StatProfileDefinition(key, key.title(), 500, 500, key)


def _improvement_action(
    *, trait_index: int = 0, previous=True, lineage: str = "marking"
) -> TraitDevelopmentAction:
    card = _card_spec()
    developed = replace(
        card.traits[0],
        lineage_key=lineage,
        mechanic=replace(card.traits[0].mechanic, key="perfect_form"),
        canonical_rule_text="Perfekte Form.",
    )
    return TraitDevelopmentAction(
        "improve_existing_trait",
        trait_index,
        card.traits[0] if previous else None,
        developed,
    )


def _addition_action(
    *, trait_index: int = 1, previous=None
) -> TraitDevelopmentAction:
    card = _card_spec()
    trait = replace(
        card.traits[0],
        mechanic=replace(card.traits[0].mechanic, key="support_fire"),
        canonical_rule_text="Unterstützungsfeuer.",
    )
    return TraitDevelopmentAction(
        "add_compatible_trait", trait_index, previous, trait
    )


def _service(
    *,
    planner: _Planner | None = None,
    improvement: _Improvement | None = None,
    addition: _Addition | None = None,
    materialization: _ServiceMaterializationRepository | None = None,
    stats: object | None = None,
) -> CardDevelopmentService:
    return CardDevelopmentService(
        cast(CardBattlerModelRepository, _ModelRepository()),
        cast(
            CardMaterializationModelRepository,
            materialization or _ServiceMaterializationRepository(),
        ),
        cast(DevelopmentPlanner, planner or _Planner()),
        cast(
            ExistingTraitImprovementPolicy,
            improvement or _Improvement(_improvement_action()),
        ),
        cast(
            CompatibleTraitAdditionPolicy,
            addition or _Addition(_addition_action()),
        ),
        cast(CardStatMaterializer, stats or CardStatMaterializer()),
    )


def test_card_development_service_advances_one_tier_and_one_improvement() -> (
    None
):
    card = _card_spec()

    result = _service().advance(card)

    assert (
        result.card.rarity_key,
        result.card.level,
        result.card.tier_ordinal,
    ) == (
        "common",
        2,
        2,
    )
    assert result.card.stats.budget == 3200
    assert result.card.stats.stat_profile_key == "balanced"
    assert len(result.card.traits) == 1
    assert result.card.traits[0].mechanic.key == "perfect_form"
    assert result.card.imprint is card.imprint
    assert result.card.provenance is card.provenance
    assert result.action.action == "improve_existing_trait"
    assert result.provenance == _plan().provenance
    assert card.level == 1
    assert card.traits[0].mechanic.key == "measured_strike"


def test_card_development_service_appends_exactly_one_trait() -> None:
    plan = _plan(primary_trait_action="add_compatible_trait")
    improvement = _Improvement(_improvement_action())
    addition = _Addition(_addition_action())

    result = _service(
        planner=_Planner(plan),
        improvement=improvement,
        addition=addition,
    ).advance(_card_spec())

    assert tuple(trait.mechanic.key for trait in result.card.traits) == (
        "measured_strike",
        "support_fire",
    )
    assert improvement.calls == 0
    assert addition.calls == 1


def test_card_development_service_propagates_planning_failure_atomically() -> (
    None
):
    card = _card_spec()
    error = CardDevelopmentPlanningError("locked")

    with pytest.raises(CardDevelopmentPlanningError, match="locked"):
        _service(planner=_Planner(error=error)).advance(card)

    assert card == _card_spec()


def test_card_development_service_rejects_unsupported_planned_action() -> None:
    plan = replace(
        _plan(),
        primary_trait_action="add_first_trait",
    )
    with pytest.raises(CardDevelopmentPlanningError, match="unsupported"):
        _service(planner=_Planner(plan)).advance(_card_spec())


@pytest.mark.parametrize(
    "action",
    (
        _improvement_action(trait_index=-1),
        _improvement_action(trait_index=2),
        _improvement_action(previous=False),
        _improvement_action(lineage="other"),
    ),
)
def test_card_development_service_rejects_stale_improvements(
    action: TraitDevelopmentAction,
) -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="does not match"):
        _service(improvement=_Improvement(action)).advance(_card_spec())


@pytest.mark.parametrize(
    "action",
    (
        _addition_action(trait_index=0),
        _addition_action(previous=_card_spec().traits[0]),
    ),
)
def test_card_development_service_rejects_stale_additions(
    action: TraitDevelopmentAction,
) -> None:
    plan = _plan(primary_trait_action="add_compatible_trait")
    with pytest.raises(CardDevelopmentPlanningError, match="append"):
        _service(planner=_Planner(plan), addition=_Addition(action)).advance(
            _card_spec()
        )


def test_card_development_service_rejects_unknown_returned_action() -> None:
    invalid = replace(
        _improvement_action(),
        action="add_first_trait",
    )
    with pytest.raises(CardDevelopmentPlanningError, match="not supported"):
        _service(improvement=_Improvement(invalid)).advance(_card_spec())


def test_card_development_service_requires_one_stable_stat_profile() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="uniquely"):
        _service(
            materialization=_ServiceMaterializationRepository(
                profiles=(_profile("other"),)
            )
        ).advance(_card_spec())
    with pytest.raises(CardDevelopmentPlanningError, match="uniquely"):
        _service(
            materialization=_ServiceMaterializationRepository(
                profiles=(_profile(), _profile())
            )
        ).advance(_card_spec())


def test_card_development_service_rejects_changed_stat_profile() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="changed"):
        _service(stats=_WrongProfileStats()).advance(_card_spec())


def test_card_development_service_rejects_stale_target_tier() -> None:
    materialization = _ServiceMaterializationRepository(
        tier=_tier(stat_budget=3300)
    )
    with pytest.raises(CardDevelopmentPlanningError, match="balance tier"):
        _service(materialization=materialization).advance(_card_spec())
