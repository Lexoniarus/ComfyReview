"""Lifecycle owner for the canonical ComfyReview SQLite database."""

from __future__ import annotations

import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from comfyreview.application import CanonicalSchemaReport
from comfyreview.domain import (
    PromptAtomUsage,
    prompt_atom_usages_from_text,
    render_prompt_atom_usages,
)

SCHEMA_VERSION = 7
_MIN_UPGRADE_VERSION = 1

_SCHEMA_V1_SQL = r"""
PRAGMA foreign_keys = ON;

CREATE TABLE schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE prompt_atoms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    canonical_text TEXT NOT NULL UNIQUE
);

CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scope TEXT NOT NULL CHECK (scope IN ('pos', 'neg')),
    prompt_hash TEXT NOT NULL,
    text TEXT NOT NULL,
    UNIQUE (scope, prompt_hash)
);

CREATE TABLE prompt_memberships (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    prompt_id INTEGER NOT NULL
        REFERENCES prompts(id) ON DELETE CASCADE,
    atom_id INTEGER NOT NULL
        REFERENCES prompt_atoms(id),
    position INTEGER NOT NULL,
    weight_milli INTEGER NOT NULL,
    raw_text TEXT NOT NULL,
    UNIQUE (prompt_id, position)
);

CREATE INDEX idx_prompt_memberships_atom
    ON prompt_memberships(atom_id);

CREATE TABLE prompt_components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,
    component_key TEXT NOT NULL,
    name TEXT NOT NULL,
    tags TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (kind, component_key)
);

CREATE TABLE component_atoms (
    component_id INTEGER NOT NULL
        REFERENCES prompt_components(id) ON DELETE CASCADE,
    atom_id INTEGER NOT NULL
        REFERENCES prompt_atoms(id),
    scope TEXT NOT NULL CHECK (scope IN ('pos', 'neg')),
    position INTEGER NOT NULL,
    weight_milli INTEGER NOT NULL,
    locked INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (component_id, scope, position)
);

CREATE TABLE generations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generation_uid TEXT NOT NULL UNIQUE,
    model_branch TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    combo_key TEXT NOT NULL,
    seed INTEGER,
    steps INTEGER,
    cfg REAL,
    sampler TEXT,
    scheduler TEXT,
    denoise REAL,
    loras_json TEXT NOT NULL DEFAULT '[]',
    positive_prompt_id INTEGER NOT NULL
        REFERENCES prompts(id),
    negative_prompt_id INTEGER NOT NULL
        REFERENCES prompts(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_uid TEXT NOT NULL UNIQUE,
    generation_id INTEGER NOT NULL UNIQUE
        REFERENCES generations(id) ON DELETE CASCADE,
    png_path TEXT NOT NULL UNIQUE,
    json_path TEXT NOT NULL UNIQUE,
    last_seen_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE review_clock (
    singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
    value INTEGER NOT NULL
);

CREATE TABLE image_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_id INTEGER NOT NULL UNIQUE
        REFERENCES images(id) ON DELETE CASCADE,
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 10),
    version INTEGER NOT NULL UNIQUE,
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE deleted_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    generation_id INTEGER NOT NULL UNIQUE
        REFERENCES generations(id) ON DELETE CASCADE,
    png_path TEXT NOT NULL,
    json_path TEXT NOT NULL,
    version INTEGER NOT NULL UNIQUE,
    deleted_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE atom_learning_stats (
    atom_id INTEGER NOT NULL REFERENCES prompt_atoms(id),
    scope TEXT NOT NULL CHECK (scope IN ('pos', 'neg')),
    model_branch TEXT NOT NULL,
    weight_milli INTEGER NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    rating_sum REAL NOT NULL DEFAULT 0,
    rating_sq_sum REAL NOT NULL DEFAULT 0,
    deleted_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (atom_id, scope, model_branch, weight_milli)
);

CREATE TABLE render_learning_stats (
    model_branch TEXT NOT NULL,
    checkpoint TEXT NOT NULL,
    sampler TEXT NOT NULL,
    scheduler TEXT NOT NULL,
    steps INTEGER NOT NULL,
    cfg_milli INTEGER NOT NULL,
    denoise_milli INTEGER NOT NULL,
    sample_count INTEGER NOT NULL DEFAULT 0,
    rating_sum REAL NOT NULL DEFAULT 0,
    rating_sq_sum REAL NOT NULL DEFAULT 0,
    deleted_count INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (
        model_branch,
        checkpoint,
        sampler,
        scheduler,
        steps,
        cfg_milli,
        denoise_milli
    )
);

INSERT INTO schema_metadata(key, value)
VALUES ('schema_version', '1');

INSERT INTO review_clock(singleton_id, value)
VALUES (1, 0);

CREATE VIEW ratings AS
SELECT
    review.version AS id,
    image.png_path AS png_path,
    image.json_path AS json_path,
    review.version AS run,
    generation.model_branch AS model_branch,
    generation.checkpoint AS checkpoint,
    generation.combo_key AS combo_key,
    review.rating AS rating,
    0 AS deleted,
    1 AS rating_count,
    generation.steps AS steps,
    generation.cfg AS cfg,
    generation.sampler AS sampler,
    generation.scheduler AS scheduler,
    generation.denoise AS denoise,
    generation.loras_json AS loras_json,
    positive_prompt.text AS pos_prompt,
    negative_prompt.text AS neg_prompt
FROM image_reviews AS review
JOIN images AS image ON image.id = review.image_id
JOIN generations AS generation
    ON generation.id = image.generation_id
JOIN prompts AS positive_prompt
    ON positive_prompt.id = generation.positive_prompt_id
JOIN prompts AS negative_prompt
    ON negative_prompt.id = generation.negative_prompt_id
UNION ALL
SELECT
    deleted.version AS id,
    deleted.png_path AS png_path,
    deleted.json_path AS json_path,
    deleted.version AS run,
    generation.model_branch AS model_branch,
    generation.checkpoint AS checkpoint,
    generation.combo_key AS combo_key,
    NULL AS rating,
    1 AS deleted,
    1 AS rating_count,
    generation.steps AS steps,
    generation.cfg AS cfg,
    generation.sampler AS sampler,
    generation.scheduler AS scheduler,
    generation.denoise AS denoise,
    generation.loras_json AS loras_json,
    positive_prompt.text AS pos_prompt,
    negative_prompt.text AS neg_prompt
FROM deleted_images AS deleted
JOIN generations AS generation
    ON generation.id = deleted.generation_id
JOIN prompts AS positive_prompt
    ON positive_prompt.id = generation.positive_prompt_id
JOIN prompts AS negative_prompt
    ON negative_prompt.id = generation.negative_prompt_id;

CREATE VIEW tokens AS
WITH observations AS (
    SELECT
        review.version AS version,
        image.json_path AS json_path,
        generation.model_branch AS model_branch,
        review.rating AS rating,
        0 AS deleted,
        generation.positive_prompt_id AS positive_prompt_id,
        generation.negative_prompt_id AS negative_prompt_id
    FROM image_reviews AS review
    JOIN images AS image ON image.id = review.image_id
    JOIN generations AS generation
        ON generation.id = image.generation_id
    UNION ALL
    SELECT
        deleted_image.version AS version,
        deleted_image.json_path AS json_path,
        generation.model_branch AS model_branch,
        NULL AS rating,
        1 AS deleted,
        generation.positive_prompt_id AS positive_prompt_id,
        generation.negative_prompt_id AS negative_prompt_id
    FROM deleted_images AS deleted_image
    JOIN generations AS generation
        ON generation.id = deleted_image.generation_id
),
positive_tokens AS (
    SELECT
        observation.version * 100000 + membership.position * 2 + 1 AS id,
        observation.json_path AS json_path,
        observation.version AS run,
        observation.model_branch AS model_branch,
        'pos' AS scope,
        CASE
            WHEN membership.weight_milli = 1000
                THEN atom.canonical_text
            ELSE '(' || atom.canonical_text || ':' ||
                RTRIM(
                    RTRIM(
                        printf('%.3f', membership.weight_milli / 1000.0),
                        '0'
                    ),
                    '.'
                ) || ')'
        END AS token,
        observation.rating AS rating,
        observation.deleted AS deleted
    FROM observations AS observation
    JOIN prompt_memberships AS membership
        ON membership.prompt_id = observation.positive_prompt_id
    JOIN prompt_atoms AS atom ON atom.id = membership.atom_id
),
negative_tokens AS (
    SELECT
        observation.version * 100000 + membership.position * 2 AS id,
        observation.json_path AS json_path,
        observation.version AS run,
        observation.model_branch AS model_branch,
        'neg' AS scope,
        CASE
            WHEN membership.weight_milli = 1000
                THEN atom.canonical_text
            ELSE '(' || atom.canonical_text || ':' ||
                RTRIM(
                    RTRIM(
                        printf('%.3f', membership.weight_milli / 1000.0),
                        '0'
                    ),
                    '.'
                ) || ')'
        END AS token,
        observation.rating AS rating,
        observation.deleted AS deleted
    FROM observations AS observation
    JOIN prompt_memberships AS membership
        ON membership.prompt_id = observation.negative_prompt_id
    JOIN prompt_atoms AS atom ON atom.id = membership.atom_id
)
SELECT * FROM positive_tokens
UNION ALL
SELECT * FROM negative_tokens;
"""

