"""Application contracts for visual prompt-catalog evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CatalogEvidenceImage:
    """Describe one ranked canonical image for a catalog component."""

    image_uid: str
    average_rating: float | None
    rating_count: int


class CatalogEvidenceRepository(Protocol):
    """Read ranked image evidence for canonical prompt components."""

    def list_top_images(
        self,
        component_uid: str,
        *,
        limit: int,
    ) -> tuple[CatalogEvidenceImage, ...]:
        """Return top live images in deterministic ranking order."""
        ...


class CatalogEvidenceService:
    """Validate and expose bounded visual evidence for catalog entries."""

    def __init__(self, repository: CatalogEvidenceRepository) -> None:
        self._repository = repository

    def list_top_images(
        self,
        component_uid: str,
        *,
        limit: int = 3,
    ) -> tuple[CatalogEvidenceImage, ...]:
        """Return at most three ranked images for one stable component."""
        normalized_uid = str(component_uid).strip()
        if not normalized_uid:
            raise ValueError("component_uid is required")
        if limit < 1 or limit > 3:
            raise ValueError("catalog evidence limit must be between 1 and 3")
        return self._repository.list_top_images(
            normalized_uid,
            limit=limit,
        )
