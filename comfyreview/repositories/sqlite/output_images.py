"""Read canonical output images and their generation facts."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import CanonicalOutputImageRecord
from comfyreview.repositories.sqlite.connection import connect_read_only

_SELECT_LIVE_IMAGES = """
SELECT
    image.image_uid,
    image.png_path,
    image.json_path,
    image.output_node_id,
    image.output_index,
    generation.generation_uid,
    generation.model_branch,
    generation.checkpoint,
    generation.combo_key,
    generation.seed,
    generation.steps,
    generation.cfg,
    generation.sampler,
    generation.scheduler,
    generation.denoise,
    generation.loras_json,
    generation.source,
    generation.raw_metadata_json,
    generation.workflow_json,
    positive_prompt.text AS positive_prompt,
    negative_prompt.text AS negative_prompt,
    summary.current_rating,
    summary.latest_rating_sequence AS review_version,
    summary.average_rating,
    summary.rating_count,
    assignment.set_key AS assigned_set_key
FROM images AS image
JOIN generations AS generation
    ON generation.id = image.generation_id
JOIN prompts AS positive_prompt
    ON positive_prompt.id = generation.positive_prompt_id
JOIN prompts AS negative_prompt
    ON negative_prompt.id = generation.negative_prompt_id
LEFT JOIN image_review_summary AS summary
    ON summary.image_id = image.id
LEFT JOIN curation_assignments AS assignment
    ON assignment.image_id = image.id
WHERE image.deleted_at IS NULL
"""


class SqliteOutputImageRepository:
    """Read live canonical images without touching the filesystem."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_live_images(self) -> tuple[CanonicalOutputImageRecord, ...]:
        """Return all live canonical images in stable database order."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                _SELECT_LIVE_IMAGES + " ORDER BY image.id"
            ).fetchall()
            return tuple(self._record(row) for row in rows)
        finally:
            connection.close()

    def get_live_image(
        self,
        image_uid: str,
    ) -> CanonicalOutputImageRecord | None:
        """Return one live canonical image by stable UID."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                _SELECT_LIVE_IMAGES + " AND image.image_uid = ?",
                (str(image_uid),),
            ).fetchone()
            return None if row is None else self._record(row)
        finally:
            connection.close()

    @staticmethod
    def _record(row: sqlite3.Row) -> CanonicalOutputImageRecord:
        json_value = row["json_path"]
        return CanonicalOutputImageRecord(
            image_uid=str(row["image_uid"]),
            generation_uid=str(row["generation_uid"]),
            png_path=Path(str(row["png_path"])),
            json_path=(
                Path(str(json_value))
                if json_value is not None and str(json_value).strip()
                else None
            ),
            output_node_id=str(row["output_node_id"] or ""),
            output_index=int(row["output_index"] or 0),
            model_branch=str(row["model_branch"] or ""),
            checkpoint=str(row["checkpoint"] or ""),
            combo_key=str(row["combo_key"] or ""),
            seed=int(row["seed"]) if row["seed"] is not None else None,
            steps=int(row["steps"]) if row["steps"] is not None else None,
            cfg=float(row["cfg"]) if row["cfg"] is not None else None,
            sampler=(
                str(row["sampler"]) if row["sampler"] is not None else None
            ),
            scheduler=(
                str(row["scheduler"]) if row["scheduler"] is not None else None
            ),
            denoise=(
                float(row["denoise"]) if row["denoise"] is not None else None
            ),
            loras_json=str(row["loras_json"] or "[]"),
            positive_prompt=str(row["positive_prompt"] or ""),
            negative_prompt=str(row["negative_prompt"] or ""),
            source=str(row["source"] or ""),
            raw_metadata_json=(
                str(row["raw_metadata_json"])
                if row["raw_metadata_json"] is not None
                else None
            ),
            workflow_json=(
                str(row["workflow_json"])
                if row["workflow_json"] is not None
                else None
            ),
            current_rating=(
                int(row["current_rating"])
                if row["current_rating"] is not None
                else None
            ),
            review_version=(
                int(row["review_version"])
                if row["review_version"] is not None
                else None
            ),
            average_rating=(
                float(row["average_rating"])
                if row["average_rating"] is not None
                else None
            ),
            rating_count=int(row["rating_count"] or 0),
            assigned_set_key=(
                str(row["assigned_set_key"])
                if row["assigned_set_key"] is not None
                else None
            ),
        )
