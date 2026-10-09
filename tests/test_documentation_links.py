"""Regression tests for active Markdown and immutable historical references."""

from __future__ import annotations

import hashlib
from pathlib import Path

from scripts.check_documentation import (
    REQUIRED_FILES,
    SOURCE_BOUNDARY,
    find_documentation_issues,
)


def _write(root: Path, filename: str, content: str) -> Path:
    """Write a fixture document under a temporary repository."""
    path = root / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def _minimal_repo(root: Path) -> Path:
    """Build only the documents required by the validator."""
    for filename in REQUIRED_FILES:
        _write(root, filename, "# Example\n")
    sources = root / "docs" / "character-chronicles" / "sources"
    for index in range(24):
        _write(
            root,
            f"docs/character-chronicles/sources/source-{index:02}.md",
            "# Old source\n\n"
            "> SOURCE_MATERIAL – NICHT VERBINDLICH\n\n"
            "## Übernommene Quellenfassung\n\n"
            "[Old foundation](../foundation/missing.md)\n",
        )
    return sources


def test_current_documentation_links_and_source_boundaries() -> None:
    """Keep the live documentation tree navigable at this commit."""
    assert find_documentation_issues() == []


def test_missing_legacy_targets_in_original_source_are_allowed(
    tmp_path: Path,
) -> None:
    """Never rewrite archival targets into falsely current authority."""
    _minimal_repo(tmp_path)
    assert find_documentation_issues(tmp_path) == []


