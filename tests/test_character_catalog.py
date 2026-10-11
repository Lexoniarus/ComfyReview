"""C1 behavior and source-integrity tests for the authored character cast."""

from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import FrozenInstanceError, asdict
from pathlib import Path

import pytest

from comfyreview.application.character_catalog import (
    CharacterCatalogPort,
    CharacterCatalogService,
)
from comfyreview.providers.character_catalog_files import (
    CharacterCatalogDataError,
    FileCharacterCatalog,
    UnknownCharacterError,
)

ROOT = (
    Path(__file__).resolve().parents[1] / "comfyreview/resources/character_lab"
)
HASH_MANIFEST = ROOT / "original_sha256.json"
CAST = ("aiko", "hina", "kaori", "mitsuki", "natsumi", "saki")


def _originals() -> dict[str, bytes]:
    paths = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    return {path: (ROOT / path).read_bytes() for path in paths}


def _copy_resources(tmp_path: Path) -> Path:
    destination = tmp_path / "resources"
    shutil.copytree(ROOT, destination)
    return destination


def _alter_resource(
    tmp_path: Path,
    relative_path: str,
    content: bytes,
) -> Path:
    destination = _copy_resources(tmp_path)
    (destination / relative_path).write_bytes(content)
    return destination


def test_v82_original_resources_are_byte_exact() -> None:
    """Preserve hashes captured independently from the v8.2 ZIP."""
    content = _originals()
    digests = json.loads(HASH_MANIFEST.read_text(encoding="utf-8"))
    assert len(content) == 18
    for path, expected in digests.items():
        assert hashlib.sha256(content[path]).hexdigest() == expected


def test_six_profiles_are_loaded_with_revisioned_sources() -> None:
    adapter = FileCharacterCatalog(ROOT)
    catalog: CharacterCatalogPort = adapter
    service = CharacterCatalogService(catalog)
    assert adapter.character_ids() == CAST
    assert tuple(c.character_id for c in service.list_public()) == CAST
    originals = _originals()

    for character_id in CAST:
        profile = service.get_profile(character_id)
        assert profile.character_id == character_id
        assert profile.display_name == character_id.title()
        assert profile.status == "draft_fixture"
        assert profile.source_file == f"{character_id.title()}.md"
        assert all(
            (
                profile.public_identity,
                profile.personal_values,
                profile.behavioral_signature,
                profile.voice_signature,
                profile.internal_mechanisms,
                profile.private_topics,
                profile.forbidden_in_low_trust,
                profile.general_boundaries,
            )
        )
        source_bytes = originals[f"sources/{character_id.title()}.md"]
        voice_bytes = originals[f"prompts/characters/{character_id}.md"]
        profile_bytes = originals[f"characters/{character_id}.json"]
        assert service.get_source_document(
            character_id
        ) == source_bytes.decode("utf-8")
        assert service.get_voice_prompt(character_id) == voice_bytes.decode(
            "utf-8"
        )
        revision = service.get_revisions(character_id)
        assert revision.source == hashlib.sha256(source_bytes).hexdigest()[:16]
        assert (
            revision.voice_prompt
            == hashlib.sha256(voice_bytes).hexdigest()[:16]
        )
        assert (
            revision.profile
            == hashlib.sha256(
                profile_bytes + revision.source.encode("ascii")
            ).hexdigest()[:16]
        )
        assert service.get_public(character_id).revisions == revision


def test_public_projection_hides_private_and_personality_details() -> None:
    service = CharacterCatalogService(FileCharacterCatalog(ROOT))
    for summary in service.list_public():
        data = asdict(summary)
        assert set(data) == {
            "character_id",
            "display_name",
            "status",
            "revisions",
        }
        text = json.dumps(data)
        profile = service.get_profile(summary.character_id)
        assert profile.private_topics[0] not in text
        assert profile.internal_mechanisms[0] not in text
        assert "base_personality" not in text
    saki = service.get_profile("saki")
    assert "17" in saki.public_identity[0]
    assert "seventeen" in service.get_source_document("saki").lower()
    with pytest.raises(FrozenInstanceError):
        saki.status = "canon"  # type: ignore[misc]


