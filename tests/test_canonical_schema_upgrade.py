"""Behavior tests for explicit canonical schema version-two upgrades."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

import comfyreview.repositories.sqlite.canonical_schema as schema_module
from comfyreview.__main__ import main
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
)


def _create_version_one_database(path: Path) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.executescript(schema_module._SCHEMA_V1_SQL)
        connection.execute("PRAGMA user_version = 1")
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos-hash', 'hero')"
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg-hash', 'blur')"
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid,
                model_branch,
                checkpoint,
                combo_key,
                seed,
                steps,
                cfg,
                sampler,
                scheduler,
                denoise,
                loras_json,
                positive_prompt_id,
                negative_prompt_id
            )
            VALUES (
                'generation-one',
                'sdxl',
                'model.safetensors',
                'combo',
                123,
                24,
                6.5,
                'euler',
                'normal',
                1.0,
                '[]',
                1,
                2
            )
            """
        )
        connection.commit()
    finally:
        connection.close()


def test_version_one_requires_explicit_upgrade(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_one_database(database_path)

    with pytest.raises(
        CanonicalSchemaValidationError,
        match="canonical-db upgrade",
    ):
        CanonicalSchemaManager(database_path).prepare_startup()


def test_upgrade_backs_up_and_preserves_generation_facts(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    backup_root = tmp_path / "backups"
    _create_version_one_database(database_path)

    report = CanonicalSchemaManager(database_path).upgrade(backup_root)

    assert report.schema_version == 2
    assert report.upgraded_from == 1
    assert report.backup_path is not None
    assert report.backup_path.is_file()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        row = connection.execute(
            """
            SELECT generation_uid, source, status, seed
            FROM generations
            """
        ).fetchone()
        assert row == (
            "generation-one",
            "legacy_sidecar",
            "completed",
            123,
        )
        objects = dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE name = 'generation_sampler_stages'"
            ).fetchall()
        )
        assert objects == {"generation_sampler_stages": "table"}

    with sqlite3.connect(report.backup_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        stage_table = connection.execute(
            "SELECT 1 FROM sqlite_master "
            "WHERE type = 'table' "
            "AND name = 'generation_sampler_stages'"
        ).fetchone()
        assert stage_table is None


def test_upgrade_restores_backup_after_failed_migration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_one_database(database_path)
    original_upgrade = CanonicalSchemaManager._upgrade_v1_to_v2

    def fail_after_upgrade(
        self: CanonicalSchemaManager,
        connection: sqlite3.Connection,
    ) -> None:
        original_upgrade(self, connection)
        raise OSError("forced migration failure")

    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_upgrade_v1_to_v2",
        fail_after_upgrade,
    )

    with pytest.raises(OSError, match="forced migration failure"):
        CanonicalSchemaManager(database_path).upgrade(tmp_path / "backups")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (1,)
        row = connection.execute(
            "SELECT generation_uid FROM generations"
        ).fetchone()
        assert row == ("generation-one",)


def test_canonical_database_cli_validates_and_upgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_one_database(database_path)
    monkeypatch.setenv("COMFYREVIEW_DATABASE", str(database_path))

    assert main(["canonical-db", "validate"]) == 2
    assert "canonical-db upgrade" in capsys.readouterr().err

    assert (
        main(
            [
                "canonical-db",
                "upgrade",
                "--backup-dir",
                str(tmp_path / "backups"),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"schema_version": 2' in output
    assert '"upgraded_from": 1' in output

    assert main(["canonical-db", "validate"]) == 0
    assert '"schema_version": 2' in capsys.readouterr().out
