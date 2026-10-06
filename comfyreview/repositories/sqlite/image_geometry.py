"""SQLite adapter for rebuildable image geometry projections."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application.generation_geometry import ImageGeometryProjection
from comfyreview.application.image_geometry import ImageGeometrySource
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteImageGeometryRepository:
    """Own short reads and atomic projection writes."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_sources(self) -> tuple[ImageGeometrySource, ...]:
        """Return live canonical identities and their path attributes."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                "SELECT image_uid, png_path FROM images "
                "WHERE deleted_at IS NULL ORDER BY image_uid"
            ).fetchall()
            return tuple(
                ImageGeometrySource(
                    image_uid=str(row["image_uid"]),
                    png_path=Path(str(row["png_path"])),
                )
                for row in rows
            )
        finally:
            connection.close()

    def replace_all(
        self, projections: tuple[ImageGeometryProjection, ...]
    ) -> None:
        """Replace the complete derived projection atomically."""
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute("DELETE FROM image_geometry_projection")
            connection.executemany(
                self._insert_statement(),
                tuple(self._values(item) for item in projections),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def upsert(self, projection: ImageGeometryProjection) -> None:
        """Replace one derived row after successful file capture."""
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                self._insert_statement()
                + " ON CONFLICT(image_id) DO UPDATE SET "
                "actual_width=excluded.actual_width, "
                "actual_height=excluded.actual_height, "
                "aspect_format=excluded.aspect_format, "
                "resolution_class=excluded.resolution_class, "
                "target_width=excluded.target_width, "
                "target_height=excluded.target_height, "
                "is_exact=excluded.is_exact, "
                "classifier_version=excluded.classifier_version, "
                "projected_at=datetime('now')",
                self._values(projection),
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _insert_statement() -> str:
        return """
            INSERT INTO image_geometry_projection(
                image_id, actual_width, actual_height, aspect_format,
                resolution_class, target_width, target_height, is_exact,
                classifier_version
            )
            SELECT id, ?, ?, ?, ?, ?, ?, ?, ? FROM images
            WHERE image_uid = ?
        """

    @staticmethod
    def _values(projection: ImageGeometryProjection) -> tuple[object, ...]:
        return (
            projection.actual_width,
            projection.actual_height,
            projection.aspect_format.value,
            projection.resolution_class.value,
            projection.target_width,
            projection.target_height,
            int(projection.exact),
            projection.classifier_version,
            projection.image_uid,
        )
