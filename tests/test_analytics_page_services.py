"""Behavior tests for canonical analytics template composition."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsService,
    ObservedPromptCombination,
    PromptTokenStatistic,
)
from services.analytics_page_service import AnalyticsPageService
from services.playground_hub_service import PlaygroundHubService


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
    monkeypatch,
) -> None:
    analytics, _ = _analytics(tmp_path)
    combo_row = {"combo_key": "character:1|scene:2"}
    monkeypatch.setattr(
        "services.analytics_page_service.fetch_combo_stats",
        lambda *args, **kwargs: [combo_row],
    )
    monkeypatch.setattr(
        "services.analytics_page_service.fetch_recommendations",
        lambda *args, **kwargs: {"stable": ["yes"], "avoid": ["no"]},
    )
    monkeypatch.setattr(
        "services.analytics_page_service.list_models_from_db",
        lambda path: ["sdxl"],
    )
    service = AnalyticsPageService(
        database_path=tmp_path / "canonical.sqlite3",
        analytics=cast(AnalyticsService, analytics),
        image_url=lambda path: f"url:{Path(path).name}",
    )

    stats = service.stats_context(model=" sdxl ", min_n=2, limit=5)
    recommendations = service.recommendations_context(model="sdxl")

    assert stats["rows"][0]["best_images"] == [
        {"url": "url:image.png", "avg_rating": 8.5, "runs": 4}
    ]
    assert stats["model_list"] == ["sdxl"]
    assert recommendations["stable"] == ["yes"]
    assert recommendations["approx"] == {
        "base": None,
        "rows": [],
        "notes": "",
    }


def test_analytics_pages_build_parameter_and_token_contexts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    analytics, _ = _analytics(tmp_path)
    monkeypatch.setattr(
        "services.analytics_page_service.fetch_param_stats",
        lambda *args, **kwargs: [
            {"feat": "steps", "value": "20"},
            {"feat": "unknown", "value": "ignored"},
        ],
    )
    monkeypatch.setattr(
        "services.analytics_page_service.fetch_calculated_best_cases",
        lambda *args, **kwargs: ["best"],
    )
    monkeypatch.setattr(
        "services.analytics_page_service.fetch_combo_stats",
        lambda *args, **kwargs: ["tested"],
    )
    monkeypatch.setattr(
        "services.analytics_page_service.list_models_from_db",
        lambda path: [],
    )
    service = AnalyticsPageService(
        database_path=tmp_path / "canonical.sqlite3",
        analytics=cast(AnalyticsService, analytics),
        image_url=lambda path: "" if "missing" in path else "url:image.png",
    )

    parameters = service.parameter_context(model="sdxl")
    tokens = service.prompt_tokens_context(scope="invalid", min_n=1)

    steps = next(
        section for section in parameters["stats"] if section["key"] == "steps"
    )
    assert steps["rows"][0]["best_images"][0]["url"] == "url:image.png"
    assert parameters["best"] == ["best"]
    assert parameters["best_tested"] == ["tested"]
    assert tokens["scope"] == "pos"
    assert tokens["rows"] == [
        {"token": "hero", "n": 4, "mean_score": 8.5, "lb05": 7.25}
    ]


def test_playground_hub_uses_observed_canonical_combinations(
    tmp_path: Path,
) -> None:
    analytics, _ = _analytics(tmp_path)
    service = PlaygroundHubService(
        analytics=cast(AnalyticsService, analytics),
        image_url=lambda path: f"url:{Path(path).name}",
        default_max_attempts=7,
    )

    context = service.build_context()

    assert context["default_max_tries"] == 7
    assert context["max_rating_id"] == 42
    assert context["mv_status"] == []
    assert context["top2"][0]["outfit_id"] is None
    assert context["top3"][0]["outfit_id"] == 3
    assert context["top2"][0]["best_images"] == [
        {
            "url": "url:image.png",
            "png_path": str(tmp_path / "image.png"),
            "json_path": "",
            "avg_rating": 8.5,
            "runs": 4,
        }
    ]


def test_playground_hub_drops_images_without_public_url(
    tmp_path: Path,
) -> None:
    analytics, _ = _analytics(tmp_path)
    service = PlaygroundHubService(
        analytics=cast(AnalyticsService, analytics),
        image_url=lambda path: "",
        default_max_attempts=1,
    )

    assert service.build_context()["top2"][0]["best_images"] == []
