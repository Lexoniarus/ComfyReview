"""SQLite repository for canonical analytics page reports."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from comfyreview.application.analytics import (
    CompositionStatistic,
    ScopeStatistic,
)
from comfyreview.application.image_queries import ScopeKind
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

    def scope_statistics(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
    ) -> tuple[ScopeStatistic, ...]:
        """Aggregate live image evidence by canonical prompt component."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                _scope_statistics_statement(bool(model)),
                (*((model,) if model else ()), min_n, limit),
            ).fetchall()
            return tuple(
                ScopeStatistic(
                    kind=ScopeKind(str(row["kind"])),
                    component_uid=str(row["component_uid"]),
                    name=str(row["name"]),
                    archived=row["archived_at"] is not None,
                    image_count=int(row["image_count"]),
                    rating_count=int(row["rating_count"]),
                    average_rating=_optional_float(row["average_rating"]),
                )
                for row in rows
            )
        finally:
            connection.close()

    def composition_statistics(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
    ) -> tuple[CompositionStatistic, ...]:
        """Aggregate live image evidence by canonical composition."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                _composition_statistics_statement(bool(model)),
                (*((model,) if model else ()), min_n, limit),
            ).fetchall()
            composition_ids = tuple(int(row["composition_id"]) for row in rows)
            names = _composition_component_names(connection, composition_ids)
            return tuple(
                CompositionStatistic(
                    composition_uid=str(row["composition_uid"]),
                    component_names=names.get(int(row["composition_id"]), ()),
                    image_count=int(row["image_count"]),
                    rating_count=int(row["rating_count"]),
                    average_rating=_optional_float(row["average_rating"]),
                )
                for row in rows
            )
        finally:
            connection.close()

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


def _scope_statistics_statement(filter_model: bool) -> str:
    model_filter = "AND generation.model_branch = ?" if filter_model else ""
    return f"""
        WITH component_images AS (
            SELECT DISTINCT
                component.id AS component_id,
                image.id AS image_id,
                summary.rating_count,
                summary.rating_sum
            FROM prompt_components AS component
            JOIN prompt_revisions AS revision
                ON revision.component_id = component.id
            JOIN prompt_composition_revisions AS membership
                ON membership.revision_id = revision.id
            JOIN generations AS generation
                ON generation.prompt_composition_id = membership.composition_id
            JOIN images AS image ON image.generation_id = generation.id
            JOIN image_review_summary AS summary ON summary.image_id = image.id
            WHERE image.deleted_at IS NULL
              {model_filter}
        )
        SELECT
            component.kind,
            component.component_uid,
            component.name,
            component.archived_at,
            COUNT(component_images.image_id) AS image_count,
            SUM(component_images.rating_count) AS rating_count,
            CASE WHEN SUM(component_images.rating_count) > 0
                THEN CAST(SUM(component_images.rating_sum) AS REAL)
                    / SUM(component_images.rating_count)
            END AS average_rating
        FROM prompt_components AS component
        JOIN component_images ON component_images.component_id = component.id
        GROUP BY component.id
        HAVING SUM(component_images.rating_count) >= ?
        ORDER BY
            average_rating IS NULL,
            average_rating DESC,
            rating_count DESC,
            component.kind,
            component.name COLLATE NOCASE,
            component.component_uid
        LIMIT ?
    """


def _composition_statistics_statement(filter_model: bool) -> str:
    model_filter = "AND generation.model_branch = ?" if filter_model else ""
    return f"""
        WITH composition_images AS (
            SELECT DISTINCT
                composition.id AS composition_id,
                composition.composition_uid,
                image.id AS image_id,
                summary.rating_count,
                summary.rating_sum
            FROM prompt_compositions AS composition
            JOIN generations AS generation
                ON generation.prompt_composition_id = composition.id
            JOIN images AS image ON image.generation_id = generation.id
            JOIN image_review_summary AS summary ON summary.image_id = image.id
            WHERE image.deleted_at IS NULL
              {model_filter}
        )
        SELECT
            composition_id,
            composition_uid,
            COUNT(image_id) AS image_count,
            SUM(rating_count) AS rating_count,
            CASE WHEN SUM(rating_count) > 0
                THEN CAST(SUM(rating_sum) AS REAL) / SUM(rating_count)
            END AS average_rating
        FROM composition_images
        GROUP BY composition_id, composition_uid
        HAVING SUM(rating_count) >= ?
        ORDER BY
            average_rating IS NULL,
            average_rating DESC,
            rating_count DESC,
            composition_uid
        LIMIT ?
    """


def _composition_component_names(
    connection: sqlite3.Connection,
    composition_ids: tuple[int, ...],
) -> dict[int, tuple[str, ...]]:
    if not composition_ids:
        return {}
    placeholders = ", ".join("?" for _id in composition_ids)
    rows = connection.execute(
        f"""
        SELECT
            membership.composition_id,
            component.name
        FROM prompt_composition_revisions AS membership
        JOIN prompt_revisions AS revision ON revision.id = membership.revision_id
        JOIN prompt_components AS component ON component.id = revision.component_id
        WHERE membership.composition_id IN ({placeholders})
        ORDER BY membership.composition_id, membership.position, membership.slot
        """,
        composition_ids,
    ).fetchall()
    grouped: dict[int, list[str]] = {}
    for row in rows:
        grouped.setdefault(int(row["composition_id"]), []).append(
            str(row["name"])
        )
    return {key: tuple(values) for key, values in grouped.items()}


def _optional_float(value: object) -> float | None:
    return float(str(value)) if value is not None else None
