"""Canonical SQLite persistence for native generation lifecycle state."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from comfyreview.application import (
    GenerationRecord,
    PreparedGeneration,
)
from comfyreview.domain import parse_prompt_atoms
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteGenerationRepository:
    """Own short transactions for canonical generation state transitions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def prepare(self, generation: PreparedGeneration) -> GenerationRecord:
        """Persist request snapshots, composition and compiled provenance."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            positive_id = self._ensure_prompt(
                connection,
                scope="pos",
                text=generation.request.prompt.positive_text,
            )
            negative_id = self._ensure_prompt(
                connection,
                scope="neg",
                text=generation.request.prompt.negative_text,
            )
            composition_id = self._ensure_composition(
                connection,
                generation.request.prompt.revision_uids,
            )
            metadata = json.dumps(
                {
                    "blueprint_uid": generation.compiled_workflow.blueprint_uid,
                    "blueprint_version": generation.compiled_workflow.blueprint_version,
                    "revision_uids": generation.request.prompt.revision_uids,
                    "output_policy": {
                        "output_subdirectory": generation.request.output_policy.output_subdirectory,
                        "filename_prefix": generation.request.output_policy.filename_prefix,
                        "expected_roles": generation.request.output_policy.expected_roles,
                    },
                    "output_bindings": [
                        {"role": binding.role, "node_id": binding.node_id}
                        for binding in generation.compiled_workflow.output_bindings
                    ],
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            cursor = connection.execute(
                """
                INSERT INTO generations(
                    generation_uid, model_branch, checkpoint, combo_key,
                    seed, steps, cfg, sampler, scheduler, denoise,
                    loras_json, positive_prompt_id, negative_prompt_id,
                    source, raw_metadata_json, workflow_json, workflow_hash,
                    status, prompt_composition_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'native_comfyui', ?, ?, ?, 'prepared', ?
                )
                """,
                (
                    generation.generation_uid,
                    generation.request.model_branch,
                    generation.request.checkpoint or "",
                    generation.request.combo_key,
                    self._primary_stage_value(generation, "seed"),
                    self._primary_stage_value(generation, "steps"),
                    self._primary_stage_value(generation, "cfg"),
                    self._primary_stage_value(generation, "sampler"),
                    self._primary_stage_value(generation, "scheduler"),
                    self._primary_stage_value(generation, "denoise"),
                    generation.request.loras_json,
                    positive_id,
                    negative_id,
                    metadata,
                    json.dumps(
                        generation.compiled_workflow.graph,
                        ensure_ascii=False,
                        sort_keys=True,
                        separators=(",", ":"),
                    ),
                    generation.compiled_workflow.graph_hash,
                    composition_id,
                ),
            )
            generation_id = int(cursor.lastrowid or 0)
            for order, stage in enumerate(
                generation.compiled_workflow.sampler_stages
            ):
                connection.execute(
                    """
                    INSERT INTO generation_sampler_stages(
                        generation_id, node_id, stage_order, role, seed,
                        steps, cfg, sampler, scheduler, denoise, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'workflow_compiler')
                    """,
                    (
                        generation_id,
                        stage.node_id,
                        order,
                        stage.role,
                        stage.seed,
                        stage.steps,
                        stage.cfg,
                        stage.sampler,
                        stage.scheduler,
                        stage.denoise,
                    ),
                )
            connection.commit()
            return GenerationRecord(
                generation.generation_uid, "prepared", None
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, generation_uid: str) -> GenerationRecord:
        """Return one current lifecycle record."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            return self._get(connection, generation_uid)
        finally:
            connection.close()

    def mark_submitting(self, generation_uid: str) -> GenerationRecord:
        """Move prepared work into submitting state."""
        return self._transition(generation_uid, "submitting", ("prepared",))

    def mark_submitted(
        self,
        generation_uid: str,
        prompt_id: str,
    ) -> GenerationRecord:
        """Persist external identity and submitted state."""
        return self._transition(
            generation_uid,
            "submitted",
            ("submitting", "reconciliation_required"),
            prompt_id=prompt_id,
            timestamp_column="submitted_at",
        )

    def mark_running(self, generation_uid: str) -> GenerationRecord:
        """Record observed external execution."""
        return self._transition(
            generation_uid,
            "running",
            ("submitted", "running", "reconciliation_required"),
            timestamp_column="started_at",
        )

    def mark_completed(self, generation_uid: str) -> GenerationRecord:
        """Record successful external completion."""
        return self._transition(
            generation_uid,
            "completed",
            ("submitted", "running", "reconciliation_required"),
            timestamp_column="completed_at",
        )

    def mark_failed(
        self,
        generation_uid: str,
        reason: str,
    ) -> GenerationRecord:
        """Record a definitive failure and its normalized reason."""
        return self._transition(
            generation_uid,
            "failed",
            (
                "prepared",
                "submitting",
                "submitted",
                "running",
                "reconciliation_required",
            ),
            reason=reason,
        )

    def mark_reconciliation_required(
        self,
        generation_uid: str,
        prompt_id: str | None,
        reason: str,
    ) -> GenerationRecord:
        """Record an ambiguous external submission outcome."""
        return self._transition(
            generation_uid,
            "reconciliation_required",
            (
                "submitting",
                "submitted",
                "running",
                "reconciliation_required",
            ),
            prompt_id=prompt_id,
            reason=reason,
        )

    def _transition(
        self,
        generation_uid: str,
        target: str,
        expected: tuple[str, ...],
        *,
        prompt_id: str | None = None,
        reason: str | None = None,
        timestamp_column: str | None = None,
    ) -> GenerationRecord:
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = self._get(connection, generation_uid)
            if current.status not in expected:
                raise RuntimeError(
                    f"Invalid generation transition {current.status} -> {target}"
                )
            assignments = ["status = ?"]
            values: list[object] = [target]
            if prompt_id is not None:
                assignments.append("comfy_prompt_id = ?")
                values.append(prompt_id)
            if reason is not None:
                assignments.append(
                    "raw_metadata_json = json_set(COALESCE(raw_metadata_json, '{}'), '$.last_error', ?)"
                )
                values.append(reason)
            if timestamp_column is not None:
                assignments.append(f"{timestamp_column} = datetime('now')")
            values.append(generation_uid)
            connection.execute(
                f"UPDATE generations SET {', '.join(assignments)} WHERE generation_uid = ?",
                values,
            )
            connection.commit()
            return self._get(connection, generation_uid)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _get(
        connection: sqlite3.Connection, generation_uid: str
    ) -> GenerationRecord:
        row = connection.execute(
            "SELECT generation_uid, status, comfy_prompt_id FROM generations WHERE generation_uid = ?",
            (generation_uid,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown generation: {generation_uid}")
        return GenerationRecord(
            generation_uid=str(row["generation_uid"]),
            status=str(row["status"]),
            prompt_id=(
                str(row["comfy_prompt_id"]) if row["comfy_prompt_id"] else None
            ),
        )

    @staticmethod
    def _primary_stage_value(
        generation: PreparedGeneration, field: str
    ) -> object:
        stages = generation.compiled_workflow.sampler_stages
        return getattr(stages[0], field) if stages else None

    def _ensure_prompt(
        self,
        connection: sqlite3.Connection,
        *,
        scope: str,
        text: str,
    ) -> int:
        prompt_text = str(text)
        prompt_hash = hashlib.sha256(
            f"{scope}\0{prompt_text}".encode()
        ).hexdigest()
        connection.execute(
            "INSERT OR IGNORE INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
            (scope, prompt_hash, prompt_text),
        )
        row = connection.execute(
            "SELECT id, text FROM prompts WHERE scope = ? AND prompt_hash = ?",
            (scope, prompt_hash),
        ).fetchone()
        if row is None or str(row["text"]) != prompt_text:
            raise RuntimeError("Prompt identity collision")
        prompt_id = int(row["id"])
        exists = connection.execute(
            "SELECT 1 FROM prompt_memberships WHERE prompt_id = ? LIMIT 1",
            (prompt_id,),
        ).fetchone()
        if exists is None:
            for position, atom in enumerate(parse_prompt_atoms(prompt_text)):
                connection.execute(
                    "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                    (atom.text,),
                )
                atom_row = connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (atom.text,),
                ).fetchone()
                if atom_row is None:
                    raise RuntimeError("Prompt atom could not be persisted")
                connection.execute(
                    """
                    INSERT INTO prompt_memberships(
                        prompt_id, atom_id, position, weight_milli, raw_text
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        prompt_id,
                        int(atom_row["id"]),
                        position,
                        atom.weight_milli,
                        atom.raw_text,
                    ),
                )
        return prompt_id

    @staticmethod
    def _ensure_composition(
        connection: sqlite3.Connection,
        revision_uids: tuple[str, ...],
    ) -> int | None:
        if not revision_uids:
            return None
        digest = hashlib.sha256("\0".join(revision_uids).encode()).hexdigest()
        composition_uid = f"prompt-composition-{digest}"
        connection.execute(
            "INSERT OR IGNORE INTO prompt_compositions(composition_uid) VALUES (?)",
            (composition_uid,),
        )
        composition_row = connection.execute(
            "SELECT id FROM prompt_compositions WHERE composition_uid = ?",
            (composition_uid,),
        ).fetchone()
        if composition_row is None:
            raise RuntimeError("Prompt composition could not be persisted")
        composition_id = int(composition_row["id"])
        existing = connection.execute(
            "SELECT COUNT(*) FROM prompt_composition_revisions WHERE composition_id = ?",
            (composition_id,),
        ).fetchone()
        if existing is not None and int(existing[0]) == 0:
            for position, revision_uid in enumerate(revision_uids):
                revision = connection.execute(
                    "SELECT id FROM prompt_revisions WHERE revision_uid = ?",
                    (revision_uid,),
                ).fetchone()
                if revision is None:
                    raise RuntimeError(
                        f"Unknown prompt revision: {revision_uid}"
                    )
                connection.execute(
                    """
                    INSERT INTO prompt_composition_revisions(
                        composition_id, revision_id, slot, position
                    ) VALUES (?, ?, 'selected', ?)
                    """,
                    (composition_id, int(revision["id"]), position),
                )
        return composition_id
