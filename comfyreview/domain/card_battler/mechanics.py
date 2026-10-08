"""Immutable mechanical facts for Card Battler cards."""

from __future__ import annotations

from dataclasses import dataclass

MaterializedParameterValue = int | str | bool


@dataclass(frozen=True, slots=True)
class MaterializedParameter:
    """Freeze one resolved parameter value."""

    key: str
    value: MaterializedParameterValue


@dataclass(frozen=True, slots=True)
class MaterializedCondition:
    """Freeze one resolved condition."""

    order: int
    condition_type_key: str
    target_type_key: str | None
    comparator: str | None
    value: MaterializedParameterValue | None
    negated: bool
    status_type_key: str | None


@dataclass(frozen=True, slots=True)
class MaterializedConditionGroup:
    """Freeze one ordered boolean condition group."""

    order: int
    operator: str
    join_with_previous: str | None
    scope: str
    conditions: tuple[MaterializedCondition, ...]


@dataclass(frozen=True, slots=True)
class MaterializedStep:
    """Freeze one resolved mechanic effect step."""

    order: int
    effect_type_key: str
    target_type_key: str
    duration_type_key: str
    status_type_key: str | None
    parameters: tuple[MaterializedParameter, ...]


@dataclass(frozen=True, slots=True)
class MaterializedBranchConditionGroup:
    """Attach one condition group to a branch without losing join semantics."""

    order: int
    condition_group_order: int
    join_with_previous: str | None


@dataclass(frozen=True, slots=True)
class MaterializedBranch:
    """Freeze one resolved mechanic branch."""

    key: str
    order: int
    branch_type: str
    condition_groups: tuple[MaterializedBranchConditionGroup, ...]
    steps: tuple[MaterializedStep, ...]


@dataclass(frozen=True, slots=True)
class MaterializedCost:
    """Freeze one resolved mechanic cost."""

    order: int
    cost_type_key: str
    target_type_key: str | None
    amount: int | None


@dataclass(frozen=True, slots=True)
class MaterializedUsageLimit:
    """Freeze one resolved mechanic usage limit."""

    usage_limit_key: str
    max_uses: int | None
    scope: str
    reset_trigger_key: str | None


@dataclass(frozen=True, slots=True)
class MaterializedMechanic:
    """Freeze the complete authoritative structure of one mechanic."""

    key: str
    trigger_key: str
    usage_limits: tuple[MaterializedUsageLimit, ...]
    condition_groups: tuple[MaterializedConditionGroup, ...]
    branches: tuple[MaterializedBranch, ...]
    costs: tuple[MaterializedCost, ...]
    parameters: tuple[MaterializedParameter, ...]


@dataclass(frozen=True, slots=True)
class MaterializedParameterUpgrade:
    """Count applied model-authorized upgrades for one stable parameter."""

    parameter_key: str
    applied_steps: int


@dataclass(frozen=True, slots=True)
class MaterializedTrait:
    """Attach one authoritative mechanic to its stable trait lineage."""

    lineage_key: str
    mechanic: MaterializedMechanic
    canonical_rule_text: str
    parameter_upgrades: tuple[MaterializedParameterUpgrade, ...] = ()
