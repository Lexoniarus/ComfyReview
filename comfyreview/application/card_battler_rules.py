"""Deterministic materialization of structured Card Battler mechanics."""

from __future__ import annotations

from comfyreview.application.card_battler_materialization import (
    MechanicBranchDefinition,
    MechanicConditionDefinition,
    MechanicParameterDefinition,
    MechanicTemplateDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.domain.card_battler import (
    MaterializedBranch,
    MaterializedBranchConditionGroup,
    MaterializedCondition,
    MaterializedConditionGroup,
    MaterializedCost,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedParameterValue,
    MaterializedStep,
    MaterializedUsageLimit,
)


class MechanicMaterializer:
    """Resolve one model-owned mechanic graph without inventing facts."""

    def materialize(
        self,
        mechanic: MechanicTemplateDefinition,
        tier: TierBalanceProfile,
        random: DomainSeparatedCardRandom,
    ) -> MaterializedMechanic:
        """Materialize parameters and copy the complete authoritative graph."""
        if not mechanic.key or not mechanic.default_trigger_key:
            raise CardBattlerModelInvalid(
                "mechanic requires stable key and default trigger"
            )
        if tier.parameter_scale_milli <= 0:
            raise CardBattlerModelInvalid(
                "tier parameter scale must be positive"
            )
        parameters = self._materialize_parameters(
            mechanic.structure.parameters, tier, random
        )
        parameter_by_key = {
            parameter.key: parameter for parameter in parameters
        }
        return MaterializedMechanic(
            key=mechanic.key,
            trigger_key=mechanic.default_trigger_key,
            usage_limits=self._usage_limits(mechanic),
            condition_groups=self._condition_groups(mechanic),
            branches=self._branches(mechanic, parameter_by_key),
            costs=self._costs(mechanic),
            parameters=tuple(
                parameter_by_key[definition.key]
                for definition in sorted(
                    mechanic.structure.parameters,
                    key=lambda item: item.key,
                )
                if definition.branch_key is None
                and definition.step_order is None
            ),
        )

    def _materialize_parameters(
        self,
        definitions: tuple[MechanicParameterDefinition, ...],
        tier: TierBalanceProfile,
        random: DomainSeparatedCardRandom,
    ) -> tuple[MaterializedParameter, ...]:
        ordered = tuple(sorted(definitions, key=lambda item: item.key))
        keys = tuple(definition.key for definition in ordered)
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise CardBattlerModelInvalid(
                "mechanic parameters require unique stable keys"
            )
        return tuple(
            MaterializedParameter(
                key=definition.key,
                value=self._parameter_value(definition, tier, random),
            )
            for definition in ordered
        )

    def _parameter_value(
        self,
        definition: MechanicParameterDefinition,
        tier: TierBalanceProfile,
        random: DomainSeparatedCardRandom,
    ) -> MaterializedParameterValue:
        domain = f"parameter:{definition.key}"
        if definition.value_type == "int":
            return self._integer_parameter(definition, tier, random, domain)
        if definition.value_type == "enum":
            return self._enum_parameter(definition, random, domain)
        if definition.value_type == "bool":
            self._require_empty_parameter_metadata(definition)
            return bool(random.integer(domain, modulo=2))
        raise CardBattlerModelInvalid(
            f"unknown mechanic parameter type {definition.value_type!r}"
        )

    @staticmethod
    def _integer_parameter(
        definition: MechanicParameterDefinition,
        tier: TierBalanceProfile,
        random: DomainSeparatedCardRandom,
        domain: str,
    ) -> int:
        values = (
            definition.min_int,
            definition.max_int,
            definition.step_int,
            definition.default_int,
        )
        if any(value is None for value in values):
            raise CardBattlerModelInvalid(
                "integer mechanic parameters require min, max, step and default"
            )
        minimum, maximum, step, default = (
            int(value) for value in values if value is not None
        )
        if (
            step <= 0
            or minimum > maximum
            or not minimum <= default <= maximum
            or (default - minimum) % step != 0
            or definition.allowed_values
            or definition.enum_values
        ):
            raise CardBattlerModelInvalid(
                "integer mechanic parameter bounds are invalid"
            )
        legal = tuple(range(minimum, maximum + 1, step))
        target = default * tier.parameter_scale_milli
        distance = min(abs(candidate * 1000 - target) for candidate in legal)
        nearest = tuple(
            candidate
            for candidate in legal
            if abs(candidate * 1000 - target) == distance
        )
        return nearest[random.integer(domain, modulo=len(nearest))]

    def _enum_parameter(
        self,
        definition: MechanicParameterDefinition,
        random: DomainSeparatedCardRandom,
        domain: str,
    ) -> str:
        if any(
            value is not None
            for value in (
                definition.min_int,
                definition.max_int,
                definition.step_int,
                definition.default_int,
            )
        ):
            raise CardBattlerModelInvalid(
                "enum mechanic parameters cannot define integer bounds"
            )
        enum_values = tuple(
            item.key
            for item in sorted(
                definition.enum_values,
                key=lambda item: (item.sort_order, item.key),
            )
        )
        allowed = definition.allowed_values
        if enum_values and allowed and set(enum_values) != set(allowed):
            raise CardBattlerModelInvalid(
                "enum mechanic parameter catalogs disagree"
            )
        candidates = enum_values or allowed
        if not candidates or len(candidates) != len(set(candidates)):
            raise CardBattlerModelInvalid(
                "enum mechanic parameters require unique allowed values"
            )
        return random.weighted_choice(
            domain, tuple((candidate, 1) for candidate in candidates)
        )

    @staticmethod
    def _require_empty_parameter_metadata(
        definition: MechanicParameterDefinition,
    ) -> None:
        if (
            any(
                value is not None
                for value in (
                    definition.min_int,
                    definition.max_int,
                    definition.step_int,
                    definition.default_int,
                )
            )
            or definition.allowed_values
            or definition.enum_values
        ):
            raise CardBattlerModelInvalid(
                "boolean mechanic parameters cannot define value catalogs"
            )

    @staticmethod
    def _usage_limits(
        mechanic: MechanicTemplateDefinition,
    ) -> tuple[MaterializedUsageLimit, ...]:
        ordered = tuple(
            sorted(
                mechanic.usage_limits,
                key=lambda item: (item.usage_limit_key, item.scope),
            )
        )
        identities = tuple(
            (item.usage_limit_key, item.scope) for item in ordered
        )
        if len(identities) != len(set(identities)):
            raise CardBattlerModelInvalid(
                "mechanic usage limits are ambiguous"
            )
        if mechanic.default_usage_limit_key is not None and not any(
            item.usage_limit_key == mechanic.default_usage_limit_key
            for item in ordered
        ):
            raise CardBattlerModelInvalid(
                "default usage limit has no mechanic definition"
            )
        return tuple(
            MaterializedUsageLimit(
                usage_limit_key=item.usage_limit_key,
                max_uses=item.max_uses,
                scope=item.scope,
                reset_trigger_key=item.reset_trigger_key,
            )
            for item in ordered
        )

    def _condition_groups(
        self,
        mechanic: MechanicTemplateDefinition,
    ) -> tuple[MaterializedConditionGroup, ...]:
        groups = tuple(
            sorted(
                mechanic.structure.condition_groups,
                key=lambda item: item.order,
            )
        )
        self._require_unique_orders(
            tuple(group.order for group in groups), "condition groups"
        )
        return tuple(
            MaterializedConditionGroup(
                order=group.order,
                operator=group.operator,
                join_with_previous=group.join_with_previous,
                scope=group.scope,
                conditions=self._conditions(group.conditions),
            )
            for group in groups
        )

    def _conditions(
        self,
        conditions: tuple[MechanicConditionDefinition, ...],
    ) -> tuple[MaterializedCondition, ...]:
        ordered = tuple(sorted(conditions, key=lambda item: item.order))
        self._require_unique_orders(
            tuple(item.order for item in ordered), "conditions"
        )
        result: list[MaterializedCondition] = []
        for item in ordered:
            if item.value_int is not None and item.value_text is not None:
                raise CardBattlerModelInvalid(
                    "mechanic condition has ambiguous values"
                )
            value: MaterializedParameterValue | None = item.value_int
            if value is None:
                value = item.value_text
            result.append(
                MaterializedCondition(
                    order=item.order,
                    condition_type_key=item.condition_type_key,
                    target_type_key=item.target_type_key,
                    comparator=item.comparator,
                    value=value,
                    negated=item.negated,
                    status_type_key=item.status_type_key,
                )
            )
        return tuple(result)

    def _branches(
        self,
        mechanic: MechanicTemplateDefinition,
        parameter_by_key: dict[str, MaterializedParameter],
    ) -> tuple[MaterializedBranch, ...]:
        branches = tuple(
            sorted(mechanic.structure.branches, key=lambda item: item.order)
        )
        self._require_unique_orders(
            tuple(branch.order for branch in branches), "branches"
        )
        keys = tuple(branch.key for branch in branches)
        if len(keys) != len(set(keys)) or any(not key for key in keys):
            raise CardBattlerModelInvalid(
                "mechanic branches require unique stable keys"
            )
        if any(
            definition.branch_key is not None
            and definition.branch_key not in set(keys)
            for definition in mechanic.structure.parameters
        ):
            raise CardBattlerModelInvalid(
                "mechanic parameter references an unknown branch"
            )
        group_orders = {
            group.order for group in mechanic.structure.condition_groups
        }
        return tuple(
            self._branch(
                branch,
                group_orders,
                mechanic.structure.parameters,
                parameter_by_key,
            )
            for branch in branches
        )

    def _branch(
        self,
        branch: MechanicBranchDefinition,
        group_orders: set[int],
        parameter_definitions: tuple[MechanicParameterDefinition, ...],
        parameter_by_key: dict[str, MaterializedParameter],
    ) -> MaterializedBranch:
        links = tuple(
            sorted(branch.condition_groups, key=lambda item: item.order)
        )
        self._require_unique_orders(
            tuple(link.order for link in links), "branch condition links"
        )
        if any(
            link.condition_group_order not in group_orders for link in links
        ):
            raise CardBattlerModelInvalid(
                "branch references an unknown condition group"
            )
        steps = tuple(sorted(branch.steps, key=lambda item: item.order))
        self._require_unique_orders(
            tuple(step.order for step in steps), "mechanic steps"
        )
        step_orders = {step.order for step in steps}
        if any(
            (definition.branch_key is None) != (definition.step_order is None)
            for definition in parameter_definitions
        ):
            raise CardBattlerModelInvalid(
                "mechanic parameter scope requires branch and step together"
            )
        if any(
            definition.branch_key == branch.key
            and definition.step_order not in step_orders
            for definition in parameter_definitions
        ):
            raise CardBattlerModelInvalid(
                "mechanic parameter references an unknown step"
            )
        return MaterializedBranch(
            key=branch.key,
            order=branch.order,
            branch_type=branch.branch_type,
            condition_groups=tuple(
                MaterializedBranchConditionGroup(
                    order=link.order,
                    condition_group_order=link.condition_group_order,
                    join_with_previous=link.join_with_previous,
                )
                for link in links
            ),
            steps=tuple(
                MaterializedStep(
                    order=step.order,
                    effect_type_key=step.effect_type_key,
                    target_type_key=step.target_type_key,
                    duration_type_key=step.duration_type_key,
                    status_type_key=step.status_type_key,
                    parameters=tuple(
                        parameter_by_key[definition.key]
                        for definition in sorted(
                            parameter_definitions,
                            key=lambda item: item.key,
                        )
                        if definition.branch_key == branch.key
                        and definition.step_order == step.order
                    ),
                )
                for step in steps
            ),
        )

    def _costs(
        self,
        mechanic: MechanicTemplateDefinition,
    ) -> tuple[MaterializedCost, ...]:
        costs = tuple(
            sorted(mechanic.structure.costs, key=lambda item: item.order)
        )
        self._require_unique_orders(
            tuple(cost.order for cost in costs), "mechanic costs"
        )
        return tuple(
            MaterializedCost(
                order=cost.order,
                cost_type_key=cost.cost_type_key,
                target_type_key=cost.target_type_key,
                amount=cost.amount,
            )
            for cost in costs
        )

    @staticmethod
    def _require_unique_orders(orders: tuple[int, ...], label: str) -> None:
        if len(orders) != len(set(orders)):
            raise CardBattlerModelInvalid(f"{label} require unique ordering")
