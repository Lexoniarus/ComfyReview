"""Read canonical statistics without writable projection databases."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any

from comfyreview.application.analytics import (
    AnalyticsImage,
    ObservedPromptCombination,
    PromptMatchPreview,
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

    def list_selected_prompt_token_statistics(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str,
        scope: str,
    ) -> tuple[PromptTokenStatistic, ...]:
        """Aggregate selected canonical tokens without a projection DB."""
        if not tokens:
            return ()
        placeholders = ",".join("?" for _token in tokens)
        arguments: list[object] = [scope, *tokens]
        model_clause = ""
        if model_branch:
            model_clause = " AND model_branch = ?"
            arguments.append(model_branch)
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                f"""
                SELECT token, COUNT(rating) AS sample_count,
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
                WHERE deleted = 0 AND rating IS NOT NULL AND scope = ?
                  AND token IN ({placeholders}) {model_clause}
                GROUP BY token
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

    def find_best_prompt_match(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str,
        scope: str,
        minimum_hits: int,
        minimum_ratings: int,
        candidate_limit: int,
    ) -> PromptMatchPreview | None:
        """Find the best live image for canonical prompt-token evidence."""
        if not tokens:
            return None
        placeholders = ",".join("?" for _token in tokens)
        arguments: list[object] = [scope, *tokens]
        model_clause = ""
        if model_branch:
            model_clause = " AND token.model_branch = ?"
            arguments.append(model_branch)
        arguments.extend((minimum_hits, candidate_limit, minimum_ratings))
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                f"""
                WITH candidates AS (
                    SELECT token.json_path,
                           COUNT(DISTINCT token.token) AS token_hits
                    FROM tokens AS token
                    WHERE token.deleted = 0 AND token.scope = ?
                      AND token.token IN ({placeholders})
                      AND token.json_path IS NOT NULL
                      AND token.json_path <> '' {model_clause}
                    GROUP BY token.json_path
                    HAVING COUNT(DISTINCT token.token) >= ?
                    ORDER BY token_hits DESC
                    LIMIT ?
                )
                SELECT candidate.json_path, candidate.token_hits,
                       image.png_path, summary.average_rating,
                       summary.rating_count
                FROM candidates AS candidate
                JOIN images AS image ON image.json_path = candidate.json_path
                JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND summary.rating_count >= ?
                ORDER BY candidate.token_hits DESC,
                         summary.average_rating DESC,
                         summary.rating_count DESC,
                         image.image_uid
                LIMIT 1
                """,
                arguments,
            ).fetchone()
            if row is None:
                return None
            return PromptMatchPreview(
                json_path=Path(str(row["json_path"])),
                png_path=Path(str(row["png_path"])),
                token_hits=int(row["token_hits"]),
                average_rating=(
                    float(row["average_rating"])
                    if row["average_rating"] is not None
                    else None
                ),
                rating_count=int(row["rating_count"]),
            )
        finally:
            connection.close()

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
        """Aggregate canonical character/scene[/outfit] memberships."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                WITH composition_scopes AS (
                    SELECT
                        membership.composition_id,
                        MAX(CASE WHEN component.kind = 'character'
                            THEN component.component_uid END) AS character_uid,
                        MAX(CASE WHEN component.kind = 'character'
                            THEN component.name END) AS character_name,
                        COUNT(DISTINCT CASE WHEN component.kind = 'character'
                            THEN component.id END) AS character_count,
                        MAX(CASE WHEN component.kind = 'scene'
                            THEN component.component_uid END) AS scene_uid,
                        MAX(CASE WHEN component.kind = 'scene'
                            THEN component.name END) AS scene_name,
                        COUNT(DISTINCT CASE WHEN component.kind = 'scene'
                            THEN component.id END) AS scene_count,
                        MAX(CASE WHEN component.kind = 'outfit'
                            THEN component.component_uid END) AS outfit_uid,
                        MAX(CASE WHEN component.kind = 'outfit'
                            THEN component.name END) AS outfit_name,
                        COUNT(DISTINCT CASE WHEN component.kind = 'outfit'
                            THEN component.id END) AS outfit_count
                    FROM prompt_composition_revisions AS membership
                    JOIN prompt_revisions AS revision
                        ON revision.id = membership.revision_id
                    JOIN prompt_components AS component
                        ON component.id = revision.component_id
                    GROUP BY membership.composition_id
                )
                SELECT
                    scope.character_uid,
                    scope.character_name,
                    scope.scene_uid,
                    scope.scene_name,
                    scope.outfit_uid,
                    scope.outfit_name,
                    image.image_uid,
                    image.png_path,
                    image.json_path,
                    summary.average_rating,
                    summary.rating_count
                FROM generations AS generation
                JOIN composition_scopes AS scope
                    ON scope.composition_id = generation.prompt_composition_id
                JOIN images AS image ON image.generation_id = generation.id
                LEFT JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND scope.character_count = 1
                  AND scope.scene_count = 1
                  AND (? = 2 OR scope.outfit_count = 1)
                ORDER BY scope.character_uid, scope.scene_uid,
                         scope.outfit_uid, summary.average_rating DESC,
                         summary.rating_count DESC, image.image_uid
                """,
                (combo_size,),
            ).fetchall()
        finally:
            connection.close()
        grouped: dict[tuple[str, ...], list[Any]] = defaultdict(list)
        for row in rows:
            key: tuple[str, ...] = (
                str(row["character_uid"]),
                str(row["scene_uid"]),
            )
            if combo_size == 3:
                outfit_uid = str(row["outfit_uid"] or "")
                if not outfit_uid:
                    continue
                key = (*key, outfit_uid)
            grouped[key].append(row)
        combinations: list[ObservedPromptCombination] = []
        for component_uids, combo_rows in grouped.items():
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
            first = combo_rows[0]
            component_names = (
                str(first["character_name"]),
                str(first["scene_name"]),
                *((str(first["outfit_name"]),) if combo_size == 3 else ()),
            )
            combinations.append(
                ObservedPromptCombination(
                    combo_key="|".join(component_uids),
                    combo_size=combo_size,
                    component_uids=component_uids,
                    component_names=component_names,
                    label=" + ".join(component_names),
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
                        image.image_uid,
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
            image_uid=str(row["image_uid"] or ""),
        )
