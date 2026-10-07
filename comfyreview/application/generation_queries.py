"""Canonical generation lifecycle read contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


class GenerationQueryValidationError(ValueError):
    """Reject invalid canonical generation query input."""


class GenerationNotFoundError(LookupError):
    """Report an unknown canonical generation identity."""


@dataclass(frozen=True, slots=True)
class GenerationOutputSummary:
    """Describe one canonical output without exposing its file path."""

    image_uid: str
    role: str
    node_id: str
    output_index: int
    content_hash: str


@dataclass(frozen=True, slots=True)
class GenerationStageSummary:
    """Describe one normalized sampler stage."""

    role: str
    node_id: str
    order: int
    seed: int | None
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None


@dataclass(frozen=True, slots=True)
class GenerationSummary:
    """Describe one persisted generation lifecycle entry."""

    generation_uid: str
    status: str
    prompt_id: str | None
    source: str
    model: str
    checkpoint: str
    blueprint_uid: str | None
    blueprint_version: int | None
    graph_hash: str | None
    created_at: str
    submitted_at: str | None
    started_at: str | None
    completed_at: str | None
    output_count: int
    failure_reason: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationDetail:
    """Expose reproducible generation facts and collected outputs."""

    summary: GenerationSummary
    positive_prompt: str
    negative_prompt: str
    revision_uids: tuple[str, ...]
    sampler_stages: tuple[GenerationStageSummary, ...]
    outputs: tuple[GenerationOutputSummary, ...]


@dataclass(frozen=True, slots=True)
class GenerationPage:
    """Return one bounded page of persisted lifecycle entries."""

    entries: tuple[GenerationSummary, ...]
    total: int
    offset: int
    limit: int


class GenerationQueryRepository(Protocol):
    """Read canonical generation lifecycle and provenance facts."""

    def list_generations(
        self,
        *,
        status: str,
        offset: int,
        limit: int,
    ) -> GenerationPage:
        """Return a database-filtered generation page."""
        ...

    def get_generation(self, generation_uid: str) -> GenerationDetail | None:
        """Return one generation detail when it exists."""
        ...


class GenerationQueryService:
    """Validate and orchestrate canonical generation reads."""

    _STATUSES = frozenset(
        {
            "prepared",
            "submitting",
            "submitted",
            "running",
            "completed",
            "failed",
            "cancelled",
            "reconciliation_required",
        }
    )

    def __init__(self, repository: GenerationQueryRepository) -> None:
        self._repository = repository

    def list_generations(
        self,
        *,
        status: str = "",
        offset: int = 0,
        limit: int = 48,
    ) -> GenerationPage:
        """Return one validated lifecycle page without inventing queue state."""
        normalized_status = str(status or "").strip()
        if normalized_status and normalized_status not in self._STATUSES:
            raise GenerationQueryValidationError(
                f"unknown generation status: {normalized_status}"
            )
        if offset < 0:
            raise GenerationQueryValidationError("offset must not be negative")
        if not 1 <= limit <= 100:
            raise GenerationQueryValidationError(
                "limit must be between 1 and 100"
            )
        return self._repository.list_generations(
            status=normalized_status,
            offset=offset,
            limit=limit,
        )

    def get_generation(self, generation_uid: str) -> GenerationDetail:
        """Return one canonical generation by stable identity."""
        normalized_uid = str(generation_uid or "").strip()
        if not normalized_uid:
            raise GenerationQueryValidationError("generation_uid is required")
        generation = self._repository.get_generation(normalized_uid)
        if generation is None:
            raise GenerationNotFoundError(
                f"unknown canonical generation: {normalized_uid}"
            )
        return generation
