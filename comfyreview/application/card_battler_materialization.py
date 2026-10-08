"""Typed model facts used to materialize deterministic Card Battler cards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from comfyreview.application.card_battler_model import CardBattlerRulesetRef

StatProfileAffinitySource = Literal["class", "role", "lineage"]
MechanicAffinitySource = Literal["world_style", "class", "role", "lineage"]


@dataclass(frozen=True, slots=True)
class CardBalancePolicy:
    """Versioned integer-only balance configuration from the model."""

    key: str
    version: int
    stat_rounding_step: int
    atk_def_minimum: int
    no_negative_stats: bool
    trait_budget_is_milli: bool
    calibration_status: str


@dataclass(frozen=True, slots=True)
class TierBalanceProfile:
    """Budget and legal stat bounds for one exact development tier."""

    rarity_key: str
    level: int
    ordinal: int
    stat_budget: int
    mechanic_budget_milli: int
    min_atk: int
    max_atk: int
    min_def: int
    max_def: int
    max_traits: int
    parameter_scale_milli: int


@dataclass(frozen=True, slots=True)
class StatProfileDefinition:
    """Declare one stable ATK/DEF share profile."""

    key: str
    name: str
    atk_share_milli: int
    def_share_milli: int
    description: str


@dataclass(frozen=True, slots=True)
class StatProfileAffinity:
    """Relate one imprint axis value to one stat profile."""

    source: StatProfileAffinitySource
    source_key: str
    stat_profile_key: str
    weight_milli: int


@dataclass(frozen=True, slots=True)
class MechanicUsageLimitDefinition:
    """Describe one usage limit attached to a mechanic template."""

    usage_limit_key: str
    max_uses: int | None
    scope: str
    reset_trigger_key: str | None


@dataclass(frozen=True, slots=True)
class RuleTextTemplateDefinition:
    """Provide one versioned localized authoritative rule template."""

    locale: str
    version: int
    template_text: str


@dataclass(frozen=True, slots=True)
class MechanicParameterEnumValue:
    """Expose one ordered enum option for a mechanic parameter."""

    key: str
    sort_order: int
    description: str | None


@dataclass(frozen=True, slots=True)
class MechanicParameterDefinition:
    """Describe one mechanic- or step-scoped parameter."""

    key: str
    branch_key: str | None
    step_order: int | None
    value_type: str
    min_int: int | None
    max_int: int | None
    step_int: int | None
    default_int: int | None
    allowed_values: tuple[str, ...]
    enum_values: tuple[MechanicParameterEnumValue, ...]


@dataclass(frozen=True, slots=True)
class MechanicConditionDefinition:
    """Describe one ordered condition inside a condition group."""

    order: int
    condition_type_key: str
    target_type_key: str | None
    comparator: str | None
    value_int: int | None
    value_text: str | None
    negated: bool
    status_type_key: str | None


@dataclass(frozen=True, slots=True)
class MechanicConditionGroupDefinition:
    """Combine ordered conditions with one deterministic boolean operator."""

    order: int
    operator: str
    join_with_previous: str | None
    scope: str
    conditions: tuple[MechanicConditionDefinition, ...]


@dataclass(frozen=True, slots=True)
class MechanicStepDefinition:
    """Describe one ordered effect step inside a mechanic branch."""

    order: int
    effect_type_key: str
    target_type_key: str
    duration_type_key: str
    status_type_key: str | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class MechanicBranchConditionGroupLink:
    """Attach a condition group to a branch without leaking database IDs."""

    order: int
    condition_group_order: int
    join_with_previous: str | None


@dataclass(frozen=True, slots=True)
class MechanicBranchDefinition:
    """Describe one ordered branch and its effect steps."""

    key: str
    order: int
    branch_type: str
    description: str | None
    condition_groups: tuple[MechanicBranchConditionGroupLink, ...]
    steps: tuple[MechanicStepDefinition, ...]


@dataclass(frozen=True, slots=True)
class MechanicCostDefinition:
    """Describe one ordered cost attached to a mechanic."""

    order: int
    cost_type_key: str
    target_type_key: str | None
    amount: int | None
    notes: str | None


@dataclass(frozen=True, slots=True)
class MechanicStructureDefinition:
    """Hold the complete structured rule graph for one mechanic."""

    branches: tuple[MechanicBranchDefinition, ...]
    condition_groups: tuple[MechanicConditionGroupDefinition, ...]
    costs: tuple[MechanicCostDefinition, ...]
    parameters: tuple[MechanicParameterDefinition, ...]


@dataclass(frozen=True, slots=True)
class MechanicTemplateDefinition:
    """Expose an active mechanic template without SQLite identities."""

    key: str
    internal_name: str
    description: str
    base_weight_milli: int
    default_trigger_key: str
    default_usage_limit_key: str | None
    usage_limits: tuple[MechanicUsageLimitDefinition, ...]
    rule_text_templates: tuple[RuleTextTemplateDefinition, ...]
    structure: MechanicStructureDefinition


@dataclass(frozen=True, slots=True)
class LineageMechanicEligibility:
    """Declare a mechanic legal for one lineage across a tier interval."""

    lineage_key: str
    mechanic_key: str
    min_tier_ordinal: int
    max_tier_ordinal: int | None
    selection_weight_milli: int


@dataclass(frozen=True, slots=True)
class MechanicAffinity:
    """Relate one imprint-axis value to a mechanic template."""

    source: MechanicAffinitySource
    source_key: str
    mechanic_key: str
    weight_milli: int


class CardMaterializationModelRepository(Protocol):
    """Supply immutable balance and materialization facts."""

    def balance_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBalancePolicy:
        """Resolve one active or explicitly versioned balance policy."""
        ...

    def tier_balance_profile(
        self,
        balance_policy: CardBalancePolicy,
        *,
        rarity_key: str,
        level: int,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> TierBalanceProfile:
        """Return the exact balance profile for a rarity and level."""
        ...

    def stat_profiles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[StatProfileDefinition, ...]:
        """Return active stat profiles in stable key order."""
        ...

    def stat_profile_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[StatProfileAffinity, ...]:
        """Return class, role and lineage affinities in stable order."""
        ...

    def mechanic_definitions(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicTemplateDefinition, ...]:
        """Return active mechanic templates with usage and rule facts."""
        ...

    def lineage_mechanic_eligibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[LineageMechanicEligibility, ...]:
        """Return lineage legality in stable lineage/mechanic order."""
        ...

    def mechanic_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicAffinity, ...]:
        """Return imprint-axis mechanic affinities in stable order."""
        ...
