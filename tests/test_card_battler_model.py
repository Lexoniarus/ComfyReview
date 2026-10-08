"""Behavior tests for the external read-only Card Battler model resource."""

from __future__ import annotations

import hashlib
import sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerModelNotFound,
    CardBattlerModelVersionUnsupported,
)
from comfyreview.repositories.sqlite.card_battler_model import (
    SqliteCardBattlerModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS,
    CardBattlerModelSchemaRequirement,
    CardBattlerModelTableRequirement,
    SqliteCardBattlerModelResource,
)
from comfyreview.settings import load_settings


def _create_model_database(
    path: Path,
    *,
    database_name: str = "card_battler_model",
    schema_version: int = 3,
) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(
            """
            CREATE TABLE schema_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE semantic_vocabularies (
                id INTEGER PRIMARY KEY,
                vocabulary_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                status TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE rulesets (
                id INTEGER PRIMARY KEY,
                ruleset_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                name TEXT NOT NULL,
                status TEXT NOT NULL,
                semantic_vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                description TEXT NOT NULL
            );
            CREATE TABLE semantic_categories (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL
            );
            CREATE TABLE semantic_concepts (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                category_id INTEGER NOT NULL
                    REFERENCES semantic_categories(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE semantic_aliases (
                id INTEGER PRIMARY KEY,
                vocabulary_id INTEGER NOT NULL
                    REFERENCES semantic_vocabularies(id),
                alias TEXT NOT NULL,
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id)
            );
            CREATE TABLE world_styles (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                parent_style_id INTEGER REFERENCES world_styles(id),
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE card_classes (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE combat_roles (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE trait_lineages (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE rarities (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                ordinal INTEGER NOT NULL,
                max_traits INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE development_tiers (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                rarity_id INTEGER NOT NULL REFERENCES rarities(id),
                level INTEGER NOT NULL,
                ordinal INTEGER NOT NULL,
                next_tier_id INTEGER REFERENCES development_tiers(id),
                development_locked INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE development_policies (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                policy_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                config_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE development_action_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE tier_development_action_weights (
                tier_id INTEGER NOT NULL REFERENCES development_tiers(id),
                action_type_id INTEGER NOT NULL
                    REFERENCES development_action_types(id),
                weight_milli INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (tier_id, action_type_id)
            );
            CREATE TABLE trigger_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE usage_limit_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE condition_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE cost_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE effect_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE target_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE duration_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE status_types (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE mechanic_templates (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                internal_name TEXT NOT NULL,
                description TEXT NOT NULL,
                base_weight_milli INTEGER NOT NULL,
                default_trigger_type_id INTEGER NOT NULL
                    REFERENCES trigger_types(id),
                default_usage_limit_type_id INTEGER
                    REFERENCES usage_limit_types(id),
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE visual_prompt_atoms (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                canonical_text TEXT NOT NULL,
                category TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE mapping_policies (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                policy_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                config_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE rng_policies (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                policy_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                algorithm TEXT NOT NULL,
                config_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE semantic_world_style_affinity (
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id),
                world_style_id INTEGER NOT NULL REFERENCES world_styles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (concept_id, world_style_id)
            );
            CREATE TABLE semantic_class_affinity (
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id),
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (concept_id, class_id)
            );
            CREATE TABLE semantic_role_affinity (
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id),
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (concept_id, role_id)
            );
            CREATE TABLE semantic_lineage_affinity (
                concept_id INTEGER NOT NULL REFERENCES semantic_concepts(id),
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (concept_id, lineage_id)
            );
            CREATE TABLE world_style_class_compatibility (
                world_style_id INTEGER NOT NULL REFERENCES world_styles(id),
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                weight_milli INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (world_style_id, class_id)
            );
            CREATE TABLE class_role_compatibility (
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                weight_milli INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (class_id, role_id)
            );
            CREATE TABLE class_lineage_compatibility (
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                weight_milli INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (class_id, lineage_id)
            );
            CREATE TABLE role_lineage_compatibility (
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                weight_milli INTEGER NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                PRIMARY KEY (role_id, lineage_id)
            );
            CREATE TABLE mapping_fallback_world_styles (
                mapping_policy_id INTEGER NOT NULL REFERENCES mapping_policies(id),
                world_style_id INTEGER NOT NULL REFERENCES world_styles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (mapping_policy_id, world_style_id)
            );
            CREATE TABLE mapping_fallback_classes (
                mapping_policy_id INTEGER NOT NULL REFERENCES mapping_policies(id),
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (mapping_policy_id, class_id)
            );
            CREATE TABLE mapping_fallback_roles (
                mapping_policy_id INTEGER NOT NULL REFERENCES mapping_policies(id),
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (mapping_policy_id, role_id)
            );
            CREATE TABLE mapping_fallback_lineages (
                mapping_policy_id INTEGER NOT NULL REFERENCES mapping_policies(id),
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (mapping_policy_id, lineage_id)
            );
            CREATE TABLE balance_policies (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                policy_key TEXT NOT NULL,
                version INTEGER NOT NULL,
                config_json TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE tier_balance_profiles (
                tier_id INTEGER PRIMARY KEY REFERENCES development_tiers(id),
                balance_policy_id INTEGER NOT NULL REFERENCES balance_policies(id),
                stat_budget INTEGER NOT NULL,
                mechanic_budget_milli INTEGER NOT NULL,
                min_atk INTEGER NOT NULL,
                max_atk INTEGER NOT NULL,
                min_def INTEGER NOT NULL,
                max_def INTEGER NOT NULL,
                max_traits INTEGER NOT NULL,
                parameter_scale_milli INTEGER NOT NULL
            );
            CREATE TABLE stat_profiles (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                key TEXT NOT NULL,
                name TEXT NOT NULL,
                atk_share_milli INTEGER NOT NULL,
                def_share_milli INTEGER NOT NULL,
                description TEXT NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE class_stat_profile_affinity (
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                stat_profile_id INTEGER NOT NULL REFERENCES stat_profiles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (class_id, stat_profile_id)
            );
            CREATE TABLE role_stat_profile_affinity (
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                stat_profile_id INTEGER NOT NULL REFERENCES stat_profiles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (role_id, stat_profile_id)
            );
            CREATE TABLE lineage_stat_profile_affinity (
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                stat_profile_id INTEGER NOT NULL REFERENCES stat_profiles(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (lineage_id, stat_profile_id)
            );
            CREATE TABLE lineage_mechanics (
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                min_tier_id INTEGER NOT NULL REFERENCES development_tiers(id),
                max_tier_id INTEGER REFERENCES development_tiers(id),
                selection_weight_milli INTEGER NOT NULL,
                PRIMARY KEY (lineage_id, mechanic_template_id)
            );
            CREATE TABLE world_style_mechanic_affinity (
                world_style_id INTEGER NOT NULL REFERENCES world_styles(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (world_style_id, mechanic_template_id)
            );
            CREATE TABLE class_mechanic_affinity (
                class_id INTEGER NOT NULL REFERENCES card_classes(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (class_id, mechanic_template_id)
            );
            CREATE TABLE role_mechanic_affinity (
                role_id INTEGER NOT NULL REFERENCES combat_roles(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (role_id, mechanic_template_id)
            );
            CREATE TABLE lineage_mechanic_affinity (
                lineage_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                weight_milli INTEGER NOT NULL,
                PRIMARY KEY (lineage_id, mechanic_template_id)
            );
            CREATE TABLE mechanic_usage_limits (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                usage_limit_type_id INTEGER NOT NULL
                    REFERENCES usage_limit_types(id),
                max_uses INTEGER,
                scope TEXT NOT NULL,
                reset_trigger_type_id INTEGER REFERENCES trigger_types(id)
            );
            CREATE TABLE rules_text_templates (
                id INTEGER PRIMARY KEY,
                ruleset_id INTEGER NOT NULL REFERENCES rulesets(id),
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                locale TEXT NOT NULL,
                template_text TEXT NOT NULL,
                version INTEGER NOT NULL,
                active INTEGER NOT NULL DEFAULT 1
            );
            CREATE TABLE mechanic_condition_groups (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                group_order INTEGER NOT NULL,
                operator TEXT NOT NULL,
                join_with_previous TEXT,
                scope TEXT NOT NULL
            );
            CREATE TABLE mechanic_branches (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                branch_key TEXT NOT NULL,
                branch_order INTEGER NOT NULL,
                branch_type TEXT NOT NULL,
                condition_group_id INTEGER
                    REFERENCES mechanic_condition_groups(id),
                description TEXT
            );
            CREATE TABLE mechanic_branch_condition_groups (
                branch_id INTEGER NOT NULL REFERENCES mechanic_branches(id),
                condition_group_id INTEGER NOT NULL
                    REFERENCES mechanic_condition_groups(id),
                group_order INTEGER NOT NULL,
                join_with_previous TEXT,
                PRIMARY KEY (branch_id, condition_group_id)
            );
            CREATE TABLE mechanic_conditions (
                id INTEGER PRIMARY KEY,
                condition_group_id INTEGER NOT NULL
                    REFERENCES mechanic_condition_groups(id),
                condition_order INTEGER NOT NULL,
                condition_type_id INTEGER NOT NULL REFERENCES condition_types(id),
                target_type_id INTEGER REFERENCES target_types(id),
                comparator TEXT,
                value_int INTEGER,
                value_text TEXT,
                negated INTEGER NOT NULL DEFAULT 0,
                status_type_id INTEGER REFERENCES status_types(id)
            );
            CREATE TABLE mechanic_steps (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                branch_id INTEGER NOT NULL REFERENCES mechanic_branches(id),
                step_order INTEGER NOT NULL,
                effect_type_id INTEGER NOT NULL REFERENCES effect_types(id),
                target_type_id INTEGER NOT NULL REFERENCES target_types(id),
                duration_type_id INTEGER NOT NULL REFERENCES duration_types(id),
                status_type_id INTEGER REFERENCES status_types(id),
                notes TEXT
            );
            CREATE TABLE mechanic_costs (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                cost_order INTEGER NOT NULL,
                cost_type_id INTEGER NOT NULL REFERENCES cost_types(id),
                target_type_id INTEGER REFERENCES target_types(id),
                amount INTEGER,
                notes TEXT
            );
            CREATE TABLE mechanic_parameters (
                id INTEGER PRIMARY KEY,
                mechanic_template_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                step_id INTEGER REFERENCES mechanic_steps(id),
                param_key TEXT NOT NULL,
                value_type TEXT NOT NULL,
                min_int INTEGER,
                max_int INTEGER,
                step_int INTEGER,
                default_int INTEGER,
                allowed_values_json TEXT
            );
            CREATE TABLE mechanic_parameter_enum_values (
                parameter_id INTEGER NOT NULL REFERENCES mechanic_parameters(id),
                value_key TEXT NOT NULL,
                sort_order INTEGER NOT NULL,
                description TEXT,
                PRIMARY KEY (parameter_id, value_key)
            );
            CREATE TABLE mechanic_upgrade_edges (
                id INTEGER PRIMARY KEY,
                from_mechanic_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                to_mechanic_id INTEGER NOT NULL
                    REFERENCES mechanic_templates(id),
                min_tier_id INTEGER NOT NULL REFERENCES development_tiers(id),
                max_tier_id INTEGER REFERENCES development_tiers(id),
                weight_milli INTEGER NOT NULL,
                upgrade_kind TEXT NOT NULL,
                notes TEXT
            );
            CREATE TABLE mechanic_parameter_progression (
                id INTEGER PRIMARY KEY,
                parameter_id INTEGER NOT NULL REFERENCES mechanic_parameters(id),
                min_tier_id INTEGER NOT NULL REFERENCES development_tiers(id),
                max_tier_id INTEGER REFERENCES development_tiers(id),
                upgrade_step_int INTEGER,
                max_upgrade_steps INTEGER,
                budget_cost_milli INTEGER NOT NULL
            );
            CREATE TABLE lineage_compatibility (
                lineage_a_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                lineage_b_id INTEGER NOT NULL REFERENCES trait_lineages(id),
                relation TEXT NOT NULL,
                weight_milli INTEGER NOT NULL,
                notes TEXT,
                PRIMARY KEY (lineage_a_id, lineage_b_id)
            );
            CREATE TABLE mechanic_compatibility (
                mechanic_a_id INTEGER NOT NULL REFERENCES mechanic_templates(id),
                mechanic_b_id INTEGER NOT NULL REFERENCES mechanic_templates(id),
                relation TEXT NOT NULL,
                weight_milli INTEGER NOT NULL,
                notes TEXT,
                PRIMARY KEY (mechanic_a_id, mechanic_b_id)
            );
            """
        )
        connection.executemany(
            "INSERT INTO schema_meta(key, value) VALUES (?, ?)",
            (
                ("database_name", database_name),
                ("schema_version", str(schema_version)),
                ("seed_version", "test-seed"),
                ("purpose", "test model"),
                ("authority", "deterministic test model"),
                ("audit_status", "fixture"),
            ),
        )
        connection.execute(
            """
            INSERT INTO semantic_vocabularies(
                id, vocabulary_key, version, status, description
            ) VALUES (1, 'image_semantics', 1, 'active', 'Fixture vocabulary')
            """
        )
        connection.executemany(
            """
            INSERT INTO rulesets(
                id, ruleset_key, version, name, status,
                semantic_vocabulary_id, description
            ) VALUES (?, 'prototype', ?, ?, ?, 1, ?)
            """,
            (
                (1, 2, "Prototype v2", "active", "Current rules"),
                (2, 1, "Prototype v1", "retired", "Prior rules"),
            ),
        )
        connection.execute(
            """
            INSERT INTO semantic_categories(
                id, vocabulary_id, key, name, description
            ) VALUES (1, 1, 'mood', 'Mood', 'Mood semantics')
            """
        )
        connection.executemany(
            """
            INSERT INTO semantic_concepts(
                id, vocabulary_id, category_id, key, name, description, active
            ) VALUES (?, 1, 1, ?, ?, ?, 1)
            """,
            (
                (2, "zeta", "Zeta", "Zeta concept"),
                (1, "alpha", "Alpha", "Alpha concept"),
            ),
        )
        connection.executemany(
            """
            INSERT INTO semantic_aliases(
                id, vocabulary_id, alias, concept_id
            ) VALUES (?, 1, ?, ?)
            """,
            (
                (1, "bright", 1),
                (2, "airy", 1),
                (3, "heavy", 2),
            ),
        )
        for table in (
            "world_styles",
            "card_classes",
            "combat_roles",
            "trait_lineages",
        ):
            if table == "world_styles":
                connection.executemany(
                    """
                    INSERT INTO world_styles(
                        id, ruleset_id, key, name, parent_style_id,
                        description, active
                    ) VALUES (?, 1, ?, ?, NULL, ?, 1)
                    """,
                    (
                        (2, "zeta", "Zeta", "Zeta definition"),
                        (1, "alpha", "Alpha", "Alpha definition"),
                    ),
                )
            else:
                connection.executemany(
                    f"""
                    INSERT INTO {table}(
                        id, ruleset_id, key, name, description, active
                    ) VALUES (?, 1, ?, ?, ?, 1)
                    """,
                    (
                        (2, "zeta", "Zeta", "Zeta definition"),
                        (1, "alpha", "Alpha", "Alpha definition"),
                    ),
                )
        connection.executemany(
            """
            INSERT INTO rarities(
                id, ruleset_id, key, name, ordinal, max_traits, active
            ) VALUES (?, 1, ?, ?, ?, ?, 1)
            """,
            (
                (1, "common", "Common", 1, 1),
                (2, "rare", "Rare", 2, 2),
            ),
        )
        connection.execute(
            """
            INSERT INTO development_tiers(
                id, ruleset_id, rarity_id, level, ordinal,
                next_tier_id, development_locked
            ) VALUES (2, 1, 2, 2, 2, NULL, 1)
            """
        )
        connection.execute(
            """
            INSERT INTO development_tiers(
                id, ruleset_id, rarity_id, level, ordinal,
                next_tier_id, development_locked
            ) VALUES (1, 1, 1, 1, 1, 2, 0)
            """
        )
        connection.execute(
            """
            INSERT INTO development_policies(
                id, ruleset_id, policy_key, version, config_json, active
            ) VALUES (1, 1, 'lineage_preserving_development', 2, ?, 1)
            """,
            (
                '{"cross_lineage_requires_compatibility":true,'
                '"immutable_imprint_dimensions":['
                '"world_style","card_class","combat_role","trait_lineage"],'
                '"legendary_locked_in_prototype":true,'
                '"prefer_existing_lineage":true,'
                '"primary_trait_actions":['
                '"add_first_trait","improve_existing_trait",'
                '"add_compatible_trait"]}',
            ),
        )
        connection.executemany(
            """
            INSERT INTO development_action_types(
                id, ruleset_id, key, name, description, active
            ) VALUES (?, 1, ?, ?, ?, 1)
            """,
            (
                (
                    1,
                    "add_first_trait",
                    "Add First Trait",
                    "Create the first trait",
                ),
                (
                    2,
                    "improve_existing_trait",
                    "Improve Existing Trait",
                    "Improve an existing trait",
                ),
                (
                    3,
                    "add_compatible_trait",
                    "Add Compatible Trait",
                    "Add a compatible trait",
                ),
            ),
        )
        connection.executemany(
            """
            INSERT INTO tier_development_action_weights(
                tier_id, action_type_id, weight_milli, enabled
            ) VALUES (?, ?, ?, ?)
            """,
            (
                (1, 3, 0, 0),
                (1, 1, 1000, 1),
                (1, 2, 800, 1),
                (2, 3, 350, 1),
                (2, 1, 50, 1),
                (2, 2, 800, 1),
            ),
        )
        connection.executemany(
            """
            INSERT INTO trigger_types(
                id, ruleset_id, key, name, description, active
            ) VALUES (?, 1, ?, ?, ?, 1)
            """,
            (
                (1, "on_play", "On Play", "When played"),
                (2, "turn_start", "Turn Start", "At turn start"),
            ),
        )
        connection.executemany(
            """
            INSERT INTO usage_limit_types(
                id, ruleset_id, key, name, description, active
            ) VALUES (?, 1, ?, ?, ?, 1)
            """,
            (
                (1, "once_per_turn", "Once per turn", "One use per turn"),
                (2, "twice_per_match", "Twice", "Two uses per match"),
            ),
        )
        lookup_rows = {
            "condition_types": (
                (1, "has_status", "Has status", "Target has status"),
            ),
            "cost_types": ((1, "discard", "Discard", "Discard a card"),),
            "effect_types": (
                (1, "gain_attack", "Gain attack", "Increase attack"),
                (2, "apply_status", "Apply status", "Apply a status"),
            ),
            "target_types": (
                (1, "self", "Self", "This card"),
                (2, "enemy", "Enemy", "An enemy"),
            ),
            "duration_types": (
                (1, "instant", "Instant", "Immediate"),
                (2, "turn", "Turn", "For this turn"),
            ),
            "status_types": ((1, "marked", "Marked", "Marked target"),),
        }
        for table, rows in lookup_rows.items():
            connection.executemany(
                f"""
                INSERT INTO {table}(
                    id, ruleset_id, key, name, description, active
                ) VALUES (?, 1, ?, ?, ?, 1)
                """,
                rows,
            )
        connection.executemany(
            """
            INSERT INTO mechanic_templates(
                id, ruleset_id, key, internal_name, description,
                base_weight_milli, default_trigger_type_id,
                default_usage_limit_type_id, active
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, 1)
            """,
            (
                (2, "zeta", "ZETA", "Zeta mechanic", 900, 2, None),
                (1, "alpha", "ALPHA", "Alpha mechanic", 1100, 1, 1),
            ),
        )
        connection.executemany(
            """
            INSERT INTO visual_prompt_atoms(
                id, ruleset_id, key, canonical_text, category, active
            ) VALUES (?, 1, ?, ?, 'style', 1)
            """,
            (
                (2, "zeta", "zeta atom"),
                (1, "alpha", "alpha atom"),
            ),
        )
        connection.execute(
            """
            INSERT INTO mapping_policies(
                id, ruleset_id, policy_key, version, config_json, active
            ) VALUES (1, 1, 'semantic_imprint_mapping', 2, ?, 1)
            """,
            (
                '{"signal_min_milli":180,"candidate_min_score_milli":100,'
                '"compatibility_floor_milli":120,"minimum_candidate_count":2,'
                '"top_pool_size":2,"use_seeded_weighted_selection":true,'
                '"fallback_when_no_candidate":true,"score_components":{'
                '"semantic_affinity":700,"compatibility":250,'
                '"fallback_prior":50},"stable_sort":["score_desc","key_asc"]}',
            ),
        )
        connection.execute(
            """
            INSERT INTO rng_policies(
                id, ruleset_id, policy_key, version, algorithm, config_json, active
            ) VALUES (1, 1, 'deterministic_rng', 2, 'sha256-counter-v1', ?, 1)
            """,
            (
                '{"seed_material":["image_uid","semantic_revision",'
                '"ruleset_revision","mapping_policy_revision","explicit_seed"],'
                '"stable_candidate_key":"entity_key",'
                '"sql_row_order_is_not_randomness":true,'
                '"runtime_hash_is_not_randomness":true}',
            ),
        )
        connection.execute(
            """
            INSERT INTO balance_policies(
                id, ruleset_id, policy_key, version, config_json, active
            ) VALUES (1, 1, 'prototype_balance', 2, ?, 1)
            """,
            (
                '{"atk_def_minimum":0,"calibration_status":"prototype",'
                '"no_negative_stats":true,"stat_rounding_step":50,'
                '"trait_budget_is_milli":true}',
            ),
        )
        connection.executemany(
            """
            INSERT INTO stat_profiles(
                id, ruleset_id, key, name, atk_share_milli,
                def_share_milli, description, active
            ) VALUES (?, 1, ?, ?, ?, ?, ?, 1)
            """,
            (
                (2, "offensive", "Offensive", 650, 350, "ATK leaning"),
                (1, "balanced", "Balanced", 500, 500, "Even shares"),
            ),
        )
        connection.executemany(
            """
            INSERT INTO tier_balance_profiles(
                tier_id, balance_policy_id, stat_budget,
                mechanic_budget_milli, min_atk, max_atk, min_def, max_def,
                max_traits, parameter_scale_milli
            ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (1, 3000, 1000, 600, 2400, 600, 2400, 1, 1000),
                (2, 4000, 1500, 800, 3200, 800, 3200, 2, 1200),
            ),
        )
        for table, source_column in (
            ("class_stat_profile_affinity", "class_id"),
            ("role_stat_profile_affinity", "role_id"),
            ("lineage_stat_profile_affinity", "lineage_id"),
        ):
            connection.executemany(
                f"INSERT INTO {table}({source_column}, stat_profile_id, weight_milli) VALUES (?, ?, ?)",
                ((1, 1, 700), (1, 2, 900), (2, 1, 800), (2, 2, 600)),
            )
        connection.executemany(
            """
            INSERT INTO lineage_mechanics(
                lineage_id, mechanic_template_id, min_tier_id,
                max_tier_id, selection_weight_milli
            ) VALUES (?, ?, 1, ?, ?)
            """,
            ((2, 2, None, 700), (1, 1, 2, 900)),
        )
        for table, source_column in (
            ("world_style_mechanic_affinity", "world_style_id"),
            ("class_mechanic_affinity", "class_id"),
            ("role_mechanic_affinity", "role_id"),
            ("lineage_mechanic_affinity", "lineage_id"),
        ):
            connection.executemany(
                f"INSERT INTO {table}({source_column}, mechanic_template_id, weight_milli) VALUES (?, ?, ?)",
                ((1, 1, 900), (1, 2, 500), (2, 1, 400), (2, 2, 800)),
            )
        connection.executemany(
            """
            INSERT INTO mechanic_usage_limits(
                id, mechanic_template_id, usage_limit_type_id,
                max_uses, scope, reset_trigger_type_id
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                (2, 2, 2, 2, "match", None),
                (1, 1, 1, 1, "turn", 2),
            ),
        )
        connection.executemany(
            """
            INSERT INTO rules_text_templates(
                id, ruleset_id, mechanic_template_id, locale,
                template_text, version, active
            ) VALUES (?, 1, ?, ?, ?, 1, 1)
            """,
            (
                (4, 2, "en-US", "Zeta rule"),
                (3, 2, "de-DE", "Zeta-Regel"),
                (2, 1, "en-US", "Alpha rule"),
                (1, 1, "de-DE", "Alpha-Regel"),
            ),
        )
        connection.execute(
            """
            INSERT INTO mechanic_condition_groups(
                id, mechanic_template_id, group_order,
                operator, join_with_previous, scope
            ) VALUES (1, 1, 1, 'AND', NULL, 'global')
            """
        )
        connection.executemany(
            """
            INSERT INTO mechanic_branches(
                id, mechanic_template_id, branch_key, branch_order,
                branch_type, condition_group_id, description
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (2, 1, "optional", 2, "optional", None, None),
                (1, 1, "main", 1, "main", 1, "Primary branch"),
                (3, 2, "main", 1, "main", None, "Zeta branch"),
            ),
        )
        connection.execute(
            """
            INSERT INTO mechanic_branch_condition_groups(
                branch_id, condition_group_id, group_order, join_with_previous
            ) VALUES (2, 1, 1, NULL)
            """
        )
        connection.execute(
            """
            INSERT INTO mechanic_conditions(
                id, condition_group_id, condition_order, condition_type_id,
                target_type_id, comparator, value_int, value_text,
                negated, status_type_id
            ) VALUES (1, 1, 1, 1, 2, 'eq', NULL, 'marked', 0, 1)
            """
        )
        connection.executemany(
            """
            INSERT INTO mechanic_steps(
                id, mechanic_template_id, branch_id, step_order,
                effect_type_id, target_type_id, duration_type_id,
                status_type_id, notes
            ) VALUES (?, ?, ?, 1, ?, ?, ?, ?, ?)
            """,
            (
                (2, 1, 2, 2, 2, 2, 1, "Mark the enemy"),
                (1, 1, 1, 1, 1, 2, None, "Gain attack"),
                (3, 2, 3, 1, 1, 1, None, None),
            ),
        )
        connection.execute(
            """
            INSERT INTO mechanic_costs(
                id, mechanic_template_id, cost_order, cost_type_id,
                target_type_id, amount, notes
            ) VALUES (1, 1, 1, 1, 1, 1, 'Discard one')
            """
        )
        connection.executemany(
            """
            INSERT INTO mechanic_parameters(
                id, mechanic_template_id, step_id, param_key, value_type,
                min_int, max_int, step_int, default_int, allowed_values_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                (
                    2,
                    1,
                    2,
                    "mode",
                    "enum",
                    None,
                    None,
                    None,
                    None,
                    '["soft","hard"]',
                ),
                (1, 1, 1, "bonus", "int", 100, 500, 100, 300, None),
                (3, 2, None, "enabled", "bool", None, None, None, None, None),
            ),
        )
        connection.executemany(
            """
            INSERT INTO mechanic_parameter_enum_values(
                parameter_id, value_key, sort_order, description
            ) VALUES (2, ?, ?, ?)
            """,
            (
                ("hard", 2, "Hard mode"),
                ("soft", 1, "Soft mode"),
            ),
        )
        connection.execute(
            """
            INSERT INTO mechanic_upgrade_edges(
                id, from_mechanic_id, to_mechanic_id,
                min_tier_id, max_tier_id, weight_milli,
                upgrade_kind, notes
            ) VALUES (1, 1, 2, 1, 2, 900, 'branch', 'Fixture edge')
            """
        )
        connection.execute(
            """
            INSERT INTO mechanic_parameter_progression(
                id, parameter_id, min_tier_id, max_tier_id,
                upgrade_step_int, max_upgrade_steps, budget_cost_milli
            ) VALUES (1, 1, 1, 2, 50, 4, 125)
            """
        )
        connection.execute(
            """
            INSERT INTO lineage_compatibility(
                lineage_a_id, lineage_b_id, relation, weight_milli, notes
            ) VALUES (2, 1, 'compatible', 700, 'Fixture lineages')
            """
        )
        connection.execute(
            """
            INSERT INTO mechanic_compatibility(
                mechanic_a_id, mechanic_b_id, relation, weight_milli, notes
            ) VALUES (2, 1, 'preferred', 850, 'Fixture mechanics')
            """
        )
        for table, target_column in (
            ("semantic_world_style_affinity", "world_style_id"),
            ("semantic_class_affinity", "class_id"),
            ("semantic_role_affinity", "role_id"),
            ("semantic_lineage_affinity", "lineage_id"),
        ):
            connection.executemany(
                f"INSERT INTO {table}(concept_id, {target_column}, weight_milli) VALUES (?, ?, ?)",
                ((1, 1, 900), (1, 2, 300), (2, 1, 200), (2, 2, 850)),
            )
        for table, source_column, target_column in (
            ("world_style_class_compatibility", "world_style_id", "class_id"),
            ("class_role_compatibility", "class_id", "role_id"),
            ("class_lineage_compatibility", "class_id", "lineage_id"),
            ("role_lineage_compatibility", "role_id", "lineage_id"),
        ):
            connection.executemany(
                f"INSERT INTO {table}({source_column}, {target_column}, weight_milli, enabled) VALUES (?, ?, ?, ?)",
                (
                    (1, 1, 900, 1),
                    (1, 2, 700, 1),
                    (2, 1, 700, 1),
                    (2, 2, 900, 1),
                ),
            )
        for table, target_column in (
            ("mapping_fallback_world_styles", "world_style_id"),
            ("mapping_fallback_classes", "class_id"),
            ("mapping_fallback_roles", "role_id"),
            ("mapping_fallback_lineages", "lineage_id"),
        ):
            connection.executemany(
                f"INSERT INTO {table}(mapping_policy_id, {target_column}, weight_milli) VALUES (1, ?, ?)",
                ((1, 800), (2, 700)),
            )
        connection.commit()
    finally:
        connection.close()


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_settings_derive_model_path_from_configured_data_directory(
    tmp_path: Path,
) -> None:
    data_directory = tmp_path / "custom-data"

    settings = load_settings(
        base_directory=tmp_path,
        environ={"COMFYREVIEW_DATA_DIR": str(data_directory)},
    )

    assert (
        settings.card_battler_model_database_path
        == (data_directory / "card_battler.sqlite3").resolve()
    )
    assert not data_directory.exists()


