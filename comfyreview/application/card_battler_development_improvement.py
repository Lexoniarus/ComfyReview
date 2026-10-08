"""Combined existing-trait improvement policy for Card Battler cards."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import cast

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    MechanicParameterProgression,
    MechanicUpgradeEdge,
)
from comfyreview.application.card_battler_development_traits import (
    RegisteredMechanicUpgradePolicy,
)
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    LineageMechanicEligibility,
    MechanicParameterDefinition,
    MechanicTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.domain.card_battler import (
    CardDevelopmentPlan,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedParameterUpgrade,
    MaterializedTrait,
    StructuredCardSpec,
    TraitDevelopmentAction,
)


@dataclass(frozen=True, slots=True)
class _EdgeCandidate:
    key: str
    trait_index: int
    definition: MechanicTemplateDefinition
    weight_milli: int


@dataclass(frozen=True, slots=True)
class _ParameterCandidate:
    key: str
    trait_index: int
    definition: MechanicTemplateDefinition
    parameter: MechanicParameterDefinition
    progression: MechanicParameterProgression
    current_value: int
    weight_milli: int = 1000


_ImprovementCandidate = _EdgeCandidate | _ParameterCandidate


class ExistingTraitImprovementPolicy(RegisteredMechanicUpgradePolicy):
    """Improve one trait through an edge or one legal parameter step."""

    def __init__(
        self,
        model_repository: CardBattlerModelRepository,
        development_repository: CardDevelopmentModelRepository,
        materialization_repository: CardMaterializationModelRepository,
        mechanics: MechanicMaterializer,
        rules: CanonicalRuleRenderer,
    ) -> None:
        super().__init__(
            model_repository,
            development_repository,
            materialization_repository,
            mechanics,
            rules,
        )
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
        """Apply one deterministic improvement within the target budget."""
        if plan.primary_trait_action != "improve_existing_trait":
            raise CardDevelopmentPlanningError(
                "development plan does not authorize a trait improvement"
            )
        ruleset = self._model_repository.resolve_ruleset(
            key=card.provenance.ruleset_key,
            version=card.provenance.ruleset_version,
        )
        definitions = self._materialization_repository.mechanic_definitions(
            ruleset
        )
        definition_by_key = {item.key: item for item in definitions}
        if len(definition_by_key) != len(definitions):
            raise CardDevelopmentPlanningError(
                "mechanic definitions are ambiguous for development"
            )
        tier = self._tier(card, plan, ruleset)
        progressions = (
            self._development_repository.mechanic_parameter_progression(
                ruleset
            )
        )
        current_cost = self._current_mechanic_cost(
            card, definition_by_key, progressions
        )
        candidates: tuple[_ImprovementCandidate, ...] = (
            *self._edge_candidates(
                card,
                plan,
                definition_by_key,
                self._materialization_repository.lineage_mechanic_eligibility(
                    ruleset
                ),
                self._development_repository.mechanic_upgrade_edges(ruleset),
                progressions,
                current_cost,
            ),
            *self._parameter_candidates(
                card,
                plan,
                definition_by_key,
                progressions,
                current_cost,
            ),
        )
        if not candidates:
            raise CardDevelopmentPlanningError(
                "card has no legal existing-trait improvement"
            )
        selected_key = self._random(card).weighted_choice(
            f"development:{plan.next_tier.ordinal}:improve-existing-trait",
            tuple(
                (candidate.key, candidate.weight_milli)
                for candidate in sorted(candidates, key=lambda item: item.key)
            ),
        )
        selected = next(
            candidate
            for candidate in candidates
            if candidate.key == selected_key
        )
        if isinstance(selected, _EdgeCandidate):
            developed = self._edge_trait(card, selected, tier, locale)
        else:
            developed = self._parameter_trait(card, selected, locale)
        return TraitDevelopmentAction(
            action="improve_existing_trait",
            trait_index=selected.trait_index,
            previous_trait=card.traits[selected.trait_index],
            developed_trait=developed,
        )

    def _edge_candidates(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        definitions: dict[str, MechanicTemplateDefinition],
        eligibility: tuple[LineageMechanicEligibility, ...],
        edges: tuple[MechanicUpgradeEdge, ...],
        progressions: tuple[MechanicParameterProgression, ...],
        current_cost: int,
    ) -> tuple[_EdgeCandidate, ...]:
        raw = self._candidates(card, plan, definitions, eligibility, edges)
        result = []
        for key, trait_index, definition, weight in raw:
            current_definition = definitions[
                card.traits[trait_index].mechanic.key
            ]
            replaced_cost = (
                current_cost
                - current_definition.base_weight_milli
                - self._trait_parameter_cost(
                    card.traits[trait_index], progressions
                )
                + definition.base_weight_milli
            )
            if replaced_cost <= plan.mechanic_budget_milli:
                result.append(
                    _EdgeCandidate(
                        key=f"edge:{key}",
                        trait_index=trait_index,
                        definition=definition,
                        weight_milli=weight,
                    )
                )
        return tuple(result)

    def _parameter_candidates(
        self,
        card: StructuredCardSpec,
        plan: CardDevelopmentPlan,
        definitions: dict[str, MechanicTemplateDefinition],
        progressions: tuple[MechanicParameterProgression, ...],
        current_cost: int,
    ) -> tuple[_ParameterCandidate, ...]:
        candidates: list[_ParameterCandidate] = []
        for trait_index, trait in enumerate(card.traits):
            definition = definitions[trait.mechanic.key]
            parameters = {
                item.key: item for item in definition.structure.parameters
            }
            if len(parameters) != len(definition.structure.parameters):
                raise CardDevelopmentPlanningError(
                    "mechanic parameter definitions are ambiguous"
                )
            values = self._parameter_values(trait.mechanic)
            applied = {
                item.parameter_key: item for item in trait.parameter_upgrades
            }
            if len(applied) != len(trait.parameter_upgrades):
                raise CardDevelopmentPlanningError(
                    "materialized parameter upgrades are ambiguous"
                )
            for parameter_key, parameter in sorted(parameters.items()):
                matches = tuple(
                    item
                    for item in progressions
                    if item.mechanic_key == definition.key
                    and item.parameter_key == parameter_key
                    and item.min_tier_ordinal <= plan.next_tier.ordinal
                    and (
                        item.max_tier_ordinal is None
                        or plan.next_tier.ordinal <= item.max_tier_ordinal
                    )
                )
                if len(matches) > 1:
                    raise CardDevelopmentPlanningError(
                        "mechanic parameter progression is ambiguous"
                    )
                if not matches:
                    continue
                progression = matches[0]
                current_value = values.get(parameter_key)
                applied_steps = applied.get(
                    parameter_key,
                    MaterializedParameterUpgrade(parameter_key, 0),
                ).applied_steps
                if self._legal_parameter_step(
                    parameter,
                    progression,
                    current_value,
                    applied_steps,
                    current_cost,
                    plan.mechanic_budget_milli,
                ):
                    candidates.append(
                        _ParameterCandidate(
                            key=f"parameter:{trait_index}:{parameter_key}",
                            trait_index=trait_index,
                            definition=definition,
                            parameter=parameter,
                            progression=progression,
                            current_value=cast(int, current_value),
                        )
                    )
        return tuple(candidates)

    @staticmethod
    def _legal_parameter_step(
        parameter: MechanicParameterDefinition,
        progression: MechanicParameterProgression,
        current_value: object,
        applied_steps: int,
        current_cost: int,
        budget: int,
    ) -> bool:
        step = progression.upgrade_step_int
        if (
            parameter.value_type != "int"
            or isinstance(current_value, bool)
            or not isinstance(current_value, int)
            or parameter.min_int is None
            or parameter.max_int is None
            or parameter.step_int is None
            or parameter.step_int <= 0
            or step is None
            or step <= 0
            or step % parameter.step_int != 0
            or not parameter.min_int <= current_value <= parameter.max_int
            or (current_value - parameter.min_int) % parameter.step_int != 0
            or current_value + step > parameter.max_int
            or applied_steps < 0
            or (
                progression.max_upgrade_steps is not None
                and applied_steps >= progression.max_upgrade_steps
            )
            or progression.budget_cost_milli < 0
        ):
            return False
        return current_cost + progression.budget_cost_milli <= budget

    def _current_mechanic_cost(
        self,
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
            total += self._trait_parameter_cost(trait, progressions)
        return total

    @staticmethod
    def _trait_parameter_cost(
        trait: MaterializedTrait,
        progressions: tuple[MechanicParameterProgression, ...],
    ) -> int:
        total = 0
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

    def _edge_trait(
        self,
        card: StructuredCardSpec,
        candidate: _EdgeCandidate,
        tier: TierBalanceProfile,
        locale: str,
    ) -> MaterializedTrait:
        mechanic = self._mechanics.materialize(
            candidate.definition,
            tier,
            self._random(card),
        )
        return MaterializedTrait(
            lineage_key=card.traits[candidate.trait_index].lineage_key,
            mechanic=mechanic,
            canonical_rule_text=self._rules.render(
                candidate.definition, mechanic, locale=locale
            ),
        )

    def _parameter_trait(
        self,
        card: StructuredCardSpec,
        candidate: _ParameterCandidate,
        locale: str,
    ) -> MaterializedTrait:
        previous = card.traits[candidate.trait_index]
        step = cast(int, candidate.progression.upgrade_step_int)
        mechanic = self._replace_parameter(
            previous.mechanic,
            candidate.parameter.key,
            candidate.current_value + step,
        )
        upgrades = {
            item.parameter_key: item for item in previous.parameter_upgrades
        }
        prior = upgrades.get(candidate.parameter.key)
        upgrades[candidate.parameter.key] = MaterializedParameterUpgrade(
            candidate.parameter.key,
            (prior.applied_steps if prior is not None else 0) + 1,
        )
        return MaterializedTrait(
            lineage_key=previous.lineage_key,
            mechanic=mechanic,
            canonical_rule_text=self._rules.render(
                candidate.definition, mechanic, locale=locale
            ),
            parameter_upgrades=tuple(
                upgrades[key] for key in sorted(upgrades)
            ),
        )

    @staticmethod
    def _parameter_values(mechanic: MaterializedMechanic) -> dict[str, object]:
        parameters = list(mechanic.parameters)
        parameters.extend(
            parameter
            for branch in mechanic.branches
            for step in branch.steps
            for parameter in step.parameters
        )
        keys = tuple(item.key for item in parameters)
        if len(keys) != len(set(keys)):
            raise CardDevelopmentPlanningError(
                "materialized mechanic parameters are ambiguous"
            )
        return {item.key: item.value for item in parameters}

    @classmethod
    def _replace_parameter(
        cls,
        mechanic: MaterializedMechanic,
        parameter_key: str,
        value: int,
    ) -> MaterializedMechanic:
        replacement = MaterializedParameter(parameter_key, value)
        top_level = tuple(
            replacement if item.key == parameter_key else item
            for item in mechanic.parameters
        )
        branches = tuple(
            replace(
                branch,
                steps=tuple(
                    replace(
                        step,
                        parameters=tuple(
                            replacement if item.key == parameter_key else item
                            for item in step.parameters
                        ),
                    )
                    for step in branch.steps
                ),
            )
            for branch in mechanic.branches
        )
        return replace(mechanic, parameters=top_level, branches=branches)
