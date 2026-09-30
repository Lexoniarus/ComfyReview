"""Read canonical statistics without writable projection databases."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from comfyreview.application.analytics import (
    AnalyticsImage,
    ObservedPromptCombination,
    PromptTokenStatistic,
)
from comfyreview.repositories.sqlite.connection import connect_read_only

_PARAMETER_COLUMNS = {
    "checkpoint": "generation.checkpoint",
    "steps": "generation.steps",
    "cfg": "ROUND(generation.cfg, 1)",
    "sampler": "generation.sampler",
    "scheduler": "generation.scheduler",
}


class SqliteAnalyticsRepository:
    """Own direct canonical SQLite queries for statistics read models."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_prompt_token_statistics(
        self,
        *,
        model_branch: str,
        scope: str,
        minimum_samples: int,
        limit: int,
    ) -> tuple[PromptTokenStatistic, ...]:
        """Aggregate the canonical token view on demand."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            model_clause = ""
            arguments: list[object] = [scope]
            if model_branch:
                model_clause = " AND model_branch = ?"
                arguments.append(model_branch)
            arguments.extend((minimum_samples, limit))
            rows = connection.execute(
                f"""
                SELECT
                    token,
                    COUNT(rating) AS sample_count,
                    AVG(rating) AS mean_score,
                    CASE
                        WHEN COUNT(rating) <= 1 THEN AVG(rating)
                        ELSE AVG(rating) - 1.645 * SQRT(
                            CASE
                                WHEN AVG(rating * rating)
                                     - AVG(rating) * AVG(rating) > 0
                                THEN AVG(rating * rating)
                                     - AVG(rating) * AVG(rating)
                                ELSE 0.0
                            END / COUNT(rating)
                        )
                    END AS lower_bound
                FROM tokens
                WHERE scope = ?
                  AND deleted = 0
                  AND rating IS NOT NULL
                  {model_clause}
                GROUP BY token
                HAVING COUNT(rating) >= ?
                ORDER BY lower_bound DESC, sample_count DESC, token
                LIMIT ?
                """,
                arguments,
            ).fetchall()
            return tuple(
                PromptTokenStatistic(
                    token=str(row["token"]),
                    sample_count=int(row["sample_count"]),
                    mean_score=float(row["mean_score"]),
                    lower_bound=float(row["lower_bound"]),
                )
                for row in rows
            )
        finally:
            connection.close()

    def list_best_images_for_combos(
        self,
        combo_keys: tuple[str, ...],
        *,
        model_branch: str,
        limit_per_combo: int,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Read and group best live images for observed combo keys."""
        rows = self._image_rows(
            expression="generation.combo_key",
            values=combo_keys,
            model_branch=model_branch,
        )
        return self._group_images(rows, limit_per_combo)

    def list_best_images_for_parameter(
        self,
        parameter: str,
        values: tuple[str, ...],
        *,
        model_branch: str,
        limit_per_value: int,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Read and group best live images for a supported parameter."""
        expression = _PARAMETER_COLUMNS.get(parameter)
        if expression is None:
            raise ValueError(f"Unsupported analytics parameter: {parameter}")
        rows = self._image_rows(
            expression=expression,
            values=values,
            model_branch=model_branch,
        )
        return self._group_images(rows, limit_per_value)

    def list_observed_combinations(
        self,
        *,
        combo_size: int,
        limit: int,
    ) -> tuple[ObservedPromptCombination, ...]:
        """Aggregate combinations that have canonical generation evidence."""
        names = self._legacy_component_names()
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT
                    generation.combo_key,
                    image.png_path,
                    image.json_path,
                    summary.average_rating,
                    summary.rating_count
                FROM generations AS generation
                JOIN images AS image ON image.generation_id = generation.id
                LEFT JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND generation.combo_key <> ''
                ORDER BY generation.combo_key, summary.average_rating DESC,
                         summary.rating_count DESC, image.image_uid
                """
            ).fetchall()
        finally:
            connection.close()
        grouped: dict[str, list[Any]] = defaultdict(list)
        for row in rows:
            grouped[str(row["combo_key"])].append(row)
        combinations: list[ObservedPromptCombination] = []
        for combo_key, combo_rows in grouped.items():
            identities = self._parse_legacy_combo_key(combo_key)
            if len(identities) != combo_size:
                continue
            character_id = identities.get("character")
            scene_id = identities.get("scene")
            if character_id is None or scene_id is None:
                continue
            outfit_id = identities.get("outfit")
            images = tuple(
                self._analytics_image(row) for row in combo_rows[:3]
            )
            total_count = sum(
                int(row["rating_count"] or 0) for row in combo_rows
            )
            weighted_sum = sum(
                float(row["average_rating"] or 0.0)
                * int(row["rating_count"] or 0)
                for row in combo_rows
            )
            label_parts = [
                names.get(
                    ("character", character_id), f"Character {character_id}"
                ),
                names.get(("scene", scene_id), f"Scene {scene_id}"),
            ]
            if outfit_id is not None:
                label_parts.append(
                    names.get(("outfit", outfit_id), f"Outfit {outfit_id}")
                )
            combinations.append(
                ObservedPromptCombination(
                    combo_key=combo_key,
                    combo_size=combo_size,
                    character_id=character_id,
                    scene_id=scene_id,
                    outfit_id=outfit_id,
                    label=" + ".join(label_parts),
                    average_rating=(
                        weighted_sum / total_count if total_count else None
                    ),
                    image_count=len(combo_rows),
                    total_rating_count=total_count,
                    best_images=images,
                )
            )
        combinations.sort(
            key=lambda item: (
                item.average_rating is not None,
                item.average_rating or 0.0,
                item.total_rating_count,
                item.image_count,
                item.combo_key,
            ),
            reverse=True,
        )
        return tuple(combinations[:limit])

    def latest_review_sequence(self) -> int:
        """Read the append-only review-event frontier."""
        connection = connect_read_only(self._database_path)
        try:
            row = connection.execute(
                "SELECT COALESCE(MAX(sequence), 0) FROM review_events"
            ).fetchone()
            return int(row[0] or 0) if row else 0
        finally:
            connection.close()

    def _image_rows(
        self,
        *,
        expression: str,
        values: tuple[str, ...],
        model_branch: str,
    ) -> list[Any]:
        if not values:
            return []
        placeholders = ",".join("?" for _value in values)
        arguments: list[object] = list(values)
        model_clause = ""
        if model_branch:
            model_clause = " AND generation.model_branch = ?"
            arguments.append(model_branch)
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return list(
                connection.execute(
                    f"""
                    SELECT
                        CAST({expression} AS TEXT) AS group_value,
                        image.png_path,
                        image.json_path,
                        summary.average_rating,
                        summary.rating_count
                    FROM images AS image
                    JOIN generations AS generation
                        ON generation.id = image.generation_id
                    JOIN image_review_summary AS summary
                        ON summary.image_id = image.id
                    WHERE image.deleted_at IS NULL
                      AND CAST({expression} AS TEXT) IN ({placeholders})
                      {model_clause}
                    ORDER BY group_value, summary.average_rating DESC,
                             summary.rating_count DESC, image.image_uid
                    """,
                    arguments,
                ).fetchall()
            )
        finally:
            connection.close()

    @classmethod
    def _group_images(
        cls,
        rows: list[Any],
        limit_per_group: int,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        grouped: dict[str, list[AnalyticsImage]] = defaultdict(list)
        for row in rows:
            group = str(row["group_value"])
            if len(grouped[group]) < limit_per_group:
                grouped[group].append(cls._analytics_image(row))
        return {key: tuple(images) for key, images in grouped.items()}

    @staticmethod
    def _analytics_image(row: Any) -> AnalyticsImage:
        return AnalyticsImage(
            png_path=Path(str(row["png_path"])),
            json_path=(
                Path(str(row["json_path"]))
                if row["json_path"] is not None
                else None
            ),
            average_rating=(
                float(row["average_rating"])
                if row["average_rating"] is not None
                else None
            ),
            rating_count=int(row["rating_count"] or 0),
        )

    def _legacy_component_names(self) -> dict[tuple[str, int], str]:
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT component.kind, source.source_key, component.name
                FROM legacy_prompt_component_sources AS source
                JOIN prompt_components AS component
                    ON component.id = source.component_id
                WHERE source.source = 'legacy_playground'
                """
            ).fetchall()
            return {
                (str(row["kind"]), int(row["source_key"])): str(row["name"])
                for row in rows
            }
        finally:
            connection.close()

    @staticmethod
    def _parse_legacy_combo_key(combo_key: str) -> dict[str, int]:
        identities: dict[str, int] = {}
        for part in str(combo_key or "").split("|"):
            kind, separator, raw_id = part.partition(":")
            if not separator or kind not in {"character", "scene", "outfit"}:
                return {}
            try:
                identities[kind] = int(raw_id)
            except ValueError:
                return {}
        return identities