def test_settings_respect_explicit_model_database_override(
    tmp_path: Path,
) -> None:
    model_path = tmp_path / "models" / "custom-card-model.sqlite3"

    settings = load_settings(
        base_directory=tmp_path,
        environ={
            "COMFYREVIEW_CARD_BATTLER_MODEL_DATABASE": str(model_path),
        },
    )

    assert settings.card_battler_model_database_path == model_path.resolve()
    assert not model_path.exists()


def test_valid_model_reads_metadata_ruleset_and_foundational_catalogs(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)

    metadata = repository.metadata()
    active = repository.resolve_ruleset()
    retired = repository.resolve_ruleset(key="prototype", version=1)
    concepts = repository.semantic_concepts(active)
    styles = repository.world_styles(active)
    classes = repository.card_classes(active)
    roles = repository.combat_roles(active)
    lineages = repository.trait_lineages(active)
    tiers = repository.development_tiers(active)
    mechanics = repository.mechanic_templates(active)
    summary = repository.summary(active)

    assert (metadata.database_name, metadata.schema_version) == (
        "card_battler_model",
        3,
    )
    assert (active.key, active.version, active.status) == (
        "prototype",
        2,
        "active",
    )
    assert (retired.version, retired.status) == (1, "retired")
    assert [item.key for item in concepts] == ["alpha", "zeta"]
    assert concepts[0].aliases == ("airy", "bright")
    assert [item.key for item in styles] == ["alpha", "zeta"]
    assert [item.key for item in classes] == ["alpha", "zeta"]
    assert [item.key for item in roles] == ["alpha", "zeta"]
    assert [item.key for item in lineages] == ["alpha", "zeta"]
    assert [item.ordinal for item in tiers] == [1, 2]
    assert tiers[0].next_ordinal == 2
    assert [item.key for item in mechanics] == ["alpha", "zeta"]
    assert (
        summary.semantic_concept_count,
        summary.world_style_count,
        summary.card_class_count,
        summary.combat_role_count,
        summary.trait_lineage_count,
        summary.development_tier_count,
        summary.mechanic_template_count,
        summary.prompt_atom_count,
    ) == (2, 2, 2, 2, 2, 2, 2, 2)
    assert summary.integrity_ok is True
    assert summary.foreign_key_violation_count == 0


