"""Canonical SQLite adapter for focused render analytics."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from comfyreview.application.analytics import AnalyticsImage
from comfyreview.application.pagination import CollectionPage
from comfyreview.application.rating_evidence import (
    _bayes_lb05,
    _classify,
    _delete_weight_for_run,
    _rating_weight_for_run,
)
from comfyreview.application.render_analytics import (
    CalculatedRenderRecommendation,
    ParameterValueStatistic,
    RenderParameter,
    RenderSamplerStage,
    RenderSetupStatistic,
)
from comfyreview.repositories.sqlite.analytics import SqliteAnalyticsRepository
from comfyreview.repositories.sqlite.connection import connect_read_only
from comfyreview.repositories.sqlite.page_analytics_parameters import (
    fetch_calculated_best_cases,
    fetch_param_stats,
)


@dataclass(frozen=True, slots=True)
class _ObservedImage:
    image_id: int
    image_uid: str
    png_path: Path
    json_path: Path | None
    run: int
    rating: int | None
    deleted: bool
    average_rating: float | None
    rating_count: int


@dataclass(slots=True)
class _SetupEvidence:
    checkpoint: str
    stages: tuple[RenderSamplerStage, ...]
    observations: list[_ObservedImage] = field(default_factory=list)


class SqliteRenderSetupQuery:
    """Read and aggregate observed render setups from canonical facts."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_setups(
        self,
        *,
        model: str,
        composition_uid: str = "",
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        offset: int = 0,
        limit: int,
    ) -> CollectionPage[RenderSetupStatistic]:
        """Return observed setup evidence with ordered sampler stages."""
        rows = self._load_rows(model=model, composition_uid=composition_uid)
        evidence = self._group_rows(rows)
        statistics = tuple(
            self._statistic(
                item,
                success_threshold=success_threshold,
                delete_weight=delete_weight,
            )
            for item in evidence.values()
            if len(item.observations) >= minimum_samples
        )
        ordered = tuple(
            sorted(
                statistics,
                key=lambda item: (
                    item.lower_bound,
                    item.expected_success_rate,
                    item.rating_count,
                    item.setup_key,
                ),
                reverse=True,
            )
        )
        return CollectionPage(
            entries=ordered[offset : offset + limit],
            total=len(ordered),
            offset=offset,
            limit=limit,
        )

    def _load_rows(self, *, model: str, composition_uid: str) -> list[Any]:
        conditions: list[str] = []
        parameters: list[object] = []
        if model:
            conditions.append("generation.model_branch = ?")
            parameters.append(model)
        if composition_uid:
            conditions.append("composition.composition_uid = ?")
            parameters.append(composition_uid)
        where = "WHERE " + " AND ".join(conditions) if conditions else ""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return connection.execute(
                f"""
                SELECT
                    generation.id AS generation_id,
                    generation.checkpoint,
                    generation.steps AS fallback_steps,
                    generation.cfg AS fallback_cfg,
                    generation.sampler AS fallback_sampler,
                    generation.scheduler AS fallback_scheduler,
                    generation.denoise AS fallback_denoise,
                    image.id AS image_id,
                    image.image_uid,
                    image.png_path,
                    image.json_path,
                    rating.run,
                    rating.rating,
                    rating.deleted,
                    summary.average_rating,
                    summary.rating_count,
                    stage.stage_order,
                    stage.role,
                    stage.steps,
                    stage.cfg,
                    stage.sampler,
                    stage.scheduler,
                    stage.denoise
                FROM ratings AS rating
                JOIN images AS image ON image.png_path = rating.png_path
                JOIN generations AS generation
                    ON generation.id = image.generation_id
                LEFT JOIN prompt_compositions AS composition
                    ON composition.id = generation.prompt_composition_id
                LEFT JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                LEFT JOIN generation_sampler_stages AS stage
                    ON stage.generation_id = generation.id
                {where}
                ORDER BY
                    generation.id,
                    image.id,
                    rating.run,
                    stage.stage_order,
                    stage.id
                """,
                parameters,
            ).fetchall()
        finally:
            connection.close()

    @staticmethod
    def _group_rows(
        rows: list[Any],
    ) -> dict[tuple[object, ...], _SetupEvidence]:
        generation_rows: dict[int, list[Any]] = {}
        for row in rows:
            generation_rows.setdefault(int(row["generation_id"]), []).append(
                row
            )

        grouped: dict[tuple[object, ...], _SetupEvidence] = {}
        for generation in generation_rows.values():
            first = generation[0]
            stages = _sampler_stages(generation)
            checkpoint = str(first["checkpoint"] or "")
            key: tuple[object, ...] = (checkpoint, stages)
            target = grouped.setdefault(
                key, _SetupEvidence(checkpoint, stages)
            )
            observations: dict[tuple[int, int, bool], _ObservedImage] = {}
            for row in generation:
                observation = _observation(row)
                observations.setdefault(
                    (
                        observation.image_id,
                        observation.run,
                        observation.deleted,
                    ),
                    observation,
                )
            target.observations.extend(observations.values())
        return grouped

    @staticmethod
    def _statistic(
        evidence: _SetupEvidence,
        *,
        success_threshold: int,
        delete_weight: int,
    ) -> RenderSetupStatistic:
        success = 0
        failure = 0
        rating_sum = 0.0
        rating_weight = 0
        images: dict[int, AnalyticsImage] = {}
        for item in evidence.observations:
            if item.deleted:
                failure += _delete_weight_for_run(item.run, delete_weight)
                continue
            classification = _classify(
                run=item.run,
                rating=item.rating,
                deleted=0,
                base_pass_min=success_threshold,
            )
            weight = _rating_weight_for_run(item.run)
            if classification is True:
                success += weight
            elif classification is False:
                failure += weight
            if item.rating is not None:
                rating_sum += item.rating * weight
                rating_weight += weight
            images[item.image_id] = AnalyticsImage(
                item.png_path,
                item.json_path,
                item.average_rating,
                item.rating_count,
                item.image_uid,
            )
        expected = (success + 1) / (success + failure + 2)
        average = rating_sum / rating_weight if rating_weight else None
        best_images = tuple(
            sorted(
                images.values(),
                key=lambda image: (
                    image.average_rating is not None,
                    image.average_rating or 0.0,
                    image.rating_count,
                    str(image.png_path),
                ),
                reverse=True,
            )[:3]
        )
        setup_key = _setup_key(evidence.checkpoint, evidence.stages)
        return RenderSetupStatistic(
            setup_key=setup_key,
            checkpoint=evidence.checkpoint,
            stages=evidence.stages,
            image_count=len({item.image_id for item in evidence.observations}),
            rating_count=sum(image.rating_count for image in images.values()),
            average_rating=average,
            expected_success_rate=float(expected),
            lower_bound=float(_bayes_lb05(float(success), float(failure))),
            best_images=best_images,
        )


