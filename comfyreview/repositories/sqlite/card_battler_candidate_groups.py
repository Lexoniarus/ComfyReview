"""SQLite persistence for revisioned complete Card candidate groups."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_candidate_groups import (
    CARD_CANDIDATE_MATERIALIZATION_REVISION,
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
)
from comfyreview.application.card_battler_semantics import SemanticImageProfile
from comfyreview.domain.card_battler import CardImprint
from comfyreview.repositories.sqlite.card_battler_candidate_generation_state import (
    SqliteCardCandidateGenerationStateWriter,
)
from comfyreview.repositories.sqlite.card_battler_candidate_group_codec import (
    decode_candidate_group,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    encode_value,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardCandidateGroupRepository:
    """Persist group reservations in short atomic transactions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._generation_state = SqliteCardCandidateGenerationStateWriter(
            self._database_path
        )

    def create(self, group: CardCandidateGroup) -> CardCandidateGroup:
        """Atomically insert one new group and its four reserved slots."""
        if (
            group.revision != 1
            or group.status is not CardCandidateGroupStatus.QUEUED
        ):
            raise ValueError(
                "New Card candidate groups must be queued revision one"
            )
        if any(
            candidate.status is not CardCandidateStatus.QUEUED
            or candidate.artifacts is not None
            for candidate in group.candidates
        ):
            raise ValueError(
                "New Card candidate slots must be empty and queued"
            )
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._insert_group(connection, group)
            connection.executemany(
                """
                INSERT INTO card_candidates (
                    candidate_id, group_id, group_revision, slot_index,
                    status, materialization_seed, materialization_revision
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        candidate.candidate_id,
                        candidate.group_id,
                        candidate.group_revision,
                        candidate.slot_index,
                        candidate.status.value,
                        str(candidate.materialization_seed),
                        CARD_CANDIDATE_MATERIALIZATION_REVISION,
                    )
                    for candidate in group.candidates
                ),
            )
            connection.commit()
            return group
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise CardCandidateGroupConflictError(
                "Card candidate group identity already exists"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, group_id: str) -> CardCandidateGroup | None:
        """Read one group and its four ordered slots without write access."""
        normalized = str(group_id or "").strip()
        if not normalized:
            raise ValueError("group_id is required")
        connection = connect_read_only(self._database_path, rows=True)
        try:
            group_row = connection.execute(
                "SELECT * FROM card_candidate_groups WHERE group_id = ?",
                (normalized,),
            ).fetchone()
            if group_row is None:
                return None
            candidate_rows = connection.execute(
                """
                SELECT * FROM card_candidates
                WHERE group_id = ? ORDER BY slot_index
                """,
                (normalized,),
            ).fetchall()
            return decode_candidate_group(group_row, candidate_rows)
        finally:
            connection.close()

    def claim_next_queued(self) -> CardCandidateGroup | None:
        """Atomically claim the oldest queued group for composition."""
        connection = connect_existing(self._database_path, rows=True)
        group_id: str | None = None
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                """
                SELECT group_id, revision FROM card_candidate_groups
                WHERE status = ? ORDER BY created_at, group_id LIMIT 1
                """,
                (CardCandidateGroupStatus.QUEUED.value,),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            group_id = str(row["group_id"])
            revision = int(row["revision"])
            next_revision = revision + 1
            cursor = connection.execute(
                """
                UPDATE card_candidate_groups
                SET revision = ?, status = ?, updated_at = datetime('now')
                WHERE group_id = ? AND revision = ? AND status = ?
                """,
                (
                    next_revision,
                    CardCandidateGroupStatus.COMPOSING.value,
                    group_id,
                    revision,
                    CardCandidateGroupStatus.QUEUED.value,
                ),
            )
            if cursor.rowcount != 1:
                raise CardCandidateGroupConflictError(
                    "Card candidate group claim is stale"
                )
            candidates = connection.execute(
                """
                UPDATE card_candidates
                SET group_revision = ?, status = ?, updated_at = datetime('now')
                WHERE group_id = ? AND group_revision = ?
                """,
                (
                    next_revision,
                    CardCandidateStatus.COMPOSING.value,
                    group_id,
                    revision,
                ),
            )
            if candidates.rowcount != 4:
                raise CardCandidateGroupConflictError(
                    "Card candidate group no longer has four slots"
                )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        claimed = self.get(group_id)
        if claimed is None:
            raise CardCandidateGroupConflictError(
                "Claimed Card candidate group disappeared"
            )
        return claimed

    def complete_composition(
        self,
        group_id: str,
        *,
        expected_revision: int,
        semantic_profile: SemanticImageProfile,
        imprint: CardImprint,
        candidates: tuple[CompleteCardCandidateArtifacts, ...],
    ) -> CardCandidateGroup:
        """Persist four complete artifacts and move the group to generation."""
        if len(candidates) != 4:
            raise ValueError("Composition requires exactly four candidates")
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            group_row, rows = self._candidate_rows_for_update(
                connection,
                group_id,
                expected_revision,
            )
            if (
                semantic_profile.image_uid
                != str(group_row["source_image_uid"])
                or imprint.source_image_uid != semantic_profile.image_uid
                or imprint.semantic_revision
                != semantic_profile.semantic_revision
            ):
                raise CardCandidateGroupConflictError(
                    "Candidate composition changed source DNA"
                )
            if tuple(
                int(row["materialization_seed"]) for row in rows
            ) != tuple(item.materialization_seed for item in candidates):
                raise CardCandidateGroupConflictError(
                    "Candidate materialization seeds changed"
                )
            next_revision = expected_revision + 1
            first = candidates[0].card
            if len(first.traits) != 1:
                raise CardCandidateGroupConflictError(
                    "Candidate composition requires one shared trait"
                )
            first_mechanic_key = first.traits[0].mechanic.key
            if any(
                item.card.imprint != imprint
                or item.card.stats.stat_profile_key
                != first.stats.stat_profile_key
                or len(item.card.traits) != 1
                or item.card.traits[0].mechanic.key != first_mechanic_key
                for item in candidates
            ):
                raise CardCandidateGroupConflictError(
                    "Candidate composition changed shared DNA"
                )
            self._update_composed_group(
                connection,
                group_id=group_id,
                expected_revision=expected_revision,
                next_revision=next_revision,
                semantic_profile_json=encode_value(semantic_profile),
                card_imprint_json=encode_value(imprint),
                stat_profile_key=first.stats.stat_profile_key,
                mechanic_key=first_mechanic_key,
            )
            for row, artifacts in zip(rows, candidates, strict=True):
                self._update_composed_candidate(
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
        return self._required(group_id)

    def fail_composition(
        self,
        group_id: str,
        *,
        expected_revision: int,
        failure_category: str,
    ) -> CardCandidateGroup:
        """Fail one claimed composition without retaining partial artifacts."""
        normalized = failure_category.strip()
        if not normalized:
            raise ValueError("failure_category is required")
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            self._fail_group(
                connection,
                group_id=group_id,
                expected_revision=expected_revision,
                failure_category=normalized,
            )
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        return self._required(group_id)

    def fail_interrupted_compositions(self) -> int:
        """Fail all composing groups left by a stopped process once."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                """
                SELECT group_id, revision FROM card_candidate_groups
                WHERE status = ? ORDER BY created_at, group_id
                """,
                (CardCandidateGroupStatus.COMPOSING.value,),
            ).fetchall()
            for row in rows:
                self._fail_group(
                    connection,
                    group_id=str(row["group_id"]),
                    expected_revision=int(row["revision"]),
                    failure_category="interrupted_composition",
                )
            connection.commit()
            return len(rows)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def mark_submitted(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        generation_uid: str,
        recipe_hash: str,
        generation_policy_revision: str,
    ) -> CardCandidateGroup:
        """Attach one submitted generation and advance the group revision."""
        self._generation_state.mark_submitted(
            candidate_id,
            expected_revision=expected_revision,
            generation_uid=generation_uid,
            recipe_hash=recipe_hash,
            generation_policy_revision=generation_policy_revision,
        )
        return self._required_group_for_candidate(candidate_id)

    def mark_generation_failed(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        failure_category: str,
        recipe_hash: str | None = None,
        generation_policy_revision: str | None = None,
    ) -> CardCandidateGroup:
        """Fail one generation slot and refresh aggregate group status."""
        self._generation_state.mark_failed(
            candidate_id,
            expected_revision=expected_revision,
            failure_category=failure_category,
            recipe_hash=recipe_hash,
            generation_policy_revision=generation_policy_revision,
        )
        return self._required_group_for_candidate(candidate_id)

    def mark_completed(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
        output_image_uid: str,
        output_content_hash: str,
    ) -> CardCandidateGroup:
        """Attach one validated primary output and refresh group status."""
        self._generation_state.mark_completed(
            candidate_id,
            expected_revision=expected_revision,
            output_image_uid=output_image_uid,
            output_content_hash=output_content_hash,
        )
        return self._required_group_for_candidate(candidate_id)

    def _required_group_for_candidate(
        self,
        candidate_id: str,
    ) -> CardCandidateGroup:
        connection = connect_read_only(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT group_id FROM card_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
        finally:
            connection.close()
        if row is None:
            raise CardCandidateGroupConflictError(
                "Card candidate generation transition failed"
            )
        return self._required(str(row["group_id"]))

    @staticmethod
    def _candidate_rows_for_update(
        connection: sqlite3.Connection,
        group_id: str,
        expected_revision: int,
    ) -> tuple[sqlite3.Row, list[sqlite3.Row]]:
        group = connection.execute(
            """
            SELECT status, revision, source_image_uid
            FROM card_candidate_groups
            WHERE group_id = ?
            """,
            (group_id,),
        ).fetchone()
        if (
            group is None
            or int(group["revision"]) != expected_revision
            or str(group["status"]) != CardCandidateGroupStatus.COMPOSING.value
        ):
            raise CardCandidateGroupConflictError(
                "Card candidate composition revision is stale"
            )
        rows = connection.execute(
            """
            SELECT candidate_id, materialization_seed FROM card_candidates
            WHERE group_id = ? AND group_revision = ? ORDER BY slot_index
            """,
            (group_id, expected_revision),
        ).fetchall()
        if len(rows) != 4:
            raise CardCandidateGroupConflictError(
                "Card candidate group no longer has four slots"
            )
        return group, rows

    @staticmethod
    def _update_composed_group(
        connection: sqlite3.Connection,
        *,
        group_id: str,
        expected_revision: int,
        next_revision: int,
        semantic_profile_json: str,
        card_imprint_json: str,
        stat_profile_key: str,
        mechanic_key: str,
    ) -> None:
        cursor = connection.execute(
            """
            UPDATE card_candidate_groups SET
                revision = ?, status = ?, semantic_profile_json = ?,
                card_imprint_json = ?, shared_stat_profile_key = ?,
                shared_mechanic_key = ?, failure_category = NULL,
                updated_at = datetime('now')
            WHERE group_id = ? AND revision = ? AND status = ?
            """,
            (
                next_revision,
                CardCandidateGroupStatus.GENERATING.value,
                semantic_profile_json,
                card_imprint_json,
                stat_profile_key,
                mechanic_key,
                group_id,
                expected_revision,
                CardCandidateGroupStatus.COMPOSING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise CardCandidateGroupConflictError(
                "Card candidate composition revision is stale"
            )

    @staticmethod
    def _update_composed_candidate(
        connection: sqlite3.Connection,
        *,
        candidate_id: str,
        expected_revision: int,
        next_revision: int,
        artifacts: CompleteCardCandidateArtifacts,
    ) -> None:
        presentation = artifacts.presentation.presentation
        presentation_error = (
            None
            if presentation is not None
            else artifacts.presentation.status.value
        )
        cursor = connection.execute(
            """
            UPDATE card_candidates SET
                group_revision = ?, status = ?,
                structured_card_spec_json = ?, visual_recipe_json = ?,
                presentation_json = ?, presentation_status = ?,
                presentation_error_category = ?, failure_category = NULL,
                updated_at = datetime('now')
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
                candidate_id,
                expected_revision,
            ),
        )
        if cursor.rowcount != 1:
            raise CardCandidateGroupConflictError(
                "Card candidate composition revision is stale"
            )

    @staticmethod
    def _fail_group(
        connection: sqlite3.Connection,
        *,
        group_id: str,
        expected_revision: int,
        failure_category: str,
    ) -> None:
        next_revision = expected_revision + 1
        cursor = connection.execute(
            """
            UPDATE card_candidate_groups SET
                revision = ?, status = ?, failure_category = ?,
                updated_at = datetime('now')
            WHERE group_id = ? AND revision = ? AND status = ?
            """,
            (
                next_revision,
                CardCandidateGroupStatus.FAILED.value,
                failure_category,
                group_id,
                expected_revision,
                CardCandidateGroupStatus.COMPOSING.value,
            ),
        )
        if cursor.rowcount != 1:
            raise CardCandidateGroupConflictError(
                "Card candidate composition revision is stale"
            )
        candidates = connection.execute(
            """
            UPDATE card_candidates SET
                group_revision = ?, status = ?, failure_category = ?,
                updated_at = datetime('now')
            WHERE group_id = ? AND group_revision = ?
            """,
            (
                next_revision,
                CardCandidateStatus.FAILED.value,
                failure_category,
                group_id,
                expected_revision,
            ),
        )
        if candidates.rowcount != 4:
            raise CardCandidateGroupConflictError(
                "Card candidate group no longer has four slots"
            )

    def _required(self, group_id: str) -> CardCandidateGroup:
        group = self.get(group_id)
        if group is None:
            raise CardCandidateGroupConflictError(
                "Card candidate group disappeared"
            )
        return group

    @staticmethod
    def _insert_group(
        connection: sqlite3.Connection,
        group: CardCandidateGroup,
    ) -> None:
        connection.execute(
            """
            INSERT INTO card_candidate_groups (
                group_id, revision, kind, status, source_image_uid,
                source_content_hash, reference_image_uid,
                reference_content_hash, group_seed, semantic_profile_json,
                card_imprint_json, source_card_id, source_card_revision,
                failure_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
            """,
            (
                group.group_id,
                group.revision,
                group.kind.value,
                group.status.value,
                group.source_image_uid,
                group.source_content_hash,
                group.reference_image_uid,
                group.reference_content_hash,
                str(group.group_seed),
                group.source_card_id,
                group.source_card_revision,
                group.failure_category,
            ),
        )
