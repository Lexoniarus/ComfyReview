"""Behavior tests for explicit canonical schema upgrades."""

from __future__ import annotations

import json
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


def _create_version_four_database(path: Path) -> None:
    _create_version_three_database(path)
    manager = CanonicalSchemaManager(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute("BEGIN IMMEDIATE")
        manager._upgrade_v3_to_v4(connection)
        connection.commit()
    finally:
        connection.close()


def _create_version_twelve_database(path: Path) -> None:
    _create_version_four_database(path)
    manager = CanonicalSchemaManager(path)
    with sqlite3.connect(path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        manager._upgrade_v7_to_v8(connection)
        manager._upgrade_v8_to_v9(connection)
        manager._upgrade_v9_to_v10(connection)
        manager._upgrade_v10_to_v11(connection)
        manager._upgrade_v11_to_v12(connection)
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name
            ) VALUES ('component-v12', 'character', 'character_v12', 'V12')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('revision-v12', ?, 1, '', '', 'prompt-v12-hash')
            """,
            (component_id,),
        )
        definition_id = connection.execute(
            """
            INSERT INTO lora_definitions(
                lora_uid, provider_name, display_name, content_level
            ) VALUES ('lora-v12', 'v12.safetensors', 'V12', 'standard')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO lora_revisions(
                revision_uid, lora_definition_id, revision_number,
                default_model_strength_milli,
                default_clip_strength_milli, content_hash
            ) VALUES ('lora-revision-v12', ?, 1, 1000, 1000, 'lora-v12-hash')
            """,
            (definition_id,),
        )
        connection.commit()


def _create_version_fourteen_database(path: Path) -> None:
    _create_version_twelve_database(path)
    with sqlite3.connect(path) as connection:
        CanonicalSchemaManager._upgrade_v12_to_v13(connection, None)
        CanonicalSchemaManager._upgrade_v13_to_v14(connection)
        connection.commit()


def _legacy_generator_state() -> dict[str, object]:
    return {
        "selections": [
            {
                "kind": "character",
                "mode": "fixed",
                "component_uid": "component-v12",
                "revision_uid": "revision-v12",
            }
        ],
        "loras": [
            {
                "lora_uid": "lora-v12",
                "revision_uid": "lora-revision-v12",
                "model_strength": 0.8,
                "clip_strength": 0.65,
            }
        ],
        "checkpoint": "model.safetensors",
        "sampler": "euler",
        "scheduler": "normal",
        "seed_mode": "fixed",
        "seed": 37,
        "steps_min": 24,
        "steps_max": 32,
        "cfg_min": 6.5,
        "cfg_max": 7.5,
        "cfg_step": 0.25,
        "denoise": 0.9,
        "batch_runs": 2,
        "aspect_format": "1:1",
        "resolution_class": "1080",
    }


def test_old_versions_require_explicit_upgrade(tmp_path: Path) -> None:
    for version, factory in (
        (1, _create_version_one_database),
        (2, _create_version_two_database),
        (3, _create_version_three_database),
        (4, _create_version_four_database),
        (12, _create_version_twelve_database),
    ):
        database_path = tmp_path / f"v{version}.sqlite3"
        factory(database_path)
        with pytest.raises(
            CanonicalSchemaValidationError,
            match="canonical-db upgrade",
        ):
            CanonicalSchemaManager(database_path).prepare_startup()


def test_version_twelve_upgrade_imports_validated_generator_state_to_copy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "canonical-v12.sqlite3"
    output = tmp_path / "canonical-v13.sqlite3"
    state_source = tmp_path / "playground_generator_last.json"
    _create_version_twelve_database(source)
    original = source.read_bytes()
    state_source.write_text(
        json.dumps(
            {
                "legacy": "preserved only in source",
                "generator_v2": _legacy_generator_state(),
            }
        ),
        encoding="utf-8",
    )

    report = CanonicalSchemaManager(source).upgrade_to(
        output,
        tmp_path / "backups",
        state_source,
    )

    assert report.upgraded_from == 12
    assert report.schema_version == 15
    assert source.read_bytes() == original
    with sqlite3.connect(source) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (12,)
    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT checkpoint, cfg_step_milli FROM playground_generator_state"
        ).fetchone() == ("model.safetensors", 250)
        assert connection.execute(
            "SELECT kind, mode FROM playground_generator_prompt_selections"
        ).fetchone() == ("character", "fixed")
        assert connection.execute(
            "SELECT model_strength_milli, clip_strength_milli "
            "FROM playground_generator_loras"
        ).fetchone() == (800, 650)


def test_version_twelve_upgrade_rejects_invalid_generator_state_atomically(
    tmp_path: Path,
) -> None:
    source = tmp_path / "canonical-v12.sqlite3"
    output = tmp_path / "canonical-v13.sqlite3"
    state_source = tmp_path / "invalid.json"
    _create_version_twelve_database(source)
    original = source.read_bytes()
    state_source.write_text(
        json.dumps({"generator_v2": {"checkpoint": "incomplete"}}),
        encoding="utf-8",
    )

    with pytest.raises(
        CanonicalSchemaValidationError,
        match="Legacy Generator state is invalid",
    ):
        CanonicalSchemaManager(source).upgrade_to(
            output,
            tmp_path / "backups",
            state_source,
        )

    assert source.read_bytes() == original
    assert not output.exists()


@pytest.mark.parametrize(
    ("contents", "message"),
    (
        ("not-json", "cannot be read"),
        (json.dumps({}), "missing generator_v2"),
    ),
)
def test_version_twelve_upgrade_rejects_unreadable_legacy_state(
    tmp_path: Path,
    contents: str,
    message: str,
) -> None:
    source = tmp_path / "canonical-v12.sqlite3"
    output = tmp_path / "canonical-v13.sqlite3"
    state_source = tmp_path / "legacy.json"
    _create_version_twelve_database(source)
    original = source.read_bytes()
    state_source.write_text(contents, encoding="utf-8")

    with pytest.raises(CanonicalSchemaValidationError, match=message):
        CanonicalSchemaManager(source).upgrade_to(
            output,
            tmp_path / "backups",
            state_source,
        )

    assert source.read_bytes() == original
    assert not output.exists()


@pytest.mark.parametrize(
    ("reference", "replacement", "message"),
    (
        ("revision_uid", "missing-prompt-revision", "unknown prompt"),
        (
            "lora_revision_uid",
            "missing-lora-revision",
            "unknown LoRA",
        ),
    ),
)
def test_version_twelve_upgrade_rejects_unknown_catalog_references(
    tmp_path: Path,
    reference: str,
    replacement: str,
    message: str,
) -> None:
    source = tmp_path / "canonical-v12.sqlite3"
    output = tmp_path / "canonical-v13.sqlite3"
    state_source = tmp_path / "legacy.json"
    _create_version_twelve_database(source)
    original = source.read_bytes()
    state = _legacy_generator_state()
    if reference == "revision_uid":
        state["selections"][0]["revision_uid"] = replacement  # type: ignore[index]
    else:
        state["loras"][0]["revision_uid"] = replacement  # type: ignore[index]
    state_source.write_text(
        json.dumps({"generator_v2": state}), encoding="utf-8"
    )

    with pytest.raises(CanonicalSchemaValidationError, match=message):
        CanonicalSchemaManager(source).upgrade_to(
            output,
            tmp_path / "backups",
            state_source,
        )

    assert source.read_bytes() == original
    assert not output.exists()


def test_generator_state_validator_rejects_missing_columns() -> None:
    with sqlite3.connect(":memory:") as connection:
        connection.executescript(
            """
            CREATE TABLE playground_generator_state(singleton_id INTEGER);
            CREATE TABLE playground_generator_prompt_selections(
                singleton_id INTEGER
            );
            CREATE TABLE playground_generator_loras(singleton_id INTEGER);
            """
        )

        with pytest.raises(
            CanonicalSchemaValidationError, match="missing columns"
        ):
            CanonicalSchemaManager._validate_generator_state_v13(connection)


@pytest.mark.parametrize("mismatch", ("prompt", "lora"))
def test_generator_state_validator_rejects_mismatched_revisions(
    tmp_path: Path,
    mismatch: str,
) -> None:
    database_path = tmp_path / f"mismatched-{mismatch}.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO playground_generator_state(
                singleton_id, checkpoint, sampler, scheduler, seed_mode, seed,
                steps_min, steps_max, cfg_min_milli, cfg_max_milli,
                cfg_step_milli, denoise_milli, batch_runs,
                aspect_format, resolution_class
            ) VALUES (1, 'model', 'euler', 'normal', 'fixed', 1,
                      1, 1, 1000, 1000, 1000, 1000, 1, '1:1', '1080')
            """
        )
        if mismatch == "prompt":
            first_component = connection.execute(
                "INSERT INTO prompt_components(component_uid, kind, "
                "component_key, name) VALUES ('first', 'character', "
                "'first', 'First')"
            ).lastrowid
            second_component = connection.execute(
                "INSERT INTO prompt_components(component_uid, kind, "
                "component_key, name) VALUES ('second', 'character', "
                "'second', 'Second')"
            ).lastrowid
            revision = connection.execute(
                "INSERT INTO prompt_revisions(revision_uid, component_id, "
                "revision_number, positive_text, negative_text, content_hash) "
                "VALUES ('second-revision', ?, 1, '', '', 'second-hash')",
                (second_component,),
            ).lastrowid
            connection.execute(
                "INSERT INTO playground_generator_prompt_selections("
                "singleton_id, position, kind, mode, component_id, revision_id) "
                "VALUES (1, 0, 'character', 'fixed', ?, ?)",
                (first_component, revision),
            )
        else:
            first_definition = connection.execute(
                "INSERT INTO lora_definitions(lora_uid, provider_name, "
                "display_name, content_level) VALUES "
                "('first', 'first.safetensors', 'First', 'standard')"
            ).lastrowid
            second_definition = connection.execute(
                "INSERT INTO lora_definitions(lora_uid, provider_name, "
                "display_name, content_level) VALUES "
                "('second', 'second.safetensors', 'Second', 'standard')"
            ).lastrowid
            revision = connection.execute(
                "INSERT INTO lora_revisions(revision_uid, "
                "lora_definition_id, revision_number, "
                "default_model_strength_milli, "
                "default_clip_strength_milli, content_hash) "
                "VALUES ('second-revision', ?, 1, 1000, 1000, 'second-hash')",
                (second_definition,),
            ).lastrowid
            connection.execute(
                "INSERT INTO playground_generator_loras("
                "singleton_id, position, lora_definition_id, "
                "lora_revision_id, model_strength_milli, "
                "clip_strength_milli) VALUES (1, 0, ?, ?, 1000, 1000)",
                (first_definition, revision),
            )

        with pytest.raises(
            CanonicalSchemaValidationError, match="mismatched catalog"
        ):
            CanonicalSchemaManager._validate_generator_state_v13(connection)


