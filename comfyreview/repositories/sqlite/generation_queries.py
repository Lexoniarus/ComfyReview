"""Read-only SQLite adapter for canonical generation lifecycle views."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from comfyreview.application.generation_queries import (
    GenerationDetail,
    GenerationOutputSummary,
    GenerationPage,
    GenerationStageSummary,
    GenerationSummary,
)
from comfyreview.repositories.sqlite.connection import connect_read_only


class SqliteGenerationQueryRepository:
    """Read persisted lifecycle state without creating queue projections."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_generations(
        self,
        *,
        status: str,
        offset: int,
        limit: int,
    ) -> GenerationPage:
        """Return a filtered page ordered by newest canonical generation."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            where = "WHERE generation.status = ?" if status else ""
            parameters: tuple[object, ...] = (status,) if status else ()
            total = int(
                connection.execute(
                    f"SELECT COUNT(*) FROM generations AS generation {where}",
                    parameters,
                ).fetchone()[0]
            )
            rows = connection.execute(
                _SUMMARY_QUERY + f" {where} GROUP BY generation.id "
                "ORDER BY generation.id DESC LIMIT ? OFFSET ?",
                (*parameters, limit, offset),
            ).fetchall()
            return GenerationPage(
                tuple(_summary(row) for row in rows),
                total,
                offset,
                limit,
            )
        finally:
            connection.close()

    def get_generation(self, generation_uid: str) -> GenerationDetail | None:
        """Return prompts, stages and outputs for one canonical generation."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                _DETAIL_QUERY,
                (generation_uid,),
            ).fetchone()
            if row is None:
                return None
            generation_id = int(row["generation_id"])
            return GenerationDetail(
                summary=_summary(row),
                positive_prompt=str(row["positive_prompt"]),
                negative_prompt=str(row["negative_prompt"]),
                revision_uids=_revision_uids(connection, generation_id),
                global_policy_revision_uids=_global_policy_revision_uids(
                    connection, generation_id
                ),
                sampler_stages=_sampler_stages(connection, generation_id),
                outputs=_outputs(connection, generation_id),
            )
        finally:
            connection.close()


_SUMMARY_FIELDS = """
    generation.id AS generation_id,
    generation.generation_uid,
    generation.status,
    generation.comfy_prompt_id,
    generation.source,
    generation.model_branch,
    generation.checkpoint,
    generation.workflow_hash,
    generation.created_at,
    generation.submitted_at,
    generation.started_at,
    generation.completed_at,
    generation.raw_metadata_json,
    COUNT(image.id) AS output_count
"""
_SUMMARY_QUERY = f"""
    SELECT {_SUMMARY_FIELDS}
    FROM generations AS generation
    LEFT JOIN images AS image
        ON image.generation_id = generation.id
       AND image.deleted_at IS NULL
"""
_DETAIL_QUERY = f"""
    SELECT {_SUMMARY_FIELDS},
           positive_prompt.text AS positive_prompt,
           negative_prompt.text AS negative_prompt
    FROM generations AS generation
    JOIN prompts AS positive_prompt
        ON positive_prompt.id = generation.positive_prompt_id
    JOIN prompts AS negative_prompt
        ON negative_prompt.id = generation.negative_prompt_id
    LEFT JOIN images AS image
        ON image.generation_id = generation.id
       AND image.deleted_at IS NULL
    WHERE generation.generation_uid = ?
    GROUP BY generation.id
"""


def _summary(row: sqlite3.Row) -> GenerationSummary:
    metadata = _metadata(row["raw_metadata_json"])
    return GenerationSummary(
        generation_uid=str(row["generation_uid"]),
        status=str(row["status"]),
        prompt_id=_text(row["comfy_prompt_id"]),
        source=str(row["source"]),
        model=str(row["model_branch"]),
        checkpoint=str(row["checkpoint"]),
        blueprint_uid=_metadata_text(metadata, "blueprint_uid"),
        blueprint_version=_metadata_int(metadata, "blueprint_version"),
        graph_hash=_text(row["workflow_hash"]),
        created_at=str(row["created_at"]),
        submitted_at=_text(row["submitted_at"]),
        started_at=_text(row["started_at"]),
        completed_at=_text(row["completed_at"]),
        output_count=int(row["output_count"]),
        failure_reason=_metadata_text(metadata, "last_error"),
    )


def _revision_uids(
    connection: sqlite3.Connection,
    generation_id: int,
) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT revision.revision_uid
        FROM generations AS generation
        JOIN prompt_composition_revisions AS membership
          ON membership.composition_id = generation.prompt_composition_id
        JOIN prompt_revisions AS revision ON revision.id = membership.revision_id
        WHERE generation.id = ?
        ORDER BY membership.position, membership.slot
        """,
        (generation_id,),
    ).fetchall()
    return tuple(str(row["revision_uid"]) for row in rows)


def _sampler_stages(
    connection: sqlite3.Connection,
    generation_id: int,
) -> tuple[GenerationStageSummary, ...]:
    rows = connection.execute(
        """
        SELECT role, node_id, stage_order, seed, steps, cfg, sampler,
               scheduler, denoise
        FROM generation_sampler_stages
        WHERE generation_id = ?
        ORDER BY stage_order, node_id
        """,
        (generation_id,),
    ).fetchall()
    return tuple(
        GenerationStageSummary(
            role=str(row["role"]),
            node_id=str(row["node_id"]),
            order=int(row["stage_order"]),
            seed=_integer(row["seed"]),
            steps=_integer(row["steps"]),
            cfg=_floating(row["cfg"]),
            sampler=_text(row["sampler"]),
            scheduler=_text(row["scheduler"]),
            denoise=_floating(row["denoise"]),
        )
        for row in rows
    )


def _global_policy_revision_uids(
    connection: sqlite3.Connection,
    generation_id: int,
) -> tuple[str, ...]:
    rows = connection.execute(
        """
        SELECT policy.policy_uid
        FROM generation_global_prompt_policies AS usage
        JOIN global_prompt_policies AS policy ON policy.id = usage.policy_id
        WHERE usage.generation_id = ?
        ORDER BY usage.position
        """,
        (generation_id,),
    ).fetchall()
    return tuple(str(row["policy_uid"]) for row in rows)


def _outputs(
    connection: sqlite3.Connection,
    generation_id: int,
) -> tuple[GenerationOutputSummary, ...]:
    rows = connection.execute(
        """
        SELECT image_uid, output_role, output_node_id, output_index,
               content_hash
        FROM images
        WHERE generation_id = ? AND deleted_at IS NULL
        ORDER BY output_node_id, output_index, image_uid
        """,
        (generation_id,),
    ).fetchall()
    return tuple(
        GenerationOutputSummary(
            image_uid=str(row["image_uid"]),
            role=str(row["output_role"]),
            node_id=str(row["output_node_id"]),
            output_index=int(row["output_index"]),
            content_hash=str(row["content_hash"] or ""),
        )
        for row in rows
    )


def _metadata(value: object) -> dict[str, object]:
    try:
        parsed = json.loads(str(value or "{}"))
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _metadata_text(metadata: dict[str, object], key: str) -> str | None:
    return _text(metadata.get(key))


def _metadata_int(metadata: dict[str, object], key: str) -> int | None:
    value = metadata.get(key)
    return int(value) if isinstance(value, int) else None


def _text(value: object) -> str | None:
    return str(value) if value is not None and str(value).strip() else None


def _integer(value: object) -> int | None:
    return int(str(value)) if value is not None else None


def _floating(value: object) -> float | None:
    return float(str(value)) if value is not None else None
