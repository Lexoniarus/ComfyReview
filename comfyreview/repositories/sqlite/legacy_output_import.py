"""Atomic SQLite writer for verified legacy-output provenance."""

from __future__ import annotations

import hashlib
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from comfyreview.domain import parse_prompt_atoms
from comfyreview.importers.legacy_models import (
    LegacyImageImport,
    LegacyOutputImportObserver,
    LegacyOutputImportRecoveryError,
    LegacyOutputImportResult,
    LegacyOutputImportValidationError,
)
from comfyreview.repositories.sqlite.canonical_schema import (
    CanonicalSchemaManager,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteLegacyOutputImportRepository:
    """Persist verified legacy outputs with backup and rollback safety."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def validate_records(
        self,
        records: tuple[LegacyImageImport, ...],
    ) -> None:
        """Reject stale audit mappings and canonical identity collisions."""
        connection = self._open_read_only(rows=True)
        try:
            for record in records:
                self._validate_record(connection, record)
        finally:
            connection.close()

    def import_records(
        self,
        records: tuple[LegacyImageImport, ...],
        *,
        excluded_without_sidecar: int,
        backup_directory: Path | None = None,
        observer: LegacyOutputImportObserver | None = None,
    ) -> LegacyOutputImportResult:
        """Import all records atomically after creating a SQLite backup."""
        backup_path = self._create_backup(backup_directory)
        if observer is not None:
            observer.backup_created(backup_path)
        connection = connect_existing(self._database_path, rows=True)
        new_images = 0
        enriched_images = 0
        new_generations = 0
        sampler_stages = 0
        processed_generations: set[str] = set()
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing_generations = self._generation_uids(connection)
            existing_images = self._image_uids(connection)
            for record in records:
                generation_was_new = (
                    record.generation_uid not in existing_generations
                )
                generation_id = self._upsert_generation(
                    connection,
                    record,
                )
                if generation_was_new:
                    existing_generations.add(record.generation_uid)
                    new_generations += 1

                if record.generation_uid not in processed_generations:
                    sampler_stages += self._replace_sampler_stages(
                        connection,
                        record,
                        generation_id=generation_id,
                    )
                    processed_generations.add(record.generation_uid)

                image_was_new = record.image_uid not in existing_images
                self._upsert_image(
                    connection,
                    record,
                    generation_id=generation_id,
                )
                if image_was_new:
                    existing_images.add(record.image_uid)
                    new_images += 1
                else:
                    enriched_images += 1
            connection.commit()
        except Exception as import_error:
            connection.rollback()
            connection.close()
            try:
                CanonicalSchemaManager(self._database_path).validate()
            except Exception as validation_error:
                try:
                    self._restore_backup(backup_path)
                    CanonicalSchemaManager(self._database_path).validate()
                except Exception as recovery_error:
                    raise LegacyOutputImportRecoveryError(
                        "Legacy output import failed and backup recovery "
                        "did not restore a valid canonical database"
                    ) from recovery_error
                raise import_error from validation_error
            raise
        else:
            connection.close()

        return LegacyOutputImportResult(
            backup_path=backup_path,
            new_images=new_images,
            enriched_images=enriched_images,
            new_generations=new_generations,
            sampler_stages=sampler_stages,
            excluded_without_sidecar=excluded_without_sidecar,
        )

    def _validate_record(
        self,
        connection: sqlite3.Connection,
        record: LegacyImageImport,
    ) -> None:
        by_uid = connection.execute(
            """
            SELECT
                image.image_uid,
                image.png_path,
                image.json_path,
                image.output_node_id,
                image.output_index,
                generation.generation_uid,
                generation.workflow_hash
            FROM images AS image
            JOIN generations AS generation
                ON generation.id = image.generation_id
            WHERE image.image_uid = ?
            """,
            (record.image_uid,),
        ).fetchone()
        if by_uid is not None:
            expected = (
                str(record.png_path),
                str(record.json_path),
                record.generation_uid,
            )
            actual = (
                str(by_uid["png_path"]),
                str(by_uid["json_path"]),
                str(by_uid["generation_uid"]),
            )
            if actual != expected:
                raise LegacyOutputImportValidationError(
                    "Canonical image identity no longer matches its audit"
                )
        elif record.existing_image_uid is not None:
            raise LegacyOutputImportValidationError(
                "Audited canonical image no longer exists"
            )

        path_owner = connection.execute(
            """
            SELECT image_uid
            FROM images
            WHERE png_path = ? OR json_path = ?
            """,
            (str(record.png_path), str(record.json_path)),
        ).fetchone()
        if path_owner is not None and str(path_owner["image_uid"]) != (
            record.image_uid
        ):
            raise LegacyOutputImportValidationError(
                "Audited path belongs to a different canonical image"
            )

        generation = connection.execute(
            """
            SELECT workflow_hash
            FROM generations
            WHERE generation_uid = ?
            """,
            (record.generation_uid,),
        ).fetchone()
        if generation is None and record.existing_generation_uid is not None:
            raise LegacyOutputImportValidationError(
                "Audited canonical generation no longer exists"
            )
        if generation is not None:
            stored_hash = generation["workflow_hash"]
            if stored_hash not in (None, "", record.workflow_hash):
                raise LegacyOutputImportValidationError(
                    "Canonical generation workflow conflicts with the audit"
                )

        if record.existing_image_uid is not None:
            return
        slot = connection.execute(
            """
            SELECT image.image_uid
            FROM images AS image
            JOIN generations AS generation
                ON generation.id = image.generation_id
            WHERE generation.generation_uid = ?
              AND image.output_node_id = ?
              AND image.output_index = ?
            """,
            (
                record.generation_uid,
                record.output_node_id,
                record.output_index,
            ),
        ).fetchone()
        if slot is not None and str(slot["image_uid"]) != record.image_uid:
            raise LegacyOutputImportValidationError(
                "Audited generation output slot is already occupied"
            )

    def _upsert_generation(
        self,
        connection: sqlite3.Connection,
        record: LegacyImageImport,
    ) -> int:
        positive_prompt_id = self._ensure_prompt(
            connection,
            scope="pos",
            prompt=record.positive_prompt,
        )
        negative_prompt_id = self._ensure_prompt(
            connection,
            scope="neg",
            prompt=record.negative_prompt,
        )
        existing = connection.execute(
            "SELECT id FROM generations WHERE generation_uid = ?",
            (record.generation_uid,),
        ).fetchone()
        if existing is None:
            connection.execute(
                """
                INSERT INTO generations(
                generation_uid,
                model_branch,
                checkpoint,
                combo_key,
                seed,
                steps,
                cfg,
                sampler,
                scheduler,
                denoise,
                loras_json,
                positive_prompt_id,
                negative_prompt_id,
                source,
                raw_metadata_json,
                workflow_json,
                workflow_hash,
                status
            )
                VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                'legacy_sidecar', ?, ?, ?, 'completed'
            )
                """,
                self._generation_values(
                    record,
                    positive_prompt_id=positive_prompt_id,
                    negative_prompt_id=negative_prompt_id,
                ),
            )
        else:
            connection.execute(
                """
                UPDATE generations
                SET model_branch = ?,
                    checkpoint = ?,
                    combo_key = ?,
                    seed = ?,
                    steps = ?,
                    cfg = ?,
                    sampler = ?,
                    scheduler = ?,
                    denoise = ?,
                    loras_json = ?,
                    positive_prompt_id = ?,
                    negative_prompt_id = ?,
                    raw_metadata_json = ?,
                    workflow_json = ?,
                    workflow_hash = ?
                WHERE generation_uid = ?
                """,
                (
                    record.model_branch,
                    record.checkpoint,
                    record.combo_key,
                    record.seed,
                    record.steps,
                    record.cfg,
                    record.sampler,
                    record.scheduler,
                    record.denoise,
                    record.loras_json,
                    positive_prompt_id,
                    negative_prompt_id,
                    record.raw_metadata_json,
                    record.workflow_json,
                    record.workflow_hash,
                    record.generation_uid,
                ),
            )
        row = connection.execute(
            "SELECT id FROM generations WHERE generation_uid = ?",
            (record.generation_uid,),
        ).fetchone()
        if row is None:
            raise RuntimeError("Legacy generation could not be persisted")
        return int(row["id"])

    @staticmethod
    def _generation_values(
        record: LegacyImageImport,
        *,
        positive_prompt_id: int,
        negative_prompt_id: int,
    ) -> tuple[object, ...]:
        return (
            record.generation_uid,
            record.model_branch,
            record.checkpoint,
            record.combo_key,
            record.seed,
            record.steps,
            record.cfg,
            record.sampler,
            record.scheduler,
            record.denoise,
            record.loras_json,
            positive_prompt_id,
            negative_prompt_id,
            record.raw_metadata_json,
            record.workflow_json,
            record.workflow_hash,
        )

    @staticmethod
    def _upsert_image(
        connection: sqlite3.Connection,
        record: LegacyImageImport,
        *,
        generation_id: int,
    ) -> None:
        existing = connection.execute(
            "SELECT id FROM images WHERE image_uid = ?",
            (record.image_uid,),
        ).fetchone()
        if existing is not None:
            connection.execute(
                "UPDATE images SET last_seen_at = datetime('now') "
                "WHERE image_uid = ?",
                (record.image_uid,),
            )
            return
        connection.execute(
            """
            INSERT INTO images(
                image_uid,
                generation_id,
                output_node_id,
                output_index,
                png_path,
                json_path,
                last_seen_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, datetime('now')
            )
            """,
            (
                record.image_uid,
                generation_id,
                record.output_node_id,
                record.output_index,
                str(record.png_path),
                str(record.json_path),
            ),
        )

    @staticmethod
    def _replace_sampler_stages(
        connection: sqlite3.Connection,
        record: LegacyImageImport,
        *,
        generation_id: int,
    ) -> int:
        connection.execute(
            "DELETE FROM generation_sampler_stages WHERE generation_id = ?",
            (generation_id,),
        )
        for stage in record.sampler_stages:
            connection.execute(
                """
                INSERT INTO generation_sampler_stages(
                    generation_id,
                    node_id,
                    stage_order,
                    role,
                    seed,
                    steps,
                    cfg,
                    sampler,
                    scheduler,
                    denoise,
                    source
                )
                VALUES (?, ?, ?, '', ?, ?, ?, ?, ?, ?, 'workflow_graph')
                """,
                (
                    generation_id,
                    stage.node_id,
                    stage.stage_order,
                    stage.seed,
                    stage.steps,
                    stage.cfg,
                    stage.sampler,
                    stage.scheduler,
                    stage.denoise,
                ),
            )
        return len(record.sampler_stages)

    def _ensure_prompt(
        self,
        connection: sqlite3.Connection,
        *,
        scope: str,
        prompt: str,
    ) -> int:
        prompt_text = str(prompt or "").strip()
        prompt_hash = hashlib.sha256(
            f"{scope}\0{prompt_text}".encode()
        ).hexdigest()
        connection.execute(
            """
            INSERT OR IGNORE INTO prompts(scope, prompt_hash, text)
            VALUES (?, ?, ?)
            """,
            (scope, prompt_hash, prompt_text),
        )
        row = connection.execute(
            """
            SELECT id, text
            FROM prompts
            WHERE scope = ? AND prompt_hash = ?
            """,
            (scope, prompt_hash),
        ).fetchone()
        if row is None or str(row["text"]) != prompt_text:
            raise RuntimeError(
                "Prompt identity collision during legacy import"
            )
        prompt_id = int(row["id"])
        membership = connection.execute(
            """
            SELECT 1 FROM prompt_memberships
            WHERE prompt_id = ?
            LIMIT 1
            """,
            (prompt_id,),
        ).fetchone()
        if membership is None:
            self._insert_prompt_memberships(
                connection,
                prompt_id=prompt_id,
                prompt_text=prompt_text,
            )
        return prompt_id

    @staticmethod
    def _insert_prompt_memberships(
        connection: sqlite3.Connection,
        *,
        prompt_id: int,
        prompt_text: str,
    ) -> None:
        for position, atom in enumerate(parse_prompt_atoms(prompt_text)):
            connection.execute(
                """
                INSERT OR IGNORE INTO prompt_atoms(canonical_text)
                VALUES (?)
                """,
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
                    prompt_id,
                    atom_id,
                    position,
                    weight_milli,
                    raw_text
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    prompt_id,
                    int(atom_row["id"]),
                    position,
                    atom.weight_milli,
                    atom.raw_text,
                ),
            )

    @staticmethod
    def _generation_uids(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row["generation_uid"])
            for row in connection.execute(
                "SELECT generation_uid FROM generations"
            ).fetchall()
        }

    @staticmethod
    def _image_uids(connection: sqlite3.Connection) -> set[str]:
        return {
            str(row["image_uid"])
            for row in connection.execute(
                "SELECT image_uid FROM images"
            ).fetchall()
        }

    def _create_backup(self, backup_directory: Path | None) -> Path:
        root = (
            Path(backup_directory).resolve()
            if backup_directory is not None
            else self._database_path.parent / "backups" / "legacy-import"
        )
        run_directory = root / (
            datetime.now(UTC).strftime("%Y%m%dT%H%M%S_%fZ")
            + f"_{uuid4().hex[:8]}"
        )
        backup_path = run_directory / self._database_path.name
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        source = sqlite3.connect(
            f"{self._database_path.as_uri()}?mode=ro",
            uri=True,
        )
        destination = sqlite3.connect(backup_path)
        try:
            source.backup(destination)
        finally:
            destination.close()
            source.close()
        return backup_path

    def _open_read_only(
        self,
        *,
        rows: bool = False,
    ) -> sqlite3.Connection:
        if not self._database_path.is_file():
            raise FileNotFoundError(
                f"SQLite database does not exist: {self._database_path}"
            )
        connection = sqlite3.connect(
            f"{self._database_path.as_uri()}?mode=ro",
            uri=True,
        )
        connection.execute("PRAGMA foreign_keys = ON")
        if rows:
            connection.row_factory = sqlite3.Row
        return connection

    def _restore_backup(self, backup_path: Path) -> None:
        for suffix in ("-wal", "-shm"):
            Path(f"{self._database_path}{suffix}").unlink(missing_ok=True)
        shutil.copy2(backup_path, self._database_path)
