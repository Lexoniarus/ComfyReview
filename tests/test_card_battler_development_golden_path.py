"""Golden replay proof for the complete prototype development ladder."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    CardDevelopmentPolicy,
    DevelopmentPlanner,
    DevelopmentTierModel,
    MechanicParameterProgression,
    TierDevelopmentActionWeight,
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
    CardBalancePolicy,
    CardMaterializationModelRepository,
    CardStatMaterializer,
    LineageMechanicEligibility,
    MechanicParameterDefinition,
    MechanicStructureDefinition,
    MechanicTemplateDefinition,
    RuleTextTemplateDefinition,
    StatProfileDefinition,
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
from comfyreview.domain.card_battler import StructuredCardSpec
from tests.test_card_battler_development_domain import _card_spec


def _tier_name(ordinal: int) -> tuple[str, int]:
    if ordinal <= 15:
        rarities = ("common", "uncommon", "rare", "epic", "ultra")
        return rarities[(ordinal - 1) // 3], ((ordinal - 1) % 3) + 1
    return "legendary", 1


def _ladder() -> tuple[DevelopmentTierModel, ...]:
    result = []
    for ordinal in range(1, 17):
        rarity, level = _tier_name(ordinal)
        result.append(
            DevelopmentTierModel(
                rarity_key=rarity,
                rarity_name=rarity.title(),
                rarity_ordinal=((ordinal - 1) // 3) + 1,
                level=level,
                ordinal=ordinal,
                next_ordinal=ordinal + 1 if ordinal < 16 else None,
                development_locked=ordinal == 16,
                balance_policy_key="prototype_balance",
                balance_policy_version=2,
                stat_budget=3000 + (ordinal - 1) * 100,
                mechanic_budget_milli=1000 + (ordinal - 1) * 50,
                trait_cap=1,
                parameter_scale_milli=1000,
            )
        )
    return tuple(result)


class _ModelRepository:
    def resolve_ruleset(
        self, *, key: str, version: int
    ) -> CardBattlerRulesetRef:
        assert (key, version) == ("prototype", 2)
        return CardBattlerRulesetRef(
            "prototype", 2, "Prototype", "active", "Fixture", "visual", 1
        )


class _DevelopmentRepository:
    def development_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardDevelopmentPolicy:
        del ruleset, key, version
        return CardDevelopmentPolicy(
            "lineage_preserving_development",
            2,
            True,
            ("world_style", "card_class", "combat_role", "trait_lineage"),
            True,
            True,
            ("improve_existing_trait",),
        )

    def development_ladder(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        balance_policy_key: str | None = None,
        balance_policy_version: int | None = None,
    ) -> tuple[DevelopmentTierModel, ...]:
        del ruleset
        assert (balance_policy_key, balance_policy_version) == (
            "prototype_balance",
            2,
        )
        return _ladder()

    def development_action_weights(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[TierDevelopmentActionWeight, ...]:
        del ruleset
        return tuple(
            TierDevelopmentActionWeight(
                ordinal,
                "improve_existing_trait",
                "Improve",
                "Improve one trait",
                1000,
                True,
            )
            for ordinal in range(2, 17)
        )

    def mechanic_upgrade_edges(self, ruleset=None):
        del ruleset
        return ()

    def mechanic_parameter_progression(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[MechanicParameterProgression, ...]:
        del ruleset
        return (
            MechanicParameterProgression(
                "measured_strike", "bonus", 2, 15, 10, 14, 50
            ),
        )


class _MaterializationRepository:
    def balance_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBalancePolicy:
        del ruleset
        assert (key, version) == ("prototype_balance", 2)
        return CardBalancePolicy(
            "prototype_balance", 2, 100, 0, True, True, "prototype"
        )

    def tier_balance_profile(
        self,
        balance_policy: CardBalancePolicy,
        *,
        rarity_key: str,
        level: int,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> TierBalanceProfile:
        del ruleset
        assert balance_policy.key == "prototype_balance"
        tier = next(
            item
            for item in _ladder()
            if item.rarity_key == rarity_key and item.level == level
        )
        return TierBalanceProfile(
            tier.rarity_key,
            tier.level,
            tier.ordinal,
            tier.stat_budget,
            tier.mechanic_budget_milli,
            0,
            tier.stat_budget,
            0,
            tier.stat_budget,
            tier.trait_cap,
            tier.parameter_scale_milli,
        )

    def stat_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[StatProfileDefinition, ...]:
        del ruleset
        return (
            StatProfileDefinition("balanced", "Balanced", 500, 500, "Even"),
        )

    def mechanic_definitions(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[MechanicTemplateDefinition, ...]:
        del ruleset
        return (_mechanic_definition(),)

    def lineage_mechanic_eligibility(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[LineageMechanicEligibility, ...]:
        del ruleset
        return (
            LineageMechanicEligibility(
                "marking", "measured_strike", 1, 15, 1000
            ),
        )


class _UnusedAddition:
    def add(self, card: object, plan: object):
        del card, plan
        raise AssertionError("golden ladder must not add a trait")


def _mechanic_definition() -> MechanicTemplateDefinition:
    return MechanicTemplateDefinition(
        key="measured_strike",
        internal_name="MEASURED_STRIKE",
        description="Measured strike",
        base_weight_milli=750,
        default_trigger_key="on_attack",
        default_usage_limit_key=None,
        usage_limits=(),
        rule_text_templates=(
            RuleTextTemplateDefinition("de-DE", 1, "Erhält {bonus} ATK."),
        ),
        structure=MechanicStructureDefinition(
            (),
            (),
            (),
            (
                MechanicParameterDefinition(
                    "bonus", None, None, "int", 0, 500, 10, 300, (), ()
                ),
            ),
        ),
    )


def _service() -> CardDevelopmentService:
    model = cast(CardBattlerModelRepository, _ModelRepository())
    development = cast(
        CardDevelopmentModelRepository, _DevelopmentRepository()
    )
    materialization = cast(
        CardMaterializationModelRepository, _MaterializationRepository()
    )
    return CardDevelopmentService(
        model,
        materialization,
        DevelopmentPlanner(model, development),
        ExistingTraitImprovementPolicy(
            model,
            development,
            materialization,
            MechanicMaterializer(),
            CanonicalRuleRenderer(),
        ),
        cast(CompatibleTraitAdditionPolicy, _UnusedAddition()),
        CardStatMaterializer(),
    )


def _replay() -> tuple[StructuredCardSpec, ...]:
    service = _service()
    cards = [_card_spec()]
    for _ in range(14):
        cards.append(service.advance(cards[-1]).card)
    return tuple(cards)


def test_card_development_golden_path_replays_common_to_ultra() -> None:
    first = _replay()
    second = _replay()

    assert first == second
    assert len(first) == 15
    assert (first[0].rarity_key, first[0].level) == ("common", 1)
    assert (first[-1].rarity_key, first[-1].level) == ("ultra", 3)
    assert tuple(card.tier_ordinal for card in first) == tuple(range(1, 16))
    assert all(card.imprint == first[0].imprint for card in first)
    assert all(card.provenance == first[0].provenance for card in first)
    assert all(card.stats.stat_profile_key == "balanced" for card in first)
    assert all(
        card.stats.budget == 3000 + index * 100
        for index, card in enumerate(first)
    )
    assert all(len(card.traits) == 1 for card in first)
    assert tuple(
        card.traits[0].mechanic.parameters[0].value for card in first
    ) == tuple(range(300, 441, 10))
    assert tuple(
        card.traits[0].parameter_upgrades[0].applied_steps
        for card in first[1:]
    ) == tuple(range(1, 15))


def test_card_development_golden_path_keeps_legendary_locked() -> None:
    ultra_three = _replay()[-1]

    with pytest.raises(CardDevelopmentPlanningError, match="locked"):
        _service().advance(ultra_three)

    assert (ultra_three.rarity_key, ultra_three.level) == ("ultra", 3)
