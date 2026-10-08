"""Behavior tests for canonical analytics template composition."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
    CalculatedRenderRecommendation,
    CharacterCombinationGroup,
    CollectionPage,
    CompositionAnalyticsService,
    CompositionStatistic,
    ObservedPromptCombination,
    ParameterValueStatistic,
    PlaygroundCombinationSelectionPolicy,
    PromptTokenStatistic,
    RenderAnalyticsService,
    RenderAnalyticsSummary,
    RenderParameter,
    RenderSamplerStage,
    RenderSetupStatistic,
    ScopeKind,
    ScopeStatistic,
)
from services.analytics_page_service import AnalyticsPageService


class _Analytics:
    def __init__(self, image: AnalyticsImage) -> None:
        self.image = image
        self.calls: list[tuple[str, object]] = []

    def prompt_token_statistics(self, **values):
        self.calls.append(("tokens", values))
        return (PromptTokenStatistic("hero", 4, 8.5, 7.25),)

    def best_images_for_combos(self, combo_keys, **values):
        self.calls.append(("combo-images", (combo_keys, values)))
        return {key: (self.image,) for key in combo_keys}

    def best_images_for_parameter(self, parameter, values, **options):
        self.calls.append(("parameter-images", (parameter, values, options)))
        return {value: (self.image,) for value in values}

    def observed_combinations(self, *, additional_factor_count, limit):
        self.calls.append(("observed", (additional_factor_count, limit)))
        pose_id = 4 if additional_factor_count == 3 else None
        suffix = "|pose:4" if pose_id is not None else ""
        return (
            ObservedPromptCombination(
                combo_key=f"character:1|scene:2|outfit:3{suffix}",
                additional_factor_count=additional_factor_count,
                component_uids=(
                    "character-a",
                    "scene-a",
                    "outfit-a",
                    *(("pose-a",) if pose_id is not None else ()),
                ),
                component_names=(
                    "Hero",
                    "Rooftop",
                    "Red Coat",
                    *(("Standing",) if pose_id is not None else ()),
                ),
                label="Hero + Rooftop",
                average_rating=8.5,
                image_count=1,
                total_rating_count=4,
                best_images=(self.image,),
            ),
        )

    def observed_combinations_by_character(self, *, additional_factor_count):
        combinations = self.observed_combinations(
            additional_factor_count=additional_factor_count,
            limit=100,
        )
        return (
            CharacterCombinationGroup(
                "character-a",
                "Hero",
                combinations,
            ),
        )

    def latest_review_sequence(self):
        self.calls.append(("frontier", None))
        return 42


class _Reports:
    def __init__(self, image: AnalyticsImage) -> None:
        self.image = image

    def combo_statistics(self, **values):
        del values
        return [{"combo_key": "character:1|scene:2"}]

    def scope_statistics(self, **values):
        return CollectionPage(
            (
                ScopeStatistic(
                    ScopeKind.CHARACTER,
                    "character-a",
                    "Aiko",
                    False,
                    2,
                    4,
                    8.5,
                    (self.image,),
                ),
            ),
            1,
            values["offset"],
            values["limit"],
        )

    def composition_statistics(self, **values):
        return CollectionPage(
            (
                CompositionStatistic(
                    "composition-a",
                    ("Aiko", "Rooftop"),
                    2,
                    4,
                    8.5,
                    (self.image,),
                ),
            ),
            1,
            values["offset"],
            values["limit"],
        )

    def recommendations(self, **values):
        del values
        return {"stable": ["yes"], "avoid": ["no"]}

    def parameter_statistics(self, **values):
        del values
        return [
            {"feat": "steps", "value": "20"},
            {"feat": "unknown", "value": "ignored"},
        ]

    def calculated_best_cases(self, **values):
        del values
        return ["best"]

    def list_models(self):
        return ("sdxl",)


class _RenderAnalytics:
    def __init__(self, image: AnalyticsImage) -> None:
        self.setup = RenderSetupStatistic(
            "setup-a",
            "model.safetensors",
            (RenderSamplerStage("base", 20, 7.0, "euler", "normal", 1.0),),
            1,
            4,
            8.5,
            0.75,
            0.6,
            (image,),
        )

    def summary(self, **values):
        return RenderAnalyticsSummary(
            (
                CalculatedRenderRecommendation(
                    "model.safetensors",
                    "euler",
                    "normal",
                    20,
                    7.0,
                    1.0,
                    0.7,
                    0.6,
                ),
            ),
            CollectionPage(
                (self.setup,),
                1,
                values.get("offset", 0),
                values.get("limit", 24),
            ),
        )

    def parameter_values(self, parameter, **values):
        return CollectionPage(
            (
                ParameterValueStatistic(
                    RenderParameter(str(parameter)),
                    "20",
                    4,
                    8.5,
                    0.75,
                    0.6,
                    self.setup.best_images,
                ),
            ),
            1,
            values.get("offset", 0),
            values.get("limit", 24),
        )


class _CompositionAnalytics:
    def __init__(
        self, image: AnalyticsImage, setup: RenderSetupStatistic
    ) -> None:
        self.image = image
        self.setup = setup

    def prompt_combinations(self, **values):
        return CollectionPage(
            (
                CompositionStatistic(
                    "composition-a",
                    ("Aiko", "Rooftop"),
                    2,
                    4,
                    8.5,
                    (self.image,),
                ),
            ),
            1,
            values.get("offset", 0),
            values.get("limit", 24),
        )

    def render_setups(self, composition_uid, **values):
        del values
        assert composition_uid == "composition-a"
        return (self.setup,)


def _analytics(tmp_path: Path) -> tuple[_Analytics, AnalyticsImage]:
    image = AnalyticsImage(
        png_path=tmp_path / "image.png",
        json_path=None,
        average_rating=8.5,
        rating_count=4,
    )
    return _Analytics(image), image


def test_analytics_pages_build_combo_and_recommendation_contexts(
    tmp_path: Path,
) -> None:
    analytics, image = _analytics(tmp_path)
    render = _RenderAnalytics(image)
    service = AnalyticsPageService(
        analytics=cast(AnalyticsService, analytics),
        reports=cast(AnalyticsReportService, _Reports(image)),
        render_analytics=cast(RenderAnalyticsService, render),
        composition_analytics=cast(
            CompositionAnalyticsService,
            _CompositionAnalytics(image, render.setup),
        ),
        playground_combinations=PlaygroundCombinationSelectionPolicy(),
        image_url=lambda path: f"url:{Path(path).name}",
    )

    stats = service.composition_context(model=" sdxl ", min_n=2, limit=5)
    playground = service.playground_combinations_context(limit=4)
    recommendations = service.recommendations_context(model="sdxl")

    assert stats["items"] == [
        {
            "composition_uid": "composition-a",
            "component_names": ["Aiko", "Rooftop"],
            "image_count": 2,
            "rating_count": 4,
            "average_rating": 8.5,
            "best_images": [
                {
                    "image_uid": "",
                    "url": "url:image.png",
                    "avg_rating": 8.5,
                    "runs": 4,
                }
            ],
        }
    ]
    assert stats["view"] == "prompt"
    assert stats["model_list"] == ["sdxl"]
    assert playground["characters"][0]["two_additional_factors"][0] == {
        "combo_key": "character:1|scene:2|outfit:3",
        "component_uids": ["character-a", "scene-a", "outfit-a"],
        "component_names": ["Hero", "Rooftop", "Red Coat"],
        "label": "Hero + Rooftop",
        "average_rating": 8.5,
        "image_count": 1,
        "rating_count": 4,
        "factors": [],
        "best_images": [
            {
                "image_uid": "",
                "url": "url:image.png",
                "avg_rating": 8.5,
                "runs": 4,
            }
        ],
    }
    assert playground["characters"][0]["three_additional_factors"][0][
        "component_uids"
    ] == [
        "character-a",
        "scene-a",
        "outfit-a",
        "pose-a",
    ]
    assert recommendations["stable"] == ["yes"]
    assert recommendations["approx"] == {
        "base": None,
        "rows": [],
        "notes": "",
    }


def test_analytics_pages_build_parameter_and_scope_contexts(
    tmp_path: Path,
) -> None:
    analytics, image = _analytics(tmp_path)
    render = _RenderAnalytics(image)
    service = AnalyticsPageService(
        analytics=cast(AnalyticsService, analytics),
        reports=cast(AnalyticsReportService, _Reports(image)),
        render_analytics=cast(RenderAnalyticsService, render),
        composition_analytics=cast(
            CompositionAnalyticsService,
            _CompositionAnalytics(image, render.setup),
        ),
        playground_combinations=PlaygroundCombinationSelectionPolicy(),
        image_url=lambda path: "" if "missing" in path else "url:image.png",
    )

    summary = service.parameter_summary_context(model="sdxl")
    parameters = service.parameter_values_context("steps", model="sdxl")
    render_setups = service.render_setups_context(model="sdxl")
    composition_setups = service.composition_render_setups_context(
        "composition-a", model="sdxl"
    )
    scopes = service.scope_context(model="sdxl", min_n=1)

    assert parameters["parameter"] == "steps"
    assert parameters["items"][0]["best_images"][0]["url"] == "url:image.png"
    assert summary["recommendations"][0]["jointly_observed"] is False
    assert summary["items"][0]["stages"][0]["sampler"] == "euler"
    assert render_setups["items"][0]["setup_key"] == "setup-a"
    assert composition_setups["rows"] == render_setups["items"]
    assert scopes["items"] == [
        {
            "kind": "character",
            "component_uid": "character-a",
            "name": "Aiko",
            "archived": False,
            "image_count": 2,
            "rating_count": 4,
            "average_rating": 8.5,
            "best_images": [
                {
                    "image_uid": "",
                    "url": "url:image.png",
                    "avg_rating": 8.5,
                    "runs": 4,
                }
            ],
        }
    ]
