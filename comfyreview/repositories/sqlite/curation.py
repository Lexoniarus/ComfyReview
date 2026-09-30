"""SQLite adapter for canonical curation state."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application.curation import (
    CurationAssignment,
    CurationImage,
    CurationResult,
    CurationValidationError,
)
from comfyreview.application.reviews import OutputPairNotFoundError
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCurationRepository:
    """Read and atomically update canonical curation state."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_live_image(self, image_uid: str) -> CurationImage:
        """Return current paths for one live canonical image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                """
                SELECT image_uid, png_path, json_path
                FROM images
                WHERE image_uid = ? AND deleted_at IS NULL
                """,
                (str(image_uid),),
            ).fetchone()
            if row is None:
                raise OutputPairNotFoundError(
                    "Canonical image is missing or deleted"
                )
            json_value = row["json_path"]
            return CurationImage(
                image_uid=str(row["image_uid"]),
                png_path=Path(str(row["png_path"])),
                json_path=(
                    Path(str(json_value))
                    if json_value is not None and str(json_value).strip()
                    else None
                ),
            )
        finally:
            connection.close()

    def assign(self, assignment: CurationAssignment) -> CurationResult:
        """Commit current paths and a single assignment atomically."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE images
                SET png_path = ?, json_path = ?, last_seen_at = datetime('now')
                WHERE image_uid = ?
                  AND deleted_at IS NULL
                  AND png_path = ?
                  AND json_path IS ?
                """,
                (
                    str(assignment.png_path),
                    self._path_text(assignment.json_path),
                    assignment.image_uid,
                    str(assignment.previous_png_path),
                    self._path_text(assignment.previous_json_path),
                ),
            )
            if cursor.rowcount != 1:
                raise CurationValidationError(
                    "Canonical image paths changed during curation"
                )
            image_row = connection.execute(
                "SELECT id FROM images WHERE image_uid = ?",
                (assignment.image_uid,),
            ).fetchone()
            if image_row is None:
                raise CurationValidationError("Canonical image is missing")
            image_id = int(image_row["id"])
            if assignment.set_key is None:
                connection.execute(
                    "DELETE FROM curation_assignments WHERE image_id = ?",
                    (image_id,),
                )
            else:
                source_key = f"runtime-curation:{assignment.image_uid}"
                connection.execute(
                    """
                    INSERT INTO curation_assignments(
                        image_id, set_key, source, source_key
                    )
                    VALUES (?, ?, 'runtime', ?)
                    ON CONFLICT(image_id) DO UPDATE SET
                        set_key = excluded.set_key,
                        source = excluded.source,
                        source_key = excluded.source_key,
                        assigned_at = datetime('now')
                    """,
                    (image_id, assignment.set_key, source_key),
                )
            connection.commit()
            return CurationResult(
                image_uid=assignment.image_uid,
                png_path=assignment.png_path,
                json_path=assignment.json_path,
                set_key=assignment.set_key,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _path_text(path: Path | None) -> str | None:
        return None if path is None else str(path)
