"""SQLite persistence for four-slot Card evolution candidate batches."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_evolution import (
    CardCandidateStatus,
    CardEvolutionCandidate,
)
from comfyreview.application.card_battler_sessions import (
    CardSession,
    CardSessionConflictError,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.repositories.sqlite.card_battler_sessions import (
    SqliteCardSessionRepository,
)
from comfyreview.repositories.sqlite.connection import (
    connect_existing,
    connect_read_only,
)


class SqliteCardCandidateRepository:
    """Reserve, transition and accept Card candidates atomically."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path).resolve()
        self._sessions = SqliteCardSessionRepository(self._database_path)

    def reserve(
        self,
        session_id: str,
        *,
        expected_revision: int,
        candidates: tuple[CardEvolutionCandidate, ...],
    ) -> CardSession:
        """Reserve exactly four current slots and mark the session generating."""
        self._validate_batch(session_id, expected_revision + 1, candidates)
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM card_sessions WHERE session_id = ?",
                (session_id,),
            ).fetchone()
            if row is None or int(row["revision"]) != expected_revision:
                raise CardSessionConflictError(
                    "Card session revision is stale"
                )
            if str(row["operation_state"]) != "idle":
                raise CardSessionConflictError(
                    "Card session operation is in progress"
                )
            recipe_payload = str(row["visual_recipe_json"])
            recipe = json.loads(recipe_payload)
            expected_hash = hashlib.sha256(
                recipe_payload.encode("utf-8")
            ).hexdigest()
            if not isinstance(recipe, dict):
                raise RuntimeError("Card session visual recipe is invalid")
            tier = int(recipe.get("tier_ordinal", 0))
            provenance = recipe.get("provenance")
            revision = (
                str(
                    provenance.get("visual_projection_algorithm_revision")
                    or ""
                )
                if isinstance(provenance, dict)
                else ""
            )
            for candidate in candidates:
                if (
                    candidate.tier_ordinal != tier
                    or candidate.recipe_revision != revision
                    or candidate.recipe_hash != expected_hash
                    or candidate.reference_image_uid
                    != str(row["active_image_uid"])
                    or candidate.reference_content_hash
                    != str(row["active_content_hash"])
                ):
                    raise CardSessionConflictError(
                        "Card candidate provenance is stale"
                    )
                connection.execute(
                    """
                    INSERT INTO card_candidates(
                        candidate_id, session_id, session_revision, slot_index,
                        tier_key, recipe_revision, recipe_hash,
                        reference_image_uid, reference_content_hash, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                    """,
                    (
                        candidate.candidate_id,
                        candidate.session_id,
                        candidate.session_revision,
                        candidate.slot_index,
                        str(candidate.tier_ordinal),
                        candidate.recipe_revision,
                        candidate.recipe_hash,
                        candidate.reference_image_uid,
                        candidate.reference_content_hash,
                    ),
                )
            cursor = connection.execute(
                """
                UPDATE card_sessions
                SET revision = ?, operation_state = 'generating',
                    updated_at = datetime('now')
                WHERE session_id = ? AND revision = ?
                """,
                (expected_revision + 1, session_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise CardSessionConflictError(
                    "Card session revision is stale"
                )
            connection.commit()
        except sqlite3.IntegrityError as error:
            connection.rollback()
            raise CardSessionConflictError(
                "Card candidate batch already exists"
            ) from error
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        session = self._sessions.get(session_id)
        assert session is not None
        return session

    def list_for_session(
        self, session_id: str, *, session_revision: int
    ) -> tuple[CardEvolutionCandidate, ...]:
        connection = connect_read_only(self._database_path, rows=True)
        try:
            rows = connection.execute(
                """
                SELECT * FROM card_candidates
                WHERE session_id = ? AND session_revision = ?
                ORDER BY slot_index
                """,
                (session_id, session_revision),
            ).fetchall()
            return tuple(self._decode(row) for row in rows)
        finally:
            connection.close()

    def mark_submitted(
        self, candidate_id: str, generation_uid: str
    ) -> CardEvolutionCandidate:
        return self._transition(
            candidate_id,
            target=CardCandidateStatus.SUBMITTED,
            expected=(CardCandidateStatus.PENDING,),
            generation_uid=generation_uid,
        )

    def mark_failed(
        self, candidate_id: str, failure_category: str
    ) -> CardEvolutionCandidate:
        return self._transition(
            candidate_id,
            target=CardCandidateStatus.FAILED,
            expected=(
                CardCandidateStatus.PENDING,
                CardCandidateStatus.SUBMITTED,
            ),
            failure_category=failure_category,
        )

    def mark_completed(
        self, candidate_id: str, output: GenerationOutput
    ) -> CardEvolutionCandidate:
        return self._transition(
            candidate_id,
            target=CardCandidateStatus.COMPLETED,
            expected=(CardCandidateStatus.SUBMITTED,),
            output_image_uid=output.image_uid,
        )

    def accept(
        self,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardSession:
        """Accept one current completed candidate and release the session lock."""
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            candidate = connection.execute(
                "SELECT * FROM card_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            if candidate is None:
                raise KeyError(f"Unknown Card candidate: {candidate_id}")
            session = connection.execute(
                "SELECT * FROM card_sessions WHERE session_id = ?",
                (str(candidate["session_id"]),),
            ).fetchone()
            if (
                session is None
                or int(session["revision"]) != expected_revision
            ):
                raise CardSessionConflictError(
                    "Card session revision is stale"
                )
            if (
                int(candidate["session_revision"]) != expected_revision
                or str(candidate["status"])
                != CardCandidateStatus.COMPLETED.value
            ):
                raise CardSessionConflictError(
                    "Card candidate is stale or incomplete"
                )
            recipe_payload = str(session["visual_recipe_json"])
            if hashlib.sha256(
                recipe_payload.encode("utf-8")
            ).hexdigest() != str(candidate["recipe_hash"]):
                raise CardSessionConflictError(
                    "Card candidate recipe is stale"
                )
            output_uid = str(candidate["output_image_uid"] or "")
            output = connection.execute(
                "SELECT content_hash FROM card_generation_outputs WHERE image_uid = ?",
                (output_uid,),
            ).fetchone()
            if output is None:
                raise CardSessionConflictError(
                    "Card candidate output is unavailable"
                )
            connection.execute(
                "UPDATE card_candidates SET status = 'accepted', "
                "updated_at = datetime('now') WHERE candidate_id = ?",
                (candidate_id,),
            )
            connection.execute(
                """
                UPDATE card_sessions
                SET revision = ?, active_image_uid = ?, active_content_hash = ?,
                    active_image_kind = 'candidate', active_visual_tier = ?,
                    operation_state = 'idle', updated_at = datetime('now')
                WHERE session_id = ? AND revision = ?
                """,
                (
                    expected_revision + 1,
                    output_uid,
                    str(output["content_hash"]),
                    str(candidate["tier_key"]),
                    str(candidate["session_id"]),
                    expected_revision,
                ),
            )
            connection.commit()
            session_id = str(candidate["session_id"])
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()
        accepted = self._sessions.get(session_id)
        assert accepted is not None
        return accepted

    def _transition(
        self,
        candidate_id: str,
        *,
        target: CardCandidateStatus,
        expected: tuple[CardCandidateStatus, ...],
        generation_uid: str | None = None,
        failure_category: str | None = None,
        output_image_uid: str | None = None,
    ) -> CardEvolutionCandidate:
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM card_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown Card candidate: {candidate_id}")
            if CardCandidateStatus(str(row["status"])) not in expected:
                raise CardSessionConflictError(
                    "Card candidate transition is stale"
                )
            connection.execute(
                """
                UPDATE card_candidates
                SET status = ?, generation_uid = COALESCE(?, generation_uid),
                    failure_category = ?,
                    output_image_uid = COALESCE(?, output_image_uid),
                    updated_at = datetime('now')
                WHERE candidate_id = ?
                """,
                (
                    target.value,
                    generation_uid,
                    failure_category,
                    output_image_uid,
                    candidate_id,
                ),
            )
            updated = connection.execute(
                "SELECT * FROM card_candidates WHERE candidate_id = ?",
                (candidate_id,),
            ).fetchone()
            connection.commit()
            assert updated is not None
            return self._decode(updated)
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _validate_batch(
        session_id: str,
        revision: int,
        candidates: tuple[CardEvolutionCandidate, ...],
    ) -> None:
        if len(candidates) != 4 or tuple(
            item.slot_index for item in candidates
        ) != (
            0,
            1,
            2,
            3,
        ):
            raise ValueError(
                "Card candidate batch requires slots zero through three"
            )
        if any(
            item.session_id != session_id
            or item.session_revision != revision
            or item.status is not CardCandidateStatus.PENDING
            for item in candidates
        ):
            raise ValueError("Card candidate batch provenance is inconsistent")

    @staticmethod
    def _decode(row: sqlite3.Row) -> CardEvolutionCandidate:
        return CardEvolutionCandidate(
            candidate_id=str(row["candidate_id"]),
            session_id=str(row["session_id"]),
            session_revision=int(row["session_revision"]),
            slot_index=int(row["slot_index"]),
            tier_ordinal=int(row["tier_key"]),
            recipe_revision=str(row["recipe_revision"]),
            recipe_hash=str(row["recipe_hash"]),
            reference_image_uid=str(row["reference_image_uid"]),
            reference_content_hash=str(row["reference_content_hash"]),
            generation_uid=(
                None
                if row["generation_uid"] is None
                else str(row["generation_uid"])
            ),
            status=CardCandidateStatus(str(row["status"])),
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
        )
