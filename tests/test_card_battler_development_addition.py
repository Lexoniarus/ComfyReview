"""Behavior tests for deterministic compatible-trait addition."""

from __future__ import annotations

from dataclasses import replace
from typing import Any, cast

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentModelRepository,
    CardDevelopmentPlanningError,
    CardDevelopmentPolicy,
    LineageCompatibility,
    MechanicCompatibility,
    MechanicParameterProgression,
)
from comfyreview.application.card_battler_development_addition import (
    CompatibleTraitAdditionPolicy,
)
from comfyreview.application.card_battler_materialization import (
    CardMaterializationModelRepository,
    LineageMechanicEligibility,
    MechanicTemplateDefinition,
    RuleTextTemplateDefinition,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelRepository,
    CardBattlerRulesetRef,
    CompatibilityFact,
)
from comfyreview.application.card_battler_rules import (
    CanonicalRuleRenderer,
    MechanicMaterializer,
)
from comfyreview.domain.card_battler import MaterializedParameterUpgrade
from tests.test_card_battler_development_domain import _card_spec
from tests.test_card_battler_development_traits import (
    _MaterializationRepository,
    _ModelRepository,
    _plan,
    _tier,
)
from tests.test_card_battler_initial_trait import _mechanic


class _CompatibleModelRepository(_ModelRepository):
    def __init__(
        self,
        class_facts: tuple[CompatibilityFact, ...],
        role_facts: tuple[CompatibilityFact, ...],
    ) -> None:
        self.class_facts = class_facts
        self.role_facts = role_facts

    def class_lineage_compatibility(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[CompatibilityFact, ...]:
        del ruleset
        return self.class_facts

    def role_lineage_compatibility(
        self, ruleset: CardBattlerRulesetRef | None = None
    ) -> tuple[CompatibilityFact, ...]:
        del ruleset
        return self.role_facts


class _CompatibleDevelopmentRepository:
    def __init__(
        self,
        *,
        policy: CardDevelopmentPolicy | None = None,
        lineages: tuple[LineageCompatibility, ...] = (),
        mechanics: tuple[MechanicCompatibility, ...] = (),
        progressions: tuple[MechanicParameterProgression, ...] = (),
    ) -> None:
        self.policy = policy or _development_policy()
        self.lineages = lineages
        self.mechanics = mechanics
        self.progressions = progressions

    def development_policy(
        self, ruleset: object = None
    ) -> CardDevelopmentPolicy:
        del ruleset
        return self.policy

    def lineage_compatibility(
        self, ruleset: object = None
    ) -> tuple[LineageCompatibility, ...]:
        del ruleset
        return self.lineages

    def mechanic_compatibility(
        self, ruleset: object = None
    ) -> tuple[MechanicCompatibility, ...]:
        del ruleset
        return self.mechanics

    def mechanic_parameter_progression(
        self, ruleset: object = None
    ) -> tuple[MechanicParameterProgression, ...]:
        del ruleset
        return self.progressions


def _development_policy(
    *,
    requires_cross: bool = True,
    prefer_anchor: bool = True,
) -> CardDevelopmentPolicy:
    return CardDevelopmentPolicy(
        key="lineage_preserving",
        version=2,
        cross_lineage_requires_compatibility=requires_cross,
        immutable_imprint_dimensions=("trait_lineage",),
        legendary_locked_in_prototype=True,
        prefer_existing_lineage=prefer_anchor,
        primary_trait_actions=("add_compatible_trait",),
    )


def _definition(key: str, *, weight: int = 500) -> MechanicTemplateDefinition:
    return replace(
        _mechanic(key, weight),
        rule_text_templates=(
            RuleTextTemplateDefinition("de-DE", 1, f"Regel {key}."),
        ),
    )


def _eligibility(
    lineage: str = "marking",
    mechanic: str = "support_fire",
    *,
    minimum: int = 1,
    maximum: int | None = 15,
    weight: int = 1000,
) -> LineageMechanicEligibility:
    return LineageMechanicEligibility(
        lineage,
        mechanic,
        minimum,
        maximum,
        weight,
    )


def _axis_fact(
    source: str,
    lineage: str,
    *,
    enabled: bool = True,
    weight: int = 800,
) -> CompatibilityFact:
    return CompatibilityFact(source, lineage, weight, enabled)


def _mechanic_fact(
    target: str = "support_fire",
    *,
    relation: str = "compatible",
    weight: int = 800,
) -> MechanicCompatibility:
    return MechanicCompatibility(
        "measured_strike",
        target,
        cast(object, relation),  # type: ignore[arg-type]
        weight,
        None,
    )


def _lineage_fact(
    target: str = "focus",
    *,
    relation: str = "compatible",
    weight: int = 700,
) -> LineageCompatibility:
    return LineageCompatibility(
        "marking",
        target,
        cast(object, relation),  # type: ignore[arg-type]
        weight,
        None,
    )


def _policy(
    *,
    eligibility: tuple[LineageMechanicEligibility, ...] | None = None,
    definitions: tuple[MechanicTemplateDefinition, ...] | None = None,
    class_facts: tuple[CompatibilityFact, ...] | None = None,
    role_facts: tuple[CompatibilityFact, ...] | None = None,
    development: _CompatibleDevelopmentRepository | None = None,
    materialization: _MaterializationRepository | None = None,
) -> CompatibleTraitAdditionPolicy:
    model = _CompatibleModelRepository(
        class_facts or (_axis_fact("ranger", "marking"),),
        role_facts or (_axis_fact("precision", "marking"),),
    )
    materialization = materialization or _MaterializationRepository(
        definitions=definitions
        or (
            _definition("measured_strike", weight=750),
            _definition("support_fire"),
        ),
        eligibility=eligibility or (_eligibility(),),
    )
    return CompatibleTraitAdditionPolicy(
        cast(CardBattlerModelRepository, model),
        cast(
            CardDevelopmentModelRepository,
            development
            or _CompatibleDevelopmentRepository(mechanics=(_mechanic_fact(),)),
        ),
        cast(CardMaterializationModelRepository, materialization),
        MechanicMaterializer(),
        CanonicalRuleRenderer(),
    )


def _addition_plan():
    return _plan(primary_trait_action="add_compatible_trait")


def test_compatible_trait_addition_prefers_the_imprint_lineage() -> None:
    eligibility = (
        _eligibility(),
        _eligibility("focus", "focused_fire"),
    )
    definitions = (
        _definition("measured_strike", weight=750),
        _definition("support_fire"),
        _definition("focused_fire"),
    )
    action = _policy(
        eligibility=eligibility,
        definitions=definitions,
        class_facts=(
            _axis_fact("ranger", "marking"),
            _axis_fact("ranger", "focus"),
        ),
        role_facts=(
            _axis_fact("precision", "marking"),
            _axis_fact("precision", "focus"),
        ),
        development=_CompatibleDevelopmentRepository(
            lineages=(_lineage_fact(),),
            mechanics=(
                _mechanic_fact(),
                _mechanic_fact("focused_fire"),
            ),
        ),
    ).add(_card_spec(), _addition_plan())

    assert action.action == "add_compatible_trait"
    assert action.trait_index == 1
    assert action.previous_trait is None
    assert action.developed_trait.lineage_key == "marking"
    assert action.developed_trait.mechanic.key == "support_fire"
    assert action.developed_trait.canonical_rule_text == "Regel support_fire."


def test_compatible_trait_addition_allows_explicit_cross_lineage() -> None:
    action = _policy(
        eligibility=(_eligibility("focus", "focused_fire"),),
        definitions=(
            _definition("measured_strike", weight=750),
            _definition("focused_fire"),
        ),
        class_facts=(_axis_fact("ranger", "focus"),),
        role_facts=(_axis_fact("precision", "focus"),),
        development=_CompatibleDevelopmentRepository(
            lineages=(_lineage_fact(),),
            mechanics=(_mechanic_fact("focused_fire"),),
        ),
    ).add(_card_spec(), _addition_plan())

    assert action.developed_trait.lineage_key == "focus"


def test_compatible_trait_addition_is_repository_order_independent() -> None:
    eligibility = (
        _eligibility("focus", "focused_fire"),
        _eligibility("marking", "support_fire"),
    )
    definitions = (
        _definition("measured_strike", weight=750),
        _definition("focused_fire"),
        _definition("support_fire"),
    )
    class_facts = (
        _axis_fact("ranger", "focus"),
        _axis_fact("ranger", "marking"),
    )
    role_facts = (
        _axis_fact("precision", "focus"),
        _axis_fact("precision", "marking"),
    )
    development = _CompatibleDevelopmentRepository(
        policy=_development_policy(prefer_anchor=False),
        lineages=(_lineage_fact(),),
        mechanics=(_mechanic_fact("focused_fire"), _mechanic_fact()),
    )
    forward = _policy(
        eligibility=eligibility,
        definitions=definitions,
        class_facts=class_facts,
        role_facts=role_facts,
        development=development,
    ).add(_card_spec(), _addition_plan())
    reverse = _policy(
        eligibility=tuple(reversed(eligibility)),
        definitions=tuple(reversed(definitions)),
        class_facts=tuple(reversed(class_facts)),
        role_facts=tuple(reversed(role_facts)),
        development=_CompatibleDevelopmentRepository(
            policy=_development_policy(prefer_anchor=False),
            lineages=tuple(reversed(development.lineages)),
            mechanics=tuple(reversed(development.mechanics)),
        ),
    ).add(_card_spec(), _addition_plan())

    assert forward == reverse


@pytest.mark.parametrize(
    "policy",
    (
        _policy(eligibility=(_eligibility(minimum=3),)),
        _policy(eligibility=(_eligibility(maximum=1),)),
        _policy(eligibility=(_eligibility(weight=0),)),
        _policy(eligibility=(_eligibility(mechanic="measured_strike"),)),
        _policy(
            eligibility=(_eligibility(mechanic="missing"),),
            definitions=(_definition("measured_strike", weight=750),),
        ),
        _policy(class_facts=(_axis_fact("ranger", "marking", enabled=False),)),
        _policy(role_facts=(_axis_fact("precision", "marking", weight=0),)),
        _policy(development=_CompatibleDevelopmentRepository()),
        _policy(
            development=_CompatibleDevelopmentRepository(
                mechanics=(_mechanic_fact(relation="incompatible"),)
            )
        ),
        _policy(
            definitions=(
                _definition("measured_strike", weight=1000),
                _definition("support_fire", weight=600),
            )
        ),
    ),
)
def test_compatible_trait_addition_rejects_illegal_candidates(
    policy: CompatibleTraitAdditionPolicy,
) -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="no legal"):
        policy.add(_card_spec(), _addition_plan())


