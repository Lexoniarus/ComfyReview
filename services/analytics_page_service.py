"""HTTP-facing view composition for canonical analytics pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
    ObservedPromptCombination,
)
from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
)
from services.context_filters import normalize_model

ImageUrlResolver = Callable[[str], str]


class AnalyticsPageService:
    """Build analytics template models from canonical repositories."""

    def __init__(
        self,
        *,
        analytics: AnalyticsService,
        reports: AnalyticsReportService,
        image_url: ImageUrlResolver,
    ) -> None:
        self._analytics = analytics
        self._reports = reports
        self._image_url = image_url

    def composition_context(
        self,
        *,
        model: str = "",
        min_n: int = 8,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Build canonical composition statistics for the V2 surface."""
        normalized_model = normalize_model(model)
        rows = self._reports.composition_statistics(
            model=normalized_model,
            minimum_samples=int(min_n),
            limit=int(limit),
        )
        return {
            "rows": [
                {
                    "composition_uid": item.composition_uid,
                    "component_names": list(item.component_names),
                    "image_count": item.image_count,
                    "rating_count": item.rating_count,
                    "average_rating": item.average_rating,
                    "best_images": self._image_views(item.best_images),
                }
                for item in rows
            ],
            "model": normalized_model,
            "min_n": min_n,
            "limit": limit,
            "model_list": self._models(),
        }

    def playground_combinations_context(
        self,
        *,
        limit: int = 8,
    ) -> dict[str, Any]:
        """Build top canonical two- and three-component examples."""
        return {
            "two_component": self._combination_views(
                self._analytics.observed_combinations(
                    combo_size=2,
                    limit=int(limit),
                )
            ),
            "three_component": self._combination_views(
                self._analytics.observed_combinations(
                    combo_size=3,
                    limit=int(limit),
                )
            ),
        }

    def scope_context(
        self,
        *,
        model: str = "",
        min_n: int = 8,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Build canonical component statistics for the V2 surface."""
        normalized_model = normalize_model(model)
        rows = self._reports.scope_statistics(
            model=normalized_model,
            minimum_samples=int(min_n),
            limit=int(limit),
        )
        return {
            "rows": [
                {
                    "kind": item.kind.value,
                    "component_uid": item.component_uid,
                    "name": item.name,
                    "archived": item.archived,
                    "image_count": item.image_count,
                    "rating_count": item.rating_count,
                    "average_rating": item.average_rating,
                    "best_images": self._image_views(item.best_images),
                }
                for item in rows
            ],
            "model": normalized_model,
            "min_n": min_n,
            "limit": limit,
            "model_list": self._models(),
        }

    def recommendations_context(
        self,
        *,
        model: str = "",
        min_n: int = 5,
        limit: int = 200,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        minimum_lower_bound: float = 0.5,
        approximate_minimum_samples: int = 8,
        approximate_limit: int = 80,
    ) -> dict[str, Any]:
        """Build recommendations from observed canonical review facts."""
        normalized_model = normalize_model(model)
        report = self._reports.recommendations(
            model=normalized_model,
            minimum_samples=int(min_n),
            limit=int(limit),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            minimum_lower_bound=float(minimum_lower_bound),
            approximate_minimum_samples=int(approximate_minimum_samples),
            approximate_limit=int(approximate_limit),
        )
        approximate = report.get("approx")
        if not isinstance(approximate, dict):
            approximate = {"base": None, "rows": [], "notes": ""}
        return {
            "stable": report.get("stable", []),
            "avoid": report.get("avoid", []),
            "approx": approximate,
            "model": normalized_model,
            "min_n": min_n,
            "limit": limit,
            "t": success_threshold,
            "dw": delete_weight,
            "min_lb": minimum_lower_bound,
            "approx_min_n": approximate_minimum_samples,
            "approx_limit": approximate_limit,
            "model_list": self._models(),
        }

    def parameter_context(
        self,
        *,
        model: str = "",
        min_n: int = 10,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
    ) -> dict[str, Any]:
        """Build render-parameter statistics and canonical image examples."""
        normalized_model = normalize_model(model)
        rows = self._reports.parameter_statistics(
            model=normalized_model,
            minimum_samples=int(min_n),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
        )
        sections = self._parameter_sections(rows, normalized_model)
        return {
            "stats": sections,
            "best": self._reports.calculated_best_cases(
                model=normalized_model,
                minimum_samples=int(min_n),
                success_threshold=int(success_threshold),
                delete_weight=int(delete_weight),
                limit=200,
            ),
            "best_tested": self._reports.combo_statistics(
                model=normalized_model,
                minimum_samples=int(min_n),
                limit=200,
                success_threshold=int(success_threshold),
                delete_weight=int(delete_weight),
            ),
            "model": normalized_model,
            "min_n": min_n,
            "t": success_threshold,
            "dw": delete_weight,
            "model_list": self._models(),
        }

    def _models(self) -> list[str]:
        return list(self._reports.list_models())

    def _parameter_sections(
        self,
        rows: list[dict[str, Any]],
        model_branch: str,
    ) -> list[dict[str, Any]]:
        titles = {
            "checkpoint": "Checkpoint",
            "steps": "Steps",
            "cfg": "CFG",
            "sampler": "Sampler",
            "scheduler": "Scheduler",
        }
        sections: list[dict[str, Any]] = []
        for parameter, title in titles.items():
            parameter_rows = [
                row for row in rows if row.get("feat") == parameter
            ]
            values = tuple(
                str(row["value"])
                for row in parameter_rows
                if row.get("value") is not None
            )
            images = self._analytics.best_images_for_parameter(
                parameter,
                values,
                model_branch=model_branch,
            )
            for row in parameter_rows:
                row["best_images"] = self._image_views(
                    images.get(str(row.get("value")), ())
                )
            sections.append(
                {"key": parameter, "title": title, "rows": parameter_rows}
            )
        return sections

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
                    "avg_rating": image.average_rating,
                    "runs": image.rating_count,
                }
            )
        return output

    def _combination_views(
        self,
        combinations: tuple[ObservedPromptCombination, ...],
    ) -> list[dict[str, object]]:
        return [
            {
                "combo_key": item.combo_key,
                "component_uids": list(item.component_uids),
                "component_names": list(item.component_names),
                "label": item.label,
                "average_rating": item.average_rating,
                "image_count": item.image_count,
                "rating_count": item.total_rating_count,
                "best_images": self._image_views(item.best_images),
            }
            for item in combinations
        ]
