"""SQLite repository for canonical analytics page reports."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from comfyreview.application.analytics import (
    AnalyticsImage,
    CompositionStatistic,
    ScopeStatistic,
)
from comfyreview.application.image_queries import ScopeKind
from comfyreview.application.pagination import CollectionPage
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
        kind: ScopeKind | None = None,
        offset: int = 0,
        limit: int,
    ) -> CollectionPage[ScopeStatistic]:
        """Aggregate live image evidence by canonical prompt component."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            filters: tuple[object, ...] = (
                *((model,) if model else ()),
                *((kind.value,) if kind is not None else ()),
                min_n,
            )
            total = int(
                connection.execute(
                    _scope_statistics_count_statement(
                        bool(model), kind is not None
                    ),
                    filters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                _scope_statistics_statement(bool(model), kind is not None),
                (*filters, limit, offset),
            ).fetchall()
            examples = _scope_example_images(
                connection,
                tuple(int(row["component_id"]) for row in rows),
                model,
            )
            entries = tuple(
                ScopeStatistic(
                    kind=ScopeKind(str(row["kind"])),
                    component_uid=str(row["component_uid"]),
                    name=str(row["name"]),
                    archived=row["archived_at"] is not None,
                    image_count=int(row["image_count"]),
                    rating_count=int(row["rating_count"]),
                    average_rating=_optional_float(row["average_rating"]),
                    best_images=examples.get(int(row["component_id"]), ()),
                )
                for row in rows
            )
            return CollectionPage(entries, total, offset, limit)
        finally:
            connection.close()

    def composition_statistics(
        self,
        *,
        model: str,
        min_n: int,
        offset: int = 0,
        limit: int,
    ) -> CollectionPage[CompositionStatistic]:
        """Aggregate live image evidence by canonical composition."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            filters: tuple[object, ...] = (
                *((model,) if model else ()),
                min_n,
            )
            total = int(
                connection.execute(
                    _composition_statistics_count_statement(bool(model)),
                    filters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                _composition_statistics_statement(bool(model)),
                (*filters, limit, offset),
            ).fetchall()
            composition_ids = tuple(int(row["composition_id"]) for row in rows)
            names = _composition_component_names(connection, composition_ids)
            examples = _composition_example_images(
                connection,
                composition_ids,
                model,
            )
            entries = tuple(
                CompositionStatistic(
                    composition_uid=str(row["composition_uid"]),
                    component_names=names.get(int(row["composition_id"]), ()),
                    image_count=int(row["image_count"]),
                    rating_count=int(row["rating_count"]),
                    average_rating=_optional_float(row["average_rating"]),
                    best_images=examples.get(int(row["composition_id"]), ()),
                )
                for row in rows
            )
            return CollectionPage(entries, total, offset, limit)
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


def _scope_statistics_base(filter_model: bool, filter_kind: bool) -> str:
    model_filter = "AND generation.model_branch = ?" if filter_model else ""
    kind_filter = "WHERE component.kind = ?" if filter_kind else ""
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
            component.id AS component_id,
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
        {kind_filter}
        GROUP BY component.id
        HAVING SUM(component_images.rating_count) >= ?
    """


def _scope_statistics_statement(filter_model: bool, filter_kind: bool) -> str:
    return (
        _scope_statistics_base(filter_model, filter_kind)
        + """
        ORDER BY
            average_rating IS NULL,
            average_rating DESC,
            rating_count DESC,
            component.kind,
            component.name COLLATE NOCASE,
            component.component_uid
        LIMIT ? OFFSET ?
    """
    )


def _scope_statistics_count_statement(
    filter_model: bool, filter_kind: bool
) -> str:
    return (
        "SELECT COUNT(*) FROM ("
        + _scope_statistics_base(filter_model, filter_kind)
        + ") AS scoped"
    )


def _composition_statistics_base(filter_model: bool) -> str:
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
    """


def _composition_statistics_statement(filter_model: bool) -> str:
    return (
        _composition_statistics_base(filter_model)
        + """
        ORDER BY
            average_rating IS NULL,
            average_rating DESC,
            rating_count DESC,
            composition_uid
        LIMIT ? OFFSET ?
    """
    )


def _composition_statistics_count_statement(filter_model: bool) -> str:
    return (
        "SELECT COUNT(*) FROM ("
        + _composition_statistics_base(filter_model)
        + ") AS scoped"
    )


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


def _scope_example_images(
    connection: sqlite3.Connection,
    component_ids: tuple[int, ...],
    model: str,
) -> dict[int, tuple[AnalyticsImage, ...]]:
    """Return up to three highest-rated live images per component."""
    if not component_ids:
        return {}
    placeholders = ", ".join("?" for _id in component_ids)
    model_filter = "AND generation.model_branch = ?" if model else ""
    arguments: tuple[object, ...] = (
        *component_ids,
        *((model,) if model else ()),
    )
    rows = connection.execute(
        f"""
        WITH ranked AS (
            SELECT DISTINCT
                component.id AS group_id,
                image.image_uid,
                image.png_path,
                image.json_path,
                summary.average_rating,
                summary.rating_count,
                ROW_NUMBER() OVER (
                    PARTITION BY component.id
                    ORDER BY
                        summary.average_rating IS NULL,
                        summary.average_rating DESC,
                        summary.rating_count DESC,
                        image.image_uid
                ) AS example_rank
            FROM prompt_components AS component
            JOIN prompt_revisions AS revision
                ON revision.component_id = component.id
            JOIN prompt_composition_revisions AS membership
                ON membership.revision_id = revision.id
            JOIN generations AS generation
                ON generation.prompt_composition_id = membership.composition_id
            JOIN images AS image ON image.generation_id = generation.id
            JOIN image_review_summary AS summary ON summary.image_id = image.id
            WHERE component.id IN ({placeholders})
              AND image.deleted_at IS NULL
              {model_filter}
        )
        SELECT * FROM ranked
        WHERE example_rank <= 3
        ORDER BY group_id, example_rank
        """,
        arguments,
    ).fetchall()
    return _group_example_images(rows)


def _composition_example_images(
    connection: sqlite3.Connection,
    composition_ids: tuple[int, ...],
    model: str,
) -> dict[int, tuple[AnalyticsImage, ...]]:
    """Return up to three highest-rated live images per composition."""
    if not composition_ids:
        return {}
    placeholders = ", ".join("?" for _id in composition_ids)
    model_filter = "AND generation.model_branch = ?" if model else ""
    arguments: tuple[object, ...] = (
        *composition_ids,
        *((model,) if model else ()),
    )
    rows = connection.execute(
        f"""
        WITH ranked AS (
            SELECT
                composition.id AS group_id,
                image.image_uid,
                image.png_path,
                image.json_path,
                summary.average_rating,
                summary.rating_count,
                ROW_NUMBER() OVER (
                    PARTITION BY composition.id
                    ORDER BY
                        summary.average_rating IS NULL,
                        summary.average_rating DESC,
                        summary.rating_count DESC,
                        image.image_uid
                ) AS example_rank
            FROM prompt_compositions AS composition
            JOIN generations AS generation
                ON generation.prompt_composition_id = composition.id
            JOIN images AS image ON image.generation_id = generation.id
            JOIN image_review_summary AS summary ON summary.image_id = image.id
            WHERE composition.id IN ({placeholders})
              AND image.deleted_at IS NULL
              {model_filter}
        )
        SELECT * FROM ranked
        WHERE example_rank <= 3
        ORDER BY group_id, example_rank
        """,
        arguments,
    ).fetchall()
    return _group_example_images(rows)


def _group_example_images(
    rows: list[sqlite3.Row],
) -> dict[int, tuple[AnalyticsImage, ...]]:
    grouped: dict[int, list[AnalyticsImage]] = {}
    for row in rows:
        json_path = str(row["json_path"] or "").strip()
        grouped.setdefault(int(row["group_id"]), []).append(
            AnalyticsImage(
                png_path=Path(str(row["png_path"])),
                json_path=Path(json_path) if json_path else None,
                average_rating=_optional_float(row["average_rating"]),
                rating_count=int(row["rating_count"]),
                image_uid=str(row["image_uid"]),
            )
        )
    return {key: tuple(images) for key, images in grouped.items()}


def _optional_float(value: object) -> float | None:
    return float(str(value)) if value is not None else None