_REQUIRED_OBJECTS_V1 = {
    "atom_learning_stats": "table",
    "component_atoms": "table",
    "deleted_images": "table",
    "generations": "table",
    "image_reviews": "table",
    "images": "table",
    "prompt_atoms": "table",
    "prompt_components": "table",
    "prompt_memberships": "table",
    "prompts": "table",
    "ratings": "view",
    "render_learning_stats": "table",
    "review_clock": "table",
    "schema_metadata": "table",
    "tokens": "view",
}

_REQUIRED_OBJECTS_V2 = {
    **_REQUIRED_OBJECTS_V1,
    "generation_sampler_stages": "table",
}

_REQUIRED_GENERATION_COLUMNS_V2 = {
    "source",
    "raw_metadata_json",
    "workflow_json",
    "workflow_hash",
    "comfy_prompt_id",
    "status",
    "submitted_at",
    "started_at",
    "completed_at",
}

_REQUIRED_OBJECTS_V3 = dict(_REQUIRED_OBJECTS_V2)
_REQUIRED_IMAGE_COLUMNS_V3 = {
    "id",
    "image_uid",
    "generation_id",
    "output_node_id",
    "output_index",
    "png_path",
    "json_path",
    "last_seen_at",
}
_REQUIRED_DELETED_IMAGE_COLUMNS_V3 = {
    "id",
    "image_uid",
    "generation_id",
    "png_path",
    "json_path",
    "version",
    "deleted_at",
}

_REQUIRED_OBJECTS_V4 = {
    **_REQUIRED_OBJECTS_V2,
    "arena_matches": "table",
    "curation_assignments": "table",
    "current_image_reviews": "view",
    "deleted_images": "view",
    "image_review_summary": "view",
    "image_reviews": "view",
    "review_events": "table",
}
_REQUIRED_IMAGE_COLUMNS_V4 = _REQUIRED_IMAGE_COLUMNS_V3 | {"deleted_at"}
_REQUIRED_REVIEW_EVENT_COLUMNS_V4 = {
    "id",
    "event_uid",
    "image_id",
    "event_type",
    "rating",
    "source",
    "source_key",
    "sequence",
    "source_created_at",
    "created_at",
}

