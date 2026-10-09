"""Validate active documentation links and historical archive boundaries.

Archived source documents retain their original, sometimes dangling hyperlinks.
Their indexes are checked; archived source bodies are deliberately excluded.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
ARCHIVE = DOCS / "archive"
CHRONICLE = ARCHIVE / "character-chronicles-v1"
LINK_PATTERN = re.compile(r"!?(?:\[[^\]]+\])\((?P<target>[^\s)]+)")
EXTERNAL_PREFIXES = ("https:", "http:", "mailto:", "tel:", "data:")

REQUIRED_DOCUMENTS = (
    "docs/README.md",
    "docs/ROADMAP.md",
    "docs/DECISIONS.md",
    "docs/POC_REGISTER.md",
    "docs/CARD_BATTLER_TARGET.md",
    "docs/archive/README.md",
    "docs/archive/character-chronicles-v1/README.md",
    "docs/archive/comfyreview-legacy/README.md",
    "docs/future/README.md",
    "docs/future/timeline/README.md",
    "docs/future/social-chat/README.md",
    "docs/future/storyline/README.md",
    "docs/future/vn-content/README.md",
)


def is_archived_source(path: Path) -> bool:
    """Exclude unchanged historical bodies, but check navigational indexes."""
    return path.is_relative_to(ARCHIVE) and path.name != "README.md"


def find_documentation_issues() -> list[str]:
    """Find missing active links and incomplete archive boundaries."""
    issues: list[str] = []
    for relative in REQUIRED_DOCUMENTS:
        if not (ROOT / relative).is_file():
            issues.append(f"missing documentation entrypoint: {relative}")

    if (DOCS / "Concepts").exists():
        issues.append("unarchived source still exists: docs/Concepts")

    source_files = sorted((CHRONICLE / "product").glob("*.md"))
    if len(source_files) != 24:
        issues.append(
            "expected 24 archived Chronicle product files, "
            f"found {len(source_files)}"
        )
    source_files.append(CHRONICLE / "historical-concept.md")
    for path in source_files:
        if not path.is_file():
            issues.append(f"missing archived source: {path.relative_to(ROOT)}")
        elif not path.read_text(encoding="utf-8").startswith("> [!CAUTION]"):
            issues.append(f"missing archive banner: {path.relative_to(ROOT)}")

    legacy_readme = ARCHIVE / "comfyreview-legacy" / "Readme Comfy Review.txt"
    if not legacy_readme.is_file():
        issues.append("missing archived legacy ComfyReview README")
    elif not legacy_readme.read_text(encoding="utf-8").startswith(
        "ARCHIVIERT"
    ):
        issues.append("missing old README archive marker")

    active_files = set(ROOT.glob("*.md")) | set(DOCS.rglob("*.md"))
    for source in sorted(active_files):
        if is_archived_source(source):
            continue
        content = source.read_text(encoding="utf-8")
        for match in LINK_PATTERN.finditer(content):
            target = match.group("target").strip("<>")
            if target.startswith(("#", *EXTERNAL_PREFIXES)):
                continue
            local_part = unquote(target.split("#", 1)[0].split("?", 1)[0])
            if not local_part:
                continue
            linked = (source.parent / local_part).resolve()
            line = content.count("\n", 0, match.start()) + 1
            if not linked.is_relative_to(ROOT) or not linked.exists():
                issues.append(
                    f"{source.relative_to(ROOT)}:{line}: broken link {target}"
                )

    return issues


def main() -> int:
    """Print concise link/archive validation results for CI or local use."""
    issues = find_documentation_issues()
    if issues:
        for issue in issues:
            print(f"documentation error: {issue}")
        return 1
    print("documentation check passed: active links and archive boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
