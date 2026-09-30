"""Explicit lifecycle management for the current legacy SQLite schemas."""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Collection, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from comfyreview.application import (
    LegacySchemaIssue,
    LegacySchemaReport,
    LegacySchemaValidationError,
)
from comfyreview.settings import LegacyMigrationSettings


@dataclass(frozen=True)
class _TableDefinition:
    name: str
    create_sql: str
    columns: Mapping[str, str]
    additive_columns: Mapping[str, str]


@dataclass(frozen=True)
class _ObjectDefinition:
    name: str
    create_sql: str


@dataclass(frozen=True)
class _DatabaseDefinition:
    tables: tuple[_TableDefinition, ...]
    indexes: tuple[_ObjectDefinition, ...] = ()
    triggers: tuple[_ObjectDefinition, ...] = ()
    post_upgrade_sql: tuple[str, ...] = ()


@dataclass(frozen=True)
class _DatabaseTarget:
    name: str
    path: Path
    definition: _DatabaseDefinition


def _columns(**columns: str) -> Mapping[str, str]:
    return columns


_RATINGS_TABLE = _TableDefinition(
    name="ratings",
    create_sql="""
        CREATE TABLE IF NOT EXISTS ratings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            png_path TEXT NOT NULL,
            json_path TEXT NOT NULL,
            run INTEGER NOT NULL DEFAULT 1,
            model_branch TEXT NOT NULL,
            checkpoint TEXT NOT NULL,
            combo_key TEXT NOT NULL,
            rating INTEGER,
            deleted INTEGER NOT NULL DEFAULT 0,
            rating_count INTEGER NOT NULL DEFAULT 1,
            steps INTEGER,
            cfg REAL,
            sampler TEXT,
            scheduler TEXT,
            denoise REAL,
            loras_json TEXT DEFAULT '',
            pos_prompt TEXT DEFAULT '',
            neg_prompt TEXT DEFAULT ''
        )
    """,
    columns=_columns(
        id="INTEGER",
        png_path="TEXT",
        json_path="TEXT",
        run="INTEGER",
        model_branch="TEXT",
        checkpoint="TEXT",
        combo_key="TEXT",
        rating="INTEGER",
        deleted="INTEGER",
        rating_count="INTEGER",
        steps="INTEGER",
        cfg="REAL",
        sampler="TEXT",
        scheduler="TEXT",
        denoise="REAL",
        loras_json="TEXT",
        pos_prompt="TEXT",
        neg_prompt="TEXT",
    ),
    additive_columns={
        "steps": "ALTER TABLE ratings ADD COLUMN steps INTEGER",
        "cfg": "ALTER TABLE ratings ADD COLUMN cfg REAL",
        "sampler": "ALTER TABLE ratings ADD COLUMN sampler TEXT",
        "scheduler": "ALTER TABLE ratings ADD COLUMN scheduler TEXT",
        "denoise": "ALTER TABLE ratings ADD COLUMN denoise REAL",
        "loras_json": (
            "ALTER TABLE ratings ADD COLUMN loras_json TEXT DEFAULT ''"
        ),
        "pos_prompt": (
            "ALTER TABLE ratings ADD COLUMN pos_prompt TEXT DEFAULT ''"
        ),
        "neg_prompt": (
            "ALTER TABLE ratings ADD COLUMN neg_prompt TEXT DEFAULT ''"
        ),
    },
)

_TOKENS_TABLE = _TableDefinition(
    name="tokens",
    create_sql="""
        CREATE TABLE IF NOT EXISTS tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            json_path TEXT NOT NULL,
            run INTEGER NOT NULL,
            model_branch TEXT NOT NULL,
            scope TEXT NOT NULL,
            token TEXT NOT NULL,
            rating INTEGER,
            deleted INTEGER NOT NULL DEFAULT 0
        )
    """,
    columns=_columns(
        id="INTEGER",
        json_path="TEXT",
        run="INTEGER",
        model_branch="TEXT",
        scope="TEXT",
        token="TEXT",
        rating="INTEGER",
        deleted="INTEGER",
    ),
    additive_columns={
        "json_path": (
            "ALTER TABLE tokens ADD COLUMN json_path TEXT NOT NULL DEFAULT ''"
        ),
        "run": (
            "ALTER TABLE tokens ADD COLUMN run INTEGER NOT NULL DEFAULT 0"
        ),
    },
)

