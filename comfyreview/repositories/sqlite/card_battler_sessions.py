"""SQLite repository for isolated revisioned Card Factory sessions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.application.card_battler_sessions import (
    CardActiveImageKind,
    CardSession,
    CardSessionCapacityError,
    CardSessionConflictError,
    CardSessionOperationState,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    decode_card_spec,
    decode_imprint,
    decode_presentation,
    decode_semantic_profile,
    decode_visual_recipe,
    encode_value,
)
from comfyreview.repositories.sqlite.connection import connect_existing


class SqliteCardSessionRepository:
    """Persist at most 64 sessions with short atomic CAS transactions."""

    def __init__(self, database_path: Path, *, capacity: int = 64) -> None:
        if capacity < 1:
            raise ValueError("Card session capacity must be positive")
        self._database_path = Path(database_path).resolve()
        self._capacity = capacity

    def create(self, session: CardSession) -> CardSession:
        """Insert one initial session without silent eviction."""
        if session.revision != 1:
            raise ValueError("new Card session revision must be one")
        connection = connect_existing(self._database_path)
        try:
            connection.execute("BEGIN IMMEDIATE")
            count = int(
                connection.execute(
                    "SELECT COUNT(*) FROM card_sessions"
                ).fetchone()[0]
            )
            if count >= self._capacity:
                raise CardSessionCapacityError("Card session capacity reached")
            try:
                connection.execute(
                    """
                    INSERT INTO card_sessions (
                        session_id, revision, source_image_uid,
                        source_content_hash, active_image_uid,
                        active_content_hash, active_image_kind,
                        active_visual_tier, operation_state,
                        semantic_profile_json, card_imprint_json,
                        structured_card_spec_json, visual_recipe_json,
                        presentation_json, presentation_status,
                        presentation_error_category
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                    """,
                    self._values(session),
                )
            except sqlite3.IntegrityError as error:
                raise CardSessionConflictError(
                    "Card session identity already exists"
                ) from error
            connection.commit()
            return session
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def get(self, session_id: str) -> CardSession | None:
        """Read and reconstruct one typed session."""
        normalized = str(session_id or "").strip()
        if not normalized:
            raise ValueError("session_id is required")
        connection = connect_existing(self._database_path, rows=True)
        try:
            row = connection.execute(
                "SELECT * FROM card_sessions WHERE session_id = ?",
                (normalized,),
            ).fetchone()
            return None if row is None else self._decode(row)
        finally:
            connection.close()

    def replace(
        self,
        session: CardSession,
        *,
        expected_revision: int,
    ) -> CardSession:
        """Replace one exact revision while preserving immutable source DNA."""
        if expected_revision < 1 or session.revision != expected_revision + 1:
            raise ValueError("replacement must advance exactly one revision")
        connection = connect_existing(self._database_path, rows=True)
        try:
            connection.execute("BEGIN IMMEDIATE")
            current_row = connection.execute(
                "SELECT * FROM card_sessions WHERE session_id = ?",
                (session.session_id,),
            ).fetchone()
            if current_row is None:
                raise CardSessionConflictError("Card session no longer exists")
            current = self._decode(current_row)
            if current.revision != expected_revision:
                raise CardSessionConflictError(
                    "Card session revision is stale"
                )
            if (
                current.source_image_uid != session.source_image_uid
                or current.source_content_hash != session.source_content_hash
                or current.semantic_profile != session.semantic_profile
                or current.imprint != session.imprint
            ):
                raise CardSessionConflictError(
                    "Card session immutable source facts changed"
                )
            values = self._values(session)
            cursor = connection.execute(
                """
                UPDATE card_sessions SET
                    revision = ?, source_image_uid = ?, source_content_hash = ?,
                    active_image_uid = ?, active_content_hash = ?,
                    active_image_kind = ?, active_visual_tier = ?,
                    operation_state = ?, semantic_profile_json = ?,
                    card_imprint_json = ?, structured_card_spec_json = ?,
                    visual_recipe_json = ?, presentation_json = ?,
                    presentation_status = ?, presentation_error_category = NULL,
                    updated_at = datetime('now')
                WHERE session_id = ? AND revision = ?
                """,
                (*values[1:], session.session_id, expected_revision),
            )
            if cursor.rowcount != 1:
                raise CardSessionConflictError(
                    "Card session revision is stale"
                )
            connection.execute(
                "DELETE FROM card_candidates WHERE session_id = ?",
                (session.session_id,),
            )
            connection.commit()
            return session
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    @staticmethod
    def _values(session: CardSession) -> tuple[object, ...]:
        presentation = session.presentation.presentation
        return (
            session.session_id,
            session.revision,
            session.source_image_uid,
            session.source_content_hash,
            session.active_image_uid,
            session.active_content_hash,
            session.active_image_kind.value,
            str(session.active_visual_tier),
            session.operation_state.value,
            encode_value(session.semantic_profile),
            encode_value(session.imprint),
            encode_value(session.card),
            encode_value(session.visual_recipe),
            None if presentation is None else encode_value(presentation),
            session.presentation.status.value,
        )

    @staticmethod
    def _decode(row: sqlite3.Row) -> CardSession:
        presentation_payload = row["presentation_json"]
        status = CardPresentationStatus(str(row["presentation_status"]))
        presentation = (
            None
            if presentation_payload is None
            else decode_presentation(str(presentation_payload))
        )
        return CardSession(
            session_id=str(row["session_id"]),
            revision=int(row["revision"]),
            source_image_uid=str(row["source_image_uid"]),
            source_content_hash=str(row["source_content_hash"]),
            semantic_profile=decode_semantic_profile(
                str(row["semantic_profile_json"])
            ),
            imprint=decode_imprint(str(row["card_imprint_json"])),
            card=decode_card_spec(str(row["structured_card_spec_json"])),
            visual_recipe=decode_visual_recipe(str(row["visual_recipe_json"])),
            presentation=CardPresentationResult(presentation, status),
            active_image_uid=str(row["active_image_uid"]),
            active_content_hash=str(row["active_content_hash"]),
            active_image_kind=CardActiveImageKind(
                str(row["active_image_kind"])
            ),
            active_visual_tier=int(row["active_visual_tier"]),
            operation_state=CardSessionOperationState(
                str(row["operation_state"])
            ),
        )
