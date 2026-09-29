"""Command-line entry point for explicit ComfyReview maintenance."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from comfyreview.application import (
    LegacySchemaReport,
    LegacySchemaValidationError,
)
from comfyreview.repositories.sqlite import LegacySchemaManager
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
    actions = legacy.add_subparsers(dest="action", required=True)
    for action_name in ("validate", "upgrade"):
        action = actions.add_parser(action_name)
        action.add_argument(
            "--database",
            action="append",
            choices=_DATABASE_NAMES,
            dest="databases",
        )
        if action_name == "upgrade":
            action.add_argument("--backup-dir", type=Path)
    return parser


def _render(report: LegacySchemaReport) -> str:
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


def main(arguments: list[str] | None = None) -> int:
    """Run a maintenance command and return its stable process exit code."""
    options = _parser().parse_args(arguments)
    manager = LegacySchemaManager(load_settings())
    try:
        if options.action == "validate":
            report = manager.validate(options.databases)
        else:
            report = manager.upgrade(
                options.databases,
                options.backup_dir,
            )
        print(_render(report))
        return 2 if report.issues else 0
    except LegacySchemaValidationError as error:
        print(_render(error.report), file=sys.stderr)
        return 2
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        print(f"legacy database operation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