def test_active_broken_link_is_reported(tmp_path: Path) -> None:
    """Current documents must not link to nonexistent files."""
    _minimal_repo(tmp_path)
    _write(tmp_path, "docs/README.md", "[Missing](does-not-exist.md)\n")
    assert any(
        "missing link target" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_unicode_heading_and_invalid_heading(tmp_path: Path) -> None:
    """Resolve Unicode GitHub-style anchor fragments on current pages."""
    _minimal_repo(tmp_path)
    _write(tmp_path, "docs/other.md", "# Fehlende Vorgängerquellen\n")
    _write(
        tmp_path,
        "docs/README.md",
        "[Correct](other.md#fehlende-vorgängerquellen)\n",
    )
    assert find_documentation_issues(tmp_path) == []
    _write(
        tmp_path,
        "docs/README.md",
        "[Wrong](other.md#fehlende-anderer-quellen)\n",
    )
    assert any(
        "missing heading" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_missing_historical_source_banner_is_reported(
    tmp_path: Path,
) -> None:
    """Historic pages need a visible warning and original-text boundary."""
    source_dir = _minimal_repo(tmp_path)
    (source_dir / "source-00.md").write_text(
        "# Old source\n\n[broken](missing.md)\n", encoding="utf-8"
    )
    assert any(
        "missing original-source banner or boundary" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_active_link_must_not_escape_repository(tmp_path: Path) -> None:
    """A relative reference must stay inside the checked repository."""
    _minimal_repo(tmp_path)
    _write(tmp_path, "docs/README.md", "[Escape](../../outside.md)\n")
    assert any(
        "link escapes repository" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_historical_source_preamble_links_are_checked(tmp_path: Path) -> None:
    """A historical warning banner cannot hide broken active navigation."""
    source_dir = _minimal_repo(tmp_path)
    original = (source_dir / "source-00.md").read_text(encoding="utf-8")
    (source_dir / "source-00.md").write_text(
        "[Wrong current link](../../not-a-document.md)\n" + original,
        encoding="utf-8",
    )
    assert any(
        "missing link target" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_archived_original_body_links_are_not_current(tmp_path: Path) -> None:
    """Archived reports can quote links removed from current code."""
    _minimal_repo(tmp_path)
    _write(
        tmp_path,
        "docs/archive/obsolete.md",
        "[Old source](../../previous-system/does-not-exist.md)\n",
    )
    assert find_documentation_issues(tmp_path) == []


def test_same_page_heading_links_are_checked(tmp_path: Path) -> None:
    """Local fragments must resolve against the current Markdown file."""
    _minimal_repo(tmp_path)
    _write(
        tmp_path,
        "docs/README.md",
        "# Beispielüberschrift\n\n[Correct](#beispielüberschrift)\n",
    )
    assert find_documentation_issues(tmp_path) == []

    _write(
        tmp_path,
        "docs/README.md",
        "# Beispielüberschrift\n\n[Wrong](#nicht-vorhanden)\n",
    )
    assert any(
        "missing heading: #nicht-vorhanden" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_historical_august_mvp_original_links_are_ignored(
    tmp_path: Path,
) -> None:
    """Only the current preface of the old August MVP is active navigation."""
    _minimal_repo(tmp_path)
    _write(
        tmp_path,
        "docs/character-chronicles/history/full-mvp-draft-2026-08.md",
        "# Earlier MVP\n\n"
        "**Dokumentklasse:** `HISTORICAL_EVIDENCE`\n\n"
        "[Current navigation](../../README.md)\n\n"
        "Status: Konzeptentwurf\n"
        "[Old missing target](../../historic/missing.md)\n",
    )
    assert find_documentation_issues(tmp_path) == []


def test_historical_august_mvp_current_preface_links_are_checked(
    tmp_path: Path,
) -> None:
    """The exclusion must not conceal broken links in the modern preface."""
    _minimal_repo(tmp_path)
    _write(
        tmp_path,
        "docs/character-chronicles/history/full-mvp-draft-2026-08.md",
        "# Earlier MVP\n\n"
        "**Dokumentklasse:** `HISTORICAL_EVIDENCE`\n\n"
        "[Broken current link](../../missing-current.md)\n\n"
        "Status: Konzeptentwurf\n"
        "[Old missing target](../../historic/missing.md)\n",
    )
    assert any(
        "missing link target: ../../missing-current.md" in issue
        for issue in find_documentation_issues(tmp_path)
    )


def test_historical_august_mvp_original_boundary_must_exist(
    tmp_path: Path,
) -> None:
    """Fail explicitly if the known historical body boundary is lost."""
    _minimal_repo(tmp_path)
    _write(
        tmp_path,
        "docs/character-chronicles/history/full-mvp-draft-2026-08.md",
        "# Earlier MVP\n\n"
        "**Dokumentklasse:** `HISTORICAL_EVIDENCE`\n\n"
        "[Old link](../../historic/missing.md)\n",
    )
    assert any(
        "missing historical MVP preface or original boundary" in issue
        for issue in find_documentation_issues(tmp_path)
    )


# Git blob OIDs at 76d71f9 (prior to the documentation reorganization).
# These verify historical provenance, not modern implementation authority.
SOURCE_ORIGINAL_GIT_BLOBS = {
    "baseline-and-entry-gates.md": "871f47cdef3d2844c0156528bd3223961c85ab18",
    "card-art-composition-and-rendering.md": "7f780a7281a13a6052e9bb029dc162cafbad5901",
    "card-battler-board-and-combat-foundation.md": (
        "0a25542d81cc91500e52822ab1e1e943e1ebd4c3"
    ),
    "card-battler-decks-turns-and-actions.md": (
        "37176ee031bab45b63d596fa4b981760a3e98b05"
    ),
    "card-battler-effect-grammar-and-llm-authoring.md": (
        "5c72b3961e5f358ed28a871f1b0edc70ea1a1a05"
    ),
    "card-battler-runtime-architecture.md": "553fa5e3b7f0c6e92a4d32d3c42a22c2b9245170",
    "card-battler-zones-statuses-and-opcode-registry.md": (
        "b6b9d9dd5e1d934df3ae78f58fbdad1a22ba082a"
    ),
    "card-crafting-and-playground-combination-lifecycle.md": (
        "47c407220619df0f035db49657e47767719a8861"
    ),
    "champion-slots-and-character-decks.md": "79dd8895b8d7dd7a2430eecabc7c498e5030bb01",
    "deck-building-embeddings-and-llm-context.md": (
        "d5ac12627a4188c6c760ecfd7f1bae8c447e84c6"
    ),
    "frontend-information-architecture.md": "37e42f291e7c9cd1abbac84ddce47eb2787a0131",
    "game-modes-and-guided-evidence.md": "60bde8223388d1f47da13567ad26eacf1527f7a2",
    "generation-profiles-and-trials.md": "f680618304d071d16c986b573e44122dbecc143c",
    "llm-rag-and-recovery.md": "3f079dd1c096fe1e07ba08c42fd683eb9dcda077",
    "network-first-vn-frontend-screen-map.md": (
        "e69bbacf2104dec1c3b7e2bf1932c76b33b1751c"
    ),
    "orchestration-guardian-and-monitoring.md": (
        "a913e24cb200aedd0c20274537f1064dc324c73b"
    ),
    "player-facing-terminology-and-voice.md": (
        "895a42c301f7964f762ccdbecaccb936a5f983f2"
    ),
    "rolling-m6-learning-loop.md": "4899454a3912670a5b0a1646d0acd1ea9e22f13d",
    "school-year-visual-portfolios-and-relationship-contexts.md": (
        "f39de95f079c7ddb96d2d44ef4d278614556d10f"
    ),
    "story-cast-and-simulation.md": "e23e721aa9c1572cd227f5cf0661b3dd363c5051",
    "target-architecture.md": "fe7d627763d6366f04b71182c6c313edd22c0ed5",
    "visual-assets-quests-and-gates.md": "ea78c3e800cab9aa95453207b103589b5859d7b3",
    "vn-social-platform-and-card-loop-concept.md": (
        "0bb64ecbd04076b84d29a28e233a4adb32ad32dd"
    ),
    "year-end-lora-and-new-game-plus.md": "614affcf342e85f9b88a61d4ee37cfd34dc27d99",
}

ARCHIVED_ORIGINAL_GIT_BLOBS = {
    "docs/archive/card-battler-target-2026-10-02.md": (
        "<!-- HISTORICAL_ORIGINAL_BODY_START -->\n",
        "cb9df89c9207f9be2877bd4b7cfb94fb79ad33ee",
    ),
    "docs/archive/project-status-log-2026-10-09.md": (
        "## Überlieferte detaillierte Statusfassung\n\n",
        "bc57369a15c7ed8de69c60eb5abe81ecd5dbef24",
    ),
    "docs/archive/refactor-slice-history-2026-10-09.md": (
        "## Vollständiger alter Refactor-Slice-Verlauf\n\n",
        "c74342ae7a00551d64e657962f9b5e6ad5b21f47",
    ),
    "docs/archive/root-readme-full-2026-10-09.md": (
        "## Originale ausführliche README-Fassung\n\n",
        "48b6cc8787f77029edbdbb7a5dca34368142f9fb",
    ),
    "docs/character-chronicles/history/full-mvp-draft-2026-08.md": (
        "<!-- HISTORICAL_ORIGINAL_BODY_START -->\n",
        "146374a0be6efee73e46e7e0b0ed10c4d8613c25",
    ),
}


def _git_blob_oid(body: bytes) -> str:
    """Compute the original Git SHA-1 object ID; not a security hash."""
    return hashlib.sha1(
        f"blob {len(body)}\0".encode("ascii") + body,
        usedforsecurity=False,
    ).hexdigest()


def test_imported_historical_source_bodies_preserve_original_blobs() -> None:
    """A revised warning may not silently change any of the 24 sources."""
    source_dir = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "character-chronicles"
        / "sources"
    )
    actual_names = {
        path.name
        for path in source_dir.glob("*.md")
        if path.name not in {"README.md", "SOURCE_RELATIONSHIP.md"}
    }
    assert actual_names == set(SOURCE_ORIGINAL_GIT_BLOBS)

    for filename, expected_oid in SOURCE_ORIGINAL_GIT_BLOBS.items():
        data = (source_dir / filename).read_bytes()
        heading, sep, _ = data.partition(b"\n")
        assert sep and heading.startswith(b"# "), filename
        _, boundary, tagged_body = data.partition(
            SOURCE_BOUNDARY.encode("utf-8")
        )
        assert boundary, filename
        _, separator, original_tail = tagged_body.partition(b"\n---\n\n")
        assert separator, filename
        original_body = heading + b"\n\n" + original_tail
        assert _git_blob_oid(original_body) == expected_oid, filename


def test_archived_historical_originals_preserve_reference_blobs() -> None:
    """A new archive preface must not rewrite the earlier recorded facts."""
    root = Path(__file__).resolve().parents[1]
    for path, (marker, expected_oid) in ARCHIVED_ORIGINAL_GIT_BLOBS.items():
        data = (root / path).read_bytes()
        _, separator, original_body = data.partition(marker.encode("utf-8"))
        assert separator, path
        assert _git_blob_oid(original_body) == expected_oid, path