def test_model_resource_caches_success_and_lends_short_read_only_connections(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )

    with patch.object(
        resource,
        "_validate_connection",
        wraps=resource._validate_connection,
    ) as validate:
        first = resource.validation()
        second = resource.validation()
        with resource.connect() as connection:
            assert connection.execute("PRAGMA query_only").fetchone()[0] == 1
            with pytest.raises(sqlite3.OperationalError):
                connection.execute("DELETE FROM schema_meta")
        with pytest.raises(sqlite3.ProgrammingError):
            connection.execute("SELECT 1")

    assert first is second
    assert validate.call_count == 1
    assert first.active_ruleset == resource.validation().active_ruleset
    assert [
        (policy.kind, policy.key, policy.version)
        for policy in first.active_policies
    ] == [
        ("balance", "prototype_balance", 2),
        ("development", "lineage_preserving_development", 2),
        ("mapping", "semantic_imprint_mapping", 2),
        ("rng", "deterministic_rng", 2),
    ]


def test_model_resource_caches_validation_failure_without_rescanning(
    tmp_path: Path,
) -> None:
    path = tmp_path / "wrong.sqlite3"
    _create_model_database(path, database_name="not_the_model")
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )

    with patch.object(
        resource,
        "_validate_connection",
        wraps=resource._validate_connection,
    ) as validate:
        messages = []
        for _ in range(2):
            with pytest.raises(CardBattlerModelInvalid) as raised:
                resource.validation()
            messages.append(str(raised.value))

    assert messages[0] == messages[1]
    assert validate.call_count == 1


