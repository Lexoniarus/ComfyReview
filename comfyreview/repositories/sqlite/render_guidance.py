"""SQLite adapter for canonical render-guidance evidence."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from comfyreview.application.rating_evidence import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    _classify,
    _delete_weight_for_run,
    _rating_weight_for_run,
)
from comfyreview.application.render_guidance import (
    RenderEvidenceObservation,
    RenderSettings,
)
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.content_visibility import (
    content_visibility_predicate,
)


@dataclass(slots=True)
class _ImageEvidence:
    image_uid: str
    fallback: RenderSettings
    stages: dict[int, RenderSettings] = field(default_factory=dict)
    events: dict[int, tuple[int, int | None, int]] = field(
        default_factory=dict
    )


class SqliteRenderEvidenceRepository:
    """Read normalized image evidence from the canonical database."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_observations(
        self, *, model: str = ""
    ) -> tuple[RenderEvidenceObservation, ...]:
        """Return one weighted evidence aggregate per visible rated image."""
        rows = self._load_rows(str(model or "").strip())
        grouped = self._group_rows(rows)
        return tuple(
            self._observation(item)
            for _, item in sorted(grouped.items())
            if item.events
        )

    def _load_rows(self, model: str) -> list[Any]:
        conditions = [content_visibility_predicate()]
        parameters: list[object] = []
        if model:
            conditions.append("generation.model_branch = ?")
            parameters.append(model)
        where = "WHERE " + " AND ".join(conditions)
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return connection.execute(
                f"""
                WITH evidence_events AS (
                    SELECT
                        event.id,
                        event.image_id,
                        event.event_type,
                        event.rating,
                        ROW_NUMBER() OVER (
                            PARTITION BY event.image_id
                            ORDER BY event.sequence, event.id
                        ) AS run
                    FROM review_events AS event
                    WHERE event.event_type IN ('rating', 'delete')
                )
                SELECT
                    image.id AS image_id,
                    image.image_uid,
                    generation.checkpoint,
                    generation.steps AS fallback_steps,
                    generation.cfg AS fallback_cfg,
                    generation.sampler AS fallback_sampler,
                    generation.scheduler AS fallback_scheduler,
                    generation.denoise AS fallback_denoise,
                    rating.id AS rating_event_id,
                    rating.run,
                    rating.rating,
                    CASE WHEN rating.event_type = 'delete' THEN 1 ELSE 0 END
                        AS deleted,
                    stage.stage_order,
                    stage.steps,
                    stage.cfg,
                    stage.sampler,
                    stage.scheduler,
                    stage.denoise
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                JOIN evidence_events AS rating
                  ON rating.image_id = image.id
                LEFT JOIN generation_sampler_stages AS stage
                  ON stage.generation_id = generation.id
                {where}
                ORDER BY image.id, stage.stage_order, rating.id
                """,
                parameters,
            ).fetchall()
        finally:
            connection.close()

    @staticmethod
    def _group_rows(rows: list[Any]) -> dict[int, _ImageEvidence]:
        grouped: dict[int, _ImageEvidence] = {}
        for row in rows:
            image_id = int(row["image_id"])
            fallback = _settings(row, prefix="fallback_")
            evidence = grouped.setdefault(
                image_id,
                _ImageEvidence(str(row["image_uid"]), fallback),
            )
            if row["stage_order"] is not None:
                evidence.stages.setdefault(
                    int(row["stage_order"]), _settings(row)
                )
            event_key = int(row["rating_event_id"] or 0) * 2 + int(
                row["deleted"] or 0
            )
            evidence.events.setdefault(
                event_key,
                (
                    int(row["run"] or 1),
                    _optional_int(row["rating"]),
                    int(row["deleted"] or 0),
                ),
            )
        return grouped

    @staticmethod
    def _observation(item: _ImageEvidence) -> RenderEvidenceObservation:
        success = 0
        failure = 0
        rating_sum = 0.0
        rating_weight = 0
        for run, rating, deleted in item.events.values():
            if deleted:
                failure += _delete_weight_for_run(run, DELETE_WEIGHT_DEFAULT)
                continue
            weight = _rating_weight_for_run(run)
            if rating is not None:
                rating_sum += rating * weight
                rating_weight += weight
            classification = _classify(
                run=run,
                rating=rating,
                deleted=deleted,
                base_pass_min=SUCCESS_THRESHOLD_DEFAULT,
            )
            if classification is True:
                success += weight
            elif classification is False:
                failure += weight
        settings = (
            item.stages[min(item.stages)] if item.stages else item.fallback
        )
        return RenderEvidenceObservation(
            image_uid=item.image_uid,
            settings=settings,
            success_weight=success,
            failure_weight=failure,
            rating_sum=rating_sum,
            rating_weight=rating_weight,
            review_count=len(item.events),
            stage_count=max(1, len(item.stages)),
        )


def _settings(row: Any, *, prefix: str = "") -> RenderSettings:
    return RenderSettings(
        checkpoint=str(row["checkpoint"] or ""),
        sampler=str(row[f"{prefix}sampler"] or ""),
        scheduler=str(row[f"{prefix}scheduler"] or ""),
        steps=int(row[f"{prefix}steps"] or 0),
        cfg=float(row[f"{prefix}cfg"] or 0.0),
        denoise=float(row[f"{prefix}denoise"] or 0.0),
    )


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        return int(value)
    raise TypeError("rating must be numeric")
