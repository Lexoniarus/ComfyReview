"""Behavior tests for pure immutable Card Battler domain contracts."""

from __future__ import annotations

from dataclasses import FrozenInstanceError

import pytest

from comfyreview.application.card_battler_mapping import (
    CardImprint as ApplicationCardImprint,
)
from comfyreview.domain.card_battler import (
    CANONICAL_RULE_RENDERER_REVISION,
    COMMON_CARD_MATERIALIZATION_REVISION,
    CardImprint,
    CardRulesProvenance,
    CardStats,
    MaterializedBranch,
    MaterializedBranchConditionGroup,
    MaterializedCondition,
    MaterializedConditionGroup,
    MaterializedCost,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedStep,
    MaterializedTrait,
    MaterializedUsageLimit,
    StructuredCardSpec,
)


def _imprint() -> CardImprint:
    return CardImprint(
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
    )


def test_card_imprint_is_domain_owned_and_application_compatible() -> None:
    assert ApplicationCardImprint is CardImprint
    imprint = _imprint()

    with pytest.raises(FrozenInstanceError):
        imprint.card_class = "changed"  # type: ignore[misc]


def test_structured_card_spec_keeps_rules_and_provenance_immutable() -> None:
    parameter = MaterializedParameter(key="bonus", value=300)
    condition = MaterializedCondition(
        order=1,
        condition_type_key="has_status",
        target_type_key="enemy",
        comparator="eq",
        value="marked",
        negated=False,
        status_type_key="marked",
    )
    condition_group = MaterializedConditionGroup(
        order=1,
        operator="AND",
        join_with_previous=None,
        scope="global",
        conditions=(condition,),
    )
    step = MaterializedStep(
        order=1,
        effect_type_key="gain_attack",
        target_type_key="self",
        duration_type_key="turn",
        status_type_key=None,
        parameters=(parameter,),
    )
    branch = MaterializedBranch(
        key="main",
        order=1,
        branch_type="main",
        condition_groups=(
            MaterializedBranchConditionGroup(
                order=1,
                condition_group_order=1,
                join_with_previous=None,
            ),
        ),
        steps=(step,),
    )
    mechanic = MaterializedMechanic(
        key="measured_strike",
        trigger_key="on_attack",
        usage_limits=(
            MaterializedUsageLimit(
                usage_limit_key="once_per_turn",
                max_uses=1,
                scope="turn",
                reset_trigger_key="turn_start",
            ),
        ),
        condition_groups=(condition_group,),
        branches=(branch,),
        costs=(
            MaterializedCost(
                order=1,
                cost_type_key="discard",
                target_type_key="self",
                amount=1,
            ),
        ),
        parameters=(parameter,),
    )
    provenance = CardRulesProvenance(
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
        materialization_algorithm_revision=COMMON_CARD_MATERIALIZATION_REVISION,
        rule_renderer_revision=CANONICAL_RULE_RENDERER_REVISION,
    )
    spec = StructuredCardSpec(
        imprint=_imprint(),
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
        provenance=provenance,
    )

    assert spec.stats.attack + spec.stats.defense == spec.stats.budget
    assert spec.traits[0].mechanic.branches[0].steps == (step,)
    assert spec.provenance.materialization_algorithm_revision.endswith("-v1")

    with pytest.raises(FrozenInstanceError):
        spec.level = 2  # type: ignore[misc]
