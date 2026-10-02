"""Application boundary for prompt-composition analytics."""

from __future__ import annotations

from typing import Protocol

from comfyreview.application.analytics import CompositionStatistic
from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
)
from comfyreview.application.render_analytics import RenderSetupStatistic


class CompositionAnalyticsRepository(Protocol):
    """Read prompt combinations and their observed render setups."""

    def list_prompt_combinations(
        self,
        *,
        model: str,
        minimum_samples: int,
        limit: int,
    ) -> tuple[CompositionStatistic, ...]:
        """Return canonical prompt compositions with review evidence."""
        ...

    def list_render_setups(
        self,
        composition_uid: str,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[RenderSetupStatistic, ...]:
        """Return observed render setups for one prompt composition."""
        ...


class CompositionAnalyticsService:
    """Validate prompt-combination analytics queries."""

    def __init__(self, repository: CompositionAnalyticsRepository) -> None:
        self._repository = repository

    def prompt_combinations(
        self,
        *,
        model: str = "",
        minimum_samples: int = 8,
        limit: int = 200,
    ) -> tuple[CompositionStatistic, ...]:
        """Return observed canonical prompt compositions."""
        return self._repository.list_prompt_combinations(
            model=str(model or "").strip(),
            minimum_samples=max(int(minimum_samples), 0),
            limit=max(int(limit), 0),
        )

    def render_setups(
        self,
        composition_uid: str,
        *,
        model: str = "",
        minimum_samples: int = 1,
        success_threshold: int = SUCCESS_THRESHOLD_DEFAULT,
        delete_weight: int = DELETE_WEIGHT_DEFAULT,
        limit: int = 20,
    ) -> tuple[RenderSetupStatistic, ...]:
        """Return observed render setups for one canonical composition."""
        normalized_uid = str(composition_uid or "").strip()
        if not normalized_uid:
            raise ValueError("composition_uid is required")
        return self._repository.list_render_setups(
            normalized_uid,
            model=str(model or "").strip(),
            minimum_samples=max(int(minimum_samples), 0),
            success_threshold=int(success_threshold),
            delete_weight=max(int(delete_weight), 0),
            limit=max(int(limit), 0),
        )
