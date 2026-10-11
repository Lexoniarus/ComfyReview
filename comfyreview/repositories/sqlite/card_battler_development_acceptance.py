"""Atomic SQLite acceptance of one Card development Candidate."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_card_pool import (
    CardPoolConflictError,
    DevelopmentCardCandidateAcceptancePolicy,
)
from comfyreview.repositories.sqlite.card_battler_candidate_group_codec import (
    decode_candidate_group,
)
from comfyreview.repositories.sqlite.card_battler_card_pool_codec import (
    decode_pool_card,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    encode_value,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteCardDevelopmentAcceptanceWriter:
    """Replace one current Card state while retaining stable identity DNA."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._policy = DevelopmentCardCandidateAcceptancePolicy()

    def accept(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> str:
        """Accept one exact Candidate and return its unchanged Card identity."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            group_row = connection.execute(
                "SELECT * FROM card_candidate_groups WHERE group_id = ?",
                (group_id,),
            ).fetchone()
            rows = connection.execute(
                """
                SELECT * FROM card_candidates
                WHERE group_id = ? ORDER BY slot_index
                """,
                (group_id,),
            ).fetchall()
            if group_row is None or len(rows) != 4:
                raise CardPoolConflictError(
                    "Development Candidate group is incomplete"
                )
            group = decode_candidate_group(group_row, rows)
            candidate = self._policy.select(
                group,
                candidate_id,
                expected_revision=expected_revision,
            )
            if (
                group.source_card_id is None
                or group.source_card_revision is None
            ):
                raise CardPoolConflictError(
                    "Development source Card revision is missing"
                )
            card_row = connection.execute(
                "SELECT * FROM cards WHERE card_id = ? AND revision = ?",
                (group.source_card_id, group.source_card_revision),
            ).fetchone()
            if card_row is None:
                raise CardPoolConflictError("Card revision is stale")
            source = decode_pool_card(card_row)
            artifacts = candidate.artifacts
            if (
                artifacts is None
                or artifacts.development is None
                or candidate.output_image_uid is None
                or candidate.output_content_hash is None
            ):
                raise CardPoolConflictError(
                    "Development Candidate artifacts are incomplete"
                )
            if (
                group.semantic_profile != source.semantic_profile
                or group.imprint != source.state.identity.imprint
                or artifacts.card.imprint != source.state.identity.imprint
                or artifacts.card.tier_ordinal
                != source.state.card.tier_ordinal + 1
                or artifacts.card.stats.stat_profile_key
                != source.state.card.stats.stat_profile_key
            ):
                raise CardPoolConflictError(
                    "Development Candidate changed immutable Card DNA"
                )
            selected_row = next(
                row for row in rows if str(row["candidate_id"]) == candidate_id
            )
            next_group_revision = expected_revision + 1
            self._complete_group(
                connection,
                group_id=group_id,
                candidate_id=candidate_id,
                expected_revision=expected_revision,
                next_revision=next_group_revision,
            )
            card_update = connection.execute(
                """
                UPDATE cards SET revision = revision + 1,
                    structured_card_spec_json = ?, visual_recipe_json = ?,
                    presentation_json = ?, presentation_status = ?,
                    presentation_error_category = ?, active_image_uid = ?,
                    active_content_hash = ?, visual_tier = ?,
                    accepted_group_id = ?, accepted_candidate_id = ?,
                    updated_at = datetime('now')
                WHERE card_id = ? AND revision = ?
                """,
                (
                    encode_value(artifacts.card),
                    encode_value(artifacts.visual_recipe),
                    selected_row["presentation_json"],
                    str(selected_row["presentation_status"]),
                    selected_row["presentation_error_category"],
                    candidate.output_image_uid,
                    candidate.output_content_hash,
                    artifacts.card.tier_ordinal,
                    group_id,
                    candidate_id,
                    group.source_card_id,
                    group.source_card_revision,
                ),
            )
            if card_update.rowcount != 1:
                raise CardPoolConflictError("Card revision is stale")
            connection.commit()
            return group.source_card_id
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise CardPoolConflictError(
                "Development Candidate acceptance conflicts"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _complete_group(
        connection: sqlite3.Connection,
        *,
        group_id: str,
        candidate_id: str,
        expected_revision: int,
        next_revision: int,
    ) -> None:
        group = connection.execute(
            """
            UPDATE card_candidate_groups SET revision = ?,
                status = 'completed', updated_at = datetime('now')
            WHERE group_id = ? AND revision = ?
              AND status IN ('ready', 'partial_failure')
            """,
            (next_revision, group_id, expected_revision),
        )
        if group.rowcount != 1:
            raise CardPoolConflictError(
                "Development Candidate group revision is stale"
            )
        candidates = connection.execute(
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
            (next_revision, candidate_id, group_id, expected_revision),
        )
        if candidates.rowcount != 4:
            raise CardPoolConflictError(
                "Development Candidate group no longer has four slots"
            )
