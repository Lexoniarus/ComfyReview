"""Command-line entry point for explicit ComfyReview maintenance."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from comfyreview.application import (
    CanonicalSchemaReport,
    LegacySchemaReport,
    LegacySchemaValidationError,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
    LegacySchemaManager,
)
from comfyreview.settings import load_settings

_DATABASE_NAMES = (
    "ratings",
    "prompt_tokens",
    "arena",
    "curation",
    "playground",
    "combo_prompts",
    "images",
    "prompt_ratings",
    "mv_queue",
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m comfyreview")
    commands = parser.add_subparsers(dest="command", required=True)

    legacy = commands.add_parser("legacy-db")
    legacy_actions = legacy.add_subparsers(dest="action", required=True)
    for action_name in ("validate", "upgrade"):
        action = legacy_actions.add_parser(action_name)
        action.add_argument(
            "--database",
            action="append",
            choices=_DATABASE_NAMES,
            dest="databases",
        )
        if action_name == "upgrade":
            action.add_argument("--backup-dir", type=Path)

    canonical = commands.add_parser("canonical-db")
    canonical_actions = canonical.add_subparsers(
        dest="action",
        required=True,
    )
    canonical_actions.add_parser("validate")
    canonical_upgrade = canonical_actions.add_parser("upgrade")
    canonical_upgrade.add_argument("--backup-dir", type=Path)
    return parser


def _render_legacy(report: LegacySchemaReport) -> str:
    payload = {
        "initialized": list(report.initialized),
        "upgraded": list(report.upgraded),
        "issues": [
            {
                "database": issue.database,
                "code": issue.code,
                "detail": issue.detail,
            }
            for issue in report.issues
        ],
    }
    return json.dumps(payload, sort_keys=True)


def _render_canonical(report: CanonicalSchemaReport) -> str:
    payload = {
        "backup_path": (
            str(report.backup_path) if report.backup_path is not None else None
        ),
        "initialized": report.initialized,
        "schema_version": report.schema_version,
        "upgraded_from": report.upgraded_from,
    }
    return json.dumps(payload, sort_keys=True)


def _run_legacy(options: argparse.Namespace) -> int:
    manager = LegacySchemaManager(load_settings())
    if options.action == "validate":
        report = manager.validate(options.databases)
    else:
        report = manager.upgrade(
            options.databases,
            options.backup_dir,
        )
    print(_render_legacy(report))
    return 2 if report.issues else 0


def _run_canonical(options: argparse.Namespace) -> int:
    settings = load_settings()
    manager = CanonicalSchemaManager(settings.canonical_database_path)
    if options.action == "validate":
        report = manager.validate()
    else:
        report = manager.upgrade(options.backup_dir)
    print(_render_canonical(report))
    return 0


def main(arguments: list[str] | None = None) -> int:
    """Run a maintenance command and return its stable process exit code."""
    options = _parser().parse_args(arguments)
    try:
        if options.command == "legacy-db":
            return _run_legacy(options)
        return _run_canonical(options)
    except LegacySchemaValidationError as error:
        print(_render_legacy(error.report), file=sys.stderr)
        return 2
    except CanonicalSchemaValidationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        print(f"database operation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
