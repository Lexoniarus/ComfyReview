"""SQLite persistence for the canonical Playground generator state."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.generator_state import (
    GeneratorLoraState,
    GeneratorPromptSelection,
    GeneratorStateSnapshot,
    GeneratorStateValidationError,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteGeneratorStateRepository:
    """Atomically persist the normalized singleton Generator state."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def get(self) -> GeneratorStateSnapshot | None:
        """Return the current normalized state when it exists."""
        with connect_existing(self._database_path, rows=True) as connection:
            row = connection.execute(
                """
                SELECT checkpoint, sampler, scheduler, seed_mode, seed,
                       steps_min, steps_max, cfg_min_milli, cfg_max_milli,
                       cfg_step_milli, denoise_milli, batch_runs,
                       aspect_format, resolution_class
                FROM playground_generator_state
                WHERE singleton_id = 1
                """
            ).fetchone()
            if row is None:
                return None
            return GeneratorStateSnapshot(
                selections=self._selections(connection),
                loras=self._loras(connection),
                checkpoint=str(row["checkpoint"]),
                sampler=str(row["sampler"]),
                scheduler=str(row["scheduler"]),
                seed_mode=str(row["seed_mode"]),  # type: ignore[arg-type]
                seed=int(row["seed"]),
                steps_min=int(row["steps_min"]),
                steps_max=int(row["steps_max"]),
                cfg_min_milli=int(row["cfg_min_milli"]),
                cfg_max_milli=int(row["cfg_max_milli"]),
                cfg_step_milli=int(row["cfg_step_milli"]),
                denoise_milli=int(row["denoise_milli"]),
                batch_runs=int(row["batch_runs"]),
                aspect_format=str(row["aspect_format"]),
                resolution_class=str(row["resolution_class"]),
            )

    def save(self, state: GeneratorStateSnapshot) -> GeneratorStateSnapshot:
        """Replace render, prompt, and LoRA rows in one transaction."""
        with connect_existing(self._database_path) as connection:
            connection.execute("BEGIN IMMEDIATE")
            prompt_references = tuple(
                self._prompt_reference(connection, selection)
                for selection in state.selections
            )
            lora_references = tuple(
                self._lora_reference(connection, lora) for lora in state.loras
            )
            connection.execute(
                """
                INSERT INTO playground_generator_state(
                    singleton_id, checkpoint, sampler, scheduler, seed_mode,
                    seed, steps_min, steps_max, cfg_min_milli,
                    cfg_max_milli, cfg_step_milli, denoise_milli, batch_runs,
                    aspect_format, resolution_class
                ) VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(singleton_id) DO UPDATE SET
                    checkpoint = excluded.checkpoint,
                    sampler = excluded.sampler,
                    scheduler = excluded.scheduler,
                    seed_mode = excluded.seed_mode,
                    seed = excluded.seed,
                    steps_min = excluded.steps_min,
                    steps_max = excluded.steps_max,
                    cfg_min_milli = excluded.cfg_min_milli,
                    cfg_max_milli = excluded.cfg_max_milli,
                    cfg_step_milli = excluded.cfg_step_milli,
                    denoise_milli = excluded.denoise_milli,
                    batch_runs = excluded.batch_runs,
                    aspect_format = excluded.aspect_format,
                    resolution_class = excluded.resolution_class,
                    updated_at = datetime('now')
                """,
                (
                    state.checkpoint,
                    state.sampler,
                    state.scheduler,
                    state.seed_mode,
                    state.seed,
                    state.steps_min,
                    state.steps_max,
                    state.cfg_min_milli,
                    state.cfg_max_milli,
                    state.cfg_step_milli,
                    state.denoise_milli,
                    state.batch_runs,
                    state.aspect_format,
                    state.resolution_class,
                ),
            )
            connection.execute(
                "DELETE FROM playground_generator_prompt_selections "
                "WHERE singleton_id = 1"
            )
            connection.executemany(
                """
                INSERT INTO playground_generator_prompt_selections(
                    singleton_id, position, kind, mode,
                    component_id, revision_id, candidate_id
                ) VALUES (1, ?, ?, ?, ?, ?, ?)
                """,
                tuple(
                    (
                        position,
                        selection.kind,
                        selection.mode,
                        component_id,
                        revision_id,
                        candidate_id,
                    )
                    for position, (
                        selection,
                        component_id,
                        revision_id,
                        candidate_id,
                    ) in enumerate(prompt_references)
                ),
            )
            connection.execute(
                "DELETE FROM playground_generator_loras WHERE singleton_id = 1"
            )
            connection.executemany(
                """
                INSERT INTO playground_generator_loras(
                    singleton_id, position, lora_definition_id,
                    lora_revision_id, model_strength_milli,
                    clip_strength_milli
                ) VALUES (1, ?, ?, ?, ?, ?)
                """,
                tuple(
                    (
                        position,
                        definition_id,
                        revision_id,
                        lora.model_strength_milli,
                        lora.clip_strength_milli,
                    )
                    for position, (
                        lora,
                        definition_id,
                        revision_id,
                    ) in enumerate(lora_references)
                ),
            )
            connection.commit()
        saved = self.get()
        if saved is None:  # pragma: no cover - protected by the transaction
            raise RuntimeError(  # pragma: no cover
                "generator state was not persisted"
            )
        return saved

    @staticmethod
    def _prompt_reference(
        connection: sqlite3.Connection,
        selection: GeneratorPromptSelection,
    ) -> tuple[
        GeneratorPromptSelection,
        int | None,
        int | None,
        int | None,
    ]:
        if selection.mode != "fixed":
            return selection, None, None, None
        row = connection.execute(
            """
            SELECT component.id, revision.id, candidate.id
            FROM prompt_components AS component
            JOIN prompt_revisions AS revision
              ON revision.component_id = component.id
            LEFT JOIN prompt_component_candidates AS candidate
              ON candidate.candidate_uid = ?
             AND candidate.component_id = component.id
             AND candidate.source_revision_id = revision.id
            WHERE component.component_uid = ? AND revision.revision_uid = ?
            """,
            (
                selection.candidate_uid,
                selection.component_uid,
                selection.revision_uid,
            ),
        ).fetchone()
        if row is None:
            raise GeneratorStateValidationError(
                f"unknown prompt selection revision: {selection.revision_uid}"
            )
        if selection.candidate_uid is not None and row[2] is None:
            raise GeneratorStateValidationError(
                f"unknown prompt candidate: {selection.candidate_uid}"
            )
        return (
            selection,
            int(row[0]),
            int(row[1]),
            int(row[2]) if row[2] is not None else None,
        )

    @staticmethod
    def _lora_reference(
        connection: sqlite3.Connection,
        lora: GeneratorLoraState,
    ) -> tuple[GeneratorLoraState, int, int]:
        row = connection.execute(
            """
            SELECT definition.id, revision.id
            FROM lora_definitions AS definition
            JOIN lora_revisions AS revision
              ON revision.lora_definition_id = definition.id
            WHERE definition.lora_uid = ? AND revision.revision_uid = ?
            """,
            (lora.lora_uid, lora.revision_uid),
        ).fetchone()
        if row is None:
            raise GeneratorStateValidationError(
                f"unknown LoRA revision: {lora.revision_uid}"
            )
        return lora, int(row[0]), int(row[1])

    @staticmethod
    def _selections(
        connection: sqlite3.Connection,
    ) -> tuple[GeneratorPromptSelection, ...]:
        rows = connection.execute(
            """
            SELECT selection.kind, selection.mode,
                   component.component_uid, revision.revision_uid,
                   candidate.candidate_uid
            FROM playground_generator_prompt_selections AS selection
            LEFT JOIN prompt_components AS component
              ON component.id = selection.component_id
            LEFT JOIN prompt_revisions AS revision
              ON revision.id = selection.revision_id
            LEFT JOIN prompt_component_candidates AS candidate
              ON candidate.id = selection.candidate_id
            WHERE selection.singleton_id = 1
            ORDER BY selection.position
            """
        ).fetchall()
        return tuple(
            GeneratorPromptSelection(
                kind=str(row[0]),  # type: ignore[arg-type]
                mode=str(row[1]),  # type: ignore[arg-type]
                component_uid=str(row[2]) if row[2] is not None else None,
                revision_uid=str(row[3]) if row[3] is not None else None,
                candidate_uid=str(row[4]) if row[4] is not None else None,
            )
            for row in rows
        )

    @staticmethod
    def _loras(
        connection: sqlite3.Connection,
    ) -> tuple[GeneratorLoraState, ...]:
        rows = connection.execute(
            """
            SELECT definition.lora_uid, revision.revision_uid,
                   selection.model_strength_milli,
                   selection.clip_strength_milli
            FROM playground_generator_loras AS selection
            JOIN lora_definitions AS definition
              ON definition.id = selection.lora_definition_id
            JOIN lora_revisions AS revision
              ON revision.id = selection.lora_revision_id
            WHERE selection.singleton_id = 1
            ORDER BY selection.position
            """
        ).fetchall()
        return tuple(
            GeneratorLoraState(
                lora_uid=str(row[0]),
                revision_uid=str(row[1]),
                model_strength_milli=int(row[2]),
                clip_strength_milli=int(row[3]),
            )
            for row in rows
        )
