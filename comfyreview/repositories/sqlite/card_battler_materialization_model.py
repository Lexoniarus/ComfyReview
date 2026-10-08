"""SQLite reads for Card Battler balance and stat-profile model facts."""

from __future__ import annotations

import json
import sqlite3

from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    StatProfileAffinity,
    StatProfileAffinitySource,
    StatProfileDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)


class SqliteCardMaterializationModelRepository:
    """Read focused materialization facts from one validated model resource."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def balance_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardBalancePolicy:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            row = self._policy_row(
                connection, ruleset_id, key=key, version=version
            )
            config = self._json_object(row["config_json"])
            return CardBalancePolicy(
                key=str(row["policy_key"]),
                version=int(row["version"]),
                stat_rounding_step=self._config_int(
                    config, "stat_rounding_step", minimum=1
                ),
                atk_def_minimum=self._config_int(
                    config, "atk_def_minimum", minimum=0
                ),
                no_negative_stats=self._config_bool(
                    config, "no_negative_stats"
                ),
                trait_budget_is_milli=self._config_bool(
                    config, "trait_budget_is_milli"
                ),
                calibration_status=self._config_text(
                    config, "calibration_status"
                ),
            )

    def tier_balance_profile(
        self,
        balance_policy: CardBalancePolicy,
        *,
        rarity_key: str,
        level: int,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> TierBalanceProfile:
        if not rarity_key:
            raise ValueError("rarity_key must not be empty")
        if level < 1:
            raise ValueError("tier level must be positive")
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT rarities.key AS rarity_key, tiers.level, tiers.ordinal,
                       profiles.stat_budget,
                       profiles.mechanic_budget_milli,
                       profiles.min_atk, profiles.max_atk,
                       profiles.min_def, profiles.max_def,
                       profiles.max_traits,
                       profiles.parameter_scale_milli
                FROM tier_balance_profiles AS profiles
                JOIN development_tiers AS tiers ON tiers.id = profiles.tier_id
                JOIN rarities ON rarities.id = tiers.rarity_id
                JOIN balance_policies AS policies
                  ON policies.id = profiles.balance_policy_id
                WHERE tiers.ruleset_id = ? AND rarities.ruleset_id = ?
                  AND rarities.key = ? AND tiers.level = ?
                  AND policies.ruleset_id = ? AND policies.policy_key = ?
                  AND policies.version = ?
                ORDER BY tiers.ordinal
                """,
                (
                    ruleset_id,
                    ruleset_id,
                    rarity_key,
                    level,
                    ruleset_id,
                    balance_policy.key,
                    balance_policy.version,
                ),
            ).fetchall()
            if len(rows) != 1:
                raise self._invalid(
                    "cannot resolve exactly one tier balance profile for "
                    f"{rarity_key} level {level}"
                )
            row = rows[0]
            return TierBalanceProfile(
                rarity_key=str(row["rarity_key"]),
                level=int(row["level"]),
                ordinal=int(row["ordinal"]),
                stat_budget=int(row["stat_budget"]),
                mechanic_budget_milli=int(row["mechanic_budget_milli"]),
                min_atk=int(row["min_atk"]),
                max_atk=int(row["max_atk"]),
                min_def=int(row["min_def"]),
                max_def=int(row["max_def"]),
                max_traits=int(row["max_traits"]),
                parameter_scale_milli=int(row["parameter_scale_milli"]),
            )

    def stat_profiles(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[StatProfileDefinition, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT key, name, atk_share_milli, def_share_milli,
                       description
                FROM stat_profiles
                WHERE ruleset_id = ? AND active = 1
                ORDER BY key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            return tuple(
                StatProfileDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    atk_share_milli=int(row["atk_share_milli"]),
                    def_share_milli=int(row["def_share_milli"]),
                    description=str(row["description"]),
                )
                for row in rows
            )

    def stat_profile_affinities(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[StatProfileAffinity, ...]:
        facts: list[StatProfileAffinity] = []
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            relations: tuple[
                tuple[StatProfileAffinitySource, str, str, str], ...
            ] = (
                (
                    "class",
                    "class_stat_profile_affinity",
                    "card_classes",
                    "class_id",
                ),
                (
                    "role",
                    "role_stat_profile_affinity",
                    "combat_roles",
                    "role_id",
                ),
                (
                    "lineage",
                    "lineage_stat_profile_affinity",
                    "trait_lineages",
                    "lineage_id",
                ),
            )
            for source, relation, entities, entity_id in relations:
                rows = connection.execute(
                    f"""
                    SELECT values_.key AS source_key,
                           profiles.key AS stat_profile_key,
                           affinity.weight_milli
                    FROM {relation} AS affinity
                    JOIN {entities} AS values_
                      ON values_.id = affinity.{entity_id}
                    JOIN stat_profiles AS profiles
                      ON profiles.id = affinity.stat_profile_id
                    WHERE values_.ruleset_id = ? AND values_.active = 1
                      AND profiles.ruleset_id = ? AND profiles.active = 1
                    ORDER BY values_.key COLLATE BINARY,
                             profiles.key COLLATE BINARY
                    """,
                    (ruleset_id, ruleset_id),
                ).fetchall()
                facts.extend(
                    StatProfileAffinity(
                        source=source,
                        source_key=str(row["source_key"]),
                        stat_profile_key=str(row["stat_profile_key"]),
                        weight_milli=int(row["weight_milli"]),
                    )
                    for row in rows
                )
        return tuple(
            sorted(
                facts,
                key=lambda fact: (
                    fact.source,
                    fact.source_key,
                    fact.stat_profile_key,
                ),
            )
        )

    def _ruleset_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> int:
        if ruleset is None:
            return self._resource.validation().active_ruleset_id
        row = connection.execute(
            """
            SELECT id
            FROM rulesets
            WHERE ruleset_key = ? AND version = ?
            """,
            (ruleset.key, ruleset.version),
        ).fetchone()
        if row is None:
            raise self._invalid(
                f"cannot resolve ruleset {ruleset.key!r} version "
                f"{ruleset.version}"
            )
        return int(row["id"])

    def _policy_row(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
        *,
        key: str | None,
        version: int | None,
    ) -> sqlite3.Row:
        if version is not None and key is None:
            raise self._invalid("balance policy version requires a policy key")
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
            "SELECT * FROM balance_policies WHERE "
            + " AND ".join(clauses)
            + " ORDER BY version DESC, policy_key COLLATE BINARY",
            tuple(parameters),
        ).fetchall()
        if not rows:
            raise self._invalid("cannot resolve balance policy")
        return rows[0]

    @staticmethod
    def _json_object(value: object) -> dict[str, object]:
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError as error:
            raise ValueError(
                "balance policy config_json is invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise ValueError("balance policy config_json must be an object")
        return parsed

    @staticmethod
    def _config_int(
        config: dict[str, object], key: str, *, minimum: int
    ) -> int:
        value = config.get(key)
        if (
            not isinstance(value, int)
            or isinstance(value, bool)
            or value < minimum
        ):
            raise ValueError(f"balance policy field {key} is invalid")
        return value

    @staticmethod
    def _config_bool(config: dict[str, object], key: str) -> bool:
        value = config.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"balance policy field {key} must be boolean")
        return value

    @staticmethod
    def _config_text(config: dict[str, object], key: str) -> str:
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"balance policy field {key} must be text")
        return value

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
