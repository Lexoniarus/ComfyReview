"""Canonical image-context and scope-query application contracts."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol


class ScopeKind(StrEnum):
    """Identify one canonical prompt-component scope kind."""

    CHARACTER = "character"
    SCENE = "scene"
    OUTFIT = "outfit"
    POSE = "pose"
    EXPRESSION = "expression"
    LIGHTING = "lighting"
    MODIFIER = "modifier"


class ImageClassification(StrEnum):
    """Select images by canonical composition availability."""

    ALL = "all"
    CLASSIFIED = "classified"
    UNCLASSIFIED = "unclassified"


class ImageOrder(StrEnum):
    """Select one stable database-side image ordering."""

    RECENT = "recent"
    TOP = "top"
    WORST = "worst"


class ImageQueryValidationError(ValueError):
    """Reject invalid canonical image-query input."""


class ImageContextNotFoundError(LookupError):
    """Report an unknown canonical image identity."""


@dataclass(frozen=True, slots=True)
class ImageScope:
    """Describe one exact catalog revision used by a generation."""

    kind: ScopeKind
    component_uid: str
    revision_uid: str
    name: str
    position: int


@dataclass(frozen=True, slots=True)
class ScopeSelection:
    """Hold selected canonical component identities."""

    component_uids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ImageFilter:
    """Describe canonical image filters shared by V2 query surfaces."""

    scopes: ScopeSelection = ScopeSelection()
    classification: ImageClassification = ImageClassification.ALL
    model: str = ""
    checkpoint: str = ""
    set_key: str = ""
    minimum_average_rating: float | None = None
    minimum_rating_count: int = 0


@dataclass(frozen=True, slots=True)
class ImageQuery:
    """Describe one paginated canonical image query."""

    filters: ImageFilter = ImageFilter()
    order: ImageOrder = ImageOrder.RECENT
    offset: int = 0
    limit: int = 48


@dataclass(frozen=True, slots=True)
class PromptSnapshot:
    """Preserve the exact prompts used for a historical generation."""

    positive: str
    negative: str
    draft_overridden: bool


@dataclass(frozen=True, slots=True)
class GenerationSettings:
    """Expose normalized generation settings for inspection."""

    model: str
    checkpoint: str
    seed: int | None
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None


@dataclass(frozen=True, slots=True)
class WorkflowProvenance:
    """Expose reproducibility identifiers without raw workflow payloads."""

    blueprint_uid: str | None
    blueprint_version: int | None
    graph_hash: str | None


@dataclass(frozen=True, slots=True)
class ReviewSummary:
    """Describe the effective live review state of an image."""

    current_rating: int | None
    rating_count: int
    average_rating: float | None


@dataclass(frozen=True, slots=True)
class CurationSummary:
    """Describe the current canonical curation assignment."""

    set_key: str
    assigned_at: str


@dataclass(frozen=True, slots=True)
class ImageContext:
    """Expose canonical image facts without HTTP or local-path contracts."""

    image_uid: str
    generation_uid: str
    classification: ImageClassification
    scopes: tuple[ImageScope, ...]
    prompt_snapshot: PromptSnapshot
    generation_settings: GenerationSettings
    workflow: WorkflowProvenance
    output_role: str
    output_index: int
    review: ReviewSummary
    curation: CurationSummary | None


@dataclass(frozen=True, slots=True)
class ImagePage:
    """Return one bounded page of canonical image contexts."""

    entries: tuple[ImageContext, ...]
    total: int
    offset: int
    limit: int


@dataclass(frozen=True, slots=True)
class ScopeFacet:
    """Describe one filterable canonical prompt component."""

    kind: ScopeKind
    component_uid: str
    revision_uid: str
    name: str
    archived: bool
    count: int


class ImageContextRepository(Protocol):
    """Read canonical image contexts with database-side filtering."""

    def unknown_scope_uids(
        self,
        component_uids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return requested component identities absent from the catalog."""
        ...

    def list_images(self, query: ImageQuery) -> ImagePage:
        """Return a filtered and paginated canonical image page."""
        ...

    def get_image(self, image_uid: str) -> ImageContext | None:
        """Return one canonical image context when it exists."""
        ...