class SqliteRenderAnalyticsRepository:
    """Implement focused render analytics against canonical SQLite."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)
        self._setups = SqliteRenderSetupQuery(database_path)
        self._images = SqliteAnalyticsRepository(database_path)

    def list_calculated_recommendations(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> tuple[CalculatedRenderRecommendation, ...]:
        """Return typed marginal recommendations from canonical facts."""
        rows = fetch_calculated_best_cases(
            self._database_path,
            model=model,
            min_n=minimum_samples,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            limit=limit,
        )
        return tuple(_recommendation(row) for row in rows)

    def list_observed_setups(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        offset: int = 0,
        limit: int,
    ) -> CollectionPage[RenderSetupStatistic]:
        """Return complete setups built from normalized columns and stages."""
        return self._setups.list_setups(
            model=model,
            minimum_samples=minimum_samples,
            success_threshold=success_threshold,
            delete_weight=delete_weight,
            offset=offset,
            limit=limit,
        )

    def list_parameter_values(
        self,
        parameter: RenderParameter,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        offset: int = 0,
        limit: int,
    ) -> CollectionPage[ParameterValueStatistic]:
        """Return one requested parameter dimension with image examples."""
        rows = tuple(
            row
            for row in fetch_param_stats(
                self._database_path,
                model=model,
                min_n=minimum_samples,
                success_threshold=success_threshold,
                delete_weight=delete_weight,
            )
            if row.get("feat") == parameter.value
        )
        total = len(rows)
        rows = rows[offset : offset + limit]
        values = tuple(str(row["value"]) for row in rows)
        images = self._images.list_best_images_for_parameter(
            parameter.value,
            values,
            model_branch=model,
            limit_per_value=3,
        )
        entries = tuple(
            ParameterValueStatistic(
                parameter=parameter,
                value=str(row["value"]),
                sample_count=int(row["n"]),
                average_rating=_optional_float(row.get("avg_rating")),
                expected_success_rate=float(row["exp_success_rate"]),
                lower_bound=float(row["stability_lb05"]),
                best_images=images.get(str(row["value"]), ()),
            )
            for row in rows
        )
        return CollectionPage(entries, total, offset, limit)


def _sampler_stages(rows: list[Any]) -> tuple[RenderSamplerStage, ...]:
    stages: dict[int, RenderSamplerStage] = {}
    for row in rows:
        if row["stage_order"] is None:
            continue
        stages.setdefault(
            int(row["stage_order"]),
            RenderSamplerStage(
                role=str(row["role"] or ""),
                steps=_optional_int(row["steps"]),
                cfg=_optional_float(row["cfg"]),
                sampler=str(row["sampler"] or ""),
                scheduler=str(row["scheduler"] or ""),
                denoise=_optional_float(row["denoise"]),
            ),
        )
    if stages:
        return tuple(stages[index] for index in sorted(stages))
    first = rows[0]
    return (
        RenderSamplerStage(
            role="base_sampler",
            steps=_optional_int(first["fallback_steps"]),
            cfg=_optional_float(first["fallback_cfg"]),
            sampler=str(first["fallback_sampler"] or ""),
            scheduler=str(first["fallback_scheduler"] or ""),
            denoise=_optional_float(first["fallback_denoise"]),
        ),
    )


def _observation(row: Any) -> _ObservedImage:
    json_path = str(row["json_path"] or "")
    return _ObservedImage(
        image_id=int(row["image_id"]),
        image_uid=str(row["image_uid"]),
        png_path=Path(str(row["png_path"])),
        json_path=Path(json_path) if json_path else None,
        run=int(row["run"] or 1),
        rating=_optional_int(row["rating"]),
        deleted=bool(row["deleted"]),
        average_rating=_optional_float(row["average_rating"]),
        rating_count=int(row["rating_count"] or 0),
    )


def _recommendation(row: dict[str, Any]) -> CalculatedRenderRecommendation:
    raw_picks = row.get("picks")
    picks: dict[str, Any] = raw_picks if isinstance(raw_picks, dict) else {}
    raw_checkpoint_stats = row.get("checkpoint_stats")
    checkpoint_stats: dict[str, Any] = (
        raw_checkpoint_stats if isinstance(raw_checkpoint_stats, dict) else {}
    )
    return CalculatedRenderRecommendation(
        checkpoint=str(row.get("checkpoint") or ""),
        sampler=_pick_text(picks, "sampler"),
        scheduler=_pick_text(picks, "scheduler"),
        steps=_pick_int(picks, "steps"),
        cfg=_pick_float(picks, "cfg"),
        denoise=_pick_float(picks, "denoise"),
        score=float(row.get("score") or 0.0),
        checkpoint_lower_bound=float(
            checkpoint_stats.get("stability_lb05") or 0.0
        ),
    )


def _pick_value(picks: dict[str, Any], name: str) -> object | None:
    value = picks.get(name)
    return value.get("value") if isinstance(value, dict) else None


def _pick_text(picks: dict[str, Any], name: str) -> str:
    return str(_pick_value(picks, name) or "")


def _pick_int(picks: dict[str, Any], name: str) -> int | None:
    return _optional_int(_pick_value(picks, name))


def _pick_float(picks: dict[str, Any], name: str) -> float | None:
    return _optional_float(_pick_value(picks, name))


def _optional_int(value: Any) -> int | None:
    return None if value is None else int(value)


def _optional_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _setup_key(
    checkpoint: str,
    stages: tuple[RenderSamplerStage, ...],
) -> str:
    content = json.dumps(
        {
            "checkpoint": checkpoint,
            "stages": [
                {
                    "role": stage.role,
                    "steps": stage.steps,
                    "cfg": stage.cfg,
                    "sampler": stage.sampler,
                    "scheduler": stage.scheduler,
                    "denoise": stage.denoise,
                }
                for stage in stages
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"render-setup-{hashlib.sha256(content.encode()).hexdigest()}"
