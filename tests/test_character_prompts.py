"""C2a: v8.2 prompt fidelity, composition and trust-boundary checks."""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from comfyreview.application.character_prompt_composer import (
    CharacterPromptComposer,
    PersonalityGuidanceUnavailable,
)
from comfyreview.domain.character_catalog import (
    CharacterRevisions,
    PublicCharacter,
)
from comfyreview.domain.character_prompts import PersonalityPromptGuidance
from comfyreview.providers.character_prompt_files import (
    FilePromptCatalog,
    PromptCatalogDataError,
    UnknownPromptVariantError,
    UnknownVoiceCandidateError,
)

ROOT = (
    Path(__file__).resolve().parents[1]
    / "comfyreview/resources/character_lab/prompts"
)
CAST = ("aiko", "hina", "kaori", "mitsuki", "natsumi", "saki")
AUTHORED_SHA256 = {
    "global_speaker.md": (
        "a8fefca1c204c239de07b8374be91a73137363c11a5115b9b04d25998d0bb8f8"
    ),
    "variants/baseline.md": (
        "b54387945e4dc9d7def1a33dc125eb56f89fec9cba261ff8e1a9470e78c3baf4"
    ),
    "variants/voice_candidate_p2.md": (
        "42cae6e8835793e6ea92b698566257f1535ede8ffc9d2a862c8a089ed218b261"
    ),
    "variants/voice_precise.md": (
        "7ed2e2b53db1b91418d13e54da6225f00349f6c4d9849a1d3a20dbbe038a06d7"
    ),
    "candidates/aiko.md": (
        "3ca53e9a8459ea431ea998c71d2cc3db4aa6632b79a3ab0fc5cb1e0b135530ab"
    ),
    "candidates/hina.md": (
        "7ac407bbac73af6a4194dd51437e8d8208137e86139387b67713b1aa458145cd"
    ),
    "candidates/kaori.md": (
        "e44f424420fc404024115995f8cc2fa7889fca139b5275cb1d219829c353f209"
    ),
    "candidates/mitsuki.md": (
        "f3cb299dfed58a030b05bc52b0ef1855dbdf1a258be84345d17c19dbbf03c124"
    ),
    "candidates/natsumi.md": (
        "715ce5b15c34e322435c695bd449ec5ab918914f2f899195ee7bcfbabd0cd25e"
    ),
    "candidates/saki.md": (
        "8c2f7bb73b439a998eb1c65b074f6551f9e53e51a43f3042ba4d11ef85c2685a"
    ),
}


class _C1Voices:
    """Strict fake for the preexisting character-catalog port."""

    def get_public(self, character_id: str) -> PublicCharacter:
        if character_id not in CAST:
            raise LookupError("Unknown C1 character")
        return PublicCharacter(
            character_id=character_id,
            display_name=character_id.title(),
            status="draft_fixture",
            revisions=self.get_revisions(character_id),
        )

    def get_voice_prompt(self, character_id: str) -> str:
        return (ROOT / "characters" / f"{character_id}.md").read_text(
            encoding="utf-8"
        )

    def get_revisions(self, character_id: str) -> CharacterRevisions:
        content = (ROOT / "characters" / f"{character_id}.md").read_bytes()
        return CharacterRevisions(
            source="source",
            profile="profile",
            voice_prompt=hashlib.sha256(content).hexdigest()[:16],
        )


class _Personality:
    def __init__(self, content: str, revision: str) -> None:
        self.content = content
        self.revision = revision
        self.called = 0

    def guidance(self, character_id: str) -> PersonalityPromptGuidance:
        self.called += 1
        assert character_id in CAST
        return PersonalityPromptGuidance(self.content, self.revision)


def _copy(tmp_path: Path) -> Path:
    target = tmp_path / "prompts"
    shutil.copytree(ROOT, target)
    return target


def _composer(
    *,
    personality: _Personality | None = None,
) -> CharacterPromptComposer:
    return CharacterPromptComposer(
        _C1Voices(), FilePromptCatalog(ROOT, CAST), personality
    )


