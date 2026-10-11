"""Versioned schema owner for the isolated Card Battler POC runtime store."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from comfyreview.application.card_battler_runtime import (
    CardBattlerRuntimeSchemaError,
    CardBattlerRuntimeSchemaReport,
)
from comfyreview.repositories.sqlite.connection import connect_read_only

CARD_BATTLER_RUNTIME_SCHEMA_VERSION = 2

_SCHEMA_V2_SQL = """
PRAGMA foreign_keys = ON;

CREATE TABLE card_runtime_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE card_candidate_groups (
    group_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    kind TEXT NOT NULL CHECK (kind IN ('initial', 'development')),
    status TEXT NOT NULL CHECK (status IN (
        'queued', 'composing', 'generating', 'ready', 'partial_failure',
        'failed', 'completed', 'rejected'
    )),
    source_image_uid TEXT NOT NULL,
    source_content_hash TEXT NOT NULL,
    reference_image_uid TEXT NOT NULL,
    reference_content_hash TEXT NOT NULL,
    group_seed TEXT NOT NULL,
    semantic_profile_json TEXT,
    card_imprint_json TEXT,
    shared_stat_profile_key TEXT,
    shared_mechanic_key TEXT,
    source_card_id TEXT,
    source_card_revision INTEGER CHECK (
        source_card_revision IS NULL OR source_card_revision >= 1
    ),
    failure_category TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    CHECK (
        (semantic_profile_json IS NULL AND card_imprint_json IS NULL)
        OR
        (semantic_profile_json IS NOT NULL AND card_imprint_json IS NOT NULL)
    ),
    CHECK (
        (kind = 'initial' AND source_card_id IS NULL
            AND source_card_revision IS NULL)
        OR
        (kind = 'development' AND source_card_id IS NOT NULL
            AND source_card_revision IS NOT NULL)
    )
);

