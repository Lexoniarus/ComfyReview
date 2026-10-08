"""Behavior tests for focused Card Battler development model reads."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_development import (
    CardDevelopmentPolicy,
)
from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.repositories.sqlite.card_battler_development_model import (
    SqliteCardDevelopmentModelRepository,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS,
    SqliteCardBattlerModelResource,
)
from tests.test_card_battler_model import _create_model_database


def _repository(path: Path) -> SqliteCardDevelopmentModelRepository:
    return SqliteCardDevelopmentModelRepository(
        SqliteCardBattlerModelResource(
            path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
        )
    )


def _execute(path: Path, *statements: str) -> None:
    connection = sqlite3.connect(path)
    try:
        for statement in statements:
            connection.execute(statement)
        connection.commit()
    finally:
        connection.close()


def _update_policy_config(path: Path, config_json: str) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            "UPDATE development_policies SET config_json = ?",
            (config_json,),
        )
        connection.commit()
    finally:
        connection.close()


def test_development_model_reads_policy_ladder_budgets_caps_and_weights(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)

    policy = repository.development_policy()
    explicit = repository.development_policy(
        key="lineage_preserving_development", version=2
    )
    ladder = repository.development_ladder(
        balance_policy_key="prototype_balance", balance_policy_version=2
    )
    weights = repository.development_action_weights()

    assert (
        policy
        == explicit
        == CardDevelopmentPolicy(
            key="lineage_preserving_development",
            version=2,
            cross_lineage_requires_compatibility=True,
            immutable_imprint_dimensions=(
                "world_style",
                "card_class",
                "combat_role",
                "trait_lineage",
            ),
            legendary_locked_in_prototype=True,
            prefer_existing_lineage=True,
            primary_trait_actions=(
                "add_first_trait",
                "improve_existing_trait",
                "add_compatible_trait",
            ),
        )
    )
    assert [tier.ordinal for tier in ladder] == [1, 2]
    assert (
        ladder[0].rarity_key,
        ladder[0].level,
        ladder[0].next_ordinal,
        ladder[0].stat_budget,
        ladder[0].mechanic_budget_milli,
        ladder[0].trait_cap,
        ladder[0].parameter_scale_milli,
    ) == ("common", 1, 2, 3000, 1000, 1, 1000)
    assert (
        ladder[1].rarity_key,
        ladder[1].development_locked,
        ladder[1].next_ordinal,
        ladder[1].trait_cap,
    ) == ("rare", True, None, 2)
    assert [
        (weight.tier_ordinal, weight.action_key) for weight in weights
    ] == sorted((weight.tier_ordinal, weight.action_key) for weight in weights)
    assert [
        (weight.action_key, weight.weight_milli, weight.enabled)
        for weight in weights[:3]
    ] == [
        ("add_compatible_trait", 0, False),
        ("add_first_trait", 1000, True),
        ("improve_existing_trait", 800, True),
    ]


def test_development_model_supports_an_explicit_ruleset_reference(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    ruleset = CardBattlerRulesetRef(
        key="prototype",
        version=2,
        name="ignored",
        status="ignored",
        description="ignored",
        semantic_vocabulary_key="ignored",
        semantic_vocabulary_version=0,
    )

    repository = _repository(path)

    assert repository.development_policy(ruleset).version == 2
    assert len(repository.development_ladder(ruleset)) == 2
    assert len(repository.development_action_weights(ruleset)) == 6


@pytest.mark.parametrize(
    ("statement", "message"),
    (
        (
            "UPDATE development_policies SET config_json = '{}'",
            "cross_lineage_requires_compatibility",
        ),
        (
            "DELETE FROM tier_balance_profiles WHERE tier_id = 2",
            "missing a balance profile",
        ),
        (
            "UPDATE development_tiers SET next_tier_id = NULL WHERE id = 1",
            "do not form one ladder",
        ),
        (
            "UPDATE tier_balance_profiles SET max_traits = 2 WHERE tier_id = 1",
            "trait cap is invalid",
        ),
    ),
)
def test_development_model_rejects_invalid_policy_or_ladder_facts(
    tmp_path: Path,
    statement: str,
    message: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(path, statement)

    repository = _repository(path)

    with pytest.raises(CardBattlerModelInvalid, match=message):
        if statement.startswith("UPDATE development_policies"):
            repository.development_policy()
        else:
            repository.development_ladder()


@pytest.mark.parametrize(
    ("statement", "missing"),
    (
        ("DROP TABLE development_policies", "development_policies"),
        (
            "ALTER TABLE tier_development_action_weights "
            "RENAME COLUMN weight_milli TO absent",
            "weight_milli",
        ),
    ),
)
def test_development_model_schema_contract_covers_every_new_read_area(
    tmp_path: Path,
    statement: str,
    missing: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(path, statement)

    with pytest.raises(CardBattlerModelInvalid, match=missing):
        _repository(path).development_policy()


@pytest.mark.parametrize(
    ("config_json", "message"),
    (
        ("not-json", "invalid JSON"),
        ("[]", "must be an object"),
        (
            '{"cross_lineage_requires_compatibility":"yes"}',
            "must be boolean",
        ),
        (
            '{"cross_lineage_requires_compatibility":true,'
            '"immutable_imprint_dimensions":[],'
            '"legendary_locked_in_prototype":true,'
            '"prefer_existing_lineage":true,'
            '"primary_trait_actions":["improve_existing_trait"]}',
            "non-empty list",
        ),
        (
            '{"cross_lineage_requires_compatibility":true,'
            '"immutable_imprint_dimensions":[1],'
            '"legendary_locked_in_prototype":true,'
            '"prefer_existing_lineage":true,'
            '"primary_trait_actions":["improve_existing_trait"]}',
            "must contain text",
        ),
        (
            '{"cross_lineage_requires_compatibility":true,'
            '"immutable_imprint_dimensions":["card_class","card_class"],'
            '"legendary_locked_in_prototype":true,'
            '"prefer_existing_lineage":true,'
            '"primary_trait_actions":["improve_existing_trait"]}',
            "contains duplicates",
        ),
    ),
)
def test_development_model_rejects_malformed_policy_config(
    tmp_path: Path,
    config_json: str,
    message: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _update_policy_config(path, config_json)

    with pytest.raises(CardBattlerModelInvalid, match=message):
        _repository(path).development_policy()


@pytest.mark.parametrize(
    ("statements", "read", "message"),
    (
        (
            ("UPDATE rarities SET active = 0",),
            "ladder",
            "ladder is empty",
        ),
        (
            ("UPDATE development_tiers SET ordinal = 1 WHERE id = 2",),
            "ladder",
            "ordinals are ambiguous",
        ),
        (
            (
                "INSERT INTO rarities(id, ruleset_id, key, name, ordinal, "
                "max_traits, active) VALUES (3, 2, 'retired', 'Retired', 1, 1, 1)",
                "INSERT INTO development_tiers(id, ruleset_id, rarity_id, "
                "level, ordinal, next_tier_id, development_locked) "
                "VALUES (3, 2, 3, 1, 1, NULL, 0)",
                "UPDATE development_tiers SET next_tier_id = 3 WHERE id = 1",
            ),
            "ladder",
            "another ruleset",
        ),
        (
            (
                "INSERT INTO development_action_types(id, ruleset_id, key, "
                "name, description, active) VALUES "
                "(4, 1, 'add_first_trait', 'Duplicate', 'Duplicate', 1)",
                "INSERT INTO tier_development_action_weights("
                "tier_id, action_type_id, weight_milli, enabled) "
                "VALUES (1, 4, 500, 1)",
            ),
            "weights",
            "weights are ambiguous",
        ),
    ),
)
def test_development_model_rejects_ambiguous_or_cross_ruleset_facts(
    tmp_path: Path,
    statements: tuple[str, ...],
    read: str,
    message: str,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(path, *statements)
    repository = _repository(path)

    with pytest.raises(CardBattlerModelInvalid, match=message):
        if read == "ladder":
            repository.development_ladder()
        else:
            repository.development_action_weights()


def test_development_model_rejects_unresolvable_references_and_policies(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)
    missing_ruleset = CardBattlerRulesetRef(
        key="absent",
        version=99,
        name="ignored",
        status="ignored",
        description="ignored",
        semantic_vocabulary_key="ignored",
        semantic_vocabulary_version=0,
    )

    with pytest.raises(
        CardBattlerModelInvalid, match="cannot resolve ruleset"
    ):
        repository.development_policy(missing_ruleset)
    with pytest.raises(CardBattlerModelInvalid, match="requires a policy key"):
        repository.development_policy(version=2)
    with pytest.raises(CardBattlerModelInvalid, match="requires a policy key"):
        repository.development_ladder(balance_policy_version=2)
    with pytest.raises(CardBattlerModelInvalid, match="cannot resolve"):
        repository.development_policy(key="absent")
