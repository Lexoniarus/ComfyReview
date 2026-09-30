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
class PromptProjection:
    """Legacy compatibility payload retained for old Arena callers."""

    json_path: Path
    run: int
    model_branch: str
    positive_prompt: str
    negative_prompt: str
    rating: int | None
    deleted: bool


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Return canonical review identity and projection scheduling result."""

    review_id: int
    run: int
    deleted: bool
    job_id: int


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

    def delete(self, review_id: int) -> None:
        """Remove one current review for compatibility compensation."""
        ...


class PromptRepository(Protocol):
    """Legacy compatibility port; canonical prompts are generation facts."""

    def save(self, projection: PromptProjection) -> None:
        """Accept a legacy request without duplicating token rows."""
        ...

    def delete(self, json_path: Path, run: int) -> None:
        """Accept compensation for a projection that is not persisted."""
        ...


class JobQueue(Protocol):
    """Request coalescing derived-projection catchup work."""

    def request_catchup(self) -> int:
        """Request catchup and return the queued or coalesced job ID."""
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
        jobs: JobQueue,
        deletions: OutputDeletionManager,
        preserve_deleted_files: bool,
        prompts: PromptRepository | None = None,
    ) -> None:
        self._image_resolver = image_resolver
        self._reviews = reviews
        self._prompts = prompts
        self._jobs = jobs
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
            if (
                self._prompts is not None
                and record.image.pair.json_path is not None
            ):
                self._prompts.save(self._prompt_projection(record, stored))
        except Exception as error:
            if stored is not None and self._prompts is not None:
                self._try_review_rollback(stored.review_id)
            if staged is not None:
                self._try_rollback(staged)
            self._logger.exception(
                "review.submission_failed",
                extra={"error_category": "canonical_write"},
            )
            raise ReviewMutationError(
                "Review mutation failed during canonical_write"
            ) from error

        job_id = (
            self._request_projection_catchup()
            if image.pair.json_path is not None
            else 0
        )
        if staged is not None:
            self._finalize_delete(staged)

        self._logger.info(
            "review.submission_completed",
            extra={"job_id": job_id},
        )
        return ReviewResult(
            review_id=stored.review_id,
            run=stored.run,
            deleted=command.delete,
            job_id=job_id,
        )

    @staticmethod
    def _validate(command: SubmitReviewCommand) -> int | None:
        if command.delete:
            return None
        if command.rating is None or not 1 <= command.rating <= 10:
            raise ReviewValidationError("rating must be between 1 and 10")
        return command.rating

    @staticmethod
    def _prompt_projection(
        record: ReviewRecord,
        stored: StoredReview,
    ) -> PromptProjection:
        image = record.image
        json_path = image.pair.json_path
        assert json_path is not None, "projection requires a JSON sidecar"
        return PromptProjection(
            json_path=json_path,
            run=stored.run,
            model_branch=image.model_branch,
            positive_prompt=image.positive_prompt,
            negative_prompt=image.negative_prompt,
            rating=record.rating,
            deleted=record.deleted,
        )

    def _request_projection_catchup(self) -> int:
        try:
            return self._jobs.request_catchup()
        except Exception:
            self._logger.exception(
                "review.projection_queue_failed",
                extra={"error_category": "projection_queue"},
            )
            return 0

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

    def _try_review_rollback(self, review_id: int) -> None:
        try:
            self._reviews.delete(review_id)
        except Exception:
            self._logger.exception(
                "review.compatibility_rollback_failed",
                extra={"error_category": "compatibility_rollback"},
            )

    def _try_rollback(self, staged: StagedDeletion) -> None:
        try:
            staged.rollback()
        except Exception:
            self._logger.exception(
                "review.delete_rollback_failed",
                extra={"error_category": "delete_rollback"},
            )