def test_compatible_trait_addition_requires_explicit_cross_lineage() -> None:
    eligibility = (_eligibility("focus", "focused_fire"),)
    definitions = (
        _definition("measured_strike", weight=750),
        _definition("focused_fire"),
    )
    class_facts = (_axis_fact("ranger", "focus"),)
    role_facts = (_axis_fact("precision", "focus"),)
    with pytest.raises(CardDevelopmentPlanningError, match="no legal"):
        _policy(
            eligibility=eligibility,
            definitions=definitions,
            class_facts=class_facts,
            role_facts=role_facts,
            development=_CompatibleDevelopmentRepository(
                mechanics=(_mechanic_fact("focused_fire"),)
            ),
        ).add(_card_spec(), _addition_plan())

    action = _policy(
        eligibility=eligibility,
        definitions=definitions,
        class_facts=class_facts,
        role_facts=role_facts,
        development=_CompatibleDevelopmentRepository(
            policy=_development_policy(requires_cross=False),
            mechanics=(_mechanic_fact("focused_fire"),),
        ),
    ).add(_card_spec(), _addition_plan())
    assert action.developed_trait.lineage_key == "focus"


@pytest.mark.parametrize(
    ("kind", "message"),
    (
        ("class", "class lineage"),
        ("role", "role lineage"),
        ("lineage", "lineage compatibility"),
        ("mechanic", "mechanic compatibility"),
        ("candidate", "candidates"),
        ("definition", "definitions"),
    ),
)
def test_compatible_trait_addition_rejects_ambiguous_model_facts(
    kind: str, message: str
) -> None:
    kwargs: dict[str, Any] = {}
    development = _CompatibleDevelopmentRepository(
        mechanics=(_mechanic_fact(),)
    )
    if kind == "class":
        class_fact = _axis_fact("ranger", "marking")
        kwargs["class_facts"] = (class_fact, class_fact)
    elif kind == "role":
        role_fact = _axis_fact("precision", "marking")
        kwargs["role_facts"] = (role_fact, role_fact)
    elif kind == "lineage":
        lineage_fact = _lineage_fact()
        development = _CompatibleDevelopmentRepository(
            lineages=(lineage_fact, lineage_fact),
            mechanics=(_mechanic_fact(),),
        )
    elif kind == "mechanic":
        mechanic_fact = _mechanic_fact()
        development = _CompatibleDevelopmentRepository(
            mechanics=(mechanic_fact, mechanic_fact)
        )
    elif kind == "candidate":
        kwargs["eligibility"] = (_eligibility(), _eligibility())
    else:
        current = _definition("measured_strike", weight=750)
        kwargs["definitions"] = (current, current)

    with pytest.raises(CardDevelopmentPlanningError, match=message):
        _policy(development=development, **kwargs).add(
            _card_spec(), _addition_plan()
        )