_ARENA_TABLE = _TableDefinition(
    name="arena_matches",
    create_sql="""
        CREATE TABLE IF NOT EXISTS arena_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            left_json TEXT NOT NULL,
            right_json TEXT NOT NULL,
            winner_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            run INTEGER
        )
    """,
    columns=_columns(
        id="INTEGER",
        left_json="TEXT",
        right_json="TEXT",
        winner_json="TEXT",
        created_at="TEXT",
        run="INTEGER",
    ),
    additive_columns={},
)

_CURATION_TABLE = _TableDefinition(
    name="curation",
    create_sql="""
        CREATE TABLE IF NOT EXISTS curation (
            png_path TEXT PRIMARY KEY,
            set_key TEXT
        )
    """,
    columns=_columns(png_path="TEXT", set_key="TEXT"),
    additive_columns={},
)

_PLAYGROUND_TABLE = _TableDefinition(
    name="playground_items",
    create_sql="""
        CREATE TABLE IF NOT EXISTS playground_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kind TEXT NOT NULL,
            name TEXT NOT NULL,
            key TEXT NOT NULL UNIQUE,
            tags TEXT NOT NULL DEFAULT '',
            pos TEXT NOT NULL DEFAULT '',
            neg TEXT NOT NULL DEFAULT '',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at TEXT NOT NULL DEFAULT (datetime('now'))
        )
    """,
    columns=_columns(
        id="INTEGER",
        kind="TEXT",
        name="TEXT",
        key="TEXT",
        tags="TEXT",
        pos="TEXT",
        neg="TEXT",
        notes="TEXT",
        created_at="TEXT",
        updated_at="TEXT",
    ),
    additive_columns={},
)

_IMAGES_COLUMNS = _columns(
    png_path="TEXT",
    json_path="TEXT",
    avg_rating="REAL",
    runs="INTEGER",
    rating_count="INTEGER",
    last_run="INTEGER",
    model_branch="TEXT",
    checkpoint="TEXT",
    combo_key="TEXT",
    steps="INTEGER",
    cfg="REAL",
    sampler="TEXT",
    scheduler="TEXT",
    denoise="REAL",
    loras_json="TEXT",
    pos_prompt="TEXT",
    neg_prompt="TEXT",
    last_updated="TEXT",
)
_IMAGES_TABLE = _TableDefinition(
    name="images",
    create_sql="""
        CREATE TABLE IF NOT EXISTS images (
            png_path TEXT PRIMARY KEY,
            json_path TEXT,
            avg_rating REAL,
            runs INTEGER NOT NULL,
            rating_count INTEGER,
            last_run INTEGER NOT NULL,
            model_branch TEXT,
            checkpoint TEXT,
            combo_key TEXT,
            steps INTEGER,
            cfg REAL,
            sampler TEXT,
            scheduler TEXT,
            denoise REAL,
            loras_json TEXT,
            pos_prompt TEXT,
            neg_prompt TEXT,
            last_updated TEXT
        )
    """,
    columns=_IMAGES_COLUMNS,
    additive_columns={
        name: f"ALTER TABLE images ADD COLUMN {name} {column_type}"
        for name, column_type in _IMAGES_COLUMNS.items()
        if name != "png_path"
    },
)

_PROMPT_RATINGS_TABLE = _TableDefinition(
    name="prompt_ratings",
    create_sql="""
        CREATE TABLE IF NOT EXISTS prompt_ratings (
            scope TEXT NOT NULL,
            token TEXT NOT NULL,
            model_branch TEXT NOT NULL,
            avg_rating REAL,
            runs INTEGER NOT NULL,
            last_updated TEXT,
            mean_score REAL,
            lb05 REAL,
            PRIMARY KEY(scope, token, model_branch)
        )
    """,
    columns=_columns(
        scope="TEXT",
        token="TEXT",
        model_branch="TEXT",
        avg_rating="REAL",
        runs="INTEGER",
        last_updated="TEXT",
        mean_score="REAL",
        lb05="REAL",
    ),
    additive_columns={
        "mean_score": (
            "ALTER TABLE prompt_ratings ADD COLUMN mean_score REAL"
        ),
        "lb05": "ALTER TABLE prompt_ratings ADD COLUMN lb05 REAL",
    },
)

