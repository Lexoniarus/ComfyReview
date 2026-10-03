"""SQLite repository for prompt-catalog image evidence."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application.catalog_evidence import CatalogEvidenceImage
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


class SqliteCatalogEvidenceRepository:
    """Read bounded evidence directly from canonical component relations."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def list_top_images(
        self,
        component_uid: str,
        *,
        limit: int,
    ) -> tuple[CatalogEvidenceImage, ...]:
        """Return deterministic top-rated live images for one component."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                f"""
                WITH candidates AS (
                    SELECT DISTINCT
                        image.image_uid,
                        summary.average_rating,
                        summary.rating_count
                    FROM prompt_components AS component
                    JOIN prompt_revisions AS revision
                      ON revision.component_id = component.id
                    JOIN prompt_composition_revisions AS membership
                      ON membership.revision_id = revision.id
                    JOIN generations AS generation
                      ON generation.prompt_composition_id =
                         membership.composition_id
                    JOIN images AS image
                      ON image.generation_id = generation.id
                    LEFT JOIN image_review_summary AS summary
                      ON summary.image_id = image.id
                    WHERE component.component_uid = ?
                      AND image.deleted_at IS NULL
                      AND {content_visibility_predicate()}
                )
                SELECT image_uid, average_rating, rating_count
                FROM candidates
                ORDER BY
                    average_rating IS NULL,
                    average_rating DESC,
                    rating_count DESC,
                    image_uid
                LIMIT ?
                """,
                (component_uid, limit),
            ).fetchall()
            return tuple(
                CatalogEvidenceImage(
                    image_uid=str(row["image_uid"]),
                    average_rating=(
                        float(row["average_rating"])
                        if row["average_rating"] is not None
                        else None
                    ),
                    rating_count=int(row["rating_count"] or 0),
                )
                for row in rows
            )
        finally:
            connection.close()
