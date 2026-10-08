"""SQLite adapter for visible Analytics coverage counts."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application.analytics_coverage import AnalyticsCoverageFacts
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


class SqliteAnalyticsCoverageRepository:
    """Count canonical facts without maintaining a writable projection."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def load(self) -> AnalyticsCoverageFacts:
        """Return counts for visible, non-deleted images."""
        visibility = content_visibility_predicate()
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                f"""
                SELECT
                    COUNT(DISTINCT image.id) AS active_images,
                    COUNT(DISTINCT CASE WHEN review.image_id IS NOT NULL
                        THEN image.id END) AS rated_images,
                    COUNT(DISTINCT CASE
                        WHEN current_catalog.composition_id IS NOT NULL
                        THEN image.id END) AS prompt_linked_images,
                    COUNT(DISTINCT CASE
                        WHEN generation.source LIKE 'legacy%'
                        THEN image.id END) AS legacy_images,
                    COUNT(DISTINCT geometry.image_id) AS geometry_images
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                LEFT JOIN image_reviews AS review
                  ON review.image_id = image.id
                LEFT JOIN current_image_catalog_compositions AS current_catalog
                  ON current_catalog.image_id = image.id
                LEFT JOIN image_geometry_projection AS geometry
                  ON geometry.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND {visibility}
                """
            ).fetchone()
            geometry_rows = connection.execute(
                f"""
                SELECT 'aspect_format' AS dimension,
                       geometry.aspect_format AS value,
                       COUNT(DISTINCT image.id) AS image_count
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                JOIN image_geometry_projection AS geometry
                  ON geometry.image_id = image.id
                WHERE image.deleted_at IS NULL AND {visibility}
                GROUP BY geometry.aspect_format
                UNION ALL
                SELECT 'resolution_class' AS dimension,
                       geometry.resolution_class AS value,
                       COUNT(DISTINCT image.id) AS image_count
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                JOIN image_geometry_projection AS geometry
                  ON geometry.image_id = image.id
                WHERE image.deleted_at IS NULL AND {visibility}
                GROUP BY geometry.resolution_class
                ORDER BY dimension, value
                """
            ).fetchall()
        finally:
            connection.close()
        if row is None:
            return AnalyticsCoverageFacts(0, 0, 0, 0, 0)
        return AnalyticsCoverageFacts(
            active_image_count=int(row["active_images"] or 0),
            rated_image_count=int(row["rated_images"] or 0),
            prompt_linked_image_count=int(row["prompt_linked_images"] or 0),
            legacy_image_count=int(row["legacy_images"] or 0),
            geometry_projected_count=int(row["geometry_images"] or 0),
            geometry_value_counts=tuple(
                (
                    str(item["dimension"]),
                    str(item["value"]),
                    int(item["image_count"] or 0),
                )
                for item in geometry_rows
            ),
        )