_COMBO_COLUMNS = _columns(
    combo_key="TEXT",
    combo_size="INTEGER",
    character_id="INTEGER",
    scene_id="INTEGER",
    outfit_id="INTEGER",
    label="TEXT",
    pos_tokens="TEXT",
    neg_tokens="TEXT",
    score="REAL",
    coverage="REAL",
    stability="REAL",
    best_json_path="TEXT",
    best_png_path="TEXT",
    best_avg_rating="REAL",
    best_runs="INTEGER",
    best_hits="INTEGER",
    combo_avg_rating="REAL",
    combo_image_count="INTEGER",
    combo_total_runs="INTEGER",
    combo_pos_avg_rating="REAL",
    combo_pos_runs="INTEGER",
    combo_pos_total_tokens="INTEGER",
    combo_pos_rated_tokens="INTEGER",
    combo_pos_coverage="REAL",
    combo_neg_avg_rating="REAL",
    combo_neg_runs="INTEGER",
    combo_neg_total_tokens="INTEGER",
    combo_neg_rated_tokens="INTEGER",
    combo_neg_coverage="REAL",
    last_updated="TEXT",
)
_COMBO_ADDITIVE_NAMES = {
    "combo_avg_rating",
    "combo_image_count",
    "combo_total_runs",
    "combo_pos_avg_rating",
    "combo_pos_runs",
    "combo_pos_total_tokens",
    "combo_pos_rated_tokens",
    "combo_pos_coverage",
    "combo_neg_avg_rating",
    "combo_neg_runs",
    "combo_neg_total_tokens",
    "combo_neg_rated_tokens",
    "combo_neg_coverage",
}
_COMBO_TABLE = _TableDefinition(
    name="combo_prompts",
    create_sql="""
        CREATE TABLE IF NOT EXISTS combo_prompts (
            combo_key TEXT PRIMARY KEY,
            combo_size INTEGER NOT NULL,
            character_id INTEGER,
            scene_id INTEGER,
            outfit_id INTEGER,
            label TEXT,
            pos_tokens TEXT,
            neg_tokens TEXT,
            score REAL,
            coverage REAL,
            stability REAL,
            best_json_path TEXT,
            best_png_path TEXT,
            best_avg_rating REAL,
            best_runs INTEGER,
            best_hits INTEGER,
            combo_avg_rating REAL,
            combo_image_count INTEGER,
            combo_total_runs INTEGER,
            combo_pos_avg_rating REAL,
            combo_pos_runs INTEGER,
            combo_pos_total_tokens INTEGER,
            combo_pos_rated_tokens INTEGER,
            combo_pos_coverage REAL,
            combo_neg_avg_rating REAL,
            combo_neg_runs INTEGER,
            combo_neg_total_tokens INTEGER,
            combo_neg_rated_tokens INTEGER,
            combo_neg_coverage REAL,
            last_updated TEXT
        )
    """,
    columns=_COMBO_COLUMNS,
    additive_columns={
        name: (
            f"ALTER TABLE combo_prompts ADD COLUMN {name} "
            f"{_COMBO_COLUMNS[name]}"
        )
        for name in _COMBO_ADDITIVE_NAMES
    },
)
_COMBO_IMAGES_TABLE = _TableDefinition(
    name="combo_best_images",
    create_sql="""
        CREATE TABLE IF NOT EXISTS combo_best_images (
            combo_key TEXT NOT NULL,
            rank INTEGER NOT NULL,
            png_path TEXT NOT NULL,
            json_path TEXT,
            avg_rating REAL,
            runs INTEGER,
            PRIMARY KEY(combo_key, rank)
        )
    """,
    columns=_columns(
        combo_key="TEXT",
        rank="INTEGER",
        png_path="TEXT",
        json_path="TEXT",
        avg_rating="REAL",
        runs="INTEGER",
    ),
    additive_columns={},
)

