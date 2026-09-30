"""Canonical Playground dashboard view composition."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsService,
    ObservedPromptCombination,
)

ImageUrlResolver = Callable[[str], str]


class PlaygroundHubService:
    """Build the Playground dashboard without legacy materialized views."""

    def __init__(
        self,
        *,
        analytics: AnalyticsService,
        image_url: ImageUrlResolver,
        default_max_attempts: int,
    ) -> None:
        self._analytics = analytics
        self._image_url = image_url
        self._default_max_attempts = int(default_max_attempts)

    def build_context(self) -> dict[str, Any]:
        """Return observed two- and three-component combinations."""
        return {
            "top2": [
                self._combination_view(item)
                for item in self._analytics.observed_combinations(
                    combo_size=2,
                    limit=8,
                )
            ],
            "top3": [
                self._combination_view(item)
                for item in self._analytics.observed_combinations(
                    combo_size=3,
                    limit=8,
                )
            ],
            "default_max_tries": self._default_max_attempts,
            "max_rating_id": self._analytics.latest_review_sequence(),
            "mv_status": [],
        }

    def _combination_view(
        self,
        item: ObservedPromptCombination,
    ) -> dict[str, Any]:
        return {
            "combo_key": item.combo_key,
            "combo_size": item.combo_size,
            "character_id": item.character_id,
            "scene_id": item.scene_id,
            "outfit_id": item.outfit_id,
            "label": item.label,
            "combo_pos_avg_rating": item.average_rating,
            "combo_pos_runs": item.total_rating_count,
            "combo_pos_coverage": 1.0 if item.total_rating_count else 0.0,
            "combo_neg_avg_rating": None,
            "combo_neg_runs": 0,
            "combo_image_count": item.image_count,
            "combo_total_runs": item.total_rating_count,
            "best_images": self._image_views(item.best_images),
        }

    def _image_views(
        self,
        images: tuple[AnalyticsImage, ...],
    ) -> list[dict[str, object]]:
        output: list[dict[str, object]] = []
        for image in images:
            url = self._image_url(str(image.png_path))
            if not url:
                continue
            output.append(
                {
                    "url": url,
                    "png_path": str(image.png_path),
                    "json_path": str(image.json_path or ""),
                    "avg_rating": image.average_rating,
                    "runs": image.rating_count,
                }
            )
        return output
