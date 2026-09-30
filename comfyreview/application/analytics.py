"""Application contracts for canonical statistics and observed combinations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AnalyticsImage:
    """Describe one live canonical image used in statistics views."""

    png_path: Path
    json_path: Path | None
    average_rating: float | None
    rating_count: int


@dataclass(frozen=True, slots=True)
class PromptTokenStatistic:
    """Describe direct canonical rating evidence for one prompt atom."""

    token: str
    sample_count: int
    mean_score: float
    lower_bound: float


@dataclass(frozen=True, slots=True)
class PromptMatchPreview:
    """Describe the best live image matching requested prompt atoms."""

    json_path: Path | None
    png_path: Path
    token_hits: int
    average_rating: float | None
    rating_count: int


@dataclass(frozen=True, slots=True)
class ObservedPromptCombination:
    """Describe one actually generated legacy-compatible prompt combination."""

    combo_key: str
    combo_size: int
    character_id: int
    scene_id: int
    outfit_id: int | None
    label: str
    average_rating: float | None
    image_count: int
    total_rating_count: int
    best_images: tuple[AnalyticsImage, ...]


class AnalyticsRepository(Protocol):
    """Read statistics directly from canonical facts and projections."""

    def list_prompt_token_statistics(
        self,
        *,
        model_branch: str,
        scope: str,
        minimum_samples: int,
        limit: int,
    ) -> tuple[PromptTokenStatistic, ...]:
        """Return prompt-token statistics without a materialized database."""
        ...

    def list_selected_prompt_token_statistics(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str,
        scope: str,
    ) -> tuple[PromptTokenStatistic, ...]:
        """Return statistics for requested canonical prompt atoms."""
        ...

    def find_best_prompt_match(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str,
        scope: str,
        minimum_hits: int,
        minimum_ratings: int,
        candidate_limit: int,
    ) -> PromptMatchPreview | None:
        """Return the strongest live image matching requested atoms."""
        ...

    def list_best_images_for_combos(
        self,
        combo_keys: tuple[str, ...],
        *,
        model_branch: str,
        limit_per_combo: int,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Return live images grouped by observed combo key."""
        ...

    def list_best_images_for_parameter(
        self,
        parameter: str,
        values: tuple[str, ...],
        *,
        model_branch: str,
        limit_per_value: int,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Return live images grouped by a supported render parameter."""
        ...

    def list_observed_combinations(
        self,
        *,
        combo_size: int,
        limit: int,
    ) -> tuple[ObservedPromptCombination, ...]:
        """Return only combinations represented by canonical generations."""
        ...

    def latest_review_sequence(self) -> int:
        """Return the current canonical review frontier."""
        ...


class AnalyticsService:
    """Expose canonical statistics use cases to HTTP-facing view services."""

    def __init__(self, repository: AnalyticsRepository) -> None:
        self._repository = repository

    def prompt_token_statistics(
        self,
        *,
        model_branch: str = "",
        scope: str = "pos",
        minimum_samples: int = 8,
        limit: int = 200,
    ) -> tuple[PromptTokenStatistic, ...]:
        """Return validated prompt statistics from canonical facts."""
        normalized_scope = str(scope or "").strip().lower()
        if normalized_scope not in {"pos", "neg"}:
            normalized_scope = "pos"
        return self._repository.list_prompt_token_statistics(
            model_branch=str(model_branch or "").strip(),
            scope=normalized_scope,
            minimum_samples=max(int(minimum_samples), 0),
            limit=max(int(limit), 0),
        )

    def token_statistics_for(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str = "",
        scope: str = "pos",
    ) -> dict[str, PromptTokenStatistic]:
        """Return one statistic for every requested unique prompt atom."""
        normalized_tokens = self._normalized_values(tokens)
        if not normalized_tokens:
            return {}
        normalized_scope = self._scope(scope)
        statistics = self._repository.list_selected_prompt_token_statistics(
            normalized_tokens,
            model_branch=str(model_branch or "").strip(),
            scope=normalized_scope,
        )
        by_token = {item.token: item for item in statistics}
        return {
            token: by_token.get(
                token,
                PromptTokenStatistic(token, 0, 0.0, 0.0),
            )
            for token in normalized_tokens
        }

    def best_prompt_match(
        self,
        tokens: tuple[str, ...],
        *,
        model_branch: str = "",
        scope: str = "pos",
        minimum_hits: int = 1,
        minimum_ratings: int = 0,
        candidate_limit: int = 128,
    ) -> PromptMatchPreview | None:
        """Return the best canonical image matching requested prompt atoms."""
        normalized_tokens = self._normalized_values(tokens)
        if not normalized_tokens:
            return None
        return self._repository.find_best_prompt_match(
            normalized_tokens,
            model_branch=str(model_branch or "").strip(),
            scope=self._scope(scope),
            minimum_hits=max(int(minimum_hits), 1),
            minimum_ratings=max(int(minimum_ratings), 0),
            candidate_limit=max(int(candidate_limit), 1),
        )

    def best_images_for_combos(
        self,
        combo_keys: tuple[str, ...],
        *,
        model_branch: str = "",
        limit_per_combo: int = 3,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Return best live images for requested observed combos."""
        normalized = tuple(
            dict.fromkeys(
                key for raw in combo_keys if (key := str(raw).strip())
            )
        )
        if not normalized:
            return {}
        return self._repository.list_best_images_for_combos(
            normalized,
            model_branch=str(model_branch or "").strip(),
            limit_per_combo=max(int(limit_per_combo), 0),
        )

    def best_images_for_parameter(
        self,
        parameter: str,
        values: tuple[str, ...],
        *,
        model_branch: str = "",
        limit_per_value: int = 3,
    ) -> dict[str, tuple[AnalyticsImage, ...]]:
        """Return best live images for one supported render parameter."""
        normalized_values = tuple(
            dict.fromkeys(
                value for raw in values if (value := str(raw).strip())
            )
        )
        if not normalized_values:
            return {}
        return self._repository.list_best_images_for_parameter(
            str(parameter or "").strip(),
            normalized_values,
            model_branch=str(model_branch or "").strip(),
            limit_per_value=max(int(limit_per_value), 0),
        )

    def observed_combinations(
        self,
        *,
        combo_size: int,
        limit: int = 8,
    ) -> tuple[ObservedPromptCombination, ...]:
        """Return generated two- or three-component combinations only."""
        if combo_size not in {2, 3}:
            raise ValueError("combo_size must be 2 or 3")
        return self._repository.list_observed_combinations(
            combo_size=combo_size,
            limit=max(int(limit), 0),
        )

    def latest_review_sequence(self) -> int:
        """Return the current canonical review frontier."""
        return self._repository.latest_review_sequence()

    @staticmethod
    def _scope(scope: str) -> str:
        normalized = str(scope or "").strip().lower()
        return normalized if normalized in {"pos", "neg"} else "pos"

    @staticmethod
    def _normalized_values(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(
            dict.fromkeys(
                value for raw in values if (value := str(raw).strip())
            )
        )