_MV_JOBS_TABLE = _TableDefinition(
    name="mv_jobs",
    create_sql="""
        CREATE TABLE IF NOT EXISTS mv_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_type TEXT NOT NULL,
            created_at TEXT NOT NULL,
            touched_at TEXT,
            status TEXT NOT NULL,
            error TEXT
        )
    """,
    columns=_columns(
        id="INTEGER",
        job_type="TEXT",
        created_at="TEXT",
        touched_at="TEXT",
        status="TEXT",
        error="TEXT",
    ),
    additive_columns={
        "touched_at": "ALTER TABLE mv_jobs ADD COLUMN touched_at TEXT"
    },
)
_MV_STATE_TABLE = _TableDefinition(
    name="mv_state",
    create_sql="""
        CREATE TABLE IF NOT EXISTS mv_state (
            aggregator_name TEXT PRIMARY KEY,
            last_processed_rating_id INTEGER NOT NULL DEFAULT 0,
            last_run_at TEXT,
            last_error TEXT
        )
    """,
    columns=_columns(
        aggregator_name="TEXT",
        last_processed_rating_id="INTEGER",
        last_run_at="TEXT",
        last_error="TEXT",
    ),
    additive_columns={},
)


def _index(name: str, sql: str) -> _ObjectDefinition:
    return _ObjectDefinition(name=name, create_sql=sql)


