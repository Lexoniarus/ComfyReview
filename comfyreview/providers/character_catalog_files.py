"""Strict, read-only adapter for byte-preserved Character Lab v8.2 data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from comfyreview.domain.character_catalog import (
    CharacterProfile,
    CharacterRevisions,
)

_CHARACTER_IDS = (
    "aiko",
    "hina",
    "kaori",
    "mitsuki",
    "natsumi",
    "saki",
)
_PROFILE_FIELDS = (
    "public_identity",
    "personal_values",
    "behavioral_signature",
    "voice_signature",
    "internal_mechanisms",
    "private_topics",
    "forbidden_in_low_trust",
    "general_boundaries",
)
_PROFILE_KEYS = frozenset(
    (
        "schema_version",
        "character_id",
        "display_name",
        "status",
        "source_file",
        "base_personality_type",
        "base_axis_vector",
        *_PROFILE_FIELDS,
    )
)
_EXPECTED_MEMBERS = frozenset(
    name
    for character_id in _CHARACTER_IDS
    for name in (
        f"characters/{character_id}.json",
        f"prompts/characters/{character_id}.md",
        f"sources/{character_id.title()}.md",
    )
)
_MAX_RESOURCE_BYTES = 128 * 1024


class CharacterCatalogDataError(ValueError):
    """Invalid, incomplete or unavailable authored catalog resources."""


class UnknownCharacterError(LookupError):
    """The requested stable character ID is not in the catalog."""


@dataclass(frozen=True, slots=True)
class _CharacterRecord:
    profile: CharacterProfile
    voice_prompt: str
    source_document: str
    revisions: CharacterRevisions


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CharacterCatalogDataError(f"Invalid character field: {field}")
    return value


def _required_lines(value: object, field: str) -> tuple[str, ...]:
    if (
        not isinstance(value, list)
        or not value
        or any(not isinstance(item, str) or not item.strip() for item in value)
    ):
        raise CharacterCatalogDataError(f"Invalid character list: {field}")
    return tuple(value)


def _decode_profile(content: bytes, character_id: str) -> CharacterProfile:
    try:
        raw: object = json.loads(content.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise CharacterCatalogDataError(
            f"Invalid JSON profile: {character_id}"
        ) from exc
    if not isinstance(raw, dict) or set(raw) != _PROFILE_KEYS:
        raise CharacterCatalogDataError(
            f"Invalid profile structure: {character_id}"
        )
    data = cast(dict[str, object], raw)
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise CharacterCatalogDataError(
            f"Unsupported profile schema: {character_id}"
        )
    if data["character_id"] != character_id:
        raise CharacterCatalogDataError(
            f"Profile ID does not match resource: {character_id}"
        )
    if data["source_file"] != f"{character_id.title()}.md":
        raise CharacterCatalogDataError(
            f"Unexpected source document: {character_id}"
        )
    # Personality candidates have not been approved as canonical traits.
    if (
        data["base_personality_type"] is not None
        or data["base_axis_vector"] is not None
    ):
        raise CharacterCatalogDataError(
            f"Unapproved personality assignment: {character_id}"
        )
    return CharacterProfile(
        character_id=_required_text(data["character_id"], "character_id"),
        display_name=_required_text(data["display_name"], "display_name"),
        status=_required_text(data["status"], "status"),
        source_file=_required_text(data["source_file"], "source_file"),
        public_identity=_required_lines(
            data["public_identity"], "public_identity"
        ),
        personal_values=_required_lines(
            data["personal_values"], "personal_values"
        ),
        behavioral_signature=_required_lines(
            data["behavioral_signature"], "behavioral_signature"
        ),
        voice_signature=_required_lines(
            data["voice_signature"], "voice_signature"
        ),
        internal_mechanisms=_required_lines(
            data["internal_mechanisms"], "internal_mechanisms"
        ),
        private_topics=_required_lines(
            data["private_topics"], "private_topics"
        ),
        forbidden_in_low_trust=_required_lines(
            data["forbidden_in_low_trust"], "forbidden_in_low_trust"
        ),
        general_boundaries=_required_lines(
            data["general_boundaries"], "general_boundaries"
        ),
    )


def _revision(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()[:16]


class FileCharacterCatalog:
    """Load six immutable originals once; do not create or edit files."""

    def __init__(self, root: Path) -> None:
        self._root = root
        try:
            paths = {
                path.relative_to(root).as_posix()
                for directory in (
                    root / "characters",
                    root / "prompts" / "characters",
                    root / "sources",
                )
                for path in directory.rglob("*")
                if path.is_file() or path.is_symlink()
            }
            if paths != _EXPECTED_MEMBERS:
                raise CharacterCatalogDataError(
                    "Missing or unexpected character resources"
                )
            self._records = {
                character_id: self._load_record(character_id)
                for character_id in _CHARACTER_IDS
            }
        except OSError as exc:
            raise CharacterCatalogDataError(
                "Could not read original character resources"
            ) from exc

    def _read_resource(self, relative_path: str) -> bytes:
        path = self._root / relative_path
        if path.is_symlink():
            raise CharacterCatalogDataError(
                f"Linked character resource: {relative_path}"
            )
        try:
            if path.stat().st_size > _MAX_RESOURCE_BYTES:
                raise CharacterCatalogDataError(
                    f"Oversized character resource: {relative_path}"
                )
            return path.read_bytes()
        except OSError as exc:
            raise CharacterCatalogDataError(
                f"Could not read character resource: {relative_path}"
            ) from exc

    def _load_record(self, character_id: str) -> _CharacterRecord:
        profile_bytes = self._read_resource(f"characters/{character_id}.json")
        voice_bytes = self._read_resource(
            f"prompts/characters/{character_id}.md"
        )
        source_bytes = self._read_resource(
            f"sources/{character_id.title()}.md"
        )
        profile = _decode_profile(profile_bytes, character_id)
        try:
            voice_prompt = voice_bytes.decode("utf-8")
            source_document = source_bytes.decode("utf-8")
        except UnicodeError as exc:
            raise CharacterCatalogDataError(
                f"Invalid UTF-8 character source: {character_id}"
            ) from exc
        if not voice_prompt.strip() or not source_document.strip():
            raise CharacterCatalogDataError(
                f"Empty character source: {character_id}"
            )
        source_revision = _revision(source_bytes)
        return _CharacterRecord(
            profile=profile,
            voice_prompt=voice_prompt,
            source_document=source_document,
            revisions=CharacterRevisions(
                source=source_revision,
                profile=_revision(
                    profile_bytes + source_revision.encode("ascii")
                ),
                voice_prompt=_revision(voice_bytes),
            ),
        )

    def _require(self, character_id: str) -> _CharacterRecord:
        try:
            return self._records[character_id]
        except KeyError as exc:
            raise UnknownCharacterError(
                f"Unknown character ID: {character_id}"
            ) from exc

    def character_ids(self) -> tuple[str, ...]:
        """Return stable IDs in deterministic source order."""
        return _CHARACTER_IDS

    def profile(self, character_id: str) -> CharacterProfile:
        """Return one immutable internal character profile."""
        return self._require(character_id).profile

    def voice_prompt(self, character_id: str) -> str:
        """Return the unchanged original character voice prompt."""
        return self._require(character_id).voice_prompt

    def source_document(self, character_id: str) -> str:
        """Return the unchanged original character source document."""
        return self._require(character_id).source_document

    def revisions(self, character_id: str) -> CharacterRevisions:
        """Return deterministic content revisions for all three sources."""
        return self._require(character_id).revisions
