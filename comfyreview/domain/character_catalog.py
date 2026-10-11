"""Immutable authored character facts and revision identities."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CharacterProfile:
    """Internal authored character profile, including restricted details."""

    character_id: str
    display_name: str
    status: str
    source_file: str
    public_identity: tuple[str, ...]
    personal_values: tuple[str, ...]
    behavioral_signature: tuple[str, ...]
    voice_signature: tuple[str, ...]
    internal_mechanisms: tuple[str, ...]
    private_topics: tuple[str, ...]
    forbidden_in_low_trust: tuple[str, ...]
    general_boundaries: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CharacterRevisions:
    """Content-addressed revisions of the original authored resources."""

    source: str
    profile: str
    voice_prompt: str


@dataclass(frozen=True, slots=True)
class PublicCharacter:
    """Deliberately restricted metadata safe for future API projection."""

    character_id: str
    display_name: str
    status: str
    revisions: CharacterRevisions
