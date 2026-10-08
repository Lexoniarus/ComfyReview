"""Focused SQLite assembly of visual atoms, bindings, and composites."""

from __future__ import annotations

import sqlite3
from typing import cast

from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_visual_model import (
    CompositeProfileDefinition,
    PromptAtomExclusion,
    VisualPromptAtomDefinition,
    VisualPromptBinding,
    VisualPromptMode,
    VisualPromptScope,
    VisualPromptSource,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    SqliteCardBattlerModelResource,
)

_SCOPES = frozenset({"positive", "negative"})
_MODES = frozenset({"optional", "required", "forbidden"})


class _SqliteCardVisualBindingReader:
    """Translate relational visual catalogs into stable ID-free facts."""

    def __init__(self, resource: SqliteCardBattlerModelResource) -> None:
        self._resource = resource

    def prompt_atoms(
        self, connection: sqlite3.Connection, ruleset_id: int
    ) -> tuple[VisualPromptAtomDefinition, ...]:
        rows = connection.execute(
            """
            SELECT key, canonical_text, category
            FROM visual_prompt_atoms
            WHERE ruleset_id = ? AND active = 1
            ORDER BY key COLLATE BINARY
            """,
            (ruleset_id,),
        ).fetchall()
        results = tuple(
            VisualPromptAtomDefinition(
                str(row["key"]),
                str(row["canonical_text"]),
                str(row["category"]),
            )
            for row in rows
        )
        keys = tuple(item.key for item in results)
        if (
            not results
            or len(keys) != len(set(keys))
            or any(not item.key or not item.canonical_text for item in results)
        ):
            raise self._invalid("visual prompt atoms are invalid")
        return results

    def prompt_bindings(
        self, connection: sqlite3.Connection, ruleset_id: int
    ) -> tuple[VisualPromptBinding, ...]:
        specifications = (
            (
                "semantic",
                "semantic_prompt_atoms",
                "semantic_concepts",
                "concept_id",
            ),
            (
                "world_style",
                "world_style_prompt_atoms",
                "world_styles",
                "world_style_id",
            ),
            ("class", "class_prompt_atoms", "card_classes", "class_id"),
            ("role", "role_prompt_atoms", "combat_roles", "role_id"),
            (
                "lineage",
                "lineage_prompt_atoms",
                "trait_lineages",
                "lineage_id",
            ),
            (
                "mechanic",
                "mechanic_prompt_atoms",
                "mechanic_templates",
                "mechanic_template_id",
            ),
            (
                "composite",
                "composite_profile_prompt_atoms",
                "composite_profiles",
                "composite_profile_id",
            ),
        )
        bindings = tuple(
            binding
            for source, table, source_table, source_column in specifications
            for binding in self._bindings(
                connection,
                ruleset_id,
                source=cast(VisualPromptSource, source),
                table=table,
                source_table=source_table,
                source_column=source_column,
            )
        )
        identities = tuple(
            (item.source_type, item.source_key, item.atom_key, item.scope)
            for item in bindings
        )
        if len(identities) != len(set(identities)):
            raise self._invalid("visual prompt bindings are ambiguous")
        return tuple(
            sorted(
                bindings,
                key=lambda item: (
                    item.priority,
                    item.source_type,
                    item.source_key,
                    item.atom_key,
                    item.scope,
                ),
            )
        )

    def _bindings(
        self,
        connection: sqlite3.Connection,
        ruleset_id: int,
        *,
        source: VisualPromptSource,
        table: str,
        source_table: str,
        source_column: str,
    ) -> tuple[VisualPromptBinding, ...]:
        if source == "semantic":
            ruleset_join = (
                "JOIN rulesets AS source_ruleset "
                "ON source_ruleset.semantic_vocabulary_id = sources.vocabulary_id"
            )
            source_ruleset = "source_ruleset.id"
        else:
            ruleset_join = ""
            source_ruleset = "sources.ruleset_id"
        rows = connection.execute(
            f"""
            SELECT sources.key AS source_key,
                   {source_ruleset} AS source_ruleset_id,
                   atoms.key AS atom_key,
                   atoms.ruleset_id AS atom_ruleset_id,
                   atoms.active AS atom_active,
                   bindings.scope, bindings.mode, bindings.weight_milli,
                   minimum.ordinal AS min_tier_ordinal,
                   minimum.ruleset_id AS min_tier_ruleset_id,
                   maximum.ordinal AS max_tier_ordinal,
                   maximum.ruleset_id AS max_tier_ruleset_id,
                   bindings.selection_weight_milli,
                   groups.key AS prompt_group_key,
                   groups.ruleset_id AS prompt_group_ruleset_id,
                   bindings.priority, bindings.intensity_channel, bindings.notes
            FROM {table} AS bindings
            JOIN {source_table} AS sources ON sources.id = bindings.{source_column}
            {ruleset_join}
            JOIN visual_prompt_atoms AS atoms ON atoms.id = bindings.prompt_atom_id
            LEFT JOIN development_tiers AS minimum ON minimum.id = bindings.min_tier_id
            LEFT JOIN development_tiers AS maximum ON maximum.id = bindings.max_tier_id
            LEFT JOIN prompt_groups AS groups ON groups.id = bindings.prompt_group_id
            WHERE {source_ruleset} = ? AND sources.active = 1
            ORDER BY sources.key COLLATE BINARY, atoms.key COLLATE BINARY, bindings.scope
            """,
            (ruleset_id,),
        ).fetchall()
        return tuple(
            self._binding(row, ruleset_id=ruleset_id, source=source)
            for row in rows
        )

    def _binding(
        self,
        row: sqlite3.Row,
        *,
        ruleset_id: int,
        source: VisualPromptSource,
    ) -> VisualPromptBinding:
        if (
            int(row["source_ruleset_id"]) != ruleset_id
            or int(row["atom_ruleset_id"]) != ruleset_id
            or not bool(row["atom_active"])
            or any(
                referenced_ruleset is not None
                and int(referenced_ruleset) != ruleset_id
                for referenced_ruleset in (
                    row["min_tier_ruleset_id"],
                    row["max_tier_ruleset_id"],
                    row["prompt_group_ruleset_id"],
                )
            )
        ):
            raise self._invalid(
                "visual binding references an unavailable fact"
            )
        scope = str(row["scope"])
        mode = str(row["mode"])
        if scope not in _SCOPES or mode not in _MODES:
            raise self._invalid("visual binding scope or mode is invalid")
        weight = int(row["weight_milli"])
        selection = int(row["selection_weight_milli"])
        minimum = (
            int(row["min_tier_ordinal"])
            if row["min_tier_ordinal"] is not None
            else None
        )
        maximum = (
            int(row["max_tier_ordinal"])
            if row["max_tier_ordinal"] is not None
            else None
        )
        if (
            weight <= 0
            or selection <= 0
            or (
                minimum is not None
                and maximum is not None
                and minimum > maximum
            )
        ):
            raise self._invalid("visual binding weights or tiers are invalid")
        return VisualPromptBinding(
            source_type=source,
            source_key=str(row["source_key"]),
            atom_key=str(row["atom_key"]),
            scope=cast(VisualPromptScope, scope),
            mode=cast(VisualPromptMode, mode),
            weight_milli=weight,
            min_tier_ordinal=minimum,
            max_tier_ordinal=maximum,
            selection_weight_milli=selection,
            prompt_group_key=(
                str(row["prompt_group_key"])
                if row["prompt_group_key"] is not None
                else None
            ),
            priority=int(row["priority"]),
            intensity_channel=str(row["intensity_channel"]),
            notes=str(row["notes"]) if row["notes"] is not None else None,
        )

    def composite_profiles(
        self, connection: sqlite3.Connection, ruleset_id: int
    ) -> tuple[CompositeProfileDefinition, ...]:
        rows = connection.execute(
            """
            SELECT composites.key, composites.name,
                   worlds.key AS world_style_key, classes.key AS class_key,
                   roles.key AS role_key, lineages.key AS lineage_key,
                   composites.weight_milli, composites.description,
                   composites.naming_hint, composites.presentation_hint
            FROM composite_profiles AS composites
            JOIN world_styles AS worlds ON worlds.id = composites.world_style_id
            JOIN card_classes AS classes ON classes.id = composites.class_id
            JOIN combat_roles AS roles ON roles.id = composites.role_id
            JOIN trait_lineages AS lineages ON lineages.id = composites.lineage_id
            WHERE composites.ruleset_id = ? AND composites.active = 1
              AND worlds.ruleset_id = ? AND worlds.active = 1
              AND classes.ruleset_id = ? AND classes.active = 1
              AND roles.ruleset_id = ? AND roles.active = 1
              AND lineages.ruleset_id = ? AND lineages.active = 1
            ORDER BY composites.key COLLATE BINARY
            """,
            (ruleset_id,) * 5,
        ).fetchall()
        results = tuple(
            CompositeProfileDefinition(
                key=str(row["key"]),
                name=str(row["name"]),
                world_style_key=str(row["world_style_key"]),
                class_key=str(row["class_key"]),
                role_key=str(row["role_key"]),
                lineage_key=str(row["lineage_key"]),
                weight_milli=int(row["weight_milli"]),
                description=str(row["description"]),
                naming_hint=str(row["naming_hint"]),
                presentation_hint=str(row["presentation_hint"]),
            )
            for row in rows
        )
        keys = tuple(item.key for item in results)
        if len(keys) != len(set(keys)) or any(
            not item.key or item.weight_milli <= 0 for item in results
        ):
            raise self._invalid("visual composite profiles are invalid")
        return results

    def prompt_atom_exclusions(
        self, connection: sqlite3.Connection, ruleset_id: int
    ) -> tuple[PromptAtomExclusion, ...]:
        rows = connection.execute(
            """
            SELECT first.key AS first_key, second.key AS second_key, exclusions.reason
            FROM prompt_atom_exclusions AS exclusions
            JOIN visual_prompt_atoms AS first ON first.id = exclusions.atom_a_id
            JOIN visual_prompt_atoms AS second ON second.id = exclusions.atom_b_id
            WHERE first.ruleset_id = ? AND second.ruleset_id = ?
              AND first.active = 1 AND second.active = 1
            ORDER BY first.key COLLATE BINARY, second.key COLLATE BINARY
            """,
            (ruleset_id, ruleset_id),
        ).fetchall()
        results = tuple(
            PromptAtomExclusion(
                atom_a_key=min(str(row["first_key"]), str(row["second_key"])),
                atom_b_key=max(str(row["first_key"]), str(row["second_key"])),
                reason=str(row["reason"]),
            )
            for row in rows
        )
        keys = tuple((item.atom_a_key, item.atom_b_key) for item in results)
        if len(keys) != len(set(keys)) or any(
            first == second or not reason
            for first, second, reason in (
                (item.atom_a_key, item.atom_b_key, item.reason)
                for item in results
            )
        ):
            raise self._invalid("visual prompt atom exclusions are invalid")
        return tuple(
            sorted(
                results, key=lambda item: (item.atom_a_key, item.atom_b_key)
            )
        )

    def _invalid(self, detail: str) -> CardBattlerModelInvalid:
        return CardBattlerModelInvalid(
            "Invalid Card Battler model database "
            f"{self._resource.database_path}: {detail}"
        )