CREATE TABLE card_generations (
    generation_uid TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    prompt_id TEXT,
    prepared_request_json TEXT NOT NULL,
    compiled_workflow_json TEXT NOT NULL,
    workflow_hash TEXT NOT NULL,
    output_policy_json TEXT NOT NULL,
    output_bindings_json TEXT NOT NULL,
    failure_category TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE card_generation_outputs (
    image_uid TEXT PRIMARY KEY,
    generation_uid TEXT NOT NULL
        REFERENCES card_generations(generation_uid) ON DELETE CASCADE,
    output_role TEXT NOT NULL,
    output_node_id TEXT NOT NULL,
    output_index INTEGER NOT NULL CHECK (output_index >= 0),
    relative_path TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (generation_uid, output_node_id, output_index)
);

CREATE TABLE card_candidates (
    candidate_id TEXT PRIMARY KEY,
    group_id TEXT NOT NULL
        REFERENCES card_candidate_groups(group_id) ON DELETE CASCADE,
    group_revision INTEGER NOT NULL CHECK (group_revision >= 1),
    slot_index INTEGER NOT NULL CHECK (slot_index BETWEEN 0 AND 3),
    status TEXT NOT NULL CHECK (status IN (
        'queued', 'composing', 'submitted', 'completed', 'failed',
        'accepted', 'rejected'
    )),
    materialization_seed TEXT NOT NULL,
    materialization_revision TEXT NOT NULL,
    structured_card_spec_json TEXT,
    visual_recipe_json TEXT,
    presentation_json TEXT,
    presentation_status TEXT,
    presentation_error_category TEXT,
    development_result_json TEXT,
    generation_uid TEXT REFERENCES card_generations(generation_uid),
    recipe_hash TEXT,
    generation_policy_revision TEXT,
    failure_category TEXT,
    output_image_uid TEXT REFERENCES card_generation_outputs(image_uid),
    output_content_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (group_id, slot_index),
    CHECK (
        (output_image_uid IS NULL AND output_content_hash IS NULL)
        OR
        (output_image_uid IS NOT NULL AND output_content_hash IS NOT NULL)
    )
);

CREATE TABLE cards (
    card_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    source_image_uid TEXT NOT NULL,
    source_content_hash TEXT NOT NULL,
    semantic_profile_json TEXT NOT NULL,
    card_imprint_json TEXT NOT NULL,
    structured_card_spec_json TEXT NOT NULL,
    visual_recipe_json TEXT NOT NULL,
    presentation_json TEXT,
    presentation_status TEXT NOT NULL,
    presentation_error_category TEXT,
    active_image_uid TEXT NOT NULL
        REFERENCES card_generation_outputs(image_uid),
    active_content_hash TEXT NOT NULL,
    visual_tier INTEGER NOT NULL CHECK (visual_tier >= 1),
    accepted_group_id TEXT NOT NULL
        REFERENCES card_candidate_groups(group_id),
    accepted_candidate_id TEXT NOT NULL
        REFERENCES card_candidates(candidate_id),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE card_decks (
    deck_id TEXT PRIMARY KEY,
    revision INTEGER NOT NULL CHECK (revision >= 1),
    capacity INTEGER NOT NULL CHECK (capacity = 40),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE card_deck_entries (
    deck_id TEXT NOT NULL
        REFERENCES card_decks(deck_id) ON DELETE CASCADE,
    card_id TEXT NOT NULL REFERENCES cards(card_id) ON DELETE CASCADE,
    position INTEGER NOT NULL CHECK (position BETWEEN 0 AND 39),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (deck_id, card_id),
    UNIQUE (deck_id, position)
);

CREATE INDEX idx_card_candidate_groups_status
ON card_candidate_groups(status, created_at, group_id);

CREATE INDEX idx_card_candidates_group
ON card_candidates(group_id, slot_index);

CREATE INDEX idx_card_generations_prompt
ON card_generations(prompt_id);

INSERT INTO card_runtime_metadata(key, value)
VALUES ('schema_version', '2');

INSERT INTO card_decks(deck_id, revision, capacity)
VALUES ('poc-deck', 1, 40);
"""

_REQUIRED_COLUMNS = {
    "card_runtime_metadata": {"key", "value"},
    "card_candidate_groups": {
        "group_id",
        "revision",
        "kind",
        "status",
        "source_image_uid",
        "source_content_hash",
        "reference_image_uid",
        "reference_content_hash",
        "group_seed",
        "semantic_profile_json",
        "card_imprint_json",
        "shared_stat_profile_key",
        "shared_mechanic_key",
        "source_card_id",
        "source_card_revision",
        "failure_category",
        "created_at",
        "updated_at",
    },
    "card_candidates": {
        "candidate_id",
        "group_id",
        "group_revision",
        "slot_index",
        "status",
        "materialization_seed",
        "materialization_revision",
        "structured_card_spec_json",
        "visual_recipe_json",
        "presentation_json",
        "presentation_status",
        "presentation_error_category",
        "development_result_json",
        "generation_uid",
        "recipe_hash",
        "generation_policy_revision",
        "failure_category",
        "output_image_uid",
        "output_content_hash",
        "created_at",
        "updated_at",
    },
    "cards": {
        "card_id",
        "revision",
        "source_image_uid",
        "source_content_hash",
        "semantic_profile_json",
        "card_imprint_json",
        "structured_card_spec_json",
        "visual_recipe_json",
        "presentation_json",
        "presentation_status",
        "presentation_error_category",
        "active_image_uid",
        "active_content_hash",
        "visual_tier",
        "accepted_group_id",
        "accepted_candidate_id",
        "created_at",
        "updated_at",
    },
    "card_decks": {
        "deck_id",
        "revision",
        "capacity",
        "created_at",
        "updated_at",
    },
    "card_deck_entries": {
        "deck_id",
        "card_id",
        "position",
        "created_at",
    },
    "card_generations": {
        "generation_uid",
        "status",
        "prompt_id",
        "prepared_request_json",
        "compiled_workflow_json",
        "workflow_hash",
        "output_policy_json",
        "output_bindings_json",
        "failure_category",
        "created_at",
        "updated_at",
    },
    "card_generation_outputs": {
        "image_uid",
        "generation_uid",
        "output_role",
        "output_node_id",
        "output_index",
        "relative_path",
        "content_hash",
        "created_at",
    },
}


class CardBattlerRuntimeSchemaManager:
    """Create only a missing v2 store and reject unsupported existing files."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def prepare_startup(self) -> CardBattlerRuntimeSchemaReport:
        """Atomically create a missing store or validate the existing one."""
        if self._database_path.exists():
            return self.validate()
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self._database_path.with_name(
            f".{self._database_path.name}.{uuid4().hex}.tmp"
        )
        try:
            connection = sqlite3.connect(temporary)
            try:
                connection.executescript(_SCHEMA_V2_SQL)
                connection.commit()
            finally:
                connection.close()
            self._validate_path(temporary)
            os.replace(temporary, self._database_path)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
        return CardBattlerRuntimeSchemaReport(
            initialized=True,
            schema_version=CARD_BATTLER_RUNTIME_SCHEMA_VERSION,
        )

    def validate(self) -> CardBattlerRuntimeSchemaReport:
        """Validate identity, structure, integrity, and foreign keys read-only."""
        self._validate_path(self._database_path)
        return CardBattlerRuntimeSchemaReport(
            initialized=False,
            schema_version=CARD_BATTLER_RUNTIME_SCHEMA_VERSION,
        )

    @staticmethod
    def _validate_path(database_path: Path) -> None:
        try:
            connection = connect_read_only(database_path, rows=True)
        except (FileNotFoundError, sqlite3.Error) as error:
            raise CardBattlerRuntimeSchemaError(
                "Card Battler runtime database is unavailable"
            ) from error
        try:
            version_row = connection.execute(
                "SELECT value FROM card_runtime_metadata WHERE key = ?",
                ("schema_version",),
            ).fetchone()
            if version_row is None or str(version_row["value"]) != str(
                CARD_BATTLER_RUNTIME_SCHEMA_VERSION
            ):
                raise CardBattlerRuntimeSchemaError(
                    "Unsupported Card Battler runtime schema version"
                )
            for table, required in _REQUIRED_COLUMNS.items():
                rows = connection.execute(
                    f'PRAGMA table_info("{table}")'
                ).fetchall()
                actual = {str(row["name"]) for row in rows}
                missing = sorted(required - actual)
                if missing:
                    raise CardBattlerRuntimeSchemaError(
                        f"Card Battler runtime table {table} is missing: "
                        + ", ".join(missing)
                    )
            integrity = connection.execute("PRAGMA integrity_check").fetchone()
            if integrity is None or str(integrity[0]).lower() != "ok":
                raise CardBattlerRuntimeSchemaError(
                    "Card Battler runtime database failed integrity_check"
                )
            foreign_keys = connection.execute(
                "PRAGMA foreign_key_check"
            ).fetchall()
            if foreign_keys:
                raise CardBattlerRuntimeSchemaError(
                    "Card Battler runtime database failed foreign_key_check"
                )
        except CardBattlerRuntimeSchemaError:
            raise
        except sqlite3.Error as error:
            raise CardBattlerRuntimeSchemaError(
                "Card Battler runtime schema is invalid"
            ) from error
        finally:
            connection.close()
