"""SQLite adapters for canonical ranking and Arena workflows."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from uuid import uuid4

from comfyreview.application.arena import (
    ArenaCompetitor,
    ArenaDecision,
    ArenaMutationError,
    ArenaResult,
    ArenaValidationError,
)
from comfyreview.application.curation import (
    CurationAssignment,
    CurationImage,
    CurationResult,
    CurationValidationError,
)
from comfyreview.application.ranking import RankedImage
from comfyreview.application.reviews import OutputPairNotFoundError
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteRankingRepository:
    """Read canonical ranking aggregates without mutating persistence."""

    def __init__(
        self,
        database_path: Path,
        *,
        output_root: Path,
        allowed_set_keys: tuple[str, ...],
    ) -> None:
        self._database_path = Path(database_path)
        self._output_root = Path(output_root).resolve(strict=False)
        self._allowed_set_keys = frozenset(allowed_set_keys)

    def list_ranked_images(self) -> tuple[RankedImage, ...]:
        """Return rated, non-deleted images from canonical facts."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT
                    image.image_uid,
                    image.png_path,
                    image.json_path,
                    generation.model_branch,
                    generation.checkpoint,
                    generation.combo_key,
                    generation.sampler,
                    generation.scheduler,
                    generation.steps,
                    generation.cfg,
                    generation.denoise,
                    positive_prompt.text AS positive_prompt,
                    summary.current_rating,
                    summary.rating_count,
                    summary.average_rating,
                    assignment.set_key AS assigned_set_key
                FROM images AS image
                JOIN generations AS generation
                    ON generation.id = image.generation_id
                JOIN prompts AS positive_prompt
                    ON positive_prompt.id = generation.positive_prompt_id
                JOIN image_review_summary AS summary
                    ON summary.image_id = image.id
                LEFT JOIN curation_assignments AS assignment
                    ON assignment.image_id = image.id
                WHERE image.deleted_at IS NULL
                  AND summary.average_rating IS NOT NULL
                  AND summary.rating_count > 0
                ORDER BY image.id
                """
            ).fetchall()
            return tuple(self._ranked_image(row) for row in rows)
        finally:
            connection.close()

    def _ranked_image(self, row: sqlite3.Row) -> RankedImage:
        png_path = Path(str(row["png_path"]))
        json_value = row["json_path"]
        assigned = (
            str(row["assigned_set_key"])
            if row["assigned_set_key"] is not None
            else self._infer_set_key(png_path)
        )
        return RankedImage(
            image_uid=str(row["image_uid"]),
            png_path=png_path,
            json_path=(
                Path(str(json_value))
                if json_value is not None and str(json_value).strip()
                else None
            ),
            subdir=self._subdir(png_path),
            model_branch=str(row["model_branch"] or ""),
            checkpoint=str(row["checkpoint"] or ""),
            combo_key=str(row["combo_key"] or ""),
            positive_prompt=str(row["positive_prompt"] or ""),
            average_rating=float(row["average_rating"]),
            rating_count=int(row["rating_count"]),
            current_rating=(
                int(row["current_rating"])
                if row["current_rating"] is not None
                else None
            ),
            sampler=(
                str(row["sampler"]) if row["sampler"] is not None else None
            ),
            scheduler=(
                str(row["scheduler"]) if row["scheduler"] is not None else None
            ),
            steps=(int(row["steps"]) if row["steps"] is not None else None),
            cfg=(float(row["cfg"]) if row["cfg"] is not None else None),
            denoise=(
                float(row["denoise"]) if row["denoise"] is not None else None
            ),
            assigned_set_key=assigned,
        )

    def _relative_parts(self, png_path: Path) -> tuple[str, ...]:
        candidate = (
            png_path
            if png_path.is_absolute()
            else self._output_root / png_path
        ).resolve(strict=False)
        try:
            relative = candidate.parent.relative_to(self._output_root)
        except ValueError:
            return (candidate.parent.name,)
        return tuple(str(part) for part in relative.parts if str(part))

    def _subdir(self, png_path: Path) -> str:
        parts = self._relative_parts(png_path)
        if len(parts) >= 2 and parts[0].lower() == "playground":
            return f"playground/{parts[1]}"
        return "/".join(parts)

    def _infer_set_key(self, png_path: Path) -> str | None:
        parts = self._relative_parts(png_path)
        if len(parts) < 3 or parts[0].lower() != "playground":
            return None
        candidate = parts[2]
        return candidate if candidate in self._allowed_set_keys else None


class SqliteArenaRepository:
    """Persist canonical Arena matches and review events atomically."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_played_directions(
        self,
        image_uids: tuple[str, ...],
    ) -> frozenset[tuple[str, str]]:
        """Return canonical directed matches within the supplied pool."""
        if len(image_uids) < 2:
            return frozenset()
        placeholders = ",".join("?" for _value in image_uids)
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                f"""
                SELECT left_image.image_uid AS left_uid,
                       right_image.image_uid AS right_uid
                FROM arena_matches AS match
                JOIN images AS left_image
                    ON left_image.id = match.left_image_id
                JOIN images AS right_image
                    ON right_image.id = match.right_image_id
                WHERE left_image.image_uid IN ({placeholders})
                  AND right_image.image_uid IN ({placeholders})
                """,
                (*image_uids, *image_uids),
            ).fetchall()
            return frozenset(
                (str(row["left_uid"]), str(row["right_uid"])) for row in rows
            )
        finally:
            connection.close()

    def get_competitors(
        self,
        left_image_uid: str,
        right_image_uid: str,
    ) -> tuple[ArenaCompetitor, ArenaCompetitor]:
        """Return live aggregate state for exactly two images."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            competitors = self._load_competitors(
                connection,
                left_image_uid,
                right_image_uid,
            )
            return (
                competitors[left_image_uid][1],
                competitors[right_image_uid][1],
            )
        finally:
            connection.close()

    def save_decision(self, decision: ArenaDecision) -> ArenaResult:
        """Write one match and its two generated ratings in one transaction."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            command = decision.command
            competitors = self._load_competitors(
                connection,
                command.left_image_uid,
                command.right_image_uid,
            )
            self._ensure_direction_is_new(
                connection,
                command.left_image_uid,
                command.right_image_uid,
            )
            match_uid = f"runtime-arena-{uuid4()}"
            left_id = competitors[command.left_image_uid][0]
            right_id = competitors[command.right_image_uid][0]
            winner_uid = (
                command.left_image_uid
                if command.winner_side == "left"
                else command.right_image_uid
            )
            winner_id = competitors[winner_uid][0]
            connection.execute(
                """
                INSERT INTO arena_matches(
                    match_uid,
                    left_image_id,
                    right_image_id,
                    winner_image_id,
                    decision,
                    source,
                    source_key
                )
                VALUES (?, ?, ?, ?, ?, 'runtime', ?)
                """,
                (
                    match_uid,
                    left_id,
                    right_id,
                    winner_id,
                    command.winner_side,
                    match_uid,
                ),
            )
            loser_uid = (
                command.right_image_uid
                if command.winner_side == "left"
                else command.left_image_uid
            )
            self._append_rating(
                connection,
                competitors[winner_uid][0],
                decision.winner_rating,
                match_uid,
                "winner",
            )
            self._append_rating(
                connection,
                competitors[loser_uid][0],
                decision.loser_rating,
                match_uid,
                "loser",
            )
            connection.commit()
            return ArenaResult(
                match_uid=match_uid,
                winner_image_uid=winner_uid,
                winner_rating=decision.winner_rating,
                loser_rating=decision.loser_rating,
            )
        except ArenaValidationError:
            connection.rollback()
            raise
        except Exception as error:
            connection.rollback()
            raise ArenaMutationError(
                "Could not record canonical Arena decision"
            ) from error
        finally:
            connection.close()

    @staticmethod
    def _load_competitors(
        connection: sqlite3.Connection,
        left_image_uid: str,
        right_image_uid: str,
    ) -> dict[str, tuple[int, ArenaCompetitor]]:
        rows = connection.execute(
            """
            SELECT image.id,
                   image.image_uid,
                   summary.average_rating
            FROM images AS image
            JOIN image_review_summary AS summary
                ON summary.image_id = image.id
            WHERE image.image_uid IN (?, ?)
              AND image.deleted_at IS NULL
              AND summary.average_rating IS NOT NULL
              AND summary.rating_count > 0
            """,
            (left_image_uid, right_image_uid),
        ).fetchall()
        competitors = {
            str(row["image_uid"]): (
                int(row["id"]),
                ArenaCompetitor(
                    image_uid=str(row["image_uid"]),
                    average_rating=float(row["average_rating"]),
                ),
            )
            for row in rows
        }
        if set(competitors) != {left_image_uid, right_image_uid}:
            raise ArenaValidationError(
                "Arena pair no longer contains two live rated images"
            )
        return competitors

    @staticmethod
    def _ensure_direction_is_new(
        connection: sqlite3.Connection,
        left_image_uid: str,
        right_image_uid: str,
    ) -> None:
        row = connection.execute(
            """
            SELECT 1
            FROM arena_matches AS match
            JOIN images AS left_image
                ON left_image.id = match.left_image_id
            JOIN images AS right_image
                ON right_image.id = match.right_image_id
            WHERE left_image.image_uid = ?
              AND right_image.image_uid = ?
            LIMIT 1
            """,
            (left_image_uid, right_image_uid),
        ).fetchone()
        if row is not None:
            raise ArenaValidationError(
                "Arena pairing was already decided in this direction"
            )

    @staticmethod
    def _append_rating(
        connection: sqlite3.Connection,
        image_id: int,
        rating: int,
        match_uid: str,
        role: str,
    ) -> None:
        connection.execute(
            "UPDATE review_clock SET value = value + 1 WHERE singleton_id = 1"
        )
        sequence_row = connection.execute(
            "SELECT value FROM review_clock WHERE singleton_id = 1"
        ).fetchone()
        if sequence_row is None:
            raise RuntimeError("Review clock is unavailable")
        event_uid = f"{match_uid}-{role}"
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid,
                image_id,
                event_type,
                rating,
                source,
                source_key,
                sequence
            )
            VALUES (?, ?, 'rating', ?, 'runtime_arena', ?, ?)
            """,
            (
                event_uid,
                image_id,
                int(rating),
                event_uid,
                int(sequence_row[0]),
            ),
        )


class SqliteCurationRepository:
    """Read and atomically update canonical curation state."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def get_live_image(self, image_uid: str) -> CurationImage:
        """Return current paths for one live canonical image."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                """
                SELECT image_uid, png_path, json_path
                FROM images
                WHERE image_uid = ? AND deleted_at IS NULL
                """,
                (str(image_uid),),
            ).fetchone()
            if row is None:
                raise OutputPairNotFoundError(
                    "Canonical image is missing or deleted"
                )
            json_value = row["json_path"]
            return CurationImage(
                image_uid=str(row["image_uid"]),
                png_path=Path(str(row["png_path"])),
                json_path=(
                    Path(str(json_value))
                    if json_value is not None and str(json_value).strip()
                    else None
                ),
            )
        finally:
            connection.close()

    def assign(self, assignment: CurationAssignment) -> CurationResult:
        """Commit current paths and a single assignment atomically."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                """
                UPDATE images
                SET png_path = ?, json_path = ?, last_seen_at = datetime('now')
                WHERE image_uid = ?
                  AND deleted_at IS NULL
                  AND png_path = ?
                  AND json_path IS ?
                """,
                (
                    str(assignment.png_path),
                    self._path_text(assignment.json_path),
                    assignment.image_uid,
                    str(assignment.previous_png_path),
                    self._path_text(assignment.previous_json_path),
                ),
            )
            if cursor.rowcount != 1:
                raise CurationValidationError(
                    "Canonical image paths changed during curation"
                )
            image_row = connection.execute(
                "SELECT id FROM images WHERE image_uid = ?",
                (assignment.image_uid,),
            ).fetchone()
            if image_row is None:
                raise CurationValidationError("Canonical image is missing")
            image_id = int(image_row["id"])
            if assignment.set_key is None:
                connection.execute(
                    "DELETE FROM curation_assignments WHERE image_id = ?",
                    (image_id,),
                )
            else:
                source_key = f"runtime-curation:{assignment.image_uid}"
                connection.execute(
                    """
                    INSERT INTO curation_assignments(
                        image_id, set_key, source, source_key
                    )
                    VALUES (?, ?, 'runtime', ?)
                    ON CONFLICT(image_id) DO UPDATE SET
                        set_key = excluded.set_key,
                        source = excluded.source,
                        source_key = excluded.source_key,
                        assigned_at = datetime('now')
                    """,
                    (image_id, assignment.set_key, source_key),
                )
            connection.commit()
            return CurationResult(
                image_uid=assignment.image_uid,
                png_path=assignment.png_path,
                json_path=assignment.json_path,
                set_key=assignment.set_key,
            )
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _path_text(path: Path | None) -> str | None:
        return None if path is None else str(path)
