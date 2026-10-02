"""HTTP-facing view composition for canonical analytics pages."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from comfyreview.application import (
    AnalyticsImage,
    AnalyticsReportService,
    AnalyticsService,
    CalculatedRenderRecommendation,
    CompositionAnalyticsService,
    ObservedPromptCombination,
    ParameterValueStatistic,
    RenderAnalyticsService,
    RenderParameter,
    RenderSetupStatistic,
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
        render_analytics: RenderAnalyticsService,
        composition_analytics: CompositionAnalyticsService,
        image_url: ImageUrlResolver,
    ) -> None:
        self._analytics = analytics
        self._reports = reports
        self._render_analytics = render_analytics
        self._composition_analytics = composition_analytics
        self._image_url = image_url

    def composition_context(
        self,
        *,
        model: str = "",
        min_n: int = 8,
        offset: int = 0,
        limit: int = 24,
    ) -> dict[str, Any]:
        """Build canonical composition statistics for the V2 surface."""
        normalized_model = normalize_model(model)
        page = self._composition_analytics.prompt_combinations(
            model=normalized_model,
            minimum_samples=int(min_n),
            offset=int(offset),
            limit=int(limit),
        )
        return {
            "view": "prompt",
            "items": [
                {
                    "composition_uid": item.composition_uid,
                    "component_names": list(item.component_names),
                    "image_count": item.image_count,
                    "rating_count": item.rating_count,
                    "average_rating": item.average_rating,
                    "best_images": self._image_views(item.best_images),
                }
                for item in page.entries
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "model": normalized_model,
            "min_n": min_n,
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
        kind: str = "character",
        offset: int = 0,
        limit: int = 24,
    ) -> dict[str, Any]:
        """Build canonical component statistics for the V2 surface."""
        normalized_model = normalize_model(model)
        page = self._reports.scope_statistics(
            model=normalized_model,
            minimum_samples=int(min_n),
            kind=kind,
            offset=int(offset),
            limit=int(limit),
        )
        return {
            "items": [
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
                for item in page.entries
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "kind": kind,
            "model": normalized_model,
            "min_n": min_n,
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

    def parameter_summary_context(
        self,
        *,
        model: str = "",
        min_n: int = 10,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        offset: int = 0,
        limit: int = 24,
    ) -> dict[str, Any]:
        """Build calculated recommendations and observed complete setups."""
        normalized_model = normalize_model(model)
        summary = self._render_analytics.summary(
            model=normalized_model,
            minimum_samples=int(min_n),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            offset=int(offset),
            limit=int(limit),
        )
        return {
            "view": "summary",
            "recommendations": [
                self._recommendation_view(item)
                for item in summary.recommendations
            ],
            "items": [
                self._render_setup_view(item)
                for item in summary.observed_setups.entries
            ],
            "total": summary.observed_setups.total,
            "offset": summary.observed_setups.offset,
            "limit": summary.observed_setups.limit,
            "model": normalized_model,
            "min_n": min_n,
            "t": success_threshold,
            "dw": delete_weight,
            "model_list": self._models(),
        }

    def parameter_values_context(
        self,
        parameter: str | RenderParameter,
        *,
        model: str = "",
        min_n: int = 10,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        offset: int = 0,
        limit: int = 24,
    ) -> dict[str, Any]:
        """Build one selected single-parameter evidence list."""
        normalized_model = normalize_model(model)
        page = self._render_analytics.parameter_values(
            parameter,
            model=normalized_model,
            minimum_samples=int(min_n),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            offset=int(offset),
            limit=int(limit),
        )
        normalized_parameter = RenderParameter(str(parameter))
        return {
            "view": "values",
            "parameter": normalized_parameter.value,
            "items": [
                self._parameter_value_view(item) for item in page.entries
            ],
            "total": page.total,
            "offset": page.offset,
            "limit": page.limit,
            "model": normalized_model,
            "min_n": min_n,
            "t": success_threshold,
            "dw": delete_weight,
            "model_list": self._models(),
        }

    def render_setups_context(
        self,
        *,
        model: str = "",
        min_n: int = 8,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        offset: int = 0,
        limit: int = 24,
    ) -> dict[str, Any]:
        """Build the observed render-setup combinations view."""
        normalized_model = normalize_model(model)
        summary = self._render_analytics.summary(
            model=normalized_model,
            minimum_samples=int(min_n),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            offset=int(offset),
            limit=int(limit),
        )
        return {
            "view": "render",
            "items": [
                self._render_setup_view(item)
                for item in summary.observed_setups.entries
            ],
            "total": summary.observed_setups.total,
            "offset": summary.observed_setups.offset,
            "limit": summary.observed_setups.limit,
            "model": normalized_model,
            "min_n": min_n,
            "model_list": self._models(),
        }

    def composition_render_setups_context(
        self,
        composition_uid: str,
        *,
        model: str = "",
        min_n: int = 1,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Build observed render setups for one prompt composition."""
        normalized_model = normalize_model(model)
        rows = self._composition_analytics.render_setups(
            composition_uid,
            model=normalized_model,
            minimum_samples=int(min_n),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            limit=int(limit),
        )
        return {
            "composition_uid": str(composition_uid).strip(),
            "rows": [self._render_setup_view(item) for item in rows],
        }

    def _models(self) -> list[str]:
        return list(self._reports.list_models())

    def _recommendation_view(
        self,
        item: CalculatedRenderRecommendation,
    ) -> dict[str, object]:
        return {
            "checkpoint": item.checkpoint,
            "sampler": item.sampler,
            "scheduler": item.scheduler,
            "steps": item.steps,
            "cfg": item.cfg,
            "denoise": item.denoise,
            "score": item.score,
            "checkpoint_lower_bound": item.checkpoint_lower_bound,
            "jointly_observed": False,
        }

    def _render_setup_view(
        self,
        item: RenderSetupStatistic,
    ) -> dict[str, object]:
        return {
            "setup_key": item.setup_key,
            "checkpoint": item.checkpoint,
            "stages": [
                {
                    "role": stage.role,
                    "steps": stage.steps,
                    "cfg": stage.cfg,
                    "sampler": stage.sampler,
                    "scheduler": stage.scheduler,
                    "denoise": stage.denoise,
                }
                for stage in item.stages
            ],
            "image_count": item.image_count,
            "rating_count": item.rating_count,
            "average_rating": item.average_rating,
            "expected_success_rate": item.expected_success_rate,
            "lower_bound": item.lower_bound,
            "best_images": self._image_views(item.best_images),
        }

    def _parameter_value_view(
        self,
        item: ParameterValueStatistic,
    ) -> dict[str, object]:
        return {
            "parameter": item.parameter.value,
            "value": item.value,
            "sample_count": item.sample_count,
            "average_rating": item.average_rating,
            "expected_success_rate": item.expected_success_rate,
            "lower_bound": item.lower_bound,
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
                    "image_uid": image.image_uid,
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