_DEFINITIONS = {
    "ratings": _DatabaseDefinition(
        tables=(_RATINGS_TABLE,),
        indexes=(
            _index(
                "idx_ratings_json_run",
                "CREATE INDEX IF NOT EXISTS idx_ratings_json_run "
                "ON ratings(json_path, run)",
            ),
            _index(
                "idx_ratings_model",
                "CREATE INDEX IF NOT EXISTS idx_ratings_model "
                "ON ratings(model_branch)",
            ),
            _index(
                "idx_ratings_combo",
                "CREATE INDEX IF NOT EXISTS idx_ratings_combo "
                "ON ratings(model_branch, combo_key)",
            ),
            _index(
                "idx_ratings_deleted",
                "CREATE INDEX IF NOT EXISTS idx_ratings_deleted "
                "ON ratings(deleted)",
            ),
            _index(
                "idx_ratings_rating",
                "CREATE INDEX IF NOT EXISTS idx_ratings_rating "
                "ON ratings(rating)",
            ),
        ),
    ),
    "prompt_tokens": _DatabaseDefinition(
        tables=(_TOKENS_TABLE,),
        indexes=tuple(
            _index(name, sql)
            for name, sql in (
                (
                    "idx_tokens_model",
                    "CREATE INDEX IF NOT EXISTS idx_tokens_model "
                    "ON tokens(model_branch)",
                ),
                (
                    "idx_tokens_scope",
                    "CREATE INDEX IF NOT EXISTS idx_tokens_scope "
                    "ON tokens(scope)",
                ),
                (
                    "idx_tokens_token",
                    "CREATE INDEX IF NOT EXISTS idx_tokens_token "
                    "ON tokens(token)",
                ),
                (
                    "idx_tokens_json",
                    "CREATE INDEX IF NOT EXISTS idx_tokens_json "
                    "ON tokens(json_path)",
                ),
                (
                    "idx_tokens_run",
                    "CREATE INDEX IF NOT EXISTS idx_tokens_run ON tokens(run)",
                ),
            )
        ),
    ),
    "arena": _DatabaseDefinition(
        tables=(_ARENA_TABLE,),
        indexes=(
            _index(
                "ux_arena_left_right",
                "CREATE UNIQUE INDEX IF NOT EXISTS ux_arena_left_right "
                "ON arena_matches(left_json, right_json)",
            ),
        ),
    ),
    "curation": _DatabaseDefinition(tables=(_CURATION_TABLE,)),
    "playground": _DatabaseDefinition(
        tables=(_PLAYGROUND_TABLE,),
        indexes=tuple(
            _index(name, sql)
            for name, sql in (
                (
                    "idx_pg_kind",
                    "CREATE INDEX IF NOT EXISTS idx_pg_kind "
                    "ON playground_items(kind)",
                ),
                (
                    "idx_pg_key",
                    "CREATE INDEX IF NOT EXISTS idx_pg_key "
                    "ON playground_items(key)",
                ),
                (
                    "idx_pg_name",
                    "CREATE INDEX IF NOT EXISTS idx_pg_name "
                    "ON playground_items(name)",
                ),
            )
        ),
        triggers=(
            _ObjectDefinition(
                name="trg_pg_updated",
                create_sql="""
                    CREATE TRIGGER IF NOT EXISTS trg_pg_updated
                    AFTER UPDATE ON playground_items
                    FOR EACH ROW
                    BEGIN
                        UPDATE playground_items
                        SET updated_at = datetime('now')
                        WHERE id = NEW.id;
                    END
                """,
            ),
        ),
    ),
    "images": _DatabaseDefinition(tables=(_IMAGES_TABLE,)),
    "prompt_ratings": _DatabaseDefinition(
        tables=(_PROMPT_RATINGS_TABLE,),
        indexes=tuple(
            _index(name, sql)
            for name, sql in (
                (
                    "idx_pr_scope",
                    "CREATE INDEX IF NOT EXISTS idx_pr_scope "
                    "ON prompt_ratings(scope)",
                ),
                (
                    "idx_pr_token",
                    "CREATE INDEX IF NOT EXISTS idx_pr_token "
                    "ON prompt_ratings(token)",
                ),
                (
                    "idx_pr_model",
                    "CREATE INDEX IF NOT EXISTS idx_pr_model "
                    "ON prompt_ratings(model_branch)",
                ),
            )
        ),
    ),
    "combo_prompts": _DatabaseDefinition(
        tables=(_COMBO_TABLE, _COMBO_IMAGES_TABLE),
        indexes=(
            _index(
                "idx_combo_prompts_size_score",
                "CREATE INDEX IF NOT EXISTS idx_combo_prompts_size_score "
                "ON combo_prompts(combo_size, score DESC)",
            ),
            _index(
                "idx_combo_best_images_combo",
                "CREATE INDEX IF NOT EXISTS idx_combo_best_images_combo "
                "ON combo_best_images(combo_key)",
            ),
        ),
    ),
    "mv_queue": _DatabaseDefinition(
        tables=(_MV_JOBS_TABLE, _MV_STATE_TABLE),
        indexes=(
            _index(
                "idx_mv_jobs_status",
                "CREATE INDEX IF NOT EXISTS idx_mv_jobs_status "
                "ON mv_jobs(status)",
            ),
        ),
        post_upgrade_sql=(
            "UPDATE mv_jobs SET touched_at = created_at "
            "WHERE touched_at IS NULL",
        ),
    ),
}


def _targets(
    settings: LegacyMigrationSettings,
) -> tuple[_DatabaseTarget, ...]:
    paths = {
        "ratings": settings.ratings_database_path,
        "prompt_tokens": settings.prompt_tokens_database_path,
        "arena": settings.arena_database_path,
        "curation": settings.curation_database_path,
        "playground": settings.playground_database_path,
        "combo_prompts": settings.combo_prompts_database_path,
        "images": settings.images_database_path,
        "prompt_ratings": settings.prompt_ratings_database_path,
        "mv_queue": settings.worker_queue_database_path,
    }
    return tuple(
        _DatabaseTarget(name, Path(path), _DEFINITIONS[name])
        for name, path in paths.items()
    )


def _read_only_connection(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True)


