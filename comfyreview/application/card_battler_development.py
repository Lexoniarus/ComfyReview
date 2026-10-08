"""Application ports and immutable read models for card development."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from comfyreview.application.card_battler_model import CardBattlerRulesetRef


@dataclass(frozen=True, slots=True)
class CardDevelopmentPolicy:
    """Versioned policy facts that constrain every development decision."""

    key: str
    version: int
    cross_lineage_requires_compatibility: bool
    immutable_imprint_dimensions: tuple[str, ...]
    legendary_locked_in_prototype: bool
    prefer_existing_lineage: bool
    primary_trait_actions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DevelopmentTierModel:
    """One ordered development tier with its authoritative budgets and cap."""

    rarity_key: str
    rarity_name: str
    rarity_ordinal: int
    level: int
    ordinal: int
    next_ordinal: int | None
    development_locked: bool
    balance_policy_key: str
    balance_policy_version: int
    stat_budget: int
    mechanic_budget_milli: int
    trait_cap: int
    parameter_scale_milli: int


@dataclass(frozen=True, slots=True)
class TierDevelopmentActionWeight:
    """Declare one weighted primary action for one development tier."""

    tier_ordinal: int
    action_key: str
    action_name: str
    action_description: str
    weight_milli: int
    enabled: bool


MechanicUpgradeKind = Literal["replace", "branch", "augment"]


@dataclass(frozen=True, slots=True)
class MechanicUpgradeEdge:
    """Declare one registered mechanic-to-mechanic development edge."""

    from_mechanic_key: str
    to_mechanic_key: str
    min_tier_ordinal: int
    max_tier_ordinal: int | None
    weight_milli: int
    upgrade_kind: MechanicUpgradeKind
    notes: str | None


@dataclass(frozen=True, slots=True)
class MechanicParameterProgression:
    """Declare the legal upgrade budget for one mechanic parameter."""

    mechanic_key: str
    parameter_key: str
    min_tier_ordinal: int
    max_tier_ordinal: int | None
    upgrade_step_int: int | None
    max_upgrade_steps: int | None
    budget_cost_milli: int


class CardDevelopmentModelRepository(Protocol):
    """Read versioned development facts from the immutable model resource."""

    def development_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardDevelopmentPolicy:
        """Return the active or explicitly selected development policy."""
        ...

    def development_ladder(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        balance_policy_key: str | None = None,
        balance_policy_version: int | None = None,
    ) -> tuple[DevelopmentTierModel, ...]:
        """Return the complete ordered ladder with budgets and trait caps."""
        ...

    def development_action_weights(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[TierDevelopmentActionWeight, ...]:
        """Return stable per-tier primary-action weights."""
        ...

    def mechanic_upgrade_edges(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicUpgradeEdge, ...]:
        """Return registered mechanic upgrade edges in stable order."""
        ...

    def mechanic_parameter_progression(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicParameterProgression, ...]:
        """Return registered parameter progressions in stable order."""
        ...
