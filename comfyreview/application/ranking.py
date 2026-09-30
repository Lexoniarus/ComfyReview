"""Application contracts for canonical image rankings."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RankingQuery:
    """Describe one Top/Worst image query."""

    model: str = ""
    subdir: str = ""
    set_key: str = ""
    mode: str = "top"
    minimum_ratings: int = 0
    limit: int = 128


@dataclass(frozen=True, slots=True)
class RankedImage:
    """Present one live canonical image and its review aggregate."""

    image_uid: str
    png_path: Path
    json_path: Path | None
    subdir: str
    model_branch: str
    checkpoint: str
    combo_key: str
    positive_prompt: str
    average_rating: float
    rating_count: int
    current_rating: int | None
    sampler: str | None
    scheduler: str | None
    steps: int | None
    cfg: float | None
    denoise: float | None
    assigned_set_key: str | None


class RankingRepository(Protocol):
    """Read live canonical image aggregates."""

    def list_ranked_images(self) -> tuple[RankedImage, ...]:
        """Return rated, non-deleted canonical images."""
        ...


class RankingService:
    """Apply stable ranking and gallery filters to canonical image facts."""

    def __init__(self, repository: RankingRepository) -> None:
        self._repository = repository

    def list_images(self, query: RankingQuery) -> tuple[RankedImage, ...]:
        """Return canonical images matching one Top/Worst query."""
        mode = str(query.mode or "top").strip().lower()
        if mode not in {"top", "worst"}:
            mode = "top"
        model = str(query.model or "").strip()
        selected_subdir = self._normalize_subdir(query.subdir)
        selected_set = str(query.set_key or "").strip()
        minimum = max(0, int(query.minimum_ratings))
        limit = max(0, int(query.limit))

        images = [
            image
            for image in self._repository.list_ranked_images()
            if (not model or image.model_branch == model)
            and self._matches_subdir(image.subdir, selected_subdir)
            and self._matches_set(image.assigned_set_key, selected_set)
            and image.rating_count >= minimum
        ]
        if mode == "top":
            images.sort(
                key=lambda image: (
                    -image.average_rating,
                    -image.rating_count,
                    image.image_uid,
                )
            )
        else:
            images.sort(
                key=lambda image: (
                    image.average_rating,
                    -image.rating_count,
                    image.image_uid,
                )
            )
        return tuple(images[:limit])

    @staticmethod
    def _normalize_subdir(value: str) -> str:
        normalized = str(value or "").replace("\\", "/").strip("/")
        parts = tuple(part for part in normalized.split("/") if part)
        if len(parts) >= 2 and parts[0].lower() == "playground":
            return f"playground/{parts[1]}"
        return normalized

    @classmethod
    def _matches_subdir(cls, candidate: str, selected: str) -> bool:
        normalized = cls._normalize_subdir(candidate)
        if selected:
            return normalized == selected
        character = normalized.rsplit("/", 1)[-1].strip().lower()
        return character != "empty"

    @staticmethod
    def _matches_set(candidate: str | None, selected: str) -> bool:
        if not selected:
            return True
        effective = str(candidate or "").strip()
        if selected == "unsorted":
            return not effective or effective == "unsorted"
        return effective == selected
