"""Read-side orchestration for Card Factory session projections."""

from __future__ import annotations

from dataclasses import dataclass

from comfyreview.application.card_battler_evolution import (
    CardCandidateRepository,
    CardEvolutionCandidate,
    CardEvolutionService,
)
from comfyreview.application.card_battler_session_service import (
    CardFactorySessionService,
)
from comfyreview.application.card_battler_sessions import (
    CardSession,
    CardSessionOperationState,
)


@dataclass(frozen=True, slots=True)
class CardFactorySessionSnapshot:
    """Return one session with its latest stable candidate slots."""

    session: CardSession
    candidates: tuple[CardEvolutionCandidate, ...]


class CardFactorySessionQueryService:
    """Synchronize active jobs and project one persisted Card session."""

    def __init__(
        self,
        *,
        sessions: CardFactorySessionService,
        evolution: CardEvolutionService,
        candidates: CardCandidateRepository,
    ) -> None:
        self._sessions = sessions
        self._evolution = evolution
        self._candidates = candidates

    def get(self, session_id: str) -> CardFactorySessionSnapshot:
        """Refresh submitted slots once before returning the latest snapshot."""
        session = self._sessions.get(session_id)
        if session.operation_state is CardSessionOperationState.GENERATING:
            self._evolution.synchronize(
                session.session_id,
                session_revision=session.revision,
            )
        return CardFactorySessionSnapshot(
            session=session,
            candidates=self._candidates.latest_for_session(session.session_id),
        )
