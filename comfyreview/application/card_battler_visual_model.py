"""Typed read models for Card Battler visual prompt projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol

from comfyreview.application.card_battler_model import CardBattlerRulesetRef


@dataclass(frozen=True, slots=True)
class VisualProjectionPolicy:
    """Version the deterministic visual projection contract."""

    key: str
    version: int
    apply_intensity_channels: bool
    origin_semantics_are_upstream_inputs: bool
    render_syntax: str
    respect_exclusion_groups: bool
    respect_forbidden_bindings: bool
    stable_order: tuple[str, ...]
    weight_decimals: int
    weight_scale: int


@dataclass(frozen=True, slots=True)
class VisualProgressionProfile:
    """Expose per-channel intensity for one exact development tier."""

    tier_ordinal: int
    world_intensity_milli: int
    class_intensity_milli: int
    role_intensity_milli: int
    lineage_intensity_milli: int
    mechanic_intensity_milli: int
    semantic_preservation_milli: int


@dataclass(frozen=True, slots=True)
class PromptGroupDefinition:
    """Constrain deterministic selection inside one prompt group."""

    key: str
    name: str
    min_selected: int
    max_selected: int
    description: str


VisualPromptScope = Literal["positive", "negative"]
VisualPromptMode = Literal["optional", "required", "forbidden"]
VisualPromptSource = Literal[
    "semantic",
    "world_style",
    "class",
    "role",
    "lineage",
    "mechanic",
    "composite",
]


@dataclass(frozen=True, slots=True)
class VisualPromptAtomDefinition:
    """Expose one active canonical visual prompt atom."""

    key: str
    canonical_text: str
    category: str


@dataclass(frozen=True, slots=True)
class VisualPromptBinding:
    """Bind one source fact to one atom without leaking technical IDs."""

    source_type: VisualPromptSource
    source_key: str
    atom_key: str
    scope: VisualPromptScope
    mode: VisualPromptMode
    weight_milli: int
    min_tier_ordinal: int | None
    max_tier_ordinal: int | None
    selection_weight_milli: int
    prompt_group_key: str | None
    priority: int
    intensity_channel: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class CompositeProfileDefinition:
    """Describe one exact four-axis visual composite profile."""

    key: str
    name: str
    world_style_key: str
    class_key: str
    role_key: str
    lineage_key: str
    weight_milli: int
    description: str
    naming_hint: str
    presentation_hint: str


@dataclass(frozen=True, slots=True)
class PromptAtomExclusion:
    """Declare one symmetric pair of mutually exclusive prompt atoms."""

    atom_a_key: str
    atom_b_key: str
    reason: str


class CardVisualModelRepository(Protocol):
    """Read immutable visual projection facts from the model resource."""

    def projection_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> VisualProjectionPolicy:
        """Resolve one active or explicitly versioned projection policy."""
        ...

    def progression_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualProgressionProfile, ...]:
        """Return all tier intensity profiles in stable ordinal order."""
        ...

    def prompt_groups(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[PromptGroupDefinition, ...]:
        """Return stable prompt-selection groups."""
        ...

    def prompt_atoms(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualPromptAtomDefinition, ...]:
        """Return active canonical prompt atoms."""
        ...

    def prompt_bindings(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualPromptBinding, ...]:
        """Return every typed visual binding in stable order."""
        ...

    def composite_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[CompositeProfileDefinition, ...]:
        """Return active exact-axis composite profiles."""
        ...

    def prompt_atom_exclusions(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[PromptAtomExclusion, ...]:
        """Return stable symmetric atom exclusions."""
        ...
