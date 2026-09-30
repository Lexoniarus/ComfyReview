"""HTTP-facing view composition for canonical analytics pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
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

    def stats_context(
        self,
        *,
        model: str = "",
        min_n: int = 8,
        limit: int = 200,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: float = DELETE_WEIGHT_DEFAULT,
    ) -> dict[str, Any]:
        """Build the observed combo-statistics page model."""
        normalized_model = normalize_model(model)
        rows = self._reports.combo_statistics(
            model=normalized_model,
            minimum_samples=int(min_n),
            limit=int(limit),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
        )
        self._attach_combo_images(rows, normalized_model)
        return {
            "rows": rows,
            "model": normalized_model,
            "min_n": min_n,
            "limit": limit,
            "t": success_threshold,
            "dw": delete_weight,
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

    def prompt_tokens_context(
        self,
        *,
        model: str = "",
        scope: str = "pos",
        min_n: int = 8,
        limit: int = 200,
    ) -> dict[str, Any]:
        """Build prompt-token statistics directly from the canonical view."""
        normalized_model = normalize_model(model)
        statistics = self._analytics.prompt_token_statistics(
            model_branch=normalized_model,
            scope=scope,
            minimum_samples=min_n,
            limit=limit,
        )
        return {
            "rows": [
                {
                    "token": item.token,
                    "n": item.sample_count,
                    "mean_score": item.mean_score,
                    "lb05": item.lower_bound,
                }
                for item in statistics
            ],
            "model": normalized_model,
            "scope": scope if scope in {"pos", "neg"} else "pos",
            "min_n": min_n,
            "limit": limit,
            "model_list": self._models(),
        }

    def _models(self) -> list[str]:
        return list(self._reports.list_models())

    def _attach_combo_images(
        self,
        rows: list[dict[str, Any]],
        model_branch: str,
    ) -> None:
        combo_keys = tuple(
            str(row.get("combo_key") or "")
            for row in rows
            if row.get("combo_key")
        )
        images = self._analytics.best_images_for_combos(
            combo_keys,
            model_branch=model_branch,
        )
        for row in rows:
            row["best_images"] = self._image_views(
                images.get(str(row.get("combo_key") or ""), ())
            )

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
