"""Compose bounded, source-revisioned speaker instructions without chat data."""

from __future__ import annotations

import hashlib

from comfyreview.application.character_prompt_catalog import (
    VOICE_CANDIDATE_VARIANT,
    CharacterVoicePort,
    PersonalityPromptPort,
    PromptCatalogPort,
)
from comfyreview.domain.character_prompts import (
    ComposedCharacterPrompt,
    PromptResourceRevision,
    PromptRole,
    VoiceSelection,
)

_COMPOSITION_VERSION = "character-lab-c2a-v1"


class PersonalityGuidanceUnavailable(ValueError):
    """Personality was requested but no valid opt-in provider exists."""


def _composition_revision(
    *,
    character_id: str,
    variant_id: str,
    voice_selection: VoiceSelection,
    system_instructions: str,
    original_voice_revision: str,
    resources: tuple[PromptResourceRevision, ...],
) -> str:
    """Hash the actual instructions and all composition inputs stably."""
    fields = (
        _COMPOSITION_VERSION,
        character_id,
        variant_id,
        voice_selection,
        original_voice_revision,
        system_instructions,
        *(
            f"{item.role}:{item.resource_id}:{item.revision}"
            for item in resources
        ),
    )
    framed = "".join(f"{len(value)}:{value}" for value in fields)
    return hashlib.sha256(framed.encode("utf-8")).hexdigest()


class CharacterPromptComposer:
    """Use one existing C1 voice and explicitly selected lab resources."""

    def __init__(
        self,
        characters: CharacterVoicePort,
        prompts: PromptCatalogPort,
        personality: PersonalityPromptPort | None = None,
    ) -> None:
        self._characters = characters
        self._prompts = prompts
        self._personality = personality

    def compose(
        self,
        character_id: str,
        variant_id: str = "baseline",
        *,
        enable_personality: bool = False,
    ) -> ComposedCharacterPrompt:
        """Return system instructions; never insert chat, RAG or memories."""
        person = self._characters.get_public(character_id)
        original_voice = self._characters.get_voice_prompt(character_id)
        original_revision = self._characters.get_revisions(
            character_id
        ).voice_prompt
        global_speaker = self._prompts.global_speaker()
        variant = self._prompts.variant(variant_id)

        resources = [
            PromptResourceRevision(
                "global_speaker",
                global_speaker.resource_id,
                global_speaker.revision,
            ),
        ]
        voice_selection: VoiceSelection = "original"
        voice = original_voice
        voice_revision = original_revision
        voice_id = f"characters/{character_id}"
        role: PromptRole = "original_voice"
        if variant_id == VOICE_CANDIDATE_VARIANT:
            candidate = self._prompts.candidate(character_id)
            voice_selection = "experimental_candidate"
            voice = candidate.content
            voice_revision = candidate.revision
            voice_id = candidate.resource_id
            role = "candidate_voice"
        resources.append(
            PromptResourceRevision(role, voice_id, voice_revision)
        )
        resources.append(
            PromptResourceRevision(
                "variant", variant.resource_id, variant.revision
            )
        )
        sections = [
            "# GLOBAL SPEAKER CONTRACT\n" + global_speaker.content.strip(),
            "# INDIVIDUAL CHARACTER IDENTITY AND VOICE\n"
            + f"Name: {person.display_name}\n"
            + voice.strip(),
            "# SELECTED PROMPT VARIANT\n" + variant.content.strip(),
        ]
        if enable_personality:
            if self._personality is None:
                raise PersonalityGuidanceUnavailable(
                    "Personality guidance is not configured"
                )
            guidance = self._personality.guidance(character_id)
            if not guidance.content.strip() or not guidance.revision.strip():
                raise PersonalityGuidanceUnavailable(
                    "Personality guidance has no content or revision"
                )
            sections.append(
                "# EXPLICIT PERSONALITY EXPERIMENT\n"
                + guidance.content.strip()
            )
            resources.append(
                PromptResourceRevision(
                    "personality",
                    f"personality/{character_id}",
                    guidance.revision,
                )
            )
        system_instructions = "\n\n".join(sections)
        contributors = tuple(resources)
        return ComposedCharacterPrompt(
            character_id=person.character_id,
            variant_id=variant_id,
            voice_selection=voice_selection,
            system_instructions=system_instructions,
            resources=contributors,
            original_voice_revision=original_revision,
            composition_revision=_composition_revision(
                character_id=person.character_id,
                variant_id=variant_id,
                voice_selection=voice_selection,
                system_instructions=system_instructions,
                original_voice_revision=original_revision,
                resources=contributors,
            ),
            personality_enabled=enable_personality,
        )
