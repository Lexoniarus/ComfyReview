"""Focused policies for deterministic Card Battler trait development."""

from __future__ import annotations

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    MechanicUpgradeEdge,
)
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    LineageMechanicEligibility,
    MechanicTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentPlan,
    MaterializedTrait,
    StructuredCardSpec,
    TraitDevelopmentAction,
)


class RegisteredMechanicUpgradePolicy:
    """Improve one trait through a registered mechanic upgrade edge."""

    def __init__(
        self,
        model_repository: CardBattlerModelRepository,
        development_repository: CardDevelopmentModelRepository,
        materialization_repository: CardMaterializationModelRepository,
        mechanics: MechanicMaterializer,
        rules: CanonicalRuleRenderer,
    ) -> None:
        self._model_repository = model_repository
        self._development_repository = development_repository
        self._materialization_repository = materialization_repository
        self._mechanics = mechanics
        self._rules = rules

    def improve(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        *,
        locale: str = "de-DE",
    ) -> TraitDevelopmentAction:
        """Materialize one deterministic, lineage-legal registered edge."""
        if plan.primary_trait_action != "improve_existing_trait":
            raise CardDevelopmentPlanningError(
                "development plan does not authorize a trait improvement"
            )
        ruleset = self._model_repository.resolve_ruleset(
            key=card.provenance.ruleset_key,
            version=card.provenance.ruleset_version,
        )
        materialization = self._materialization_repository
        definitions = materialization.mechanic_definitions(ruleset)
        definition_by_key = {item.key: item for item in definitions}
        if len(definition_by_key) != len(definitions):
            raise CardDevelopmentPlanningError(
                "mechanic definitions are ambiguous for development"
            )
        eligibility = materialization.lineage_mechanic_eligibility(ruleset)
        candidates = self._candidates(
            card,
            plan,
            definition_by_key,
            eligibility,
            self._development_repository.mechanic_upgrade_edges(ruleset),
        )
        if not candidates:
            raise CardDevelopmentPlanningError(
                "card has no legal registered mechanic upgrade"
            )
        selected = self._random(card).weighted_choice(
            f"development:{plan.next_tier.ordinal}:improve-edge",
            tuple(
                (key, weight)
                for key, _index, _definition, weight in candidates
            ),
        )
        _key, trait_index, definition, _weight = next(
            candidate for candidate in candidates if candidate[0] == selected
        )
        tier = self._tier(card, plan, ruleset)
        mechanic = self._mechanics.materialize(
            definition,
            tier,
            self._random(card),
        )
        developed = MaterializedTrait(
            lineage_key=card.traits[trait_index].lineage_key,
            mechanic=mechanic,
            canonical_rule_text=self._rules.render(
                definition,
                mechanic,
                locale=locale,
            ),
        )
        return TraitDevelopmentAction(
            action="improve_existing_trait",
            trait_index=trait_index,
            previous_trait=card.traits[trait_index],
            developed_trait=developed,
        )

    @staticmethod
    def _candidates(
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        definitions: dict[str, MechanicTemplateDefinition],
        eligibility: tuple[LineageMechanicEligibility, ...],
        edges: tuple[MechanicUpgradeEdge, ...],
    ) -> tuple[tuple[str, int, MechanicTemplateDefinition, int], ...]:
        legal = {
            (item.lineage_key, item.mechanic_key)
            for item in eligibility
            if item.min_tier_ordinal <= plan.next_tier.ordinal
            and (
                item.max_tier_ordinal is None
                or plan.next_tier.ordinal <= item.max_tier_ordinal
            )
        }
        result: list[tuple[str, int, MechanicTemplateDefinition, int]] = []
        for index, trait in enumerate(card.traits):
            for edge in edges:
                definition = definitions.get(edge.to_mechanic_key)
                if (
                    edge.from_mechanic_key != trait.mechanic.key
                    or definition is None
                    or edge.weight_milli <= 0
                    or plan.next_tier.ordinal < edge.min_tier_ordinal
                    or (
                        edge.max_tier_ordinal is not None
                        and plan.next_tier.ordinal > edge.max_tier_ordinal
                    )
                    or (trait.lineage_key, edge.to_mechanic_key) not in legal
                ):
                    continue
                result.append(
                    (
                        f"{index}:{edge.to_mechanic_key}",
                        index,
                        definition,
                        edge.weight_milli,
                    )
                )
        return tuple(sorted(result, key=lambda item: item[0]))

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
