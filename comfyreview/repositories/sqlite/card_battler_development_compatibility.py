"""Focused SQLite reader for symmetric Card Battler compatibility facts."""

from __future__ import annotations

import sqlite3
from typing import cast

from comfyreview.application.card_battler_development import (
    CompatibilityRelation,
    LineageCompatibility,
    MechanicCompatibility,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)

_RELATIONS = frozenset({"preferred", "compatible", "neutral", "incompatible"})


class _SqliteCardDevelopmentCompatibilityReader:
    """Assemble canonical ID-free symmetric compatibility relations."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def lineage_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[LineageCompatibility, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT first.key AS first_key, second.key AS second_key,
                       first.ruleset_id AS first_ruleset_id,
                       second.ruleset_id AS second_ruleset_id,
                       first.active AS first_active,
                       second.active AS second_active,
                       facts.relation, facts.weight_milli, facts.notes
                FROM lineage_compatibility AS facts
                JOIN trait_lineages AS first
                  ON first.id = facts.lineage_a_id
                JOIN trait_lineages AS second
                  ON second.id = facts.lineage_b_id
                WHERE first.ruleset_id = ?
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                LineageCompatibility(
                    lineage_a_key=first,
                    lineage_b_key=second,
                    relation=relation,
                    weight_milli=weight,
                    notes=notes,
                )
                for first, second, relation, weight, notes in (
                    self._fact(row, ruleset_id=ruleset_id) for row in rows
                )
            )
            return self._unique_lineages(results)

    def mechanic_compatibility(
        self,
        ruleset: CardBattlerRulesetRef | None = None,
    ) -> tuple[MechanicCompatibility, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT first.key AS first_key, second.key AS second_key,
                       first.ruleset_id AS first_ruleset_id,
                       second.ruleset_id AS second_ruleset_id,
                       first.active AS first_active,
                       second.active AS second_active,
                       facts.relation, facts.weight_milli, facts.notes
                FROM mechanic_compatibility AS facts
                JOIN mechanic_templates AS first
                  ON first.id = facts.mechanic_a_id
                JOIN mechanic_templates AS second
                  ON second.id = facts.mechanic_b_id
                WHERE first.ruleset_id = ?
                """,
                (ruleset_id,),
            ).fetchall()
            results = tuple(
                MechanicCompatibility(
                    mechanic_a_key=first,
                    mechanic_b_key=second,
                    relation=relation,
                    weight_milli=weight,
                    notes=notes,
                )
                for first, second, relation, weight, notes in (
                    self._fact(row, ruleset_id=ruleset_id) for row in rows
                )
            )
            return self._unique_mechanics(results)

    def _fact(
        self, row: sqlite3.Row, *, ruleset_id: int
    ) -> tuple[str, str, CompatibilityRelation, int, str | None]:
        if (
            int(row["first_ruleset_id"]) != ruleset_id
            or int(row["second_ruleset_id"]) != ruleset_id
            or not bool(row["first_active"])
            or not bool(row["second_active"])
        ):
            raise self._invalid(
                "development compatibility references an unavailable value"
            )
        first, second = sorted((str(row["first_key"]), str(row["second_key"])))
        if first == second:
            raise self._invalid(
                "development compatibility cannot be reflexive"
            )
        relation = str(row["relation"])
        if relation not in _RELATIONS:
            raise self._invalid(
                "development compatibility relation is invalid"
            )
        weight = int(row["weight_milli"])
        if weight < 0 or weight > 1000:
            raise self._invalid("development compatibility weight is invalid")
        return (
            first,
            second,
            cast(CompatibilityRelation, relation),
            weight,
            str(row["notes"]) if row["notes"] is not None else None,
        )

    def _unique_lineages(
        self, facts: tuple[LineageCompatibility, ...]
    ) -> tuple[LineageCompatibility, ...]:
        ordered = tuple(
            sorted(
                facts,
                key=lambda item: (item.lineage_a_key, item.lineage_b_key),
            )
        )
        keys = tuple(
            (item.lineage_a_key, item.lineage_b_key) for item in ordered
        )
        if len(keys) != len(set(keys)):
            raise self._invalid("lineage compatibility is ambiguous")
        return ordered

    def _unique_mechanics(
        self, facts: tuple[MechanicCompatibility, ...]
    ) -> tuple[MechanicCompatibility, ...]:
        ordered = tuple(
            sorted(
                facts,
                key=lambda item: (item.mechanic_a_key, item.mechanic_b_key),
            )
        )
        keys = tuple(
            (item.mechanic_a_key, item.mechanic_b_key) for item in ordered
        )
        if len(keys) != len(set(keys)):
            raise self._invalid("mechanic compatibility is ambiguous")
        return ordered

    def _ruleset_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> int:
        if ruleset is None:
            return self._resource.validation().active_ruleset_id
        rows = connection.execute(
            """
            SELECT id FROM rulesets
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
