"""Run the repository quality gate and enforce its legacy ratchet."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LEGACY_FILES_PATH = ROOT / "quality" / "legacy_python_files.txt"
BASELINE_PATH = ROOT / "quality" / "legacy_diagnostics.json"
DEFAULT_BASE_REF = "origin/master"


class QualityError(RuntimeError):
    """Represent a quality-gate configuration or execution failure."""


@dataclass(frozen=True)
class CommandResult:
    """Contain the captured result of one quality command."""

    return_code: int
    stdout: str
    stderr: str


def run_command(arguments: Sequence[str]) -> CommandResult:
    """Run a command from the repository root without invoking a shell."""
    completed = subprocess.run(
        list(arguments),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return CommandResult(
        return_code=completed.returncode,
        stdout=completed.stdout,
        stderr=completed.stderr,
    )


def require_tool_result(name: str, result: CommandResult) -> None:
    """Reject tool failures that are not ordinary diagnostic exits."""
    if result.return_code in {0, 1}:
        return
    details = (result.stderr or result.stdout).strip()
    raise QualityError(f"{name} failed to run: {details}")


def normalize_path(raw_path: str) -> str:
    """Return a stable repository-relative POSIX path."""
    path = Path(raw_path)
    if path.is_absolute():
        path = path.resolve().relative_to(ROOT)
    return path.as_posix()


def read_legacy_files() -> set[str]:
    """Read the current versioned set of legacy Python files."""
    return {
        line.strip()
        for line in LEGACY_FILES_PATH.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def list_current_python_files() -> set[str]:
    """List tracked and untracked non-ignored Python files."""
    tracked = run_command(["git", "ls-files", "--", "*.py"])
    untracked = run_command(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"]
    )
    if tracked.return_code != 0 or untracked.return_code != 0:
        raise QualityError("Git could not enumerate Python files")
    return {
        normalize_path(path)
        for path in (tracked.stdout + untracked.stdout).splitlines()
        if path.strip()
    }


def resolve_base_commit(base_ref: str) -> str:
    """Resolve the common ancestor used for changed-file enforcement."""
    result = run_command(["git", "merge-base", base_ref, "HEAD"])
    if result.return_code != 0 or not result.stdout.strip():
        raise QualityError(f"Cannot resolve quality base ref {base_ref!r}")
    return result.stdout.strip()


def list_python_files_at_revision(revision: str) -> set[str]:
    """List Python files tracked at a Git revision."""
    result = run_command(["git", "ls-tree", "-r", "--name-only", revision])
    if result.return_code != 0:
        raise QualityError(f"Cannot inspect revision {revision!r}")
    return {
        normalize_path(path)
        for path in result.stdout.splitlines()
        if path.strip().endswith(".py")
    }


def read_base_legacy_files(base_ref: str, base_commit: str) -> set[str]:
    """Read the prior legacy set or derive the bootstrap set."""
    result = run_command(
        ["git", "show", f"{base_ref}:quality/legacy_python_files.txt"]
    )
    if result.return_code != 0:
        return list_python_files_at_revision(base_commit)
    return {
        line.strip()
        for line in result.stdout.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }


def validate_legacy_files(
    base_ref: str,
    base_commit: str,
    current_files: set[str],
    legacy_files: set[str],
) -> None:
    """Ensure the legacy set only shrinks and contains existing files."""
    base_legacy_files = read_base_legacy_files(base_ref, base_commit)
    additions = legacy_files - base_legacy_files
    missing = legacy_files - current_files
    errors: list[str] = []
    if additions:
        errors.append("legacy additions: " + ", ".join(sorted(additions)))
    if missing:
        errors.append("deleted legacy entries: " + ", ".join(sorted(missing)))
    if errors:
        raise QualityError("; ".join(errors))


def list_changed_python_files(base_commit: str) -> set[str]:
    """List Python files changed since the quality base, including untracked."""
    changed = run_command(
        [
            "git",
            "diff",
            "--name-only",
            "--diff-filter=ACMRT",
            base_commit,
            "--",
            "*.py",
        ]
    )
    untracked = run_command(
        ["git", "ls-files", "--others", "--exclude-standard", "--", "*.py"]
    )
    if changed.return_code != 0 or untracked.return_code != 0:
        raise QualityError("Git could not enumerate changed Python files")
    return {
        normalize_path(path)
        for path in (changed.stdout + untracked.stdout).splitlines()
        if path.strip()
    }


def diagnostic_key(tool: str, path: str, rule: str) -> str:
    """Build the stable key used by the diagnostic baseline."""
    return f"{tool}|{normalize_path(path)}|{rule or 'unknown'}"


def collect_ruff(files: Sequence[str]) -> Counter[str]:
    """Collect Ruff lint diagnostics grouped by file and rule."""
    result = run_command(
        [sys.executable, "-m", "ruff", "check", "--output-format=json", *files]
    )
    require_tool_result("Ruff lint", result)
    payload = json.loads(result.stdout or "[]")
    return Counter(
        diagnostic_key("ruff", item["filename"], item["code"])
        for item in payload
    )


def collect_ruff_format(files: Sequence[str]) -> Counter[str]:
    """Collect files that do not conform to Ruff formatting."""
    result = run_command(
        [
            sys.executable,
            "-m",
            "ruff",
            "format",
            "--check",
            "--output-format=json",
            *files,
        ]
    )
    require_tool_result("Ruff format", result)
    payload = json.loads(result.stdout or "[]")
    return Counter(
        diagnostic_key("format", item["filename"], "unformatted")
        for item in payload
    )


def collect_mypy(files: Sequence[str]) -> Counter[str]:
    """Collect mypy diagnostics grouped by file and error code."""
    result = run_command(
        [sys.executable, "-m", "mypy", "--output", "json", *files]
    )
    require_tool_result("mypy", result)
    diagnostics: Counter[str] = Counter()
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        diagnostics[
            diagnostic_key(
                "mypy",
                item["file"],
                item.get("code") or item.get("severity", "unknown"),
            )
        ] += 1
    return diagnostics


def collect_pyright(files: Sequence[str]) -> Counter[str]:
    """Collect Pyright diagnostics grouped by file and rule."""
    result = run_command(
        [sys.executable, "-m", "pyright", "--outputjson", *files]
    )
    require_tool_result("Pyright", result)
    payload = json.loads(result.stdout)
    return Counter(
        diagnostic_key(
            "pyright",
            item["file"],
            item.get("rule") or item.get("severity", "unknown"),
        )
        for item in payload.get("generalDiagnostics", [])
    )


def collect_diagnostics(files: Iterable[str]) -> dict[str, Counter[str]]:
    """Run all static tools and return their normalized diagnostics."""
    ordered_files = sorted(files)
    return {
        "ruff": collect_ruff(ordered_files),
        "format": collect_ruff_format(ordered_files),
        "mypy": collect_mypy(ordered_files),
        "pyright": collect_pyright(ordered_files),
    }


def filter_legacy_diagnostics(
    diagnostics: dict[str, Counter[str]], legacy_files: set[str]
) -> dict[str, Counter[str]]:
    """Keep only diagnostics that belong to versioned legacy files."""
    filtered: dict[str, Counter[str]] = {}
    for tool, counts in diagnostics.items():
        filtered[tool] = Counter(
            {
                key: count
                for key, count in counts.items()
                if key.split("|", 2)[1] in legacy_files
            }
        )
    return filtered


def load_baseline() -> dict[str, Any]:
    """Load and validate the versioned diagnostics baseline."""
    payload: Any = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise QualityError("Unsupported quality baseline schema")
    if not isinstance(payload.get("tools"), dict):
        raise QualityError("Quality baseline has no tool diagnostics")
    return payload


def _load_base_baseline(base_ref: str) -> dict[str, Any] | None:
    result = run_command(
        ["git", "show", f"{base_ref}:quality/legacy_diagnostics.json"]
    )
    if result.return_code != 0:
        return None
    payload: Any = json.loads(result.stdout)
    if not isinstance(payload, dict) or not isinstance(
        payload.get("tools"), dict
    ):
        raise QualityError("Base quality baseline is invalid")
    return payload


def _find_baseline_growth(
    current: dict[str, Any], previous: dict[str, Any]
) -> list[str]:
    growth: list[str] = []
    previous_tools = previous["tools"]
    for tool, counts in current["tools"].items():
        prior_counts = previous_tools.get(tool, {})
        for key, count in counts.items():
            prior_count = int(prior_counts.get(key, 0))
            if int(count) > prior_count:
                growth.append(f"{key}: {count} > {prior_count}")
    return sorted(growth)


def _validate_baseline_does_not_grow(
    base_ref: str,
    baseline: dict[str, Any],
) -> None:
    """Reject baseline additions after the initial foundation bootstrap."""
    previous = _load_base_baseline(base_ref)
    if previous is None:
        return
    growth = _find_baseline_growth(baseline, previous)
    if growth:
        raise QualityError("Diagnostic baseline grew:\n" + "\n".join(growth))


def compare_baseline(
    current: dict[str, Counter[str]], baseline: dict[str, Any]
) -> None:
    """Reject diagnostic groups that are new or exceed their baseline."""
    failures: list[str] = []
    baseline_tools = baseline["tools"]
    for tool, counts in current.items():
        allowed_counts = baseline_tools.get(tool, {})
        for key, count in sorted(counts.items()):
            allowed = int(allowed_counts.get(key, 0))
            if count > allowed:
                failures.append(f"{key}: {count} > {allowed}")
    if failures:
        raise QualityError(
            "Legacy diagnostics worsened:\n" + "\n".join(failures)
        )


def validate_strict_files(
    diagnostics: dict[str, Counter[str]], strict_files: set[str]
) -> None:
    """Require every new, changed, or migrated file to be fully clean."""
    failures = sorted(
        f"{key}: {count}"
        for counts in diagnostics.values()
        for key, count in counts.items()
        if key.split("|", 2)[1] in strict_files
    )
    if failures:
        raise QualityError("Strict-file diagnostics:\n" + "\n".join(failures))


def render_baseline(
    base_commit: str,
    diagnostics: dict[str, Counter[str]],
    legacy_files: set[str],
) -> str:
    """Render a deterministic baseline document for explicit review."""
    legacy_diagnostics = filter_legacy_diagnostics(diagnostics, legacy_files)
    payload = {
        "base_commit": base_commit,
        "schema_version": 1,
        "tools": {
            tool: dict(sorted(counts.items()))
            for tool, counts in sorted(legacy_diagnostics.items())
        },
    }
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def run_pytest() -> None:
    """Run the complete Python regression suite with scoped core coverage."""
    scope_path = ROOT / "quality" / "core_scope.txt"
    coverage_sources: list[str] = []
    for raw_line in scope_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        candidate = ROOT / line
        if candidate.is_file():
            coverage_sources.append(line.removesuffix(".py").replace("/", "."))
        elif candidate.is_dir():
            coverage_sources.append(line.replace("/", "."))
    erase_result = run_command([sys.executable, "-m", "coverage", "erase"])
    if erase_result.return_code != 0:
        raise QualityError("coverage could not remove its prior data")
    source_argument = ",".join(coverage_sources)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "run",
            f"--source={source_argument}",
            "-m",
            "pytest",
        ],
        cwd=ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise QualityError("pytest failed")
    report_result = subprocess.run(
        [sys.executable, "-m", "coverage", "report", "--fail-under=100"],
        cwd=ROOT,
        check=False,
    )
    if report_result.returncode != 0:
        raise QualityError("Python-core coverage is below 100%")


def parse_arguments() -> argparse.Namespace:
    """Parse quality-gate command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--base-ref",
        default=os.environ.get("QUALITY_BASE_REF", DEFAULT_BASE_REF),
        help="Git ref used to identify changed files",
    )
    parser.add_argument(
        "--print-baseline",
        action="store_true",
        help="print measured legacy diagnostics without changing files",
    )
    return parser.parse_args()


def main() -> int:
    """Run the quality gate and return a process exit code."""
    arguments = parse_arguments()
    try:
        current_files = list_current_python_files()
        legacy_files = read_legacy_files()
        base_commit = resolve_base_commit(arguments.base_ref)
        validate_legacy_files(
            arguments.base_ref,
            base_commit,
            current_files,
            legacy_files,
        )
        diagnostics = collect_diagnostics(current_files)
        if arguments.print_baseline:
            print(
                render_baseline(base_commit, diagnostics, legacy_files), end=""
            )
            return 0
        baseline = load_baseline()
        _validate_baseline_does_not_grow(arguments.base_ref, baseline)
        compare_baseline(
            filter_legacy_diagnostics(diagnostics, legacy_files),
            baseline,
        )
        strict_files = (
            current_files - legacy_files
        ) | list_changed_python_files(base_commit)
        validate_strict_files(diagnostics, strict_files)
        run_pytest()
    except (OSError, ValueError, QualityError, json.JSONDecodeError) as error:
        print(f"quality gate failed: {error}", file=sys.stderr)
        return 1
    print("quality gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
