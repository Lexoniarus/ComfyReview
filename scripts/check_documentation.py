"""Validate active documentation links while preserving historical sources."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
SOURCE_INDEX_FILES = {"README.md", "SOURCE_RELATIONSHIP.md"}
SOURCE_BOUNDARY = "## Übernommene Quellenfassung"
SOURCE_BANNER = "SOURCE_MATERIAL – NICHT VERBINDLICH"
HISTORICAL_MVP_PATH = Path(
    "docs/character-chronicles/history/full-mvp-draft-2026-08.md"
)
HISTORICAL_MVP_BODY_START = "\nStatus: Konzeptentwurf"
LINK_PATTERN = re.compile(r"!?\[[^\]]+\]\((?P<target><[^>]+>|[^)\n]+)\)")
HEADING_PATTERN = re.compile(r"^#{1,6}\s+(.+?)\s*$")
REQUIRED_FILES = (
    "README.md",
    "AGENTS.md",
    "docs/README.md",
    "docs/DECISION_POLICY.md",
    "docs/CONFIRMED_CONSTRAINTS.md",
    "docs/DECISION_POC_RECONCILIATION.md",
    "docs/OPEN_DECISIONS.md",
    "docs/DOCUMENTATION_GUIDE.md",
    "docs/PROJECT_EVOLUTION.md",
    "docs/pocs/card-battler.md",
    "docs/character-chronicles/vision/README.md",
)


def _visible_source_text(path: Path, root: Path, content: str) -> str:
    """Return navigational Markdown, omitting archived original bodies."""
    docs = root / "docs"
    source_dir = docs / "character-chronicles" / "sources"
    archive_dir = docs / "archive"
    if path.is_relative_to(archive_dir) and path.name != "README.md":
        return ""
    if path.parent == source_dir and path.name not in SOURCE_INDEX_FILES:
        return content.split(SOURCE_BOUNDARY, 1)[0]
    if path == root / HISTORICAL_MVP_PATH:
        return content.split(HISTORICAL_MVP_BODY_START, 1)[0]
    return content


def _headings(path: Path) -> set[str]:
    """Approximate GitHub's Unicode-preserving heading anchors."""
    identifiers: set[str] = set()
    repeated: dict[str, int] = {}
    fenced = False
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.lstrip().startswith((chr(96) * 3, "~~~")):
            fenced = not fenced
            continue
        if fenced:
            continue
        match = HEADING_PATTERN.match(line)
        if match is None:
            continue
        heading = re.sub(r"<[^>]*>", "", match.group(1))
        heading = re.sub(r"[*_~]", "", heading).replace(chr(96), "").lower()
        slug = re.sub(r"[^\w -]", "", heading).strip()
        slug = slug.replace(" ", "-")
        suffix = repeated.get(slug, 0)
        repeated[slug] = suffix + 1
        identifiers.add(f"{slug}-{suffix}" if suffix else slug)
    return identifiers


def find_documentation_issues(root: Path = ROOT) -> list[str]:
    """Report missing current links, headings and archive source boundaries."""
    root = root.resolve()
    docs = root / "docs"
    source_dir = docs / "character-chronicles" / "sources"
    issues: list[str] = []
    for name in REQUIRED_FILES:
        if not (root / name).is_file():
            issues.append(f"missing current document: {name}")

    source_files = sorted(
        path
        for path in source_dir.glob("*.md")
        if path.name not in SOURCE_INDEX_FILES
    )
    if len(source_files) != 24:
        issues.append(
            f"expected 24 original sources, found {len(source_files)}"
        )
    for source in source_files:
        content = source.read_text(encoding="utf-8")
        header, sep, _ = content.partition(SOURCE_BOUNDARY)
        if SOURCE_BANNER not in header or not sep:
            issues.append(
                f"missing original-source banner or boundary: "
                f"{source.relative_to(root)}"
            )

    historical_mvp = root / HISTORICAL_MVP_PATH
    if historical_mvp.is_file():
        historical_text = historical_mvp.read_text(encoding="utf-8")
        preface, boundary, _ = historical_text.partition(
            HISTORICAL_MVP_BODY_START
        )
        if not boundary or "`HISTORICAL_EVIDENCE`" not in preface:
            issues.append(
                "missing historical MVP preface or original boundary: "
                f"{historical_mvp.relative_to(root)}"
            )

    files = sorted((*root.glob("*.md"), *docs.rglob("*.md")))
    heading_cache: dict[Path, set[str]] = {}
    for source in files:
        content = _visible_source_text(
            source, root, source.read_text(encoding="utf-8")
        )
        fenced = False
        for line_no, line in enumerate(content.splitlines(), start=1):
            if line.lstrip().startswith((chr(96) * 3, "~~~")):
                fenced = not fenced
                continue
            if fenced:
                continue
            for match in LINK_PATTERN.finditer(line):
                raw = match.group("target").strip()
                if raw.startswith("<"):
                    url = raw[1:].split(">", 1)[0]
                else:
                    url = raw.split(maxsplit=1)[0]
                if url.lower().startswith(
                    ("https:", "http:", "mailto:", "tel:", "data:")
                ):
                    continue
                destination, _, fragment = url.partition("#")
                destination = unquote(destination.split("?", 1)[0])
                target = (
                    source
                    if not destination
                    else (source.parent / destination).resolve()
                )
                location = f"{source.relative_to(root)}:{line_no}"
                if not target.is_relative_to(root):
                    issues.append(
                        f"{location}: link escapes repository: {url}"
                    )
                elif not target.exists():
                    issues.append(f"{location}: missing link target: {url}")
                elif fragment and target.suffix.lower() == ".md":
                    if target not in heading_cache:
                        heading_cache[target] = _headings(target)
                    headings = heading_cache[target]
                    if unquote(fragment) not in headings:
                        issues.append(f"{location}: missing heading: {url}")
    return issues


def main() -> int:
    """Return a nonzero exit on invalid active links or source boundaries."""
    issues = find_documentation_issues()
    for issue in issues:
        print(f"documentation error: {issue}")
    if issues:
        return 1
    print("documentation check passed: current links and source boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
