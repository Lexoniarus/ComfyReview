"""Shared lifecycle for the immutable Card Battler SQLite model resource."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from threading import Lock

from comfyreview.application.card_battler_model import (
    CardBattlerModelError,
    CardBattlerModelInvalid,
    CardBattlerModelMetadata,
    CardBattlerModelNotFound,
    CardBattlerModelVersionUnsupported,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.connection import connect_read_only

_EXPECTED_DATABASE_NAME = "card_battler_model"
_SUPPORTED_SCHEMA_VERSIONS = frozenset({3})


@dataclass(frozen=True, slots=True)
class CardBattlerModelTableRequirement:
    """Declare the columns one authoritative model read area requires."""

    table: str
    columns: frozenset[str]


@dataclass(frozen=True, slots=True)
class CardBattlerModelSchemaRequirement:
    """Group related table contracts under one focused read responsibility."""

    group: str
    tables: tuple[CardBattlerModelTableRequirement, ...]


@dataclass(frozen=True, slots=True)
class CardBattlerModelPolicyRef:
    """Identify one active versioned policy validated with the model."""

    kind: str
    key: str
    version: int


@dataclass(frozen=True, slots=True)
class CardBattlerModelValidation:
    """Cache the immutable facts established by full resource validation."""

    metadata: CardBattlerModelMetadata
    active_ruleset_id: int
    active_ruleset: CardBattlerRulesetRef
    active_policies: tuple[CardBattlerModelPolicyRef, ...]


MODEL_IDENTITY_SCHEMA = CardBattlerModelSchemaRequirement(
    group="identity",
    tables=(
        CardBattlerModelTableRequirement(
            "schema_meta", frozenset({"key", "value"})
        ),
        CardBattlerModelTableRequirement(
            "semantic_vocabularies",
            frozenset(
                {
                    "id",
                    "vocabulary_key",
                    "version",
                    "status",
                    "description",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "rulesets",
            frozenset(
                {
                    "id",
                    "ruleset_key",
                    "version",
                    "name",
                    "status",
                    "semantic_vocabulary_id",
                    "description",
                }
            ),
        ),
    ),
)

FOUNDATIONAL_CARD_BATTLER_SCHEMA = CardBattlerModelSchemaRequirement(
    group="foundational-catalog",
    tables=(
        CardBattlerModelTableRequirement(
            "semantic_categories",
            frozenset({"id", "vocabulary_id", "key", "name", "description"}),
        ),
        CardBattlerModelTableRequirement(
            "semantic_concepts",
            frozenset(
                {
                    "id",
                    "vocabulary_id",
                    "category_id",
                    "key",
                    "name",
                    "description",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "semantic_aliases",
            frozenset({"id", "vocabulary_id", "alias", "concept_id"}),
        ),
        CardBattlerModelTableRequirement(
            "world_styles",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "name",
                    "parent_style_id",
                    "description",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "card_classes",
            frozenset(
                {"id", "ruleset_id", "key", "name", "description", "active"}
            ),
        ),
        CardBattlerModelTableRequirement(
            "combat_roles",
            frozenset(
                {"id", "ruleset_id", "key", "name", "description", "active"}
            ),
        ),
        CardBattlerModelTableRequirement(
            "trait_lineages",
            frozenset(
                {"id", "ruleset_id", "key", "name", "description", "active"}
            ),
        ),
        CardBattlerModelTableRequirement(
            "rarities",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "name",
                    "ordinal",
                    "max_traits",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "development_tiers",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "rarity_id",
                    "level",
                    "ordinal",
                    "next_tier_id",
                    "development_locked",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_templates",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "internal_name",
                    "description",
                    "base_weight_milli",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "visual_prompt_atoms",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "canonical_text",
                    "category",
                    "active",
                }
            ),
        ),
    ),
)

CARD_BATTLER_MAPPING_SCHEMA = CardBattlerModelSchemaRequirement(
    group="imprint-mapping",
    tables=(
        CardBattlerModelTableRequirement(
            "mapping_policies",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "policy_key",
                    "version",
                    "config_json",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "rng_policies",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "policy_key",
                    "version",
                    "algorithm",
                    "config_json",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "semantic_world_style_affinity",
            frozenset({"concept_id", "world_style_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "semantic_class_affinity",
            frozenset({"concept_id", "class_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "semantic_role_affinity",
            frozenset({"concept_id", "role_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "semantic_lineage_affinity",
            frozenset({"concept_id", "lineage_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "world_style_class_compatibility",
            frozenset(
                {"world_style_id", "class_id", "weight_milli", "enabled"}
            ),
        ),
        CardBattlerModelTableRequirement(
            "class_role_compatibility",
            frozenset({"class_id", "role_id", "weight_milli", "enabled"}),
        ),
        CardBattlerModelTableRequirement(
            "class_lineage_compatibility",
            frozenset({"class_id", "lineage_id", "weight_milli", "enabled"}),
        ),
        CardBattlerModelTableRequirement(
            "role_lineage_compatibility",
            frozenset({"role_id", "lineage_id", "weight_milli", "enabled"}),
        ),
        CardBattlerModelTableRequirement(
            "mapping_fallback_world_styles",
            frozenset({"mapping_policy_id", "world_style_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "mapping_fallback_classes",
            frozenset({"mapping_policy_id", "class_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "mapping_fallback_roles",
            frozenset({"mapping_policy_id", "role_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "mapping_fallback_lineages",
            frozenset({"mapping_policy_id", "lineage_id", "weight_milli"}),
        ),
    ),
)

CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS = (
    MODEL_IDENTITY_SCHEMA,
    FOUNDATIONAL_CARD_BATTLER_SCHEMA,
    CARD_BATTLER_MAPPING_SCHEMA,
)


class SqliteCardBattlerModelResource:
    """Validate one immutable model lazily once, then lend read connections."""

    def __init__(
        self,
        database_path: Path,
        schema_requirements: Sequence[CardBattlerModelSchemaRequirement],
    ) -> None:
        self._database_path = Path(database_path).expanduser().resolve()
        self._required_columns = self._merge_requirements(schema_requirements)
        self._validation_lock = Lock()
        self._validation: CardBattlerModelValidation | None = None
        self._validation_failure: (
            tuple[type[CardBattlerModelError], str] | None
        ) = None

    @property
    def database_path(self) -> Path:
        """Return the fixed path owned for this resource lifetime."""
        return self._database_path

    def validation(self) -> CardBattlerModelValidation:
        """Return the once-computed validation snapshot or cached failure."""
        with self._validation_lock:
            if self._validation is not None:
                return self._validation
            if self._validation_failure is not None:
                error_type, message = self._validation_failure
                raise error_type(message)
            try:
                with self._raw_connection() as connection:
                    validation = self._validate_connection(connection)
            except CardBattlerModelError as error:
                self._validation_failure = (type(error), str(error))
                raise
            except (
                sqlite3.DatabaseError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                normalized = self._invalid(str(error))
                self._validation_failure = (type(normalized), str(normalized))
                raise normalized from error
            self._validation = validation
            return validation

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        """Open one short read-only connection after validation succeeds."""
        self.validation()
        with self._raw_connection() as connection:
            try:
                yield connection
            except CardBattlerModelError:
                raise
            except (
                sqlite3.DatabaseError,
                KeyError,
                TypeError,
                ValueError,
            ) as error:
                raise self._invalid(str(error)) from error

    @contextmanager
    def _raw_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._open_connection()
        try:
            yield connection
        finally:
            connection.close()

    def _open_connection(self) -> sqlite3.Connection:
        path = self._database_path
        if not path.exists():
            raise CardBattlerModelNotFound(
                f"Card Battler model database does not exist: {path}"
            )
        if not path.is_file():
            raise self._invalid(
                f"configured Card Battler model path is not a file: {path}"
            )
        try:
            connection = connect_read_only(path, rows=True)
            connection.execute("PRAGMA query_only = ON")
            return connection
        except (OSError, sqlite3.DatabaseError) as error:
            raise self._invalid(
                f"cannot open model database: {error}"
            ) from error

    def _validate_connection(
        self, connection: sqlite3.Connection
    ) -> CardBattlerModelValidation:
        self._validate_table_contract(
            connection,
            "schema_meta",
            frozenset({"key", "value"}),
        )
        metadata = self._read_metadata(connection)
        if metadata.database_name != _EXPECTED_DATABASE_NAME:
            raise self._invalid(
                "unexpected database identity "
                f"{metadata.database_name!r}; expected "
                f"{_EXPECTED_DATABASE_NAME!r}"
            )
        if metadata.schema_version not in _SUPPORTED_SCHEMA_VERSIONS:
            supported = ", ".join(
                str(version) for version in sorted(_SUPPORTED_SCHEMA_VERSIONS)
            )
            raise CardBattlerModelVersionUnsupported(
                "unsupported Card Battler model schema version "
                f"{metadata.schema_version}; supported: {supported}"
            )
        self._validate_registered_schema(connection)
        integrity = connection.execute("PRAGMA integrity_check").fetchall()
        if not integrity or any(
            str(row[0]).lower() != "ok" for row in integrity
        ):
            raise self._invalid("SQLite integrity_check did not report ok")
        foreign_keys = connection.execute(
            "PRAGMA foreign_key_check"
        ).fetchall()
        if foreign_keys:
            raise self._invalid(
                "SQLite foreign_key_check reported "
                f"{len(foreign_keys)} violation(s)"
            )
        ruleset_id, ruleset = self._resolve_active_ruleset(connection)
        return CardBattlerModelValidation(
            metadata=metadata,
            active_ruleset_id=ruleset_id,
            active_ruleset=ruleset,
            active_policies=self._resolve_active_policies(
                connection, ruleset_id
            ),
        )

    def _validate_registered_schema(
        self, connection: sqlite3.Connection
    ) -> None:
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        available = {str(row["name"]) for row in table_rows}
        missing = sorted(self._required_columns.keys() - available)
        if missing:
            raise self._invalid(
                "missing required table(s): " + ", ".join(missing)
            )
        for table, columns in self._required_columns.items():
            self._validate_table_contract(connection, table, columns)

    def _validate_table_contract(
        self,
        connection: sqlite3.Connection,
        table: str,
        required_columns: frozenset[str],
    ) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute(
                f"PRAGMA table_info({table})"
            ).fetchall()
        }
        if not columns:
            raise self._invalid(f"missing required table: {table}")
        missing = sorted(required_columns - columns)
        if missing:
            raise self._invalid(
                f"table {table!r} is missing required column(s): "
                + ", ".join(missing)
            )

    def _read_metadata(
        self, connection: sqlite3.Connection
    ) -> CardBattlerModelMetadata:
        rows = connection.execute(
            "SELECT key, value FROM schema_meta ORDER BY key COLLATE BINARY"
        ).fetchall()
        values = {str(row["key"]): str(row["value"]) for row in rows}
        if "database_name" not in values or "schema_version" not in values:
            raise self._invalid("schema_meta is missing model identity fields")
        try:
            schema_version = int(values["schema_version"])
        except ValueError as error:
            raise self._invalid("schema_version is not an integer") from error
        return CardBattlerModelMetadata(
            database_name=values["database_name"],
            schema_version=schema_version,
            seed_version=values.get("seed_version"),
            purpose=values.get("purpose"),
            authority=values.get("authority"),
            audit_status=values.get("audit_status"),
        )

    def _resolve_active_ruleset(
        self, connection: sqlite3.Connection
    ) -> tuple[int, CardBattlerRulesetRef]:
        rows = connection.execute(
            """
            SELECT rulesets.id, rulesets.ruleset_key, rulesets.version,
                   rulesets.name, rulesets.status, rulesets.description,
                   vocabularies.vocabulary_key,
                   vocabularies.version AS vocabulary_version
            FROM rulesets
            JOIN semantic_vocabularies AS vocabularies
              ON vocabularies.id = rulesets.semantic_vocabulary_id
            WHERE rulesets.status = 'active'
            ORDER BY rulesets.version DESC,
                     rulesets.ruleset_key COLLATE BINARY
            """
        ).fetchall()
        if not rows:
            raise self._invalid("cannot resolve active ruleset")
        row = rows[0]
        return int(row["id"]), CardBattlerRulesetRef(
            key=str(row["ruleset_key"]),
            version=int(row["version"]),
            name=str(row["name"]),
            status=str(row["status"]),
            description=str(row["description"]),
            semantic_vocabulary_key=str(row["vocabulary_key"]),
            semantic_vocabulary_version=int(row["vocabulary_version"]),
        )

    def _resolve_active_policies(
        self, connection: sqlite3.Connection, ruleset_id: int
    ) -> tuple[CardBattlerModelPolicyRef, ...]:
        policies: list[CardBattlerModelPolicyRef] = []
        for kind, table in (
            ("mapping", "mapping_policies"),
            ("rng", "rng_policies"),
        ):
            rows = connection.execute(
                f"""
                SELECT policy_key, version
                FROM {table}
                WHERE ruleset_id = ? AND active = 1
                ORDER BY version DESC, policy_key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            if not rows:
                raise self._invalid(
                    f"cannot resolve active {kind} policy for active ruleset"
                )
            policies.extend(
                CardBattlerModelPolicyRef(
                    kind=kind,
                    key=str(row["policy_key"]),
                    version=int(row["version"]),
                )
                for row in rows
            )
        return tuple(
            sorted(
                policies,
                key=lambda policy: (policy.kind, policy.key, policy.version),
            )
        )

    @staticmethod
    def _merge_requirements(
        requirements: Sequence[CardBattlerModelSchemaRequirement],
    ) -> dict[str, frozenset[str]]:
        merged: dict[str, set[str]] = {}
        for requirement in requirements:
            if not requirement.group:
                raise ValueError("schema requirement group must not be empty")
            for table in requirement.tables:
                if not table.table.isidentifier():
                    raise ValueError(
                        f"invalid model schema table name: {table.table!r}"
                    )
                if not table.columns or any(
                    not column.isidentifier() for column in table.columns
                ):
                    raise ValueError(
                        f"invalid column contract for table {table.table!r}"
                    )
                merged.setdefault(table.table, set()).update(table.columns)
        return {
            table: frozenset(columns)
            for table, columns in sorted(merged.items())
        }

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._database_path}: {detail}"
        )
