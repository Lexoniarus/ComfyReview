"""Declarative schema contracts for the Card Battler model database."""

from __future__ import annotations

from dataclasses import dataclass


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

CARD_MATERIALIZATION_SCHEMA = CardBattlerModelSchemaRequirement(
    group="card-materialization",
    tables=(
        CardBattlerModelTableRequirement(
            "balance_policies",
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
            "tier_balance_profiles",
            frozenset(
                {
                    "tier_id",
                    "balance_policy_id",
                    "stat_budget",
                    "mechanic_budget_milli",
                    "min_atk",
                    "max_atk",
                    "min_def",
                    "max_def",
                    "max_traits",
                    "parameter_scale_milli",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "stat_profiles",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "name",
                    "atk_share_milli",
                    "def_share_milli",
                    "description",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "class_stat_profile_affinity",
            frozenset({"class_id", "stat_profile_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "role_stat_profile_affinity",
            frozenset({"role_id", "stat_profile_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "lineage_stat_profile_affinity",
            frozenset({"lineage_id", "stat_profile_id", "weight_milli"}),
        ),
    ),
)

CARD_MECHANIC_CATALOG_SCHEMA = CardBattlerModelSchemaRequirement(
    group="mechanic-catalog",
    tables=(
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
                    "default_trigger_type_id",
                    "default_usage_limit_type_id",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "lineage_mechanics",
            frozenset(
                {
                    "lineage_id",
                    "mechanic_template_id",
                    "min_tier_id",
                    "max_tier_id",
                    "selection_weight_milli",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "world_style_mechanic_affinity",
            frozenset(
                {"world_style_id", "mechanic_template_id", "weight_milli"}
            ),
        ),
        CardBattlerModelTableRequirement(
            "class_mechanic_affinity",
            frozenset({"class_id", "mechanic_template_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "role_mechanic_affinity",
            frozenset({"role_id", "mechanic_template_id", "weight_milli"}),
        ),
        CardBattlerModelTableRequirement(
            "lineage_mechanic_affinity",
            frozenset({"lineage_id", "mechanic_template_id", "weight_milli"}),
        ),
        *(
            CardBattlerModelTableRequirement(
                table,
                frozenset(
                    {
                        "id",
                        "ruleset_id",
                        "key",
                        "name",
                        "description",
                        "active",
                    }
                ),
            )
            for table in ("trigger_types", "usage_limit_types")
        ),
        CardBattlerModelTableRequirement(
            "mechanic_usage_limits",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "usage_limit_type_id",
                    "max_uses",
                    "scope",
                    "reset_trigger_type_id",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "rules_text_templates",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "mechanic_template_id",
                    "locale",
                    "template_text",
                    "version",
                    "active",
                }
            ),
        ),
    ),
)

CARD_MECHANIC_STRUCTURE_SCHEMA = CardBattlerModelSchemaRequirement(
    group="mechanic-structure",
    tables=(
        *(
            CardBattlerModelTableRequirement(
                table,
                frozenset(
                    {
                        "id",
                        "ruleset_id",
                        "key",
                        "name",
                        "description",
                        "active",
                    }
                ),
            )
            for table in (
                "condition_types",
                "cost_types",
                "effect_types",
                "target_types",
                "duration_types",
                "status_types",
            )
        ),
        CardBattlerModelTableRequirement(
            "mechanic_branches",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "branch_key",
                    "branch_order",
                    "branch_type",
                    "condition_group_id",
                    "description",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_condition_groups",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "group_order",
                    "operator",
                    "join_with_previous",
                    "scope",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_branch_condition_groups",
            frozenset(
                {
                    "branch_id",
                    "condition_group_id",
                    "group_order",
                    "join_with_previous",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_conditions",
            frozenset(
                {
                    "id",
                    "condition_group_id",
                    "condition_order",
                    "condition_type_id",
                    "target_type_id",
                    "comparator",
                    "value_int",
                    "value_text",
                    "negated",
                    "status_type_id",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_steps",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "branch_id",
                    "step_order",
                    "effect_type_id",
                    "target_type_id",
                    "duration_type_id",
                    "status_type_id",
                    "notes",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_costs",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "cost_order",
                    "cost_type_id",
                    "target_type_id",
                    "amount",
                    "notes",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_parameters",
            frozenset(
                {
                    "id",
                    "mechanic_template_id",
                    "step_id",
                    "param_key",
                    "value_type",
                    "min_int",
                    "max_int",
                    "step_int",
                    "default_int",
                    "allowed_values_json",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_parameter_enum_values",
            frozenset(
                {"parameter_id", "value_key", "sort_order", "description"}
            ),
        ),
    ),
)

CARD_DEVELOPMENT_POLICY_SCHEMA = CardBattlerModelSchemaRequirement(
    group="card-development-policy",
    tables=(
        CardBattlerModelTableRequirement(
            "development_policies",
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
            "development_action_types",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "key",
                    "name",
                    "description",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "tier_development_action_weights",
            frozenset(
                {"tier_id", "action_type_id", "weight_milli", "enabled"}
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
            "balance_policies",
            frozenset(
                {
                    "id",
                    "ruleset_id",
                    "policy_key",
                    "version",
                    "active",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "tier_balance_profiles",
            frozenset(
                {
                    "tier_id",
                    "balance_policy_id",
                    "stat_budget",
                    "mechanic_budget_milli",
                    "max_traits",
                    "parameter_scale_milli",
                }
            ),
        ),
    ),
)

CARD_DEVELOPMENT_PROGRESSION_SCHEMA = CardBattlerModelSchemaRequirement(
    group="card-development-progression",
    tables=(
        CardBattlerModelTableRequirement(
            "mechanic_upgrade_edges",
            frozenset(
                {
                    "id",
                    "from_mechanic_id",
                    "to_mechanic_id",
                    "min_tier_id",
                    "max_tier_id",
                    "weight_milli",
                    "upgrade_kind",
                    "notes",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_parameter_progression",
            frozenset(
                {
                    "id",
                    "parameter_id",
                    "min_tier_id",
                    "max_tier_id",
                    "upgrade_step_int",
                    "max_upgrade_steps",
                    "budget_cost_milli",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_templates",
            frozenset({"id", "ruleset_id", "key", "active"}),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_parameters",
            frozenset({"id", "mechanic_template_id", "param_key"}),
        ),
        CardBattlerModelTableRequirement(
            "development_tiers",
            frozenset({"id", "ruleset_id", "ordinal"}),
        ),
    ),
)

CARD_DEVELOPMENT_COMPATIBILITY_SCHEMA = CardBattlerModelSchemaRequirement(
    group="card-development-compatibility",
    tables=(
        CardBattlerModelTableRequirement(
            "lineage_compatibility",
            frozenset(
                {
                    "lineage_a_id",
                    "lineage_b_id",
                    "relation",
                    "weight_milli",
                    "notes",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_compatibility",
            frozenset(
                {
                    "mechanic_a_id",
                    "mechanic_b_id",
                    "relation",
                    "weight_milli",
                    "notes",
                }
            ),
        ),
        CardBattlerModelTableRequirement(
            "trait_lineages",
            frozenset({"id", "ruleset_id", "key", "active"}),
        ),
        CardBattlerModelTableRequirement(
            "mechanic_templates",
            frozenset({"id", "ruleset_id", "key", "active"}),
        ),
    ),
)

CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS = (
    MODEL_IDENTITY_SCHEMA,
    FOUNDATIONAL_CARD_BATTLER_SCHEMA,
    CARD_BATTLER_MAPPING_SCHEMA,
    CARD_MATERIALIZATION_SCHEMA,
    CARD_MECHANIC_CATALOG_SCHEMA,
    CARD_MECHANIC_STRUCTURE_SCHEMA,
    CARD_DEVELOPMENT_POLICY_SCHEMA,
    CARD_DEVELOPMENT_PROGRESSION_SCHEMA,
    CARD_DEVELOPMENT_COMPATIBILITY_SCHEMA,
)