def test_model_resource_validation_is_thread_safe(tmp_path: Path) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )

    with patch.object(
        resource,
        "_validate_connection",
        wraps=resource._validate_connection,
    ) as validate:
        with ThreadPoolExecutor(max_workers=8) as executor:
            validations = tuple(
                executor.map(lambda _: resource.validation(), range(24))
            )

    assert all(item is validations[0] for item in validations)
    assert validate.call_count == 1


def test_model_resource_rejects_registered_missing_columns(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    extra_requirement = CardBattlerModelSchemaRequirement(
        group="future-read-area",
        tables=(
            CardBattlerModelTableRequirement(
                table="rulesets",
                columns=frozenset({"future_contract_column"}),
            ),
        ),
    )
    resource = SqliteCardBattlerModelResource(
        path,
        CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS + (extra_requirement,),
    )

    with pytest.raises(
        CardBattlerModelInvalid, match="future_contract_column"
    ):
        resource.validation()


def test_model_resource_normalizes_connection_scope_failures(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )

    with pytest.raises(CardBattlerModelInvalid, match="decode failed"):
        with resource.connect():
            raise ValueError("decode failed")
    with pytest.raises(CardBattlerModelInvalid, match="sentinel"):
        with resource.connect():
            raise CardBattlerModelInvalid("sentinel")


def test_model_resource_rejects_directory_and_open_failures(
    tmp_path: Path,
) -> None:
    directory_resource = SqliteCardBattlerModelResource(
        tmp_path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    with pytest.raises(CardBattlerModelInvalid, match="not a file"):
        directory_resource.validation()

    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    with patch(
        "comfyreview.repositories.sqlite.card_battler_model_resource."
        "connect_read_only",
        side_effect=sqlite3.DatabaseError("open failed"),
    ):
        with pytest.raises(CardBattlerModelInvalid, match="cannot open"):
            resource.validation()


def test_model_resource_rejects_failed_integrity_check(tmp_path: Path) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    connection = resource._open_connection()
    wrapped = Mock(wraps=connection)

    def execute(
        statement: str, parameters: tuple[str | int, ...] = ()
    ) -> object:
        if statement == "PRAGMA integrity_check":
            cursor = Mock()
            cursor.fetchall.return_value = [("broken",)]
            return cursor
        return connection.execute(statement, parameters)

    wrapped.execute.side_effect = execute
    with patch.object(resource, "_open_connection", return_value=wrapped):
        with pytest.raises(CardBattlerModelInvalid, match="integrity_check"):
            resource.validation()


@pytest.mark.parametrize(
    ("mutation", "message"),
    (
        ("DELETE FROM schema_meta WHERE key = 'database_name'", "identity"),
        (
            "UPDATE schema_meta SET value = 'invalid' "
            "WHERE key = 'schema_version'",
            "not an integer",
        ),
        ("UPDATE rulesets SET status = 'retired'", "active ruleset"),
        (
            "UPDATE balance_policies SET active = 0",
            "active balance policy",
        ),
        (
            "UPDATE mapping_policies SET active = 0",
            "active mapping policy",
        ),
        ("UPDATE rng_policies SET active = 0", "active rng policy"),
    ),
)
def test_model_resource_rejects_unresolvable_identity_and_active_contracts(
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()

    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    with pytest.raises(CardBattlerModelInvalid, match=message):
        resource.validation()


def test_model_resource_rejects_missing_identity_table(tmp_path: Path) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE schema_meta")
        connection.commit()
    finally:
        connection.close()

    resource = SqliteCardBattlerModelResource(
        path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
    )
    with pytest.raises(CardBattlerModelInvalid, match="schema_meta"):
        resource.validation()


@pytest.mark.parametrize(
    "requirement",
    (
        CardBattlerModelSchemaRequirement(group="", tables=()),
        CardBattlerModelSchemaRequirement(
            group="invalid-table",
            tables=(
                CardBattlerModelTableRequirement(
                    table="bad-name", columns=frozenset({"column"})
                ),
            ),
        ),
        CardBattlerModelSchemaRequirement(
            group="empty-columns",
            tables=(
                CardBattlerModelTableRequirement(
                    table="rulesets", columns=frozenset()
                ),
            ),
        ),
        CardBattlerModelSchemaRequirement(
            group="invalid-column",
            tables=(
                CardBattlerModelTableRequirement(
                    table="rulesets", columns=frozenset({"bad-name"})
                ),
            ),
        ),
    ),
)
def test_model_resource_rejects_invalid_schema_registrations(
    tmp_path: Path,
    requirement: CardBattlerModelSchemaRequirement,
) -> None:
    with pytest.raises(ValueError, match="schema|table|column"):
        SqliteCardBattlerModelResource(
            tmp_path / "unused.sqlite3", (requirement,)
        )


def test_missing_model_database_is_normalized(tmp_path: Path) -> None:
    repository = SqliteCardBattlerModelRepository(tmp_path / "missing.sqlite3")

    with pytest.raises(CardBattlerModelNotFound, match="does not exist"):
        repository.metadata()


def test_wrong_database_identity_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "wrong.sqlite3"
    _create_model_database(path, database_name="not_the_model")

    with pytest.raises(CardBattlerModelInvalid, match="unexpected database"):
        SqliteCardBattlerModelRepository(path).metadata()


def test_unsupported_schema_version_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    _create_model_database(path, schema_version=99)

    with pytest.raises(
        CardBattlerModelVersionUnsupported,
        match="schema version 99",
    ):
        SqliteCardBattlerModelRepository(path).metadata()


def test_unsupported_schema_is_reported_before_v3_structure_checks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "future-layout.sqlite3"
    _create_model_database(path, schema_version=99)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE visual_prompt_atoms")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(
        CardBattlerModelVersionUnsupported,
        match="schema version 99",
    ):
        SqliteCardBattlerModelRepository(path).metadata()


def test_missing_foundational_table_is_rejected_without_repair(
    tmp_path: Path,
) -> None:
    path = tmp_path / "malformed.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("DROP TABLE visual_prompt_atoms")
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="visual_prompt_atoms"):
        SqliteCardBattlerModelRepository(path).metadata()

    connection = sqlite3.connect(path)
    try:
        table = connection.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type = 'table' AND name = 'visual_prompt_atoms'
            """
        ).fetchone()
    finally:
        connection.close()
    assert table is None


def test_corrupt_sqlite_is_rejected_as_invalid(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.sqlite3"
    path.write_bytes(b"this is not a sqlite database")

    with pytest.raises(CardBattlerModelInvalid):
        SqliteCardBattlerModelRepository(path).metadata()


def test_foreign_key_violation_is_rejected_without_repair(
    tmp_path: Path,
) -> None:
    path = tmp_path / "broken-fk.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(
            """
            INSERT INTO card_classes(
                id, ruleset_id, key, name, description, active
            ) VALUES (99, 999, 'broken', 'Broken', 'Broken FK', 1)
            """
        )
        connection.commit()
    finally:
        connection.close()

    before = _digest(path)
    with pytest.raises(CardBattlerModelInvalid, match="foreign_key_check"):
        SqliteCardBattlerModelRepository(path).summary()
    assert _digest(path) == before


def test_catalog_reads_are_stably_ordered_and_read_only(
    tmp_path: Path,
) -> None:
    path = tmp_path / "stable.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)
    before = _digest(path)

    first = (
        repository.semantic_concepts(),
        repository.world_styles(),
        repository.card_classes(),
        repository.combat_roles(),
        repository.trait_lineages(),
        repository.development_tiers(),
        repository.mechanic_templates(),
        repository.summary(),
    )
    second = (
        repository.semantic_concepts(),
        repository.world_styles(),
        repository.card_classes(),
        repository.combat_roles(),
        repository.trait_lineages(),
        repository.development_tiers(),
        repository.mechanic_templates(),
        repository.summary(),
    )

    assert first == second
    assert _digest(path) == before


def test_mapping_and_rng_policies_are_typed_and_validated(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)
    ruleset = repository.resolve_ruleset()

    mapping = repository.mapping_policy(ruleset)
    rng = repository.rng_policy(ruleset)

    assert (mapping.key, mapping.version) == ("semantic_imprint_mapping", 2)
    assert mapping.signal_min_milli == 180
    assert mapping.candidate_min_score_milli == 100
    assert mapping.compatibility_floor_milli == 120
    assert mapping.minimum_candidate_count == 2
    assert mapping.top_pool_size == 2
    assert (
        mapping.semantic_affinity_weight,
        mapping.compatibility_weight,
        mapping.fallback_prior_weight,
    ) == (700, 250, 50)
    assert (rng.key, rng.version, rng.algorithm) == (
        "deterministic_rng",
        2,
        "sha256-counter-v1",
    )
    assert rng.seed_material == (
        "image_uid",
        "semantic_revision",
        "ruleset_revision",
        "mapping_policy_revision",
        "explicit_seed",
    )


def test_mapping_relations_are_read_in_stable_typed_order(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = SqliteCardBattlerModelRepository(path)
    ruleset = repository.resolve_ruleset()
    policy = repository.mapping_policy(ruleset)

    affinity_groups = (
        repository.world_style_affinities(ruleset),
        repository.class_affinities(ruleset),
        repository.role_affinities(ruleset),
        repository.lineage_affinities(ruleset),
    )
    assert all(
        [(item.concept_key, item.entity_key) for item in group]
        == sorted((item.concept_key, item.entity_key) for item in group)
        for group in affinity_groups
    )
    assert all(len(group) == 4 for group in affinity_groups)

    compatibility_groups = (
        repository.world_style_class_compatibility(ruleset),
        repository.class_role_compatibility(ruleset),
        repository.class_lineage_compatibility(ruleset),
        repository.role_lineage_compatibility(ruleset),
    )
    assert all(len(group) == 4 for group in compatibility_groups)
    assert all(
        item.enabled for group in compatibility_groups for item in group
    )

    fallback_groups = (
        repository.fallback_world_styles(policy, ruleset),
        repository.fallback_classes(policy, ruleset),
        repository.fallback_roles(policy, ruleset),
        repository.fallback_lineages(policy, ruleset),
    )
    assert all(
        [(item.weight_milli, item.entity_key) for item in group]
        == sorted(
            ((item.weight_milli, item.entity_key) for item in group),
            key=lambda item: (-item[0], item[1]),
        )
        for group in fallback_groups
    )


def test_malformed_policy_config_is_a_model_contract_failure(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE mapping_policies SET config_json = ? WHERE id = 1",
            ('{"stable_sort":["key_asc"]}',),
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid):
        SqliteCardBattlerModelRepository(path).mapping_policy()


def test_mapping_repository_reads_do_not_mutate_model_file(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    before = _digest(path)
    repository = SqliteCardBattlerModelRepository(path)
    ruleset = repository.resolve_ruleset()
    policy = repository.mapping_policy(ruleset)

    repository.rng_policy(ruleset)
    repository.world_style_affinities(ruleset)
    repository.class_affinities(ruleset)
    repository.role_affinities(ruleset)
    repository.lineage_affinities(ruleset)
    repository.world_style_class_compatibility(ruleset)
    repository.class_role_compatibility(ruleset)
    repository.class_lineage_compatibility(ruleset)
    repository.role_lineage_compatibility(ruleset)
    repository.fallback_world_styles(policy, ruleset)
    repository.fallback_classes(policy, ruleset)
    repository.fallback_roles(policy, ruleset)
    repository.fallback_lineages(policy, ruleset)

    assert _digest(path) == before
