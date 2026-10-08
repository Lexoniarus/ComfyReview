"""Focused SQLite reads for Card Battler mechanic catalog facts."""

from __future__ import annotations

import sqlite3
from collections import defaultdict

from comfyreview.application.card_battler_materialization import (
    LineageMechanicEligibility,
    MechanicAffinity,
    MechanicAffinitySource,
    MechanicTemplateDefinition,
    MechanicUsageLimitDefinition,
    RuleTextTemplateDefinition,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)


class _SqliteCardMechanicModelReader:
    """Read mechanic facts for the materialization repository facade."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def definitions(
        self,
        ruleset: CardBattlerRulesetRef | None,
    ) -> tuple[MechanicTemplateDefinition, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            templates = connection.execute(
                """
                SELECT mechanics.id, mechanics.key, mechanics.internal_name,
                       mechanics.description, mechanics.base_weight_milli,
                       triggers.key AS trigger_key,
                       triggers.ruleset_id AS trigger_ruleset_id,
                       triggers.active AS trigger_active,
                       usage_types.key AS default_usage_key,
                       usage_types.ruleset_id AS usage_ruleset_id,
                       usage_types.active AS usage_active
                FROM mechanic_templates AS mechanics
                JOIN trigger_types AS triggers
                  ON triggers.id = mechanics.default_trigger_type_id
                LEFT JOIN usage_limit_types AS usage_types
                  ON usage_types.id = mechanics.default_usage_limit_type_id
                WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
                ORDER BY mechanics.key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            self._validate_template_lookups(templates, ruleset_id)
            usage_by_mechanic = self._usage_limits(connection, ruleset_id)
            rules_by_mechanic = self._rule_templates(connection, ruleset_id)
            return tuple(
                MechanicTemplateDefinition(
                    key=str(row["key"]),
                    internal_name=str(row["internal_name"]),
                    description=str(row["description"]),
                    base_weight_milli=int(row["base_weight_milli"]),
                    default_trigger_key=str(row["trigger_key"]),
                    default_usage_limit_key=(
                        None
                        if row["default_usage_key"] is None
                        else str(row["default_usage_key"])
                    ),
                    usage_limits=tuple(usage_by_mechanic[int(row["id"])]),
                    rule_text_templates=tuple(
                        rules_by_mechanic[int(row["id"])]
                    ),
                )
                for row in templates
            )

    def lineage_eligibility(
        self,
        ruleset: CardBattlerRulesetRef | None,
    ) -> tuple[LineageMechanicEligibility, ...]:
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            rows = connection.execute(
                """
                SELECT lineages.key AS lineage_key,
                       mechanics.key AS mechanic_key,
                       mechanics.ruleset_id AS mechanic_ruleset_id,
                       mechanics.active AS mechanic_active,
                       min_tier.ordinal AS min_tier_ordinal,
                       min_tier.ruleset_id AS min_tier_ruleset_id,
                       max_tier.ordinal AS max_tier_ordinal,
                       max_tier.ruleset_id AS max_tier_ruleset_id,
                       legal.selection_weight_milli
                FROM lineage_mechanics AS legal
                JOIN trait_lineages AS lineages
                  ON lineages.id = legal.lineage_id
                JOIN mechanic_templates AS mechanics
                  ON mechanics.id = legal.mechanic_template_id
                JOIN development_tiers AS min_tier
                  ON min_tier.id = legal.min_tier_id
                LEFT JOIN development_tiers AS max_tier
                  ON max_tier.id = legal.max_tier_id
                WHERE lineages.ruleset_id = ? AND lineages.active = 1
                ORDER BY lineages.key COLLATE BINARY,
                         mechanics.key COLLATE BINARY
                """,
                (ruleset_id,),
            ).fetchall()
            for row in rows:
                if (
                    int(row["mechanic_ruleset_id"]) != ruleset_id
                    or not bool(row["mechanic_active"])
                    or int(row["min_tier_ruleset_id"]) != ruleset_id
                    or (
                        row["max_tier_ruleset_id"] is not None
                        and int(row["max_tier_ruleset_id"]) != ruleset_id
                    )
                ):
                    raise self._invalid(
                        "lineage mechanic eligibility crosses a ruleset "
                        "or references an inactive mechanic"
                    )
            return tuple(
                LineageMechanicEligibility(
                    lineage_key=str(row["lineage_key"]),
                    mechanic_key=str(row["mechanic_key"]),
                    min_tier_ordinal=int(row["min_tier_ordinal"]),
                    max_tier_ordinal=(
                        None
                        if row["max_tier_ordinal"] is None
                        else int(row["max_tier_ordinal"])
                    ),
                    selection_weight_milli=int(row["selection_weight_milli"]),
                )
                for row in rows
            )

    def affinities(
        self,
        ruleset: CardBattlerRulesetRef | None,
    ) -> tuple[MechanicAffinity, ...]:
        facts: list[MechanicAffinity] = []
        with self._resource.connect() as connection:
            ruleset_id = self._ruleset_id(connection, ruleset)
            relations: tuple[
                tuple[MechanicAffinitySource, str, str, str], ...
            ] = (
                (
                    "world_style",
                    "world_style_mechanic_affinity",
                    "world_styles",
                    "world_style_id",
                ),
                (
                    "class",
                    "class_mechanic_affinity",
                    "card_classes",
                    "class_id",
                ),
                (
                    "role",
                    "role_mechanic_affinity",
                    "combat_roles",
                    "role_id",
                ),
                (
                    "lineage",
                    "lineage_mechanic_affinity",
                    "trait_lineages",
                    "lineage_id",
                ),
            )
            for source, relation, entities, entity_id in relations:
                rows = connection.execute(
                    f"""
                    SELECT values_.key AS source_key,
                           mechanics.key AS mechanic_key,
                           mechanics.ruleset_id AS mechanic_ruleset_id,
                           mechanics.active AS mechanic_active,
                           affinity.weight_milli
                    FROM {relation} AS affinity
                    JOIN {entities} AS values_
                      ON values_.id = affinity.{entity_id}
                    JOIN mechanic_templates AS mechanics
                      ON mechanics.id = affinity.mechanic_template_id
                    WHERE values_.ruleset_id = ? AND values_.active = 1
                    ORDER BY values_.key COLLATE BINARY,
                             mechanics.key COLLATE BINARY
                    """,
                    (ruleset_id,),
                ).fetchall()
                if any(
                    int(row["mechanic_ruleset_id"]) != ruleset_id
                    or not bool(row["mechanic_active"])
                    for row in rows
                ):
                    raise self._invalid(
                        f"{source} mechanic affinity crosses a ruleset "
                        "or references an inactive mechanic"
                    )
                facts.extend(
                    MechanicAffinity(
                        source=source,
                        source_key=str(row["source_key"]),
                        mechanic_key=str(row["mechanic_key"]),
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
                    fact.mechanic_key,
                ),
            )
        )

    def _usage_limits(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[MechanicUsageLimitDefinition]]:
        rows = connection.execute(
            """
            SELECT limits.mechanic_template_id,
                   usage_types.key AS usage_limit_key,
                   usage_types.ruleset_id AS usage_ruleset_id,
                   usage_types.active AS usage_active,
                   limits.max_uses, limits.scope,
                   reset_triggers.key AS reset_trigger_key,
                   reset_triggers.ruleset_id AS reset_ruleset_id,
                   reset_triggers.active AS reset_active
            FROM mechanic_usage_limits AS limits
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = limits.mechanic_template_id
            JOIN usage_limit_types AS usage_types
              ON usage_types.id = limits.usage_limit_type_id
            LEFT JOIN trigger_types AS reset_triggers
              ON reset_triggers.id = limits.reset_trigger_type_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
            ORDER BY mechanics.key COLLATE BINARY,
                     usage_types.key COLLATE BINARY,
                     limits.scope COLLATE BINARY
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[MechanicUsageLimitDefinition]] = defaultdict(
            list
        )
        for row in rows:
            if (
                int(row["usage_ruleset_id"]) != ruleset_id
                or not bool(row["usage_active"])
                or (
                    row["reset_ruleset_id"] is not None
                    and (
                        int(row["reset_ruleset_id"]) != ruleset_id
                        or not bool(row["reset_active"])
                    )
                )
            ):
                raise self._invalid(
                    "mechanic usage limit crosses a ruleset or references "
                    "an inactive lookup"
                )
            result[int(row["mechanic_template_id"])].append(
                MechanicUsageLimitDefinition(
                    usage_limit_key=str(row["usage_limit_key"]),
                    max_uses=(
                        None
                        if row["max_uses"] is None
                        else int(row["max_uses"])
                    ),
                    scope=str(row["scope"]),
                    reset_trigger_key=(
                        None
                        if row["reset_trigger_key"] is None
                        else str(row["reset_trigger_key"])
                    ),
                )
            )
        return result

    def _rule_templates(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
    ) -> dict[int, list[RuleTextTemplateDefinition]]:
        rows = connection.execute(
            """
            SELECT templates.mechanic_template_id, templates.ruleset_id,
                   templates.locale, templates.version,
                   templates.template_text
            FROM rules_text_templates AS templates
            JOIN mechanic_templates AS mechanics
              ON mechanics.id = templates.mechanic_template_id
            WHERE mechanics.ruleset_id = ? AND mechanics.active = 1
              AND templates.active = 1
            ORDER BY mechanics.key COLLATE BINARY,
                     templates.locale COLLATE BINARY,
                     templates.version
            """,
            (ruleset_id,),
        ).fetchall()
        result: dict[int, list[RuleTextTemplateDefinition]] = defaultdict(list)
        for row in rows:
            if int(row["ruleset_id"]) != ruleset_id:
                raise self._invalid("rule text template crosses a ruleset")
            result[int(row["mechanic_template_id"])].append(
                RuleTextTemplateDefinition(
                    locale=str(row["locale"]),
                    version=int(row["version"]),
                    template_text=str(row["template_text"]),
                )
            )
        return result

    def _ruleset_id(
        self,
        connection: sqlite3.Connection,
        ruleset: CardBattlerRulesetRef | None,
    ) -> int:
        if ruleset is None:
            return self._resource.validation().active_ruleset_id
        row = connection.execute(
            """
            SELECT id FROM rulesets WHERE ruleset_key = ? AND version = ?
            """,
            (ruleset.key, ruleset.version),
        ).fetchone()
        if row is None:
            raise self._invalid(
                f"cannot resolve ruleset {ruleset.key!r} version "
                f"{ruleset.version}"
            )
        return int(row["id"])

    def _validate_template_lookups(
        self,
        templates: list[sqlite3.Row],
        ruleset_id: int,
    ) -> None:
        for row in templates:
            invalid_trigger = int(
                row["trigger_ruleset_id"]
            ) != ruleset_id or not bool(row["trigger_active"])
            invalid_usage = row["default_usage_key"] is not None and (
                int(row["usage_ruleset_id"]) != ruleset_id
                or not bool(row["usage_active"])
            )
            if invalid_trigger or invalid_usage:
                raise self._invalid(
                    "mechanic template crosses a ruleset or references an "
                    "inactive lookup"
                )

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
