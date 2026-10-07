"""Typed application boundary for the read-only Card Battler model."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class CardBattlerModelError(RuntimeError):
    """Base failure raised while reading the Card Battler model resource."""


class CardBattlerModelNotFound(CardBattlerModelError):
    """Signal that the configured Card Battler model database is absent."""


class CardBattlerModelInvalid(CardBattlerModelError):
    """Signal that the configured model database violates its contract."""


class CardBattlerModelVersionUnsupported(CardBattlerModelError):
    """Signal that the model database schema version is not supported."""


@dataclass(frozen=True, slots=True)
class CardBattlerModelMetadata:
    """Describe the identity and version of the model database itself."""

    database_name: str
    schema_version: int
    seed_version: str | None
    purpose: str | None
    authority: str | None
    audit_status: str | None


@dataclass(frozen=True, slots=True)
class CardBattlerRulesetRef:
    """Identify one versioned Card Battler ruleset and semantic vocabulary."""

    key: str
    version: int
    name: str
    status: str
    description: str
    semantic_vocabulary_key: str
    semantic_vocabulary_version: int


@dataclass(frozen=True, slots=True)
class SemanticConceptDefinition:
    """Describe one controlled Stage-1 semantic concept and its aliases."""

    key: str
    name: str
    category_key: str
    category_name: str
    description: str
    aliases: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorldStyleDefinition:
    """Describe one selectable Card-Imprint World Style."""

    key: str
    name: str
    description: str
    parent_key: str | None


@dataclass(frozen=True, slots=True)
class CardClassDefinition:
    """Describe one selectable Card-Imprint Card Class."""

    key: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class CombatRoleDefinition:
    """Describe one selectable Card-Imprint Combat Role."""

    key: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class TraitLineageDefinition:
    """Describe one selectable Card-Imprint Trait Lineage."""

    key: str
    name: str
    description: str


@dataclass(frozen=True, slots=True)
class DevelopmentTierDefinition:
    """Describe one ordered rarity/level development tier."""

    ordinal: int
    rarity_key: str
    rarity_name: str
    rarity_ordinal: int
    level: int
    development_locked: bool
    next_ordinal: int | None


@dataclass(frozen=True, slots=True)
class MechanicTemplateReference:
    """Describe one mechanic template at catalog/reference granularity."""

    key: str
    internal_name: str
    description: str
    base_weight_milli: int


@dataclass(frozen=True, slots=True)
class CardBattlerModelSummary:
    """Summarize populated foundational model content for one ruleset."""

    semantic_concept_count: int
    world_style_count: int
    card_class_count: int
    combat_role_count: int
    trait_lineage_count: int
    development_tier_count: int
    mechanic_template_count: int
    prompt_atom_count: int
    integrity_ok: bool
    foreign_key_violation_count: int


class CardBattlerModelRepository(Protocol):
    """Read and validate the external Card Battler model resource."""

    def metadata(self) -> CardBattlerModelMetadata:
        """Return validated model-database identity and schema metadata."""
        ...

    def resolve_ruleset(
        self,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBattlerRulesetRef:
        """Resolve the active or explicitly requested versioned ruleset."""
        ...

    def semantic_concepts(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticConceptDefinition, ...]:
        """Return the controlled semantic vocabulary in stable order."""
        ...

    def world_styles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[WorldStyleDefinition, ...]:
        """Return active World Styles in stable order."""
        ...

    def card_classes(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CardClassDefinition, ...]:
        """Return active Card Classes in stable order."""
        ...

    def combat_roles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CombatRoleDefinition, ...]:
        """Return active Combat Roles in stable order."""
        ...

    def trait_lineages(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[TraitLineageDefinition, ...]:
        """Return active Trait Lineages in stable order."""
        ...

    def development_tiers(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[DevelopmentTierDefinition, ...]:
        """Return the ordered rarity/level development ladder."""
        ...

    def mechanic_templates(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicTemplateReference, ...]:
        """Return active mechanic templates at reference granularity."""
        ...

    def summary(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> CardBattlerModelSummary:
        """Return populated-model counts plus validation health facts."""
        ...
