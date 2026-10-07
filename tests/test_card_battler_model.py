"""Behavior tests for the external read-only Card Battler model resource."""

from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerModelNotFound,
    CardBattlerModelVersionUnsupported,
)
from comfyreview.repositories.sqlite.card_battler_model import (
    SqliteCardBattlerModelRepository,
)
from comfyreview.settings import load_settings


def _create_model_database(
    path: Path,
    *,
    database_name: str = "card_battler_model",
    schema_version: int = 3,
) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE semantic_vocabularies (
                id INTEGER PRIMARY KEY,
                vocabulary_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE rulesets (
                id INTEGER PRIMARY KEY,
                ruleset_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                semantic_vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                description TEXT NOT NULL
            );
            CREATE TABLE semantic_categories (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE semantic_concepts (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                category_id INTEGER NOT NULL
                    REFERENCES semantic_categories(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE semantic_aliases (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                alias TEXT NOT NULL,
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id)
            );
            CREATE TABLE world_styles (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                parent_style_id INTEGER REFERENCES world_styles(id),
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE card_classes (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE combat_roles (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE trait_lineages (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE rarities (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                max_traits INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE development_tiers (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                rarity_id INTEGER NOT NULL REFERENCES rarities(id),
                level INTEGER NOT NULL,
                ordinal INTEGER NOT NULL,
                next_tier_id INTEGER REFERENCES development_tiers(id),
                development_locked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE mechanic_templates (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                internal_name TEXT NOT NULL,
                description TEXT NOT NULL,
                base_weight_milli INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE visual_prompt_atoms (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                canonical_text TEXT NOT NULL,
                category TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            """
        )
        connection.executemany(
            "INSERT INTO schema_meta(key, value) VALUES (?, ?)",
            (
                ("database_name", database_name),
                ("schema_version", str(schema_version)),
                ("seed_version", "test-seed"),
                ("purpose", "test model"),
                ("authority", "deterministic test model"),
                ("audit_status", "fixture"),
            ),
        )
        connection.execute(
            """
            INSERT INTO semantic_vocabularies(
                id, vocabulary_key, version, status, description
            ) VALUES (1, 'image_semantics', 1, 'active', 'Fixture vocabulary')
            """
        )
        connection.executemany(
            """
            INSERT INTO rulesets(
                id, ruleset_key, version, name, status,
                semantic_vocabulary_id, description
            ) VALUES (?, 'prototype', ?, ?, ?, 1, ?)
            """,
            (
                (1, 2, "Prototype v2", "active", "Current rules"),
                (2, 1, "Prototype v1", "retired", "Prior rules"),
            ),
        )
        connection.execute(
            """
            INSERT INTO semantic_categories(
                id, vocabulary_id, key, name, description
            ) VALUES (1, 1, 'mood', 'Mood', 'Mood semantics')
            """
        )
        connection.executemany(
            """
            INSERT INTO semantic_concepts(
                id, vocabulary_id, category_id, key, name, description, active
            ) VALUES (?, 1, 1, ?, ?, ?, 1)
            """,
            (
                (2, "zeta", "Zeta", "Zeta concept"),
                (1, "alpha", "Alpha", "Alpha concept"),
            ),
        )
        connection.executemany(
            """
            INSERT INTO semantic_aliases(
                id, vocabulary_id, alias, concept_id
            ) VALUES (?, 1, ?, ?)
            """,
            (
                (1, "bright", 1),
                (2, "airy", 1),
                (3, "heavy", 2),
            ),
        )
        for table in (
            "world_styles",
            "card_classes",
            "combat_roles",
            "trait_lineages",
        ):
            if table == "world_styles":
                connection.executemany(
                    """
                    INSERT INTO world_styles(
                        id, ruleset_id, key, name, parent_style_id,
                        description, active
                    ) VALUES (?, 1, ?, ?, NULL, ?, 1)
                    """,
                    (
                        (2, "zeta", "Zeta", "Zeta definition"),
                        (1, "alpha", "Alpha", "Alpha definition"),
                    ),
                )
            else:
                connection.executemany(
                    f"""
                    INSERT INTO {table}(
                        id, ruleset_id, key, name, description, active
                    ) VALUES (?, 1, ?, ?, ?, 1)
                    """,
                    (
                        (2, "zeta", "Zeta", "Zeta definition"),
                        (1, "alpha", "Alpha", "Alpha definition"),
                    ),
                )
        connection.executemany(
            """
            INSERT INTO rarities(
                id, ruleset_id, key, name, ordinal, max_traits, active
            ) VALUES (?, 1, ?, ?, ?, 1, 1)
            """,
            (
                (1, "common", "Common", 1),
                (2, "rare", "Rare", 2),
            ),
        )
        connection.execute(
            """
            INSERT INTO development_tiers(
                id, ruleset_id, rarity_id, level, ordinal,
                next_tier_id, development_locked
            ) VALUES (2, 1, 2, 2, 2, NULL, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO development_tiers(
                id, ruleset_id, rarity_id, level, ordinal,
                next_tier_id, development_locked
            ) VALUES (1, 1, 1, 1, 1, 2, 0)
            """
        )
        connection.executemany(
            """
            INSERT INTO mechanic_templates(
                id, ruleset_id, key, internal_name, description,
                base_weight_milli, active
            ) VALUES (?, 1, ?, ?, ?, ?, 1)
            """,
            (
                (2, "zeta", "ZETA", "Zeta mechanic", 900),
                (1, "alpha", "ALPHA", "Alpha mechanic", 1100),
            ),
        )
        connection.executemany(
            """
            INSERT INTO visual_prompt_atoms(
                id, ruleset_id, key, canonical_text, category, active
            ) VALUES (?, 1, ?, ?, 'style', 1)
            """,
            (
                (2, "zeta", "zeta atom"),
                (1, "alpha", "alpha atom"),
            ),
        )
        connection.commit()
    finally:
        connection.close()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_settings_derive_model_path_from_configured_data_directory(
    tmp_path: Path,
) -> None:
    data_directory = tmp_path / "custom-data"

    settings = load_settings(
        base_directory=tmp_path,
        environ={"COMFYREVIEW_DATA_DIR": str(data_directory)},
    )

    assert (
        settings.card_battler_model_database_path
        == (data_directory / "card_battler.sqlite3").resolve()
    )
    assert not data_directory.exists()


def test_settings_respect_explicit_model_database_override(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "models" / "custom-card-model.sqlite3"

    settings = load_settings(
        base_directory=tmp_path,
        environ={
            "COMFYREVIEW_CARD_BATTLER_MODEL_DATABASE": str(model_path),
        },
    )

    assert settings.card_battler_model_database_path == model_path.resolve()
    assert not model_path.exists()


def test_valid_model_reads_metadata_ruleset_and_foundational_catalogs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)

    metadata = repository.metadata()
    active = repository.resolve_ruleset()
    retired = repository.resolve_ruleset(key="prototype", version=1)
    concepts = repository.semantic_concepts(active)
    styles = repository.world_styles(active)
    classes = repository.card_classes(active)
    roles = repository.combat_roles(active)
    lineages = repository.trait_lineages(active)
    tiers = repository.development_tiers(active)
    mechanics = repository.mechanic_templates(active)
    summary = repository.summary(active)

    assert (metadata.database_name, metadata.schema_version) == (
        "card_battler_model",
        3,
    )
    assert (active.key, active.version, active.status) == (
        "prototype",
        2,
        "active",
    )
    assert (retired.version, retired.status) == (1, "retired")
    assert [item.key for item in concepts] == ["alpha", "zeta"]
    assert concepts[0].aliases == ("airy", "bright")
    assert [item.key for item in styles] == ["alpha", "zeta"]
    assert [item.key for item in classes] == ["alpha", "zeta"]
    assert [item.key for item in roles] == ["alpha", "zeta"]
    assert [item.key for item in lineages] == ["alpha", "zeta"]
    assert [item.ordinal for item in tiers] == [1, 2]
    assert tiers[0].next_ordinal == 2
    assert [item.key for item in mechanics] == ["alpha", "zeta"]
    assert (
        summary.semantic_concept_count,
        summary.world_style_count,
        summary.card_class_count,
        summary.combat_role_count,
        summary.trait_lineage_count,
        summary.development_tier_count,
        summary.mechanic_template_count,
        summary.prompt_atom_count,
    ) == (2, 2, 2, 2, 2, 2, 2, 2)
    assert summary.integrity_ok is True
    assert summary.foreign_key_violation_count == 0


def test_missing_model_database_is_normalized(tmp_path: Path) -> None:
    repository = SqliteCardBattlerModelRepository(tmp_path / "missing.sqlite3")

    with pytest.raises(CardBattlerModelNotFound, match="does not exist"):
        repository.metadata()


def test_wrong_database_identity_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "wrong.sqlite3"
    _create_model_database(path, database_name="not_the_model")

    with pytest.raises(CardBattlerModelInvalid, match="unexpected database"):
        SqliteCardBattlerModelRepository(path).metadata()


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    _create_model_database(path, schema_version=99)

    with pytest.raises(
        CardBattlerModelVersionUnsupported,
        match="schema version 99",
    ):
        SqliteCardBattlerModelRepository(path).metadata()


def test_unsupported_schema_is_reported_before_v3_structure_checks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "future-layout.sqlite3"
    _create_model_database(path, schema_version=99)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE visual_prompt_atoms")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        CardBattlerModelVersionUnsupported,
        match="schema version 99",
    ):
        SqliteCardBattlerModelRepository(path).metadata()


def test_missing_foundational_table_is_rejected_without_repair(
    tmp_path: Path,
) -> None:
    path = tmp_path / "malformed.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE visual_prompt_atoms")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="visual_prompt_atoms"):
        SqliteCardBattlerModelRepository(path).metadata()

    connection = sqlite3.connect(path)
    try:
        table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'visual_prompt_atoms'
            """
        ).fetchone()
    finally:
        connection.close()
    assert table is None


def test_corrupt_sqlite_is_rejected_as_invalid(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"this is not a sqlite database")

    with pytest.raises(CardBattlerModelInvalid):
        SqliteCardBattlerModelRepository(path).metadata()


def test_foreign_key_violation_is_rejected_without_repair(
    tmp_path: Path,
) -> None:
    path = tmp_path / "broken-fk.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO card_classes(
                id, ruleset_id, key, name, description, active
            ) VALUES (99, 999, 'broken', 'Broken', 'Broken FK', 1)
            """
        )
        connection.commit()
    finally:
        connection.close()

    before = _digest(path)
    with pytest.raises(CardBattlerModelInvalid, match="foreign_key_check"):
        SqliteCardBattlerModelRepository(path).summary()
    assert _digest(path) == before


def test_catalog_reads_are_stably_ordered_and_read_only(
    tmp_path: Path,
) -> None:
    path = tmp_path / "stable.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)
    before = _digest(path)

    first = (
        repository.semantic_concepts(),
        repository.world_styles(),
        repository.card_classes(),
        repository.combat_roles(),
        repository.trait_lineages(),
        repository.development_tiers(),
        repository.mechanic_templates(),
        repository.summary(),
    )
    second = (
        repository.semantic_concepts(),
        repository.world_styles(),
        repository.card_classes(),
        repository.combat_roles(),
        repository.trait_lineages(),
        repository.development_tiers(),
        repository.mechanic_templates(),
        repository.summary(),
    )

    assert first == second
    assert _digest(path) == before