def test_original_v82_prompt_bytes_and_explicit_catalog_revisions() -> None:
    """All ten new prompt files match independent v8.2 SHA-256 evidence."""
    assert len(AUTHORED_SHA256) == 10
    catalog = FilePromptCatalog(ROOT, CAST)
    resources = [catalog.global_speaker()]
    for variant in ("baseline", "voice_candidate_p2", "voice_precise"):
        resources.append(catalog.variant(variant))
    for actor in CAST:
        resources.append(catalog.candidate(actor))
    assert {item.resource_id + ".md" for item in resources} == set(
        AUTHORED_SHA256
    )
    for resource in resources:
        relative = resource.resource_id + ".md"
        digest = hashlib.sha256((ROOT / relative).read_bytes())
        assert digest.hexdigest() == AUTHORED_SHA256[relative]
        assert resource.revision == AUTHORED_SHA256[relative]
        assert resource.content == (ROOT / relative).read_text(
            encoding="utf-8"
        )
    assert catalog.global_speaker() is catalog.global_speaker()
    assert catalog.candidate("aiko") is catalog.candidate("aiko")


def test_composer_is_stable_and_c1_voice_is_only_baseline_voice() -> None:
    """Do not repeat dossiers or use candidates by default."""
    composer = _composer()
    for actor in CAST:
        baseline = composer.compose(actor)
        same = composer.compose(actor, "baseline")
        original = _C1Voices().get_voice_prompt(actor)
        assert baseline == same
        assert baseline.voice_selection == "original"
        assert baseline.personality_enabled is False
        assert baseline.variant_id == "baseline"
        assert original.strip() in baseline.system_instructions
        assert "# GLOBAL SPEAKER CONTRACT" in baseline.system_instructions
        assert (
            "# INDIVIDUAL CHARACTER IDENTITY AND VOICE"
            in baseline.system_instructions
        )
        assert "# SELECTED PROMPT VARIANT" in baseline.system_instructions
        assert (
            "# EXPERIMENTAL VOICE CANDIDATE"
            not in baseline.system_instructions
        )
        assert all(
            item.role != "candidate_voice" for item in baseline.resources
        )
        roles = tuple(item.role for item in baseline.resources)
        assert roles == ("global_speaker", "original_voice", "variant")
        revision = _C1Voices().get_revisions(actor).voice_prompt
        assert baseline.original_voice_revision == revision
        assert len(baseline.composition_revision) == 64
        assert "earlier_messages" not in baseline.system_instructions
        assert "permitted_memory_excerpts" not in baseline.system_instructions
        with pytest.raises(FrozenInstanceError):
            baseline.__setattr__("voice_selection", "candidate")


def test_variants_are_selected_explicitly_and_compared_fairly() -> None:
    """Candidate use is visible, revisioned, actor-local and not canonical."""
    composer = _composer()
    for actor in CAST:
        baseline = composer.compose(actor)
        precise = composer.compose(actor, "voice_precise")
        candidate = composer.compose(actor, "voice_candidate_p2")
        assert precise.voice_selection == "original"
        assert precise.resources[1] == baseline.resources[1]
        assert precise.resources[2] != baseline.resources[2]
        assert candidate.voice_selection == "experimental_candidate"
        assert candidate.personality_enabled is False
        assert candidate.original_voice_revision == (
            baseline.original_voice_revision
        )
        assert candidate.resources[0] == baseline.resources[0]
        assert candidate.resources[1].role == "candidate_voice"
        candidate_digest = AUTHORED_SHA256[f"candidates/{actor}.md"]
        assert candidate.resources[1].revision == candidate_digest
        assert "(unbestätigt)" in candidate.system_instructions
        assert composer.compose(actor, "voice_candidate_p2") == candidate
        assert candidate.composition_revision != baseline.composition_revision
        assert precise.composition_revision != baseline.composition_revision
        assert candidate.system_instructions != baseline.system_instructions
        original = _C1Voices().get_voice_prompt(actor)
        assert original.strip() not in candidate.system_instructions
        assert "Name: " + actor.title() in candidate.system_instructions
    aiko = composer.compose("aiko")
    hina = composer.compose("hina")
    assert aiko.composition_revision != hina.composition_revision


