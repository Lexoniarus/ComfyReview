"""Strict read-only adapter for the authored v8.2 speaker prompt set."""

from __future__ import annotations

import hashlib
from pathlib import Path

from comfyreview.domain.character_prompts import PromptResource

_VARIANTS = ("baseline", "voice_candidate_p2", "voice_precise")
_MAX_RESOURCE_BYTES = 16 * 1024


class PromptCatalogDataError(ValueError):
    """The authored prompt set is incomplete, malformed or unsafe."""


class UnknownPromptVariantError(LookupError):
    """Only explicitly shipped prompt variants can be selected."""


class UnknownVoiceCandidateError(LookupError):
    """A candidate must belong to an existing C1 character."""


class FilePromptCatalog:
    """Load revisioned text once; never create, modify or promote it."""

    def __init__(self, root: Path, character_ids: tuple[str, ...]) -> None:
        if not character_ids or len(set(character_ids)) != len(
            character_ids
        ):
            raise PromptCatalogDataError("Invalid C1 character set")
        expected = {
            "global_speaker.md",
            *(f"variants/{variant}.md" for variant in _VARIANTS),
            *(f"candidates/{actor}.md" for actor in character_ids),
            *(f"characters/{actor}.md" for actor in character_ids),
        }
        actual = {
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() or path.is_symlink()
        }
        if actual != expected:
            raise PromptCatalogDataError(
                "Missing or unexpected authored prompt resources"
            )
        self._global = self._read(root, "global_speaker.md")
        self._variants = {
            name: self._read(root, f"variants/{name}.md")
            for name in _VARIANTS
        }
        self._candidates = {
            actor: self._read(root, f"candidates/{actor}.md")
            for actor in character_ids
        }
        for actor, resource in self._candidates.items():
            if (
                not resource.content.startswith(f"# {actor.title()} · ")
                or "(unbestätigt)" not in resource.content
                or not 250 <= len(resource.content) <= 1400
            ):
                raise PromptCatalogDataError(
                    f"Invalid unapproved candidate: {actor}"
                )

    @staticmethod
    def _read(root: Path, relative_path: str) -> PromptResource:
        path = root / relative_path
        if path.is_symlink():
            raise PromptCatalogDataError(
                f"Linked authored prompt resource: {relative_path}"
            )
        try:
            if path.stat().st_size > _MAX_RESOURCE_BYTES:
                raise PromptCatalogDataError(
                    f"Oversized authored prompt: {relative_path}"
                )
            content = path.read_bytes()
        except OSError as exc:
            raise PromptCatalogDataError(
                f"Unable to read authored prompt: {relative_path}"
            ) from exc
        try:
            decoded = content.decode("utf-8")
        except UnicodeError as exc:
            raise PromptCatalogDataError(
                f"Invalid UTF-8 authored prompt: {relative_path}"
            ) from exc
        if not decoded.strip():
            raise PromptCatalogDataError(
                f"Empty authored prompt: {relative_path}"
            )
        return PromptResource(
            resource_id=relative_path.removesuffix(".md"),
            content=decoded,
            revision=hashlib.sha256(content).hexdigest(),
        )

    def global_speaker(self) -> PromptResource:
        """Return the authored global speaker contract."""
        return self._global

    def variant(self, variant_id: str) -> PromptResource:
        """Require an explicitly named authored variant."""
        try:
            return self._variants[variant_id]
        except KeyError as exc:
            raise UnknownPromptVariantError(variant_id) from exc

    def candidate(self, character_id: str) -> PromptResource:
        """Return an explicitly unapproved candidate by character ID."""
        try:
            return self._candidates[character_id]
        except KeyError as exc:
            raise UnknownVoiceCandidateError(character_id) from exc
