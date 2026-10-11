"""Application facade for revision-safe Card Factory prototype commands."""

from __future__ import annotations

from comfyreview.application.card_battler_evolution import CardEvolutionService
from comfyreview.application.card_battler_session_queries import (
    CardFactorySessionQueryService,
    CardFactorySessionSnapshot,
)
from comfyreview.application.card_battler_session_service import (
    CardFactorySessionService,
)


class CardFactoryPrototypeService:
    """Expose one cohesive command/query boundary to the HTTP adapter."""

    def __init__(
        self,
        *,
        sessions: CardFactorySessionService,
        queries: CardFactorySessionQueryService,
        evolution: CardEvolutionService,
    ) -> None:
        self._sessions = sessions
        self._queries = queries
        self._evolution = evolution

    def create(self, image_uid: str) -> CardFactorySessionSnapshot:
        """Create and return one initial persistent prototype session."""
        session = self._sessions.create(image_uid)
        return CardFactorySessionSnapshot(session, ())

    def get(self, session_id: str) -> CardFactorySessionSnapshot:
        """Return one current session after one bounded synchronization pass."""
        return self._queries.get(session_id)

    def develop(
        self, session_id: str, *, expected_revision: int
    ) -> CardFactorySessionSnapshot:
        """Advance one accepted session and return its cleared next tier."""
        session = self._sessions.develop(
            session_id,
            expected_revision=expected_revision,
        )
        return CardFactorySessionSnapshot(session, ())

    def generate_candidates(
        self, session_id: str, *, expected_revision: int
    ) -> CardFactorySessionSnapshot:
        """Reserve and submit four slots without re-running Stage 1."""
        candidates = self._evolution.generate_candidates(
            session_id,
            expected_revision=expected_revision,
        )
        session = self._sessions.get(session_id)
        return CardFactorySessionSnapshot(session, candidates)

    def accept_candidate(
        self,
        session_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardFactorySessionSnapshot:
        """Accept one current completed slot and return the updated session."""
        session = self._evolution.accept(
            session_id,
            candidate_id,
            expected_revision=expected_revision,
        )
        return self._queries.get(session.session_id)