def test_compatible_trait_addition_validates_plan_and_free_slot() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="authorize"):
        _policy().add(_card_spec(), _plan())
    with pytest.raises(CardDevelopmentPlanningError, match="free"):
        _policy().add(replace(_card_spec(), traits=()), _addition_plan())
    with pytest.raises(CardDevelopmentPlanningError, match="free"):
        _policy().add(_card_spec(), replace(_addition_plan(), trait_cap=1))
    stale_materialization = _MaterializationRepository(
        definitions=(
            _definition("measured_strike", weight=750),
            _definition("support_fire"),
        ),
        tier=_tier(stat_budget=3300),
    )
    with pytest.raises(CardDevelopmentPlanningError, match="balance tier"):
        _policy(materialization=stale_materialization).add(
            _card_spec(), _addition_plan()
        )


@pytest.mark.parametrize(
    ("steps", "maximum", "message"),
    ((0, 3, "unique progression"), (4, 3, "step cap")),
)
def test_compatible_trait_addition_validates_existing_parameter_cost(
    steps: int, maximum: int, message: str
) -> None:
    card = _card_spec()
    card = replace(
        card,
        traits=(
            replace(
                card.traits[0],
                parameter_upgrades=(
                    MaterializedParameterUpgrade("bonus", steps),
                ),
            ),
        ),
    )
    progression = MechanicParameterProgression(
        "measured_strike", "bonus", 1, 15, 50, maximum, 125
    )
    with pytest.raises(CardDevelopmentPlanningError, match=message):
        _policy(
            development=_CompatibleDevelopmentRepository(
                mechanics=(_mechanic_fact(),),
                progressions=(progression,),
            )
        ).add(card, _addition_plan())


def test_compatible_trait_addition_counts_existing_parameter_cost() -> None:
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
    progression = MechanicParameterProgression(
        "measured_strike", "bonus", 1, 15, 50, 3, 125
    )

    action = _policy(
        development=_CompatibleDevelopmentRepository(
            mechanics=(_mechanic_fact(),),
            progressions=(progression,),
        )
    ).add(card, _addition_plan())

    assert action.developed_trait.mechanic.key == "support_fire"


def test_compatible_trait_addition_rejects_unknown_existing_mechanic() -> None:
    with pytest.raises(CardDevelopmentPlanningError, match="unknown mechanic"):
        _policy(
            definitions=(_definition("support_fire"),),
        ).add(_card_spec(), _addition_plan())
