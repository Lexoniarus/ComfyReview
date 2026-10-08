"""Behavior tests for Playground combination cover-image diversity."""

from pathlib import Path

from comfyreview.application import (
    AnalyticsImage,
    CharacterCombinationGroup,
    ObservedPromptCombination,
    PlaygroundCombinationSelectionPolicy,
)


def test_policy_prefers_unique_covers_across_groups() -> None:
    two_groups = (
        _group(
            "character-a",
            "Aiko",
            _combination("two-a", 2, "shared", 10.0),
            _combination("two-b", 2, "two-b", 9.0),
            _combination("two-c", 2, "two-c", 8.0),
        ),
        _group(
            "character-b",
            "Hina",
            _combination("hina-two", 2, "shared", 7.0),
        ),
    )
    three_groups = (
        _group(
            "character-a",
            "Aiko",
            _combination("three-a", 3, "shared", 9.5),
            _combination("three-b", 3, "three-b", 8.5),
            _combination("three-c", 3, "three-c", 7.5),
        ),
        _group(
            "character-b",
            "Hina",
            _combination("hina-three", 3, "hina-three", 6.0),
        ),
    )

    selections = PlaygroundCombinationSelectionPolicy().select(
        two_additional_factors=two_groups,
        three_additional_factors=three_groups,
        limit_per_group=2,
    )

    assert [item.character_uid for item in selections] == [
        "character-a",
        "character-b",
    ]
    assert _keys(selections[0].two_additional_factors) == ["two-a", "two-b"]
    assert _keys(selections[0].three_additional_factors) == [
        "three-b",
        "three-c",
    ]
    aiko_images = {
        item.best_images[0].image_uid
        for group in (
            selections[0].two_additional_factors,
            selections[0].three_additional_factors,
        )
        for item in group
    }
    assert aiko_images == {"shared", "two-b", "three-b", "three-c"}
    assert _keys(selections[1].two_additional_factors) == ["hina-two"]
    assert _keys(selections[1].three_additional_factors) == ["hina-three"]


def test_playground_combination_policy_falls_back_in_rank_order() -> None:
    two_groups = (
        _group(
            "character-a",
            "Aiko",
            _combination("two-a", 2, "shared", 10.0),
            _combination("two-b", 2, "shared", 9.0),
            _combination("two-without-image", 2, None, 8.5),
        ),
    )
    three_groups = (
        _group(
            "character-a",
            "Aiko",
            _combination("three-a", 3, "shared", 8.0),
            _combination("three-b", 3, "shared", 7.0),
        ),
    )
    policy = PlaygroundCombinationSelectionPolicy()

    selection = policy.select(
        two_additional_factors=two_groups,
        three_additional_factors=three_groups,
        limit_per_group=3,
    )[0]
    empty = policy.select(
        two_additional_factors=two_groups,
        three_additional_factors=(),
        limit_per_group=-1,
    )[0]

    assert _keys(selection.two_additional_factors) == [
        "two-a",
        "two-b",
        "two-without-image",
    ]
    assert _keys(selection.three_additional_factors) == [
        "three-a",
        "three-b",
    ]
    assert empty.character_name == "Aiko"
    assert empty.two_additional_factors == ()
    assert empty.three_additional_factors == ()


def _group(
    character_uid: str,
    character_name: str,
    *combinations: ObservedPromptCombination,
) -> CharacterCombinationGroup:
    return CharacterCombinationGroup(
        character_uid=character_uid,
        character_name=character_name,
        combinations=combinations,
    )


def _combination(
    combo_key: str,
    additional_factor_count: int,
    image_uid: str | None,
    rating: float,
) -> ObservedPromptCombination:
    best_images: tuple[AnalyticsImage, ...] = ()
    if image_uid is not None:
        best_images = (
            AnalyticsImage(
                png_path=Path(f"{image_uid}.png"),
                json_path=None,
                average_rating=rating,
                rating_count=1,
                image_uid=image_uid,
            ),
        )
    return ObservedPromptCombination(
        combo_key=combo_key,
        additional_factor_count=additional_factor_count,
        component_uids=("character-a",),
        component_names=("Aiko",),
        label=combo_key,
        average_rating=rating,
        image_count=1,
        total_rating_count=1,
        best_images=best_images,
    )


def _keys(combinations: tuple[ObservedPromptCombination, ...]) -> list[str]:
    return [item.combo_key for item in combinations]
