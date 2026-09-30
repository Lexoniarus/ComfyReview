"""SQLite repository for canonical analytics page reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.page_analytics_combos import (
    fetch_combo_stats,
    fetch_recommendations,
)
from comfyreview.repositories.sqlite.page_analytics_parameters import (
    fetch_calculated_best_cases,
    fetch_param_stats,
)


class SqliteAnalyticsReportRepository:
    """Own canonical SQLite access for legacy-compatible analytics reports."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def combo_statistics(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return combination statistics from canonical review facts."""
        return fetch_combo_stats(
            self._database_path,
            model=model,
            min_n=min_n,
            limit=limit,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
        )

    def recommendations(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
        min_lb: float,
        approx_min_n: int,
        approx_limit: int,
    ) -> dict[str, Any]:
        """Return recommendation sections from canonical review facts."""
        return fetch_recommendations(
            self._database_path,
            model=model,
            min_n=min_n,
            limit=limit,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            min_lb=min_lb,
            approx_min_n=approx_min_n,
            approx_limit=approx_limit,
        )

    def parameter_statistics(
        self,
        *,
        model: str,
        min_n: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return parameter statistics from canonical review facts."""
        return fetch_param_stats(
            self._database_path,
            model=model,
            min_n=min_n,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
        )

    def calculated_best_cases(
        self,
        *,
        model: str,
        min_n: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return calculated best cases from canonical review facts."""
        return fetch_calculated_best_cases(
            self._database_path,
            model=model,
            min_n=min_n,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            limit=limit,
        )

    def list_models(self) -> tuple[str, ...]:
        """Return distinct canonical generation model branches."""
        connection = connect_read_only(self._database_path)
        try:
            rows = connection.execute(
                "SELECT DISTINCT model_branch FROM generations "
                "WHERE model_branch <> '' ORDER BY model_branch"
            ).fetchall()
            return tuple(str(row[0]) for row in rows)
        finally:
            connection.close()
