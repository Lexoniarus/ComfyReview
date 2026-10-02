"""Typed application boundary for canonical render analytics."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from comfyreview.application.analytics import AnalyticsImage
from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
)


class RenderParameter(StrEnum):
    """Identify one supported single-parameter evidence dimension."""

    CHECKPOINT = "checkpoint"
    STEPS = "steps"
    CFG = "cfg"
    SAMPLER = "sampler"
    SCHEDULER = "scheduler"


@dataclass(frozen=True, slots=True)
class RenderSamplerStage:
    """Describe one ordered sampler stage without seed identity."""

    role: str
    steps: int | None
    cfg: float | None
    sampler: str
    scheduler: str
    denoise: float | None


@dataclass(frozen=True, slots=True)
class RenderSetupStatistic:
    """Summarize evidence for one actually observed render setup."""

    setup_key: str
    checkpoint: str
    stages: tuple[RenderSamplerStage, ...]
    image_count: int
    rating_count: int
    average_rating: float | None
    expected_success_rate: float
    lower_bound: float
    best_images: tuple[AnalyticsImage, ...] = ()


@dataclass(frozen=True, slots=True)
class ParameterValueStatistic:
    """Summarize evidence for one value of one render parameter."""

    parameter: RenderParameter
    value: str
    sample_count: int
    average_rating: float | None
    expected_success_rate: float
    lower_bound: float
    best_images: tuple[AnalyticsImage, ...] = ()


@dataclass(frozen=True, slots=True)
class CalculatedRenderRecommendation:
    """Describe a marginal recommendation that was not jointly tested."""

    checkpoint: str
    sampler: str
    scheduler: str
    steps: int | None
    cfg: float | None
    denoise: float | None
    score: float
    checkpoint_lower_bound: float


@dataclass(frozen=True, slots=True)
class RenderAnalyticsSummary:
    """Keep calculated recommendations separate from observed setups."""

    recommendations: tuple[CalculatedRenderRecommendation, ...]
    observed_setups: tuple[RenderSetupStatistic, ...]


class RenderAnalyticsRepository(Protocol):
    """Read canonical render evidence without exposing SQLite."""

    def list_calculated_recommendations(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[CalculatedRenderRecommendation, ...]:
        """Return marginal per-checkpoint recommendations."""
        ...

    def list_observed_setups(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[RenderSetupStatistic, ...]:
        """Return actually observed complete render setups."""
        ...

    def list_parameter_values(
        self,
        parameter: RenderParameter,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[ParameterValueStatistic, ...]:
        """Return evidence for one selected parameter dimension."""
        ...


class RenderAnalyticsService:
    """Validate and orchestrate focused canonical render analytics."""

    def __init__(self, repository: RenderAnalyticsRepository) -> None:
        self._repository = repository

    def summary(
        self,
        *,
        model: str = "",
        minimum_samples: int = 10,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        limit: int = 50,
    ) -> RenderAnalyticsSummary:
        """Return calculated and observed render evidence separately."""
        options = self._options(
            model,
            minimum_samples,
            success_threshold,
            delete_weight,
            limit,
        )
        return RenderAnalyticsSummary(
            recommendations=self._repository.list_calculated_recommendations(
                model=options[0],
                minimum_samples=options[1],
                success_threshold=options[2],
                delete_weight=options[3],
                limit=options[4],
            ),
            observed_setups=self._repository.list_observed_setups(
                model=options[0],
                minimum_samples=options[1],
                success_threshold=options[2],
                delete_weight=options[3],
                limit=options[4],
            ),
        )

    def parameter_values(
        self,
        parameter: str | RenderParameter,
        *,
        model: str = "",
        minimum_samples: int = 10,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        limit: int = 100,
    ) -> tuple[ParameterValueStatistic, ...]:
        """Return evidence only for the requested parameter dimension."""
        try:
            normalized_parameter = RenderParameter(str(parameter).strip())
        except ValueError as error:
            raise ValueError(
                f"unsupported render parameter: {parameter}"
            ) from error
        options = self._options(
            model,
            minimum_samples,
            success_threshold,
            delete_weight,
            limit,
        )
        return self._repository.list_parameter_values(
            normalized_parameter,
            model=options[0],
            minimum_samples=options[1],
            success_threshold=options[2],
            delete_weight=options[3],
            limit=options[4],
        )

    @staticmethod
    def _options(
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[str, int, int, int, int]:
        return (
            str(model or "").strip(),
            max(int(minimum_samples), 0),
            int(success_threshold),
            max(int(delete_weight), 0),
            max(int(limit), 0),
        )
