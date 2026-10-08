"""SQLite facts adapter for image-to-generator handoffs."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.generation_queries import GenerationStageSummary
from comfyreview.application.image_generator_handoff import (
    ImageGenerationFacts,
    ImageLoraSnapshot,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite.connection import connect_read_only


class SqliteImageGeneratorHandoffRepository:
    """Load normalized sampler and LoRA facts for generator handoff."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_generation_facts(
        self, generation_uid: str
    ) -> ImageGenerationFacts | None:
        """Return exact stored generation facts without policy decisions."""
        with connect_read_only(self._database_path, rows=True) as connection:
            generation = connection.execute(
                "SELECT id FROM generations WHERE generation_uid = ?",
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
            lora_atoms = connection.execute(
                """
                SELECT usage.scope, selection.position AS group_position,
                       usage.position AS atom_position, atom.canonical_text,
                       usage.weight_milli
                FROM generation_loras AS selection
                JOIN lora_revision_atom_usages AS usage
                  ON usage.revision_id = selection.lora_revision_id
                JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                WHERE selection.generation_id = ?
                ORDER BY group_position, atom_position
                """,
                (generation_id,),
            ).fetchall()
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
                    model_effective=int(row["model_strength_milli"]) != 0,
                    clip_effective=int(row["clip_strength_milli"]) != 0,
                )
                for row in loras
            ),
            lora_positive_atoms=self._atoms(lora_atoms, "pos"),
            lora_negative_atoms=self._atoms(lora_atoms, "neg"),
        )

    @staticmethod
    def _atoms(
        rows: list[sqlite3.Row], scope: str
    ) -> tuple[PromptAtomUsage, ...]:
        return tuple(
            PromptAtomUsage(
                str(row["canonical_text"]), int(row["weight_milli"])
            )
            for row in rows
            if str(row["scope"]) == scope
        )

    @staticmethod
    def _text(value: object) -> str | None:
        return str(value) if value is not None and str(value).strip() else None

    @staticmethod
    def _integer(value: object) -> int | None:
        return int(str(value)) if value is not None else None

    @staticmethod
    def _floating(value: object) -> float | None:
        return float(str(value)) if value is not None else None
