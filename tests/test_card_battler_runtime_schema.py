"""Behavior tests for the isolated Card Battler runtime schema owner."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import CardBattlerRuntimeSchemaError
from comfyreview.repositories.sqlite import (
    CARD_BATTLER_RUNTIME_SCHEMA_VERSION,
    CardBattlerRuntimeSchemaManager,
)


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_initializes_only_missing_runtime_database(tmp_path: Path) -> None:
    canonical = tmp_path / "comfyreview.sqlite3"
    model = tmp_path / "card_battler.sqlite3"
    canonical.write_bytes(b"canonical-unchanged")
    model.write_bytes(b"model-unchanged")
    canonical_digest = _digest(canonical)
    model_digest = _digest(model)
    runtime = tmp_path / "runtime" / "card_battler_runtime.sqlite3"

    report = CardBattlerRuntimeSchemaManager(runtime).prepare_startup()

    assert report.initialized is True
    assert report.schema_version == CARD_BATTLER_RUNTIME_SCHEMA_VERSION
    assert runtime.is_file()
    assert _digest(canonical) == canonical_digest
    assert _digest(model) == model_digest
    with sqlite3.connect(runtime) as connection:
        tables = {
            str(row[0])
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
    assert {
        "card_runtime_metadata",
        "card_sessions",
        "card_generations",
        "card_generation_outputs",
        "card_candidates",
    } <= tables


def test_validates_existing_runtime_without_writing(tmp_path: Path) -> None:
    runtime = tmp_path / "card_battler_runtime.sqlite3"
    manager = CardBattlerRuntimeSchemaManager(runtime)
    manager.prepare_startup()
    before = runtime.read_bytes()

    report = manager.prepare_startup()

    assert report.initialized is False
    assert report.schema_version == CARD_BATTLER_RUNTIME_SCHEMA_VERSION
    assert runtime.read_bytes() == before


def test_rejects_unknown_version_without_repair(tmp_path: Path) -> None:
    runtime = tmp_path / "card_battler_runtime.sqlite3"
    manager = CardBattlerRuntimeSchemaManager(runtime)
    manager.prepare_startup()
    with sqlite3.connect(runtime) as connection:
        connection.execute(
            "UPDATE card_runtime_metadata SET value = '99' "
            "WHERE key = 'schema_version'"
        )
        connection.commit()
    before = runtime.read_bytes()

    with pytest.raises(
        CardBattlerRuntimeSchemaError,
        match="Unsupported Card Battler runtime schema version",
    ):
        manager.prepare_startup()

    assert runtime.read_bytes() == before


def test_rejects_missing_columns_and_foreign_key_corruption(
    tmp_path: Path,
) -> None:
    missing = tmp_path / "missing.sqlite3"
    with sqlite3.connect(missing) as connection:
        connection.executescript(
            """
            CREATE TABLE card_runtime_metadata(key TEXT PRIMARY KEY, value TEXT);
            INSERT INTO card_runtime_metadata VALUES ('schema_version', '1');
            """
        )
    with pytest.raises(CardBattlerRuntimeSchemaError, match="is missing"):
        CardBattlerRuntimeSchemaManager(missing).validate()

    runtime = tmp_path / "foreign-key.sqlite3"
    manager = CardBattlerRuntimeSchemaManager(runtime)
    manager.prepare_startup()
    with sqlite3.connect(runtime) as connection:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO card_generation_outputs(
                image_uid, generation_uid, output_role, output_node_id,
                output_index, relative_path, content_hash
            ) VALUES ('image', 'missing', 'primary', '1', 0, 'x.png', 'hash')
            """
        )
        connection.commit()

    with pytest.raises(CardBattlerRuntimeSchemaError, match="foreign_key"):
        manager.validate()


def test_rejects_missing_runtime_on_read_only_validation(
    tmp_path: Path,
) -> None:
    with pytest.raises(CardBattlerRuntimeSchemaError, match="unavailable"):
        CardBattlerRuntimeSchemaManager(
            tmp_path / "missing.sqlite3"
        ).validate()