def test_no_unknown_character_or_variant_can_be_composed() -> None:
    composer = _composer()
    with pytest.raises(LookupError, match="Unknown C1"):
        composer.compose("invented")
    with pytest.raises(UnknownPromptVariantError):
        composer.compose("aiko", "unknown_variant")
    catalog = FilePromptCatalog(ROOT, CAST)
    with pytest.raises(UnknownVoiceCandidateError):
        catalog.candidate("invented")


def test_personality_is_inert_until_explicitly_enabled() -> None:
    personality = _Personality("Optional direction", "experimental-rev")
    composer = _composer(personality=personality)
    base = composer.compose("aiko")
    assert personality.called == 0
    assert all(x.role != "personality" for x in base.resources)
    enabled = composer.compose("aiko", enable_personality=True)
    assert personality.called == 1
    assert enabled.personality_enabled is True
    assert enabled.resources[-1].role == "personality"
    assert enabled.resources[-1].revision == "experimental-rev"
    assert enabled.composition_revision != base.composition_revision
    assert "Optional direction" in enabled.system_instructions
    with pytest.raises(PersonalityGuidanceUnavailable, match="configured"):
        _composer().compose("aiko", enable_personality=True)
    for content, revision in ((" ", "rev"), ("ok", " ")):
        bad = _composer(personality=_Personality(content, revision))
        with pytest.raises(PersonalityGuidanceUnavailable, match="revision"):
            bad.compose("aiko", enable_personality=True)


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("global_speaker.md", "Missing"),
        ("variants/baseline.md", "Missing"),
        ("candidates/aiko.md", "Missing"),
        ("characters/aiko.md", "Missing"),
    ],
)
def test_missing_resource_fails_closed(
    tmp_path: Path,
    path: str,
    message: str,
) -> None:
    root = _copy(tmp_path)
    (root / path).unlink()
    with pytest.raises(PromptCatalogDataError, match=message):
        FilePromptCatalog(root, CAST)


def test_extra_or_linked_resource_and_invalid_character_ids_fail(
    tmp_path: Path,
) -> None:
    root = _copy(tmp_path)
    (root / "variants" / "surprise.md").write_text("unexpected")
    with pytest.raises(PromptCatalogDataError, match="unexpected"):
        FilePromptCatalog(root, CAST)
    (root / "variants" / "surprise.md").unlink()
    candidate = root / "candidates" / "aiko.md"
    candidate.unlink()
    try:
        candidate.symlink_to(ROOT / "candidates" / "aiko.md")
    except OSError:
        pytest.skip("Symlinks unavailable")
    with pytest.raises(PromptCatalogDataError, match="Linked"):
        FilePromptCatalog(root, CAST)
    with pytest.raises(PromptCatalogDataError, match="character set"):
        FilePromptCatalog(ROOT, ())
    with pytest.raises(PromptCatalogDataError, match="character set"):
        FilePromptCatalog(ROOT, ("aiko", "aiko"))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (b"\xff", "Invalid UTF-8"),
        (b" ", "Empty"),
        (b"x" * (16 * 1024 + 1), "Oversized"),
    ],
)
def test_malformed_resource_is_rejected(
    tmp_path: Path,
    content: bytes,
    message: str,
) -> None:
    root = _copy(tmp_path)
    (root / "global_speaker.md").write_bytes(content)
    with pytest.raises(PromptCatalogDataError, match=message):
        FilePromptCatalog(root, CAST)


def test_invalid_candidate_is_never_silently_promoted(tmp_path: Path) -> None:
    root = _copy(tmp_path)
    (root / "candidates" / "hina.md").write_text(
        "# Hina · Canonical voice\n" + "x" * 260,
        encoding="utf-8",
    )
    with pytest.raises(PromptCatalogDataError, match="unapproved"):
        FilePromptCatalog(root, CAST)


def test_unreadable_resource_fails_with_typed_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy(tmp_path)
    original = Path.read_bytes

    def failing_read(path: Path) -> bytes:
        if path.name == "global_speaker.md":
            raise OSError("temporary denial")
        return original(path)

    monkeypatch.setattr(Path, "read_bytes", failing_read)
    with pytest.raises(PromptCatalogDataError, match="Unable"):
        FilePromptCatalog(root, CAST)
