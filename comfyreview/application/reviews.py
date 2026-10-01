"""Typed application contracts and orchestration for image reviews."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ReviewValidationError(ValueError):
    """Reject a review command before any mutation starts."""


class ReviewMutationError(RuntimeError):
    """Report a failed canonical review mutation."""


class ReviewHistoryNotFoundError(LookupError):
    """Report that no canonical image exists for a history query."""


class InvalidOutputPathError(ValueError):
    """Reject a submitted path outside the configured output boundary."""


class OutputPairNotFoundError(FileNotFoundError):
    """Report that a referenced output pair no longer exists."""


class OutputMutationError(RuntimeError):
    """Report a filesystem mutation that could not complete safely."""


@dataclass(frozen=True, slots=True)
class OutputImageReference:
    """Identify one canonical output image by stable UID."""

    image_uid: str

    @classmethod
    def from_client_uid(cls, image_uid: str) -> OutputImageReference:
        """Validate a stable image UID received at an HTTP boundary."""
        uid = str(image_uid or "").strip()
        if not uid:
            raise ReviewValidationError("image_uid is required")
        return cls(image_uid=uid)


@dataclass(frozen=True, slots=True)
class OutputPair:
    """Identify provider-validated output files."""

    png_path: Path
    json_path: Path | None


@dataclass(frozen=True, slots=True)
class ReviewImage:
    """Carry normalized generation data into review persistence."""

    pair: OutputPair
    model_branch: str
    checkpoint: str
    combo_key: str
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None
    loras_json: str
    positive_prompt: str
    negative_prompt: str
    image_uid: str
    generation_uid: str
    output_node_id: str = "legacy_sidecar"
    output_index: int = 0


@dataclass(frozen=True, slots=True)
class SubmitReviewCommand:
    """Request either a scored review or a delete observation."""

    image: OutputImageReference
    rating: int | None
    delete: bool = False


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Describe one current review mutation for a resolved generation."""

    image: ReviewImage
    rating: int | None
    deleted: bool


@dataclass(frozen=True, slots=True)
class StoredReview:
    """Identify the current canonical review revision."""

    review_id: int
    run: int


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Return the identity and state of one canonical review mutation."""

    review_id: int
    run: int
    deleted: bool


@dataclass(frozen=True, slots=True)
class ReviewHistoryEntry:
    """Describe one immutable canonical review event."""

    event_uid: str
    event_type: str
    rating: int | None
    sequence: int
    reviewed_at: str


class ReviewImageResolver(Protocol):
    """Resolve client references into authoritative generation data."""

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        """Return a validated and normalized review image."""
        ...


class ReviewRepository(Protocol):
    """Persist current reviews and their normalized generation facts."""

    def append(self, record: ReviewRecord) -> StoredReview:
        """Apply one review mutation and return its canonical revision."""
        ...


class ReviewHistoryRepository(Protocol):
    """Read append-only review history by canonical image identity."""

    def list_for_image(
        self, image_uid: str
    ) -> tuple[ReviewHistoryEntry, ...] | None:
        """Return ordered events or None when the image does not exist."""
        ...


class StagedDeletion(Protocol):
    """Control a reversible output-pair deletion."""

    def rollback(self) -> None:
        """Restore both staged files to their original locations."""
        ...

    def finalize(self, *, preserve_in_trash: bool) -> None:
        """Complete the deletion and optionally retain trash files."""
        ...


class OutputDeletionManager(Protocol):
    """Stage reversible mutations of provider-validated output pairs."""

    def stage(self, pair: OutputPair) -> StagedDeletion:
        """Move the pair out of the live output tree reversibly."""
        ...


class ReviewService:
    """Coordinate canonical review persistence and output deletion."""

    def __init__(
        self,
        *,
        image_resolver: ReviewImageResolver,
        reviews: ReviewRepository,
        deletions: OutputDeletionManager,
        preserve_deleted_files: bool,
    ) -> None:
        self._image_resolver = image_resolver
        self._reviews = reviews
        self._deletions = deletions
        self._preserve_deleted_files = preserve_deleted_files
        self._logger = logging.getLogger("comfyreview.review")

    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        """Apply one review; derived-projection scheduling is best effort."""
        rating = self._validate(command)
        self._logger.info("review.submission_started")
        image = self._image_resolver.resolve(command.image)
        record = ReviewRecord(
            image=image,
            rating=rating,
            deleted=command.delete,
        )
        staged: StagedDeletion | None = None
        stored: StoredReview | None = None
        try:
            if command.delete:
                staged = self._deletions.stage(image.pair)
            stored = self._reviews.append(record)
        except Exception as error:
            if staged is not None:
                self._try_rollback(staged)
            self._logger.exception(
                "review.submission_failed",
                extra={"error_category": "canonical_write"},
            )
            raise ReviewMutationError(
                "Review mutation failed during canonical_write"
            ) from error

        if staged is not None:
            self._finalize_delete(staged)

        self._logger.info("review.submission_completed")
        return ReviewResult(
            review_id=stored.review_id,
            run=stored.run,
            deleted=command.delete,
        )

    @staticmethod
    def _validate(command: SubmitReviewCommand) -> int | None:
        if command.delete:
            return None
        if command.rating is None or not 1 <= command.rating <= 10:
            raise ReviewValidationError("rating must be between 1 and 10")
        return command.rating

    def _finalize_delete(self, staged: StagedDeletion) -> None:
        try:
            staged.finalize(
                preserve_in_trash=self._preserve_deleted_files,
            )
        except Exception:
            self._logger.exception(
                "review.delete_finalize_failed",
                extra={"error_category": "delete_finalize"},
            )

    def _try_rollback(self, staged: StagedDeletion) -> None:
        try:
            staged.rollback()
        except Exception:
            self._logger.exception(
                "review.delete_rollback_failed",
                extra={"error_category": "delete_rollback"},
            )


class ReviewHistoryService:
    """Expose canonical review history without mutation concerns."""

    def __init__(self, repository: ReviewHistoryRepository) -> None:
        self._repository = repository

    def list_for_image(self, image_uid: str) -> tuple[ReviewHistoryEntry, ...]:
        """Return review events for one validated canonical image UID."""
        normalized_uid = str(image_uid or "").strip()
        if not normalized_uid:
            raise ReviewValidationError("image_uid is required")
        entries = self._repository.list_for_image(normalized_uid)
        if entries is None:
            raise ReviewHistoryNotFoundError(
                f"unknown canonical image: {normalized_uid}"
            )
        return entries
