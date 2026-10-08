"""Behavior tests for deterministic Card Battler stat-profile selection."""

from __future__ import annotations

import pytest

from comfyreview.application.card_battler_materialization import (
    StatProfileAffinity,
    StatProfileAffinitySource,
    StatProfileDefinition,
    StatProfileSelector,
)
from comfyreview.application.card_battler_model import CardBattlerModelInvalid
from comfyreview.domain.card_battler import CardImprint


def _imprint() -> CardImprint:
    return CardImprint(
        world_style="world-a",
        card_class="class-a",
        combat_role="role-a",
        trait_lineage="lineage-a",
        source_image_uid="image-1",
        semantic_revision="semantic-v1",
        ruleset_key="prototype",
        ruleset_version=2,
        mapping_policy_key="mapping",
        mapping_policy_version=2,
        rng_policy_key="rng",
        rng_policy_version=2,
        rng_algorithm="sha256-counter-v1",
        explicit_seed=42,
    )


def _profiles() -> tuple[StatProfileDefinition, ...]:
    return (
        StatProfileDefinition("zeta", "Zeta", 600, 400, "Zeta profile"),
        StatProfileDefinition("alpha", "Alpha", 400, 600, "Alpha profile"),
    )


def _affinities() -> tuple[StatProfileAffinity, ...]:
    return (
        StatProfileAffinity("class", "class-a", "alpha", 900),
        StatProfileAffinity("role", "role-a", "alpha", 300),
        StatProfileAffinity("class", "class-a", "zeta", 0),
        StatProfileAffinity("role", "role-a", "zeta", 600),
        StatProfileAffinity("lineage", "lineage-a", "zeta", 901),
        StatProfileAffinity("lineage", "other-lineage", "alpha", 999),
    )


def test_stat_profile_selector_uses_three_axis_integer_mean() -> None:
    selection = StatProfileSelector().select(
        _imprint(), _profiles(), _affinities()
    )

    assert selection.profile.key == "zeta"
    assert selection.selected_score_milli == 500
    assert [
        candidate.stat_profile_key for candidate in selection.candidates
    ] == [
        "alpha",
        "zeta",
    ]
    assert (
        selection.candidates[0].class_affinity_milli,
        selection.candidates[0].role_affinity_milli,
        selection.candidates[0].lineage_affinity_milli,
        selection.candidates[0].average_affinity_milli,
    ) == (900, 300, 0, 400)
    assert selection == StatProfileSelector().select(
        _imprint(),
        tuple(reversed(_profiles())),
        tuple(reversed(_affinities())),
    )


def test_stat_profile_selector_breaks_equal_scores_by_stable_key() -> None:
    axis_values: tuple[tuple[StatProfileAffinitySource, str], ...] = (
        ("class", "class-a"),
        ("role", "role-a"),
        ("lineage", "lineage-a"),
    )
    affinities = tuple(
        StatProfileAffinity(source, source_key, profile.key, 600)
        for profile in _profiles()
        for source, source_key in axis_values
    )

    selection = StatProfileSelector().select(
        _imprint(), _profiles(), affinities
    )

    assert selection.profile.key == "alpha"
    assert selection.selected_score_milli == 600


@pytest.mark.parametrize(
    "profiles, affinities, message",
    (
        ((), (), "unique stable keys"),
        (
            (_profiles()[0], _profiles()[0]),
            (),
            "unique stable keys",
        ),
        (
            _profiles(),
            (StatProfileAffinity("class", "class-a", "missing", 1),),
            "unknown profile",
        ),
        (
            _profiles(),
            (
                StatProfileAffinity("class", "class-a", "alpha", 1),
                StatProfileAffinity("class", "class-a", "alpha", 2),
            ),
            "unique axis facts",
        ),
    ),
)
def test_stat_profile_selector_rejects_ambiguous_model_facts(
    profiles: tuple[StatProfileDefinition, ...],
    affinities: tuple[StatProfileAffinity, ...],
    message: str,
) -> None:
    with pytest.raises(CardBattlerModelInvalid, match=message):
        StatProfileSelector().select(_imprint(), profiles, affinities)
