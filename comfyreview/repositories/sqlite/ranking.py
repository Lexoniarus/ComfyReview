"""SQLite adapter for canonical image ranking queries."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.ranking import RankedImage
from comfyreview.repositories.sqlite.connection import connect_read_only


class SqliteRankingRepository:
    """Read canonical ranking aggregates without mutating persistence."""

    def __init__(
        self,
        database_path: Path,
        *,
        output_root: Path,
        allowed_set_keys: tuple[str, ...],
    ) -> None:
        self._database_path = Path(database_path)
        self._output_root = Path(output_root).resolve(strict=False)
        self._allowed_set_keys = frozenset(allowed_set_keys)

    def list_ranked_images(self) -> tuple[RankedImage, ...]:
        """Return rated, non-deleted images from canonical facts."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT
                    image.image_uid,
                    image.png_path,
                    image.json_path,
                    generation.model_branch,
                    generation.checkpoint,
                    generation.combo_key,
                    generation.sampler,
                    generation.scheduler,
                    generation.steps,
                    generation.cfg,
                    generation.denoise,
                    positive_prompt.text AS positive_prompt,
                    summary.current_rating,
                    summary.rating_count,
                    summary.average_rating,
                    assignment.set_key AS assigned_set_key
                FROM images AS image
                JOIN generations AS generation
                    ON generation.id = image.generation_id
                JOIN prompts AS positive_prompt
                    ON positive_prompt.id = generation.positive_prompt_id
                JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                LEFT JOIN curation_assignments AS assignment
                    ON assignment.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND summary.average_rating IS NOT NULL
                  AND summary.rating_count > 0
                ORDER BY image.id
                """
            ).fetchall()
            return tuple(self._ranked_image(row) for row in rows)
        finally:
            connection.close()

    def _ranked_image(self, row: sqlite3.Row) -> RankedImage:
        png_path = Path(str(row["png_path"]))
        json_value = row["json_path"]
        assigned = (
            str(row["assigned_set_key"])
            if row["assigned_set_key"] is not None
            else self._infer_set_key(png_path)
        )
        return RankedImage(
            image_uid=str(row["image_uid"]),
            png_path=png_path,
            json_path=(
                Path(str(json_value))
                if json_value is not None and str(json_value).strip()
                else None
            ),
            subdir=self._subdir(png_path),
            model_branch=str(row["model_branch"] or ""),
            checkpoint=str(row["checkpoint"] or ""),
            combo_key=str(row["combo_key"] or ""),
            positive_prompt=str(row["positive_prompt"] or ""),
            average_rating=float(row["average_rating"]),
            rating_count=int(row["rating_count"]),
            current_rating=(
                int(row["current_rating"])
                if row["current_rating"] is not None
                else None
            ),
            sampler=(
                str(row["sampler"]) if row["sampler"] is not None else None
            ),
            scheduler=(
                str(row["scheduler"]) if row["scheduler"] is not None else None
            ),
            steps=(int(row["steps"]) if row["steps"] is not None else None),
            cfg=(float(row["cfg"]) if row["cfg"] is not None else None),
            denoise=(
                float(row["denoise"]) if row["denoise"] is not None else None
            ),
            assigned_set_key=assigned,
        )

    def _relative_parts(self, png_path: Path) -> tuple[str, ...]:
        candidate = (
            png_path
            if png_path.is_absolute()
            else self._output_root / png_path
        ).resolve(strict=False)
        try:
            relative = candidate.parent.relative_to(self._output_root)
        except ValueError:
            return (candidate.parent.name,)
        return tuple(str(part) for part in relative.parts if str(part))

    def _subdir(self, png_path: Path) -> str:
        parts = self._relative_parts(png_path)
        if len(parts) >= 2 and parts[0].lower() == "playground":
            return f"playground/{parts[1]}"
        return "/".join(parts)

    def _infer_set_key(self, png_path: Path) -> str | None:
        parts = self._relative_parts(png_path)
        if len(parts) < 3 or parts[0].lower() != "playground":
            return None
        candidate = parts[2]
        return candidate if candidate in self._allowed_set_keys else None