class ScopeFacetRepository(Protocol):
    """Count canonical scopes using database-side filtering."""

    def unknown_scope_uids(
        self,
        component_uids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return requested component identities absent from the catalog."""
        ...

    def list_facets(self, filters: ImageFilter) -> tuple[ScopeFacet, ...]:
        """Return contextual counts for every canonical scope."""
        ...


class ReviewCandidateRepository(Protocol):
    """Select one review candidate from canonical image facts."""

    def unknown_scope_uids(
        self,
        component_uids: tuple[str, ...],
    ) -> tuple[str, ...]:
        """Return requested component identities absent from the catalog."""
        ...

    def next_candidate(self, filters: ImageFilter) -> ImageContext | None:
        """Return the next matching live image when available."""
        ...


class ImageContextQueryService:
    """Validate and orchestrate canonical image-context queries."""

    def __init__(self, repository: ImageContextRepository) -> None:
        self._repository = repository

    def list_images(self, query: ImageQuery) -> ImagePage:
        """Return one validated canonical image page."""
        if query.offset < 0:
            raise ImageQueryValidationError("offset must not be negative")
        if not 1 <= query.limit <= 100:
            raise ImageQueryValidationError("limit must be between 1 and 100")
        filters = _normalize_filter(query.filters)
        _validate_scope_selection(self._repository, filters.scopes)
        return self._repository.list_images(replace(query, filters=filters))

    def get_image(self, image_uid: str) -> ImageContext:
        """Return one canonical image or report a missing stable identity."""
        normalized_uid = str(image_uid or "").strip()
        if not normalized_uid:
            raise ImageQueryValidationError("image_uid is required")
        image = self._repository.get_image(normalized_uid)
        if image is None:
            raise ImageContextNotFoundError(
                f"unknown canonical image: {normalized_uid}"
            )
        return image


class ScopeFacetService:
    """Validate filters and request contextual SQL facet counts."""

    def __init__(self, repository: ScopeFacetRepository) -> None:
        self._repository = repository

    def list_facets(self, filters: ImageFilter) -> tuple[ScopeFacet, ...]:
        """Return canonical scope facets for one normalized context."""
        normalized = _normalize_filter(filters)
        _validate_scope_selection(self._repository, normalized.scopes)
        return self._repository.list_facets(normalized)


class ReviewCandidateService:
    """Select review candidates without presentation or path heuristics."""

    def __init__(self, repository: ReviewCandidateRepository) -> None:
        self._repository = repository

    def next_candidate(self, filters: ImageFilter) -> ImageContext | None:
        """Return the next candidate matching one canonical filter."""
        normalized = _normalize_filter(filters)
        _validate_scope_selection(self._repository, normalized.scopes)
        return self._repository.next_candidate(normalized)


def _normalize_filter(filters: ImageFilter) -> ImageFilter:
    component_uids = tuple(
        sorted(
            {
                str(component_uid or "").strip()
                for component_uid in filters.scopes.component_uids
                if str(component_uid or "").strip()
            }
        )
    )
    return replace(
        filters,
        scopes=ScopeSelection(component_uids),
        model=str(filters.model or "").strip(),
        checkpoint=str(filters.checkpoint or "").strip(),
        set_key=str(filters.set_key or "").strip(),
        minimum_rating_count=max(0, int(filters.minimum_rating_count)),
    )


def _validate_scope_selection(
    repository: ImageContextRepository
    | ScopeFacetRepository
    | ReviewCandidateRepository,
    selection: ScopeSelection,
) -> None:
    unknown = repository.unknown_scope_uids(selection.component_uids)
    if unknown:
        raise ImageQueryValidationError(
            f"unknown scope component_uid: {', '.join(unknown)}"
        )