def _inspect_target(target: _DatabaseTarget) -> list[LegacySchemaIssue]:
    if not target.path.is_file():
        return [
            LegacySchemaIssue(
                target.name,
                "missing_database",
                "database file is missing",
            )
        ]
    try:
        connection = _read_only_connection(target.path)
        try:
            quick_check = connection.execute("PRAGMA quick_check").fetchone()
            if not quick_check or str(quick_check[0]).lower() != "ok":
                return [
                    LegacySchemaIssue(
                        target.name,
                        "corrupt",
                        "SQLite quick_check failed",
                    )
                ]
            objects = {
                (str(row[0]), str(row[1]))
                for row in connection.execute(
                    "SELECT type, name FROM sqlite_master"
                ).fetchall()
            }
            issues: list[LegacySchemaIssue] = []
            for table in target.definition.tables:
                if ("table", table.name) not in objects:
                    issues.append(
                        LegacySchemaIssue(
                            target.name,
                            "missing_table",
                            f"missing table {table.name}",
                        )
                    )
                    continue
                actual_columns = {
                    str(row[1]): str(row[2]).upper()
                    for row in connection.execute(
                        f"PRAGMA table_info({table.name})"
                    ).fetchall()
                }
                for column_name, expected_type in table.columns.items():
                    actual_type = actual_columns.get(column_name)
                    if actual_type is None:
                        issues.append(
                            LegacySchemaIssue(
                                target.name,
                                "missing_column",
                                f"{table.name}.{column_name}",
                            )
                        )
                    elif actual_type != expected_type:
                        issues.append(
                            LegacySchemaIssue(
                                target.name,
                                "incompatible_column",
                                (
                                    f"{table.name}.{column_name} has type "
                                    f"{actual_type or '<empty>'}, expected "
                                    f"{expected_type}"
                                ),
                            )
                        )
            for index in target.definition.indexes:
                if ("index", index.name) not in objects:
                    issues.append(
                        LegacySchemaIssue(
                            target.name,
                            "missing_index",
                            f"missing index {index.name}",
                        )
                    )
            for trigger in target.definition.triggers:
                if ("trigger", trigger.name) not in objects:
                    issues.append(
                        LegacySchemaIssue(
                            target.name,
                            "missing_trigger",
                            f"missing trigger {trigger.name}",
                        )
                    )
            return issues
        finally:
            connection.close()
    except (OSError, sqlite3.DatabaseError):
        return [
            LegacySchemaIssue(
                target.name,
                "corrupt",
                "database cannot be opened as SQLite",
            )
        ]


def _apply_definition(path: Path, definition: _DatabaseDefinition) -> None:
    connection = sqlite3.connect(path)
    try:
        existing_tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }
        existing_columns = {
            table.name: {
                str(row[1])
                for row in connection.execute(
                    f"PRAGMA table_info({table.name})"
                ).fetchall()
            }
            for table in definition.tables
            if table.name in existing_tables
        }
        for table in definition.tables:
            connection.execute(table.create_sql)
            prior_columns = existing_columns.get(table.name, set())
            for column_name, statement in table.additive_columns.items():
                if prior_columns and column_name not in prior_columns:
                    connection.execute(statement)
        for index in definition.indexes:
            connection.execute(index.create_sql)
        for trigger in definition.triggers:
            connection.execute(trigger.create_sql)
        for statement in definition.post_upgrade_sql:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def _initialize_to_temporary(target: _DatabaseTarget) -> Path:
    target.path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = target.path.with_name(
        f".{target.path.name}.{uuid4().hex}.tmp"
    )
    try:
        _apply_definition(temporary_path, target.definition)
        temporary_target = _DatabaseTarget(
            target.name,
            temporary_path,
            target.definition,
        )
        issues = _inspect_target(temporary_target)
        if issues:
            raise LegacySchemaValidationError(
                LegacySchemaReport(issues=tuple(issues))
            )
        return temporary_path
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _create_backup(source_path: Path, backup_path: Path) -> None:
    backup_path.parent.mkdir(parents=True, exist_ok=True)
    source = _read_only_connection(source_path)
    destination = sqlite3.connect(backup_path)
    try:
        source.backup(destination)
    finally:
        destination.close()
        source.close()


