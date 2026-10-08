"""Behavior tests for focused existing-trait development policies."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    MechanicUpgradeEdge,
)
from comfyreview.application.card_battler_development_traits import (
    RegisteredMechanicUpgradePolicy,
)
from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    CardMaterializationModelRepository,
    LineageMechanicEligibility,
    MechanicTemplateDefinition,
    RuleTextTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.domain.card_battler import (
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    CardDevelopmentPlan,
    CardDevelopmentProvenance,
    DevelopmentTier,
    PrimaryTraitAction,
)
from tests.test_card_battler_development_domain import _card_spec
from tests.test_card_battler_initial_trait import _mechanic


class _ModelRepository:
    def resolve_ruleset(
        self, *, key: str, version: int
    ) -> CardBattlerRulesetRef:
        assert (key, version) == ("prototype", 2)
        return _ruleset()


class _DevelopmentRepository:
    def __init__(self, edges: tuple[MechanicUpgradeEdge, ...]) -> None:
        self.edges = edges

    def mechanic_upgrade_edges(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicUpgradeEdge, ...]:
        assert ruleset == _ruleset()
        return self.edges


class _MaterializationRepository:
    def __init__(
        self,
        *,
        definitions: tuple[MechanicTemplateDefinition, ...] | None = None,
        eligibility: tuple[LineageMechanicEligibility, ...] | None = None,
        tier: TierBalanceProfile | None = None,
    ) -> None:
        self.definitions = definitions or (_target_mechanic(),)
        self.eligibility = eligibility or (_eligibility(),)
        self.tier = tier or _tier()

    def mechanic_definitions(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicTemplateDefinition, ...]:
        assert ruleset == _ruleset()
        return self.definitions

    def lineage_mechanic_eligibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[LineageMechanicEligibility, ...]:
        assert ruleset == _ruleset()
        return self.eligibility

    def balance_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBalancePolicy:
        assert ruleset == _ruleset()
        assert (key, version) == ("prototype_balance", 2)
        return CardBalancePolicy(
            key="prototype_balance",
            version=2,
            stat_rounding_step=100,
            atk_def_minimum=0,
            no_negative_stats=True,
            trait_budget_is_milli=True,
            calibration_status="prototype",
        )

    def tier_balance_profile(
        self,
        balance_policy: CardBalancePolicy,
        *,
        rarity_key: str,
        level: int,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> TierBalanceProfile:
        assert balance_policy.key == "prototype_balance"
        assert (rarity_key, level, ruleset) == ("common", 2, _ruleset())
        return self.tier


def _policy(
    development: _DevelopmentRepository,
    materialization: _MaterializationRepository,
) -> RegisteredMechanicUpgradePolicy:
    return RegisteredMechanicUpgradePolicy(
        cast(CardBattlerModelRepository, _ModelRepository()),
        cast(CardDevelopmentModelRepository, development),
        cast(CardMaterializationModelRepository, materialization),
        MechanicMaterializer(),
        CanonicalRuleRenderer(),
    )


def _ruleset() -> CardBattlerRulesetRef:
    return CardBattlerRulesetRef(
        "prototype",
        2,
        "Prototype",
        "active",
        "Fixture",
        "visual-semantics",
        1,
    )


def _target_mechanic() -> MechanicTemplateDefinition:
    return replace(
        _mechanic("perfect_form"),
        rule_text_templates=(
            RuleTextTemplateDefinition("de-DE", 1, "Perfekte Form."),
        ),
    )


def _edge(
    *,
    to_mechanic_key: str = "perfect_form",
    min_tier_ordinal: int = 2,
    max_tier_ordinal: int | None = 15,
    weight_milli: int = 900,
) -> MechanicUpgradeEdge:
    return MechanicUpgradeEdge(
        from_mechanic_key="measured_strike",
        to_mechanic_key=to_mechanic_key,
        min_tier_ordinal=min_tier_ordinal,
        max_tier_ordinal=max_tier_ordinal,
        weight_milli=weight_milli,
        upgrade_kind="branch",
        notes=None,
    )


def _eligibility(
    *,
    lineage_key: str = "marking",
    mechanic_key: str = "perfect_form",
    min_tier_ordinal: int = 2,
    max_tier_ordinal: int | None = 15,
) -> LineageMechanicEligibility:
    return LineageMechanicEligibility(
        lineage_key=lineage_key,
        mechanic_key=mechanic_key,
        min_tier_ordinal=min_tier_ordinal,
        max_tier_ordinal=max_tier_ordinal,
        selection_weight_milli=1000,
    )


def _tier(*, stat_budget: int = 3200) -> TierBalanceProfile:
    return TierBalanceProfile(
        rarity_key="common",
        level=2,
        ordinal=2,
        stat_budget=stat_budget,
        mechanic_budget_milli=1500,
        min_atk=0,
        max_atk=3200,
        min_def=0,
        max_def=3200,
        max_traits=2,
        parameter_scale_milli=1100,
    )


def _plan(
    *,
    primary_trait_action: str = "improve_existing_trait",
) -> CardDevelopmentPlan:
    return CardDevelopmentPlan(
        current_tier=DevelopmentTier("common", 1, 1),
        next_tier=DevelopmentTier("common", 2, 2),
        stat_budget=3200,
        mechanic_budget_milli=1500,
        trait_cap=2,
        parameter_scale_milli=1100,
        primary_trait_action=cast(PrimaryTraitAction, primary_trait_action),
        provenance=CardDevelopmentProvenance(
            "lineage-preserving",
            2,
            CARD_DEVELOPMENT_ALGORITHM_REVISION,
        ),
    )


def test_registered_upgrade_policy_materializes_a_lineage_legal_edge() -> None:
    card = _card_spec()
    action = _policy(
        _DevelopmentRepository((_edge(),)),
        _MaterializationRepository(),
    ).improve(card, _plan())

    assert action.action == "improve_existing_trait"
    assert action.trait_index == 0
    assert action.previous_trait is card.traits[0]
    assert action.developed_trait.lineage_key == "marking"
    assert action.developed_trait.mechanic.key == "perfect_form"
    assert action.developed_trait.canonical_rule_text == "Perfekte Form."


def test_registered_upgrade_policy_is_repository_order_independent() -> None:
    second = replace(
        _target_mechanic(),
        key="zeta_form",
        internal_name="ZETA_FORM",
    )
    edges = (_edge(), _edge(to_mechanic_key="zeta_form", weight_milli=1))
    eligibility = (
        _eligibility(),
        _eligibility(mechanic_key="zeta_form"),
    )
    forward = _policy(
        _DevelopmentRepository(edges),
        _MaterializationRepository(
            definitions=(_target_mechanic(), second),
            eligibility=eligibility,
        ),
    ).improve(_card_spec(), _plan())
    reversed_result = _policy(
        _DevelopmentRepository(tuple(reversed(edges))),
        _MaterializationRepository(
            definitions=(second, _target_mechanic()),
            eligibility=tuple(reversed(eligibility)),
        ),
    ).improve(_card_spec(), _plan())

    assert forward == reversed_result


def test_registered_upgrade_policy_requires_an_improvement_plan() -> None:
    plan = _plan(primary_trait_action="add_compatible_trait")

    with pytest.raises(
        CardDevelopmentPlanningError, match="does not authorize"
    ):
        _policy(
            _DevelopmentRepository((_edge(),)),
            _MaterializationRepository(),
        ).improve(_card_spec(), plan)


@pytest.mark.parametrize(
    ("edge", "eligibility"),
    (
        (_edge(to_mechanic_key="missing"), _eligibility()),
        (_edge(weight_milli=0), _eligibility()),
        (_edge(min_tier_ordinal=3), _eligibility()),
        (_edge(max_tier_ordinal=1), _eligibility()),
        (_edge(), _eligibility(lineage_key="other")),
        (_edge(), _eligibility(min_tier_ordinal=3)),
        (_edge(), _eligibility(max_tier_ordinal=1)),
    ),
)
def test_registered_upgrade_policy_rejects_illegal_edges(
    edge: MechanicUpgradeEdge,
    eligibility: LineageMechanicEligibility,
) -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="no legal"):
        _policy(
            _DevelopmentRepository((edge,)),
            _MaterializationRepository(eligibility=(eligibility,)),
        ).improve(_card_spec(), _plan())


def test_registered_upgrade_policy_rejects_ambiguous_definitions() -> None:
    target = _target_mechanic()

    with pytest.raises(CardDevelopmentPlanningError, match="ambiguous"):
        _policy(
            _DevelopmentRepository((_edge(),)),
            _MaterializationRepository(definitions=(target, target)),
        ).improve(_card_spec(), _plan())


def test_registered_upgrade_policy_rejects_a_stale_balance_plan() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="balance tier"):
        _policy(
            _DevelopmentRepository((_edge(),)),
            _MaterializationRepository(tier=_tier(stat_budget=3300)),
        ).improve(_card_spec(), _plan())
