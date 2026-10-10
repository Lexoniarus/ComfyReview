"""Read-only character catalog use cases and injected port."""

from __future__ import annotations

from typing import Protocol

from comfyreview.domain.character_catalog import (
    CharacterProfile,
    CharacterRevisions,
    PublicCharacter,
)


class CharacterCatalogPort(Protocol):
    """Provide authored profiles without prescribing their storage."""

    def character_ids(self) -> tuple[str, ...]: ...

    def profile(self, character_id: str) -> CharacterProfile: ...

    def voice_prompt(self, character_id: str) -> str: ...

    def source_document(self, character_id: str) -> str: ...

    def revisions(self, character_id: str) -> CharacterRevisions: ...


class CharacterCatalogService:
    """Expose explicit public metadata and separate internal authored reads."""

    def __init__(self, catalog: CharacterCatalogPort) -> None:
        self._catalog = catalog

    def list_public(self) -> tuple[PublicCharacter, ...]:
        """List minimal metadata, never private character information."""
        return tuple(
            self.get_public(character_id)
            for character_id in self._catalog.character_ids()
        )

    def get_public(self, character_id: str) -> PublicCharacter:
        """Project metadata only for an existing character."""
        profile = self._catalog.profile(character_id)
        return PublicCharacter(
            character_id=profile.character_id,
            display_name=profile.display_name,
            status=profile.status,
            revisions=self._catalog.revisions(character_id),
        )

    def get_profile(self, character_id: str) -> CharacterProfile:
        """Read the full restricted profile for trusted internal callers."""
        return self._catalog.profile(character_id)

    def get_voice_prompt(self, character_id: str) -> str:
        """Read the original voice guide for trusted internal callers."""
        return self._catalog.voice_prompt(character_id)

    def get_source_document(self, character_id: str) -> str:
        """Read the original authored dossier for trusted internal callers."""
        return self._catalog.source_document(character_id)

    def get_revisions(self, character_id: str) -> CharacterRevisions:
        """Read revisions without returning restricted source text."""
        return self._catalog.revisions(character_id)
