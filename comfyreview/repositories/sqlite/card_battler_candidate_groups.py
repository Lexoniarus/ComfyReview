"""SQLite persistence for revisioned complete Card candidate groups."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_candidate_groups import (
    CARD_CANDIDATE_MATERIALIZATION_REVISION,
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    decode_card_spec,
    decode_imprint,
    decode_presentation,
    decode_semantic_profile,
    decode_visual_recipe,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardCandidateGroupRepository:
    """Persist group reservations in short atomic transactions."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()

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
            return self._decode_group(group_row, candidate_rows)
        finally:
            connection.close()

    @staticmethod
    def _insert_group(
        connection: sqlite3.Connection,
        group: CardCandidateGroup,
    ) -> None:
        connection.execute(
            """
            INSERT INTO card_candidate_groups (
                group_id, revision, kind, status, source_image_uid,
                source_content_hash, group_seed, semantic_profile_json,
                card_imprint_json, source_card_id, source_card_revision,
                failure_category
            ) VALUES (?, ?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?, ?)
            """,
            (
                group.group_id,
                group.revision,
                group.kind.value,
                group.status.value,
                group.source_image_uid,
                group.source_content_hash,
                str(group.group_seed),
                group.source_card_id,
                group.source_card_revision,
                group.failure_category,
            ),
        )

    @classmethod
    def _decode_group(
        cls,
        row: sqlite3.Row,
        candidate_rows: list[sqlite3.Row],
    ) -> CardCandidateGroup:
        semantic_payload = row["semantic_profile_json"]
        imprint_payload = row["card_imprint_json"]
        return CardCandidateGroup(
            group_id=str(row["group_id"]),
            revision=int(row["revision"]),
            kind=CardCandidateGroupKind(str(row["kind"])),
            status=CardCandidateGroupStatus(str(row["status"])),
            source_image_uid=str(row["source_image_uid"]),
            source_content_hash=str(row["source_content_hash"]),
            group_seed=int(row["group_seed"]),
            candidates=tuple(
                cls._decode_candidate(item) for item in candidate_rows
            ),
            semantic_profile=(
                None
                if semantic_payload is None
                else decode_semantic_profile(str(semantic_payload))
            ),
            imprint=(
                None
                if imprint_payload is None
                else decode_imprint(str(imprint_payload))
            ),
            source_card_id=(
                None
                if row["source_card_id"] is None
                else str(row["source_card_id"])
            ),
            source_card_revision=(
                None
                if row["source_card_revision"] is None
                else int(row["source_card_revision"])
            ),
            failure_category=(
                None
                if row["failure_category"] is None
                else str(row["failure_category"])
            ),
        )

    @staticmethod
    def _decode_candidate(row: sqlite3.Row) -> CardCandidate:
        card_payload = row["structured_card_spec_json"]
        recipe_payload = row["visual_recipe_json"]
        status_payload = row["presentation_status"]
        presentation_payload = row["presentation_json"]
        artifact_payloads = (card_payload, recipe_payload, status_payload)
        if any(value is None for value in artifact_payloads) and any(
            value is not None for value in artifact_payloads
        ):
            raise ValueError("Candidate artifact columns are incomplete")
        materialization_seed = int(row["materialization_seed"])
        artifacts = None
        if card_payload is not None:
            presentation_status = CardPresentationStatus(str(status_payload))
            presentation = (
                None
                if presentation_payload is None
                else decode_presentation(str(presentation_payload))
            )
            artifacts = CompleteCardCandidateArtifacts(
                card=decode_card_spec(str(card_payload)),
                visual_recipe=decode_visual_recipe(str(recipe_payload)),
                presentation=CardPresentationResult(
                    presentation,
                    presentation_status,
                ),
                materialization_seed=materialization_seed,
                materialization_revision=str(row["materialization_revision"]),
            )
        return CardCandidate(
            candidate_id=str(row["candidate_id"]),
            group_id=str(row["group_id"]),
            group_revision=int(row["group_revision"]),
            slot_index=int(row["slot_index"]),
            status=CardCandidateStatus(str(row["status"])),
            materialization_seed=materialization_seed,
            artifacts=artifacts,
            generation_uid=(
                None
                if row["generation_uid"] is None
                else str(row["generation_uid"])
            ),
            failure_category=(
                None
                if row["failure_category"] is None
                else str(row["failure_category"])
            ),
            output_image_uid=(
                None
                if row["output_image_uid"] is None
                else str(row["output_image_uid"])
            ),
            output_content_hash=(
                None
                if row["output_content_hash"] is None
                else str(row["output_content_hash"])
            ),
        )
