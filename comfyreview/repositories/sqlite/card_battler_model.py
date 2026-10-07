"""Read-only SQLite adapter for the external Card Battler model database."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from comfyreview.application.card_battler_model import (
    CardBattlerMappingPolicy,
    CardBattlerModelInvalid,
    CardBattlerModelMetadata,
    CardBattlerModelNotFound,
    CardBattlerModelSummary,
    CardBattlerModelVersionUnsupported,
    CardBattlerRngPolicy,
    CardBattlerRulesetRef,
    CardClassDefinition,
    CombatRoleDefinition,
    CompatibilityFact,
    DevelopmentTierDefinition,
    FallbackCandidate,
    MechanicTemplateReference,
    SemanticAffinity,
    SemanticConceptDefinition,
    TraitLineageDefinition,
    WorldStyleDefinition,
)
from comfyreview.repositories.sqlite.connection import connect_read_only

_EXPECTED_DATABASE_NAME = "card_battler_model"
_SUPPORTED_SCHEMA_VERSIONS = frozenset({3})
_REQUIRED_COLUMNS: dict[str, frozenset[str]] = {
    "schema_meta": frozenset({"key", "value"}),
    "semantic_vocabularies": frozenset(
        {"id", "vocabulary_key", "version", "status", "description"}
    ),
    "rulesets": frozenset(
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
    "semantic_categories": frozenset(
        {"id", "vocabulary_id", "key", "name", "description"}
    ),
    "semantic_concepts": frozenset(
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
    "semantic_aliases": frozenset(
        {"id", "vocabulary_id", "alias", "concept_id"}
    ),
    "world_styles": frozenset(
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
    "card_classes": frozenset(
        {"id", "ruleset_id", "key", "name", "description", "active"}
    ),
    "combat_roles": frozenset(
        {"id", "ruleset_id", "key", "name", "description", "active"}
    ),
    "trait_lineages": frozenset(
        {"id", "ruleset_id", "key", "name", "description", "active"}
    ),
    "rarities": frozenset(
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
    "development_tiers": frozenset(
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
    "mechanic_templates": frozenset(
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
    "visual_prompt_atoms": frozenset(
        {
            "id",
            "ruleset_id",
            "key",
            "canonical_text",
            "category",
            "active",
        }
    ),
    "mapping_policies": frozenset(
        {"id", "ruleset_id", "policy_key", "version", "config_json", "active"}
    ),
    "rng_policies": frozenset(
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
    "semantic_world_style_affinity": frozenset(
        {"concept_id", "world_style_id", "weight_milli"}
    ),
    "semantic_class_affinity": frozenset(
        {"concept_id", "class_id", "weight_milli"}
    ),
    "semantic_role_affinity": frozenset(
        {"concept_id", "role_id", "weight_milli"}
    ),
    "semantic_lineage_affinity": frozenset(
        {"concept_id", "lineage_id", "weight_milli"}
    ),
    "world_style_class_compatibility": frozenset(
        {"world_style_id", "class_id", "weight_milli", "enabled"}
    ),
    "class_role_compatibility": frozenset(
        {"class_id", "role_id", "weight_milli", "enabled"}
    ),
    "class_lineage_compatibility": frozenset(
        {"class_id", "lineage_id", "weight_milli", "enabled"}
    ),
    "role_lineage_compatibility": frozenset(
        {"role_id", "lineage_id", "weight_milli", "enabled"}
    ),
    "mapping_fallback_world_styles": frozenset(
        {"mapping_policy_id", "world_style_id", "weight_milli"}
    ),
    "mapping_fallback_classes": frozenset(
        {"mapping_policy_id", "class_id", "weight_milli"}
    ),
    "mapping_fallback_roles": frozenset(
        {"mapping_policy_id", "role_id", "weight_milli"}
    ),
    "mapping_fallback_lineages": frozenset(
        {"mapping_policy_id", "lineage_id", "weight_milli"}
    ),
}


class SqliteCardBattlerModelRepository:
    """Read a validated Card Battler model without ever mutating it."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def metadata(self) -> CardBattlerModelMetadata:
        with self._validated_connection() as connection:
            return self._read_metadata(connection)

    def resolve_ruleset(
        self,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBattlerRulesetRef:
        with self._validated_connection() as connection:
            _, ruleset = self._resolve_ruleset(connection, key, version)
            return ruleset

    def semantic_concepts(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticConceptDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, resolved = self._resolve_ruleset_ref(
                connection, ruleset
            )
            del ruleset_id
            vocabulary = connection.execute(
                """
                SELECT id
                FROM semantic_vocabularies
                WHERE vocabulary_key = ? AND version = ?
                """,
                (
                    resolved.semantic_vocabulary_key,
                    resolved.semantic_vocabulary_version,
                ),
            ).fetchone()
            if vocabulary is None:
                raise self._invalid(
                    "ruleset semantic vocabulary cannot be resolved"
                )
            rows = connection.execute(
                """
                SELECT
                    concepts.id,
                    concepts.key,
                    concepts.name,
                    categories.key AS category_key,
                    categories.name AS category_name,
                    concepts.description
                FROM semantic_concepts AS concepts
                JOIN semantic_categories AS categories
                  ON categories.id = concepts.category_id
                WHERE concepts.vocabulary_id = ? AND concepts.active = 1
                ORDER BY categories.key COLLATE BINARY,
                         concepts.key COLLATE BINARY
                """,
                (int(vocabulary["id"]),),
            ).fetchall()
            aliases = self._semantic_aliases(
                connection,
                int(vocabulary["id"]),
            )
            return tuple(
                SemanticConceptDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    category_key=str(row["category_key"]),
                    category_name=str(row["category_name"]),
                    description=str(row["description"]),
                    aliases=aliases.get(int(row["id"]), ()),
                )
                for row in rows
            )

    def world_styles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[WorldStyleDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            rows = connection.execute(
                """
                SELECT styles.key, styles.name, styles.description,
                       parents.key AS parent_key
                FROM world_styles AS styles
                LEFT JOIN world_styles AS parents
                  ON parents.id = styles.parent_style_id
                WHERE styles.ruleset_id = ? AND styles.active = 1
                ORDER BY styles.key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            return tuple(
                WorldStyleDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                    parent_key=(
                        None
                        if row["parent_key"] is None
                        else str(row["parent_key"])
                    ),
                )
                for row in rows
            )

    def card_classes(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CardClassDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            return tuple(
                CardClassDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                )
                for row in self._dimension_rows(
                    connection,
                    "card_classes",
                    ruleset_id,
                )
            )

    def combat_roles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CombatRoleDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            return tuple(
                CombatRoleDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                )
                for row in self._dimension_rows(
                    connection,
                    "combat_roles",
                    ruleset_id,
                )
            )

    def trait_lineages(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[TraitLineageDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            return tuple(
                TraitLineageDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    description=str(row["description"]),
                )
                for row in self._dimension_rows(
                    connection,
                    "trait_lineages",
                    ruleset_id,
                )
            )

    def development_tiers(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[DevelopmentTierDefinition, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            rows = connection.execute(
                """
                SELECT tiers.ordinal, rarities.key AS rarity_key,
                       rarities.name AS rarity_name,
                       rarities.ordinal AS rarity_ordinal,
                       tiers.level, tiers.development_locked,
                       next_tier.ordinal AS next_ordinal
                FROM development_tiers AS tiers
                JOIN rarities ON rarities.id = tiers.rarity_id
                LEFT JOIN development_tiers AS next_tier
                  ON next_tier.id = tiers.next_tier_id
                WHERE tiers.ruleset_id = ?
                ORDER BY tiers.ordinal
                """,
                (ruleset_id,),
            ).fetchall()
            return tuple(
                DevelopmentTierDefinition(
                    ordinal=int(row["ordinal"]),
                    rarity_key=str(row["rarity_key"]),
                    rarity_name=str(row["rarity_name"]),
                    rarity_ordinal=int(row["rarity_ordinal"]),
                    level=int(row["level"]),
                    development_locked=bool(row["development_locked"]),
                    next_ordinal=(
                        None
                        if row["next_ordinal"] is None
                        else int(row["next_ordinal"])
                    ),
                )
                for row in rows
            )

    def mechanic_templates(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicTemplateReference, ...]:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            rows = connection.execute(
                """
                SELECT key, internal_name, description, base_weight_milli
                FROM mechanic_templates
                WHERE ruleset_id = ? AND active = 1
                ORDER BY key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            return tuple(
                MechanicTemplateReference(
                    key=str(row["key"]),
                    internal_name=str(row["internal_name"]),
                    description=str(row["description"]),
                    base_weight_milli=int(row["base_weight_milli"]),
                )
                for row in rows
            )

    def mapping_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBattlerMappingPolicy:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            row = self._resolve_policy_row(
                connection, "mapping_policies", ruleset_id, key, version
            )
            config = self._json_object(row["config_json"], "mapping policy")
            components = config.get("score_components")
            if not isinstance(components, dict):
                raise self._invalid(
                    "mapping policy score_components is invalid"
                )
            expected_sort = ["score_desc", "key_asc"]
            if config.get("stable_sort") != expected_sort:
                raise self._invalid("unsupported mapping policy stable_sort")
            policy = CardBattlerMappingPolicy(
                key=str(row["policy_key"]),
                version=int(row["version"]),
                signal_min_milli=self._config_int(config, "signal_min_milli"),
                candidate_min_score_milli=self._config_int(
                    config, "candidate_min_score_milli"
                ),
                compatibility_floor_milli=self._config_int(
                    config, "compatibility_floor_milli"
                ),
                minimum_candidate_count=self._config_int(
                    config, "minimum_candidate_count", minimum=1
                ),
                top_pool_size=self._config_int(
                    config, "top_pool_size", minimum=1
                ),
                use_seeded_weighted_selection=self._config_bool(
                    config, "use_seeded_weighted_selection"
                ),
                fallback_when_no_candidate=self._config_bool(
                    config, "fallback_when_no_candidate"
                ),
                semantic_affinity_weight=self._config_int(
                    components, "semantic_affinity", minimum=0
                ),
                compatibility_weight=self._config_int(
                    components, "compatibility", minimum=0
                ),
                fallback_prior_weight=self._config_int(
                    components, "fallback_prior", minimum=0
                ),
            )
            base_weight = (
                policy.semantic_affinity_weight + policy.fallback_prior_weight
            )
            if base_weight <= 0:
                raise self._invalid(
                    "mapping policy World Style score weights are empty"
                )
            if base_weight + policy.compatibility_weight <= 0:
                raise self._invalid(
                    "mapping policy compatible-axis score weights are empty"
                )
            return policy

    def rng_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBattlerRngPolicy:
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            row = self._resolve_policy_row(
                connection, "rng_policies", ruleset_id, key, version
            )
            config = self._json_object(row["config_json"], "RNG policy")
            seed_material = config.get("seed_material")
            if not isinstance(seed_material, list) or not all(
                isinstance(value, str) and value for value in seed_material
            ):
                raise self._invalid("RNG policy seed_material is invalid")
            if config.get("stable_candidate_key") != "entity_key":
                raise self._invalid("unsupported RNG stable_candidate_key")
            if config.get("sql_row_order_is_not_randomness") is not True:
                raise self._invalid(
                    "RNG policy must reject SQL row-order randomness"
                )
            if config.get("runtime_hash_is_not_randomness") is not True:
                raise self._invalid(
                    "RNG policy must reject runtime hash randomness"
                )
            return CardBattlerRngPolicy(
                key=str(row["policy_key"]),
                version=int(row["version"]),
                algorithm=str(row["algorithm"]),
                seed_material=tuple(seed_material),
                stable_candidate_key="entity_key",
            )

    def world_style_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticAffinity, ...]:
        return self._affinities(
            ruleset,
            "semantic_world_style_affinity",
            "world_styles",
            "world_style_id",
        )

    def class_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticAffinity, ...]:
        return self._affinities(
            ruleset,
            "semantic_class_affinity",
            "card_classes",
            "class_id",
        )

    def role_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticAffinity, ...]:
        return self._affinities(
            ruleset,
            "semantic_role_affinity",
            "combat_roles",
            "role_id",
        )

    def lineage_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[SemanticAffinity, ...]:
        return self._affinities(
            ruleset,
            "semantic_lineage_affinity",
            "trait_lineages",
            "lineage_id",
        )

    def world_style_class_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CompatibilityFact, ...]:
        return self._compatibility(
            ruleset,
            "world_style_class_compatibility",
            "world_styles",
            "world_style_id",
            "card_classes",
            "class_id",
        )

    def class_role_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CompatibilityFact, ...]:
        return self._compatibility(
            ruleset,
            "class_role_compatibility",
            "card_classes",
            "class_id",
            "combat_roles",
            "role_id",
        )

    def class_lineage_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CompatibilityFact, ...]:
        return self._compatibility(
            ruleset,
            "class_lineage_compatibility",
            "card_classes",
            "class_id",
            "trait_lineages",
            "lineage_id",
        )

    def role_lineage_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[CompatibilityFact, ...]:
        return self._compatibility(
            ruleset,
            "role_lineage_compatibility",
            "combat_roles",
            "role_id",
            "trait_lineages",
            "lineage_id",
        )

    def fallback_world_styles(
        self,
        policy: CardBattlerMappingPolicy,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[FallbackCandidate, ...]:
        return self._fallback(
            ruleset,
            policy,
            "mapping_fallback_world_styles",
            "world_styles",
            "world_style_id",
        )

    def fallback_classes(
        self,
        policy: CardBattlerMappingPolicy,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[FallbackCandidate, ...]:
        return self._fallback(
            ruleset,
            policy,
            "mapping_fallback_classes",
            "card_classes",
            "class_id",
        )

    def fallback_roles(
        self,
        policy: CardBattlerMappingPolicy,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[FallbackCandidate, ...]:
        return self._fallback(
            ruleset,
            policy,
            "mapping_fallback_roles",
            "combat_roles",
            "role_id",
        )

    def fallback_lineages(
        self,
        policy: CardBattlerMappingPolicy,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[FallbackCandidate, ...]:
        return self._fallback(
            ruleset,
            policy,
            "mapping_fallback_lineages",
            "trait_lineages",
            "lineage_id",
        )

    def summary(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> CardBattlerModelSummary:
        with self._validated_connection() as connection:
            ruleset_id, resolved = self._resolve_ruleset_ref(
                connection, ruleset
            )
            vocabulary_id = self._vocabulary_id(connection, resolved)
            return CardBattlerModelSummary(
                semantic_concept_count=self._count(
                    connection,
                    "semantic_concepts",
                    "vocabulary_id",
                    vocabulary_id,
                ),
                world_style_count=self._count(
                    connection, "world_styles", "ruleset_id", ruleset_id
                ),
                card_class_count=self._count(
                    connection, "card_classes", "ruleset_id", ruleset_id
                ),
                combat_role_count=self._count(
                    connection, "combat_roles", "ruleset_id", ruleset_id
                ),
                trait_lineage_count=self._count(
                    connection, "trait_lineages", "ruleset_id", ruleset_id
                ),
                development_tier_count=self._count(
                    connection,
                    "development_tiers",
                    "ruleset_id",
                    ruleset_id,
                    active_only=False,
                ),
                mechanic_template_count=self._count(
                    connection,
                    "mechanic_templates",
                    "ruleset_id",
                    ruleset_id,
                ),
                prompt_atom_count=self._count(
                    connection,
                    "visual_prompt_atoms",
                    "ruleset_id",
                    ruleset_id,
                ),
                integrity_ok=True,
                foreign_key_violation_count=0,
            )

    @contextmanager
    def _validated_connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._open_connection()
        try:
            self._validate_connection(connection)
            yield connection
        except (
            CardBattlerModelInvalid,
            CardBattlerModelNotFound,
            CardBattlerModelVersionUnsupported,
        ):
            raise
        except (
            sqlite3.DatabaseError,
            KeyError,
            TypeError,
            ValueError,
        ) as error:
            raise self._invalid(str(error)) from error
        finally:
            connection.close()

    def _open_connection(self) -> sqlite3.Connection:
        path = self._database_path.expanduser().resolve()
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

    def _validate_connection(self, connection: sqlite3.Connection) -> None:
        self._validate_metadata_schema(connection)
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
        self._validate_foundational_schema(connection)
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
        self._resolve_ruleset(connection, None, None)

    def _validate_metadata_schema(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        table = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name = 'schema_meta'
            """
        ).fetchone()
        if table is None:
            raise self._invalid("missing required table: schema_meta")
        columns = {
            str(row["name"])
            for row in connection.execute(
                "PRAGMA table_info(schema_meta)"
            ).fetchall()
        }
        missing = sorted(_REQUIRED_COLUMNS["schema_meta"] - columns)
        if missing:
            raise self._invalid(
                "table 'schema_meta' is missing required column(s): "
                + ", ".join(missing)
            )

    def _validate_foundational_schema(
        self,
        connection: sqlite3.Connection,
    ) -> None:
        table_rows = connection.execute(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table' AND name NOT LIKE 'sqlite_%'
            """
        ).fetchall()
        available = {str(row["name"]) for row in table_rows}
        missing = sorted(_REQUIRED_COLUMNS.keys() - available)
        if missing:
            raise self._invalid(
                "missing required table(s): " + ", ".join(missing)
            )
        for table, required in _REQUIRED_COLUMNS.items():
            columns = {
                str(row["name"])
                for row in connection.execute(
                    f"PRAGMA table_info({table})"
                ).fetchall()
            }
            missing_columns = sorted(required - columns)
            if missing_columns:
                raise self._invalid(
                    f"table {table!r} is missing required column(s): "
                    + ", ".join(missing_columns)
                )

    def _read_metadata(
        self,
        connection: sqlite3.Connection,
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

    def _resolve_ruleset(
        self,
        connection: sqlite3.Connection,
        key: str | None,
        version: int | None,
    ) -> tuple[int, CardBattlerRulesetRef]:
        if version is not None and key is None:
            raise self._invalid("ruleset version requires a ruleset key")
        clauses: list[str] = []
        parameters: list[object] = []
        if key is None:
            clauses.append("rulesets.status = 'active'")
        else:
            clauses.append("rulesets.ruleset_key = ?")
            parameters.append(key)
        if version is not None:
            clauses.append("rulesets.version = ?")
            parameters.append(version)
        where_clause = " AND ".join(clauses)
        rows = connection.execute(
            f"""
            SELECT rulesets.id, rulesets.ruleset_key, rulesets.version,
                   rulesets.name, rulesets.status, rulesets.description,
                   vocabularies.vocabulary_key,
                   vocabularies.version AS vocabulary_version
            FROM rulesets
            JOIN semantic_vocabularies AS vocabularies
              ON vocabularies.id = rulesets.semantic_vocabulary_id
            WHERE {where_clause}
            ORDER BY rulesets.version DESC,
                     rulesets.ruleset_key COLLATE BINARY
            """,
            tuple(parameters),
        ).fetchall()
        if not rows:
            requested = "active ruleset" if key is None else repr(key)
            if version is not None:
                requested += f" version {version}"
            raise self._invalid(f"cannot resolve {requested}")
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

    def _resolve_ruleset_ref(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> tuple[int, CardBattlerRulesetRef]:
        if ruleset is None:
            return self._resolve_ruleset(connection, None, None)
        return self._resolve_ruleset(
            connection,
            ruleset.key,
            ruleset.version,
        )

    def _vocabulary_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef,
    ) -> int:
        row = connection.execute(
            """
            SELECT id
            FROM semantic_vocabularies
            WHERE vocabulary_key = ? AND version = ?
            """,
            (
                ruleset.semantic_vocabulary_key,
                ruleset.semantic_vocabulary_version,
            ),
        ).fetchone()
        if row is None:
            raise self._invalid(
                "ruleset semantic vocabulary cannot be resolved"
            )
        return int(row["id"])

    @staticmethod
    def _semantic_aliases(
        connection: sqlite3.Connection,
        vocabulary_id: int,
    ) -> dict[int, tuple[str, ...]]:
        rows = connection.execute(
            """
            SELECT concept_id, alias
            FROM semantic_aliases
            WHERE vocabulary_id = ?
            ORDER BY concept_id, alias COLLATE BINARY
            """,
            (vocabulary_id,),
        ).fetchall()
        grouped: dict[int, list[str]] = {}
        for row in rows:
            grouped.setdefault(int(row["concept_id"]), []).append(
                str(row["alias"])
            )
        return {key: tuple(values) for key, values in grouped.items()}

    @staticmethod
    def _dimension_rows(
        connection: sqlite3.Connection,
        table: str,
        ruleset_id: int,
    ) -> tuple[sqlite3.Row, ...]:
        if table not in {"card_classes", "combat_roles", "trait_lineages"}:
            raise ValueError(
                f"unsupported Card Battler dimension table: {table}"
            )
        rows = connection.execute(
            f"""
            SELECT key, name, description
            FROM {table}
            WHERE ruleset_id = ? AND active = 1
            ORDER BY key COLLATE BINARY
            """,
            (ruleset_id,),
        ).fetchall()
        return tuple(rows)

    def _resolve_policy_row(
        self,
        connection: sqlite3.Connection,
        table: str,
        ruleset_id: int,
        key: str | None,
        version: int | None,
    ) -> sqlite3.Row:
        if table not in {"mapping_policies", "rng_policies"}:
            raise ValueError(f"unsupported policy table: {table}")
        if version is not None and key is None:
            raise self._invalid("policy version requires a policy key")
        clauses = ["ruleset_id = ?"]
        parameters: list[object] = [ruleset_id]
        if key is None:
            clauses.append("active = 1")
        else:
            clauses.append("policy_key = ?")
            parameters.append(key)
        if version is not None:
            clauses.append("version = ?")
            parameters.append(version)
        rows = connection.execute(
            f"SELECT * FROM {table} WHERE "
            + " AND ".join(clauses)
            + " ORDER BY version DESC, policy_key COLLATE BINARY",
            tuple(parameters),
        ).fetchall()
        if not rows:
            raise self._invalid(f"cannot resolve {table} policy")
        return rows[0]

    @staticmethod
    def _json_object(value: object, label: str) -> dict[str, object]:
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError as error:
            raise ValueError(f"{label} config_json is invalid JSON") from error
        if not isinstance(parsed, dict):
            raise ValueError(f"{label} config_json must be an object")
        return parsed

    @staticmethod
    def _config_int(
        config: dict[str, object],
        key: str,
        *,
        minimum: int = 0,
        maximum: int = 1000,
    ) -> int:
        value = config.get(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"policy field {key} must be an integer")
        if not minimum <= value <= maximum:
            raise ValueError(f"policy field {key} is out of range")
        return value

    @staticmethod
    def _config_bool(config: dict[str, object], key: str) -> bool:
        value = config.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"policy field {key} must be boolean")
        return value

    def _affinities(
        self,
        ruleset: CardBattlerRulesetRef | None,
        relation_table: str,
        entity_table: str,
        entity_id_column: str,
    ) -> tuple[SemanticAffinity, ...]:
        allowed = {
            (
                "semantic_world_style_affinity",
                "world_styles",
                "world_style_id",
            ),
            ("semantic_class_affinity", "card_classes", "class_id"),
            ("semantic_role_affinity", "combat_roles", "role_id"),
            ("semantic_lineage_affinity", "trait_lineages", "lineage_id"),
        }
        if (relation_table, entity_table, entity_id_column) not in allowed:
            raise ValueError("unsupported semantic affinity relation")
        with self._validated_connection() as connection:
            ruleset_id, resolved = self._resolve_ruleset_ref(
                connection, ruleset
            )
            vocabulary_id = self._vocabulary_id(connection, resolved)
            rows = connection.execute(
                f"""
                SELECT concepts.key AS concept_key, entities.key AS entity_key,
                       relation.weight_milli
                FROM {relation_table} AS relation
                JOIN semantic_concepts AS concepts ON concepts.id = relation.concept_id
                JOIN {entity_table} AS entities ON entities.id = relation.{entity_id_column}
                WHERE concepts.vocabulary_id = ? AND concepts.active = 1
                  AND entities.ruleset_id = ? AND entities.active = 1
                ORDER BY concepts.key COLLATE BINARY, entities.key COLLATE BINARY
                """,
                (vocabulary_id, ruleset_id),
            ).fetchall()
            return tuple(
                SemanticAffinity(
                    concept_key=str(row["concept_key"]),
                    entity_key=str(row["entity_key"]),
                    weight_milli=int(row["weight_milli"]),
                )
                for row in rows
            )

    def _compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None,
        relation_table: str,
        source_table: str,
        source_id_column: str,
        target_table: str,
        target_id_column: str,
    ) -> tuple[CompatibilityFact, ...]:
        allowed = {
            (
                "world_style_class_compatibility",
                "world_styles",
                "world_style_id",
                "card_classes",
                "class_id",
            ),
            (
                "class_role_compatibility",
                "card_classes",
                "class_id",
                "combat_roles",
                "role_id",
            ),
            (
                "class_lineage_compatibility",
                "card_classes",
                "class_id",
                "trait_lineages",
                "lineage_id",
            ),
            (
                "role_lineage_compatibility",
                "combat_roles",
                "role_id",
                "trait_lineages",
                "lineage_id",
            ),
        }
        signature = (
            relation_table,
            source_table,
            source_id_column,
            target_table,
            target_id_column,
        )
        if signature not in allowed:
            raise ValueError("unsupported compatibility relation")
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            rows = connection.execute(
                f"""
                SELECT source.key AS source_key, target.key AS target_key,
                       relation.weight_milli, relation.enabled
                FROM {relation_table} AS relation
                JOIN {source_table} AS source ON source.id = relation.{source_id_column}
                JOIN {target_table} AS target ON target.id = relation.{target_id_column}
                WHERE source.ruleset_id = ? AND target.ruleset_id = ?
                  AND source.active = 1 AND target.active = 1
                ORDER BY source.key COLLATE BINARY, target.key COLLATE BINARY
                """,
                (ruleset_id, ruleset_id),
            ).fetchall()
            return tuple(
                CompatibilityFact(
                    source_key=str(row["source_key"]),
                    target_key=str(row["target_key"]),
                    weight_milli=int(row["weight_milli"]),
                    enabled=bool(row["enabled"]),
                )
                for row in rows
            )

    def _fallback(
        self,
        ruleset: CardBattlerRulesetRef | None,
        policy: CardBattlerMappingPolicy,
        relation_table: str,
        entity_table: str,
        entity_id_column: str,
    ) -> tuple[FallbackCandidate, ...]:
        allowed = {
            (
                "mapping_fallback_world_styles",
                "world_styles",
                "world_style_id",
            ),
            ("mapping_fallback_classes", "card_classes", "class_id"),
            ("mapping_fallback_roles", "combat_roles", "role_id"),
            ("mapping_fallback_lineages", "trait_lineages", "lineage_id"),
        }
        if (relation_table, entity_table, entity_id_column) not in allowed:
            raise ValueError("unsupported mapping fallback relation")
        with self._validated_connection() as connection:
            ruleset_id, _ = self._resolve_ruleset_ref(connection, ruleset)
            policy_row = self._resolve_policy_row(
                connection,
                "mapping_policies",
                ruleset_id,
                policy.key,
                policy.version,
            )
            rows = connection.execute(
                f"""
                SELECT entities.key AS entity_key, relation.weight_milli
                FROM {relation_table} AS relation
                JOIN {entity_table} AS entities ON entities.id = relation.{entity_id_column}
                WHERE relation.mapping_policy_id = ?
                  AND entities.ruleset_id = ? AND entities.active = 1
                ORDER BY relation.weight_milli DESC, entities.key COLLATE BINARY
                """,
                (int(policy_row["id"]), ruleset_id),
            ).fetchall()
            return tuple(
                FallbackCandidate(
                    entity_key=str(row["entity_key"]),
                    weight_milli=int(row["weight_milli"]),
                )
                for row in rows
            )

    @staticmethod
    def _count(
        connection: sqlite3.Connection,
        table: str,
        foreign_key: str,
        foreign_id: int,
        *,
        active_only: bool = True,
    ) -> int:
        allowed = {
            ("semantic_concepts", "vocabulary_id"),
            ("world_styles", "ruleset_id"),
            ("card_classes", "ruleset_id"),
            ("combat_roles", "ruleset_id"),
            ("trait_lineages", "ruleset_id"),
            ("development_tiers", "ruleset_id"),
            ("mechanic_templates", "ruleset_id"),
            ("visual_prompt_atoms", "ruleset_id"),
        }
        if (table, foreign_key) not in allowed:
            raise ValueError(
                f"unsupported summary count: {table}.{foreign_key}"
            )
        active_clause = " AND active = 1" if active_only else ""
        row = connection.execute(
            f"SELECT COUNT(*) FROM {table} "
            f"WHERE {foreign_key} = ?{active_clause}",
            (foreign_id,),
        ).fetchone()
        if row is None:
            raise ValueError(f"count query returned no row for {table}")
        return int(row[0])

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._database_path}: {detail}"
        )
