"""Lifecycle owner for the canonical ComfyReview SQLite database."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from comfyreview.application import (
    CanonicalSchemaReport,
    GeneratorStateSnapshot,
    GeneratorStateValidationError,
)
from comfyreview.domain import (
    PromptAtomUsage,
    prompt_atom_usages_from_text,
    render_prompt_atom_usages,
)

SCHEMA_VERSION = 14
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

_REQUIRED_OBJECTS_V8 = {
    **_REQUIRED_OBJECTS_V7,
    "generation_loras": "table",
    "generation_profile_loras": "table",
    "generation_profiles": "table",
    "workspace_curation_set_order": "table",
    "workspace_preferences": "table",
}
_REQUIRED_WORKSPACE_PREFERENCE_COLUMNS_V8 = {
    "singleton_id",
    "density",
    "motion",
    "analytics_page_size",
    "default_generation_profile_id",
    "review_unrated_only",
    "review_max_attempts",
    "default_curation_set_key",
    "updated_at",
}
_REQUIRED_GENERATION_PROFILE_COLUMNS_V8 = {
    "id",
    "profile_uid",
    "name",
    "blueprint_uid",
    "blueprint_version",
    "checkpoint",
    "sampler",
    "scheduler",
    "seed_mode",
    "fixed_seed",
    "steps_min",
    "steps_max",
    "cfg_min_milli",
    "cfg_max_milli",
    "denoise_milli",
    "batch_size",
    "archived_at",
    "created_at",
    "updated_at",
}
_REQUIRED_LORA_COLUMNS_V8 = {
    "position",
    "lora_name",
    "model_strength_milli",
    "clip_strength_milli",
}

_REQUIRED_OBJECTS_V9 = {
    **_REQUIRED_OBJECTS_V8,
    "workspace_content_levels": "table",
}
_REQUIRED_WORKSPACE_CONTENT_LEVEL_COLUMNS_V9 = {
    "singleton_id",
    "level",
    "position",
}
_REQUIRED_GENERATION_PROFILE_COLUMNS_V9 = (
    _REQUIRED_GENERATION_PROFILE_COLUMNS_V8 | {"image_width", "image_height"}
)

_REQUIRED_OBJECTS_V10 = {
    **_REQUIRED_OBJECTS_V9,
    "lora_definitions": "table",
    "image_content_level_events": "table",
    "image_content_level_state": "table",
}
_REQUIRED_GENERATION_PROFILE_COLUMNS_V10 = (
    _REQUIRED_GENERATION_PROFILE_COLUMNS_V9 | {"output_tier"}
)
_REQUIRED_GENERATION_COLUMNS_V10 = _REQUIRED_GENERATION_COLUMNS_V2 | {
    "image_width",
    "image_height",
    "output_tier",
    "output_width",
    "output_height",
    "inferred_content_level",
}

_REQUIRED_OBJECTS_V11 = {
    **_REQUIRED_OBJECTS_V10,
    "image_geometry_projection": "table",
}
_REQUIRED_IMAGE_GEOMETRY_COLUMNS_V11 = {
    "image_id",
    "actual_width",
    "actual_height",
    "aspect_format",
    "resolution_class",
    "target_width",
    "target_height",
    "is_exact",
    "classifier_version",
    "projected_at",
}

_REQUIRED_OBJECTS_V12 = {
    **_REQUIRED_OBJECTS_V11,
    "lora_revisions": "table",
    "lora_revision_atom_usages": "table",
}
_REQUIRED_LORA_DEFINITION_COLUMNS_V12 = {
    "id",
    "lora_uid",
    "provider_name",
    "display_name",
    "tags",
    "notes",
    "content_level",
    "revision",
    "archived_at",
    "created_at",
    "updated_at",
}
_REQUIRED_LORA_REVISION_COLUMNS_V12 = {
    "id",
    "revision_uid",
    "lora_definition_id",
    "revision_number",
    "default_model_strength_milli",
    "default_clip_strength_milli",
    "content_hash",
    "created_at",
}
_REQUIRED_LORA_REVISION_ATOM_COLUMNS_V12 = {
    "revision_id",
    "atom_id",
    "scope",
    "position",
    "weight_milli",
}
_REQUIRED_OBJECTS_V13 = {
    **_REQUIRED_OBJECTS_V12,
    "playground_generator_state": "table",
    "playground_generator_prompt_selections": "table",
    "playground_generator_loras": "table",
}
_REQUIRED_OBJECTS_V14 = dict(_REQUIRED_OBJECTS_V13)
_REQUIRED_LORA_REVISION_COLUMNS_V14 = _REQUIRED_LORA_REVISION_COLUMNS_V12 | {
    "content_level"
}
_REQUIRED_GENERATOR_STATE_COLUMNS_V13 = {
    "singleton_id",
    "checkpoint",
    "sampler",
    "scheduler",
    "seed_mode",
    "seed",
    "steps_min",
    "steps_max",
    "cfg_min_milli",
    "cfg_max_milli",
    "cfg_step_milli",
    "denoise_milli",
    "batch_runs",
    "aspect_format",
    "resolution_class",
    "updated_at",
}
_REQUIRED_GENERATOR_SELECTION_COLUMNS_V13 = {
    "singleton_id",
    "position",
    "kind",
    "mode",
    "component_id",
    "revision_id",
}
_REQUIRED_GENERATOR_LORA_COLUMNS_V13 = {
    "singleton_id",
    "position",
    "lora_definition_id",
    "lora_revision_id",
    "model_strength_milli",
    "clip_strength_milli",
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
        legacy_generator_state_path: Path | None = None,
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
        if current_version not in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}:
            raise CanonicalSchemaValidationError(
                "Unsupported canonical schema version "
                f"{current_version}; expected 1 through 13, or "
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
        elif current_version == 6:
            self._validate_version_six()
        elif current_version == 7:
            self._validate_version_seven()
        elif current_version == 8:
            self._validate_version_eight()
        elif current_version == 9:
            self._validate_version_nine()
        elif current_version == 10:
            self._validate_version_ten()
        elif current_version == 11:
            self._validate_version_eleven()
        elif current_version == 12:
            self._validate_version_twelve()
        else:
            self._validate_version_thirteen()

        legacy_generator_state = self._read_legacy_generator_state(
            legacy_generator_state_path
        )

        backup_path = self._create_backup(backup_directory)
        source_path = self._database_path
        migration_path = source_path.with_name(
            f".{source_path.name}.{uuid4().hex}.upgrade"
        )
        shutil.copy2(source_path, migration_path)
        self._database_path = migration_path
        skipped_lora_items = 0
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
                if current_version <= 6:
                    self._upgrade_v6_to_v7(connection)
                if current_version <= 7:
                    skipped_lora_items = self._upgrade_v7_to_v8(connection)
                if current_version <= 8:
                    self._upgrade_v8_to_v9(connection)
                if current_version <= 9:
                    self._upgrade_v9_to_v10(connection)
                if current_version <= 10:
                    self._upgrade_v10_to_v11(connection)
                if current_version <= 11:
                    self._upgrade_v11_to_v12(connection)
                if current_version <= 12:
                    self._upgrade_v12_to_v13(
                        connection, legacy_generator_state
                    )
                self._upgrade_v13_to_v14(connection)
                connection.commit()
                connection.execute("PRAGMA foreign_keys = ON")
            except Exception:
                connection.rollback()
                raise
            finally:
                connection.close()
            self._validate_existing()
            self._database_path = source_path
            shutil.copy2(migration_path, source_path)
            migration_path.unlink(missing_ok=True)
        except Exception:
            self._database_path = source_path
            migration_path.unlink(missing_ok=True)
            raise
        finally:
            self._database_path = source_path

        return CanonicalSchemaReport(
            schema_version=SCHEMA_VERSION,
            upgraded_from=current_version,
            backup_path=backup_path,
            warnings=(
                (
                    f"skipped {skipped_lora_items} incomplete historical "
                    "LoRA provenance items",
                )
                if skipped_lora_items
                else ()
            ),
        )

    def upgrade_to(
        self,
        output_path: Path,
        backup_directory: Path | None = None,
        legacy_generator_state_path: Path | None = None,
    ) -> CanonicalSchemaReport:
        """Upgrade into a new validated database while preserving the source."""
        if not self._database_path.exists():
            raise CanonicalSchemaValidationError(
                f"Canonical database does not exist: {self._database_path}"
            )
        target = Path(output_path).resolve()
        if target == self._database_path:
            raise CanonicalSchemaValidationError(
                "Migration output must differ from the source database"
            )
        if target.exists():
            raise CanonicalSchemaValidationError(
                f"Migration output already exists: {target}"
            )
        target.parent.mkdir(parents=True, exist_ok=True)
        source_hash = self._file_hash(self._database_path)
        shutil.copy2(self._database_path, target)
        try:
            report = CanonicalSchemaManager(target).upgrade(
                backup_directory,
                legacy_generator_state_path,
            )
            CanonicalSchemaManager(target).validate()
            if self._file_hash(self._database_path) != source_hash:
                raise CanonicalSchemaValidationError(
                    "Source database changed during migration"
                )
            return report
        except Exception:
            target.unlink(missing_ok=True)
            raise

    @staticmethod
    def _file_hash(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(1024 * 1024), b""):
                digest.update(block)
        return digest.hexdigest()

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
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v7_to_v8(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v8_to_v9(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v9_to_v10(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v10_to_v11(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v11_to_v12(connection)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v12_to_v13(connection, None)
                connection.commit()
                connection.execute("BEGIN IMMEDIATE")
                self._upgrade_v13_to_v14(connection)
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
            if version in {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}:
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

    def _validate_version_seven(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 7:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 7 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V7)
            self._validate_metadata_version(connection, 7)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v6(connection)
            self._validate_prompt_catalog_v5(connection)
            self._validate_prompt_catalog_v7(connection)
        finally:
            connection.close()

    def _validate_version_eight(self) -> None:
        connection = self._open_read_only()
        try:
            version = self._schema_version(connection)
            if version != 8:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 8 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V8)
            self._validate_metadata_version(connection, 8)
            self._validate_generation_columns(connection)
            self._validate_output_identity_v6(connection)
            self._validate_prompt_catalog_v5(connection)
            self._validate_prompt_catalog_v7(connection)
            self._validate_workspace_settings_v8(connection)
        finally:
            connection.close()

    def _validate_version_nine(self) -> None:
        connection = self._open_read_only()
        try:
            if self._schema_version(connection) != 9:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 9 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V9)
            self._validate_metadata_version(connection, 9)
            self._validate_workspace_settings_v9(connection)
        finally:
            connection.close()

    def _validate_version_ten(self) -> None:
        connection = self._open_read_only()
        try:
            if self._schema_version(connection) != 10:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 10 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V10)
            self._validate_metadata_version(connection, 10)
            self._validate_workspace_settings_v10(connection)
        finally:
            connection.close()

    def _validate_version_eleven(self) -> None:
        connection = self._open_read_only()
        try:
            if self._schema_version(connection) != 11:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 11 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V11)
            self._validate_metadata_version(connection, 11)
            self._validate_image_geometry_v11(connection)
        finally:
            connection.close()

    def _validate_version_twelve(self) -> None:
        connection = self._open_read_only()
        try:
            if self._schema_version(connection) != 12:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 12 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V12)
            self._validate_metadata_version(connection, 12)
            self._validate_lora_catalog_v12(connection)
        finally:
            connection.close()

    def _validate_version_thirteen(self) -> None:
        connection = self._open_read_only()
        try:
            if self._schema_version(connection) != 13:
                raise CanonicalSchemaValidationError(
                    "Expected canonical schema version 13 before upgrade"
                )
            self._validate_integrity(connection)
            self._validate_required_objects(connection, _REQUIRED_OBJECTS_V13)
            self._validate_metadata_version(connection, 13)
            self._validate_lora_catalog_v12(connection)
            self._validate_generator_state_v13(connection)
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
        self._validate_required_objects(connection, _REQUIRED_OBJECTS_V14)
        self._validate_metadata_version(connection, SCHEMA_VERSION)
        self._validate_generation_columns(connection)
        self._validate_output_identity_v6(connection)
        self._validate_prompt_catalog_v5(connection)
        self._validate_prompt_catalog_v7(connection)
        self._validate_workspace_settings_v8(connection)
        self._validate_workspace_settings_v9(connection)
        self._validate_workspace_settings_v10(connection)
        self._validate_image_geometry_v11(connection)
        self._validate_lora_catalog_v12(connection)
        self._validate_generator_state_v13(connection)
        self._validate_lora_catalog_v14(connection)

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

    @classmethod
    def _upgrade_v7_to_v8(cls, connection: sqlite3.Connection) -> int:
        connection.execute(
            """
            CREATE TABLE generation_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                profile_uid TEXT NOT NULL UNIQUE,
                name TEXT NOT NULL,
                blueprint_uid TEXT NOT NULL,
                blueprint_version INTEGER NOT NULL CHECK (blueprint_version > 0),
                checkpoint TEXT NOT NULL,
                sampler TEXT NOT NULL,
                scheduler TEXT NOT NULL,
                seed_mode TEXT NOT NULL
                    CHECK (seed_mode IN ('fixed', 'random')),
                fixed_seed INTEGER,
                steps_min INTEGER NOT NULL CHECK (steps_min > 0),
                steps_max INTEGER NOT NULL CHECK (steps_max >= steps_min),
                cfg_min_milli INTEGER NOT NULL CHECK (cfg_min_milli > 0),
                cfg_max_milli INTEGER NOT NULL
                    CHECK (cfg_max_milli >= cfg_min_milli),
                denoise_milli INTEGER NOT NULL
                    CHECK (denoise_milli BETWEEN 0 AND 1000),
                batch_size INTEGER NOT NULL CHECK (batch_size > 0),
                archived_at TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK (seed_mode = 'random' OR fixed_seed IS NOT NULL)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE generation_profile_loras (
                profile_id INTEGER NOT NULL
                    REFERENCES generation_profiles(id) ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                lora_name TEXT NOT NULL,
                model_strength_milli INTEGER NOT NULL,
                clip_strength_milli INTEGER NOT NULL,
                PRIMARY KEY (profile_id, position),
                UNIQUE (profile_id, lora_name)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE generation_loras (
                generation_id INTEGER NOT NULL
                    REFERENCES generations(id) ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                lora_name TEXT NOT NULL,
                model_strength_milli INTEGER NOT NULL,
                clip_strength_milli INTEGER NOT NULL,
                PRIMARY KEY (generation_id, position)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE workspace_preferences (
                singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                density TEXT NOT NULL DEFAULT 'comfortable'
                    CHECK (density IN ('comfortable', 'compact')),
                motion TEXT NOT NULL DEFAULT 'system'
                    CHECK (motion IN ('system', 'reduced')),
                analytics_page_size INTEGER NOT NULL DEFAULT 24
                    CHECK (analytics_page_size IN (12, 24, 48)),
                default_generation_profile_id INTEGER
                    REFERENCES generation_profiles(id),
                review_unrated_only INTEGER NOT NULL DEFAULT 1
                    CHECK (review_unrated_only IN (0, 1)),
                review_max_attempts INTEGER NOT NULL DEFAULT 50
                    CHECK (review_max_attempts > 0),
                default_curation_set_key TEXT,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE workspace_curation_set_order (
                singleton_id INTEGER NOT NULL DEFAULT 1
                    REFERENCES workspace_preferences(singleton_id)
                    ON DELETE CASCADE,
                set_key TEXT NOT NULL,
                position INTEGER NOT NULL CHECK (position >= 0),
                PRIMARY KEY (singleton_id, position),
                UNIQUE (singleton_id, set_key)
            )
            """
        )
        connection.execute(
            "INSERT INTO workspace_preferences(singleton_id) VALUES (1)"
        )
        skipped_lora_items = 0
        for generation_id, loras_json in connection.execute(
            "SELECT id, loras_json FROM generations ORDER BY id"
        ).fetchall():
            selections, skipped = cls._legacy_lora_selections(
                str(loras_json or "[]")
            )
            skipped_lora_items += skipped
            for position, lora in enumerate(selections):
                connection.execute(
                    """
                    INSERT INTO generation_loras(
                        generation_id, position, lora_name,
                        model_strength_milli, clip_strength_milli
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (int(generation_id), position, *lora),
                )
        connection.execute(
            "UPDATE schema_metadata SET value = '8' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 8")
        return skipped_lora_items

    @staticmethod
    def _upgrade_v8_to_v9(connection: sqlite3.Connection) -> None:
        connection.execute(
            "ALTER TABLE generation_profiles ADD COLUMN "
            "image_width INTEGER NOT NULL DEFAULT 1024 "
            "CHECK (image_width BETWEEN 64 AND 4096 AND image_width % 8 = 0)"
        )
        connection.execute(
            "ALTER TABLE generation_profiles ADD COLUMN "
            "image_height INTEGER NOT NULL DEFAULT 1024 "
            "CHECK (image_height BETWEEN 64 AND 4096 AND image_height % 8 = 0)"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN image_width INTEGER "
            "CHECK (image_width IS NULL OR "
            "(image_width BETWEEN 64 AND 4096 AND image_width % 8 = 0))"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN image_height INTEGER "
            "CHECK (image_height IS NULL OR "
            "(image_height BETWEEN 64 AND 4096 AND image_height % 8 = 0))"
        )
        connection.execute(
            """
            CREATE TABLE workspace_content_levels (
                singleton_id INTEGER NOT NULL DEFAULT 1
                    REFERENCES workspace_preferences(singleton_id)
                    ON DELETE CASCADE,
                level TEXT NOT NULL
                    CHECK (level IN ('standard', 'sexy', 'lewd', 'nude', 'explicit')),
                position INTEGER NOT NULL CHECK (position >= 0),
                PRIMARY KEY (singleton_id, position),
                UNIQUE (singleton_id, level)
            )
            """
        )
        connection.execute(
            "INSERT INTO workspace_content_levels(singleton_id, level, position) "
            "VALUES (1, 'standard', 0)"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '9' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 9")

    @staticmethod
    def _upgrade_v9_to_v10(connection: sqlite3.Connection) -> None:
        levels = "'standard', 'sexy', 'lewd', 'nude', 'explicit'"
        tiers = "'hd_720', 'full_hd_1080', 'uhd_4k'"
        connection.execute(
            "ALTER TABLE generation_profiles ADD COLUMN output_tier TEXT "
            "NOT NULL DEFAULT 'full_hd_1080' CHECK (output_tier IN ("
            + tiers
            + "))"
        )
        connection.execute(
            "UPDATE generation_profiles SET blueprint_version = 4 "
            "WHERE blueprint_uid = 'default-character' "
            "AND blueprint_version <= 3 AND archived_at IS NULL"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN output_tier TEXT "
            "CHECK (output_tier IS NULL OR output_tier IN (" + tiers + "))"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN output_width INTEGER"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN output_height INTEGER"
        )
        connection.execute(
            "ALTER TABLE generations ADD COLUMN inferred_content_level TEXT "
            "NOT NULL DEFAULT 'standard' CHECK (inferred_content_level IN ("
            + levels
            + "))"
        )
        connection.execute(
            """
            CREATE TABLE lora_definitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lora_uid TEXT NOT NULL UNIQUE,
                provider_name TEXT NOT NULL UNIQUE,
                content_level TEXT
                    CHECK (content_level IS NULL OR content_level IN (
                        'standard', 'sexy', 'lewd', 'nude', 'explicit'
                    )),
                revision INTEGER NOT NULL DEFAULT 1 CHECK (revision > 0),
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        names = connection.execute(
            "SELECT lora_name FROM generation_profile_loras "
            "UNION SELECT lora_name FROM generation_loras"
        ).fetchall()
        for (name,) in names:
            connection.execute(
                "INSERT INTO lora_definitions(lora_uid, provider_name) "
                "VALUES (?, ?)",
                (f"lora-{uuid4().hex}", str(name)),
            )
        connection.execute(
            "ALTER TABLE generation_profile_loras ADD COLUMN lora_uid TEXT"
        )
        connection.execute(
            "UPDATE generation_profile_loras SET lora_uid = ("
            "SELECT definition.lora_uid FROM lora_definitions AS definition "
            "WHERE definition.provider_name = generation_profile_loras.lora_name)"
        )
        connection.execute(
            "ALTER TABLE generation_loras ADD COLUMN lora_uid TEXT"
        )
        connection.execute(
            "ALTER TABLE generation_loras ADD COLUMN content_level_snapshot "
            "TEXT CHECK (content_level_snapshot IS NULL OR "
            "content_level_snapshot IN (" + levels + "))"
        )
        connection.execute(
            "UPDATE generation_loras SET lora_uid = ("
            "SELECT definition.lora_uid FROM lora_definitions AS definition "
            "WHERE definition.provider_name = generation_loras.lora_name)"
        )
        connection.execute(
            """
            CREATE TABLE image_content_level_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_uid TEXT NOT NULL UNIQUE,
                image_id INTEGER NOT NULL REFERENCES images(id) ON DELETE CASCADE,
                content_level TEXT CHECK (content_level IS NULL OR content_level IN (
                    'standard', 'sexy', 'lewd', 'nude', 'explicit'
                )),
                source TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE image_content_level_state (
                image_id INTEGER PRIMARY KEY
                    REFERENCES images(id) ON DELETE CASCADE,
                event_id INTEGER NOT NULL UNIQUE
                    REFERENCES image_content_level_events(id) ON DELETE CASCADE,
                override_content_level TEXT NOT NULL CHECK (
                    override_content_level IN (
                        'standard', 'sexy', 'lewd', 'nude', 'explicit'
                    )
                )
            )
            """
        )
        rank_tags = {
            "sexy": (
                "suggestive",
                "seductive",
                "sensual",
                "lingerie",
                "nsfw_level_suggestive",
            ),
            "lewd": ("lewd", "nsfw_level_partial"),
            "nude": ("nsfw_level_nude",),
            "explicit": (
                "nsfw_level_explicit_exposure",
                "nsfw_level_explicit_act",
            ),
        }
        for level, tags in rank_tags.items():
            placeholders = ", ".join("?" for _tag in tags)
            connection.execute(
                f"""
                UPDATE generations
                SET inferred_content_level = ?
                WHERE EXISTS (
                    SELECT 1
                    FROM prompt_composition_revisions AS membership
                    JOIN prompt_revisions AS revision
                      ON revision.id = membership.revision_id
                    JOIN prompt_components AS component
                      ON component.id = revision.component_id
                    JOIN json_each(
                        CASE WHEN json_valid(component.tags)
                             THEN component.tags ELSE '[]' END
                    ) AS tag
                    WHERE membership.composition_id =
                          generations.prompt_composition_id
                      AND lower(CAST(tag.value AS TEXT)) IN ({placeholders})
                )
                """,
                (level, *tags),
            )
        connection.execute(
            "UPDATE schema_metadata SET value = '10' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 10")

    @staticmethod
    def _upgrade_v10_to_v11(connection: sqlite3.Connection) -> None:
        connection.execute(
            """
            CREATE TABLE image_geometry_projection (
                image_id INTEGER PRIMARY KEY
                    REFERENCES images(id) ON DELETE CASCADE,
                actual_width INTEGER NOT NULL CHECK (actual_width > 0),
                actual_height INTEGER NOT NULL CHECK (actual_height > 0),
                aspect_format TEXT NOT NULL CHECK (aspect_format IN (
                    '2:3', '3:2', '16:9', '9:16', '1:1'
                )),
                resolution_class TEXT NOT NULL CHECK (resolution_class IN (
                    '720', '1080', '2160'
                )),
                target_width INTEGER NOT NULL CHECK (target_width > 0),
                target_height INTEGER NOT NULL CHECK (target_height > 0),
                is_exact INTEGER NOT NULL CHECK (is_exact IN (0, 1)),
                classifier_version INTEGER NOT NULL
                    CHECK (classifier_version > 0),
                projected_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '11' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 11")

    @staticmethod
    def _upgrade_v11_to_v12(connection: sqlite3.Connection) -> None:
        """Add revisioned LoRA catalog facts without inventing old triggers."""
        connection.execute(
            "ALTER TABLE lora_definitions ADD COLUMN "
            "display_name TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            "ALTER TABLE lora_definitions ADD COLUMN "
            "tags TEXT NOT NULL DEFAULT '[]'"
        )
        connection.execute(
            "ALTER TABLE lora_definitions ADD COLUMN "
            "notes TEXT NOT NULL DEFAULT ''"
        )
        connection.execute(
            "ALTER TABLE lora_definitions ADD COLUMN archived_at TEXT"
        )
        connection.execute(
            "UPDATE lora_definitions SET display_name = provider_name "
            "WHERE display_name = ''"
        )
        connection.execute(
            """
            CREATE TABLE lora_revisions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                revision_uid TEXT NOT NULL UNIQUE,
                lora_definition_id INTEGER NOT NULL
                    REFERENCES lora_definitions(id) ON DELETE CASCADE,
                revision_number INTEGER NOT NULL CHECK (revision_number > 0),
                default_model_strength_milli INTEGER NOT NULL,
                default_clip_strength_milli INTEGER NOT NULL,
                content_hash TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (lora_definition_id, revision_number),
                UNIQUE (lora_definition_id, content_hash)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE lora_revision_atom_usages (
                revision_id INTEGER NOT NULL
                    REFERENCES lora_revisions(id) ON DELETE CASCADE,
                atom_id INTEGER NOT NULL REFERENCES prompt_atoms(id),
                scope TEXT NOT NULL CHECK (scope IN ('pos', 'neg')),
                position INTEGER NOT NULL CHECK (position >= 0),
                weight_milli INTEGER NOT NULL CHECK (weight_milli > 0),
                PRIMARY KEY (revision_id, scope, position)
            )
            """
        )
        definitions = connection.execute(
            "SELECT id, lora_uid FROM lora_definitions ORDER BY id"
        ).fetchall()
        for definition_id, lora_uid in definitions:
            content = f"{1000}\0{1000}\0\0"
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            revision_hash = hashlib.sha256(
                f"{lora_uid}\0{content_hash}".encode()
            ).hexdigest()
            revision_uid = f"lora-revision-{revision_hash}"
            connection.execute(
                """
                INSERT INTO lora_revisions(
                    revision_uid, lora_definition_id, revision_number,
                    default_model_strength_milli,
                    default_clip_strength_milli, content_hash
                ) VALUES (?, ?, 1, 1000, 1000, ?)
                """,
                (revision_uid, int(definition_id), content_hash),
            )
        connection.execute(
            "ALTER TABLE generation_loras ADD COLUMN lora_revision_id INTEGER "
            "REFERENCES lora_revisions(id)"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '12' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 12")

    @classmethod
    def _upgrade_v12_to_v13(
        cls,
        connection: sqlite3.Connection,
        legacy_state: GeneratorStateSnapshot | None,
    ) -> None:
        """Add normalized Generator state and optionally import legacy JSON."""
        connection.execute(
            """
            CREATE TABLE playground_generator_state (
                singleton_id INTEGER PRIMARY KEY CHECK (singleton_id = 1),
                checkpoint TEXT NOT NULL,
                sampler TEXT NOT NULL,
                scheduler TEXT NOT NULL,
                seed_mode TEXT NOT NULL
                    CHECK (seed_mode IN ('fixed', 'random')),
                seed INTEGER NOT NULL,
                steps_min INTEGER NOT NULL CHECK (steps_min > 0),
                steps_max INTEGER NOT NULL CHECK (steps_max > 0),
                cfg_min_milli INTEGER NOT NULL CHECK (cfg_min_milli > 0),
                cfg_max_milli INTEGER NOT NULL CHECK (cfg_max_milli > 0),
                cfg_step_milli INTEGER NOT NULL CHECK (cfg_step_milli > 0),
                denoise_milli INTEGER NOT NULL
                    CHECK (denoise_milli BETWEEN 0 AND 1000),
                batch_runs INTEGER NOT NULL CHECK (batch_runs > 0),
                aspect_format TEXT NOT NULL CHECK (aspect_format IN (
                    '2:3', '3:2', '16:9', '9:16', '1:1'
                )),
                resolution_class TEXT NOT NULL CHECK (resolution_class IN (
                    '720', '1080', '2160'
                )),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                CHECK (steps_min <= steps_max),
                CHECK (cfg_min_milli <= cfg_max_milli)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE playground_generator_prompt_selections (
                singleton_id INTEGER NOT NULL
                    REFERENCES playground_generator_state(singleton_id)
                    ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                kind TEXT NOT NULL CHECK (kind IN (
                    'character', 'scene', 'outfit', 'pose', 'expression',
                    'lighting', 'modifier'
                )),
                mode TEXT NOT NULL CHECK (mode IN ('fixed', 'random', 'off')),
                component_id INTEGER REFERENCES prompt_components(id),
                revision_id INTEGER REFERENCES prompt_revisions(id),
                PRIMARY KEY (singleton_id, position),
                UNIQUE (singleton_id, kind),
                CHECK (
                    (mode = 'fixed' AND component_id IS NOT NULL
                        AND revision_id IS NOT NULL)
                    OR (mode != 'fixed' AND component_id IS NULL
                        AND revision_id IS NULL)
                )
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE playground_generator_loras (
                singleton_id INTEGER NOT NULL
                    REFERENCES playground_generator_state(singleton_id)
                    ON DELETE CASCADE,
                position INTEGER NOT NULL CHECK (position >= 0),
                lora_definition_id INTEGER NOT NULL
                    REFERENCES lora_definitions(id),
                lora_revision_id INTEGER NOT NULL
                    REFERENCES lora_revisions(id),
                model_strength_milli INTEGER NOT NULL,
                clip_strength_milli INTEGER NOT NULL,
                PRIMARY KEY (singleton_id, position),
                UNIQUE (singleton_id, lora_definition_id, lora_revision_id)
            )
            """
        )
        if legacy_state is not None:
            cls._insert_generator_state(connection, legacy_state)
        connection.execute(
            "UPDATE schema_metadata SET value = '13' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 13")

    @staticmethod
    def _upgrade_v13_to_v14(connection: sqlite3.Connection) -> None:
        """Move LoRA safety classification onto immutable trigger revisions."""
        connection.execute(
            "ALTER TABLE lora_revisions ADD COLUMN content_level TEXT "
            "NOT NULL DEFAULT 'standard' CHECK (content_level IN ("
            "'standard', 'sexy', 'lewd', 'nude', 'explicit'))"
        )
        connection.execute(
            """
            UPDATE lora_revisions
            SET content_level = COALESCE((
                SELECT definition.content_level
                FROM lora_definitions AS definition
                WHERE definition.id = lora_revisions.lora_definition_id
            ), 'standard')
            """
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '14' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 14")

    @staticmethod
    def _insert_generator_state(
        connection: sqlite3.Connection,
        state: GeneratorStateSnapshot,
    ) -> None:
        connection.execute(
            """
            INSERT INTO playground_generator_state(
                singleton_id, checkpoint, sampler, scheduler, seed_mode, seed,
                steps_min, steps_max, cfg_min_milli, cfg_max_milli,
                cfg_step_milli, denoise_milli, batch_runs,
                aspect_format, resolution_class
            ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.checkpoint,
                state.sampler,
                state.scheduler,
                state.seed_mode,
                state.seed,
                state.steps_min,
                state.steps_max,
                state.cfg_min_milli,
                state.cfg_max_milli,
                state.cfg_step_milli,
                state.denoise_milli,
                state.batch_runs,
                state.aspect_format,
                state.resolution_class,
            ),
        )
        for position, selection in enumerate(state.selections):
            component_id = None
            revision_id = None
            if selection.mode == "fixed":
                row = connection.execute(
                    """
                    SELECT component.id, revision.id
                    FROM prompt_components AS component
                    JOIN prompt_revisions AS revision
                      ON revision.component_id = component.id
                    WHERE component.component_uid = ?
                      AND revision.revision_uid = ?
                    """,
                    (selection.component_uid, selection.revision_uid),
                ).fetchone()
                if row is None:
                    raise CanonicalSchemaValidationError(
                        "Legacy Generator state references unknown prompt "
                        f"revision: {selection.revision_uid}"
                    )
                component_id, revision_id = int(row[0]), int(row[1])
            connection.execute(
                """
                INSERT INTO playground_generator_prompt_selections(
                    singleton_id, position, kind, mode,
                    component_id, revision_id
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    position,
                    selection.kind,
                    selection.mode,
                    component_id,
                    revision_id,
                ),
            )
        for position, lora in enumerate(state.loras):
            row = connection.execute(
                """
                SELECT definition.id, revision.id
                FROM lora_definitions AS definition
                JOIN lora_revisions AS revision
                  ON revision.lora_definition_id = definition.id
                WHERE definition.lora_uid = ? AND revision.revision_uid = ?
                """,
                (lora.lora_uid, lora.revision_uid),
            ).fetchone()
            if row is None:
                raise CanonicalSchemaValidationError(
                    "Legacy Generator state references unknown LoRA revision: "
                    f"{lora.revision_uid}"
                )
            connection.execute(
                """
                INSERT INTO playground_generator_loras(
                    singleton_id, position, lora_definition_id,
                    lora_revision_id, model_strength_milli,
                    clip_strength_milli
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                (
                    position,
                    int(row[0]),
                    int(row[1]),
                    lora.model_strength_milli,
                    lora.clip_strength_milli,
                ),
            )

    @staticmethod
    def _read_legacy_generator_state(
        source_path: Path | None,
    ) -> GeneratorStateSnapshot | None:
        if source_path is None:
            return None
        path = Path(source_path).resolve()
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise CanonicalSchemaValidationError(
                f"Legacy Generator state cannot be read: {path}"
            ) from error
        if not isinstance(payload, dict) or not isinstance(
            payload.get("generator_v2"), dict
        ):
            raise CanonicalSchemaValidationError(
                "Legacy Generator state is missing generator_v2"
            )
        try:
            return GeneratorStateSnapshot.from_mapping(payload["generator_v2"])
        except GeneratorStateValidationError as error:
            raise CanonicalSchemaValidationError(
                f"Legacy Generator state is invalid: {error}"
            ) from error

    @staticmethod
    def _legacy_lora_selections(
        payload: str,
    ) -> tuple[tuple[tuple[str, int, int], ...], int]:
        try:
            values = json.loads(payload)
        except json.JSONDecodeError as error:
            raise CanonicalSchemaValidationError(
                "generation LoRA provenance is not valid JSON"
            ) from error
        if not isinstance(values, list):
            raise CanonicalSchemaValidationError(
                "generation LoRA provenance must be a list"
            )
        result: list[tuple[str, int, int]] = []
        skipped = 0
        for value in values:
            if not isinstance(value, dict):
                raise CanonicalSchemaValidationError(
                    "generation LoRA provenance contains an invalid item"
                )
            name = value.get("name")
            model_strength = CanonicalSchemaManager._legacy_lora_strength(
                value,
                ("strength_model", "model_strength", "sm"),
            )
            clip_strength = CanonicalSchemaManager._legacy_lora_strength(
                value,
                ("strength_clip", "clip_strength", "sc"),
            )
            if (
                not isinstance(name, str)
                or not name.strip()
                or model_strength is None
                or clip_strength is None
            ):
                skipped += 1
                continue
            result.append(
                (
                    name.strip(),
                    round(float(model_strength) * 1000),
                    round(float(clip_strength) * 1000),
                )
            )
        return tuple(result), skipped

    @staticmethod
    def _legacy_lora_strength(
        value: dict[str, object],
        aliases: tuple[str, ...],
    ) -> float | None:
        candidates = [value[key] for key in aliases if key in value]
        if not candidates:
            return None
        numeric_candidates: list[float] = []
        for candidate in candidates:
            if isinstance(candidate, bool) or not isinstance(
                candidate, (int, float)
            ):
                return None
            numeric_candidates.append(float(candidate))
        normalized = set(numeric_candidates)
        if len(normalized) != 1:
            raise CanonicalSchemaValidationError(
                "generation LoRA provenance contains conflicting strengths"
            )
        return normalized.pop()

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

    @classmethod
    def _validate_workspace_settings_v8(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        preference_columns = cls._table_column_rows(
            connection,
            "workspace_preferences",
        )
        profile_columns = cls._table_column_rows(
            connection,
            "generation_profiles",
        )
        profile_lora_columns = cls._table_column_rows(
            connection,
            "generation_profile_loras",
        )
        generation_lora_columns = cls._table_column_rows(
            connection,
            "generation_loras",
        )
        missing = sorted(
            (
                _REQUIRED_WORKSPACE_PREFERENCE_COLUMNS_V8
                - preference_columns.keys()
            )
            | (
                _REQUIRED_GENERATION_PROFILE_COLUMNS_V8
                - profile_columns.keys()
            )
            | (_REQUIRED_LORA_COLUMNS_V8 - profile_lora_columns.keys())
            | (_REQUIRED_LORA_COLUMNS_V8 - generation_lora_columns.keys())
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical settings tables are missing required columns: "
                + ", ".join(missing)
            )
        if connection.execute(
            "SELECT COUNT(*) FROM workspace_preferences WHERE singleton_id = 1"
        ).fetchone() != (1,):
            raise CanonicalSchemaValidationError(
                "workspace preferences singleton is missing"
            )
        if ("profile_uid",) not in cls._unique_index_columns(
            connection,
            "generation_profiles",
        ):
            raise CanonicalSchemaValidationError(
                "generation profiles are missing stable UID uniqueness"
            )

    @classmethod
    def _validate_workspace_settings_v9(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        profile_columns = cls._table_column_rows(
            connection,
            "generation_profiles",
        )
        generation_columns = cls._table_column_rows(connection, "generations")
        level_columns = cls._table_column_rows(
            connection,
            "workspace_content_levels",
        )
        missing = sorted(
            (_REQUIRED_GENERATION_PROFILE_COLUMNS_V9 - profile_columns.keys())
            | ({"image_width", "image_height"} - generation_columns.keys())
            | (
                _REQUIRED_WORKSPACE_CONTENT_LEVEL_COLUMNS_V9
                - level_columns.keys()
            )
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical content and resolution settings are missing "
                "required columns: " + ", ".join(missing)
            )
        levels = connection.execute(
            "SELECT level FROM workspace_content_levels "
            "WHERE singleton_id = 1 ORDER BY position"
        ).fetchall()
        if not levels:
            raise CanonicalSchemaValidationError(
                "workspace must enable at least one content level"
            )

    @classmethod
    def _validate_workspace_settings_v10(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        profile_columns = cls._table_column_rows(
            connection, "generation_profiles"
        )
        generation_columns = cls._table_column_rows(connection, "generations")
        missing = sorted(
            (_REQUIRED_GENERATION_PROFILE_COLUMNS_V10 - profile_columns.keys())
            | (_REQUIRED_GENERATION_COLUMNS_V10 - generation_columns.keys())
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical content classification is missing columns: "
                + ", ".join(missing)
            )

    @classmethod
    def _validate_image_geometry_v11(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        columns = cls._table_column_rows(
            connection, "image_geometry_projection"
        )
        missing = sorted(_REQUIRED_IMAGE_GEOMETRY_COLUMNS_V11 - columns.keys())
        if missing:
            raise CanonicalSchemaValidationError(
                "Image geometry projection is missing columns: "
                + ", ".join(missing)
            )

    @classmethod
    def _validate_lora_catalog_v12(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        definition_columns = cls._table_column_rows(
            connection, "lora_definitions"
        )
        revision_columns = cls._table_column_rows(connection, "lora_revisions")
        atom_columns = cls._table_column_rows(
            connection, "lora_revision_atom_usages"
        )
        generation_lora_columns = cls._table_column_rows(
            connection, "generation_loras"
        )
        missing = sorted(
            (_REQUIRED_LORA_DEFINITION_COLUMNS_V12 - definition_columns.keys())
            | (_REQUIRED_LORA_REVISION_COLUMNS_V12 - revision_columns.keys())
            | (_REQUIRED_LORA_REVISION_ATOM_COLUMNS_V12 - atom_columns.keys())
            | ({"lora_revision_id"} - generation_lora_columns.keys())
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical LoRA catalog is missing columns: "
                + ", ".join(missing)
            )
        orphaned = connection.execute(
            "SELECT COUNT(*) FROM lora_definitions AS definition "
            "WHERE NOT EXISTS (SELECT 1 FROM lora_revisions AS revision "
            "WHERE revision.lora_definition_id = definition.id)"
        ).fetchone()[0]
        if int(orphaned):
            raise CanonicalSchemaValidationError(
                "Every LoRA definition requires an immutable revision"
            )

    @classmethod
    def _validate_lora_catalog_v14(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        revision_columns = cls._table_column_rows(connection, "lora_revisions")
        missing = sorted(
            _REQUIRED_LORA_REVISION_COLUMNS_V14 - revision_columns.keys()
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "LoRA trigger revisions are missing required columns: "
                + ", ".join(missing)
            )
        invalid = connection.execute(
            "SELECT COUNT(*) FROM lora_revisions "
            "WHERE content_level NOT IN ("
            "'standard', 'sexy', 'lewd', 'nude', 'explicit')"
        ).fetchone()[0]
        if int(invalid):
            raise CanonicalSchemaValidationError(
                "LoRA trigger revisions contain invalid content levels"
            )

    @classmethod
    def _validate_generator_state_v13(
        cls,
        connection: sqlite3.Connection,
    ) -> None:
        state_columns = cls._table_column_rows(
            connection, "playground_generator_state"
        )
        selection_columns = cls._table_column_rows(
            connection, "playground_generator_prompt_selections"
        )
        lora_columns = cls._table_column_rows(
            connection, "playground_generator_loras"
        )
        missing = sorted(
            (_REQUIRED_GENERATOR_STATE_COLUMNS_V13 - state_columns.keys())
            | (
                _REQUIRED_GENERATOR_SELECTION_COLUMNS_V13
                - selection_columns.keys()
            )
            | (_REQUIRED_GENERATOR_LORA_COLUMNS_V13 - lora_columns.keys())
        )
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical Generator state is missing columns: "
                + ", ".join(missing)
            )
        mismatched_prompt_revisions = connection.execute(
            """
            SELECT COUNT(*)
            FROM playground_generator_prompt_selections AS selection
            JOIN prompt_revisions AS revision
              ON revision.id = selection.revision_id
            WHERE revision.component_id != selection.component_id
            """
        ).fetchone()[0]
        mismatched_lora_revisions = connection.execute(
            """
            SELECT COUNT(*)
            FROM playground_generator_loras AS selection
            JOIN lora_revisions AS revision
              ON revision.id = selection.lora_revision_id
            WHERE revision.lora_definition_id != selection.lora_definition_id
            """
        ).fetchone()[0]
        if int(mismatched_prompt_revisions) or int(mismatched_lora_revisions):
            raise CanonicalSchemaValidationError(
                "Generator state contains mismatched catalog revisions"
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
            elif version == 7:
                self._validate_version_seven()
            elif version == 8:
                self._validate_version_eight()
            elif version == 9:
                self._validate_version_nine()
            elif version == 10:
                self._validate_version_ten()
            elif version == 11:
                self._validate_version_eleven()
            elif version == 12:
                self._validate_version_twelve()
            elif version == 13:
                self._validate_version_thirteen()
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
