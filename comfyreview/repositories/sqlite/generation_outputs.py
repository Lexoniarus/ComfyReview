"""Canonical SQLite persistence for native multi-output images."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from comfyreview.application import (
    CompiledOutputBinding,
    GenerationOutput,
    GenerationOutputRecoveryPlan,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteGenerationOutputRepository:
    """Persist all outputs for one generation in a short atomic transaction."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def expected_bindings(
        self,
        generation_uid: str,
    ) -> tuple[CompiledOutputBinding, ...]:
        """Load expected role/node bindings captured during compilation."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT raw_metadata_json FROM generations WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown generation: {generation_uid}")
            metadata = json.loads(str(row["raw_metadata_json"] or "{}"))
            raw_bindings = metadata.get("output_bindings", [])
            if not isinstance(raw_bindings, list):
                raise RuntimeError("Generation output bindings are invalid")
            return tuple(
                CompiledOutputBinding(
                    str(binding["role"]), str(binding["node_id"])
                )
                for binding in raw_bindings
                if isinstance(binding, dict)
            )
        finally:
            connection.close()

    def save_outputs(
        self,
        generation_uid: str,
        outputs: tuple[GenerationOutput, ...],
    ) -> tuple[GenerationOutput, ...]:
        """Insert or verify every canonical output atomically."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            generation = connection.execute(
                "SELECT id FROM generations WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if generation is None:
                raise KeyError(f"Unknown generation: {generation_uid}")
            generation_id = int(generation["id"])
            for output in outputs:
                existing = connection.execute(
                    """
                    SELECT image_uid, output_role, png_path, content_hash
                    FROM images
                    WHERE generation_id = ? AND output_node_id = ? AND output_index = ?
                    """,
                    (generation_id, output.node_id, output.output_index),
                ).fetchone()
                if existing is None:
                    cursor = connection.execute(
                        """
                        INSERT INTO images(
                            image_uid, generation_id, output_node_id,
                            output_index, output_role, png_path, json_path,
                            content_hash
                        ) VALUES (?, ?, ?, ?, ?, ?, NULL, ?)
                        """,
                        (
                            output.image_uid,
                            generation_id,
                            output.node_id,
                            output.output_index,
                            output.role,
                            str(output.path),
                            output.content_hash,
                        ),
                    )
                    image_id = int(cursor.lastrowid or 0)
                elif (
                    str(existing["image_uid"]) != output.image_uid
                    or str(existing["output_role"]) != output.role
                    or Path(str(existing["png_path"])) != output.path
                    or str(existing["content_hash"]) != output.content_hash
                ):
                    raise RuntimeError(
                        f"Generation output identity conflict at {output.node_id}:{output.output_index}"
                    )
                else:
                    image_id = int(
                        connection.execute(
                            "SELECT id FROM images WHERE image_uid = ?",
                            (output.image_uid,),
                        ).fetchone()["id"]
                    )
                self._ensure_current_catalog_composition(
                    connection,
                    image_id=image_id,
                    image_uid=output.image_uid,
                    generation_id=generation_id,
                )
            connection.commit()
            return outputs
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _ensure_current_catalog_composition(
        connection: sqlite3.Connection,
        *,
        image_id: int,
        image_uid: str,
        generation_id: int,
    ) -> None:
        generation = connection.execute(
            "SELECT prompt_composition_id FROM generations WHERE id = ?",
            (generation_id,),
        ).fetchone()
        if generation is None or generation["prompt_composition_id"] is None:
            return
        composition_uid = f"image-catalog-generation-{image_uid}"
        connection.execute(
            """
            INSERT OR IGNORE INTO image_catalog_compositions(
                composition_uid, image_id, version, source
            ) VALUES (?, ?, 1, 'generation')
            """,
            (composition_uid, image_id),
        )
        current = connection.execute(
            "SELECT id FROM image_catalog_compositions "
            "WHERE composition_uid = ?",
            (composition_uid,),
        ).fetchone()
        composition_id = int(current["id"])
        connection.execute(
            """
            INSERT OR IGNORE INTO image_catalog_composition_revisions(
                composition_id, revision_id, position
            )
            SELECT ?, membership.revision_id, membership.position
            FROM generations AS generation
            JOIN prompt_composition_revisions AS membership
              ON membership.composition_id = generation.prompt_composition_id
            WHERE generation.id = ?
            ORDER BY membership.position, membership.slot
            """,
            (composition_id, generation_id),
        )
        connection.execute(
            """
            INSERT INTO current_image_catalog_compositions(
                image_id, composition_id
            ) VALUES (?, ?)
            ON CONFLICT(image_id) DO NOTHING
            """,
            (image_id, composition_id),
        )

    def outputs_complete(self, generation_uid: str) -> bool:
        """Return whether every compiled output binding has a saved image."""
        expected = {
            (binding.role, binding.node_id)
            for binding in self.expected_bindings(generation_uid)
        }
        if not expected:
            return False
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT image.output_role, image.output_node_id
                FROM images AS image
                JOIN generations AS generation
                  ON generation.id = image.generation_id
                WHERE generation.generation_uid = ?
                """,
                (generation_uid,),
            ).fetchall()
            persisted = {
                (str(row["output_role"]), str(row["output_node_id"]))
                for row in rows
            }
            return expected <= persisted
        finally:
            connection.close()

    def recovery_plan(
        self,
        generation_uid: str,
    ) -> GenerationOutputRecoveryPlan:
        """Load the exact output policy persisted before submission."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT raw_metadata_json FROM generations "
                "WHERE generation_uid = ?",
                (generation_uid,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown generation: {generation_uid}")
            metadata = json.loads(str(row["raw_metadata_json"] or "{}"))
            policy = metadata.get("output_policy")
            if not isinstance(policy, dict):
                raise RuntimeError("Generation output policy is invalid")
            return GenerationOutputRecoveryPlan(
                output_subdirectory=str(
                    policy.get("output_subdirectory") or ""
                ),
                filename_prefix=str(policy.get("filename_prefix") or ""),
                bindings=self.expected_bindings(generation_uid),
            )
        finally:
            connection.close()