_REQUIRED_OBJECTS_V5 = {
    **_REQUIRED_OBJECTS_V4,
    "legacy_prompt_component_sources": "table",
    "prompt_composition_revisions": "table",
    "prompt_compositions": "table",
    "prompt_revisions": "table",
}
_REQUIRED_PROMPT_COMPONENT_COLUMNS_V5 = {
    "id",
    "component_uid",
    "kind",
    "component_key",
    "name",
    "tags",
    "notes",
    "archived_at",
    "created_at",
    "updated_at",
}
_REQUIRED_PROMPT_REVISION_COLUMNS_V5 = {
    "id",
    "revision_uid",
    "component_id",
    "revision_number",
    "positive_text",
    "negative_text",
    "content_hash",
    "created_at",
}

_REQUIRED_OBJECTS_V6 = dict(_REQUIRED_OBJECTS_V5)
_REQUIRED_IMAGE_COLUMNS_V6 = _REQUIRED_IMAGE_COLUMNS_V4 | {
    "content_hash",
    "output_role",
}

_REQUIRED_OBJECTS_V7 = {
    **_REQUIRED_OBJECTS_V6,
    "prompt_revision_atom_usages": "table",
}
_REQUIRED_REVISION_ATOM_COLUMNS_V7 = {
    "revision_id",
    "atom_id",
    "scope",
    "position",
    "weight_milli",
}


class CanonicalSchemaValidationError(RuntimeError):
    """Signal an unsupported or corrupt canonical database."""


