"""Typed application contracts and orchestration for image reviews."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class ReviewValidationError(ValueError):
    """Reject a review command before any mutation starts."""


class ReviewMutationError(RuntimeError):
    """Report a failed review workflow after compensation was attempted."""


@dataclass(frozen=True, slots=True)
class OutputImageReference:
    """Represent an untrusted client reference to one PNG/JSON pair."""

    png_path: Path
    json_path: Path

    @classmethod
    def from_client_paths(
        cls,
        *,
        png_path: str,
        json_path: str,
    ) -> OutputImageReference:
        """Validate pair syntax without asserting root membership or existence."""
        if not png_path.strip() or not json_path.strip():
            raise ReviewValidationError("Output pair paths are required")
        png = Path(png_path)
        sidecar = Path(json_path)
        if png.suffix.lower() != ".png" or sidecar.suffix.lower() != ".json":
            raise ReviewValidationError("Expected a PNG and JSON sidecar pair")
        if png.parent != sidecar.parent or png.stem != sidecar.stem:
            raise ReviewValidationError("PNG and JSON sidecar do not match")
        return cls(png_path=png, json_path=sidecar)


@dataclass(frozen=True, slots=True)
class OutputPair:
    """Identify one provider-validated PNG/JSON output pair."""

    png_path: Path
    json_path: Path


@dataclass(frozen=True, slots=True)
class ReviewImage:
    """Carry authoritative, normalized sidecar data into the review use case."""

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


@dataclass(frozen=True, slots=True)
class SubmitReviewCommand:
    """Request either a scored review or a delete tombstone."""

    image: OutputImageReference
    rating: int | None
    delete: bool = False


@dataclass(frozen=True, slots=True)
class ReviewRecord:
    """Describe the canonical values written to the legacy ratings store."""

    image: ReviewImage
    rating: int | None
    deleted: bool


@dataclass(frozen=True, slots=True)
class StoredReview:
    """Identify one persisted legacy review event and its assigned run."""

    review_id: int
    run: int


@dataclass(frozen=True, slots=True)
class PromptProjection:
    """Describe prompt-token rows derived from one persisted review run."""

    json_path: Path
    run: int
    model_branch: str
    positive_prompt: str
    negative_prompt: str
    rating: int | None
    deleted: bool


@dataclass(frozen=True, slots=True)
class ReviewResult:
    """Return the persisted review identity and queued projection work."""

    review_id: int
    run: int
    deleted: bool
    job_id: int


class ReviewImageResolver(Protocol):
    """Resolve client references into authoritative sidecar-backed data."""

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        """Return a validated and normalized review image."""
        ...


class ReviewRepository(Protocol):
    """Persist and compensate legacy review events."""

    def append(self, record: ReviewRecord) -> StoredReview:
        """Append one review event and return its exact ID and run."""
        ...

    def delete(self, review_id: int) -> None:
        """Delete one review event during compensation."""
        ...


class PromptRepository(Protocol):
    """Persist and compensate the legacy prompt-token projection."""

    def save(self, projection: PromptProjection) -> None:
        """Write prompt tokens for one exact review run."""
        ...

    def delete(self, json_path: Path, run: int) -> None:
        """Delete prompt rows for one compensated review run."""
        ...


class JobQueue(Protocol):
    """Request coalescing legacy projection catchup work."""

    def request_catchup(self) -> int:
        """Request catchup and return the queued or coalesced job ID."""
        ...


class StagedDeletion(Protocol):
    """Control a reversible output-pair deletion."""

    def rollback(self) -> None:
        """Restore the staged pair to its original location."""
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
    """Coordinate review persistence across current legacy boundaries."""

    def __init__(
        self,
        *,
        image_resolver: ReviewImageResolver,
        reviews: ReviewRepository,
        prompts: PromptRepository,
        jobs: JobQueue,
        deletions: OutputDeletionManager,
        preserve_deleted_files: bool,
    ) -> None:
        self._image_resolver = image_resolver
        self._reviews = reviews
        self._prompts = prompts
        self._jobs = jobs
        self._deletions = deletions
        self._preserve_deleted_files = preserve_deleted_files
        self._logger = logging.getLogger("comfyreview.review")

    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        """Persist one review workflow or compensate all completed steps."""
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
        prompt_attempted = False
        phase = "delete_stage" if command.delete else "review_write"
        try:
            if command.delete:
                staged = self._deletions.stage(image.pair)
                phase = "review_write"
            stored = self._reviews.append(record)
            projection = self._prompt_projection(record, stored)
            phase = "prompt_write"
            prompt_attempted = True
            self._prompts.save(projection)
            phase = "queue_enqueue"
            job_id = self._jobs.request_catchup()
            if staged is not None:
                phase = "delete_finalize"
                staged.finalize(preserve_in_trash=self._preserve_deleted_files)
        except Exception as error:
            self._logger.exception(
                "review.submission_failed",
                extra={"error_category": phase},
            )
            self._compensate(
                image=image,
                stored=stored,
                prompt_attempted=prompt_attempted,
                staged=staged,
            )
            raise ReviewMutationError(
                f"Review mutation failed during {phase}"
            ) from error

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
        return PromptProjection(
            json_path=image.pair.json_path,
            run=stored.run,
            model_branch=image.model_branch,
            positive_prompt=image.positive_prompt,
            negative_prompt=image.negative_prompt,
            rating=record.rating,
            deleted=record.deleted,
        )

    def _compensate(
        self,
        *,
        image: ReviewImage,
        stored: StoredReview | None,
        prompt_attempted: bool,
        staged: StagedDeletion | None,
    ) -> None:
        if prompt_attempted and stored is not None:
            self._try_compensation(
                "prompt_delete",
                lambda: self._prompts.delete(
                    image.pair.json_path,
                    stored.run,
                ),
            )
        if stored is not None:
            self._try_compensation(
                "review_delete",
                lambda: self._reviews.delete(stored.review_id),
            )
        if staged is not None:
            self._try_compensation("delete_rollback", staged.rollback)

    def _try_compensation(
        self,
        phase: str,
        operation: Callable[[], None],
    ) -> None:
        try:
            operation()
        except Exception:
            self._logger.exception(
                "review.compensation_failed",
                extra={"error_category": phase},
            )
