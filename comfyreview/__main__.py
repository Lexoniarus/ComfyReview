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
from comfyreview.importers import (
    LegacyFeatureImportRecoveryError,
    LegacyFeatureImportValidationError,
    LegacyOutputAuditor,
    LegacyOutputImporter,
    LegacyOutputImportRecoveryError,
    LegacyOutputImportValidationError,
    SqliteLegacyFeatureMigration,
)
from comfyreview.providers import LocalLegacyOutputImportSource
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
    LegacySchemaManager,
)
from comfyreview.repositories.sqlite.legacy_output_import import (
    SqliteLegacyOutputImportRepository,
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

    legacy_output = commands.add_parser("legacy-output")
    output_actions = legacy_output.add_subparsers(
        dest="action",
        required=True,
    )
    output_audit = output_actions.add_parser("audit")
    output_audit.add_argument("--output-root", type=Path)
    output_audit.add_argument("--database", type=Path)
    output_audit.add_argument("--report", type=Path)
    output_import = output_actions.add_parser("import")
    output_import.add_argument("--report", type=Path)
    output_import.add_argument("--backup-dir", type=Path)

    legacy_features = commands.add_parser("legacy-features")
    feature_actions = legacy_features.add_subparsers(
        dest="action",
        required=True,
    )
    feature_audit = feature_actions.add_parser("audit")
    feature_audit.add_argument("--report", type=Path)
    feature_import = feature_actions.add_parser("import")
    feature_import.add_argument("--report", type=Path)
    feature_import.add_argument("--backup-dir", type=Path)
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


def _run_legacy_output(options: argparse.Namespace) -> int:
    settings = load_settings()
    if options.action == "import":
        return _run_legacy_output_import(options)
    output_root = (
        options.output_root
        if options.output_root is not None
        else settings.output_root
    )
    database_path = (
        options.database
        if options.database is not None
        else settings.canonical_database_path
    )
    report_path = (
        options.report
        if options.report is not None
        else settings.data_directory / "reports" / "legacy-output-audit.json"
    )
    result = LegacyOutputAuditor(
        output_root=output_root,
        canonical_database_path=database_path,
    ).audit(report_path)
    payload = {
        "report_path": str(result.report_path),
        **result.summary,
        "conflict_fields": result.conflict_fields,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


class _CliImportObserver:
    def backup_created(self, backup_path: Path) -> None:
        payload = {
            "event": "legacy_output_import.backup_created",
            "backup_path": str(backup_path),
        }
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)


class _CliFeatureImportObserver:
    def backup_created(self, backup_path: Path) -> None:
        payload = {
            "event": "legacy_feature_import.backup_created",
            "backup_path": str(backup_path),
        }
        print(json.dumps(payload, sort_keys=True), file=sys.stderr)


def _run_legacy_output_import(options: argparse.Namespace) -> int:
    settings = load_settings()
    report_path = (
        options.report
        if options.report is not None
        else settings.data_directory / "reports" / "legacy-output-audit.json"
    )
    database_path = settings.canonical_database_path
    repository = SqliteLegacyOutputImportRepository(database_path)
    result = LegacyOutputImporter(
        schema=CanonicalSchemaManager(database_path),
        source=LocalLegacyOutputImportSource(database_path),
        repository=repository,
        observer=_CliImportObserver(),
    ).import_audit(
        report_path,
        backup_directory=options.backup_dir,
    )
    payload = {
        "backup_path": str(result.backup_path),
        "new_images": result.new_images,
        "enriched_images": result.enriched_images,
        "new_generations": result.new_generations,
        "sampler_stages": result.sampler_stages,
        "excluded_without_sidecar": result.excluded_without_sidecar,
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


def _run_legacy_features(options: argparse.Namespace) -> int:
    settings = load_settings()
    report_path = (
        options.report
        if options.report is not None
        else settings.data_directory / "reports" / "legacy-feature-audit.json"
    )
    migration = SqliteLegacyFeatureMigration(
        canonical_database_path=settings.canonical_database_path,
        ratings_database_path=settings.ratings_database_path,
        arena_database_path=settings.arena_database_path,
        curation_database_path=settings.curation_database_path,
        images_projection_database_path=settings.images_database_path,
        observer=_CliFeatureImportObserver(),
    )
    if options.action == "audit":
        audit_result = migration.audit(report_path)
        print(
            json.dumps(
                {
                    "report_path": str(audit_result.report_path),
                    **audit_result.summary,
                },
                sort_keys=True,
            )
        )
        return 2 if audit_result.summary["conflicts"] else 0
    import_result = migration.import_audit(
        report_path,
        backup_directory=options.backup_dir,
    )
    print(
        json.dumps(
            {
                "backup_path": str(import_result.backup_path),
                "rating_events": import_result.rating_events,
                "deduplicated_ratings": (import_result.deduplicated_ratings),
                "arena_matches": import_result.arena_matches,
                "curation_assignments": import_result.curation_assignments,
                "orphan_ratings": import_result.orphan_ratings,
                "orphan_arena_matches": (import_result.orphan_arena_matches),
                "orphan_curation_assignments": (
                    import_result.orphan_curation_assignments
                ),
            },
            sort_keys=True,
        )
    )
    return 0


def main(arguments: list[str] | None = None) -> int:
    """Run a maintenance command and return its stable process exit code."""
    options = _parser().parse_args(arguments)
    try:
        if options.command == "legacy-db":
            return _run_legacy(options)
        if options.command == "canonical-db":
            return _run_canonical(options)
        if options.command == "legacy-features":
            return _run_legacy_features(options)
        return _run_legacy_output(options)
    except LegacySchemaValidationError as error:
        print(_render_legacy(error.report), file=sys.stderr)
        return 2
    except CanonicalSchemaValidationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except LegacyOutputImportValidationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except LegacyOutputImportRecoveryError as error:
        print(str(error), file=sys.stderr)
        return 1
    except LegacyFeatureImportValidationError as error:
        print(str(error), file=sys.stderr)
        return 2
    except LegacyFeatureImportRecoveryError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, sqlite3.DatabaseError, ValueError) as error:
        print(f"database operation failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
