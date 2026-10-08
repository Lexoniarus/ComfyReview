"""Focused SQLite reader for Card Battler development progression facts."""

from __future__ import annotations

import sqlite3
from typing import cast

from comfyreview.application.card_battler_development import (
    MechanicParameterProgression,
    MechanicUpgradeEdge,
    MechanicUpgradeKind,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)

_UPGRADE_KINDS = frozenset({"replace", "branch", "augment"})


class _SqliteCardDevelopmentProgressionReader:
    """Assemble ID-free upgrade and parameter-progression facts."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def mechanic_upgrade_edges(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicUpgradeEdge, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT source.key AS from_mechanic_key,
                       target.key AS to_mechanic_key,
                       source.active AS source_active,
                       target.active AS target_active,
                       target.ruleset_id AS target_ruleset_id,
                       min_tier.ordinal AS min_tier_ordinal,
                       min_tier.ruleset_id AS min_tier_ruleset_id,
                       max_tier.ordinal AS max_tier_ordinal,
                       max_tier.ruleset_id AS max_tier_ruleset_id,
                       edges.weight_milli, edges.upgrade_kind, edges.notes
                FROM mechanic_upgrade_edges AS edges
                JOIN mechanic_templates AS source
                  ON source.id = edges.from_mechanic_id
                JOIN mechanic_templates AS target
                  ON target.id = edges.to_mechanic_id
                JOIN development_tiers AS min_tier
                  ON min_tier.id = edges.min_tier_id
                LEFT JOIN development_tiers AS max_tier
                  ON max_tier.id = edges.max_tier_id
                WHERE source.ruleset_id = ?
                ORDER BY source.key COLLATE BINARY,
                         target.key COLLATE BINARY, min_tier.ordinal
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                self._upgrade_edge(row, ruleset_id=ruleset_id) for row in rows
            )
            keys = tuple(
                (
                    item.from_mechanic_key,
                    item.to_mechanic_key,
                    item.min_tier_ordinal,
                )
                for item in results
            )
            if len(keys) != len(set(keys)):
                raise self._invalid("mechanic upgrade edges are ambiguous")
            return results

    def mechanic_parameter_progression(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicParameterProgression, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT mechanics.key AS mechanic_key,
                       parameters.param_key AS parameter_key,
                       min_tier.ordinal AS min_tier_ordinal,
                       min_tier.ruleset_id AS min_tier_ruleset_id,
                       max_tier.ordinal AS max_tier_ordinal,
                       max_tier.ruleset_id AS max_tier_ruleset_id,
                       progression.upgrade_step_int,
                       progression.max_upgrade_steps,
                       progression.budget_cost_milli
                FROM mechanic_parameter_progression AS progression
                JOIN mechanic_parameters AS parameters
                  ON parameters.id = progression.parameter_id
                JOIN mechanic_templates AS mechanics
                  ON mechanics.id = parameters.mechanic_template_id
                JOIN development_tiers AS min_tier
                  ON min_tier.id = progression.min_tier_id
                LEFT JOIN development_tiers AS max_tier
                  ON max_tier.id = progression.max_tier_id
                WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
                ORDER BY mechanics.key COLLATE BINARY,
                         parameters.param_key COLLATE BINARY,
                         min_tier.ordinal
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                self._parameter_progression(row, ruleset_id=ruleset_id)
                for row in rows
            )
            keys = tuple(
                (
                    item.mechanic_key,
                    item.parameter_key,
                    item.min_tier_ordinal,
                )
                for item in results
            )
            if len(keys) != len(set(keys)):
                raise self._invalid(
                    "mechanic parameter progression is ambiguous"
                )
            return results

    def _upgrade_edge(
        self, row: sqlite3.Row, *, ruleset_id: int
    ) -> MechanicUpgradeEdge:
        if (
            not bool(row["source_active"])
            or not bool(row["target_active"])
            or int(row["target_ruleset_id"]) != ruleset_id
        ):
            raise self._invalid(
                "mechanic upgrade edge references an unavailable mechanic"
            )
        minimum, maximum = self._tier_range(row, ruleset_id=ruleset_id)
        weight = int(row["weight_milli"])
        if weight < 0 or weight > 1000:
            raise self._invalid("mechanic upgrade edge weight is invalid")
        kind = str(row["upgrade_kind"])
        if kind not in _UPGRADE_KINDS:
            raise self._invalid("mechanic upgrade kind is invalid")
        return MechanicUpgradeEdge(
            from_mechanic_key=str(row["from_mechanic_key"]),
            to_mechanic_key=str(row["to_mechanic_key"]),
            min_tier_ordinal=minimum,
            max_tier_ordinal=maximum,
            weight_milli=weight,
            upgrade_kind=cast(MechanicUpgradeKind, kind),
            notes=str(row["notes"]) if row["notes"] is not None else None,
        )

    def _parameter_progression(
        self, row: sqlite3.Row, *, ruleset_id: int
    ) -> MechanicParameterProgression:
        minimum, maximum = self._tier_range(row, ruleset_id=ruleset_id)
        maximum_steps = (
            int(row["max_upgrade_steps"])
            if row["max_upgrade_steps"] is not None
            else None
        )
        budget = int(row["budget_cost_milli"])
        if maximum_steps is not None and maximum_steps < 0:
            raise self._invalid("maximum parameter upgrade steps are invalid")
        if budget < 0:
            raise self._invalid("parameter progression budget is invalid")
        return MechanicParameterProgression(
            mechanic_key=str(row["mechanic_key"]),
            parameter_key=str(row["parameter_key"]),
            min_tier_ordinal=minimum,
            max_tier_ordinal=maximum,
            upgrade_step_int=(
                int(row["upgrade_step_int"])
                if row["upgrade_step_int"] is not None
                else None
            ),
            max_upgrade_steps=maximum_steps,
            budget_cost_milli=budget,
        )

    def _tier_range(
        self, row: sqlite3.Row, *, ruleset_id: int
    ) -> tuple[int, int | None]:
        if int(row["min_tier_ruleset_id"]) != ruleset_id or (
            row["max_tier_ruleset_id"] is not None
            and int(row["max_tier_ruleset_id"]) != ruleset_id
        ):
            raise self._invalid("development progression crosses rulesets")
        minimum = int(row["min_tier_ordinal"])
        maximum = (
            int(row["max_tier_ordinal"])
            if row["max_tier_ordinal"] is not None
            else None
        )
        if maximum is not None and maximum < minimum:
            raise self._invalid(
                "development progression tier range is invalid"
            )
        return minimum, maximum

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

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
