"""Behavior tests for the explicit legacy SQLite schema lifecycle."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

import pytest

import comfyreview.repositories.sqlite.legacy_schema as schema_module
from comfyreview.__main__ import main
from comfyreview.application import LegacySchemaValidationError
from comfyreview.repositories.sqlite import LegacySchemaManager
from comfyreview.repositories.sqlite.connection import connect_existing
from comfyreview.settings import Settings, load_settings


def _settings(tmp_path: Path) -> Settings:
    return load_settings(base_directory=tmp_path, environ={})


def _database_paths(settings: Settings) -> tuple[Path, ...]:
    return (
        settings.ratings_database_path,
        settings.prompt_tokens_database_path,
        settings.arena_database_path,
        settings.curation_database_path,
        settings.playground_database_path,
        settings.combo_prompts_database_path,
        settings.images_database_path,
        settings.prompt_ratings_database_path,
        settings.worker_queue_database_path,
    )


def _create_old_ratings_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE ratings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                png_path TEXT NOT NULL,
                json_path TEXT NOT NULL,
                run INTEGER NOT NULL DEFAULT 1,
                model_branch TEXT NOT NULL,
                checkpoint TEXT NOT NULL,
                combo_key TEXT NOT NULL,
                rating INTEGER,
                deleted INTEGER NOT NULL DEFAULT 0,
                rating_count INTEGER NOT NULL DEFAULT 1
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_startup_initializes_only_fully_missing_databases(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    manager = LegacySchemaManager(settings)

    report = manager.prepare_startup()

    assert set(report.initialized) == {
        "ratings",
        "prompt_tokens",
        "arena",
        "curation",
        "playground",
        "combo_prompts",
        "images",
        "prompt_ratings",
        "mv_queue",
    }
    assert all(path.is_file() for path in _database_paths(settings))
    assert not manager.validate().issues


def test_runtime_startup_initializes_only_selected_legacy_database(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    manager = LegacySchemaManager(
        settings,
        startup_database_names=("playground",),
    )

    report = manager.prepare_startup()

    assert report.initialized == ("playground",)
    assert settings.playground_database_path.is_file()
    assert all(
        not path.exists()
        for path in _database_paths(settings)
        if path != settings.playground_database_path
    )


def test_startup_does_not_modify_valid_databases(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = LegacySchemaManager(settings)
    manager.prepare_startup()
    before = {path: path.read_bytes() for path in _database_paths(settings)}

    report = manager.prepare_startup()

    assert report.initialized == ()
    assert {path: path.read_bytes() for path in before} == before


def test_invalid_existing_database_prevents_all_initialization(
    tmp_path: Path,
) -> None:
    settings = _settings(tmp_path)
    settings.ratings_database_path.write_bytes(b"")

    with pytest.raises(LegacySchemaValidationError):
        LegacySchemaManager(settings).prepare_startup()

    assert settings.ratings_database_path.is_file()
    assert all(
        not path.exists()
        for path in _database_paths(settings)
        if path != settings.ratings_database_path
    )


def test_startup_removes_partial_initialization_when_replace_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    original_replace = Path.replace
    replacements = 0

    def fail_second_replace(source: Path, target: Path) -> Path:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("replace failed")
        return original_replace(source, target)

    monkeypatch.setattr(Path, "replace", fail_second_replace)

    with pytest.raises(OSError, match="replace failed"):
        LegacySchemaManager(settings).prepare_startup()

    assert all(not path.exists() for path in _database_paths(settings))
    assert not tuple(tmp_path.rglob("*.tmp"))


def test_validation_allows_unknown_tables_and_columns(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    manager = LegacySchemaManager(settings)
    manager.upgrade(["ratings"], tmp_path / "backups")
    with sqlite3.connect(settings.ratings_database_path) as connection:
        connection.execute("ALTER TABLE ratings ADD COLUMN future_value TEXT")
        connection.execute("CREATE TABLE future_table (value TEXT)")

    assert not manager.validate(["ratings"]).issues


def test_upgrade_backs_up_before_adding_known_columns(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    _create_old_ratings_database(settings.ratings_database_path)

    report = LegacySchemaManager(settings).upgrade(
        ["ratings"],
        tmp_path / "backups",
    )

    assert report.upgraded == ("ratings",)
    with sqlite3.connect(settings.ratings_database_path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(ratings)")
        }
    assert "steps" in columns
    backups = tuple((tmp_path / "backups").rglob("ratings-ratings.sqlite3"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as connection:
        backup_columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(ratings)")
        }
    assert "steps" not in backup_columns


def test_upgrade_restores_backup_when_upgrade_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = _settings(tmp_path)
    _create_old_ratings_database(settings.ratings_database_path)
    original_apply = schema_module._apply_definition

    def fail_after_apply(path: Path, definition: Any) -> None:
        original_apply(path, definition)
        raise OSError("upgrade failed")

    monkeypatch.setattr(schema_module, "_apply_definition", fail_after_apply)

    with pytest.raises(OSError, match="upgrade failed"):
        LegacySchemaManager(settings).upgrade(
            ["ratings"],
            tmp_path / "backups",
        )

    with sqlite3.connect(settings.ratings_database_path) as connection:
        columns = {
            str(row[1])
            for row in connection.execute("PRAGMA table_info(ratings)")
        }
    assert "steps" not in columns


def test_repository_connection_never_creates_missing_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "missing.sqlite3"

    with pytest.raises(FileNotFoundError):
        connect_existing(database_path)

    assert not database_path.exists()


def test_legacy_database_cli_has_stable_validation_exit_codes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "ratings.sqlite3"
    monkeypatch.setenv("COMFYREVIEW_RATINGS_DB", str(database_path))

    assert main(["legacy-db", "validate", "--database", "ratings"]) == 2
    assert '"code": "missing_database"' in capsys.readouterr().out

    assert (
        main(
            [
                "legacy-db",
                "upgrade",
                "--database",
                "ratings",
                "--backup-dir",
                str(tmp_path / "backups"),
            ]
        )
        == 0
    )
    assert '"initialized": ["ratings"]' in capsys.readouterr().out
    assert main(["legacy-db", "validate", "--database", "ratings"]) == 0
