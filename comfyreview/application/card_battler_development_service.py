"""Application orchestration for one atomic Card Battler development step."""

from __future__ import annotations

from dataclasses import replace

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
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    CardStatMaterializer,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentPlan,
    CardDevelopmentResult,
    CardStats,
    MaterializedTrait,
    StructuredCardSpec,
    TraitDevelopmentAction,
)


class CardDevelopmentService:
    """Advance one immutable card by one tier and one trait action."""

    def __init__(
        self,
        model_repository: CardBattlerModelRepository,
        materialization_repository: CardMaterializationModelRepository,
        planner: DevelopmentPlanner,
        improvement: ExistingTraitImprovementPolicy,
        addition: CompatibleTraitAdditionPolicy,
        stats: CardStatMaterializer,
    ) -> None:
        self._model_repository = model_repository
        self._materialization_repository = materialization_repository
        self._planner = planner
        self._improvement = improvement
        self._addition = addition
        self._stats = stats

    def advance(self, card: StructuredCardSpec) -> CardDevelopmentResult:
        """Return one fully valid adjacent-tier development result."""
        plan = self._planner.plan(card)
        ruleset = self._model_repository.resolve_ruleset(
            key=card.provenance.ruleset_key,
            version=card.provenance.ruleset_version,
        )
        tier = self._tier(card, plan, ruleset)
        action = self._trait_action(card, plan)
        traits = self._apply_action(card, action)
        stats = self._materialize_stats(card, ruleset, tier)
        developed = replace(
            card,
            rarity_key=plan.next_tier.rarity_key,
            level=plan.next_tier.level,
            tier_ordinal=plan.next_tier.ordinal,
            stats=stats,
            traits=traits,
        )
        return CardDevelopmentResult(
            card=developed,
            action=action,
            provenance=plan.provenance,
        )

    def _trait_action(
        self, card: StructuredCardSpec, plan: CardDevelopmentPlan
    ) -> TraitDevelopmentAction:
        if plan.primary_trait_action == "improve_existing_trait":
            return self._improvement.improve(card, plan)
        if plan.primary_trait_action == "add_compatible_trait":
            return self._addition.add(card, plan)
        raise CardDevelopmentPlanningError(
            "development plan contains an unsupported trait action"
        )

    @staticmethod
    def _apply_action(
        card: StructuredCardSpec, action: TraitDevelopmentAction
    ) -> tuple[MaterializedTrait, ...]:
        if action.action == "improve_existing_trait":
            previous = action.previous_trait
            if (
                previous is None
                or action.trait_index < 0
                or action.trait_index >= len(card.traits)
                or previous != card.traits[action.trait_index]
                or action.developed_trait.lineage_key != previous.lineage_key
            ):
                raise CardDevelopmentPlanningError(
                    "trait improvement does not match the input card"
                )
            traits = list(card.traits)
            traits[action.trait_index] = action.developed_trait
            return tuple(traits)
        if action.action == "add_compatible_trait":
            if (
                action.trait_index != len(card.traits)
                or action.previous_trait is not None
            ):
                raise CardDevelopmentPlanningError(
                    "trait addition does not append exactly one trait"
                )
            return (*card.traits, action.developed_trait)
        raise CardDevelopmentPlanningError(
            "development action is not supported by the service"
        )

    def _materialize_stats(
        self,
        card: StructuredCardSpec,
        ruleset: CardBattlerRulesetRef,
        tier: TierBalanceProfile,
    ) -> CardStats:
        repository = self._materialization_repository
        profiles = repository.stat_profiles(ruleset)
        matches = tuple(
            item
            for item in profiles
            if item.key == card.stats.stat_profile_key
        )
        if len(matches) != 1:
            raise CardDevelopmentPlanningError(
                "card stat profile cannot be resolved uniquely"
            )
        balance = repository.balance_policy(
            ruleset,
            key=card.provenance.balance_policy_key,
            version=card.provenance.balance_policy_version,
        )
        result = self._stats.materialize(
            balance,
            tier,
            matches[0],
            self._random(card),
        )
        if result.stat_profile_key != card.stats.stat_profile_key:
            raise CardDevelopmentPlanningError(
                "development changed the card stat profile"
            )
        return result

    def _tier(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        ruleset: CardBattlerRulesetRef,
    ) -> TierBalanceProfile:
        repository = self._materialization_repository
        balance = repository.balance_policy(
            ruleset,
            key=card.provenance.balance_policy_key,
            version=card.provenance.balance_policy_version,
        )
        tier = repository.tier_balance_profile(
            balance,
            rarity_key=plan.next_tier.rarity_key,
            level=plan.next_tier.level,
            ruleset=ruleset,
        )
        if (
            tier.ordinal != plan.next_tier.ordinal
            or tier.stat_budget != plan.stat_budget
            or tier.mechanic_budget_milli != plan.mechanic_budget_milli
            or tier.max_traits != plan.trait_cap
            or tier.parameter_scale_milli != plan.parameter_scale_milli
        ):
            raise CardDevelopmentPlanningError(
                "development plan does not match its balance tier"
            )
        return tier

    @staticmethod
    def _random(card: StructuredCardSpec) -> DomainSeparatedCardRandom:
        imprint = card.imprint
        return DomainSeparatedCardRandom(
            (
                imprint.source_image_uid,
                imprint.semantic_revision,
                f"{imprint.ruleset_key}@{imprint.ruleset_version}",
                f"{imprint.mapping_policy_key}@{imprint.mapping_policy_version}",
                f"{imprint.rng_policy_key}@{imprint.rng_policy_version}",
                str(imprint.explicit_seed),
            )
        )
