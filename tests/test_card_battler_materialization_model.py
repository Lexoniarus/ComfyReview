"""Behavior tests for focused Card Battler materialization model reads."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_materialization import (
    CardBalancePolicy,
    MechanicUsageLimitDefinition,
    RuleTextTemplateDefinition,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_materialization_model import (
    SqliteCardMaterializationModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS,
    SqliteCardBattlerModelResource,
)
from tests.test_card_battler_model import _create_model_database


def _repository(path: Path) -> SqliteCardMaterializationModelRepository:
    return SqliteCardMaterializationModelRepository(
        SqliteCardBattlerModelResource(
            path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
        )
    )


def test_materialization_model_reads_balance_tier_profiles_and_affinities(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)

    policy = repository.balance_policy()
    explicit = repository.balance_policy(key="prototype_balance", version=2)
    tier = repository.tier_balance_profile(
        policy, rarity_key="common", level=1
    )
    profiles = repository.stat_profiles()
    affinities = repository.stat_profile_affinities()

    assert (
        policy
        == explicit
        == CardBalancePolicy(
            key="prototype_balance",
            version=2,
            stat_rounding_step=50,
            atk_def_minimum=0,
            no_negative_stats=True,
            trait_budget_is_milli=True,
            calibration_status="prototype",
        )
    )
    assert (
        tier.rarity_key,
        tier.level,
        tier.ordinal,
        tier.stat_budget,
        tier.mechanic_budget_milli,
        tier.min_atk,
        tier.max_atk,
        tier.min_def,
        tier.max_def,
        tier.max_traits,
        tier.parameter_scale_milli,
    ) == ("common", 1, 1, 3000, 1000, 600, 2400, 600, 2400, 1, 1000)
    assert [profile.key for profile in profiles] == ["balanced", "offensive"]
    assert [
        (fact.source, fact.source_key, fact.stat_profile_key)
        for fact in affinities
    ] == sorted(
        (fact.source, fact.source_key, fact.stat_profile_key)
        for fact in affinities
    )
    assert len(affinities) == 12


def test_materialization_model_supports_an_explicit_ruleset_reference(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)
    active = CardBattlerRulesetRef(
        key="prototype",
        version=2,
        name="ignored",
        status="ignored",
        description="ignored",
        semantic_vocabulary_key="ignored",
        semantic_vocabulary_version=0,
    )

    assert repository.balance_policy(active).key == "prototype_balance"
    assert len(repository.stat_profiles(active)) == 2
    assert len(repository.stat_profile_affinities(active)) == 12
    assert len(repository.mechanic_definitions(active)) == 2
    assert len(repository.lineage_mechanic_eligibility(active)) == 2
    assert len(repository.mechanic_affinities(active)) == 16


def test_materialization_model_reads_stable_id_free_mechanic_facts(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)

    definitions = repository.mechanic_definitions()
    eligibility = repository.lineage_mechanic_eligibility()
    affinities = repository.mechanic_affinities()

    assert [definition.key for definition in definitions] == ["alpha", "zeta"]
    alpha = definitions[0]
    assert (
        alpha.key,
        alpha.internal_name,
        alpha.description,
        alpha.base_weight_milli,
        alpha.default_trigger_key,
        alpha.default_usage_limit_key,
    ) == (
        "alpha",
        "ALPHA",
        "Alpha mechanic",
        1100,
        "on_play",
        "once_per_turn",
    )
    assert alpha.usage_limits == (
        MechanicUsageLimitDefinition(
            usage_limit_key="once_per_turn",
            max_uses=1,
            scope="turn",
            reset_trigger_key="turn_start",
        ),
    )
    assert alpha.rule_text_templates == (
        RuleTextTemplateDefinition(
            locale="de-DE",
            version=1,
            template_text="Alpha-Regel",
        ),
        RuleTextTemplateDefinition(
            locale="en-US",
            version=1,
            template_text="Alpha rule",
        ),
    )
    assert (
        definitions[0].usage_limits[0].usage_limit_key,
        definitions[0].usage_limits[0].max_uses,
        definitions[0].usage_limits[0].scope,
        definitions[0].usage_limits[0].reset_trigger_key,
    ) == ("once_per_turn", 1, "turn", "turn_start")
    assert [
        (template.locale, template.version, template.template_text)
        for template in definitions[0].rule_text_templates
    ] == [
        ("de-DE", 1, "Alpha-Regel"),
        ("en-US", 1, "Alpha rule"),
    ]
    assert [
        (
            item.lineage_key,
            item.mechanic_key,
            item.min_tier_ordinal,
            item.max_tier_ordinal,
            item.selection_weight_milli,
        )
        for item in eligibility
    ] == [
        ("alpha", "alpha", 1, 2, 900),
        ("zeta", "zeta", 1, None, 700),
    ]
    assert [
        (fact.source, fact.source_key, fact.mechanic_key)
        for fact in affinities
    ] == sorted(
        (fact.source, fact.source_key, fact.mechanic_key)
        for fact in affinities
    )
    assert len(affinities) == 16


def test_materialization_model_assembles_complete_mechanic_structures(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)

    alpha, zeta = _repository(path).mechanic_definitions()

    assert [branch.key for branch in alpha.structure.branches] == [
        "main",
        "optional",
    ]
    assert [
        step.effect_type_key for step in alpha.structure.branches[0].steps
    ] == ["gain_attack"]
    assert [
        (
            link.order,
            link.condition_group_order,
            link.join_with_previous,
        )
        for link in alpha.structure.branches[1].condition_groups
    ] == [(1, 1, None)]
    group = alpha.structure.condition_groups[0]
    assert (group.order, group.operator, group.scope) == (1, "AND", "global")
    assert (
        group.conditions[0].condition_type_key,
        group.conditions[0].target_type_key,
        group.conditions[0].status_type_key,
        group.conditions[0].value_text,
    ) == ("has_status", "enemy", "marked", "marked")
    assert (
        alpha.structure.costs[0].cost_type_key,
        alpha.structure.costs[0].target_type_key,
        alpha.structure.costs[0].amount,
    ) == ("discard", "self", 1)
    assert [parameter.key for parameter in alpha.structure.parameters] == [
        "bonus",
        "mode",
    ]
    assert (
        alpha.structure.parameters[0].branch_key,
        alpha.structure.parameters[0].step_order,
        alpha.structure.parameters[0].default_int,
    ) == ("main", 1, 300)
    assert alpha.structure.parameters[1].allowed_values == ("soft", "hard")
    assert [
        value.key for value in alpha.structure.parameters[1].enum_values
    ] == ["soft", "hard"]
    assert [branch.key for branch in zeta.structure.branches] == ["main"]
    assert zeta.structure.condition_groups == ()
    assert zeta.structure.costs == ()
    assert zeta.structure.parameters[0].branch_key is None


@pytest.mark.parametrize(
    "statement, missing",
    (
        ("DROP TABLE rules_text_templates", "rules_text_templates"),
        ("DROP TABLE mechanic_steps", "mechanic_steps"),
        (
            "ALTER TABLE mechanic_usage_limits RENAME COLUMN scope TO absent",
            "scope",
        ),
        (
            "ALTER TABLE mechanic_parameters "
            "RENAME COLUMN allowed_values_json TO absent_values",
            "allowed_values_json",
        ),
    ),
)
def test_materialization_model_rejects_incomplete_mechanic_schema(
    tmp_path: Path,
    statement: str,
    missing: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute("PRAGMA foreign_keys = OFF")
        connection.execute(statement)
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match=missing):
        _repository(path).mechanic_definitions()


def test_materialization_model_rejects_cross_ruleset_mechanic_lookup(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            INSERT INTO trigger_types(
                id, ruleset_id, key, name, description, active
            ) VALUES (9, 2, 'foreign', 'Foreign', 'Foreign trigger', 1)
            """
        )
        connection.execute(
            "UPDATE mechanic_templates SET default_trigger_type_id = 9 "
            "WHERE key = 'alpha'"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="crosses a ruleset"):
        _repository(path).mechanic_definitions()


