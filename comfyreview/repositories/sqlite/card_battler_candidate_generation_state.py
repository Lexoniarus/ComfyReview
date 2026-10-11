"""Atomic SQLite transitions for Card candidate image generation."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteCardCandidateGenerationStateWriter:
    """Persist one candidate transition and its aggregate group revision."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def mark_submitted(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        generation_uid: str,
        recipe_hash: str,
        generation_policy_revision: str,
    ) -> None:
        """Attach complete generation provenance to one composed slot."""
        required = (generation_uid, recipe_hash, generation_policy_revision)
        if any(not value.strip() for value in required):
            raise ValueError("Candidate generation provenance is required")
        self._transition(
            candidate_id,
            expected_revision=expected_revision,
            allowed_statuses=(CardCandidateStatus.COMPOSING,),
            target_status=CardCandidateStatus.SUBMITTED,
            generation_uid=generation_uid,
            recipe_hash=recipe_hash,
            generation_policy_revision=generation_policy_revision,
        )

    def mark_failed(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        failure_category: str,
        recipe_hash: str | None,
        generation_policy_revision: str | None,
    ) -> None:
        """Persist one terminal slot failure."""
        normalized = failure_category.strip()
        if not normalized:
            raise ValueError("failure_category is required")
        self._transition(
            candidate_id,
            expected_revision=expected_revision,
            allowed_statuses=(
                CardCandidateStatus.COMPOSING,
                CardCandidateStatus.SUBMITTED,
            ),
            target_status=CardCandidateStatus.FAILED,
            recipe_hash=recipe_hash,
            generation_policy_revision=generation_policy_revision,
            failure_category=normalized,
        )

    def mark_completed(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        output_image_uid: str,
        output_content_hash: str,
    ) -> None:
        """Attach one validated Card-runtime primary output."""
        if not output_image_uid.strip() or not output_content_hash.strip():
            raise ValueError("Candidate output identity is required")
        self._transition(
            candidate_id,
            expected_revision=expected_revision,
            allowed_statuses=(CardCandidateStatus.SUBMITTED,),
            target_status=CardCandidateStatus.COMPLETED,
            output_image_uid=output_image_uid,
            output_content_hash=output_content_hash,
        )

    def _transition(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        allowed_statuses: tuple[CardCandidateStatus, ...],
        target_status: CardCandidateStatus,
        generation_uid: str | None = None,
        recipe_hash: str | None = None,
        generation_policy_revision: str | None = None,
        failure_category: str | None = None,
        output_image_uid: str | None = None,
        output_content_hash: str | None = None,
    ) -> None:
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT candidate_id, group_id, group_revision, status,
                       generation_uid
                FROM card_candidates WHERE candidate_id = ?
                """,
                (candidate_id,),
            ).fetchone()
            if (
                row is None
                or int(row["group_revision"]) != expected_revision
                or CardCandidateStatus(str(row["status"]))
                not in allowed_statuses
            ):
                raise CardCandidateGroupConflictError(
                    "Card candidate generation transition is stale"
                )
            group_id = str(row["group_id"])
            self._require_generating_group(
                connection,
                group_id,
                expected_revision,
            )
            if target_status is CardCandidateStatus.COMPLETED:
                self._validate_primary_output(
                    connection,
                    generation_uid=str(row["generation_uid"]),
                    output_image_uid=output_image_uid,
                    output_content_hash=output_content_hash,
                )
            next_revision = expected_revision + 1
            candidates = connection.execute(
                """
                UPDATE card_candidates SET group_revision = ?
                WHERE group_id = ? AND group_revision = ?
                """,
                (next_revision, group_id, expected_revision),
            )
            if candidates.rowcount != 4:
                raise CardCandidateGroupConflictError(
                    "Card candidate group no longer has four slots"
                )
            candidate = connection.execute(
                """
                UPDATE card_candidates SET
                    status = ?, generation_uid = COALESCE(?, generation_uid),
                    recipe_hash = COALESCE(?, recipe_hash),
                    generation_policy_revision = COALESCE(
                        ?, generation_policy_revision
                    ),
                    failure_category = ?, output_image_uid = ?,
                    output_content_hash = ?, updated_at = datetime('now')
                WHERE candidate_id = ? AND group_revision = ?
                """,
                (
                    target_status.value,
                    generation_uid,
                    recipe_hash,
                    generation_policy_revision,
                    failure_category,
                    output_image_uid,
                    output_content_hash,
                    candidate_id,
                    next_revision,
                ),
            )
            if candidate.rowcount != 1:
                raise CardCandidateGroupConflictError(
                    "Card candidate generation transition is stale"
                )
            group_status = self._group_status(connection, group_id)
            group = connection.execute(
                """
                UPDATE card_candidate_groups SET revision = ?, status = ?,
                    updated_at = datetime('now')
                WHERE group_id = ? AND revision = ? AND status = ?
                """,
                (
                    next_revision,
                    group_status.value,
                    group_id,
                    expected_revision,
                    CardCandidateGroupStatus.GENERATING.value,
                ),
            )
            if group.rowcount != 1:
                raise CardCandidateGroupConflictError(
                    "Card candidate group generation revision is stale"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _require_generating_group(
        connection: sqlite3.Connection,
        group_id: str,
        expected_revision: int,
    ) -> None:
        row = connection.execute(
            """
            SELECT 1 FROM card_candidate_groups
            WHERE group_id = ? AND revision = ? AND status = ?
            """,
            (
                group_id,
                expected_revision,
                CardCandidateGroupStatus.GENERATING.value,
            ),
        ).fetchone()
        if row is None:
            raise CardCandidateGroupConflictError(
                "Card candidate group generation revision is stale"
            )

    @staticmethod
    def _validate_primary_output(
        connection: sqlite3.Connection,
        *,
        generation_uid: str,
        output_image_uid: str | None,
        output_content_hash: str | None,
    ) -> None:
        row = connection.execute(
            """
            SELECT 1 FROM card_generation_outputs
            WHERE image_uid = ? AND generation_uid = ?
              AND output_role = 'primary' AND content_hash = ?
            """,
            (output_image_uid, generation_uid, output_content_hash),
        ).fetchone()
        if row is None:
            raise CardCandidateGroupConflictError(
                "Candidate primary output provenance is invalid"
            )

    @staticmethod
    def _group_status(
        connection: sqlite3.Connection,
        group_id: str,
    ) -> CardCandidateGroupStatus:
        statuses = tuple(
            CardCandidateStatus(str(row[0]))
            for row in connection.execute(
                """
                SELECT status FROM card_candidates
                WHERE group_id = ? ORDER BY slot_index
                """,
                (group_id,),
            ).fetchall()
        )
        if len(statuses) != 4:
            raise CardCandidateGroupConflictError(
                "Card candidate group no longer has four slots"
            )
        terminal = {
            CardCandidateStatus.COMPLETED,
            CardCandidateStatus.FAILED,
        }
        if any(status not in terminal for status in statuses):
            return CardCandidateGroupStatus.GENERATING
        completed = sum(
            status is CardCandidateStatus.COMPLETED for status in statuses
        )
        if completed == 4:
            return CardCandidateGroupStatus.READY
        if completed == 0:
            return CardCandidateGroupStatus.FAILED
        return CardCandidateGroupStatus.PARTIAL_FAILURE
