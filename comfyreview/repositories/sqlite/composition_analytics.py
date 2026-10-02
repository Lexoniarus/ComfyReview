"""Canonical SQLite adapter for prompt-composition analytics."""

from pathlib import Path

from comfyreview.application.analytics import CompositionStatistic
from comfyreview.application.render_analytics import RenderSetupStatistic
from comfyreview.repositories.sqlite.analytics_reports import (
    SqliteAnalyticsReportRepository,
)
from comfyreview.repositories.sqlite.render_analytics import (
    SqliteRenderSetupQuery,
)


class SqliteCompositionAnalyticsRepository:
    """Read canonical prompt compositions and their render setups."""

    def __init__(self, database_path: Path) -> None:
        self._reports = SqliteAnalyticsReportRepository(database_path)
        self._setups = SqliteRenderSetupQuery(database_path)

    def list_prompt_combinations(
        self,
        *,
        model: str,
        minimum_samples: int,
        limit: int,
    ) -> tuple[CompositionStatistic, ...]:
        """Return canonical prompt compositions with evidence."""
        return self._reports.composition_statistics(
            model=model,
            min_n=minimum_samples,
            limit=limit,
        )

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
        """Return observed setups for one prompt composition."""
        return self._setups.list_setups(
            model=model,
            composition_uid=composition_uid,
            minimum_samples=minimum_samples,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            limit=limit,
        )
