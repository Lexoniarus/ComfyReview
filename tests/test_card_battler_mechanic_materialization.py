"""Behavior tests for deterministic structured mechanic materialization."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_materialization import (
    MechanicBranchConditionGroupLink,
    MechanicBranchDefinition,
    MechanicConditionDefinition,
    MechanicConditionGroupDefinition,
    MechanicCostDefinition,
    MechanicParameterDefinition,
    MechanicParameterEnumValue,
    MechanicStepDefinition,
    MechanicStructureDefinition,
    MechanicTemplateDefinition,
    MechanicUsageLimitDefinition,
    TierBalanceProfile,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)
from comfyreview.application.card_battler_rules import MechanicMaterializer
from comfyreview.domain.card_battler import MaterializedParameter


def _tier(scale: int = 1000) -> TierBalanceProfile:
    return TierBalanceProfile(
        rarity_key="common",
        level=1,
        ordinal=1,
        stat_budget=3000,
        mechanic_budget_milli=1000,
        min_atk=600,
        max_atk=2400,
        min_def=600,
        max_def=2400,
        max_traits=1,
        parameter_scale_milli=scale,
    )


def _random() -> DomainSeparatedCardRandom:
    return DomainSeparatedCardRandom(("image-1", "42"))


def _bonus() -> MechanicParameterDefinition:
    return MechanicParameterDefinition(
        key="bonus",
        branch_key="main",
        step_order=1,
        value_type="int",
        min_int=100,
        max_int=500,
        step_int=100,
        default_int=300,
        allowed_values=(),
        enum_values=(),
    )


def _mode() -> MechanicParameterDefinition:
    return MechanicParameterDefinition(
        key="mode",
        branch_key="optional",
        step_order=1,
        value_type="enum",
        min_int=None,
        max_int=None,
        step_int=None,
        default_int=None,
        allowed_values=("soft", "hard"),
        enum_values=(
            MechanicParameterEnumValue("hard", 2, "Hard mode"),
            MechanicParameterEnumValue("soft", 1, "Soft mode"),
        ),
    )


def _enabled() -> MechanicParameterDefinition:
    return MechanicParameterDefinition(
        key="enabled",
        branch_key=None,
        step_order=None,
        value_type="bool",
        min_int=None,
        max_int=None,
        step_int=None,
        default_int=None,
        allowed_values=(),
        enum_values=(),
    )


def _condition() -> MechanicConditionDefinition:
    return MechanicConditionDefinition(
        order=1,
        condition_type_key="has_status",
        target_type_key="enemy",
        comparator="eq",
        value_int=None,
        value_text="marked",
        negated=False,
        status_type_key="marked",
    )


def _group() -> MechanicConditionGroupDefinition:
    return MechanicConditionGroupDefinition(
        order=1,
        operator="AND",
        join_with_previous=None,
        scope="global",
        conditions=(_condition(),),
    )


def _main_branch() -> MechanicBranchDefinition:
    return MechanicBranchDefinition(
        key="main",
        order=1,
        branch_type="main",
        description="Primary branch",
        condition_groups=(MechanicBranchConditionGroupLink(1, 1, None),),
        steps=(
            MechanicStepDefinition(
                1, "gain_attack", "self", "turn", None, "Gain attack"
            ),
        ),
    )


def _optional_branch() -> MechanicBranchDefinition:
    return MechanicBranchDefinition(
        key="optional",
        order=2,
        branch_type="optional",
        description=None,
        condition_groups=(),
        steps=(
            MechanicStepDefinition(
                1,
                "apply_status",
                "enemy",
                "turn",
                "marked",
                "Mark enemy",
            ),
        ),
    )


def _mechanic() -> MechanicTemplateDefinition:
    return MechanicTemplateDefinition(
        key="alpha",
        internal_name="ALPHA",
        description="Alpha mechanic",
        base_weight_milli=1100,
        default_trigger_key="on_play",
        default_usage_limit_key="once_per_turn",
        usage_limits=(
            MechanicUsageLimitDefinition(
                "once_per_turn", 1, "turn", "turn_start"
            ),
        ),
        rule_text_templates=(),
        structure=MechanicStructureDefinition(
            branches=(_optional_branch(), _main_branch()),
            condition_groups=(_group(),),
            costs=(MechanicCostDefinition(1, "discard", "self", 1, None),),
            parameters=(_mode(), _enabled(), _bonus()),
        ),
    )


def _with_structure(
    mechanic: MechanicTemplateDefinition,
    *,
    branches: tuple[MechanicBranchDefinition, ...] | None = None,
    condition_groups: tuple[MechanicConditionGroupDefinition, ...]
    | None = None,
    costs: tuple[MechanicCostDefinition, ...] | None = None,
    parameters: tuple[MechanicParameterDefinition, ...] | None = None,
) -> MechanicTemplateDefinition:
    structure = mechanic.structure
    return replace(
        mechanic,
        structure=replace(
            structure,
            branches=structure.branches if branches is None else branches,
            condition_groups=(
                structure.condition_groups
                if condition_groups is None
                else condition_groups
            ),
            costs=structure.costs if costs is None else costs,
            parameters=(
                structure.parameters if parameters is None else parameters
            ),
        ),
    )


def test_mechanic_materializer_builds_complete_authoritative_graph() -> None:
    materialized = MechanicMaterializer().materialize(
        _mechanic(), _tier(), _random()
    )

    assert (materialized.key, materialized.trigger_key) == ("alpha", "on_play")
    assert materialized.usage_limits[0].usage_limit_key == "once_per_turn"
    assert materialized.condition_groups[0].conditions[0].value == "marked"
    assert [branch.key for branch in materialized.branches] == [
        "main",
        "optional",
    ]
    assert (
        materialized.branches[0].condition_groups[0].condition_group_order == 1
    )
    assert materialized.branches[0].steps[0].parameters == (
        MaterializedParameter("bonus", 300),
    )
    assert materialized.branches[1].steps[0].parameters == (
        MaterializedParameter("mode", "soft"),
    )
    assert materialized.costs[0].amount == 1
    assert materialized.parameters == (MaterializedParameter("enabled", True),)


def test_mechanic_materializer_is_input_order_independent() -> None:
    mechanic = _mechanic()
    reversed_groups = tuple(
        replace(group, conditions=tuple(reversed(group.conditions)))
        for group in reversed(mechanic.structure.condition_groups)
    )
    reversed_branches = tuple(
        replace(
            branch,
            condition_groups=tuple(reversed(branch.condition_groups)),
            steps=tuple(reversed(branch.steps)),
        )
        for branch in reversed(mechanic.structure.branches)
    )
    reordered = replace(
        mechanic,
        usage_limits=tuple(reversed(mechanic.usage_limits)),
        structure=replace(
            mechanic.structure,
            branches=reversed_branches,
            condition_groups=reversed_groups,
            costs=tuple(reversed(mechanic.structure.costs)),
            parameters=tuple(reversed(mechanic.structure.parameters)),
        ),
    )

    assert MechanicMaterializer().materialize(
        mechanic, _tier(), _random()
    ) == MechanicMaterializer().materialize(reordered, _tier(), _random())


def test_integer_parameter_scaling_uses_isolated_rng() -> None:
    materialized = MechanicMaterializer().materialize(
        _mechanic(), _tier(1500), _random()
    )

    assert materialized.branches[0].steps[0].parameters == (
        MaterializedParameter("bonus", 500),
    )
    assert _random().integer(
        "initial-trait", modulo=1_000_000
    ) == _random().integer("initial-trait", modulo=1_000_000)


def test_mechanic_materializer_rejects_invalid_parameter_contracts() -> None:
    invalid_parameters = (
        (replace(_bonus(), key=""), "unique stable keys"),
        ((_bonus(), _bonus()), "unique stable keys"),
        (
            replace(_bonus(), value_type="unknown"),
            "unknown mechanic parameter",
        ),
        (
            replace(_bonus(), min_int=None),
            "require min, max, step and default",
        ),
        (replace(_bonus(), step_int=0), "bounds are invalid"),
        (replace(_bonus(), default_int=350), "bounds are invalid"),
        (replace(_bonus(), allowed_values=("bad",)), "bounds are invalid"),
        (replace(_mode(), min_int=1), "cannot define integer bounds"),
        (
            replace(_mode(), allowed_values=("different",)),
            "catalogs disagree",
        ),
        (
            replace(_mode(), allowed_values=(), enum_values=()),
            "unique allowed values",
        ),
        (replace(_enabled(), allowed_values=("bad",)), "value catalogs"),
    )
    for value, message in invalid_parameters:
        parameters = value if isinstance(value, tuple) else (value,)
        mechanic = _with_structure(_mechanic(), parameters=parameters)
        with pytest.raises(CardBattlerModelInvalid, match=message):
            MechanicMaterializer().materialize(mechanic, _tier(), _random())


def test_mechanic_materializer_rejects_invalid_top_level_contracts() -> None:
    mechanic = _mechanic()
    invalid = (
        (replace(mechanic, key=""), _tier(), "stable key"),
        (mechanic, _tier(0), "scale must be positive"),
        (
            replace(
                mechanic,
                usage_limits=mechanic.usage_limits + mechanic.usage_limits,
            ),
            _tier(),
            "usage limits are ambiguous",
        ),
        (
            replace(mechanic, default_usage_limit_key="missing"),
            _tier(),
            "default usage limit",
        ),
    )
    for candidate, tier, message in invalid:
        with pytest.raises(CardBattlerModelInvalid, match=message):
            MechanicMaterializer().materialize(candidate, tier, _random())


def test_mechanic_materializer_rejects_ambiguous_graphs() -> None:
    mechanic = _mechanic()
    duplicate_condition = replace(
        _group(), conditions=(_condition(), _condition())
    )
    ambiguous_value = replace(_condition(), value_int=1)
    duplicate_groups = (_group(), _group())
    duplicate_branches = (_main_branch(), _main_branch())
    duplicate_branch_keys = (
        _main_branch(),
        replace(_optional_branch(), key="main"),
    )
    bad_cases = (
        (
            _with_structure(mechanic, condition_groups=(duplicate_condition,)),
            "conditions require unique",
        ),
        (
            _with_structure(
                mechanic,
                condition_groups=(
                    replace(_group(), conditions=(ambiguous_value,)),
                ),
            ),
            "ambiguous values",
        ),
        (
            _with_structure(mechanic, condition_groups=duplicate_groups),
            "condition groups require unique",
        ),
        (
            _with_structure(mechanic, branches=duplicate_branches),
            "branches require unique ordering",
        ),
        (
            _with_structure(mechanic, branches=duplicate_branch_keys),
            "branches require unique stable keys",
        ),
        (
            _with_structure(
                mechanic,
                parameters=(replace(_bonus(), branch_key="missing"),),
            ),
            "unknown branch",
        ),
        (
            _with_structure(
                mechanic,
                parameters=(replace(_bonus(), step_order=None),),
            ),
            "scope requires branch and step",
        ),
        (
            _with_structure(
                mechanic,
                parameters=(replace(_bonus(), step_order=99),),
            ),
            "unknown step",
        ),
        (
            _with_structure(
                mechanic,
                branches=(
                    replace(
                        _main_branch(),
                        condition_groups=(
                            MechanicBranchConditionGroupLink(1, 99, None),
                        ),
                    ),
                ),
                parameters=(),
            ),
            "unknown condition group",
        ),
        (
            _with_structure(
                mechanic,
                branches=(
                    replace(
                        _main_branch(),
                        condition_groups=(
                            MechanicBranchConditionGroupLink(1, 1, None),
                            MechanicBranchConditionGroupLink(1, 1, "AND"),
                        ),
                    ),
                ),
                parameters=(),
            ),
            "branch condition links require unique",
        ),
        (
            _with_structure(
                mechanic,
                branches=(
                    replace(
                        _main_branch(),
                        steps=_main_branch().steps + _main_branch().steps,
                    ),
                ),
                parameters=(),
            ),
            "mechanic steps require unique",
        ),
        (
            _with_structure(
                mechanic,
                costs=mechanic.structure.costs + mechanic.structure.costs,
            ),
            "mechanic costs require unique",
        ),
    )
    for candidate, message in bad_cases:
        with pytest.raises(CardBattlerModelInvalid, match=message):
            MechanicMaterializer().materialize(candidate, _tier(), _random())
