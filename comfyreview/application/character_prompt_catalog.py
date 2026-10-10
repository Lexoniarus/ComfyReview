"""Read-only application ports for the Character Lab prompt experiment."""

from __future__ import annotations

from typing import Protocol

from comfyreview.domain.character_catalog import (
    CharacterRevisions,
    PublicCharacter,
)
from comfyreview.domain.character_prompts import (
    PersonalityPromptGuidance,
    PromptResource,
)

VOICE_CANDIDATE_VARIANT = "voice_candidate_p2"


class CharacterVoicePort(Protocol):
    """Read the existing C1 authoritative voice and its revisions."""

    def get_public(self, character_id: str) -> PublicCharacter: ...

    def get_voice_prompt(self, character_id: str) -> str: ...

    def get_revisions(self, character_id: str) -> CharacterRevisions: ...


class PromptCatalogPort(Protocol):
    """Resolve approved variants and explicitly unapproved candidates."""

    def global_speaker(self) -> PromptResource: ...

    def variant(self, variant_id: str) -> PromptResource: ...

    def candidate(self, character_id: str) -> PromptResource: ...


class PersonalityPromptPort(Protocol):
    """Optional, separately authorized future contribution provider."""

    def guidance(self, character_id: str) -> PersonalityPromptGuidance: ...
