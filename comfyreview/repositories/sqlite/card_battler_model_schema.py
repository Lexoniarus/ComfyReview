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

CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS = (
    MODEL_IDENTITY_SCHEMA,
    FOUNDATIONAL_CARD_BATTLER_SCHEMA,
    CARD_BATTLER_MAPPING_SCHEMA,
    CARD_MATERIALIZATION_SCHEMA,
)
