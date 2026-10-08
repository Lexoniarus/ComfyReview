"""Immutable Card Battler card facts."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.domain.card_battler.mechanics import MaterializedTrait

COMMON_CARD_MATERIALIZATION_REVISION = "common-card-materialization-v1"
CANONICAL_RULE_RENDERER_REVISION = "canonical-rule-renderer-v1"


@dataclass(frozen=True, slots=True)
class CardImprint:
    """Persistent four-axis Card DNA plus deterministic provenance."""

    world_style: str
    card_class: str
    combat_role: str
    trait_lineage: str
    source_image_uid: str
    semantic_revision: str
    ruleset_key: str
    ruleset_version: int
    mapping_policy_key: str
    mapping_policy_version: int
    rng_policy_key: str
    rng_policy_version: int
    rng_algorithm: str
    explicit_seed: int


@dataclass(frozen=True, slots=True)
class CardStats:
    """Freeze integer combat stats and their selected profile."""

    attack: int
    defense: int
    budget: int
    stat_profile_key: str


@dataclass(frozen=True, slots=True)
class CardRulesProvenance:
    """Freeze every data and code revision needed to reproduce card rules."""

    ruleset_key: str
    ruleset_version: int
    mapping_policy_key: str
    mapping_policy_version: int
    rng_policy_key: str
    rng_policy_version: int
    rng_algorithm: str
    balance_policy_key: str
    balance_policy_version: int
    explicit_seed: int
    materialization_algorithm_revision: str
    rule_renderer_revision: str


@dataclass(frozen=True, slots=True)
class StructuredCardSpec:
    """Authoritative structured card rules independent of presentation."""

    imprint: CardImprint
    rarity_key: str
    level: int
    tier_ordinal: int
    stats: CardStats
    traits: tuple[MaterializedTrait, ...]
    provenance: CardRulesProvenance
