"""Regression tests for active Markdown and immutable historical references."""

from __future__ import annotations

from pathlib import Path

from scripts.check_documentation import (
    REQUIRED_FILES,
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
