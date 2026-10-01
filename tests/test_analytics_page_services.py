"""Behavior tests for canonical analytics template composition."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
    CompositionStatistic,
    ObservedPromptCombination,
    PromptTokenStatistic,
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

    def observed_combinations(self, *, combo_size, limit):
        self.calls.append(("observed", (combo_size, limit)))
        outfit_id = 3 if combo_size == 3 else None
        suffix = "|outfit:3" if outfit_id is not None else ""
        return (
            ObservedPromptCombination(
                combo_key=f"character:1|scene:2{suffix}",
                combo_size=combo_size,
                character_id=1,
                scene_id=2,
                outfit_id=outfit_id,
                label="Hero + Rooftop",
                average_rating=8.5,
                image_count=1,
                total_rating_count=4,
                best_images=(self.image,),
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
        del values
        return (
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
        )

    def composition_statistics(self, **values):
        del values
        return (
            CompositionStatistic(
                "composition-a",
                ("Aiko", "Rooftop"),
                2,
                4,
                8.5,
                (self.image,),
            ),
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
    service = AnalyticsPageService(
        analytics=cast(AnalyticsService, analytics),
        reports=cast(AnalyticsReportService, _Reports(image)),
        image_url=lambda path: f"url:{Path(path).name}",
    )

    stats = service.composition_context(model=" sdxl ", min_n=2, limit=5)
    recommendations = service.recommendations_context(model="sdxl")

    assert stats["rows"] == [
        {
            "composition_uid": "composition-a",
            "component_names": ["Aiko", "Rooftop"],
            "image_count": 2,
            "rating_count": 4,
            "average_rating": 8.5,
            "best_images": [
                {"url": "url:image.png", "avg_rating": 8.5, "runs": 4}
            ],
        }
    ]
    assert stats["model_list"] == ["sdxl"]
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
    service = AnalyticsPageService(
        analytics=cast(AnalyticsService, analytics),
        reports=cast(AnalyticsReportService, _Reports(image)),
        image_url=lambda path: "" if "missing" in path else "url:image.png",
    )

    parameters = service.parameter_context(model="sdxl")
    scopes = service.scope_context(model="sdxl", min_n=1)

    steps = next(
        section for section in parameters["stats"] if section["key"] == "steps"
    )
    assert steps["rows"][0]["best_images"][0]["url"] == "url:image.png"
    assert parameters["best"] == ["best"]
    assert parameters["best_tested"] == [{"combo_key": "character:1|scene:2"}]
    assert scopes["rows"] == [
        {
            "kind": "character",
            "component_uid": "character-a",
            "name": "Aiko",
            "archived": False,
            "image_count": 2,
            "rating_count": 4,
            "average_rating": 8.5,
            "best_images": [
                {"url": "url:image.png", "avg_rating": 8.5, "runs": 4}
            ],
        }
    ]