def test_materialization_model_rejects_invalid_parameter_enum_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE mechanic_parameters SET allowed_values_json = '{}' "
            "WHERE param_key = 'mode'"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="must contain text"):
        _repository(path).mechanic_definitions()


def test_materialization_model_rejects_cross_ruleset_structure_lookup(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            INSERT INTO condition_types(
                id, ruleset_id, key, name, description, active
            ) VALUES (9, 2, 'foreign', 'Foreign', 'Foreign condition', 1)
            """
        )
        connection.execute(
            "UPDATE mechanic_conditions SET condition_type_id = 9 WHERE id = 1"
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="condition lookup"):
        _repository(path).mechanic_definitions()


def test_materialization_model_rejects_unknown_or_invalid_requests(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)
    policy = repository.balance_policy()

    with pytest.raises(CardBattlerModelInvalid, match="requires a policy key"):
        repository.balance_policy(version=2)
    with pytest.raises(CardBattlerModelInvalid, match="cannot resolve"):
        repository.balance_policy(key="missing", version=1)
    with pytest.raises(ValueError, match="rarity_key"):
        repository.tier_balance_profile(policy, rarity_key="", level=1)
    with pytest.raises(ValueError, match="positive"):
        repository.tier_balance_profile(policy, rarity_key="common", level=0)
    with pytest.raises(CardBattlerModelInvalid, match="tier balance"):
        repository.tier_balance_profile(policy, rarity_key="common", level=99)
    with pytest.raises(
        CardBattlerModelInvalid, match="cannot resolve ruleset"
    ):
        repository.stat_profiles(
            CardBattlerRulesetRef(
                key="missing",
                version=1,
                name="missing",
                status="retired",
                description="missing",
                semantic_vocabulary_key="missing",
                semantic_vocabulary_version=1,
            )
        )


@pytest.mark.parametrize(
    "config_json",
    (
        "not-json",
        "[]",
        '{"atk_def_minimum":0}',
        (
            '{"atk_def_minimum":0,"calibration_status":"prototype",'
            '"no_negative_stats":1,"stat_rounding_step":50,'
            '"trait_budget_is_milli":true}'
        ),
        (
            '{"atk_def_minimum":0,"calibration_status":"",'
            '"no_negative_stats":true,"stat_rounding_step":50,'
            '"trait_budget_is_milli":true}'
        ),
        (
            '{"atk_def_minimum":0,"calibration_status":"prototype",'
            '"no_negative_stats":true,"stat_rounding_step":0,'
            '"trait_budget_is_milli":true}'
        ),
    ),
)
def test_materialization_model_rejects_malformed_balance_policy(
    tmp_path: Path,
    config_json: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE balance_policies SET config_json = ?", (config_json,)
        )
        connection.commit()
    finally:
        connection.close()

    with pytest.raises(CardBattlerModelInvalid, match="balance policy"):
        _repository(path).balance_policy()
