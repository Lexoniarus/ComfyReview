"""Behavior tests for combined existing-trait improvements."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    MechanicParameterProgression,
    MechanicUpgradeEdge,
)
from comfyreview.application.card_battler_development_improvement import (
    ExistingTraitImprovementPolicy,
)
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    MechanicParameterDefinition,
    MechanicStructureDefinition,
    MechanicTemplateDefinition,
    RuleTextTemplateDefinition,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.domain.card_battler import (
    MaterializedBranch,
    MaterializedMechanic,
    MaterializedParameter,
    MaterializedParameterUpgrade,
    MaterializedParameterValue,
    MaterializedStep,
)
from tests.test_card_battler_development_domain import _card_spec
from tests.test_card_battler_development_traits import (
    _DevelopmentRepository,
    _edge,
    _eligibility,
    _MaterializationRepository,
    _ModelRepository,
    _plan,
    _target_mechanic,
)
from tests.test_card_battler_initial_trait import _mechanic


class _CompleteDevelopmentRepository(_DevelopmentRepository):
    def __init__(
        self,
        edges: tuple[MechanicUpgradeEdge, ...] = (),
        progressions: tuple[MechanicParameterProgression, ...] = (),
    ) -> None:
        super().__init__(edges)
        self.progressions = progressions

    def mechanic_parameter_progression(
        self, ruleset: object = None
    ) -> tuple[MechanicParameterProgression, ...]:
        del ruleset
        return self.progressions


def _policy(
    development: _CompleteDevelopmentRepository,
    materialization: _MaterializationRepository,
) -> ExistingTraitImprovementPolicy:
    return ExistingTraitImprovementPolicy(
        cast(CardBattlerModelRepository, _ModelRepository()),
        cast(CardDevelopmentModelRepository, development),
        cast(CardMaterializationModelRepository, materialization),
        MechanicMaterializer(),
        CanonicalRuleRenderer(),
    )


def _parameter(
    *,
    key: str = "bonus",
    branch_key: str | None = None,
    step_order: int | None = None,
    value_type: str = "int",
    minimum: int | None = 0,
    maximum: int | None = 500,
    step: int | None = 50,
) -> MechanicParameterDefinition:
    return MechanicParameterDefinition(
        key=key,
        branch_key=branch_key,
        step_order=step_order,
        value_type=value_type,
        min_int=minimum,
        max_int=maximum,
        step_int=step,
        default_int=300 if key == "bonus" else 100,
        allowed_values=(),
        enum_values=(),
    )


def _definition(
    *,
    base_weight_milli: int = 750,
    parameters: tuple[MechanicParameterDefinition, ...] | None = None,
) -> MechanicTemplateDefinition:
    return replace(
        _mechanic("measured_strike", base_weight_milli),
        rule_text_templates=(
            RuleTextTemplateDefinition("de-DE", 1, "Bonus {bonus}."),
        ),
        structure=MechanicStructureDefinition(
            branches=(),
            condition_groups=(),
            costs=(),
            parameters=parameters or (_parameter(),),
        ),
    )


def _progression(
    *,
    parameter_key: str = "bonus",
    upgrade_step_int: int | None = 50,
    max_upgrade_steps: int | None = 3,
    budget_cost_milli: int = 125,
    min_tier_ordinal: int = 2,
    max_tier_ordinal: int | None = 15,
) -> MechanicParameterProgression:
    return MechanicParameterProgression(
        mechanic_key="measured_strike",
        parameter_key=parameter_key,
        min_tier_ordinal=min_tier_ordinal,
        max_tier_ordinal=max_tier_ordinal,
        upgrade_step_int=upgrade_step_int,
        max_upgrade_steps=max_upgrade_steps,
        budget_cost_milli=budget_cost_milli,
    )


def _card_with_mechanic(mechanic: MaterializedMechanic):
    card = _card_spec()
    return replace(
        card,
        traits=(replace(card.traits[0], mechanic=mechanic),),
    )


def test_existing_trait_improvement_applies_one_parameter_step() -> None:
    card = _card_spec()
    policy = _policy(
        _CompleteDevelopmentRepository(progressions=(_progression(),)),
        _MaterializationRepository(definitions=(_definition(),)),
    )

    action = policy.improve(card, _plan())

    assert action.previous_trait is card.traits[0]
    assert action.developed_trait.mechanic.parameters == (
        MaterializedParameter("bonus", 350),
    )
    assert action.developed_trait.parameter_upgrades == (
        MaterializedParameterUpgrade("bonus", 1),
    )
    assert action.developed_trait.canonical_rule_text == "Bonus 350."
    assert card.traits[0].mechanic.parameters[0].value == 300


def test_existing_trait_improvement_preserves_other_values_and_step_scope() -> (
    None
):
    definition = _definition(
        parameters=(
            _parameter(),
            _parameter(key="support", branch_key="main", step_order=1),
        )
    )
    branch = MaterializedBranch(
        key="main",
        order=1,
        branch_type="default",
        condition_groups=(),
        steps=(
            MaterializedStep(
                order=1,
                effect_type_key="buff",
                target_type_key="self",
                duration_type_key="instant",
                status_type_key=None,
                parameters=(MaterializedParameter("support", 100),),
            ),
        ),
    )
    mechanic = replace(_card_spec().traits[0].mechanic, branches=(branch,))
    action = _policy(
        _CompleteDevelopmentRepository(
            progressions=(_progression(parameter_key="support"),)
        ),
        _MaterializationRepository(definitions=(definition,)),
    ).improve(_card_with_mechanic(mechanic), _plan())

    assert action.developed_trait.mechanic.parameters[0].value == 300
    assert (
        action.developed_trait.mechanic.branches[0]
        .steps[0]
        .parameters[0]
        .value
        == 150
    )


def test_existing_trait_improvement_combines_edges_and_parameters_stably() -> (
    None
):
    current = _definition()
    target = _target_mechanic()
    development = _CompleteDevelopmentRepository(
        edges=(_edge(weight_milli=1),),
        progressions=(_progression(),),
    )
    materialization = _MaterializationRepository(
        definitions=(current, target), eligibility=(_eligibility(),)
    )

    forward = _policy(development, materialization).improve(
        _card_spec(), _plan()
    )
    reverse = _policy(
        _CompleteDevelopmentRepository(
            edges=tuple(reversed(development.edges)),
            progressions=tuple(reversed(development.progressions)),
        ),
        _MaterializationRepository(
            definitions=(target, current), eligibility=(_eligibility(),)
        ),
    ).improve(_card_spec(), _plan())

    assert forward == reverse


@pytest.mark.parametrize(
    ("parameter", "progression", "value", "upgrades", "definition_weight"),
    (
        (_parameter(value_type="enum"), _progression(), 300, (), 750),
        (_parameter(step=0), _progression(), 300, (), 750),
        (_parameter(), _progression(upgrade_step_int=None), 300, (), 750),
        (_parameter(), _progression(upgrade_step_int=-1), 300, (), 750),
        (_parameter(step=30), _progression(), 300, (), 750),
        (_parameter(), _progression(), -50, (), 750),
        (_parameter(), _progression(), 525, (), 750),
        (_parameter(), _progression(), 500, (), 750),
        (
            _parameter(),
            _progression(max_upgrade_steps=1),
            350,
            (MaterializedParameterUpgrade("bonus", 1),),
            750,
        ),
        (_parameter(), _progression(budget_cost_milli=-1), 300, (), 750),
        (_parameter(), _progression(), 300, (), 1400),
        (_parameter(), _progression(min_tier_ordinal=3), 300, (), 750),
        (_parameter(), _progression(max_tier_ordinal=1), 300, (), 750),
    ),
)
def test_existing_trait_improvement_rejects_illegal_parameter_steps(
    parameter: MechanicParameterDefinition,
    progression: MechanicParameterProgression,
    value: MaterializedParameterValue,
    upgrades: tuple[MaterializedParameterUpgrade, ...],
    definition_weight: int,
) -> None:
    card = _card_spec()
    mechanic = replace(
        card.traits[0].mechanic,
        parameters=(MaterializedParameter("bonus", value),),
    )
    card = replace(
        card,
        traits=(
            replace(
                card.traits[0],
                mechanic=mechanic,
                parameter_upgrades=upgrades,
            ),
        ),
    )

    with pytest.raises(CardDevelopmentPlanningError, match="no legal"):
        _policy(
            _CompleteDevelopmentRepository(progressions=(progression,)),
            _MaterializationRepository(
                definitions=(
                    _definition(
                        base_weight_milli=definition_weight,
                        parameters=(parameter,),
                    ),
                )
            ),
        ).improve(card, _plan())


def test_existing_trait_improvement_tracks_cumulative_budget_and_steps() -> (
    None
):
    card = _card_spec()
    card = replace(
        card,
        traits=(
            replace(
                card.traits[0],
                parameter_upgrades=(MaterializedParameterUpgrade("bonus", 1),),
            ),
        ),
    )
    action = _policy(
        _CompleteDevelopmentRepository(progressions=(_progression(),)),
        _MaterializationRepository(
            definitions=(_definition(base_weight_milli=1200),)
        ),
    ).improve(card, _plan())

    assert action.developed_trait.parameter_upgrades == (
        MaterializedParameterUpgrade("bonus", 2),
    )


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        ("duplicate_progression", "ambiguous"),
        ("duplicate_definition", "ambiguous"),
        ("duplicate_parameter_definition", "ambiguous"),
        ("duplicate_materialized", "ambiguous"),
        ("duplicate_upgrade", "ambiguous"),
        ("missing_definition", "unknown mechanic"),
        ("unknown_upgrade", "unique progression"),
        ("over_cap_upgrade", "step cap"),
        ("missing_position", "no legal"),
    ),
)
def test_existing_trait_improvement_rejects_ambiguous_or_stale_facts(
    mutate: str, message: str
) -> None:
    definition = _definition()
    definitions: tuple[MechanicTemplateDefinition, ...] = (definition,)
    progressions: tuple[MechanicParameterProgression, ...] = (_progression(),)
    card = _card_spec()
    if mutate == "duplicate_progression":
        progressions = (_progression(), _progression())
    elif mutate == "duplicate_definition":
        definitions = (definition, definition)
    elif mutate == "duplicate_parameter_definition":
        definitions = (_definition(parameters=(_parameter(), _parameter())),)
    elif mutate == "duplicate_materialized":
        card = _card_with_mechanic(
            replace(
                card.traits[0].mechanic,
                parameters=(
                    MaterializedParameter("bonus", 300),
                    MaterializedParameter("bonus", 300),
                ),
            )
        )
    elif mutate == "duplicate_upgrade":
        card = replace(
            card,
            traits=(
                replace(
                    card.traits[0],
                    parameter_upgrades=(
                        MaterializedParameterUpgrade("bonus", 1),
                        MaterializedParameterUpgrade("bonus", 1),
                    ),
                ),
            ),
        )
    elif mutate == "missing_definition":
        definitions = (_target_mechanic(),)
    elif mutate == "unknown_upgrade":
        card = replace(
            card,
            traits=(
                replace(
                    card.traits[0],
                    parameter_upgrades=(
                        MaterializedParameterUpgrade("other", 1),
                    ),
                ),
            ),
        )
    elif mutate == "over_cap_upgrade":
        card = replace(
            card,
            traits=(
                replace(
                    card.traits[0],
                    parameter_upgrades=(
                        MaterializedParameterUpgrade("bonus", 4),
                    ),
                ),
            ),
        )
    else:
        card = _card_with_mechanic(
            replace(card.traits[0].mechanic, parameters=())
        )

    with pytest.raises(CardDevelopmentPlanningError, match=message):
        _policy(
            _CompleteDevelopmentRepository(progressions=progressions),
            _MaterializationRepository(definitions=definitions),
        ).improve(card, _plan())


def test_existing_trait_improvement_requires_an_improvement_plan() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="authorize"):
        _policy(
            _CompleteDevelopmentRepository(),
            _MaterializationRepository(),
        ).improve(
            _card_spec(), _plan(primary_trait_action="add_compatible_trait")
        )


def test_existing_trait_improvement_can_select_a_registered_edge() -> None:
    current = _definition()
    action = _policy(
        _CompleteDevelopmentRepository(edges=(_edge(),)),
        _MaterializationRepository(
            definitions=(current, _target_mechanic()),
            eligibility=(_eligibility(),),
        ),
    ).improve(_card_spec(), _plan())

    assert action.developed_trait.mechanic.key == "perfect_form"
    assert action.developed_trait.parameter_upgrades == ()
