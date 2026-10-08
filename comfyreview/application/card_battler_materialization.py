"""Typed model facts used to materialize deterministic Card Battler cards."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from comfyreview.application.card_battler_model import CardBattlerRulesetRef

StatProfileAffinitySource = Literal["class", "role", "lineage"]


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