def test_version_two_upgrade_preserves_output_identity_and_reviews(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    backup_root = tmp_path / "backups"
    _create_version_two_database(database_path)

    report = CanonicalSchemaManager(database_path).upgrade(backup_root)

    assert report.schema_version == 15
    assert report.upgraded_from == 2
    assert report.backup_path is not None
    assert report.backup_path.is_file()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
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

    assert report.schema_version == 15
    assert report.upgraded_from == 1
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
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

    assert report.schema_version == 15
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


def test_version_four_upgrade_adds_revisioned_prompt_catalog(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            INSERT INTO prompt_components(kind, component_key, name)
            VALUES ('scene', 'legacy-scene', 'Legacy Scene')
            """
        )

    report = CanonicalSchemaManager(database_path).upgrade(
        tmp_path / "backups"
    )

    assert report.schema_version == 15
    assert report.upgraded_from == 4
    with sqlite3.connect(database_path) as connection:
        objects = dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master WHERE name IN "
                "('prompt_revisions', 'prompt_compositions', "
                "'prompt_composition_revisions', "
                "'legacy_prompt_component_sources')"
            ).fetchall()
        )
        assert objects == {
            "legacy_prompt_component_sources": "table",
            "prompt_composition_revisions": "table",
            "prompt_compositions": "table",
            "prompt_revisions": "table",
        }
        component_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(prompt_components)"
            )
        }
        generation_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(generations)")
        }
        assert "archived_at" in component_columns
        assert "component_uid" in component_columns
        assert "prompt_composition_id" in generation_columns
        assert connection.execute(
            "SELECT component_uid FROM prompt_components "
            "WHERE component_key = 'legacy-scene'"
        ).fetchone() == ("canonical-v4-component-1",)


def test_version_five_upgrade_adds_output_provenance(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    with sqlite3.connect(database_path) as connection:
        CanonicalSchemaManager._upgrade_v4_to_v5(connection)

    report = CanonicalSchemaManager(database_path).upgrade(
        tmp_path / "backups"
    )

    assert report.schema_version == 15
    assert report.upgraded_from == 5
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        image_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(images)")
        }
        assert {"content_hash", "output_role"} <= image_columns


def test_version_six_upgrade_normalizes_prompt_atoms_without_changing_snapshots(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name
            ) VALUES ('component-a', 'character', 'character_a', 'A')
            """
        ).lastrowid
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES (?, ?, 1, ?, ?, 'hash-a')
            """,
            (
                "revision-a",
                component_id,
                "silver hair, (cyan eyes:1.2)",
                "multiple people",
            ),
        )
        manager._upgrade_v5_to_v6(connection)
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.schema_version == 15
    assert report.upgraded_from == 6
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT revision_uid, positive_text, negative_text "
            "FROM prompt_revisions"
        ).fetchone() == (
            "revision-a",
            "silver hair, (cyan eyes:1.2)",
            "multiple people",
        )
        assert connection.execute(
            """
            SELECT usage.scope, usage.position, atom.canonical_text,
                   usage.weight_milli
            FROM prompt_revision_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            ORDER BY usage.scope DESC, usage.position
            """
        ).fetchall() == [
            ("pos", 0, "silver hair", 1000),
            ("pos", 1, "cyan eyes", 1200),
            ("neg", 0, "multiple people", 1000),
        ]


def test_version_seven_upgrade_adds_settings_and_normalizes_generation_loras(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        connection.execute(
            "UPDATE generations SET loras_json = ? WHERE id = 1",
            (
                '[{"name":"style.safetensors","strength_model":0.8,'
                '"strength_clip":0.65}]',
            ),
        )
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.schema_version == 15
    assert report.upgraded_from == 7
    assert report.backup_path is not None
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute("PRAGMA foreign_key_check").fetchall() == []
        assert connection.execute(
            "SELECT density, motion, analytics_page_size, "
            "review_unrated_only, review_max_attempts "
            "FROM workspace_preferences WHERE singleton_id = 1"
        ).fetchone() == ("comfortable", "system", 24, 1, 50)
        assert connection.execute(
            "SELECT generation_id, position, lora_name, "
            "model_strength_milli, clip_strength_milli "
            "FROM generation_loras"
        ).fetchall() == [(1, 0, "style.safetensors", 800, 650)]

    with sqlite3.connect(report.backup_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (7,)


def test_version_seven_upgrade_reports_and_skips_incomplete_lora_provenance(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        connection.execute(
            "UPDATE generations SET loras_json = ? WHERE id = 1",
            ('[{"name":"style.safetensors"}]',),
        )
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT COUNT(*) FROM generation_loras"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT loras_json FROM generations WHERE id = 1"
        ).fetchone() == ('[{"name":"style.safetensors"}]',)
    assert report.warnings == (
        "skipped 1 incomplete historical LoRA provenance items",
    )


def test_version_seven_upgrade_normalizes_metadata_export_lora_keys(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        connection.execute(
            "UPDATE generations SET loras_json = ? WHERE id = 1",
            (
                '[{"name":"style.safetensors","sm":0.8,"sc":0.65,'
                '"node_id":"37","class_type":"LoraLoader"}]',
            ),
        )
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.warnings == ()
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT lora_name, model_strength_milli, clip_strength_milli "
            "FROM generation_loras"
        ).fetchall() == [("style.safetensors", 800, 650)]


def test_version_eight_upgrade_adds_content_levels_and_image_dimensions(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        manager._upgrade_v7_to_v8(connection)
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.schema_version == 15
    assert report.upgraded_from == 8
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT level, position FROM workspace_content_levels"
        ).fetchall() == [("standard", 0)]
        profile_columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(generation_profiles)"
            )
        }
        generation_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(generations)")
        }
        assert {"image_width", "image_height"} <= profile_columns
        assert {"image_width", "image_height"} <= generation_columns
        assert "output_tier" in profile_columns
        assert {
            "output_tier",
            "output_width",
            "output_height",
            "inferred_content_level",
        } <= generation_columns
    assert report.backup_path is not None
    with sqlite3.connect(report.backup_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (8,)


def test_version_nine_upgrade_adds_output_and_content_classification(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        manager._upgrade_v7_to_v8(connection)
        manager._upgrade_v8_to_v9(connection)
        connection.execute(
            """
            INSERT INTO generation_profiles(
                profile_uid, name, blueprint_uid, blueprint_version,
                checkpoint, sampler, scheduler, seed_mode, steps_min,
                steps_max, cfg_min_milli, cfg_max_milli, denoise_milli,
                batch_size, image_width, image_height
            ) VALUES (
                'profile-1', 'Default', 'default-character', 3,
                'model', 'euler', 'normal', 'random', 20, 30,
                5000, 7000, 1000, 1, 768, 1152
            )
            """
        )
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.upgraded_from == 9
    assert report.backup_path is not None
    with sqlite3.connect(report.backup_path) as backup:
        assert backup.execute("PRAGMA user_version").fetchone() == (9,)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT blueprint_version, output_tier "
            "FROM generation_profiles WHERE profile_uid = 'profile-1'"
        ).fetchone() == (4, "full_hd_1080")
        objects = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "lora_definitions",
            "image_content_level_events",
            "image_content_level_state",
            "image_geometry_projection",
        } <= objects


def test_version_ten_upgrade_adds_empty_geometry_projection(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        manager._upgrade_v7_to_v8(connection)
        manager._upgrade_v8_to_v9(connection)
        manager._upgrade_v9_to_v10(connection)
        connection.commit()

    report = manager.upgrade(tmp_path / "backups")

    assert report.upgraded_from == 10
    assert report.schema_version == 15
    assert report.backup_path is not None
    with sqlite3.connect(report.backup_path) as backup:
        assert backup.execute("PRAGMA user_version").fetchone() == (10,)
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT COUNT(*) FROM image_geometry_projection"
        ).fetchone() == (0,)


def test_version_thirteen_upgrade_moves_lora_level_to_revision_copy(
    tmp_path: Path,
) -> None:
    source = tmp_path / "schema-v13.sqlite3"
    output = tmp_path / "schema-v15.sqlite3"
    _create_version_twelve_database(source)
    with sqlite3.connect(source) as connection:
        connection.execute(
            "UPDATE lora_definitions SET content_level = 'nude' "
            "WHERE lora_uid = 'lora-v12'"
        )
        CanonicalSchemaManager._upgrade_v12_to_v13(connection, None)
        connection.commit()
    source_before = source.read_bytes()

    report = CanonicalSchemaManager(source).upgrade_to(output)

    assert report.upgraded_from == 13
    assert report.schema_version == 15
    assert source.read_bytes() == source_before
    with sqlite3.connect(output) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (15,)
        assert connection.execute(
            "SELECT content_level FROM lora_revisions "
            "WHERE revision_uid = 'lora-revision-v12'"
        ).fetchone() == ("nude",)


def test_version_fourteen_upgrade_adds_prompt_variant_facts_and_baseline(
    tmp_path: Path,
) -> None:
    source = tmp_path / "schema-v14.sqlite3"
    output = tmp_path / "schema-v15.sqlite3"
    _create_version_fourteen_database(source)
    with sqlite3.connect(source) as connection:
        component_id = connection.execute(
            "SELECT id FROM prompt_components "
            "WHERE component_uid = 'component-v12'"
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES (
                'revision-v14-latest', ?, 2, 'hero', 'blur', 'prompt-v14-hash'
            )
            """,
            (component_id,),
        )
        revision_id = connection.execute(
            "SELECT id FROM prompt_revisions "
            "WHERE revision_uid = 'revision-v14-latest'"
        ).fetchone()[0]
        for scope, text in (("pos", "hero"), ("neg", "blur")):
            connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                (text,),
            )
            atom_id = connection.execute(
                "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                (text,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO prompt_revision_atom_usages("
                "revision_id, atom_id, scope, position, weight_milli) "
                "VALUES (?, ?, ?, 0, 1000)",
                (revision_id, atom_id, scope),
            )
        exact_composition_id = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-exact')"
        ).lastrowid
        ambiguous_composition_id = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-ambiguous')"
        ).lastrowid
        old_revision_id = connection.execute(
            "SELECT id FROM prompt_revisions "
            "WHERE revision_uid = 'revision-v12'"
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO prompt_composition_revisions("
            "composition_id, revision_id, slot, position) "
            "VALUES (?, ?, 'character', 0)",
            (exact_composition_id, revision_id),
        )
        connection.execute(
            "INSERT INTO prompt_composition_revisions("
            "composition_id, revision_id, slot, position) "
            "VALUES (?, ?, 'character', 0)",
            (ambiguous_composition_id, old_revision_id),
        )
        connection.execute(
            "UPDATE generations SET prompt_composition_id = CASE id "
            "WHEN 1 THEN ? WHEN 2 THEN ? END WHERE id IN (1, 2)",
            (exact_composition_id, ambiguous_composition_id),
        )
        connection.commit()
    source_before = source.read_bytes()

    report = CanonicalSchemaManager(source).upgrade_to(output)

    assert report.schema_version == 15
    assert report.upgraded_from == 14
    assert source.read_bytes() == source_before
    with sqlite3.connect(output) as connection:
        objects = {
            name
            for (name,) in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        assert {
            "prompt_component_candidates",
            "prompt_candidate_atom_usages",
            "generation_prompt_groups",
            "generation_prompt_group_atom_usages",
            "prompt_component_promotions",
        } <= objects
        assert connection.execute(
            """
            SELECT revision.revision_uid,
                   promotion.previous_revision_id,
                   promotion.policy_version,
                   promotion.review_frontier,
                   promotion.reason,
                   promotion.provisional
            FROM prompt_component_promotions AS promotion
            JOIN prompt_revisions AS revision
              ON revision.id = promotion.revision_id
            """
        ).fetchall() == [
            (
                "revision-v14-latest",
                None,
                "prompt-guidance-v1",
                2,
                "migration_baseline",
                1,
            )
        ]
        selection_columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(playground_generator_prompt_selections)"
            )
        }
        assert "candidate_id" in selection_columns
        assert connection.execute(
            "SELECT generation_id, kind, position "
            "FROM generation_prompt_groups"
        ).fetchall() == [(1, "character", 0)]
        assert connection.execute(
            "SELECT COUNT(*) FROM generation_prompt_group_atom_usages"
        ).fetchone() == (2,)


