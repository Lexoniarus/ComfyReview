"""Canonical SQLite persistence for native generation lifecycle state."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from comfyreview.application import (
    ContentLevel,
    GenerationPromptGroup,
    GenerationRecord,
    PreparedGeneration,
    PromptCompositionMembership,
    infer_content_level,
    prompt_composition_identity,
    prompt_revision_identity,
)
from comfyreview.application.content_classification import (
    PromptContentLevelPolicy,
)
from comfyreview.domain import parse_prompt_atoms, render_prompt_atom_usages
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


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
                    "canvas": (
                        {
                            "width": generation.request.canvas.width,
                            "height": generation.request.canvas.height,
                        }
                        if generation.request.canvas is not None
                        else None
                    ),
                    "geometry": (
                        {
                            "output_tier": generation.request.geometry.output_tier.value,
                            "output_width": generation.request.geometry.output_width,
                            "output_height": generation.request.geometry.output_height,
                        }
                        if generation.request.geometry is not None
                        else None
                    ),
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
                    loras_json, image_width, image_height, output_tier,
                    output_width, output_height,
                    positive_prompt_id, negative_prompt_id,
                    source, raw_metadata_json, workflow_json, workflow_hash,
                    status, prompt_composition_id
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
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
                    self._loras_json(generation),
                    (
                        generation.request.canvas.width
                        if generation.request.canvas is not None
                        else None
                    ),
                    (
                        generation.request.canvas.height
                        if generation.request.canvas is not None
                        else None
                    ),
                    (
                        generation.request.geometry.output_tier.value
                        if generation.request.geometry is not None
                        else None
                    ),
                    (
                        generation.request.geometry.output_width
                        if generation.request.geometry is not None
                        else None
                    ),
                    (
                        generation.request.geometry.output_height
                        if generation.request.geometry is not None
                        else None
                    ),
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
            self._persist_prompt_groups(
                connection,
                generation_id,
                generation.generation_uid,
                generation.request.prompt.prompt_groups,
            )
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
            connection.executemany(
                """
                INSERT INTO generation_loras(
                    generation_id, position, lora_name, lora_uid,
                    lora_revision_id, content_level_snapshot,
                    model_strength_milli, clip_strength_milli
                ) VALUES (
                    ?, ?, ?, ?,
                    (SELECT id FROM lora_revisions WHERE revision_uid = ?),
                    ?, ?, ?
                )
                """,
                tuple(
                    (
                        generation_id,
                        lora.position,
                        lora.name,
                        lora.lora_uid,
                        lora.revision_uid,
                        lora.content_level,
                        lora.model_strength_milli,
                        lora.clip_strength_milli,
                    )
                    for lora in generation.request.loras
                ),
            )
            self._update_inferred_content_level(
                connection, generation_id, generation
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

    @staticmethod
    def _loras_json(generation: PreparedGeneration) -> str:
        return json.dumps(
            [
                {
                    "name": lora.name,
                    "strength_model": lora.model_strength_milli / 1000,
                    "strength_clip": lora.clip_strength_milli / 1000,
                }
                for lora in generation.request.loras
            ],
            ensure_ascii=False,
            separators=(",", ":"),
        )

    @staticmethod
    def _update_inferred_content_level(
        connection: sqlite3.Connection,
        generation_id: int,
        generation: PreparedGeneration,
    ) -> None:
        if not generation.request.prompt.revision_uids:
            component_levels: tuple[ContentLevel, ...] = ()
        else:
            placeholders = ", ".join(
                "?" for _uid in generation.request.prompt.revision_uids
            )
            rows = connection.execute(
                f"""
                SELECT component.tags
                FROM prompt_revisions AS revision
                JOIN prompt_components AS component
                  ON component.id = revision.component_id
                WHERE revision.revision_uid IN ({placeholders})
                """,
                generation.request.prompt.revision_uids,
            ).fetchall()
            levels: list[ContentLevel] = []
            policy = PromptContentLevelPolicy()
            for (payload,) in rows:
                try:
                    decoded = json.loads(str(payload or "[]"))
                except json.JSONDecodeError:
                    decoded = []
                if isinstance(decoded, list):
                    levels.append(
                        policy.read(
                            tuple(str(item) for item in decoded)
                        ).content_level
                    )
            component_levels = tuple(levels)
        lora_levels = tuple(
            ContentLevel(item.content_level)
            for item in generation.request.loras
            if item.content_level is not None
        )
        level = infer_content_level(component_levels, lora_levels)
        connection.execute(
            "UPDATE generations SET inferred_content_level = ? WHERE id = ?",
            (level.value, generation_id),
        )

    def get(self, generation_uid: str) -> GenerationRecord:
        """Return one current lifecycle record."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return self._get(connection, generation_uid)
        finally:
            connection.close()

    def list_active(self, limit: int) -> tuple[GenerationRecord, ...]:
        """Return bounded non-terminal native generations oldest first."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT generation_uid, status, comfy_prompt_id
                FROM generations
                WHERE source = 'native_comfyui'
                  AND status IN ('prepared', 'submitting', 'submitted', 'running')
                ORDER BY id
                LIMIT ?
                """,
                (max(1, int(limit)),),
            ).fetchall()
            return tuple(
                GenerationRecord(
                    generation_uid=str(row["generation_uid"]),
                    status=str(row["status"]),
                    prompt_id=(
                        str(row["comfy_prompt_id"])
                        if row["comfy_prompt_id"]
                        else None
                    ),
                )
                for row in rows
            )
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
            elif target in {"submitted", "running", "completed"}:
                assignments.append(
                    "raw_metadata_json = json_remove("
                    "COALESCE(raw_metadata_json, '{}'), '$.last_error')"
                )
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

    @classmethod
    def _persist_prompt_groups(
        cls,
        connection: sqlite3.Connection,
        generation_id: int,
        generation_uid: str,
        groups: tuple[GenerationPromptGroup, ...],
    ) -> None:
        for group in groups:
            source = connection.execute(
                """
                SELECT component.id AS component_id,
                       component.kind AS kind,
                       revision.id AS revision_id
                FROM prompt_components AS component
                JOIN prompt_revisions AS revision
                  ON revision.component_id = component.id
                WHERE component.component_uid = ?
                  AND revision.revision_uid = ?
                """,
                (group.component_uid, group.revision_uid),
            ).fetchone()
            if source is None or str(source["kind"]) != group.kind:
                raise RuntimeError(
                    "Prompt group source revision does not match"
                )
            _revision_uid, content_hash = prompt_revision_identity(
                group.component_uid,
                render_prompt_atom_usages(group.positive_atoms),
                render_prompt_atom_usages(group.negative_atoms),
            )
            candidate_id = cls._candidate_id(
                connection,
                group,
                int(source["component_id"]),
                int(source["revision_id"]),
                content_hash,
            )
            group_uid = (
                "prompt-group-"
                + hashlib.sha256(
                    (
                        f"{generation_uid}\0{group.position}\0"
                        f"{group.component_uid}\0{content_hash}"
                    ).encode()
                ).hexdigest()
            )
            cursor = connection.execute(
                """
                INSERT INTO generation_prompt_groups(
                    group_uid, generation_id, component_id,
                    source_revision_id, candidate_id, kind, position,
                    content_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    group_uid,
                    generation_id,
                    int(source["component_id"]),
                    int(source["revision_id"]),
                    candidate_id,
                    group.kind,
                    group.position,
                    content_hash,
                ),
            )
            group_id = int(cursor.lastrowid or 0)
            for scope, atoms in (
                ("pos", group.positive_atoms),
                ("neg", group.negative_atoms),
            ):
                for position, atom in enumerate(atoms):
                    atom_id = cls._ensure_atom_id(connection, atom.text)
                    connection.execute(
                        """
                        INSERT INTO generation_prompt_group_atom_usages(
                            group_id, atom_id, scope, position, weight_milli
                        ) VALUES (?, ?, ?, ?, ?)
                        """,
                        (
                            group_id,
                            atom_id,
                            scope,
                            position,
                            atom.weight_milli,
                        ),
                    )

    @classmethod
    def _candidate_id(
        cls,
        connection: sqlite3.Connection,
        group: GenerationPromptGroup,
        component_id: int,
        revision_id: int,
        content_hash: str,
    ) -> int | None:
        if group.candidate_uid is None:
            return None
        candidate = connection.execute(
            """
            SELECT id, component_id, source_revision_id, content_hash
            FROM prompt_component_candidates
            WHERE candidate_uid = ?
            """,
            (group.candidate_uid,),
        ).fetchone()
        if candidate is None:
            raise RuntimeError("Unknown prompt component candidate")
        if (
            int(candidate["component_id"]) != component_id
            or int(candidate["source_revision_id"]) != revision_id
            or str(candidate["content_hash"]) != content_hash
        ):
            raise RuntimeError("Prompt candidate does not match its group")
        expected = tuple(
            (scope, position, atom.text, atom.weight_milli)
            for scope, atoms in (
                ("pos", group.positive_atoms),
                ("neg", group.negative_atoms),
            )
            for position, atom in enumerate(atoms)
        )
        observed = tuple(
            (
                str(row["scope"]),
                int(row["position"]),
                str(row["canonical_text"]),
                int(row["weight_milli"]),
            )
            for row in connection.execute(
                """
                SELECT usage.scope, usage.position, atom.canonical_text,
                       usage.weight_milli
                FROM prompt_candidate_atom_usages AS usage
                JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                WHERE usage.candidate_id = ?
                ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                         usage.position
                """,
                (int(candidate["id"]),),
            ).fetchall()
        )
        if observed != expected:
            raise RuntimeError("Prompt candidate atoms do not match its group")
        return int(candidate["id"])

    @staticmethod
    def _ensure_atom_id(
        connection: sqlite3.Connection,
        canonical_text: str,
    ) -> int:
        connection.execute(
            "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
            (canonical_text,),
        )
        row = connection.execute(
            "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
            (canonical_text,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Prompt atom could not be persisted")
        return int(row["id"])

    @staticmethod
    def _ensure_composition(
        connection: sqlite3.Connection,
        revision_uids: tuple[str, ...],
    ) -> int | None:
        if not revision_uids:
            return None
        revisions: list[tuple[int, PromptCompositionMembership]] = []
        for position, revision_uid in enumerate(revision_uids):
            revision = connection.execute(
                """
                SELECT revision.id, component.kind
                FROM prompt_revisions AS revision
                JOIN prompt_components AS component
                    ON component.id = revision.component_id
                WHERE revision.revision_uid = ?
                """,
                (revision_uid,),
            ).fetchone()
            if revision is None:
                raise RuntimeError(f"Unknown prompt revision: {revision_uid}")
            revisions.append(
                (
                    int(revision["id"]),
                    PromptCompositionMembership(
                        slot=str(revision["kind"]),
                        position=position,
                        revision_uid=revision_uid,
                    ),
                )
            )
        composition_uid = prompt_composition_identity(
            membership for _revision_id, membership in revisions
        )
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
            """
            SELECT revision.revision_uid, membership.slot,
                   membership.position
            FROM prompt_composition_revisions AS membership
            JOIN prompt_revisions AS revision
                ON revision.id = membership.revision_id
            WHERE membership.composition_id = ?
            ORDER BY membership.position
            """,
            (composition_id,),
        ).fetchall()
        expected = tuple(
            (
                membership.revision_uid,
                membership.slot,
                membership.position,
            )
            for _revision_id, membership in revisions
        )
        observed = tuple(
            (str(row["revision_uid"]), str(row["slot"]), int(row["position"]))
            for row in existing
        )
        if observed and observed != expected:
            raise RuntimeError("Prompt composition identity collision")
        if not observed:
            for revision_id, membership in revisions:
                connection.execute(
                    """
                    INSERT INTO prompt_composition_revisions(
                        composition_id, revision_id, slot, position
                    ) VALUES (?, ?, ?, ?)
                    """,
                    (
                        composition_id,
                        revision_id,
                        membership.slot,
                        membership.position,
                    ),
                )
        return composition_id
