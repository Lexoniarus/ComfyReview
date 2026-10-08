"""Immutable output contracts for deterministic visual prompt projection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from comfyreview.application.card_battler_visual_model import (
    VisualPromptMode,
    VisualPromptScope,
    VisualPromptSource,
)

VISUAL_PROMPT_PROJECTION_REVISION = "visual-prompt-projection-v1"

VisualPromptDiagnosticLevel = Literal["info", "warning"]


@dataclass(frozen=True, slots=True)
class VisualPromptAtomSource:
    """Preserve one model binding that contributed to a selected atom."""

    source_type: VisualPromptSource
    source_key: str
    mode: VisualPromptMode
    weight_milli: int
    priority: int

    def __post_init__(self) -> None:
        if not self.source_key.strip():
            raise ValueError("visual prompt source key must be non-empty")
        if self.weight_milli <= 0:
            raise ValueError("visual prompt source weight must be positive")


@dataclass(frozen=True, slots=True)
class VisualPromptAtom:
    """Freeze one selected positive or negative canonical prompt atom."""

    key: str
    canonical_text: str
    scope: VisualPromptScope
    weight_milli: int
    required: bool
    priority: int
    sources: tuple[VisualPromptAtomSource, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "sources", tuple(self.sources))
        if not self.key.strip() or not self.canonical_text.strip():
            raise ValueError("visual prompt atom identity must be non-empty")
        if self.weight_milli <= 0:
            raise ValueError("visual prompt atom weight must be positive")
        if not self.sources:
            raise ValueError(
                "visual prompt atom must retain source provenance"
            )
        identities = tuple(
            (source.source_type, source.source_key, source.mode)
            for source in self.sources
        )
        if len(identities) != len(set(identities)):
            raise ValueError("visual prompt atom sources must be unique")


@dataclass(frozen=True, slots=True)
class VisualPromptDiagnostic:
    """Expose one non-fatal deterministic projection decision."""

    level: VisualPromptDiagnosticLevel
    code: str
    message: str
    atom_keys: tuple[str, ...] = ()
    source_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "atom_keys", tuple(self.atom_keys))
        object.__setattr__(self, "source_keys", tuple(self.source_keys))
        if not self.code.strip() or not self.message.strip():
            raise ValueError("visual prompt diagnostic must be descriptive")


@dataclass(frozen=True, slots=True)
class VisualPromptProvenance:
    """Freeze data, seed, RNG, and code revisions for one recipe."""

    ruleset_key: str
    ruleset_version: int
    projection_policy_key: str
    projection_policy_version: int
    explicit_seed: int
    rng_algorithm: str
    visual_projection_algorithm_revision: str

    def __post_init__(self) -> None:
        values = (
            self.ruleset_key,
            self.projection_policy_key,
            self.rng_algorithm,
            self.visual_projection_algorithm_revision,
        )
        if any(not value.strip() for value in values):
            raise ValueError(
                "visual prompt provenance revisions must be non-empty"
            )
        if self.ruleset_version <= 0 or self.projection_policy_version <= 0:
            raise ValueError(
                "visual prompt provenance versions must be positive"
            )


@dataclass(frozen=True, slots=True)
class VisualPromptRecipe:
    """Freeze a complete newly projected visual recipe for one exact tier."""

    tier_ordinal: int
    positive_atoms: tuple[VisualPromptAtom, ...]
    negative_atoms: tuple[VisualPromptAtom, ...]
    diagnostics: tuple[VisualPromptDiagnostic, ...]
    provenance: VisualPromptProvenance

    def __post_init__(self) -> None:
        object.__setattr__(self, "positive_atoms", tuple(self.positive_atoms))
        object.__setattr__(self, "negative_atoms", tuple(self.negative_atoms))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        if self.tier_ordinal <= 0:
            raise ValueError("visual prompt recipe tier must be positive")
        if any(atom.scope != "positive" for atom in self.positive_atoms):
            raise ValueError("positive recipe atoms must use positive scope")
        if any(atom.scope != "negative" for atom in self.negative_atoms):
            raise ValueError("negative recipe atoms must use negative scope")
        identities = tuple(
            (atom.scope, atom.key)
            for atom in self.positive_atoms + self.negative_atoms
        )
        if len(identities) != len(set(identities)):
            raise ValueError(
                "visual prompt recipe atoms must be unique per scope"
            )
