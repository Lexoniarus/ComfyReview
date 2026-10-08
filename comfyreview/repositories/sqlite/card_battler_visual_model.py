"""Read-only SQLite adapter for Card Battler visual projection facts."""

from __future__ import annotations

import json
import sqlite3

from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_visual_model import (
    PromptGroupDefinition,
    VisualProgressionProfile,
    VisualProjectionPolicy,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)

_STABLE_ORDER_FIELDS = frozenset(
    {"priority_asc", "source_type_asc", "atom_key_asc"}
)


class SqliteCardVisualModelRepository:
    """Read focused visual facts through one validated model resource."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def projection_policy(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
        *,
        key: str | None = None,
        version: int | None = None,
    ) -> VisualProjectionPolicy:
        """Resolve and validate one projection policy."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            clauses = ["ruleset_id = ?", "active = 1"]
            parameters: list[object] = [ruleset_id]
            if key is not None:
                clauses.append("policy_key = ?")
                parameters.append(key)
            if version is not None:
                clauses.append("version = ?")
                parameters.append(version)
            rows = connection.execute(
                "SELECT policy_key, version, config_json "
                "FROM prompt_projection_policies WHERE "
                + " AND ".join(clauses)
                + " ORDER BY version DESC, policy_key COLLATE BINARY",
                tuple(parameters),
            ).fetchall()
            if len(rows) != 1:
                raise self._invalid(
                    "visual projection policy cannot be resolved uniquely"
                )
            config = self._json_object(rows[0]["config_json"])
            stable_order = self._text_tuple(config, "stable_order")
            if set(stable_order) != _STABLE_ORDER_FIELDS:
                raise self._invalid(
                    "visual projection stable order is invalid"
                )
            return VisualProjectionPolicy(
                key=str(rows[0]["policy_key"]),
                version=int(rows[0]["version"]),
                apply_intensity_channels=self._boolean(
                    config, "apply_intensity_channels"
                ),
                origin_semantics_are_upstream_inputs=self._boolean(
                    config, "origin_semantics_are_upstream_inputs"
                ),
                render_syntax=self._text(config, "render_syntax"),
                respect_exclusion_groups=self._boolean(
                    config, "respect_exclusion_groups"
                ),
                respect_forbidden_bindings=self._boolean(
                    config, "respect_forbidden_bindings"
                ),
                stable_order=stable_order,
                weight_decimals=self._integer(
                    config, "weight_decimals", minimum=0
                ),
                weight_scale=self._integer(config, "weight_scale", minimum=1),
            )

    def progression_profiles(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[VisualProgressionProfile, ...]:
        """Return validated per-tier visual intensity profiles."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT tiers.ordinal,
                       profiles.world_intensity_milli,
                       profiles.class_intensity_milli,
                       profiles.role_intensity_milli,
                       profiles.lineage_intensity_milli,
                       profiles.mechanic_intensity_milli,
                       profiles.semantic_preservation_milli
                FROM visual_progression_profiles AS profiles
                JOIN development_tiers AS tiers ON tiers.id = profiles.tier_id
                WHERE tiers.ruleset_id = ?
                ORDER BY tiers.ordinal
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                VisualProgressionProfile(
                    tier_ordinal=int(row["ordinal"]),
                    world_intensity_milli=self._milli(
                        row["world_intensity_milli"]
                    ),
                    class_intensity_milli=self._milli(
                        row["class_intensity_milli"]
                    ),
                    role_intensity_milli=self._milli(
                        row["role_intensity_milli"]
                    ),
                    lineage_intensity_milli=self._milli(
                        row["lineage_intensity_milli"]
                    ),
                    mechanic_intensity_milli=self._milli(
                        row["mechanic_intensity_milli"]
                    ),
                    semantic_preservation_milli=self._milli(
                        row["semantic_preservation_milli"]
                    ),
                )
                for row in rows
            )
            ordinals = tuple(item.tier_ordinal for item in results)
            if not results or len(ordinals) != len(set(ordinals)):
                raise self._invalid(
                    "visual progression requires one profile per tier"
                )
            return results

    def prompt_groups(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[PromptGroupDefinition, ...]:
        """Return validated prompt groups in stable key order."""
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT key, name, min_selected, max_selected, description
                FROM prompt_groups
                WHERE ruleset_id = ?
                ORDER BY key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                PromptGroupDefinition(
                    key=str(row["key"]),
                    name=str(row["name"]),
                    min_selected=int(row["min_selected"]),
                    max_selected=int(row["max_selected"]),
                    description=str(row["description"]),
                )
                for row in rows
            )
            keys = tuple(item.key for item in results)
            if len(keys) != len(set(keys)) or any(
                not item.key
                or item.min_selected < 0
                or item.max_selected < item.min_selected
                for item in results
            ):
                raise self._invalid("visual prompt groups are invalid")
            return results

    def _ruleset_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> int:
        if ruleset is None:
            return self._resource.validation().active_ruleset_id
        rows = connection.execute(
            "SELECT id FROM rulesets WHERE ruleset_key = ? AND version = ?",
            (ruleset.key, ruleset.version),
        ).fetchall()
        if len(rows) != 1:
            raise self._invalid(
                f"cannot resolve ruleset {ruleset.key!r} version {ruleset.version}"
            )
        return int(rows[0]["id"])

    @staticmethod
    def _json_object(raw: object) -> dict[str, object]:
        value = json.loads(str(raw))
        if not isinstance(value, dict):
            raise ValueError("visual projection config must be a JSON object")
        return {str(key): item for key, item in value.items()}

    @staticmethod
    def _boolean(config: dict[str, object], key: str) -> bool:
        value = config.get(key)
        if not isinstance(value, bool):
            raise ValueError(
                f"visual projection config {key!r} must be boolean"
            )
        return value

    @staticmethod
    def _text(config: dict[str, object], key: str) -> str:
        value = config.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"visual projection config {key!r} must be text")
        return value

    @staticmethod
    def _integer(config: dict[str, object], key: str, *, minimum: int) -> int:
        value = config.get(key)
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < minimum
        ):
            raise ValueError(
                f"visual projection config {key!r} must be an integer"
            )
        return value

    @staticmethod
    def _text_tuple(config: dict[str, object], key: str) -> tuple[str, ...]:
        value = config.get(key)
        if (
            not isinstance(value, list)
            or not value
            or any(not isinstance(item, str) or not item for item in value)
        ):
            raise ValueError(
                f"visual projection config {key!r} must be text list"
            )
        return tuple(value)

    @staticmethod
    def _milli(raw: object) -> int:
        if isinstance(raw, bool) or not isinstance(raw, int):
            raise ValueError("visual progression intensity is invalid")
        value = raw
        if value < 0 or value > 2000:
            raise ValueError("visual progression intensity is invalid")
        return value

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
