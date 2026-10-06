"""SQLite facts for Playground example evidence."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application.generation_geometry import (
    AspectFormat,
    ResolutionClass,
)
from comfyreview.application.playground_evidence import (
    PlaygroundEvidenceCandidate,
)
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


class SqlitePlaygroundEvidenceRepository:
    """Read normalized visible image facts for deterministic scoring."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_candidates(self) -> tuple[PlaygroundEvidenceCandidate, ...]:
        """Return every live visible canonical image with comparison facts."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                f"""
                SELECT image.image_uid,
                       positive_prompt.text AS positive_prompt,
                       negative_prompt.text AS negative_prompt,
                       generation.checkpoint, generation.sampler,
                       generation.scheduler, generation.steps,
                       generation.cfg, generation.denoise,
                       geometry.aspect_format, geometry.resolution_class,
                       summary.average_rating, summary.rating_count
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                JOIN prompts AS positive_prompt
                  ON positive_prompt.id = generation.positive_prompt_id
                JOIN prompts AS negative_prompt
                  ON negative_prompt.id = generation.negative_prompt_id
                JOIN image_review_summary AS summary ON summary.image_id = image.id
                LEFT JOIN image_geometry_projection AS geometry
                  ON geometry.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND {content_visibility_predicate()}
                ORDER BY image.image_uid
                """
            ).fetchall()
            return tuple(self._map(row) for row in rows)
        finally:
            connection.close()

    @staticmethod
    def _map(row) -> PlaygroundEvidenceCandidate:
        return PlaygroundEvidenceCandidate(
            image_uid=str(row["image_uid"]),
            positive_atoms=prompt_atom_usages_from_text(
                row["positive_prompt"]
            ),
            negative_atoms=prompt_atom_usages_from_text(
                row["negative_prompt"]
            ),
            checkpoint=str(row["checkpoint"] or ""),
            sampler=str(row["sampler"] or ""),
            scheduler=str(row["scheduler"] or ""),
            steps=int(row["steps"]) if row["steps"] is not None else None,
            cfg=float(row["cfg"]) if row["cfg"] is not None else None,
            denoise=float(row["denoise"])
            if row["denoise"] is not None
            else None,
            aspect_format=(
                AspectFormat(str(row["aspect_format"]))
                if row["aspect_format"] is not None
                else None
            ),
            resolution_class=(
                ResolutionClass(str(row["resolution_class"]))
                if row["resolution_class"] is not None
                else None
            ),
            average_rating=(
                float(row["average_rating"])
                if row["average_rating"] is not None
                else None
            ),
            rating_count=int(row["rating_count"]),
        )