class CanonicalSchemaManager:
    """Validate, initialize, and explicitly upgrade the canonical database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def prepare_startup(self) -> CanonicalSchemaReport:
        """Validate or atomically create the current canonical schema."""
        if self._database_path.exists():
            self._validate_existing()
            return CanonicalSchemaReport(schema_version=SCHEMA_VERSION)
        self._create_new_database()
        return CanonicalSchemaReport(
            initialized=True,
            schema_version=SCHEMA_VERSION,
        )

    def validate(self) -> CanonicalSchemaReport:
        """Validate the existing canonical database without mutating it."""
        if not self._database_path.exists():
            raise CanonicalSchemaValidationError(
                f"Canonical database does not exist: {self._database_path}"
            )
        self._validate_existing()
        return CanonicalSchemaReport(schema_version=SCHEMA_VERSION)

    def upgrade(
        self,
        backup_directory: Path | None = None,
    ) -> CanonicalSchemaReport:
        """Back up and explicitly upgrade a supported older schema."""
        if not self._database_path.exists():
            self._create_new_database()
            return CanonicalSchemaReport(
                initialized=True,
                schema_version=SCHEMA_VERSION,
            )

        current_version = self._read_existing_version()
        if current_version == SCHEMA_VERSION:
            self._validate_existing()
            return CanonicalSchemaReport(schema_version=SCHEMA_VERSION)
        if current_version not in {1, 2, 3, 4, 5, 6}:
            raise CanonicalSchemaValidationError(
                "Unsupported canonical schema version "
                f"{current_version}; expected 1, 2, 3, 4, 5, 6, or "
                f"{SCHEMA_VERSION}"
            )

        if current_version == _MIN_UPGRADE_VERSION:
            self._validate_version_one()
        elif current_version == 2:
            self._validate_version_two()
        elif current_version == 3:
            self._validate_version_three()
        elif current_version == 4:
            self._validate_version_four()
        elif current_version == 5:
            self._validate_version_five()
        else:
            self._validate_version_six()

        backup_path = self._create_backup(backup_directory)
        committed = False
        try:
            connection = self._open_read_write(foreign_keys=False)
            try:
                connection.execute("BEGIN IMMEDIATE")
                if current_version == _MIN_UPGRADE_VERSION:
                    self._upgrade_v1_to_v2(connection)
                if current_version <= 2:
                    self._upgrade_v2_to_v3(connection)
                if current_version <= 3:
                    self._upgrade_v3_to_v4(connection)
                if current_version <= 4:
                    self._upgrade_v4_to_v5(connection)
                if current_version <= 5:
                    self._upgrade_v5_to_v6(connection)
                self._upgrade_v6_to_v7(connection)
                connection.commit()
                committed = True
                connection.execute("PRAGMA foreign_keys = ON")
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            self._validate_existing()
        except Exception:
            if committed or not self._is_valid_version(current_version):
                self._restore_backup(backup_path)
            raise

        return CanonicalSchemaReport(
            schema_version=SCHEMA_VERSION,
            upgraded_from=current_version,
            backup_path=backup_path,
        )

    def _create_new_database(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._database_path.with_name(
            f".{self._database_path.name}.{uuid4().hex}.tmp"
        )
        try:
            connection = sqlite3.connect(temporary_path)
            try:
                connection.executescript(_SCHEMA_V1_SQL)
                connection.execute(
                    f"PRAGMA user_version = {_MIN_UPGRADE_VERSION}"
                )
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v1_to_v2(connection)
                connection.commit()
                connection.execute("PRAGMA foreign_keys = OFF")
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v2_to_v3(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v3_to_v4(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v4_to_v5(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v5_to_v6(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v6_to_v7(connection)
                connection.commit()
                connection.execute("PRAGMA foreign_keys = ON")
                self._validate_connection(connection)
            finally:
                connection.close()
            os.replace(temporary_path, self._database_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _validate_existing(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version in {1, 2, 3, 4, 5, 6}:
                raise CanonicalSchemaValidationError(
                    f"Canonical schema version {version} requires an "
                    "explicit upgrade; run "
                    "`python -m comfyreview canonical-db upgrade`"
                )
            self._validate_connection(connection)
        finally:
            connection.close()

    def _validate_version_one(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != _MIN_UPGRADE_VERSION:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 1 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(
                connection,
                _REQUIRED_OBJECTS_V1,
            )
            self._validate_metadata_version(
                connection,
                _MIN_UPGRADE_VERSION,
            )
        finally:
            connection.close()

    def _validate_version_two(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 2:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 2 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(
                connection,
                _REQUIRED_OBJECTS_V2,
            )
            self._validate_metadata_version(
                connection,
                2,
            )
            self._validate_generation_columns(connection)
        finally:
            connection.close()

    def _validate_version_three(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 3:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 3 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V3)
            self._validate_metadata_version(connection, 3)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v3(connection)
        finally:
            connection.close()

    def _validate_version_four(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 4:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 4 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V4)
            self._validate_metadata_version(connection, 4)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v4(connection)
        finally:
            connection.close()

    def _validate_version_five(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 5:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 5 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V5)
            self._validate_metadata_version(connection, 5)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v4(connection)
            self._validate_prompt_catalog_v5(connection)
        finally:
            connection.close()

    def _validate_version_six(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 6:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 6 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V6)
            self._validate_metadata_version(connection, 6)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v6(connection)
            self._validate_prompt_catalog_v5(connection)
        finally:
            connection.close()

    def _validate_connection(self, connection: sqlite3.Connection) -> None:
        version = self._schema_version(connection)
        if version != SCHEMA_VERSION:
            raise CanonicalSchemaValidationError(
                "Unsupported canonical schema version "
                f"{version}; expected {SCHEMA_VERSION}"
            )
        self._validate_integrity(connection)
        self._validate_required_objects(connection, _REQUIRED_OBJECTS_V7)
        self._validate_metadata_version(connection, SCHEMA_VERSION)
        self._validate_generation_columns(connection)
        self._validate_output_identity_v6(connection)
        self._validate_prompt_catalog_v5(connection)
        self._validate_prompt_catalog_v7(connection)

    def _upgrade_v1_to_v2(self, connection: sqlite3.Connection) -> None:
        statements = (
            "ALTER TABLE generations ADD COLUMN source TEXT NOT NULL "
            "DEFAULT 'legacy_sidecar'",
            "ALTER TABLE generations ADD COLUMN raw_metadata_json TEXT",
            "ALTER TABLE generations ADD COLUMN workflow_json TEXT",
            "ALTER TABLE generations ADD COLUMN workflow_hash TEXT",
            "ALTER TABLE generations ADD COLUMN comfy_prompt_id TEXT",
            "ALTER TABLE generations ADD COLUMN status TEXT NOT NULL "
            "DEFAULT 'completed'",
            "ALTER TABLE generations ADD COLUMN submitted_at TEXT",
            "ALTER TABLE generations ADD COLUMN started_at TEXT",
            "ALTER TABLE generations ADD COLUMN completed_at TEXT",
        )
        for statement in statements:
            connection.execute(statement)
        connection.execute(
            """
            CREATE TABLE generation_sampler_stages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                generation_id INTEGER NOT NULL
                    REFERENCES generations(id) ON DELETE CASCADE,
                node_id TEXT NOT NULL,
                stage_order INTEGER NOT NULL,
                role TEXT NOT NULL DEFAULT '',
                seed INTEGER,
                steps INTEGER,
                cfg REAL,
                sampler TEXT,
                scheduler TEXT,
                denoise REAL,
                source TEXT NOT NULL DEFAULT 'workflow_graph',
                UNIQUE (generation_id, node_id)
            )
            """
        )
        connection.execute(
            "CREATE INDEX idx_generation_sampler_stages_generation "
            "ON generation_sampler_stages(generation_id, stage_order)"
        )
        connection.execute(
            "CREATE INDEX idx_generations_workflow_hash "
            "ON generations(workflow_hash)"
        )
        connection.execute(
            "CREATE UNIQUE INDEX ux_generations_comfy_prompt_id "
            "ON generations(comfy_prompt_id) "
            "WHERE comfy_prompt_id IS NOT NULL"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = ? "
            "WHERE key = 'schema_version'",
            ("2",),
        )
        connection.execute("PRAGMA user_version = 2")

    def _upgrade_v2_to_v3(self, connection: sqlite3.Connection) -> None:
        views = self._capture_compatibility_views(connection)
        connection.execute("DROP VIEW ratings")
        connection.execute("DROP VIEW tokens")
        connection.execute(
            """
            CREATE TABLE images_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_uid TEXT NOT NULL UNIQUE,
                generation_id INTEGER NOT NULL
                    REFERENCES generations(id) ON DELETE CASCADE,
                output_node_id TEXT NOT NULL DEFAULT 'legacy_sidecar',
                output_index INTEGER NOT NULL DEFAULT 0,
                png_path TEXT NOT NULL UNIQUE,
                json_path TEXT UNIQUE,
                last_seen_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (generation_id, output_node_id, output_index)
            )
            """
        )
        connection.execute(
            """
            INSERT INTO images_v3(
                id,
                image_uid,
                generation_id,
                output_node_id,
                output_index,
                png_path,
                json_path,
                last_seen_at
            )
            SELECT
                id,
                image_uid,
                generation_id,
                'legacy_sidecar',
                0,
                png_path,
                json_path,
                last_seen_at
            FROM images
            """
        )
        connection.execute(
            """
            CREATE TABLE deleted_images_v3 (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_uid TEXT NOT NULL UNIQUE,
                generation_id INTEGER NOT NULL
                    REFERENCES generations(id) ON DELETE CASCADE,
                png_path TEXT NOT NULL,
                json_path TEXT,
                version INTEGER NOT NULL UNIQUE,
                deleted_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            INSERT INTO deleted_images_v3(
                id,
                image_uid,
                generation_id,
                png_path,
                json_path,
                version,
                deleted_at
            )
            SELECT
                deleted.id,
                generation.generation_uid,
                deleted.generation_id,
                deleted.png_path,
                deleted.json_path,
                deleted.version,
                deleted.deleted_at
            FROM deleted_images AS deleted
            JOIN generations AS generation
                ON generation.id = deleted.generation_id
            """
        )
        connection.execute("DROP TABLE deleted_images")
        connection.execute("DROP TABLE images")
        connection.execute("ALTER TABLE images_v3 RENAME TO images")
        connection.execute(
            "ALTER TABLE deleted_images_v3 RENAME TO deleted_images"
        )
        connection.execute(
            "CREATE INDEX idx_images_generation ON images(generation_id)"
        )
        connection.execute(
            "CREATE INDEX idx_deleted_images_generation "
            "ON deleted_images(generation_id)"
        )
        for name in ("ratings", "tokens"):
            connection.execute(views[name])
        connection.execute(
            "UPDATE schema_metadata SET value = ? "
            "WHERE key = 'schema_version'",
            ("3",),
        )
        connection.execute("PRAGMA user_version = 3")

    def _upgrade_v3_to_v4(self, connection: sqlite3.Connection) -> None:
        compatibility_views = self._capture_compatibility_views(connection)
        connection.execute("DROP VIEW ratings")
        connection.execute("DROP VIEW tokens")
        connection.execute(
            "ALTER TABLE image_reviews RENAME TO image_reviews_v3"
        )
        connection.execute(
            "ALTER TABLE deleted_images RENAME TO deleted_images_v3"
        )
        connection.execute("ALTER TABLE images ADD COLUMN deleted_at TEXT")
        connection.execute(
            """
            CREATE TABLE review_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_uid TEXT NOT NULL UNIQUE,
                image_id INTEGER NOT NULL
                    REFERENCES images(id) ON DELETE CASCADE,
                event_type TEXT NOT NULL
                    CHECK (event_type IN ('rating', 'delete', 'restore')),
                rating INTEGER CHECK (
                    (event_type = 'rating' AND rating BETWEEN 1 AND 10)
                    OR (event_type != 'rating' AND rating IS NULL)
                ),
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                sequence INTEGER NOT NULL UNIQUE,
                source_created_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (source, source_key)
            )
            """
        )
        connection.execute(
            "CREATE INDEX idx_review_events_image_sequence "
            "ON review_events(image_id, sequence)"
        )
        connection.execute(
            """
            CREATE TABLE arena_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                match_uid TEXT NOT NULL UNIQUE,
                left_image_id INTEGER NOT NULL
                    REFERENCES images(id),
                right_image_id INTEGER NOT NULL
                    REFERENCES images(id),
                winner_image_id INTEGER REFERENCES images(id),
                decision TEXT NOT NULL
                    CHECK (decision IN ('left', 'right', 'skip')),
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                source_created_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK (left_image_id != right_image_id),
                CHECK (
                    (decision = 'skip' AND winner_image_id IS NULL)
                    OR (
                        decision != 'skip'
                        AND winner_image_id IN (
                            left_image_id,
                            right_image_id
                        )
                    )
                ),
                UNIQUE (source, source_key)
            )
            """
        )
        connection.execute(
            "CREATE INDEX idx_arena_matches_images "
            "ON arena_matches(left_image_id, right_image_id)"
        )
        connection.execute(
            """
            CREATE TABLE curation_assignments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                image_id INTEGER NOT NULL UNIQUE
                    REFERENCES images(id) ON DELETE CASCADE,
                set_key TEXT NOT NULL,
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                source_created_at TEXT,
                assigned_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (source, source_key)
            )
            """
        )
        connection.execute(
            "CREATE INDEX idx_curation_assignments_set "
            "ON curation_assignments(set_key, image_id)"
        )
        connection.execute(
            """
            INSERT INTO images(
                image_uid,
                generation_id,
                output_node_id,
                output_index,
                png_path,
                json_path,
                last_seen_at,
                deleted_at
            )
            SELECT
                deleted.image_uid,
                deleted.generation_id,
                'legacy_deleted',
                deleted.version,
                deleted.png_path,
                deleted.json_path,
                deleted.deleted_at,
                deleted.deleted_at
            FROM deleted_images_v3 AS deleted
            WHERE NOT EXISTS (
                SELECT 1
                FROM images AS image
                WHERE image.image_uid = deleted.image_uid
            )
            """
        )
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid,
                image_id,
                event_type,
                rating,
                source,
                source_key,
                sequence,
                source_created_at,
                created_at
            )
            SELECT
                'canonical-v3-rating-' || review.id,
                review.image_id,
                'rating',
                review.rating,
                'canonical_v3',
                'image-review:' || review.id,
                review.version,
                review.updated_at,
                review.updated_at
            FROM image_reviews_v3 AS review
            """
        )
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid,
                image_id,
                event_type,
                rating,
                source,
                source_key,
                sequence,
                source_created_at,
                created_at
            )
            SELECT
                'canonical-v3-delete-' || deleted.id,
                image.id,
                'delete',
                NULL,
                'canonical_v3',
                'deleted-image:' || deleted.id,
                deleted.version,
                deleted.deleted_at,
                deleted.deleted_at
            FROM deleted_images_v3 AS deleted
            JOIN images AS image
                ON image.image_uid = deleted.image_uid
            """
        )
        connection.execute(
            """
            UPDATE review_clock
            SET value = MAX(
                value,
                COALESCE((SELECT MAX(sequence) FROM review_events), 0)
            )
            WHERE singleton_id = 1
            """
        )
        connection.execute("DROP TABLE image_reviews_v3")
        connection.execute("DROP TABLE deleted_images_v3")
        self._create_review_views(connection)
        for name in ("ratings", "tokens"):
            connection.execute(compatibility_views[name])
        connection.execute(
            "UPDATE schema_metadata SET value = ? "
            "WHERE key = 'schema_version'",
            ("4",),
        )
        connection.execute("PRAGMA user_version = 4")

    @staticmethod
    def _upgrade_v4_to_v5(connection: sqlite3.Connection) -> None:
        connection.execute(
            "ALTER TABLE prompt_components ADD COLUMN component_uid TEXT"
        )
        connection.execute(
            "UPDATE prompt_components "
            "SET component_uid = 'canonical-v4-component-' || id"
        )
        connection.execute(
            "CREATE UNIQUE INDEX ux_prompt_components_uid "
            "ON prompt_components(component_uid)"
        )
        connection.execute(
            "ALTER TABLE prompt_components ADD COLUMN archived_at TEXT"
        )
        connection.execute(
            """
            CREATE TABLE prompt_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                revision_uid TEXT NOT NULL UNIQUE,
                component_id INTEGER NOT NULL
                    REFERENCES prompt_components(id) ON DELETE CASCADE,
                revision_number INTEGER NOT NULL,
                positive_text TEXT NOT NULL DEFAULT '',
                negative_text TEXT NOT NULL DEFAULT '',
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (component_id, revision_number),
                UNIQUE (component_id, content_hash)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE prompt_compositions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                composition_uid TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE prompt_composition_revisions (
                composition_id INTEGER NOT NULL
                    REFERENCES prompt_compositions(id) ON DELETE CASCADE,
                revision_id INTEGER NOT NULL REFERENCES prompt_revisions(id),
                slot TEXT NOT NULL,
                position INTEGER NOT NULL,
                PRIMARY KEY (composition_id, slot, position),
                UNIQUE (composition_id, revision_id, slot)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE legacy_prompt_component_sources (
                component_id INTEGER NOT NULL
                    REFERENCES prompt_components(id) ON DELETE CASCADE,
                source TEXT NOT NULL,
                source_key TEXT NOT NULL,
                PRIMARY KEY (source, source_key),
                UNIQUE (component_id, source)
            )
            """
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN prompt_composition_id "
            "INTEGER REFERENCES prompt_compositions(id)"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '5' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 5")

    @staticmethod
    def _upgrade_v5_to_v6(connection: sqlite3.Connection) -> None:
        connection.execute(
            "ALTER TABLE images ADD COLUMN output_role TEXT NOT NULL "
            "DEFAULT 'primary'"
        )
        connection.execute("ALTER TABLE images ADD COLUMN content_hash TEXT")
        connection.execute(
            "UPDATE schema_metadata SET value = '6' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 6")

    @staticmethod
    def _upgrade_v6_to_v7(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE prompt_revision_atom_usages (
                revision_id INTEGER NOT NULL
                    REFERENCES prompt_revisions(id) ON DELETE CASCADE,
                atom_id INTEGER NOT NULL REFERENCES prompt_atoms(id),
                scope TEXT NOT NULL CHECK (scope IN ('pos', 'neg')),
                position INTEGER NOT NULL,
                weight_milli INTEGER NOT NULL CHECK (weight_milli > 0),
                PRIMARY KEY (revision_id, scope, position)
            )
            """
        )
        rows = connection.execute(
            """
            SELECT id, positive_text, negative_text
            FROM prompt_revisions
            ORDER BY id
            """
        ).fetchall()
        for revision_id, positive_text, negative_text in rows:
            for scope, snapshot in (
                ("pos", str(positive_text or "")),
                ("neg", str(negative_text or "")),
            ):
                usages = prompt_atom_usages_from_text(snapshot)
                if (
                    prompt_atom_usages_from_text(
                        render_prompt_atom_usages(usages)
                    )
                    != usages
                ):
                    raise CanonicalSchemaValidationError(
                        "prompt revision atom roundtrip failed"
                    )
                for position, usage in enumerate(usages):
                    connection.execute(
                        "INSERT OR IGNORE INTO prompt_atoms(canonical_text) "
                        "VALUES (?)",
                        (usage.text,),
                    )
                    atom_row = connection.execute(
                        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                        (usage.text,),
                    ).fetchone()
                    connection.execute(
                        """
                        INSERT INTO prompt_revision_atom_usages(
                            revision_id, atom_id, scope, position, weight_milli
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            int(revision_id),
                            int(atom_row[0]),
                            scope,
                            position,
                            usage.weight_milli,
                        ),
                    )
        connection.execute(
            "UPDATE schema_metadata SET value = '7' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 7")

    @staticmethod
    def _create_review_views(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE VIEW current_image_reviews AS
            WITH boundaries AS (
                SELECT
                    image_id,
                    COALESCE(MAX(sequence), 0) AS sequence
                FROM review_events
                WHERE event_type IN ('delete', 'restore')
                GROUP BY image_id
            ),
            current_ratings AS (
                SELECT event.*
                FROM review_events AS event
                LEFT JOIN boundaries AS boundary
                    ON boundary.image_id = event.image_id
                WHERE event.event_type = 'rating'
                  AND event.sequence > COALESCE(boundary.sequence, 0)
            )
            SELECT
                event.id AS event_id,
                event.image_id,
                event.rating,
                event.sequence,
                COALESCE(event.source_created_at, event.created_at)
                    AS reviewed_at
            FROM current_ratings AS event
            WHERE event.sequence = (
                SELECT MAX(candidate.sequence)
                FROM current_ratings AS candidate
                WHERE candidate.image_id = event.image_id
            )
            """
        )
        connection.execute(
            """
            CREATE VIEW image_reviews AS
            SELECT
                event_id AS id,
                image_id,
                rating,
                sequence AS version,
                reviewed_at AS updated_at
            FROM current_image_reviews
            """
        )
        connection.execute(
            """
            CREATE VIEW deleted_images AS
            SELECT
                event.id AS id,
                image.image_uid,
                image.generation_id,
                image.png_path,
                image.json_path,
                event.sequence AS version,
                image.deleted_at
            FROM images AS image
            JOIN review_events AS event
                ON event.image_id = image.id
               AND event.event_type = 'delete'
            WHERE image.deleted_at IS NOT NULL
              AND event.sequence = (
                  SELECT MAX(candidate.sequence)
                  FROM review_events AS candidate
                  WHERE candidate.image_id = image.id
                    AND candidate.event_type = 'delete'
              )
            """
        )
        connection.execute(
            """
            CREATE VIEW image_review_summary AS
            SELECT
                image.id AS image_id,
                image.image_uid,
                current.rating AS current_rating,
                COUNT(event.id) AS rating_count,
                COALESCE(SUM(event.rating), 0) AS rating_sum,
                AVG(event.rating) AS average_rating,
                MAX(event.sequence) AS latest_rating_sequence,
                image.deleted_at
            FROM images AS image
            LEFT JOIN current_image_reviews AS current
                ON current.image_id = image.id
            LEFT JOIN review_events AS event
                ON event.image_id = image.id
               AND event.event_type = 'rating'
            GROUP BY image.id
            """
        )

    @staticmethod
    def _capture_compatibility_views(
        connection: sqlite3.Connection,
    ) -> dict[str, str]:
        rows = connection.execute(
            "SELECT name, sql FROM sqlite_master "
            "WHERE type = 'view' AND name IN ('ratings', 'tokens')"
        ).fetchall()
        views = {str(name): str(sql) for name, sql in rows if sql is not None}
        if set(views) != {"ratings", "tokens"}:
            raise CanonicalSchemaValidationError(
                "Canonical compatibility views are incomplete"
            )
        return views

    def _read_existing_version(self) -> int:
        connection = self._open_read_only()
        try:
            return self._schema_version(connection)
        finally:
            connection.close()

    def _open_read_only(self) -> sqlite3.Connection:
        try:
            return sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=ro",
                uri=True,
            )
        except sqlite3.Error as error:
            raise CanonicalSchemaValidationError(
                f"Cannot open canonical database: {error}"
            ) from error

    def _open_read_write(
        self,
        *,
        foreign_keys: bool = True,
    ) -> sqlite3.Connection:
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=rw",
                uri=True,
            )
        except sqlite3.Error as error:
            raise CanonicalSchemaValidationError(
                f"Cannot open canonical database: {error}"
            ) from error
        connection.execute(
            "PRAGMA foreign_keys = " + ("ON" if foreign_keys else "OFF")
        )
        return connection

    @staticmethod
    def _schema_version(connection: sqlite3.Connection) -> int:
        row = connection.execute("PRAGMA user_version").fetchone()
        return int(row[0]) if row else 0

    @staticmethod
    def _validate_integrity(connection: sqlite3.Connection) -> None:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise CanonicalSchemaValidationError(
                "Canonical database integrity_check failed"
            )
        foreign_key_issue = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchone()
        if foreign_key_issue is not None:
            raise CanonicalSchemaValidationError(
                "Canonical database foreign_key_check failed"
            )

    @staticmethod
    def _validate_required_objects(
        connection: sqlite3.Connection,
        required_objects: dict[str, str],
    ) -> None:
        rows = connection.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table', 'view')"
        ).fetchall()
        objects = {str(name): str(object_type) for name, object_type in rows}
        missing = [
            name
            for name, object_type in required_objects.items()
            if objects.get(name) != object_type
        ]
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical database is missing required objects: "
                + ", ".join(sorted(missing))
            )

    @staticmethod
    def _validate_metadata_version(
        connection: sqlite3.Connection,
        expected_version: int,
    ) -> None:
        row = connection.execute(
            "SELECT value FROM schema_metadata WHERE key = 'schema_version'"
        ).fetchone()
        actual = int(row[0]) if row else 0
        if actual != expected_version:
            raise CanonicalSchemaValidationError(
                "Canonical schema metadata version "
                f"{actual}; expected {expected_version}"
            )

    @staticmethod
    def _validate_generation_columns(connection: sqlite3.Connection) -> None:
        columns = {
            str(row[1])
            for row in connection.execute(
                "PRAGMA table_info(generations)"
            ).fetchall()
        }
        missing = sorted(_REQUIRED_GENERATION_COLUMNS_V2 - columns)
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical generations table is missing required columns: "
                + ", ".join(missing)
            )

    @classmethod
    def _validate_output_identity_v3(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        image_columns = cls._table_column_rows(connection, "images")
        deleted_columns = cls._table_column_rows(
            connection,
            "deleted_images",
        )
        missing_images = sorted(
            _REQUIRED_IMAGE_COLUMNS_V3 - image_columns.keys()
        )
        missing_deleted = sorted(
            _REQUIRED_DELETED_IMAGE_COLUMNS_V3 - deleted_columns.keys()
        )
        if missing_images or missing_deleted:
            missing = missing_images + missing_deleted
            raise CanonicalSchemaValidationError(
                "Canonical output tables are missing required columns: "
                + ", ".join(missing)
            )
        if int(str(image_columns["json_path"][3])) != 0:
            raise CanonicalSchemaValidationError(
                "images.json_path must be nullable in schema version 3"
            )
        if int(str(deleted_columns["json_path"][3])) != 0:
            raise CanonicalSchemaValidationError(
                "deleted_images.json_path must be nullable in schema version 3"
            )

        unique_indexes = cls._unique_index_columns(connection, "images")
        if ("generation_id",) in unique_indexes:
            raise CanonicalSchemaValidationError(
                "images.generation_id must not be unique"
            )
        expected_output_key = (
            "generation_id",
            "output_node_id",
            "output_index",
        )
        if expected_output_key not in unique_indexes:
            raise CanonicalSchemaValidationError(
                "images is missing its generation output-slot constraint"
            )
        deleted_unique = cls._unique_index_columns(
            connection,
            "deleted_images",
        )
        if ("image_uid",) not in deleted_unique:
            raise CanonicalSchemaValidationError(
                "deleted_images.image_uid must be unique"
            )

    @classmethod
    def _validate_output_identity_v4(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        image_columns = cls._table_column_rows(connection, "images")
        event_columns = cls._table_column_rows(connection, "review_events")
        missing_images = sorted(
            _REQUIRED_IMAGE_COLUMNS_V4 - image_columns.keys()
        )
        missing_events = sorted(
            _REQUIRED_REVIEW_EVENT_COLUMNS_V4 - event_columns.keys()
        )
        if missing_images or missing_events:
            raise CanonicalSchemaValidationError(
                "Canonical review tables are missing required columns: "
                + ", ".join(missing_images + missing_events)
            )
        if int(str(image_columns["json_path"][3])) != 0:
            raise CanonicalSchemaValidationError(
                "images.json_path must be nullable in schema version 4"
            )
        expected_output_key = (
            "generation_id",
            "output_node_id",
            "output_index",
        )
        if expected_output_key not in cls._unique_index_columns(
            connection,
            "images",
        ):
            raise CanonicalSchemaValidationError(
                "images is missing its generation output-slot constraint"
            )
        event_indexes = cls._unique_index_columns(
            connection,
            "review_events",
        )
        for expected in (("event_uid",), ("source", "source_key")):
            if expected not in event_indexes:
                raise CanonicalSchemaValidationError(
                    "review_events is missing canonical identity constraints"
                )

    @classmethod
    def _validate_output_identity_v6(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        cls._validate_output_identity_v4(connection)
        image_columns = cls._table_column_rows(connection, "images")
        missing = sorted(_REQUIRED_IMAGE_COLUMNS_V6 - image_columns.keys())
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical outputs are missing required columns: "
                + ", ".join(missing)
            )

    @classmethod
    def _validate_prompt_catalog_v5(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        component_columns = cls._table_column_rows(
            connection,
            "prompt_components",
        )
        revision_columns = cls._table_column_rows(
            connection,
            "prompt_revisions",
        )
        generation_columns = cls._table_column_rows(
            connection,
            "generations",
        )
        missing = sorted(
            (_REQUIRED_PROMPT_COMPONENT_COLUMNS_V5 - component_columns.keys())
            | (_REQUIRED_PROMPT_REVISION_COLUMNS_V5 - revision_columns.keys())
        )
        if "prompt_composition_id" not in generation_columns:
            missing.append("generations.prompt_composition_id")
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical prompt catalog is missing required columns: "
                + ", ".join(missing)
            )

        revision_indexes = cls._unique_index_columns(
            connection,
            "prompt_revisions",
        )
        for expected in (
            ("revision_uid",),
            ("component_id", "revision_number"),
            ("component_id", "content_hash"),
        ):
            if expected not in revision_indexes:
                raise CanonicalSchemaValidationError(
                    "prompt_revisions is missing immutable identity constraints"
                )
        component_indexes = cls._unique_index_columns(
            connection,
            "prompt_components",
        )
        if ("component_uid",) not in component_indexes:
            raise CanonicalSchemaValidationError(
                "prompt_components is missing stable UID uniqueness"
            )

    @classmethod
    def _validate_prompt_catalog_v7(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        usage_columns = cls._table_column_rows(
            connection,
            "prompt_revision_atom_usages",
        )
        missing = sorted(
            _REQUIRED_REVISION_ATOM_COLUMNS_V7 - usage_columns.keys()
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Prompt revision atom usages are missing required columns: "
                + ", ".join(missing)
            )
        revisions = connection.execute(
            "SELECT id, positive_text, negative_text FROM prompt_revisions"
        ).fetchall()
        for revision_id, positive_text, negative_text in revisions:
            for scope, snapshot in (
                ("pos", str(positive_text or "")),
                ("neg", str(negative_text or "")),
            ):
                rows = connection.execute(
                    """
                    SELECT atom.canonical_text, usage.weight_milli
                    FROM prompt_revision_atom_usages AS usage
                    JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                    WHERE usage.revision_id = ? AND usage.scope = ?
                    ORDER BY usage.position
                    """,
                    (revision_id, scope),
                ).fetchall()
                usages = tuple(
                    PromptAtomUsage(str(text), int(weight_milli))
                    for text, weight_milli in rows
                )
                if usages != prompt_atom_usages_from_text(snapshot):
                    raise CanonicalSchemaValidationError(
                        "prompt revision atom usages do not match snapshots"
                    )

    def _is_valid_version(self, version: int) -> bool:
        try:
            if version == 1:
                self._validate_version_one()
            elif version == 2:
                self._validate_version_two()
            elif version == 3:
                self._validate_version_three()
            elif version == 4:
                self._validate_version_four()
            elif version == 5:
                self._validate_version_five()
            elif version == 6:
                self._validate_version_six()
            else:
                self._validate_existing()
        except (CanonicalSchemaValidationError, sqlite3.DatabaseError):
            return False
        return True

    @staticmethod
    def _table_column_rows(
        connection: sqlite3.Connection,
        table: str,
    ) -> dict[str, tuple[object, ...]]:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        return {str(row[1]): tuple(row) for row in rows}

    @staticmethod
    def _unique_index_columns(
        connection: sqlite3.Connection,
        table: str,
    ) -> set[tuple[str, ...]]:
        indexes: set[tuple[str, ...]] = set()
        for row in connection.execute(
            f"PRAGMA index_list({table})"
        ).fetchall():
            if int(row[2]) != 1:
                continue
            index_name = str(row[1]).replace('"', '""')
            columns = tuple(
                str(info[2])
                for info in connection.execute(
                    f'PRAGMA index_info("{index_name}")'
                ).fetchall()
                if info[2] is not None
            )
            indexes.add(columns)
        return indexes

    def _create_backup(self, backup_directory: Path | None) -> Path:
        backup_root = Path(
            backup_directory
            if backup_directory is not None
            else self._database_path.parent / "backups"
        )
        run_directory = backup_root / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
            + f"_{uuid4().hex[:8]}"
        )
        backup_path = run_directory / self._database_path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        source = self._open_read_only()
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        return backup_path

    def _restore_backup(self, backup_path: Path) -> None:
        for suffix in ("-wal", "-shm"):
            Path(f"{self._database_path}{suffix}").unlink(missing_ok=True)
        shutil.copy2(backup_path, self._database_path)
