"""Application ports and immutable read models for card development."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, cast

from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.domain.card_battler import (
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    CardDevelopmentPlan,
    CardDevelopmentProvenance,
    DevelopmentTier,
    PrimaryTraitAction,
    StructuredCardSpec,
)


class CardDevelopmentPlanningError(RuntimeError):
    """Signal that a card cannot take one valid next-tier step."""


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
CompatibilityRelation = Literal[
    "preferred", "compatible", "neutral", "incompatible"
]


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


@dataclass(frozen=True, slots=True)
class LineageCompatibility:
    """Describe one symmetric compatibility relation between lineages."""

    lineage_a_key: str
    lineage_b_key: str
    relation: CompatibilityRelation
    weight_milli: int
    notes: str | None


@dataclass(frozen=True, slots=True)
class MechanicCompatibility:
    """Describe one symmetric compatibility relation between mechanics."""

    mechanic_a_key: str
    mechanic_b_key: str
    relation: CompatibilityRelation
    weight_milli: int
    notes: str | None


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

    def lineage_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[LineageCompatibility, ...]:
        """Return symmetric lineage compatibility facts in stable order."""
        ...

    def mechanic_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicCompatibility, ...]:
        """Return symmetric mechanic compatibility facts in stable order."""
        ...


class DevelopmentPlanner:
    """Plan one exact next-tier step without changing card mechanics."""

    def __init__(
        self,
        model_repository: CardBattlerModelRepository,
        development_repository: CardDevelopmentModelRepository,
    ) -> None:
        self._model_repository = model_repository
        self._development_repository = development_repository

    def plan(self, card: StructuredCardSpec) -> CardDevelopmentPlan:
        """Return the deterministic plan for exactly the next model tier."""
        ruleset = self._model_repository.resolve_ruleset(
            key=card.provenance.ruleset_key,
            version=card.provenance.ruleset_version,
        )
        repository = self._development_repository
        policy = repository.development_policy(ruleset)
        ladder = repository.development_ladder(
            ruleset,
            balance_policy_key=card.provenance.balance_policy_key,
            balance_policy_version=card.provenance.balance_policy_version,
        )
        current = self._current_tier(card, ladder)
        next_tier = self._next_tier(current, ladder, policy)
        action = self._primary_action(
            card,
            next_tier,
            policy,
            repository.development_action_weights(ruleset),
        )
        provenance = CardDevelopmentProvenance(
            development_policy_key=policy.key,
            development_policy_version=policy.version,
            development_algorithm_revision=(
                CARD_DEVELOPMENT_ALGORITHM_REVISION
            ),
        )
        return CardDevelopmentPlan(
            current_tier=self._domain_tier(current),
            next_tier=self._domain_tier(next_tier),
            stat_budget=next_tier.stat_budget,
            mechanic_budget_milli=next_tier.mechanic_budget_milli,
            trait_cap=next_tier.trait_cap,
            parameter_scale_milli=next_tier.parameter_scale_milli,
            primary_trait_action=action,
            provenance=provenance,
        )

    @staticmethod
    def _current_tier(
        card: StructuredCardSpec,
        ladder: tuple[DevelopmentTierModel, ...],
    ) -> DevelopmentTierModel:
        matches = tuple(
            tier
            for tier in ladder
            if tier.ordinal == card.tier_ordinal
            and tier.rarity_key == card.rarity_key
            and tier.level == card.level
        )
        if len(matches) != 1:
            raise CardDevelopmentPlanningError(
                "card does not match one development tier"
            )
        current = matches[0]
        if (
            card.stats.budget != current.stat_budget
            or card.stats.attack + card.stats.defense != card.stats.budget
        ):
            raise CardDevelopmentPlanningError(
                "card stats do not match its development tier"
            )
        if len(card.traits) > current.trait_cap:
            raise CardDevelopmentPlanningError(
                "card exceeds its current trait cap"
            )
        return current

    @staticmethod
    def _next_tier(
        current: DevelopmentTierModel,
        ladder: tuple[DevelopmentTierModel, ...],
        policy: CardDevelopmentPolicy,
    ) -> DevelopmentTierModel:
        if current.development_locked or current.next_ordinal is None:
            raise CardDevelopmentPlanningError(
                "card development is locked at its current tier"
            )
        matches = tuple(
            tier for tier in ladder if tier.ordinal == current.next_ordinal
        )
        if len(matches) != 1 or current.next_ordinal != current.ordinal + 1:
            raise CardBattlerModelInvalid(
                "development ladder does not expose one exact next tier"
            )
        next_tier = matches[0]
        if next_tier.development_locked or (
            next_tier.rarity_key == "legendary"
            and policy.legendary_locked_in_prototype
        ):
            raise CardDevelopmentPlanningError(
                "card development into the next tier is locked"
            )
        return next_tier

    def _primary_action(
        self,
        card: StructuredCardSpec,
        next_tier: DevelopmentTierModel,
        policy: CardDevelopmentPolicy,
        weights: tuple[TierDevelopmentActionWeight, ...],
    ) -> PrimaryTraitAction:
        supported = frozenset(
            {
                "add_first_trait",
                "improve_existing_trait",
                "add_compatible_trait",
            }
        )
        if any(
            action not in supported for action in policy.primary_trait_actions
        ):
            raise CardBattlerModelInvalid(
                "development policy contains an unknown primary action"
            )
        structurally_legal = (
            frozenset({"add_first_trait"})
            if not card.traits
            else frozenset(
                {"improve_existing_trait"}
                | (
                    {"add_compatible_trait"}
                    if len(card.traits) < next_tier.trait_cap
                    else set()
                )
            )
        )
        candidates = tuple(
            (weight.action_key, weight.weight_milli)
            for weight in weights
            if weight.tier_ordinal == next_tier.ordinal
            and weight.action_key in policy.primary_trait_actions
            and weight.action_key in structurally_legal
            and weight.enabled
            and weight.weight_milli > 0
        )
        if not candidates:
            raise CardDevelopmentPlanningError(
                "next tier has no legal primary trait action"
            )
        selected = self._random(card).weighted_choice(
            f"development:{next_tier.ordinal}", candidates
        )
        return cast(PrimaryTraitAction, selected)

    @staticmethod
    def _domain_tier(tier: DevelopmentTierModel) -> DevelopmentTier:
        return DevelopmentTier(
            rarity_key=tier.rarity_key,
            level=tier.level,
            ordinal=tier.ordinal,
        )

    @staticmethod
    def _random(card: StructuredCardSpec) -> DomainSeparatedCardRandom:
        imprint = card.imprint
        return DomainSeparatedCardRandom(
            (
                imprint.source_image_uid,
                imprint.semantic_revision,
                f"{imprint.ruleset_key}@{imprint.ruleset_version}",
                (
                    f"{imprint.mapping_policy_key}"
                    f"@{imprint.mapping_policy_version}"
                ),
                f"{imprint.rng_policy_key}@{imprint.rng_policy_version}",
                str(imprint.explicit_seed),
            )
        )
