"""SQLite persistence for the isolated confirmed POC Card pool."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_card_pool import (
    CardPoolCard,
    CardPoolConflictError,
    InitialCardCandidateAcceptancePolicy,
)
from comfyreview.repositories.sqlite.card_battler_candidate_group_codec import (
    decode_candidate_group,
)
from comfyreview.repositories.sqlite.card_battler_card_pool_codec import (
    decode_pool_card,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardPoolRepository:
    """Accept and query Cards using short Card-runtime transactions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._acceptance = InitialCardCandidateAcceptancePolicy()

    def accept_initial_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
        card_id: str,
    ) -> CardPoolCard:
        """Atomically accept one initial Candidate and complete its group."""
        if not card_id.strip():
            raise ValueError("Card identity is required")
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            group_row = connection.execute(
                "SELECT * FROM card_candidate_groups WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            if group_row is None:
                raise CardPoolConflictError("Candidate group does not exist")
            candidate_rows = connection.execute(
                """
                SELECT * FROM card_candidates
                WHERE group_id = ? ORDER BY slot_index
                """,
                (group_id,),
            ).fetchall()
            group = decode_candidate_group(group_row, candidate_rows)
            candidate = self._acceptance.select(
                group,
                candidate_id,
                expected_revision=expected_revision,
            )
            artifacts = candidate.artifacts
            if (
                artifacts is None
                or group.semantic_profile is None
                or group.imprint is None
                or candidate.output_image_uid is None
                or candidate.output_content_hash is None
            ):
                raise CardPoolConflictError(
                    "Accepted Candidate artifacts are incomplete"
                )
            selected_row = next(
                row
                for row in candidate_rows
                if str(row["candidate_id"]) == candidate_id
            )
            next_revision = expected_revision + 1
            group_update = connection.execute(
                """
                UPDATE card_candidate_groups SET revision = ?,
                    status = 'completed', updated_at = datetime('now')
                WHERE group_id = ? AND revision = ?
                  AND status IN ('ready', 'partial_failure')
                """,
                (next_revision, group_id, expected_revision),
            )
            if group_update.rowcount != 1:
                raise CardPoolConflictError(
                    "Candidate group acceptance revision is stale"
                )
            candidate_update = connection.execute(
                """
                UPDATE card_candidates SET group_revision = ?,
                    status = CASE
                        WHEN candidate_id = ? THEN 'accepted'
                        WHEN status = 'completed' THEN 'rejected'
                        ELSE status
                    END,
                    updated_at = datetime('now')
                WHERE group_id = ? AND group_revision = ?
                """,
                (
                    next_revision,
                    candidate_id,
                    group_id,
                    expected_revision,
                ),
            )
            if candidate_update.rowcount != 4:
                raise CardPoolConflictError(
                    "Candidate group no longer has four slots"
                )
            connection.execute(
                """
                INSERT INTO cards(
                    card_id, revision, source_image_uid,
                    source_content_hash, semantic_profile_json,
                    card_imprint_json, structured_card_spec_json,
                    visual_recipe_json, presentation_json,
                    presentation_status, presentation_error_category,
                    active_image_uid, active_content_hash, visual_tier,
                    accepted_group_id, accepted_candidate_id
                ) VALUES (?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    card_id,
                    group.source_image_uid,
                    group.source_content_hash,
                    str(group_row["semantic_profile_json"]),
                    str(group_row["card_imprint_json"]),
                    str(selected_row["structured_card_spec_json"]),
                    str(selected_row["visual_recipe_json"]),
                    selected_row["presentation_json"],
                    str(selected_row["presentation_status"]),
                    selected_row["presentation_error_category"],
                    candidate.output_image_uid,
                    candidate.output_content_hash,
                    artifacts.card.tier_ordinal,
                    group_id,
                    candidate_id,
                ),
            )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise CardPoolConflictError(
                "Card identity or Candidate acceptance conflicts"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self._required(card_id)

    def get(self, card_id: str) -> CardPoolCard | None:
        """Return one current confirmed Card."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT * FROM cards WHERE card_id = ?",
                (card_id,),
            ).fetchone()
            return None if row is None else decode_pool_card(row)
        finally:
            connection.close()

    def list_cards(self) -> tuple[CardPoolCard, ...]:
        """Return the unbounded POC Card pool in stable creation order."""
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                "SELECT * FROM cards ORDER BY created_at, card_id"
            ).fetchall()
            return tuple(decode_pool_card(row) for row in rows)
        finally:
            connection.close()

    def _required(self, card_id: str) -> CardPoolCard:
        card = self.get(card_id)
        if card is None:
            raise CardPoolConflictError("Accepted Card was not persisted")
        return card
