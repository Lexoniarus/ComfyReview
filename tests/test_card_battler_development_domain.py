"""Behavior tests for immutable Card Battler development contracts."""

from dataclasses import FrozenInstanceError

import pytest

from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    CARD_DEVELOPMENT_ALGORITHM_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardDevelopmentPlan,
    CardDevelopmentProvenance,
    CardDevelopmentResult,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    DevelopmentTier,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedTrait,
    StructuredCardSpec,
    TraitDevelopmentAction,
)


def test_development_contracts_freeze_one_next_tier_and_trait_action() -> None:
    card = _card_spec()
    previous_trait = card.traits[0]
    developed_trait = MaterializedTrait(
        lineage_key=previous_trait.lineage_key,
        mechanic=previous_trait.mechanic,
        canonical_rule_text="Erhält 400 ATK.",
    )
    provenance = CardDevelopmentProvenance(
        development_policy_key="prototype_development",
        development_policy_version=1,
        development_algorithm_revision=CARD_DEVELOPMENT_ALGORITHM_REVISION,
    )
    plan = CardDevelopmentPlan(
        current_tier=DevelopmentTier("common", 1, 1),
        next_tier=DevelopmentTier("common", 2, 2),
        mechanic_budget_milli=1250,
        trait_cap=1,
        primary_trait_action="improve_existing_trait",
        provenance=provenance,
    )
    action = TraitDevelopmentAction(
        action=plan.primary_trait_action,
        trait_index=0,
        previous_trait=previous_trait,
        developed_trait=developed_trait,
    )
    result = CardDevelopmentResult(
        card=card,
        action=action,
        provenance=provenance,
    )

    assert plan.next_tier.ordinal == plan.current_tier.ordinal + 1
    assert result.action.previous_trait is previous_trait
    assert result.provenance.development_algorithm_revision.endswith("-v1")

    with pytest.raises(FrozenInstanceError):
        plan.primary_trait_action = "add_compatible_trait"  # type: ignore[misc]


def _card_spec() -> StructuredCardSpec:
    mechanic = MaterializedMechanic(
        key="measured_strike",
        trigger_key="on_attack",
        usage_limits=(),
        condition_groups=(),
        branches=(),
        costs=(),
        parameters=(MaterializedParameter(key="bonus", value=300),),
    )
    return StructuredCardSpec(
        imprint=CardImprint(
            world_style="urban",
            card_class="ranger",
            combat_role="precision",
            trait_lineage="marking",
            source_image_uid="image-1",
            semantic_revision="semantic-v1",
            ruleset_key="prototype",
            ruleset_version=2,
            mapping_policy_key="semantic_imprint_mapping",
            mapping_policy_version=2,
            rng_policy_key="deterministic_rng",
            rng_policy_version=2,
            rng_algorithm="sha256-counter-v1",
            explicit_seed=42,
        ),
        rarity_key="common",
        level=1,
        tier_ordinal=1,
        stats=CardStats(
            attack=1600,
            defense=1400,
            budget=3000,
            stat_profile_key="balanced",
        ),
        traits=(
            MaterializedTrait(
                lineage_key="marking",
                mechanic=mechanic,
                canonical_rule_text="Erhält 300 ATK.",
            ),
        ),
        provenance=CardRulesProvenance(
            ruleset_key="prototype",
            ruleset_version=2,
            mapping_policy_key="semantic_imprint_mapping",
            mapping_policy_version=2,
            rng_policy_key="deterministic_rng",
            rng_policy_version=2,
            rng_algorithm="sha256-counter-v1",
            balance_policy_key="prototype_balance",
            balance_policy_version=2,
            explicit_seed=42,
            materialization_algorithm_revision=(
                COMMON_CARD_MATERIALIZATION_REVISION
            ),
            rule_renderer_revision=CANONICAL_RULE_RENDERER_REVISION,
        ),
    )
