"""Lifecycle owner for the canonical ComfyReview SQLite database."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path
from uuid import uuid4

from comfyreview.application import CanonicalSchemaReport

SCHEMA_VERSION = 1

_SCHEMA_SQL = r"""
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

_REQUIRED_OBJECTS = {
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


class CanonicalSchemaValidationError(RuntimeError):
    """Signal an unsupported or corrupt canonical database."""


class CanonicalSchemaManager:
    """Validate or atomically initialize the canonical SQLite database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def prepare_startup(self) -> CanonicalSchemaReport:
        """Validate or atomically create canonical schema version one."""
        if self._database_path.exists():
            self._validate_existing()
            return CanonicalSchemaReport(
                initialized=False,
                schema_version=SCHEMA_VERSION,
            )
        self._create_new_database()
        return CanonicalSchemaReport(
            initialized=True,
            schema_version=SCHEMA_VERSION,
        )

    def _create_new_database(self) -> None:
        self._database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = self._database_path.with_name(
            f".{self._database_path.name}.{uuid4().hex}.tmp"
        )
        try:
            connection = sqlite3.connect(temporary_path)
            try:
                connection.executescript(_SCHEMA_SQL)
                connection.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
                connection.commit()
                self._validate_connection(connection)
            finally:
                connection.close()
            os.replace(temporary_path, self._database_path)
        finally:
            temporary_path.unlink(missing_ok=True)

    def _validate_existing(self) -> None:
        try:
            connection = sqlite3.connect(
                f"{self._database_path.as_uri()}?mode=rw",
                uri=True,
            )
        except sqlite3.Error as error:
            raise CanonicalSchemaValidationError(
                f"Cannot open canonical database: {error}"
            ) from error
        try:
            self._validate_connection(connection)
        finally:
            connection.close()

    def _validate_connection(self, connection: sqlite3.Connection) -> None:
        version = int(connection.execute("PRAGMA user_version").fetchone()[0])
        if version != SCHEMA_VERSION:
            raise CanonicalSchemaValidationError(
                "Unsupported canonical schema version "
                f"{version}; expected {SCHEMA_VERSION}"
            )
        rows = connection.execute(
            "SELECT name, type FROM sqlite_master "
            "WHERE type IN ('table', 'view')"
        ).fetchall()
        objects = {str(name): str(object_type) for name, object_type in rows}
        missing = [
            name
            for name, object_type in _REQUIRED_OBJECTS.items()
            if objects.get(name) != object_type
        ]
        if missing:
            raise CanonicalSchemaValidationError(
                "Canonical database is missing required objects: "
                + ", ".join(sorted(missing))
            )
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if not integrity or str(integrity[0]).lower() != "ok":
            raise CanonicalSchemaValidationError(
                "Canonical database integrity_check failed"
            )
