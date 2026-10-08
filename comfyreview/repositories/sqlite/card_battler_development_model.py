"""SQLite reads for versioned Card Battler development policy facts."""

from __future__ import annotations

import json
import sqlite3

from comfyreview.application.card_battler_development import (
    CardDevelopmentPolicy,
    DevelopmentTierModel,
    TierDevelopmentActionWeight,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)


class SqliteCardDevelopmentModelRepository:
    """Read development-only facts from one validated immutable resource."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def development_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> CardDevelopmentPolicy:
        """Return one validated development policy without technical IDs."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            row = self._policy_row(
                connection,
                "development_policies",
                ruleset_id,
                key=key,
                version=version,
            )
            config = self._json_object(row["config_json"])
            return CardDevelopmentPolicy(
                key=str(row["policy_key"]),
                version=int(row["version"]),
                cross_lineage_requires_compatibility=self._config_bool(
                    config, "cross_lineage_requires_compatibility"
                ),
                immutable_imprint_dimensions=self._config_text_list(
                    config, "immutable_imprint_dimensions"
                ),
                legendary_locked_in_prototype=self._config_bool(
                    config, "legendary_locked_in_prototype"
                ),
                prefer_existing_lineage=self._config_bool(
                    config, "prefer_existing_lineage"
                ),
                primary_trait_actions=self._config_text_list(
                    config, "primary_trait_actions"
                ),
            )

    def development_ladder(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        balance_policy_key: str | None = None,
        balance_policy_version: int | None = None,
    ) -> tuple[DevelopmentTierModel, ...]:
        """Return a complete validated ladder for one balance policy."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            policy = self._policy_row(
                connection,
                "balance_policies",
                ruleset_id,
                key=balance_policy_key,
                version=balance_policy_version,
            )
            rows = connection.execute(
                """
                SELECT tiers.id AS tier_id, tiers.level, tiers.ordinal,
                       tiers.next_tier_id, tiers.development_locked,
                       rarities.key AS rarity_key,
                       rarities.name AS rarity_name,
                       rarities.ordinal AS rarity_ordinal,
                       rarities.max_traits AS rarity_max_traits,
                       next_tier.ordinal AS next_ordinal,
                       next_tier.ruleset_id AS next_ruleset_id,
                       profiles.stat_budget,
                       profiles.mechanic_budget_milli,
                       profiles.max_traits AS tier_max_traits,
                       profiles.parameter_scale_milli
                FROM development_tiers AS tiers
                JOIN rarities ON rarities.id = tiers.rarity_id
                LEFT JOIN development_tiers AS next_tier
                  ON next_tier.id = tiers.next_tier_id
                LEFT JOIN tier_balance_profiles AS profiles
                  ON profiles.tier_id = tiers.id
                 AND profiles.balance_policy_id = ?
                WHERE tiers.ruleset_id = ? AND rarities.ruleset_id = ?
                  AND rarities.active = 1
                ORDER BY tiers.ordinal, rarities.key COLLATE BINARY,
                         tiers.level
                """,
                (int(policy["id"]), ruleset_id, ruleset_id),
            ).fetchall()
            return self._ladder_rows(
                rows,
                ruleset_id=ruleset_id,
                balance_policy_key=str(policy["policy_key"]),
                balance_policy_version=int(policy["version"]),
            )

    def development_action_weights(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[TierDevelopmentActionWeight, ...]:
        """Return stable ID-free per-tier action weights."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT tiers.ordinal AS tier_ordinal,
                       actions.key AS action_key,
                       actions.name AS action_name,
                       actions.description AS action_description,
                       weights.weight_milli, weights.enabled
                FROM tier_development_action_weights AS weights
                JOIN development_tiers AS tiers
                  ON tiers.id = weights.tier_id
                JOIN development_action_types AS actions
                  ON actions.id = weights.action_type_id
                WHERE tiers.ruleset_id = ? AND actions.ruleset_id = ?
                  AND actions.active = 1
                ORDER BY tiers.ordinal, actions.key COLLATE BINARY
                """,
                (ruleset_id, ruleset_id),
            ).fetchall()
            results = tuple(
                TierDevelopmentActionWeight(
                    tier_ordinal=int(row["tier_ordinal"]),
                    action_key=str(row["action_key"]),
                    action_name=str(row["action_name"]),
                    action_description=str(row["action_description"]),
                    weight_milli=int(row["weight_milli"]),
                    enabled=bool(row["enabled"]),
                )
                for row in rows
            )
            keys = tuple(
                (item.tier_ordinal, item.action_key) for item in results
            )
            if len(keys) != len(set(keys)):
                raise self._invalid("development action weights are ambiguous")
            return results

    def _ladder_rows(
        self,
        rows: list[sqlite3.Row],
        *,
        ruleset_id: int,
        balance_policy_key: str,
        balance_policy_version: int,
    ) -> tuple[DevelopmentTierModel, ...]:
        if not rows:
            raise self._invalid("development ladder is empty")
        ordinals = tuple(int(row["ordinal"]) for row in rows)
        if len(ordinals) != len(set(ordinals)):
            raise self._invalid("development tier ordinals are ambiguous")
        for index, row in enumerate(rows):
            self._validate_ladder_row(
                row,
                ruleset_id=ruleset_id,
                expected_next_ordinal=(
                    int(rows[index + 1]["ordinal"])
                    if index + 1 < len(rows)
                    else None
                ),
            )
        return tuple(
            DevelopmentTierModel(
                rarity_key=str(row["rarity_key"]),
                rarity_name=str(row["rarity_name"]),
                rarity_ordinal=int(row["rarity_ordinal"]),
                level=int(row["level"]),
                ordinal=int(row["ordinal"]),
                next_ordinal=(
                    int(row["next_ordinal"])
                    if row["next_ordinal"] is not None
                    else None
                ),
                development_locked=bool(row["development_locked"]),
                balance_policy_key=balance_policy_key,
                balance_policy_version=balance_policy_version,
                stat_budget=int(row["stat_budget"]),
                mechanic_budget_milli=int(row["mechanic_budget_milli"]),
                trait_cap=int(row["tier_max_traits"]),
                parameter_scale_milli=int(row["parameter_scale_milli"]),
            )
            for row in rows
        )

    def _validate_ladder_row(
        self,
        row: sqlite3.Row,
        *,
        ruleset_id: int,
        expected_next_ordinal: int | None,
    ) -> None:
        if row["stat_budget"] is None:
            raise self._invalid(
                "development tier is missing a balance profile"
            )
        if (
            row["next_tier_id"] is not None
            and row["next_ruleset_id"] != ruleset_id
        ):
            raise self._invalid("development tier points to another ruleset")
        actual_next = (
            int(row["next_ordinal"])
            if row["next_ordinal"] is not None
            else None
        )
        if actual_next != expected_next_ordinal:
            raise self._invalid("development tiers do not form one ladder")
        tier_cap = int(row["tier_max_traits"])
        rarity_cap = int(row["rarity_max_traits"])
        if tier_cap < 0 or tier_cap > rarity_cap:
            raise self._invalid("development tier trait cap is invalid")

    def _ruleset_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> int:
        if ruleset is None:
            return self._resource.validation().active_ruleset_id
        rows = connection.execute(
            """
            SELECT id
            FROM rulesets
            WHERE ruleset_key = ? AND version = ?
            ORDER BY id
            """,
            (ruleset.key, ruleset.version),
        ).fetchall()
        if len(rows) != 1:
            raise self._invalid(
                f"cannot resolve ruleset {ruleset.key!r} version "
                f"{ruleset.version}"
            )
        return int(rows[0]["id"])

    def _policy_row(
        self,
        connection: sqlite3.Connection,
        table: str,
        ruleset_id: int,
        *,
        key: str | None,
        version: int | None,
    ) -> sqlite3.Row:
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
    def _json_object(value: object) -> dict[str, object]:
        try:
            parsed = json.loads(str(value))
        except json.JSONDecodeError as error:
            raise ValueError(
                "development policy config_json is invalid JSON"
            ) from error
        if not isinstance(parsed, dict):
            raise ValueError(
                "development policy config_json must be an object"
            )
        return parsed

    @staticmethod
    def _config_bool(config: dict[str, object], key: str) -> bool:
        value = config.get(key)
        if not isinstance(value, bool):
            raise ValueError(f"development policy field {key} must be boolean")
        return value

    @staticmethod
    def _config_text_list(
        config: dict[str, object], key: str
    ) -> tuple[str, ...]:
        value = config.get(key)
        if not isinstance(value, list) or not value:
            raise ValueError(
                f"development policy field {key} must be a non-empty list"
            )
        items = tuple(value)
        if any(not isinstance(item, str) or not item for item in items):
            raise ValueError(
                f"development policy field {key} must contain text"
            )
        if len(items) != len(set(items)):
            raise ValueError(
                f"development policy field {key} contains duplicates"
            )
        return items

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
