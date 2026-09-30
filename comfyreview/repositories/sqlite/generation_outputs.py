"""Canonical SQLite persistence for native multi-output images."""

from __future__ import annotations

import json
from pathlib import Path

from comfyreview.application import CompiledOutputBinding, GenerationOutput
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
                    SELECT image_uid, png_path
                    FROM images
                    WHERE generation_id = ? AND output_node_id = ? AND output_index = ?
                    """,
                    (generation_id, output.node_id, output.output_index),
                ).fetchone()
                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO images(
                            image_uid, generation_id, output_node_id,
                            output_index, png_path, json_path
                        ) VALUES (?, ?, ?, ?, ?, NULL)
                        """,
                        (
                            output.image_uid,
                            generation_id,
                            output.node_id,
                            output.output_index,
                            str(output.path),
                        ),
                    )
                elif (
                    str(existing["image_uid"]) != output.image_uid
                    or Path(str(existing["png_path"])) != output.path
                ):
                    raise RuntimeError(
                        f"Generation output identity conflict at {output.node_id}:{output.output_index}"
                    )
            connection.commit()
            return outputs
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
