"""Application contracts for canonical statistics and observed combinations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from comfyreview.application.image_queries import ScopeKind
from comfyreview.application.pagination import CollectionPage, normalize_page


@dataclass(frozen=True, slots=True)
class AnalyticsImage:
    """Describe one live canonical image used in statistics views."""

    png_path: Path
    json_path: Path | None
    average_rating: float | None
    rating_count: int
    image_uid: str = ""


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
class PromptFactor:
    """Describe one component or LoRA factor usable by the Generator."""

    source: str
    kind: str
    uid: str
    name: str
    revision_uid: str | None = None
    applicable: bool = True
    reason: str | None = None
    model_strength_milli: int | None = None
    clip_strength_milli: int | None = None


@dataclass(frozen=True, slots=True)
class ObservedPromptCombination:
    """Describe one generated canonical prompt-component combination."""

    combo_key: str
    additional_factor_count: int
    component_uids: tuple[str, ...]
    component_names: tuple[str, ...]
    label: str
    average_rating: float | None
    image_count: int
    total_rating_count: int
    best_images: tuple[AnalyticsImage, ...]
    factors: tuple[PromptFactor, ...] = ()


@dataclass(frozen=True, slots=True)
class CharacterCombinationGroup:
    """Group the strongest observed combinations for one character."""

    character_uid: str
    character_name: str
    combinations: tuple[ObservedPromptCombination, ...]


@dataclass(frozen=True, slots=True)
class PlaygroundCharacterCombinationSelection:
    """Carry diverse Playground combinations for one canonical character."""

    character_uid: str
    character_name: str
    two_additional_factors: tuple[ObservedPromptCombination, ...]
    three_additional_factors: tuple[ObservedPromptCombination, ...]


class PlaygroundCombinationSelectionPolicy:
    """Prefer distinct cover images across both Playground factor groups."""

    def select(
        self,
        *,
        two_additional_factors: tuple[CharacterCombinationGroup, ...],
        three_additional_factors: tuple[CharacterCombinationGroup, ...],
        limit_per_group: int,
    ) -> tuple[PlaygroundCharacterCombinationSelection, ...]:
        """Select diverse ranked rows and fall back only after exhaustion."""
        limit = max(int(limit_per_group), 0)
        two_by_uid = {
            group.character_uid: group for group in two_additional_factors
        }
        three_by_uid = {
            group.character_uid: group for group in three_additional_factors
        }
        character_uids = dict.fromkeys((*two_by_uid, *three_by_uid))
        return tuple(
            self._select_character(
                two_by_uid.get(character_uid),
                three_by_uid.get(character_uid),
                limit=limit,
            )
            for character_uid in character_uids
        )

    def _select_character(
        self,
        two_group: CharacterCombinationGroup | None,
        three_group: CharacterCombinationGroup | None,
        *,
        limit: int,
    ) -> PlaygroundCharacterCombinationSelection:
        group = two_group or three_group
        assert group is not None
        candidates = {
            2: two_group.combinations if two_group is not None else (),
            3: three_group.combinations if three_group is not None else (),
        }
        selected: dict[int, list[ObservedPromptCombination]] = {2: [], 3: []}
        selected_keys: dict[int, set[str]] = {2: set(), 3: set()}
        used_image_uids: set[str] = set()

        while True:
            progress = False
            for factor_count in (2, 3):
                if len(selected[factor_count]) >= limit:
                    continue
                candidate = next(
                    (
                        item
                        for item in candidates[factor_count]
                        if item.combo_key not in selected_keys[factor_count]
                        and (image_uid := self._cover_image_uid(item))
                        and image_uid not in used_image_uids
                    ),
                    None,
                )
                if candidate is None:
                    continue
                selected[factor_count].append(candidate)
                selected_keys[factor_count].add(candidate.combo_key)
                used_image_uids.add(self._cover_image_uid(candidate))
                progress = True
            if not progress:
                break

        for factor_count in (2, 3):
            for candidate in candidates[factor_count]:
                if len(selected[factor_count]) >= limit:
                    break
                if candidate.combo_key in selected_keys[factor_count]:
                    continue
                selected[factor_count].append(candidate)
                selected_keys[factor_count].add(candidate.combo_key)

        return PlaygroundCharacterCombinationSelection(
            character_uid=group.character_uid,
            character_name=group.character_name,
            two_additional_factors=tuple(selected[2]),
            three_additional_factors=tuple(selected[3]),
        )

    @staticmethod
    def _cover_image_uid(combination: ObservedPromptCombination) -> str:
        if not combination.best_images:
            return ""
        return combination.best_images[0].image_uid.strip()


@dataclass(frozen=True, slots=True)
class ScopeStatistic:
    """Summarize review evidence for one canonical prompt component."""

    kind: ScopeKind
    component_uid: str
    name: str
    archived: bool
    image_count: int
    rating_count: int
    average_rating: float | None
    best_images: tuple[AnalyticsImage, ...] = ()


@dataclass(frozen=True, slots=True)
class CompositionStatistic:
    """Summarize review evidence for one canonical prompt composition."""

    composition_uid: str
    component_names: tuple[str, ...]
    image_count: int
    rating_count: int
    average_rating: float | None
    best_images: tuple[AnalyticsImage, ...] = ()


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
        additional_factor_count: int,
        limit: int,
    ) -> tuple[ObservedPromptCombination, ...]:
        """Return only combinations represented by canonical generations."""
        ...

    def list_observed_combinations_by_character(
        self,
        *,
        additional_factor_count: int,
    ) -> tuple[CharacterCombinationGroup, ...]:
        """Return ranked observed combinations grouped by character."""
        ...

    def latest_review_sequence(self) -> int:
        """Return the current canonical review frontier."""
        ...


class AnalyticsReportRepository(Protocol):
    """Build legacy-compatible report rows from canonical SQLite facts."""

    def combo_statistics(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return observed combination statistics."""
        ...

    def scope_statistics(
        self,
        *,
        model: str,
        min_n: int,
        kind: ScopeKind | None,
        offset: int,
        limit: int,
    ) -> CollectionPage[ScopeStatistic]:
        """Return statistics grouped by canonical prompt component."""
        ...

    def composition_statistics(
        self,
        *,
        model: str,
        min_n: int,
        offset: int,
        limit: int,
    ) -> CollectionPage[CompositionStatistic]:
        """Return statistics grouped by canonical prompt composition."""
        ...

    def recommendations(
        self,
        *,
        model: str,
        min_n: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
        min_lb: float,
        approx_min_n: int,
        approx_limit: int,
    ) -> dict[str, Any]:
        """Return stable and approximate recommendations."""
        ...

    def parameter_statistics(
        self,
        *,
        model: str,
        min_n: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return render-parameter statistics."""
        ...

    def calculated_best_cases(
        self,
        *,
        model: str,
        min_n: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return calculated best render configurations."""
        ...

    def list_models(self) -> tuple[str, ...]:
        """Return canonical model branches represented by generations."""
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
        additional_factor_count: int,
        limit: int = 8,
    ) -> tuple[ObservedPromptCombination, ...]:
        """Return combinations with two or three additional factors."""
        if additional_factor_count not in {2, 3}:
            raise ValueError("additional_factor_count must be 2 or 3")
        return self._repository.list_observed_combinations(
            additional_factor_count=additional_factor_count,
            limit=max(int(limit), 0),
        )

    def observed_combinations_by_character(
        self,
        *,
        additional_factor_count: int,
    ) -> tuple[CharacterCombinationGroup, ...]:
        """Return every ranked combination candidate per character."""
        if additional_factor_count not in {2, 3}:
            raise ValueError("additional_factor_count must be 2 or 3")
        return self._repository.list_observed_combinations_by_character(
            additional_factor_count=additional_factor_count,
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


class AnalyticsReportService:
    """Validate and expose canonical analytics report use cases."""

    def __init__(self, repository: AnalyticsReportRepository) -> None:
        self._repository = repository

    def combo_statistics(
        self,
        *,
        model: str,
        minimum_samples: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return normalized observed-combination report rows."""
        return self._repository.combo_statistics(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            limit=max(int(limit), 0),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
        )

    def scope_statistics(
        self,
        *,
        model: str,
        minimum_samples: int,
        kind: str = "character",
        offset: int = 0,
        limit: int = 24,
    ) -> CollectionPage[ScopeStatistic]:
        """Return normalized canonical component statistics."""
        try:
            normalized_kind = ScopeKind(str(kind).strip())
        except ValueError as error:
            raise ValueError(f"unsupported scope kind: {kind}") from error
        normalized_offset, normalized_limit = normalize_page(offset, limit)
        return self._repository.scope_statistics(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            kind=normalized_kind,
            offset=normalized_offset,
            limit=normalized_limit,
        )

    def composition_statistics(
        self,
        *,
        model: str,
        minimum_samples: int,
        offset: int = 0,
        limit: int = 24,
    ) -> CollectionPage[CompositionStatistic]:
        """Return normalized canonical composition statistics."""
        normalized_offset, normalized_limit = normalize_page(offset, limit)
        return self._repository.composition_statistics(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            offset=normalized_offset,
            limit=normalized_limit,
        )

    def recommendations(
        self,
        *,
        model: str,
        minimum_samples: int,
        limit: int,
        success_threshold: int,
        delete_weight: int,
        minimum_lower_bound: float,
        approximate_minimum_samples: int,
        approximate_limit: int,
    ) -> dict[str, Any]:
        """Return normalized stable and approximate recommendations."""
        return self._repository.recommendations(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            limit=max(int(limit), 0),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            min_lb=float(minimum_lower_bound),
            approx_min_n=max(int(approximate_minimum_samples), 0),
            approx_limit=max(int(approximate_limit), 0),
        )

    def parameter_statistics(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
    ) -> list[dict[str, Any]]:
        """Return normalized render-parameter report rows."""
        return self._repository.parameter_statistics(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
        )

    def calculated_best_cases(
        self,
        *,
        model: str,
        minimum_samples: int,
        success_threshold: int,
        delete_weight: int,
        limit: int,
    ) -> list[dict[str, Any]]:
        """Return normalized best render configurations."""
        return self._repository.calculated_best_cases(
            model=str(model or "").strip(),
            min_n=max(int(minimum_samples), 0),
            success_threshold=int(success_threshold),
            delete_weight=int(delete_weight),
            limit=max(int(limit), 0),
        )

    def list_models(self) -> tuple[str, ...]:
        """Return model branches available to analytics filters."""
        return self._repository.list_models()
