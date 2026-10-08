"""Deterministic policy for adding one compatible Card Battler trait."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    CardDevelopmentPolicy,
    LineageCompatibility,
    MechanicCompatibility,
    MechanicParameterProgression,
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
    CompatibilityFact,
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


@dataclass(frozen=True, slots=True)
class _TraitCandidate:
    key: str
    lineage_key: str
    definition: MechanicTemplateDefinition
    weight_milli: int


class CompatibleTraitAdditionPolicy:
    """Add one tier-, lineage-, mechanic-, and budget-compatible trait."""

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

    def add(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        *,
        locale: str = "de-DE",
    ) -> TraitDevelopmentAction:
        """Materialize exactly one deterministic compatible new trait."""
        if plan.primary_trait_action != "add_compatible_trait":
            raise CardDevelopmentPlanningError(
                "development plan does not authorize a compatible trait"
            )
        if not card.traits or len(card.traits) >= plan.trait_cap:
            raise CardDevelopmentPlanningError(
                "card does not have one free compatible-trait slot"
            )
        ruleset = self._model_repository.resolve_ruleset(
            key=card.provenance.ruleset_key,
            version=card.provenance.ruleset_version,
        )
        policy = self._development_repository.development_policy(ruleset)
        definitions = self._materialization_repository.mechanic_definitions(
            ruleset
        )
        definition_by_key = {item.key: item for item in definitions}
        if len(definition_by_key) != len(definitions):
            raise CardDevelopmentPlanningError(
                "mechanic definitions are ambiguous for development"
            )
        tier = self._tier(card, plan, ruleset)
        candidates = self._candidates(
            card,
            plan,
            policy,
            definition_by_key,
            self._materialization_repository.lineage_mechanic_eligibility(
                ruleset
            ),
            self._model_repository.class_lineage_compatibility(ruleset),
            self._model_repository.role_lineage_compatibility(ruleset),
            self._development_repository.lineage_compatibility(ruleset),
            self._development_repository.mechanic_compatibility(ruleset),
            self._development_repository.mechanic_parameter_progression(
                ruleset
            ),
        )
        if not candidates:
            raise CardDevelopmentPlanningError(
                "card has no legal compatible trait addition"
            )
        anchor_candidates = tuple(
            item
            for item in candidates
            if item.lineage_key == card.imprint.trait_lineage
        )
        pool = (
            anchor_candidates
            if policy.prefer_existing_lineage and anchor_candidates
            else candidates
        )
        selected_key = self._random(card).weighted_choice(
            f"development:{plan.next_tier.ordinal}:add-compatible-trait",
            tuple(
                (item.key, item.weight_milli)
                for item in sorted(pool, key=lambda candidate: candidate.key)
            ),
        )
        selected = next(item for item in pool if item.key == selected_key)
        mechanic = self._mechanics.materialize(
            selected.definition,
            tier,
            self._random(card),
        )
        trait = MaterializedTrait(
            lineage_key=selected.lineage_key,
            mechanic=mechanic,
            canonical_rule_text=self._rules.render(
                selected.definition, mechanic, locale=locale
            ),
        )
        return TraitDevelopmentAction(
            action="add_compatible_trait",
            trait_index=len(card.traits),
            previous_trait=None,
            developed_trait=trait,
        )

    def _candidates(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        policy: CardDevelopmentPolicy,
        definitions: dict[str, MechanicTemplateDefinition],
        eligibility: tuple[LineageMechanicEligibility, ...],
        class_compatibility: tuple[CompatibilityFact, ...],
        role_compatibility: tuple[CompatibilityFact, ...],
        lineage_compatibility: tuple[LineageCompatibility, ...],
        mechanic_compatibility: tuple[MechanicCompatibility, ...],
        progressions: tuple[MechanicParameterProgression, ...],
    ) -> tuple[_TraitCandidate, ...]:
        class_index = self._directed_index(class_compatibility, "class")
        role_index = self._directed_index(role_compatibility, "role")
        lineage_index = self._lineage_index(lineage_compatibility)
        mechanic_index = self._mechanic_index(mechanic_compatibility)
        current_cost = self._current_cost(card, definitions, progressions)
        existing_mechanics = frozenset(
            trait.mechanic.key for trait in card.traits
        )
        result: list[_TraitCandidate] = []
        for fact in eligibility:
            definition = definitions.get(fact.mechanic_key)
            if (
                definition is None
                or fact.mechanic_key in existing_mechanics
                or fact.min_tier_ordinal > plan.next_tier.ordinal
                or (
                    fact.max_tier_ordinal is not None
                    and plan.next_tier.ordinal > fact.max_tier_ordinal
                )
                or fact.selection_weight_milli <= 0
                or current_cost + definition.base_weight_milli
                > plan.mechanic_budget_milli
            ):
                continue
            class_fact = class_index.get(
                (card.imprint.card_class, fact.lineage_key)
            )
            role_fact = role_index.get(
                (card.imprint.combat_role, fact.lineage_key)
            )
            if not self._enabled(class_fact) or not self._enabled(role_fact):
                continue
            class_fact = cast(CompatibilityFact, class_fact)
            role_fact = cast(CompatibilityFact, role_fact)
            lineage_weight = self._lineage_weight(
                card.imprint.trait_lineage,
                fact.lineage_key,
                policy,
                lineage_index,
            )
            if lineage_weight is None:
                continue
            mechanic_weights = tuple(
                self._mechanic_weight(
                    existing,
                    fact.mechanic_key,
                    mechanic_index,
                )
                for existing in sorted(existing_mechanics)
            )
            if any(weight is None for weight in mechanic_weights):
                continue
            weights = (
                fact.selection_weight_milli,
                class_fact.weight_milli,
                role_fact.weight_milli,
                lineage_weight,
                *(cast(int, weight) for weight in mechanic_weights),
            )
            result.append(
                _TraitCandidate(
                    key=f"{fact.lineage_key}:{fact.mechanic_key}",
                    lineage_key=fact.lineage_key,
                    definition=definition,
                    weight_milli=sum(weights) // len(weights),
                )
            )
        keys = tuple(item.key for item in result)
        if len(keys) != len(set(keys)):
            raise CardDevelopmentPlanningError(
                "compatible trait candidates are ambiguous"
            )
        return tuple(sorted(result, key=lambda item: item.key))

    @staticmethod
    def _directed_index(
        facts: tuple[CompatibilityFact, ...], label: str
    ) -> dict[tuple[str, str], CompatibilityFact]:
        result: dict[tuple[str, str], CompatibilityFact] = {}
        for fact in facts:
            key = (fact.source_key, fact.target_key)
            if key in result:
                raise CardDevelopmentPlanningError(
                    f"{label} lineage compatibility is ambiguous"
                )
            result[key] = fact
        return result

    @staticmethod
    def _lineage_index(
        facts: tuple[LineageCompatibility, ...],
    ) -> dict[tuple[str, str], LineageCompatibility]:
        result: dict[tuple[str, str], LineageCompatibility] = {}
        for fact in facts:
            key = CompatibleTraitAdditionPolicy._pair(
                fact.lineage_a_key, fact.lineage_b_key
            )
            if key in result:
                raise CardDevelopmentPlanningError(
                    "lineage compatibility is ambiguous"
                )
            result[key] = fact
        return result

    @staticmethod
    def _mechanic_index(
        facts: tuple[MechanicCompatibility, ...],
    ) -> dict[tuple[str, str], MechanicCompatibility]:
        result: dict[tuple[str, str], MechanicCompatibility] = {}
        for fact in facts:
            key = CompatibleTraitAdditionPolicy._pair(
                fact.mechanic_a_key, fact.mechanic_b_key
            )
            if key in result:
                raise CardDevelopmentPlanningError(
                    "mechanic compatibility is ambiguous"
                )
            result[key] = fact
        return result

    @staticmethod
    def _enabled(fact: CompatibilityFact | None) -> bool:
        return fact is not None and fact.enabled and fact.weight_milli > 0

    @staticmethod
    def _lineage_weight(
        anchor: str,
        target: str,
        policy: CardDevelopmentPolicy,
        facts: dict[tuple[str, str], LineageCompatibility],
    ) -> int | None:
        if anchor == target:
            return 1000
        fact = facts.get(CompatibleTraitAdditionPolicy._pair(anchor, target))
        if not policy.cross_lineage_requires_compatibility and fact is None:
            return 500
        if (
            fact is None
            or fact.relation == "incompatible"
            or fact.weight_milli <= 0
        ):
            return None
        return fact.weight_milli

    @staticmethod
    def _mechanic_weight(
        current: str,
        target: str,
        facts: dict[tuple[str, str], MechanicCompatibility],
    ) -> int | None:
        fact = facts.get(CompatibleTraitAdditionPolicy._pair(current, target))
        if (
            fact is None
            or fact.relation == "incompatible"
            or fact.weight_milli <= 0
        ):
            return None
        return fact.weight_milli

    @staticmethod
    def _pair(first: str, second: str) -> tuple[str, str]:
        return (first, second) if first <= second else (second, first)

    @staticmethod
    def _current_cost(
        card: StructuredCardSpec,
        definitions: dict[str, MechanicTemplateDefinition],
        progressions: tuple[MechanicParameterProgression, ...],
    ) -> int:
        total = 0
        for trait in card.traits:
            definition = definitions.get(trait.mechanic.key)
            if definition is None:
                raise CardDevelopmentPlanningError(
                    "card trait references an unknown mechanic definition"
                )
            total += definition.base_weight_milli
            for upgrade in trait.parameter_upgrades:
                matches = tuple(
                    item
                    for item in progressions
                    if item.mechanic_key == trait.mechanic.key
                    and item.parameter_key == upgrade.parameter_key
                )
                if len(matches) != 1 or upgrade.applied_steps <= 0:
                    raise CardDevelopmentPlanningError(
                        "materialized parameter upgrade has no unique progression"
                    )
                progression = matches[0]
                if (
                    progression.max_upgrade_steps is not None
                    and upgrade.applied_steps > progression.max_upgrade_steps
                ):
                    raise CardDevelopmentPlanningError(
                        "materialized parameter upgrade exceeds its step cap"
                    )
                total += upgrade.applied_steps * progression.budget_cost_milli
        return total

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
