"""SQLite facts adapter for image-to-generator handoffs."""

from __future__ import annotations

import json
from pathlib import Path

from comfyreview.application.generation_queries import GenerationStageSummary
from comfyreview.application.image_generator_handoff import (
    ImageGenerationFacts,
    ImageLoraSnapshot,
)
from comfyreview.repositories.sqlite.connection import connect_read_only


class SqliteImageGeneratorHandoffRepository:
    """Load normalized sampler, LoRA and workflow provenance facts."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_generation_facts(
        self, generation_uid: str
    ) -> ImageGenerationFacts | None:
        """Return exact stored generation facts without policy decisions."""
        with connect_read_only(self._database_path, rows=True) as connection:
            generation = connection.execute(
                "SELECT id, workflow_json FROM generations "
                "WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if generation is None:
                return None
            generation_id = int(generation["id"])
            stages = connection.execute(
                """
                SELECT role, node_id, stage_order, seed, steps, cfg,
                       sampler, scheduler, denoise
                FROM generation_sampler_stages
                WHERE generation_id = ?
                ORDER BY stage_order, node_id
                """,
                (generation_id,),
            ).fetchall()
            loras = connection.execute(
                """
                SELECT selection.position, selection.lora_name,
                       selection.lora_uid, revision.revision_uid,
                       selection.model_strength_milli,
                       selection.clip_strength_milli,
                       selection.content_level_snapshot
                FROM generation_loras AS selection
                LEFT JOIN lora_revisions AS revision
                  ON revision.id = selection.lora_revision_id
                WHERE selection.generation_id = ?
                ORDER BY selection.position
                """,
                (generation_id,),
            ).fetchall()
        workflow = self._workflow(generation["workflow_json"])
        return ImageGenerationFacts(
            sampler_stages=tuple(
                GenerationStageSummary(
                    role=str(row["role"]),
                    node_id=str(row["node_id"]),
                    order=int(row["stage_order"]),
                    seed=self._integer(row["seed"]),
                    steps=self._integer(row["steps"]),
                    cfg=self._floating(row["cfg"]),
                    sampler=self._text(row["sampler"]),
                    scheduler=self._text(row["scheduler"]),
                    denoise=self._floating(row["denoise"]),
                )
                for row in stages
            ),
            loras=tuple(
                ImageLoraSnapshot(
                    lora_uid=self._text(row["lora_uid"]),
                    revision_uid=self._text(row["revision_uid"]),
                    provider_name=str(row["lora_name"]),
                    position=int(row["position"]),
                    model_strength_milli=int(row["model_strength_milli"]),
                    clip_strength_milli=int(row["clip_strength_milli"]),
                    content_level=self._text(row["content_level_snapshot"]),
                    model_effective=False,
                    clip_effective=False,
                )
                for row in loras
            ),
            workflow_graph=workflow,
        )

    @staticmethod
    def _workflow(value: object) -> dict[str, object]:
        try:
            decoded = json.loads(str(value or "{}"))
        except json.JSONDecodeError:
            return {}
        return decoded if isinstance(decoded, dict) else {}

    @staticmethod
    def _text(value: object) -> str | None:
        return str(value) if value is not None and str(value).strip() else None

    @staticmethod
    def _integer(value: object) -> int | None:
        return int(str(value)) if value is not None else None

    @staticmethod
    def _floating(value: object) -> float | None:
        return float(str(value)) if value is not None else None
