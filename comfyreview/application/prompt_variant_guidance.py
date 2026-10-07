"""Evidence-guided prompt component recommendations."""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Protocol

from comfyreview.application.rating_evidence import _bayes_lb05, _sigmoid
from comfyreview.domain import PromptAtomUsage, render_prompt_atom_usages

MODEL_VERSION = "prompt-guidance-v1"
STABILITY_IMAGE_FLOOR = 5
WEIGHT_ANCHOR_IMAGE_FLOOR = 3
SHRINKAGE_PRIOR = 10
WEIGHT_INTERPOLATION_STEP = 50
DISCOVERY_Z_SCORE = 1.645


@dataclass(frozen=True, slots=True)
class PromptVariantRecipe:
    """Describe one exact ordered positive/negative component recipe."""

    positive_atoms: tuple[PromptAtomUsage, ...]
    negative_atoms: tuple[PromptAtomUsage, ...]

    @property
    def key(self) -> str:
        """Return a stable identity for the complete weighted recipe."""
        content = (
            f"{render_prompt_atom_usages(self.positive_atoms)}\0"
            f"{render_prompt_atom_usages(self.negative_atoms)}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    @property
    def structural_key(self) -> tuple[tuple[str, int, str], ...]:
        """Return identity without weights for Weight-only modeling."""
        return tuple(
            (scope, position, atom.text)
            for scope, atoms in (
                ("pos", self.positive_atoms),
                ("neg", self.negative_atoms),
            )
            for position, atom in enumerate(atoms)
        )


@dataclass(frozen=True, slots=True)
class PromptVariantObservation:
    """Aggregate immutable review evidence for one image and exact group."""

    image_uid: str
    recipe: PromptVariantRecipe
    success_weight: int
    failure_weight: int
    rating_sum: float
    rating_weight: int
    review_count: int
    revision_uid: str
    candidate_uid: str | None = None
    deleted_count: int = 0


@dataclass(frozen=True, slots=True)
class PromptCurrentStandard:
    """Describe the revision selected by the newest promotion fact."""

    component_uid: str
    revision_uid: str
    recipe: PromptVariantRecipe
    provisional: bool


@dataclass(frozen=True, slots=True)
class PromptVariantScore:
    """Expose quality, uncertainty and support without conflating them."""

    lower_bound: float | None
    expected_success_rate: float
    average_rating: float | None
    image_count: int
    review_count: int
    standard_deviation: float
    sufficiently_observed: bool
    deleted_count: int = 0


@dataclass(frozen=True, slots=True)
class PromptVariantRecommendation:
    """Describe one observed or calculated component recipe."""

    recipe: PromptVariantRecipe
    score: PromptVariantScore
    image_uids: tuple[str, ...] = ()
    revision_uid: str | None = None
    candidate_uid: str | None = None


@dataclass(frozen=True, slots=True)
class PromptVariantCoverage:
    """Summarize component evidence and Weight-only model coverage."""

    image_count: int
    review_count: int
    observed_variant_count: int
    stable_variant_count: int
    modeled_atom_count: int
    atom_count: int


@dataclass(frozen=True, slots=True)
class PromptVariantGuidance:
    """Return catalog, observed, optimized and discovery choices."""

    current_standard: PromptVariantRecommendation
    current_provisional: bool
    best_observed: PromptVariantRecommendation | None
    optimized: PromptVariantRecommendation
    next_test: PromptVariantRecommendation | None
    coverage: PromptVariantCoverage
    model_version: str = MODEL_VERSION


class PromptVariantEvidenceRepository(Protocol):
    """Read canonical prompt-component evidence without exposing SQLite."""

    def get_current_standard(
        self, component_uid: str
    ) -> PromptCurrentStandard:
        """Return the revision selected by the newest promotion."""
        ...

    def list_observations(
        self, component_uid: str
    ) -> tuple[PromptVariantObservation, ...]:
        """Return one weighted observation per visible reviewed image."""
        ...


@dataclass(frozen=True, slots=True)
class _Aggregate:
    image_count: int
    review_count: int
    success: int
    failure: int
    rating_sum: float
    rating_weight: int
    deleted_count: int


@dataclass(frozen=True, slots=True)
class _WeightEstimate:
    weight_milli: int
    delta: float
    standard_deviation: float
    image_count: int


class PromptVariantGuidanceService:
    """Calculate deterministic component-global prompt guidance."""

    def __init__(self, repository: PromptVariantEvidenceRepository) -> None:
        self._repository = repository

    def build(
        self,
        component_uid: str,
        *,
        positive_atoms: tuple[PromptAtomUsage, ...] | None = None,
        negative_atoms: tuple[PromptAtomUsage, ...] | None = None,
    ) -> PromptVariantGuidance:
        """Evaluate the current or explicitly loaded ordered atom list."""
        current = self._repository.get_current_standard(component_uid)
        recipe = PromptVariantRecipe(
            current.recipe.positive_atoms
            if positive_atoms is None
            else tuple(positive_atoms),
            current.recipe.negative_atoms
            if negative_atoms is None
            else tuple(negative_atoms),
        )
        observations = self._repository.list_observations(component_uid)
        observed = _observed_recommendations(observations)
        current_observed = next(
            (
                item
                for item in observed
                if item.recipe.key == current.recipe.key
            ),
            None,
        )
        current_recommendation = (
            current_observed
            or PromptVariantRecommendation(
                recipe=current.recipe,
                score=_empty_score(),
                revision_uid=current.revision_uid,
            )
        )
        if current_recommendation.revision_uid is None:
            current_recommendation = PromptVariantRecommendation(
                recipe=current_recommendation.recipe,
                score=current_recommendation.score,
                image_uids=current_recommendation.image_uids,
                revision_uid=current.revision_uid,
                candidate_uid=current_recommendation.candidate_uid,
            )
        matching = tuple(
            item
            for item in observations
            if item.recipe.structural_key == recipe.structural_key
        )
        optimized, next_test, modeled_atoms = _calculated_recommendations(
            recipe, matching
        )
        return PromptVariantGuidance(
            current_standard=current_recommendation,
            current_provisional=current.provisional,
            best_observed=observed[0] if observed else None,
            optimized=optimized,
            next_test=next_test,
            coverage=PromptVariantCoverage(
                image_count=len({item.image_uid for item in observations}),
                review_count=sum(item.review_count for item in observations),
                observed_variant_count=len(observed),
                stable_variant_count=sum(
                    item.score.sufficiently_observed for item in observed
                ),
                modeled_atom_count=modeled_atoms,
                atom_count=len(recipe.structural_key),
            ),
        )


def _observed_recommendations(
    observations: tuple[PromptVariantObservation, ...],
) -> tuple[PromptVariantRecommendation, ...]:
    grouped: dict[str, list[PromptVariantObservation]] = {}
    for item in observations:
        grouped.setdefault(item.recipe.key, []).append(item)
    output = []
    for items in grouped.values():
        evidence = tuple(items)
        aggregate = _aggregate(evidence)
        revision_uids = sorted({item.revision_uid for item in evidence})
        candidate_uids = sorted(
            {item.candidate_uid for item in evidence if item.candidate_uid}
        )
        output.append(
            PromptVariantRecommendation(
                recipe=evidence[0].recipe,
                score=_observed_score(aggregate),
                image_uids=_representative_images(evidence),
                revision_uid=(
                    revision_uids[0] if len(revision_uids) == 1 else None
                ),
                candidate_uid=(
                    candidate_uids[0] if len(candidate_uids) == 1 else None
                ),
            )
        )
    output.sort(key=_observed_key, reverse=True)
    return tuple(output)


def _calculated_recommendations(
    recipe: PromptVariantRecipe,
    observations: tuple[PromptVariantObservation, ...],
) -> tuple[
    PromptVariantRecommendation,
    PromptVariantRecommendation | None,
    int,
]:
    baseline = _aggregate(observations)
    baseline_probability = _posterior_probability(baseline)
    baseline_logit = _logit(baseline_probability)
    coordinates = _coordinates(recipe)
    estimates: list[tuple[_WeightEstimate, ...]] = []
    modeled_atoms = 0
    for scope, position, atom in coordinates:
        anchors = _weight_anchors(
            observations,
            scope=scope,
            position=position,
            baseline_logit=baseline_logit,
        )
        domain = _interpolated_domain(anchors)
        if domain:
            modeled_atoms += 1
        else:
            domain = (_WeightEstimate(atom.weight_milli, 0.0, 0.0, 0),)
        estimates.append(domain)
    optimized_values = tuple(
        max(
            domain,
            key=lambda item: (
                item.delta,
                item.image_count,
                -abs(item.weight_milli - coordinates[index][2].weight_milli),
                -item.weight_milli,
            ),
        )
        for index, domain in enumerate(estimates)
    )
    optimized = _predicted_recommendation(
        recipe,
        optimized_values,
        baseline_probability,
        baseline_logit,
    )
    next_test = _discovery_recommendation(
        recipe,
        estimates,
        optimized,
        baseline_probability,
        baseline_logit,
    )
    return optimized, next_test, modeled_atoms


def _weight_anchors(
    observations: tuple[PromptVariantObservation, ...],
    *,
    scope: str,
    position: int,
    baseline_logit: float,
) -> tuple[_WeightEstimate, ...]:
    grouped: dict[int, list[PromptVariantObservation]] = {}
    for item in observations:
        atoms = (
            item.recipe.positive_atoms
            if scope == "pos"
            else item.recipe.negative_atoms
        )
        if position < len(atoms):
            grouped.setdefault(atoms[position].weight_milli, []).append(item)
    output = []
    for weight, items in grouped.items():
        aggregate = _aggregate(tuple(items))
        if aggregate.image_count < WEIGHT_ANCHOR_IMAGE_FLOOR:
            continue
        probability = _posterior_probability(aggregate)
        shrinkage = aggregate.image_count / (
            aggregate.image_count + SHRINKAGE_PRIOR
        )
        output.append(
            _WeightEstimate(
                weight_milli=weight,
                delta=(_logit(probability) - baseline_logit) * shrinkage,
                standard_deviation=_posterior_standard_deviation(aggregate),
                image_count=aggregate.image_count,
            )
        )
    return tuple(sorted(output, key=lambda item: item.weight_milli))


def _interpolated_domain(
    anchors: tuple[_WeightEstimate, ...],
) -> tuple[_WeightEstimate, ...]:
    if len(anchors) < 2:
        return anchors
    by_weight = {item.weight_milli: item for item in anchors}
    minimum = anchors[0].weight_milli
    maximum = anchors[-1].weight_milli
    for weight in range(
        _ceil_step(minimum, WEIGHT_INTERPOLATION_STEP),
        maximum + 1,
        WEIGHT_INTERPOLATION_STEP,
    ):
        if weight in by_weight:
            continue
        lower = max(
            (item for item in anchors if item.weight_milli < weight),
            key=lambda item: item.weight_milli,
            default=None,
        )
        upper = min(
            (item for item in anchors if item.weight_milli > weight),
            key=lambda item: item.weight_milli,
            default=None,
        )
        assert lower is not None and upper is not None
        fraction = (weight - lower.weight_milli) / (
            upper.weight_milli - lower.weight_milli
        )
        by_weight[weight] = _WeightEstimate(
            weight_milli=weight,
            delta=lower.delta + (upper.delta - lower.delta) * fraction,
            standard_deviation=(
                lower.standard_deviation
                + (upper.standard_deviation - lower.standard_deviation)
                * fraction
            ),
            image_count=min(lower.image_count, upper.image_count),
        )
    return tuple(by_weight[weight] for weight in sorted(by_weight))


def _discovery_recommendation(
    recipe: PromptVariantRecipe,
    estimates: list[tuple[_WeightEstimate, ...]],
    optimized: PromptVariantRecommendation,
    baseline_probability: float,
    baseline_logit: float,
) -> PromptVariantRecommendation | None:
    if not estimates or not any(len(domain) > 1 for domain in estimates):
        return None
    selected = tuple(
        max(
            domain,
            key=lambda item: (
                _estimate_ucb(item, baseline_logit),
                item.image_count,
                -item.weight_milli,
            ),
        )
        for domain in estimates
    )
    current_key = recipe.key
    optimized_key = optimized.recipe.key
    candidates = [selected]
    for index, domain in enumerate(estimates):
        for alternative in domain:
            if alternative == selected[index]:
                continue
            varied = list(selected)
            varied[index] = alternative
            candidates.append(tuple(varied))
    recommendations = tuple(
        _predicted_recommendation(
            recipe,
            candidate,
            baseline_probability,
            baseline_logit,
        )
        for candidate in candidates
    )
    eligible = tuple(
        item
        for item in recommendations
        if item.recipe.key not in {current_key, optimized_key}
    )
    if not eligible:
        return None
    return max(
        eligible,
        key=lambda item: (
            item.score.expected_success_rate
            + DISCOVERY_Z_SCORE * item.score.standard_deviation,
            item.score.image_count,
            item.recipe.key,
        ),
    )


def _predicted_recommendation(
    base_recipe: PromptVariantRecipe,
    estimates: tuple[_WeightEstimate, ...],
    baseline_probability: float,
    baseline_logit: float,
) -> PromptVariantRecommendation:
    recipe = _recipe_with_weights(
        base_recipe, tuple(item.weight_milli for item in estimates)
    )
    modeled = tuple(item for item in estimates if item.image_count > 0)
    mean_delta = (
        sum(item.delta for item in modeled) / len(modeled) if modeled else 0.0
    )
    probability = float(_sigmoid(baseline_logit + mean_delta))
    standard_deviation = (
        math.sqrt(sum(item.standard_deviation**2 for item in modeled))
        / len(modeled)
        if modeled
        else _posterior_standard_deviation_from_probability(
            baseline_probability, 0
        )
    )
    support = min((item.image_count for item in modeled), default=0)
    return PromptVariantRecommendation(
        recipe=recipe,
        score=PromptVariantScore(
            lower_bound=None,
            expected_success_rate=probability,
            average_rating=None,
            image_count=support,
            review_count=0,
            standard_deviation=standard_deviation,
            sufficiently_observed=False,
            deleted_count=0,
        ),
    )


def _coordinates(
    recipe: PromptVariantRecipe,
) -> tuple[tuple[str, int, PromptAtomUsage], ...]:
    return tuple(
        (scope, position, atom)
        for scope, atoms in (
            ("pos", recipe.positive_atoms),
            ("neg", recipe.negative_atoms),
        )
        for position, atom in enumerate(atoms)
    )


def _recipe_with_weights(
    recipe: PromptVariantRecipe,
    weights: tuple[int, ...],
) -> PromptVariantRecipe:
    coordinates = _coordinates(recipe)
    positive = tuple(
        PromptAtomUsage(atom.text, weights[index])
        for index, (scope, _position, atom) in enumerate(coordinates)
        if scope == "pos"
    )
    negative = tuple(
        PromptAtomUsage(atom.text, weights[index])
        for index, (scope, _position, atom) in enumerate(coordinates)
        if scope == "neg"
    )
    return PromptVariantRecipe(positive, negative)


def _aggregate(
    observations: tuple[PromptVariantObservation, ...],
) -> _Aggregate:
    return _Aggregate(
        image_count=len({item.image_uid for item in observations}),
        review_count=sum(item.review_count for item in observations),
        success=sum(item.success_weight for item in observations),
        failure=sum(item.failure_weight for item in observations),
        rating_sum=sum(item.rating_sum for item in observations),
        rating_weight=sum(item.rating_weight for item in observations),
        deleted_count=sum(item.deleted_count for item in observations),
    )


def _observed_score(aggregate: _Aggregate) -> PromptVariantScore:
    expected = _posterior_probability(aggregate)
    return PromptVariantScore(
        lower_bound=_bayes_lb05(
            float(aggregate.success), float(aggregate.failure)
        ),
        expected_success_rate=expected,
        average_rating=(
            aggregate.rating_sum / aggregate.rating_weight
            if aggregate.rating_weight
            else None
        ),
        image_count=aggregate.image_count,
        review_count=aggregate.review_count,
        standard_deviation=_posterior_standard_deviation(aggregate),
        sufficiently_observed=(aggregate.image_count >= STABILITY_IMAGE_FLOOR),
        deleted_count=aggregate.deleted_count,
    )


def _empty_score() -> PromptVariantScore:
    return PromptVariantScore(None, 0.5, None, 0, 0, 0.5, False, 0)


def _posterior_probability(aggregate: _Aggregate) -> float:
    return (aggregate.success + 1) / (
        aggregate.success + aggregate.failure + 2
    )


def _posterior_standard_deviation(aggregate: _Aggregate) -> float:
    probability = _posterior_probability(aggregate)
    return _posterior_standard_deviation_from_probability(
        probability, aggregate.success + aggregate.failure
    )


def _posterior_standard_deviation_from_probability(
    probability: float, evidence_count: int
) -> float:
    return math.sqrt(
        max(0.0, probability * (1.0 - probability) / (evidence_count + 3))
    )


def _observed_key(
    item: PromptVariantRecommendation,
) -> tuple[float, float, float, int, str]:
    score = item.score
    return (
        score.lower_bound or 0.0,
        score.expected_success_rate,
        score.average_rating or 0.0,
        score.image_count,
        item.recipe.key,
    )


def _representative_images(
    observations: tuple[PromptVariantObservation, ...],
) -> tuple[str, ...]:
    ordered = sorted(
        observations,
        key=lambda item: (
            item.rating_sum / item.rating_weight if item.rating_weight else -1,
            item.review_count,
            item.image_uid,
        ),
        reverse=True,
    )
    return tuple(item.image_uid for item in ordered[:8])


def _estimate_ucb(estimate: _WeightEstimate, baseline_logit: float) -> float:
    mean = float(_sigmoid(baseline_logit + estimate.delta))
    return mean + DISCOVERY_Z_SCORE * estimate.standard_deviation


def _ceil_step(value: int, step: int) -> int:
    return ((value + step - 1) // step) * step


def _logit(probability: float) -> float:
    bounded = min(max(float(probability), 1e-9), 1.0 - 1e-9)
    return math.log(bounded / (1.0 - bounded))
