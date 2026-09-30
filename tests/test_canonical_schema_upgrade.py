"""Behavior tests for explicit canonical schema upgrades."""

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


def _create_version_two_database(path: Path) -> None:
    _create_version_one_database(path)
    manager = CanonicalSchemaManager(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("BEGIN IMMEDIATE")
        manager._upgrade_v1_to_v2(connection)
        connection.commit()
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
                'generation-deleted',
                'sdxl',
                'model.safetensors',
                'combo-deleted',
                456,
                20,
                5.5,
                'euler',
                'normal',
                1.0,
                '[]',
                1,
                2
            )
            """
        )
        connection.execute(
            """
            INSERT INTO images(
                id, image_uid, generation_id, png_path, json_path
            )
            VALUES (
                10,
                'generation-one',
                1,
                'live.png',
                'live.json'
            )
            """
        )
        connection.execute(
            """
            INSERT INTO image_reviews(id, image_id, rating, version)
            VALUES (20, 10, 8, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO deleted_images(
                id,
                generation_id,
                png_path,
                json_path,
                version
            )
            VALUES (30, 2, 'deleted.png', 'deleted.json', 2)
            """
        )
        connection.execute(
            "UPDATE review_clock SET value = 2 WHERE singleton_id = 1"
        )
        connection.commit()
    finally:
        connection.close()


def _create_version_three_database(path: Path) -> None:
    _create_version_two_database(path)
    manager = CanonicalSchemaManager(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        manager._upgrade_v2_to_v3(connection)
        connection.commit()
    finally:
        connection.close()


def test_old_versions_require_explicit_upgrade(tmp_path: Path) -> None:
    for version, factory in (
        (1, _create_version_one_database),
        (2, _create_version_two_database),
        (3, _create_version_three_database),
    ):
        database_path = tmp_path / f"v{version}.sqlite3"
        factory(database_path)
        with pytest.raises(
            CanonicalSchemaValidationError,
            match="canonical-db upgrade",
        ):
            CanonicalSchemaManager(database_path).prepare_startup()


def test_version_two_upgrade_preserves_output_identity_and_reviews(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    backup_root = tmp_path / "backups"
    _create_version_two_database(database_path)

    report = CanonicalSchemaManager(database_path).upgrade(backup_root)

    assert report.schema_version == 4
    assert report.upgraded_from == 2
    assert report.backup_path is not None
    assert report.backup_path.is_file()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (4,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        live = connection.execute(
            """
            SELECT image_uid, generation_id, output_node_id, output_index,
                   png_path, json_path
            FROM images
            WHERE id = 10
            """
        ).fetchone()
        assert live == (
            "generation-one",
            1,
            "legacy_sidecar",
            0,
            "live.png",
            "live.json",
        )
        assert connection.execute(
            "SELECT image_id, rating, version FROM image_reviews"
        ).fetchone() == (10, 8, 1)
        assert connection.execute(
            """
            SELECT event_type, rating, source, source_key, sequence
            FROM review_events
            WHERE image_id = 10
            """
        ).fetchone() == (
            "rating",
            8,
            "canonical_v3",
            "image-review:20",
            1,
        )
        deleted = connection.execute(
            """
            SELECT image_uid, generation_id, png_path, json_path, version
            FROM deleted_images
            """
        ).fetchone()
        assert deleted == (
            "generation-deleted",
            2,
            "deleted.png",
            "deleted.json",
            2,
        )
        assert (
            connection.execute(
                "SELECT deleted_at FROM images WHERE image_uid = ?",
                ("generation-deleted",),
            ).fetchone()[0]
            is not None
        )
        assert connection.execute(
            """
            SELECT event_type, rating, source_key, sequence
            FROM review_events
            WHERE event_type = 'delete'
            """
        ).fetchone() == ("delete", None, "deleted-image:30", 2)
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(
                """
                INSERT INTO image_reviews(image_id, rating, version)
                VALUES (10, 9, 3)
                """
            )
        connection.execute(
            """
            INSERT INTO images(
                image_uid,
                generation_id,
                output_node_id,
                output_index,
                png_path,
                json_path
            )
            VALUES ('second-output', 1, '42', 0, 'second.png', NULL)
            """
        )
        connection.commit()
        assert connection.execute(
            "SELECT COUNT(*) FROM images WHERE generation_id = 1"
        ).fetchone() == (2,)

    with sqlite3.connect(report.backup_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)


def test_version_one_can_upgrade_directly_to_current_schema(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_one_database(database_path)

    report = CanonicalSchemaManager(database_path).upgrade(
        tmp_path / "backups"
    )

    assert report.schema_version == 4
    assert report.upgraded_from == 1
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (4,)
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


def test_version_three_upgrade_preserves_ids_and_replaces_writable_state(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_three_database(database_path)

    report = CanonicalSchemaManager(database_path).upgrade(
        tmp_path / "backups"
    )

    assert report.schema_version == 4
    assert report.upgraded_from == 3
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT id, image_uid FROM images ORDER BY id"
        ).fetchall() == [
            (10, "generation-one"),
            (11, "generation-deleted"),
        ]
        assert dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE name IN ('image_reviews', 'deleted_images')"
            ).fetchall()
        ) == {
            "deleted_images": "view",
            "image_reviews": "view",
        }
        with pytest.raises(sqlite3.OperationalError):
            connection.execute("DELETE FROM image_reviews WHERE image_id = 10")


def test_upgrade_rolls_back_without_unnecessary_backup_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_two_database(database_path)
    original_upgrade = CanonicalSchemaManager._upgrade_v2_to_v3

    def fail_after_upgrade(
        self: CanonicalSchemaManager,
        connection: sqlite3.Connection,
    ) -> None:
        original_upgrade(self, connection)
        raise OSError("forced migration failure")

    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_upgrade_v2_to_v3",
        fail_after_upgrade,
    )
    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_restore_backup",
        lambda *_args: pytest.fail("valid rollback must not restore a file"),
    )

    with pytest.raises(OSError, match="forced migration failure"):
        CanonicalSchemaManager(database_path).upgrade(tmp_path / "backups")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
        assert connection.execute(
            "SELECT image_uid FROM images WHERE id = 10"
        ).fetchone() == ("generation-one",)


def test_canonical_database_cli_validates_and_upgrades(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_two_database(database_path)
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
    assert '"schema_version": 4' in output
    assert '"upgraded_from": 2' in output

    assert main(["canonical-db", "validate"]) == 0
    assert '"schema_version": 4' in capsys.readouterr().out
