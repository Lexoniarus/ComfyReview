"""Typed read models for Card Battler visual prompt projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

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
