"""Card-runtime adapters for the existing generation application ports."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from enum import Enum
from pathlib import Path

from comfyreview.application.generation import (
    GenerationRecord,
    PreparedGeneration,
)
from comfyreview.application.generation_outputs import (
    GenerationOutput,
    GenerationOutputRecoveryPlan,
)
from comfyreview.application.workflow_compilation import CompiledOutputBinding
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardGenerationRepository:
    """Persist Card-only generation lifecycle transitions in the POC store."""

    _ACTIVE = ("prepared", "submitting", "submitted", "running")

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def prepare(self, generation: PreparedGeneration) -> GenerationRecord:
        """Persist one prepared Card generation without canonical DB writes."""
        request = generation.request
        compiled = generation.compiled_workflow
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            connection.execute(
                """
                INSERT INTO card_generations(
                    generation_uid, status, prepared_request_json,
                    compiled_workflow_json, workflow_hash,
                    output_policy_json, output_bindings_json
                ) VALUES (?, 'prepared', ?, ?, ?, ?, ?)
                """,
                (
                    generation.generation_uid,
                    _json(asdict(request)),
                    _json(compiled.graph),
                    compiled.graph_hash,
                    _json(asdict(request.output_policy)),
                    _json(
                        [
                            {"role": item.role, "node_id": item.node_id}
                            for item in compiled.output_bindings
                        ]
                    ),
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
        """Return one Card generation lifecycle record."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            return self._get(connection, generation_uid)
        finally:
            connection.close()

    def list_active(self, limit: int) -> tuple[GenerationRecord, ...]:
        """Return bounded active Card generations oldest first."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            placeholders = ", ".join("?" for _ in self._ACTIVE)
            rows = connection.execute(
                f"""
                SELECT generation_uid, status, prompt_id
                FROM card_generations
                WHERE status IN ({placeholders})
                ORDER BY created_at, generation_uid
                LIMIT ?
                """,
                (*self._ACTIVE, max(1, int(limit))),
            ).fetchall()
            return tuple(self._record(row) for row in rows)
        finally:
            connection.close()

    def mark_submitting(self, generation_uid: str) -> GenerationRecord:
        return self._transition(generation_uid, "submitting", ("prepared",))

    def mark_submitted(
        self, generation_uid: str, prompt_id: str
    ) -> GenerationRecord:
        return self._transition(
            generation_uid,
            "submitted",
            ("submitting", "reconciliation_required"),
            prompt_id=prompt_id,
        )

    def mark_running(self, generation_uid: str) -> GenerationRecord:
        return self._transition(
            generation_uid,
            "running",
            ("submitted", "running", "reconciliation_required"),
        )

    def mark_completed(self, generation_uid: str) -> GenerationRecord:
        return self._transition(
            generation_uid,
            "completed",
            ("submitted", "running", "reconciliation_required"),
        )

    def mark_failed(
        self, generation_uid: str, reason: str
    ) -> GenerationRecord:
        return self._transition(
            generation_uid,
            "failed",
            (*self._ACTIVE, "reconciliation_required"),
            reason=reason,
        )

    def mark_reconciliation_required(
        self,
        generation_uid: str,
        prompt_id: str | None,
        reason: str,
    ) -> GenerationRecord:
        return self._transition(
            generation_uid,
            "reconciliation_required",
            ("submitting", "submitted", "running", "reconciliation_required"),
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
    ) -> GenerationRecord:
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            current = self._get(connection, generation_uid)
            if current.status not in expected:
                raise RuntimeError(
                    f"Invalid Card generation transition {current.status} -> {target}"
                )
            connection.execute(
                """
                UPDATE card_generations
                SET status = ?, prompt_id = COALESCE(?, prompt_id),
                    failure_category = ?, updated_at = datetime('now')
                WHERE generation_uid = ?
                """,
                (target, prompt_id, reason, generation_uid),
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
            "SELECT generation_uid, status, prompt_id FROM card_generations "
            "WHERE generation_uid = ?",
            (generation_uid,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Unknown Card generation: {generation_uid}")
        return SqliteCardGenerationRepository._record(row)

    @staticmethod
    def _record(row: sqlite3.Row) -> GenerationRecord:
        return GenerationRecord(
            str(row["generation_uid"]),
            str(row["status"]),
            None if row["prompt_id"] is None else str(row["prompt_id"]),
        )


class SqliteCardGenerationOutputRepository:
    """Persist Card generation outputs only under the reserved output root."""

    def __init__(self, database_path: Path, output_root: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._output_root = Path(output_root).resolve()

    def expected_bindings(
        self, generation_uid: str
    ) -> tuple[CompiledOutputBinding, ...]:
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT output_bindings_json FROM card_generations "
                "WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown Card generation: {generation_uid}")
            value = json.loads(str(row["output_bindings_json"]))
            if not isinstance(value, list):
                raise RuntimeError(
                    "Card generation output bindings are invalid"
                )
            return tuple(
                CompiledOutputBinding(str(item["role"]), str(item["node_id"]))
                for item in value
                if isinstance(item, dict)
            )
        finally:
            connection.close()

    def save_outputs(
        self,
        generation_uid: str,
        outputs: tuple[GenerationOutput, ...],
    ) -> tuple[GenerationOutput, ...]:
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            if (
                connection.execute(
                    "SELECT 1 FROM card_generations WHERE generation_uid = ?",
                    (generation_uid,),
                ).fetchone()
                is None
            ):
                raise KeyError(f"Unknown Card generation: {generation_uid}")
            for output in outputs:
                relative = self._relative_output(output.path)
                existing = connection.execute(
                    """
                    SELECT image_uid, output_role, relative_path, content_hash
                    FROM card_generation_outputs
                    WHERE generation_uid = ? AND output_node_id = ?
                      AND output_index = ?
                    """,
                    (generation_uid, output.node_id, output.output_index),
                ).fetchone()
                values = (
                    output.image_uid,
                    generation_uid,
                    output.role,
                    output.node_id,
                    output.output_index,
                    relative,
                    output.content_hash,
                )
                if existing is None:
                    connection.execute(
                        """
                    INSERT INTO card_generation_outputs(
                        image_uid, generation_uid, output_role, output_node_id,
                        output_index, relative_path, content_hash
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        values,
                    )
                elif (
                    str(existing["image_uid"]) != output.image_uid
                    or str(existing["output_role"]) != output.role
                    or str(existing["relative_path"]) != relative
                    or str(existing["content_hash"]) != output.content_hash
                ):
                    raise RuntimeError(
                        "Card generation output identity conflicts with persisted output"
                    )
            connection.commit()
            return outputs
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def outputs_complete(self, generation_uid: str) -> bool:
        expected = {
            (item.role, item.node_id)
            for item in self.expected_bindings(generation_uid)
        }
        if not expected:
            return False
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                "SELECT output_role, output_node_id FROM card_generation_outputs "
                "WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchall()
            actual = {
                (str(row["output_role"]), str(row["output_node_id"]))
                for row in rows
            }
            return expected <= actual
        finally:
            connection.close()

    def recovery_plan(
        self, generation_uid: str
    ) -> GenerationOutputRecoveryPlan:
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT output_policy_json FROM card_generations "
                "WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown Card generation: {generation_uid}")
            policy = json.loads(str(row["output_policy_json"]))
            if not isinstance(policy, dict):
                raise RuntimeError("Card generation output policy is invalid")
            return GenerationOutputRecoveryPlan(
                str(policy.get("output_subdirectory") or ""),
                str(policy.get("filename_prefix") or ""),
                self.expected_bindings(generation_uid),
            )
        finally:
            connection.close()

    def primary_output(self, generation_uid: str) -> GenerationOutput | None:
        """Return the one completed primary output for Candidate projection."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT image_uid, output_role, output_node_id, output_index,
                       relative_path, content_hash
                FROM card_generation_outputs
                WHERE generation_uid = ? AND output_role = 'primary'
                ORDER BY output_index
                """,
                (generation_uid,),
            ).fetchall()
            if not rows:
                return None
            if len(rows) != 1:
                raise RuntimeError(
                    "Card generation requires exactly one primary output"
                )
            row = rows[0]
            return GenerationOutput(
                str(row["image_uid"]),
                str(row["output_role"]),
                str(row["output_node_id"]),
                int(row["output_index"]),
                self._output_root / str(row["relative_path"]),
                str(row["content_hash"]),
            )
        finally:
            connection.close()

    def output_by_image_uid(self, image_uid: str) -> GenerationOutput | None:
        """Resolve one Card output for accepted-reference byte loading."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                """
                SELECT image_uid, output_role, output_node_id, output_index,
                       relative_path, content_hash
                FROM card_generation_outputs WHERE image_uid = ?
                """,
                (image_uid,),
            ).fetchone()
            if row is None:
                return None
            return GenerationOutput(
                str(row["image_uid"]),
                str(row["output_role"]),
                str(row["output_node_id"]),
                int(row["output_index"]),
                self._output_root / str(row["relative_path"]),
                str(row["content_hash"]),
            )
        finally:
            connection.close()

    def _relative_output(self, path: Path) -> str:
        resolved = Path(path).resolve()
        try:
            relative = resolved.relative_to(self._output_root)
        except ValueError as error:
            raise ValueError(
                "Card generation output escapes output root"
            ) from error
        parts = relative.parts
        if not parts or parts[0] != "card-battler":
            raise ValueError("Card generation output is outside card-battler")
        return relative.as_posix()


def _json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=lambda item: (
            item.value if isinstance(item, Enum) else str(item)
        ),
    )
