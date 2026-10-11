"""Atomic persistence for composed Card development Candidates."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
)
from comfyreview.application.card_battler_card_pool import CardPoolCard
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


class SqliteCardDevelopmentGroupComposer:
    """Persist four one-step results against an exact current Card revision."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

    def complete(
        self,
        group_id: str,
        *,
        expected_revision: int,
        candidates: tuple[CompleteCardCandidateArtifacts, ...],
    ) -> None:
        """Move one claimed development group into image generation."""
        if len(candidates) != 4:
            raise ValueError(
                "Development composition requires four Candidates"
            )
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
                raise CardCandidateGroupConflictError(
                    "Development Candidate group is incomplete"
                )
            group = decode_candidate_group(group_row, rows)
            if (
                group.kind is not CardCandidateGroupKind.DEVELOPMENT
                or group.status is not CardCandidateGroupStatus.COMPOSING
                or group.revision != expected_revision
                or group.source_card_id is None
                or group.source_card_revision is None
            ):
                raise CardCandidateGroupConflictError(
                    "Development composition revision is stale"
                )
            card_row = connection.execute(
                "SELECT * FROM cards WHERE card_id = ? AND revision = ?",
                (group.source_card_id, group.source_card_revision),
            ).fetchone()
            if card_row is None:
                raise CardCandidateGroupConflictError(
                    "Development source Card revision is unavailable"
                )
            source = decode_pool_card(card_row)
            self._validate(group, source, rows, candidates)
            next_revision = expected_revision + 1
            first = candidates[0].card
            anchor_mechanic = source.state.card.traits[0].mechanic.key
            updated = connection.execute(
                """
                UPDATE card_candidate_groups SET revision = ?, status = ?,
                    shared_stat_profile_key = ?, shared_mechanic_key = ?,
                    failure_category = NULL, updated_at = datetime('now')
                WHERE group_id = ? AND revision = ? AND status = ?
                """,
                (
                    next_revision,
                    CardCandidateGroupStatus.GENERATING.value,
                    first.stats.stat_profile_key,
                    anchor_mechanic,
                    group_id,
                    expected_revision,
                    CardCandidateGroupStatus.COMPOSING.value,
                ),
            )
            if updated.rowcount != 1:
                raise CardCandidateGroupConflictError(
                    "Development composition revision is stale"
                )
            for row, artifacts in zip(rows, candidates, strict=True):
                self._update_candidate(
                    connection,
                    candidate_id=str(row["candidate_id"]),
                    expected_revision=expected_revision,
                    next_revision=next_revision,
                    artifacts=artifacts,
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate(
        group: CardCandidateGroup,
        source: CardPoolCard,
        rows: list[sqlite3.Row],
        candidates: tuple[CompleteCardCandidateArtifacts, ...],
    ) -> None:
        if (
            group.semantic_profile != source.semantic_profile
            or group.imprint != source.state.identity.imprint
            or group.reference_image_uid != source.state.active_image_uid
            or group.reference_content_hash != source.state.active_content_hash
        ):
            raise CardCandidateGroupConflictError(
                "Development group changed immutable Card provenance"
            )
        if tuple(int(row["materialization_seed"]) for row in rows) != tuple(
            item.materialization_seed for item in candidates
        ):
            raise CardCandidateGroupConflictError(
                "Development Candidate seeds changed"
            )
        current = source.state.card
        target_tier = current.tier_ordinal + 1
        if any(
            item.development is None
            or item.development.card != item.card
            or item.card.imprint != current.imprint
            or item.card.tier_ordinal != target_tier
            or item.card.stats.stat_profile_key
            != current.stats.stat_profile_key
            for item in candidates
        ):
            raise CardCandidateGroupConflictError(
                "Development Candidate changed stable Card DNA or tier"
            )

    @staticmethod
    def _update_candidate(
        connection: sqlite3.Connection,
        *,
        candidate_id: str,
        expected_revision: int,
        next_revision: int,
        artifacts: CompleteCardCandidateArtifacts,
    ) -> None:
        development = artifacts.development
        if development is None:
            raise CardCandidateGroupConflictError(
                "Development Candidate result is required"
            )
        presentation = artifacts.presentation.presentation
        presentation_error = (
            None
            if presentation is not None
            else artifacts.presentation.status.value
        )
        cursor = connection.execute(
            """
            UPDATE card_candidates SET group_revision = ?, status = ?,
                structured_card_spec_json = ?, visual_recipe_json = ?,
                presentation_json = ?, presentation_status = ?,
                presentation_error_category = ?, development_result_json = ?,
                failure_category = NULL, updated_at = datetime('now')
            WHERE candidate_id = ? AND group_revision = ?
            """,
            (
                next_revision,
                CardCandidateStatus.COMPOSING.value,
                encode_value(artifacts.card),
                encode_value(artifacts.visual_recipe),
                None if presentation is None else encode_value(presentation),
                artifacts.presentation.status.value,
                presentation_error,
                encode_value(development),
                candidate_id,
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise CardCandidateGroupConflictError(
                "Development Candidate composition is stale"
            )