def test_unknown_character_fails_explicitly_for_every_read() -> None:
    service = CharacterCatalogService(FileCharacterCatalog(ROOT))
    for method in (
        service.get_profile,
        service.get_public,
        service.get_voice_prompt,
        service.get_source_document,
        service.get_revisions,
    ):
        with pytest.raises(UnknownCharacterError, match="unknown-id"):
            method("unknown-id")


@pytest.mark.parametrize(
    "missing_path",
    ["characters/aiko.json", "sources/Aiko.md", "prompts/characters/aiko.md"],
)
def test_missing_resource_fails(tmp_path: Path, missing_path: str) -> None:
    destination = _copy_resources(tmp_path)
    (destination / missing_path).unlink()
    with pytest.raises(CharacterCatalogDataError, match="Missing"):
        FileCharacterCatalog(destination)


def test_extra_resource_fails(tmp_path: Path) -> None:
    destination = _copy_resources(tmp_path)
    (destination / "sources/Secret.md").write_bytes(b"private")
    with pytest.raises(CharacterCatalogDataError, match="unexpected"):
        FileCharacterCatalog(destination)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("schema_version", 2, "schema"),
        ("schema_version", True, "schema"),
        ("character_id", "hina", "ID"),
        ("source_file", "../Hina.md", "source"),
        ("base_personality_type", "INTJ", "personality"),
        ("base_axis_vector", {"social_energy": 1}, "personality"),
        ("private_topics", [], "list"),
        ("private_topics", [5], "list"),
        ("status", "", "field"),
        ("surprise", "extra", "structure"),
    ],
)
def test_invalid_profile_or_unapproved_personality_fails_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    raw = json.loads(_originals()["characters/aiko.json"])
    raw[field] = value
    content = json.dumps(raw, ensure_ascii=False).encode("utf-8")
    destination = _alter_resource(tmp_path, "characters/aiko.json", content)
    with pytest.raises(CharacterCatalogDataError, match=message):
        FileCharacterCatalog(destination)


@pytest.mark.parametrize(
    "path",
    ["characters/aiko.json", "prompts/characters/aiko.md", "sources/Aiko.md"],
)
def test_invalid_utf8_fails(tmp_path: Path, path: str) -> None:
    destination = _alter_resource(tmp_path, path, b"\xff\xfe")
    with pytest.raises(CharacterCatalogDataError, match="Invalid"):
        FileCharacterCatalog(destination)


@pytest.mark.parametrize(
    "path",
    ["prompts/characters/aiko.md", "sources/Aiko.md"],
)
def test_empty_voice_or_document_fails(tmp_path: Path, path: str) -> None:
    destination = _alter_resource(tmp_path, path, b" ")
    with pytest.raises(CharacterCatalogDataError, match="Empty"):
        FileCharacterCatalog(destination)


def test_invalid_json_and_nonobject_profile_fail(tmp_path: Path) -> None:
    for content in (b"{", b"[]"):
        destination = _alter_resource(
            tmp_path, "characters/aiko.json", content
        )
        with pytest.raises(CharacterCatalogDataError, match="Invalid"):
            FileCharacterCatalog(destination)
        shutil.rmtree(destination)


def test_oversized_resource_and_missing_directory_fail(
    tmp_path: Path,
) -> None:
    destination = _alter_resource(
        tmp_path, "sources/Aiko.md", b"a" * (128 * 1024 + 1)
    )
    with pytest.raises(CharacterCatalogDataError, match="Oversized"):
        FileCharacterCatalog(destination)
    with pytest.raises(CharacterCatalogDataError, match="Missing"):
        FileCharacterCatalog(tmp_path / "missing")


def test_symlink_source_is_rejected(tmp_path: Path) -> None:
    destination = _copy_resources(tmp_path)
    target = destination / "sources/Aiko.md"
    original_bytes = target.read_bytes()
    target.unlink()
    outside = tmp_path / "outside.md"
    outside.write_bytes(original_bytes)
    try:
        target.symlink_to(outside)
    except OSError:
        pytest.skip("Symlinks unavailable")
    with pytest.raises(CharacterCatalogDataError, match="Linked"):
        FileCharacterCatalog(destination)
