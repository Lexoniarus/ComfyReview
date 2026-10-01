"""Application contracts and orchestration for canonical Arena decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.image_queries import (
    ImageContext,
    ImageContextQueryService,
    ImageQuery,
)


class ArenaValidationError(ValueError):
    """Reject an invalid or stale Arena decision."""


class ArenaMutationError(RuntimeError):
    """Report a failed atomic Arena mutation."""


@dataclass(frozen=True, slots=True)
class ArenaQuery:
    """Describe one bounded canonical image pool for pair selection."""

    images: ImageQuery


@dataclass(frozen=True, slots=True)
class ArenaPair:
    """Present one directed pair of canonical images."""

    left: ImageContext
    right: ImageContext


@dataclass(frozen=True, slots=True)
class RecordArenaDecisionCommand:
    """Record the winning side for a stable canonical image pair."""

    left_image_uid: str
    right_image_uid: str
    winner_side: str


@dataclass(frozen=True, slots=True)
class ArenaCompetitor:
    """Carry transaction-time state required to score one competitor."""

    image_uid: str
    average_rating: float


@dataclass(frozen=True, slots=True)
class ArenaDecision:
    """Carry a validated decision and its generated ratings to persistence."""

    command: RecordArenaDecisionCommand
    winner_rating: int
    loser_rating: int


@dataclass(frozen=True, slots=True)
class ArenaResult:
    """Describe an atomically persisted Arena match."""

    match_uid: str
    winner_image_uid: str
    winner_rating: int
    loser_rating: int


class ArenaRepository(Protocol):
    """Read pair history and atomically persist Arena facts."""

    def list_played_directions(
        self,
        image_uids: tuple[str, ...],
    ) -> frozenset[tuple[str, str]]:
        """Return directed pairings already present in canonical storage."""
        ...

    def get_competitors(
        self,
        left_image_uid: str,
        right_image_uid: str,
    ) -> tuple[ArenaCompetitor, ArenaCompetitor]:
        """Return live aggregate state for a submitted pair."""
        ...

    def save_decision(self, decision: ArenaDecision) -> ArenaResult:
        """Persist match and generated rating events atomically."""
        ...


class ArenaService:
    """Select pairs and coordinate canonical Arena decisions."""

    def __init__(
        self,
        *,
        images: ImageContextQueryService,
        repository: ArenaRepository,
    ) -> None:
        self._images = images
        self._repository = repository

    def next_pair(self, query: ArenaQuery) -> ArenaPair | None:
        """Return the next unplayed directed pair from the ranked pool."""
        images = self._images.list_images(query.images).entries
        directions = self._repository.list_played_directions(
            tuple(image.image_uid for image in images)
        )
        for left_index, left in enumerate(images):
            for right in images[left_index + 1 :]:
                if (left.image_uid, right.image_uid) not in directions:
                    return ArenaPair(left=left, right=right)
                if (right.image_uid, left.image_uid) not in directions:
                    return ArenaPair(left=right, right=left)
        return None

    def record_decision(
        self,
        command: RecordArenaDecisionCommand,
    ) -> ArenaResult:
        """Validate and atomically record one Arena result."""
        left_uid = str(command.left_image_uid or "").strip()
        right_uid = str(command.right_image_uid or "").strip()
        if not left_uid or not right_uid or left_uid == right_uid:
            raise ArenaValidationError("Arena requires two distinct images")
        if command.winner_side not in {"left", "right"}:
            raise ArenaValidationError("winner_side must be 'left' or 'right'")

        left, right = self._repository.get_competitors(
            left_uid,
            right_uid,
        )
        high = max(left.average_rating, right.average_rating)
        low = min(left.average_rating, right.average_rating)
        decision = ArenaDecision(
            command=RecordArenaDecisionCommand(
                left_image_uid=left_uid,
                right_image_uid=right_uid,
                winner_side=command.winner_side,
            ),
            winner_rating=self._clamp_rating(high + 2.0),
            loser_rating=self._clamp_rating(low - 2.0),
        )
        return self._repository.save_decision(decision)

    @staticmethod
    def _clamp_rating(value: float) -> int:
        return min(10, max(1, int(round(value))))
