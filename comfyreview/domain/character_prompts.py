"""Immutable prompt-composition output and source provenance contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

VoiceSelection = Literal["original", "experimental_candidate"]
PromptRole = Literal[
    "global_speaker",
    "original_voice",
    "candidate_voice",
    "variant",
    "personality",
]


@dataclass(frozen=True, slots=True)
class PromptResource:
    """One immutable authored resource with a content-derived revision."""

    resource_id: str
    content: str
    revision: str


@dataclass(frozen=True, slots=True)
class PromptResourceRevision:
    """Identify a specific contributor without disclosing its content."""

    role: PromptRole
    resource_id: str
    revision: str


@dataclass(frozen=True, slots=True)
class PersonalityPromptGuidance:
    """Future opt-in guidance; never a canonical personality assignment."""

    content: str
    revision: str


@dataclass(frozen=True, slots=True)
class ComposedCharacterPrompt:
    """System-only instructions; conversational data stays separate."""

    character_id: str
    variant_id: str
    voice_selection: VoiceSelection
    system_instructions: str
    resources: tuple[PromptResourceRevision, ...]
    original_voice_revision: str
    composition_revision: str
    personality_enabled: bool
