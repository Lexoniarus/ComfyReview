"""Application contracts and orchestration for canonical Arena decisions."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.image_queries import (
    ImageContext,
    ImageContextQueryService,
    ImageQuery,
)
from comfyreview.application.prompt_variant_promotion import (
    PromptPromotionTrigger,
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
class ArenaImageRotation:
    """Describe the latest canonical Arena match containing one image."""

    image_uid: str
    last_match_order: int | None


@dataclass(frozen=True, slots=True)
class ArenaPairingHistory:
    """Carry directed match history and per-image rotation positions."""

    played_directions: frozenset[tuple[str, str]]
    rotations: tuple[ArenaImageRotation, ...]


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
    promotion_pending: bool = False


class ArenaRepository(Protocol):
    """Read pair history and atomically persist Arena facts."""

    def pairing_history(
        self,
        image_uids: tuple[str, ...],
    ) -> ArenaPairingHistory:
        """Return canonical pairing and rotation history for one pool."""
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


class FairArenaPairingPolicy:
    """Select the longest-waiting eligible directed Arena pair."""

    def select(
        self,
        images: tuple[ImageContext, ...],
        history: ArenaPairingHistory,
    ) -> ArenaPair | None:
        """Return a stable fair pair without mutating rotation state."""
        pool_rank = {
            image.image_uid: index for index, image in enumerate(images)
        }
        last_match = {
            item.image_uid: item.last_match_order for item in history.rotations
        }
        ordered = tuple(
            sorted(
                images,
                key=lambda image: (
                    self._rotation_order(last_match.get(image.image_uid)),
                    pool_rank[image.image_uid],
                    image.image_uid,
                ),
            )
        )
        for left_index, left in enumerate(ordered):
            for right in ordered[left_index + 1 :]:
                forward = (left.image_uid, right.image_uid)
                reverse = (right.image_uid, left.image_uid)
                if forward not in history.played_directions:
                    return ArenaPair(left=left, right=right)
                if reverse not in history.played_directions:
                    return ArenaPair(left=right, right=left)
        return None

    @staticmethod
    def _rotation_order(last_match_order: int | None) -> int:
        return -1 if last_match_order is None else last_match_order


class ArenaService:
    """Select pairs and coordinate canonical Arena decisions."""

    def __init__(
        self,
        *,
        images: ImageContextQueryService,
        repository: ArenaRepository,
        pairing: FairArenaPairingPolicy | None = None,
        prompt_promotions: PromptPromotionTrigger | None = None,
    ) -> None:
        self._images = images
        self._repository = repository
        self._pairing = pairing or FairArenaPairingPolicy()
        self._prompt_promotions = prompt_promotions
        self._logger = logging.getLogger("comfyreview.arena")

    def next_pair(self, query: ArenaQuery) -> ArenaPair | None:
        """Return the next unplayed directed pair from the ranked pool."""
        images = self._images.list_images(query.images).entries
        history = self._repository.pairing_history(
            tuple(image.image_uid for image in images)
        )
        return self._pairing.select(images, history)

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
        result = self._repository.save_decision(decision)
        pending_by_image = tuple(
            self._reconcile_prompt_promotions(image_uid)
            for image_uid in (left_uid, right_uid)
        )
        pending = any(pending_by_image)
        if not pending:
            return result
        return ArenaResult(
            match_uid=result.match_uid,
            winner_image_uid=result.winner_image_uid,
            winner_rating=result.winner_rating,
            loser_rating=result.loser_rating,
            promotion_pending=True,
        )

    def _reconcile_prompt_promotions(self, image_uid: str) -> bool:
        if self._prompt_promotions is None:
            return False
        try:
            self._prompt_promotions.reconcile_image(image_uid)
        except Exception:
            self._logger.exception(
                "arena.prompt_promotion_pending",
                extra={"image_uid": image_uid},
            )
            return True
        return False

    @staticmethod
    def _clamp_rating(value: float) -> int:
        return min(10, max(1, int(round(value))))
