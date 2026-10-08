"""Immutable Card Battler development facts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from comfyreview.domain.card_battler.cards import StructuredCardSpec
from comfyreview.domain.card_battler.mechanics import MaterializedTrait

CARD_DEVELOPMENT_ALGORITHM_REVISION = "card-development-v1"

PrimaryTraitAction = Literal[
    "add_first_trait",
    "improve_existing_trait",
    "add_compatible_trait",
]


@dataclass(frozen=True, slots=True)
class DevelopmentTier:
    """Identify one stable position in the sequential development ladder."""

    rarity_key: str
    level: int
    ordinal: int


@dataclass(frozen=True, slots=True)
class CardDevelopmentProvenance:
    """Freeze the policy and code revision used for one development step."""

    development_policy_key: str
    development_policy_version: int
    development_algorithm_revision: str


@dataclass(frozen=True, slots=True)
class CardDevelopmentPlan:
    """Describe one authorized next-tier step before trait materialization."""

    current_tier: DevelopmentTier
    next_tier: DevelopmentTier
    mechanic_budget_milli: int
    trait_cap: int
    primary_trait_action: PrimaryTraitAction
    provenance: CardDevelopmentProvenance


@dataclass(frozen=True, slots=True)
class TraitDevelopmentAction:
    """Record exactly one primary trait change performed by a step."""

    action: PrimaryTraitAction
    trait_index: int
    previous_trait: MaterializedTrait | None
    developed_trait: MaterializedTrait


@dataclass(frozen=True, slots=True)
class CardDevelopmentResult:
    """Return the developed card together with its single trait action."""

    card: StructuredCardSpec
    action: TraitDevelopmentAction
    provenance: CardDevelopmentProvenance
