"""Behavior tests for Card Battler visual model reads."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application.card_battler_model import (
    CardBattlerModelInvalid,
    CardBattlerRulesetRef,
)
from comfyreview.application.card_battler_visual_model import (
    PromptGroupDefinition,
    VisualProgressionProfile,
    VisualProjectionPolicy,
)
from comfyreview.repositories.sqlite.card_battler_model_resource import (
    CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS,
    SqliteCardBattlerModelResource,
)
from comfyreview.repositories.sqlite.card_battler_visual_model import (
    SqliteCardVisualModelRepository,
)
from tests.test_card_battler_model import _create_model_database


def _repository(path: Path) -> SqliteCardVisualModelRepository:
    return SqliteCardVisualModelRepository(
        SqliteCardBattlerModelResource(
            path, CARD_BATTLER_MODEL_SCHEMA_REQUIREMENTS
        )
    )


def _execute(
    path: Path, statement: str, parameters: tuple[object, ...] = ()
) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(statement, parameters)
        connection.commit()
    finally:
        connection.close()


def test_visual_model_reads_policy_progression_and_groups(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    repository = _repository(path)

    policy = repository.projection_policy()
    explicit = repository.projection_policy(
        key="weighted_atom_projection", version=3
    )
    profiles = repository.progression_profiles()
    groups = repository.prompt_groups()
    ruleset = CardBattlerRulesetRef(
        "prototype", 2, "Prototype", "active", "", "visual", 1
    )
    assert repository.progression_profiles(ruleset) == profiles

    assert (
        policy
        == explicit
        == VisualProjectionPolicy(
            key="weighted_atom_projection",
            version=3,
            apply_intensity_channels=True,
            origin_semantics_are_upstream_inputs=True,
            render_syntax="{atom:weight}",
            respect_exclusion_groups=True,
            respect_forbidden_bindings=True,
            stable_order=(
                "priority_asc",
                "source_type_asc",
                "atom_key_asc",
            ),
            weight_decimals=2,
            weight_scale=1000,
        )
    )
    assert profiles == (
        VisualProgressionProfile(1, 150, 120, 80, 60, 40, 950),
        VisualProgressionProfile(2, 300, 250, 200, 150, 100, 900),
    )
    assert groups == (
        PromptGroupDefinition("armor", "Armor", 0, 1, "Armor profile"),
        PromptGroupDefinition("weapon", "Weapon", 0, 1, "Primary weapon"),
    )


@pytest.mark.parametrize(
    ("statement", "message"),
    (
        (
            "DROP TABLE prompt_projection_policies",
            "prompt_projection_policies",
        ),
        (
            "ALTER TABLE visual_progression_profiles "
            "RENAME COLUMN world_intensity_milli TO missing_world",
            "world_intensity_milli",
        ),
        ("DROP TABLE prompt_groups", "prompt_groups"),
    ),
)
def test_visual_model_schema_contract_rejects_missing_tables_or_columns(
    tmp_path: Path, statement: str, message: str
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(path, statement)

    with pytest.raises(CardBattlerModelInvalid, match=message):
        _repository(path).projection_policy()


@pytest.mark.parametrize(
    "config",
    (
        "[]",
        "{}",
        '{"apply_intensity_channels":1}',
        '{"apply_intensity_channels":true,'
        '"origin_semantics_are_upstream_inputs":true,'
        '"render_syntax":"{atom:weight}",'
        '"respect_exclusion_groups":1,'
        '"respect_forbidden_bindings":true,'
        '"stable_order":["priority_asc","source_type_asc",'
        '"atom_key_asc"],"weight_decimals":2,"weight_scale":1000}',
        '{"apply_intensity_channels":true,'
        '"origin_semantics_are_upstream_inputs":true,'
        '"render_syntax":1,"respect_exclusion_groups":true,'
        '"respect_forbidden_bindings":true,'
        '"stable_order":["priority_asc","source_type_asc",'
        '"atom_key_asc"],"weight_decimals":2,"weight_scale":1000}',
        '{"apply_intensity_channels":true,'
        '"origin_semantics_are_upstream_inputs":true,'
        '"render_syntax":"","respect_exclusion_groups":true,'
        '"respect_forbidden_bindings":true,'
        '"stable_order":["priority_asc"],"weight_decimals":2,'
        '"weight_scale":1000}',
        '{"apply_intensity_channels":true,'
        '"origin_semantics_are_upstream_inputs":true,'
        '"render_syntax":"{atom:weight}",'
        '"respect_exclusion_groups":true,'
        '"respect_forbidden_bindings":true,'
        '"stable_order":[1],"weight_decimals":2,"weight_scale":1000}',
        '{"apply_intensity_channels":true,'
        '"origin_semantics_are_upstream_inputs":true,'
        '"render_syntax":"{atom:weight}",'
        '"respect_exclusion_groups":true,'
        '"respect_forbidden_bindings":true,'
        '"stable_order":["priority_asc","source_type_asc",'
        '"atom_key_asc"],"weight_decimals":true,"weight_scale":1000}',
    ),
)
def test_visual_model_rejects_invalid_projection_config(
    tmp_path: Path, config: str
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(
        path,
        "UPDATE prompt_projection_policies SET config_json = ?",
        (config,),
    )

    with pytest.raises((CardBattlerModelInvalid, ValueError)):
        _repository(path).projection_policy()


def test_visual_model_rejects_ambiguous_or_missing_policy(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(
        path,
        "INSERT INTO prompt_projection_policies VALUES "
        "(2, 1, 'second', 1, '{}', 1)",
    )
    with pytest.raises(CardBattlerModelInvalid, match="uniquely"):
        _repository(path).projection_policy()
    with pytest.raises(CardBattlerModelInvalid, match="uniquely"):
        _repository(path).projection_policy(key="missing")


def test_visual_model_rejects_invalid_progression_and_groups(
    tmp_path: Path,
) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)
    _execute(
        path,
        "UPDATE visual_progression_profiles SET world_intensity_milli = 2001",
    )
    with pytest.raises(
        (CardBattlerModelInvalid, ValueError), match="intensity"
    ):
        _repository(path).progression_profiles()

    path = tmp_path / "typed-progression.sqlite3"
    _create_model_database(path)
    _execute(
        path,
        "UPDATE visual_progression_profiles SET world_intensity_milli = 'bad'",
    )
    with pytest.raises(
        (CardBattlerModelInvalid, ValueError), match="intensity"
    ):
        _repository(path).progression_profiles()

    path = tmp_path / "empty-progression.sqlite3"
    _create_model_database(path)
    _execute(path, "DELETE FROM visual_progression_profiles")
    with pytest.raises(CardBattlerModelInvalid, match="one profile"):
        _repository(path).progression_profiles()

    path = tmp_path / "groups.sqlite3"
    _create_model_database(path)
    _execute(path, "UPDATE prompt_groups SET max_selected = -1")
    with pytest.raises(CardBattlerModelInvalid, match="groups"):
        _repository(path).prompt_groups()


def test_visual_model_rejects_unknown_explicit_ruleset(tmp_path: Path) -> None:
    path = tmp_path / "model.sqlite3"
    _create_model_database(path)

    with pytest.raises(CardBattlerModelInvalid, match="cannot resolve"):
        _repository(path).progression_profiles(
            CardBattlerRulesetRef(
                "missing", 9, "Missing", "draft", "", "visual", 1
            )
        )