def test_version_fourteen_upgrade_failure_preserves_source(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = tmp_path / "schema-v14.sqlite3"
    _create_version_fourteen_database(source)
    source_before = source.read_bytes()
    original_upgrade = CanonicalSchemaManager._upgrade_v14_to_v15

    def fail_after_schema_changes(connection: sqlite3.Connection) -> None:
        original_upgrade(connection)
        raise OSError("forced v15 migration failure")

    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_upgrade_v14_to_v15",
        staticmethod(fail_after_schema_changes),
    )

    with pytest.raises(OSError, match="forced v15 migration failure"):
        CanonicalSchemaManager(source).upgrade(tmp_path / "backups")

    assert source.read_bytes() == source_before
    with sqlite3.connect(source) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (14,)


def test_version_seven_upgrade_rejects_malformed_lora_provenance(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    _create_version_four_database(database_path)
    manager = CanonicalSchemaManager(database_path)
    with sqlite3.connect(database_path) as connection:
        manager._upgrade_v4_to_v5(connection)
        manager._upgrade_v5_to_v6(connection)
        manager._upgrade_v6_to_v7(connection)
        connection.execute(
            "UPDATE generations SET loras_json = ? WHERE id = 1",
            ("not-json",),
        )
        connection.commit()

    with pytest.raises(
        CanonicalSchemaValidationError,
        match="not valid JSON",
    ):
        manager.upgrade(tmp_path / "backups")

    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (7,)


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
    output_database = tmp_path / "comfyreview-v13.sqlite3"

    assert main(["canonical-db", "validate"]) == 2
    assert "canonical-db upgrade" in capsys.readouterr().err

    assert (
        main(
            [
                "canonical-db",
                "upgrade",
                "--backup-dir",
                str(tmp_path / "backups"),
                "--output",
                str(output_database),
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert '"schema_version": 15' in output
    assert '"upgraded_from": 2' in output

    assert main(["canonical-db", "validate"]) == 2
    assert (
        CanonicalSchemaManager(output_database).validate().schema_version == 15
    )
    with sqlite3.connect(database_path) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (2,)