class LegacySchemaManager:
    """Validate, initialize, and explicitly upgrade legacy databases."""

    def __init__(
        self,
        settings: LegacyMigrationSettings,
        *,
        startup_database_names: Collection[str] | None = None,
    ) -> None:
        self._settings = settings
        self._targets = _targets(settings)
        self._startup_database_names = (
            tuple(startup_database_names)
            if startup_database_names is not None
            else None
        )

    def _select(
        self,
        database_names: Collection[str] | None,
    ) -> tuple[_DatabaseTarget, ...]:
        if database_names is None:
            return self._targets
        requested = {str(name) for name in database_names}
        known = {target.name for target in self._targets}
        unknown = requested - known
        if unknown:
            names = ", ".join(sorted(unknown))
            raise ValueError(f"Unknown legacy database names: {names}")
        return tuple(
            target for target in self._targets if target.name in requested
        )

    def validate(
        self,
        database_names: Collection[str] | None = None,
    ) -> LegacySchemaReport:
        """Inspect selected databases without mutating them."""
        issues = [
            issue
            for target in self._select(database_names)
            for issue in _inspect_target(target)
        ]
        return LegacySchemaReport(issues=tuple(issues))

    def prepare_startup(self) -> LegacySchemaReport:
        """Validate existing databases before initializing missing files."""
        targets = self._select(self._startup_database_names)
        existing_issues = [
            issue
            for target in targets
            if target.path.exists()
            for issue in _inspect_target(target)
        ]
        if existing_issues:
            raise LegacySchemaValidationError(
                LegacySchemaReport(issues=tuple(existing_issues))
            )
        missing = tuple(
            target for target in targets if not target.path.exists()
        )
        temporary_files: list[tuple[_DatabaseTarget, Path]] = []
        created_paths: list[Path] = []
        try:
            for target in missing:
                temporary_files.append(
                    (target, _initialize_to_temporary(target))
                )
            for target, temporary_path in temporary_files:
                temporary_path.replace(target.path)
                created_paths.append(target.path)
        except Exception:
            for created_path in created_paths:
                created_path.unlink(missing_ok=True)
            raise
        finally:
            for _, temporary_path in temporary_files:
                temporary_path.unlink(missing_ok=True)
        final_report = self.validate(self._startup_database_names)
        if final_report.issues:
            raise LegacySchemaValidationError(final_report)
        return LegacySchemaReport(
            initialized=tuple(target.name for target in missing)
        )

    def upgrade(
        self,
        database_names: Collection[str] | None = None,
        backup_directory: Path | None = None,
    ) -> LegacySchemaReport:
        """Back up and additively upgrade selected legacy databases."""
        targets = self._select(database_names)
        reports = {target.name: _inspect_target(target) for target in targets}
        blocked: list[LegacySchemaIssue] = []
        for target in targets:
            table_map = {
                table.name: table for table in target.definition.tables
            }
            for issue in reports[target.name]:
                if issue.code in {"corrupt", "incompatible_column"}:
                    blocked.append(issue)
                elif issue.code == "missing_column":
                    table_name, column_name = issue.detail.split(".", 1)
                    table = table_map[table_name]
                    if column_name not in table.additive_columns:
                        blocked.append(issue)
        if blocked:
            raise LegacySchemaValidationError(
                LegacySchemaReport(issues=tuple(blocked))
            )

        changed = tuple(target for target in targets if reports[target.name])
        existing = tuple(target for target in changed if target.path.exists())
        missing = tuple(
            target for target in changed if not target.path.exists()
        )
        if not changed:
            return LegacySchemaReport()

        backup_root = Path(
            backup_directory
            if backup_directory is not None
            else self._settings.data_directory / "backups"
        )
        run_directory = backup_root / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
            + f"_{uuid4().hex[:8]}"
        )
        backups: dict[Path, Path] = {}
        created: list[Path] = []
        try:
            for target in existing:
                backup_path = (
                    run_directory / f"{target.name}-{target.path.name}"
                )
                _create_backup(target.path, backup_path)
                backups[target.path] = backup_path
            for target in existing:
                _apply_definition(target.path, target.definition)
            for target in missing:
                temporary_path = _initialize_to_temporary(target)
                temporary_path.replace(target.path)
                created.append(target.path)
            result = self.validate([target.name for target in targets])
            if result.issues:
                raise LegacySchemaValidationError(result)
        except Exception:
            for path, backup_path in backups.items():
                shutil.copy2(backup_path, path)
            for path in created:
                path.unlink(missing_ok=True)
            raise
        return LegacySchemaReport(
            initialized=tuple(target.name for target in missing),
            upgraded=tuple(target.name for target in existing),
        )
