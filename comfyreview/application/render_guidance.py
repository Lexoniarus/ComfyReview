"""Canonical evidence guidance for render and sampler settings."""

from __future__ import annotations

import heapq
import itertools
import math
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Protocol

from comfyreview.application.rating_evidence import _bayes_lb05, _sigmoid

MODEL_VERSION = "render-guidance-v1"
STABILITY_IMAGE_FLOOR = 5
MAIN_EFFECT_IMAGE_FLOOR = 3
INTERACTION_IMAGE_FLOOR = 5
SHRINKAGE_PRIOR = 10


class GuidanceBasis(StrEnum):
    """Select observed evidence or calculated prediction."""

    OBSERVED = "observed"
    PREDICTED = "predicted"


class GuidanceScope(StrEnum):
    """Select a complete setup or independent parameter values."""

    SETUP = "setup"
    PARAMETER = "parameter"


class GuidanceConfidence(StrEnum):
    """Describe support without conflating it with outcome quality."""

    INSUFFICIENT = "insufficient"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class GuidanceParameter(StrEnum):
    """Identify one optimizer-controlled render setting."""

    CHECKPOINT = "checkpoint"
    SAMPLER = "sampler"
    SCHEDULER = "scheduler"
    STEPS = "steps"
    CFG = "cfg"
    DENOISE = "denoise"


@dataclass(frozen=True, slots=True)
class RenderSettings:
    """Describe the single-stage settings supported by the generator."""

    checkpoint: str
    sampler: str
    scheduler: str
    steps: int
    cfg: float
    denoise: float

    def value(self, parameter: GuidanceParameter) -> str:
        """Return one normalized value for grouping and transport."""
        value = getattr(self, parameter.value)
        if isinstance(value, float):
            precision = 2 if parameter is GuidanceParameter.DENOISE else 1
            return f"{value:.{precision}f}".rstrip("0").rstrip(".")
        return str(value)

    @property
    def key(self) -> str:
        """Return a deterministic identity for one render setup."""
        return "|".join(
            f"{parameter.value}={self.value(parameter)}"
            for parameter in GuidanceParameter
        )


@dataclass(frozen=True, slots=True)
class RenderEvidenceObservation:
    """Aggregate immutable review evidence for one canonical image."""

    image_uid: str
    settings: RenderSettings
    success_weight: int
    failure_weight: int
    rating_sum: float
    rating_weight: int
    review_count: int
    stage_count: int = 1


@dataclass(frozen=True, slots=True)
class RenderCapabilitySet:
    """Bound recommendations to values currently accepted by ComfyUI."""

    checkpoints: tuple[str, ...]
    samplers: tuple[str, ...]
    schedulers: tuple[str, ...]

    def supports(self, settings: RenderSettings) -> bool:
        """Return whether provider enums can represent the settings."""
        return (
            settings.checkpoint in self.checkpoints
            and settings.sampler in self.samplers
            and settings.scheduler in self.schedulers
        )


@dataclass(frozen=True, slots=True)
class EvidenceScore:
    """Expose quality and support as separate concepts."""

    source: GuidanceBasis
    score: float
    expected_success_rate: float
    lower_bound: float | None
    average_rating: float | None
    image_count: int
    review_count: int
    confidence: GuidanceConfidence
    sufficiently_observed: bool
    jointly_observed: bool
    relative_rank: float | None = None


@dataclass(frozen=True, slots=True)
class ParameterGuidance:
    """Describe one value of one render parameter."""

    parameter: GuidanceParameter
    value: str
    observed: EvidenceScore | None
    predicted: EvidenceScore | None
    applicable: bool
    image_uids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RenderRecommendation:
    """Describe one complete set of settings and its evidence."""

    settings: RenderSettings
    evidence: EvidenceScore
    applicable: bool
    image_uids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class RenderGuidanceCoverage:
    """Summarize the visible canonical render evidence."""

    image_count: int
    review_count: int
    observed_setup_count: int
    stable_setup_count: int
    modeled_value_counts: tuple[tuple[GuidanceParameter, int], ...]


@dataclass(frozen=True, slots=True)
class RenderGuidance:
    """Return the shared Generator and Analytics guidance model."""

    current_observed: RenderRecommendation | None
    current_predicted: RenderRecommendation | None
    observed_setup: RenderRecommendation | None
    observed_parameters: RenderRecommendation | None
    predicted_setup: RenderRecommendation | None
    predicted_parameters: RenderRecommendation | None
    parameter_values: tuple[ParameterGuidance, ...]
    observed_setups: tuple[RenderRecommendation, ...]
    predicted_setups: tuple[RenderRecommendation, ...]
    coverage: RenderGuidanceCoverage
    model_version: str = MODEL_VERSION
    stability_image_floor: int = STABILITY_IMAGE_FLOOR


@dataclass(frozen=True, slots=True)
class RenderGuidancePage:
    """Return one server-filtered Analytics guidance collection."""

    basis: GuidanceBasis
    scope: GuidanceScope
    parameter: GuidanceParameter | None
    entries: tuple[ParameterGuidance | RenderRecommendation, ...]
    total: int
    sufficiently_observed_total: int
    filtered_total: int
    offset: int
    limit: int
    coverage: RenderGuidanceCoverage
    model_version: str = MODEL_VERSION


class RenderEvidenceRepository(Protocol):
    """Read normalized render evidence without exposing SQLite."""

    def list_observations(
        self, *, model: str = ""
    ) -> tuple[RenderEvidenceObservation, ...]:
        """Return one aggregate per visible rated image."""
        ...


@dataclass(frozen=True, slots=True)
class _Aggregate:
    image_count: int
    review_count: int
    success: int
    failure: int
    rating_sum: float
    rating_weight: int


@dataclass(frozen=True, slots=True)
class _Effect:
    probability: float
    delta: float
    image_count: int


class RenderGuidanceService:
    """Calculate deterministic observed and predicted render guidance."""

    _interaction_pairs = (
        (GuidanceParameter.CHECKPOINT, GuidanceParameter.SAMPLER),
        (GuidanceParameter.SAMPLER, GuidanceParameter.SCHEDULER),
        (GuidanceParameter.SAMPLER, GuidanceParameter.STEPS),
        (GuidanceParameter.SAMPLER, GuidanceParameter.CFG),
        (GuidanceParameter.SCHEDULER, GuidanceParameter.STEPS),
        (GuidanceParameter.STEPS, GuidanceParameter.CFG),
        (GuidanceParameter.CFG, GuidanceParameter.DENOISE),
    )

    def __init__(self, repository: RenderEvidenceRepository) -> None:
        self._repository = repository

    def build(
        self,
        *,
        current: RenderSettings | None = None,
        capabilities: RenderCapabilitySet | None = None,
        model: str = "",
        limit: int = 24,
    ) -> RenderGuidance:
        """Return all four modes from one canonical evidence snapshot."""
        observations = self._repository.list_observations(
            model=str(model or "").strip()
        )
        observed_by_setup = self._observed_setups(observations, capabilities)
        parameter_values = self._parameter_guidance(observations, capabilities)
        predicted = self._predicted_setups(
            observations,
            parameter_values,
            observed_by_setup,
            capabilities,
            max(0, int(limit)),
        )
        observed_parameters = self._parameter_recommendation(
            parameter_values, GuidanceBasis.OBSERVED
        )
        predicted_parameters = self._parameter_recommendation(
            parameter_values, GuidanceBasis.PREDICTED
        )
        observed_stable = tuple(
            item
            for item in observed_by_setup
            if item.evidence.sufficiently_observed and item.applicable
        )
        observed_setup = observed_stable[0] if observed_stable else None
        predicted_setup = predicted[0] if predicted else None
        current_observed = self._current_observed(current, observed_by_setup)
        current_predicted = self._current_predicted(
            current,
            observations,
            parameter_values,
            observed_by_setup,
            capabilities,
        )
        return RenderGuidance(
            current_observed=current_observed,
            current_predicted=current_predicted,
            observed_setup=observed_setup,
            observed_parameters=observed_parameters,
            predicted_setup=predicted_setup,
            predicted_parameters=predicted_parameters,
            parameter_values=parameter_values,
            observed_setups=observed_by_setup[: max(0, int(limit))],
            predicted_setups=predicted,
            coverage=self._coverage(
                observations, observed_by_setup, parameter_values
            ),
        )

    def query(
        self,
        *,
        basis: str | GuidanceBasis,
        scope: str | GuidanceScope,
        parameter: str | GuidanceParameter | None = None,
        model: str = "",
        minimum_images: int = 0,
        offset: int = 0,
        limit: int = 24,
    ) -> RenderGuidancePage:
        """Return one bounded Analytics view from the shared guidance model."""
        normalized_basis = GuidanceBasis(str(basis))
        normalized_scope = GuidanceScope(str(scope))
        normalized_parameter = (
            GuidanceParameter(str(parameter))
            if parameter not in (None, "")
            else None
        )
        if (
            normalized_scope is GuidanceScope.PARAMETER
            and normalized_parameter is None
        ):
            raise ValueError("parameter scope requires a render parameter")
        if (
            normalized_scope is GuidanceScope.SETUP
            and normalized_parameter is not None
        ):
            raise ValueError("setup scope does not accept a render parameter")
        normalized_minimum = max(0, int(minimum_images))
        normalized_offset = max(0, int(offset))
        normalized_limit = max(1, min(int(limit), 48))
        guidance = self.build(model=model, limit=5000)
        if normalized_scope is GuidanceScope.SETUP:
            setup_source = (
                guidance.observed_setups
                if normalized_basis is GuidanceBasis.OBSERVED
                else guidance.predicted_setups
            )
            total = guidance.coverage.observed_setup_count
            eligible = (
                guidance.coverage.stable_setup_count
                if normalized_basis is GuidanceBasis.OBSERVED
                else sum(
                    item.evidence.image_count >= STABILITY_IMAGE_FLOOR
                    for item in setup_source
                )
            )
            filtered_setups = tuple(
                item
                for item in setup_source
                if item.evidence.image_count >= normalized_minimum
            )
            entries: tuple[ParameterGuidance | RenderRecommendation, ...] = (
                filtered_setups
            )
        else:
            source_parameters = tuple(
                item
                for item in guidance.parameter_values
                if item.parameter is normalized_parameter
                and (
                    item.observed
                    if normalized_basis is GuidanceBasis.OBSERVED
                    else item.predicted
                )
                is not None
            )
            parameter_source = tuple(
                sorted(
                    source_parameters,
                    key=lambda item: _parameter_guidance_key(
                        item, normalized_basis
                    ),
                    reverse=True,
                )
            )
            total = len(parameter_source)
            eligible = sum(
                _guidance_score(item, normalized_basis).image_count
                >= STABILITY_IMAGE_FLOOR
                for item in parameter_source
            )
            filtered_parameters = tuple(
                item
                for item in parameter_source
                if _guidance_score(item, normalized_basis).image_count
                >= normalized_minimum
            )
            entries = filtered_parameters
        return RenderGuidancePage(
            basis=normalized_basis,
            scope=normalized_scope,
            parameter=normalized_parameter,
            entries=entries[
                normalized_offset : normalized_offset + normalized_limit
            ],
            total=total,
            sufficiently_observed_total=eligible,
            filtered_total=len(entries),
            offset=normalized_offset,
            limit=normalized_limit,
            coverage=guidance.coverage,
        )

    @staticmethod
    def _observed_setups(
        observations: tuple[RenderEvidenceObservation, ...],
        capabilities: RenderCapabilitySet | None,
    ) -> tuple[RenderRecommendation, ...]:
        grouped: dict[RenderSettings, list[RenderEvidenceObservation]] = {}
        for item in observations:
            grouped.setdefault(item.settings, []).append(item)
        recommendations = [
            RenderRecommendation(
                settings=settings,
                evidence=_observed_score(tuple(items), jointly_observed=True),
                applicable=(
                    all(item.stage_count == 1 for item in items)
                    and (
                        capabilities is None or capabilities.supports(settings)
                    )
                ),
                image_uids=_representative_image_uids(tuple(items)),
            )
            for settings, items in grouped.items()
        ]
        recommendations.sort(key=_observed_recommendation_key, reverse=True)
        return _rank_recommendations(tuple(recommendations))

    def _parameter_guidance(
        self,
        observations: tuple[RenderEvidenceObservation, ...],
        capabilities: RenderCapabilitySet | None,
    ) -> tuple[ParameterGuidance, ...]:
        baseline = _aggregate(observations)
        baseline_logit = _logit(_posterior_probability(baseline))
        output: list[ParameterGuidance] = []
        for parameter in GuidanceParameter:
            grouped: dict[str, list[RenderEvidenceObservation]] = {}
            for item in observations:
                grouped.setdefault(item.settings.value(parameter), []).append(
                    item
                )
            for value, items in grouped.items():
                evidence = tuple(items)
                observed = _observed_score(evidence, jointly_observed=False)
                predicted = _predicted_value_score(
                    _aggregate(evidence), baseline_logit
                )
                output.append(
                    ParameterGuidance(
                        parameter=parameter,
                        value=value,
                        observed=observed,
                        predicted=predicted,
                        applicable=_parameter_applicable(
                            parameter, value, capabilities
                        ),
                        image_uids=_representative_image_uids(evidence),
                    )
                )
        output.sort(
            key=lambda item: (
                item.parameter.value,
                _value_sort_key(item.value),
            )
        )
        return _rank_parameter_guidance(tuple(output))

    def _predicted_setups(
        self,
        observations: tuple[RenderEvidenceObservation, ...],
        parameters: tuple[ParameterGuidance, ...],
        observed: tuple[RenderRecommendation, ...],
        capabilities: RenderCapabilitySet | None,
        limit: int,
    ) -> tuple[RenderRecommendation, ...]:
        if not observations or limit <= 0:
            return ()
        baseline = _aggregate(observations)
        baseline_logit = _logit(_posterior_probability(baseline))
        effects = _main_effects(parameters, baseline_logit)
        if not all(effects.get(parameter) for parameter in GuidanceParameter):
            return ()
        interactions = self._interaction_effects(
            observations, effects, baseline_logit
        )
        observed_counts = {
            item.settings: item.evidence.image_count for item in observed
        }
        domains = [
            _candidate_values(effects[parameter])
            for parameter in GuidanceParameter
        ]
        heap: list[tuple[tuple[float, int, str], RenderRecommendation]] = []
        for values in itertools.product(*domains):
            settings = _settings_from_values(values)
            if observed_counts.get(settings, 0) >= STABILITY_IMAGE_FLOOR:
                continue
            recommendation = self._predict_settings(
                settings,
                baseline_logit=baseline_logit,
                effects=effects,
                interactions=interactions,
                observed_count=observed_counts.get(settings, 0),
            )
            score = recommendation.evidence.score
            support = recommendation.evidence.image_count
            key = (score, support, settings.key)
            entry = (key, recommendation)
            if len(heap) < limit:
                heapq.heappush(heap, entry)
            elif key > heap[0][0]:
                heapq.heapreplace(heap, entry)
        ranked = tuple(
            item[1]
            for item in sorted(heap, key=lambda entry: entry[0], reverse=True)
        )
        return _rank_recommendations(ranked)

    def _interaction_effects(
        self,
        observations: tuple[RenderEvidenceObservation, ...],
        effects: dict[GuidanceParameter, dict[str, _Effect]],
        baseline_logit: float,
    ) -> dict[
        tuple[tuple[GuidanceParameter, GuidanceParameter], tuple[str, str]],
        _Effect,
    ]:
        output = {}
        for pair in self._interaction_pairs:
            grouped: dict[
                tuple[str, str], list[RenderEvidenceObservation]
            ] = {}
            for item in observations:
                key = (
                    item.settings.value(pair[0]),
                    item.settings.value(pair[1]),
                )
                grouped.setdefault(key, []).append(item)
            for values, rows in grouped.items():
                aggregate = _aggregate(tuple(rows))
                if aggregate.image_count < INTERACTION_IMAGE_FLOOR:
                    continue
                first = effects.get(pair[0], {}).get(values[0])
                second = effects.get(pair[1], {}).get(values[1])
                if first is None or second is None:
                    continue
                raw = (
                    _logit(_posterior_probability(aggregate))
                    - baseline_logit
                    - first.delta
                    - second.delta
                )
                delta = raw * _shrinkage(aggregate.image_count)
                output[(pair, values)] = _Effect(
                    probability=float(_sigmoid(baseline_logit + delta)),
                    delta=delta,
                    image_count=aggregate.image_count,
                )
        return output

    @staticmethod
    def _parameter_recommendation(
        parameters: tuple[ParameterGuidance, ...],
        basis: GuidanceBasis,
    ) -> RenderRecommendation | None:
        values: dict[GuidanceParameter, ParameterGuidance] = {}
        for parameter in GuidanceParameter:
            candidates = []
            for item in parameters:
                if item.parameter is not parameter or not item.applicable:
                    continue
                evidence = (
                    item.observed
                    if basis is GuidanceBasis.OBSERVED
                    else item.predicted
                )
                if evidence is None:
                    continue
                if (
                    basis is GuidanceBasis.OBSERVED
                    and not evidence.sufficiently_observed
                ):
                    continue
                candidates.append(item)
            if not candidates:
                return None
            candidates.sort(
                key=lambda item: _parameter_guidance_key(item, basis),
                reverse=True,
            )
            values[parameter] = candidates[0]
        settings = RenderSettings(
            checkpoint=values[GuidanceParameter.CHECKPOINT].value,
            sampler=values[GuidanceParameter.SAMPLER].value,
            scheduler=values[GuidanceParameter.SCHEDULER].value,
            steps=int(float(values[GuidanceParameter.STEPS].value)),
            cfg=float(values[GuidanceParameter.CFG].value),
            denoise=float(values[GuidanceParameter.DENOISE].value),
        )
        evidence_items = [
            values[parameter].observed
            if basis is GuidanceBasis.OBSERVED
            else values[parameter].predicted
            for parameter in GuidanceParameter
        ]
        concrete = [item for item in evidence_items if item is not None]
        score = min(item.score for item in concrete)
        support = min(item.image_count for item in concrete)
        return RenderRecommendation(
            settings=settings,
            evidence=EvidenceScore(
                source=basis,
                score=score,
                expected_success_rate=score,
                lower_bound=(
                    min(
                        item.lower_bound
                        for item in concrete
                        if item.lower_bound is not None
                    )
                    if basis is GuidanceBasis.OBSERVED
                    else None
                ),
                average_rating=None,
                image_count=support,
                review_count=sum(item.review_count for item in concrete),
                confidence=_confidence(support),
                sufficiently_observed=(
                    basis is GuidanceBasis.OBSERVED
                    and support >= STABILITY_IMAGE_FLOOR
                ),
                jointly_observed=False,
            ),
            applicable=True,
        )

    @staticmethod
    def _current_observed(
        current: RenderSettings | None,
        observed: tuple[RenderRecommendation, ...],
    ) -> RenderRecommendation | None:
        if current is None:
            return None
        return next(
            (item for item in observed if item.settings == current), None
        )

    def _current_predicted(
        self,
        current: RenderSettings | None,
        observations: tuple[RenderEvidenceObservation, ...],
        parameters: tuple[ParameterGuidance, ...],
        observed: tuple[RenderRecommendation, ...],
        capabilities: RenderCapabilitySet | None,
    ) -> RenderRecommendation | None:
        if current is None:
            return None
        baseline_logit = _logit(
            _posterior_probability(_aggregate(observations))
        )
        effects = _main_effects(parameters, baseline_logit)
        if any(
            current.value(parameter) not in effects.get(parameter, {})
            for parameter in GuidanceParameter
        ):
            return None
        interactions = self._interaction_effects(
            observations, effects, baseline_logit
        )
        observed_item = next(
            (item for item in observed if item.settings == current), None
        )
        return self._predict_settings(
            current,
            baseline_logit=baseline_logit,
            effects=effects,
            interactions=interactions,
            observed_count=(
                observed_item.evidence.image_count if observed_item else 0
            ),
        )

    def _predict_settings(
        self,
        settings: RenderSettings,
        *,
        baseline_logit: float,
        effects: dict[GuidanceParameter, dict[str, _Effect]],
        interactions: dict[
            tuple[
                tuple[GuidanceParameter, GuidanceParameter],
                tuple[str, str],
            ],
            _Effect,
        ],
        observed_count: int,
    ) -> RenderRecommendation:
        """Score one known-value setup without a Cartesian search."""
        effect_items: list[_Effect] = []
        for parameter in GuidanceParameter:
            effect_items.append(effects[parameter][settings.value(parameter)])
        logit = baseline_logit + sum(item.delta for item in effect_items)
        for pair in self._interaction_pairs:
            pair_values = (
                settings.value(pair[0]),
                settings.value(pair[1]),
            )
            interaction = interactions.get((pair, pair_values))
            if interaction is not None:
                logit += interaction.delta
        score = float(_sigmoid(logit))
        support = min(item.image_count for item in effect_items)
        return RenderRecommendation(
            settings=settings,
            evidence=EvidenceScore(
                source=GuidanceBasis.PREDICTED,
                score=score,
                expected_success_rate=score,
                lower_bound=None,
                average_rating=None,
                image_count=support,
                review_count=0,
                confidence=_confidence(support),
                sufficiently_observed=False,
                jointly_observed=observed_count > 0,
            ),
            applicable=True,
        )

    @staticmethod
    def _coverage(
        observations: tuple[RenderEvidenceObservation, ...],
        setups: tuple[RenderRecommendation, ...],
        parameters: tuple[ParameterGuidance, ...],
    ) -> RenderGuidanceCoverage:
        counts = tuple(
            (
                parameter,
                sum(
                    1
                    for item in parameters
                    if item.parameter is parameter
                    and item.predicted is not None
                ),
            )
            for parameter in GuidanceParameter
        )
        return RenderGuidanceCoverage(
            image_count=len({item.image_uid for item in observations}),
            review_count=sum(item.review_count for item in observations),
            observed_setup_count=len(setups),
            stable_setup_count=sum(
                item.evidence.sufficiently_observed for item in setups
            ),
            modeled_value_counts=counts,
        )


def _aggregate(
    observations: tuple[RenderEvidenceObservation, ...],
) -> _Aggregate:
    return _Aggregate(
        image_count=len({item.image_uid for item in observations}),
        review_count=sum(item.review_count for item in observations),
        success=sum(item.success_weight for item in observations),
        failure=sum(item.failure_weight for item in observations),
        rating_sum=sum(item.rating_sum for item in observations),
        rating_weight=sum(item.rating_weight for item in observations),
    )


def _representative_image_uids(
    observations: tuple[RenderEvidenceObservation, ...],
) -> tuple[str, ...]:
    """Return deterministic high-rating evidence identities for presentation."""
    ordered = sorted(
        observations,
        key=lambda item: (
            item.rating_sum / item.rating_weight
            if item.rating_weight
            else -1.0,
            item.review_count,
            item.image_uid,
        ),
        reverse=True,
    )
    return tuple(item.image_uid for item in ordered[:8])


def _posterior_probability(aggregate: _Aggregate) -> float:
    return (aggregate.success + 1) / (
        aggregate.success + aggregate.failure + 2
    )


def _observed_score(
    observations: tuple[RenderEvidenceObservation, ...],
    *,
    jointly_observed: bool,
) -> EvidenceScore:
    aggregate = _aggregate(observations)
    expected = _posterior_probability(aggregate)
    average = (
        aggregate.rating_sum / aggregate.rating_weight
        if aggregate.rating_weight
        else None
    )
    lower_bound = _bayes_lb05(
        float(aggregate.success), float(aggregate.failure)
    )
    return EvidenceScore(
        source=GuidanceBasis.OBSERVED,
        score=lower_bound,
        expected_success_rate=expected,
        lower_bound=lower_bound,
        average_rating=average,
        image_count=aggregate.image_count,
        review_count=aggregate.review_count,
        confidence=_confidence(aggregate.image_count),
        sufficiently_observed=aggregate.image_count >= STABILITY_IMAGE_FLOOR,
        jointly_observed=jointly_observed,
    )


def _predicted_value_score(
    aggregate: _Aggregate, baseline_logit: float
) -> EvidenceScore | None:
    if aggregate.image_count < MAIN_EFFECT_IMAGE_FLOOR:
        return None
    raw_delta = _logit(_posterior_probability(aggregate)) - baseline_logit
    probability = float(
        _sigmoid(
            baseline_logit + raw_delta * _shrinkage(aggregate.image_count)
        )
    )
    return EvidenceScore(
        source=GuidanceBasis.PREDICTED,
        score=probability,
        expected_success_rate=probability,
        lower_bound=None,
        average_rating=None,
        image_count=aggregate.image_count,
        review_count=aggregate.review_count,
        confidence=_confidence(aggregate.image_count),
        sufficiently_observed=False,
        jointly_observed=False,
    )


def _main_effects(
    parameters: tuple[ParameterGuidance, ...],
    baseline_logit: float,
) -> dict[GuidanceParameter, dict[str, _Effect]]:
    effects: dict[GuidanceParameter, dict[str, _Effect]] = {
        parameter: {} for parameter in GuidanceParameter
    }
    for item in parameters:
        score = item.predicted
        if score is None or not item.applicable:
            continue
        effects[item.parameter][item.value] = _Effect(
            probability=score.expected_success_rate,
            delta=_logit(score.expected_success_rate) - baseline_logit,
            image_count=score.image_count,
        )
    return effects


def _candidate_values(values: dict[str, _Effect]) -> tuple[str, ...]:
    ordered = sorted(
        values.items(),
        key=lambda item: (
            item[1].probability,
            item[1].image_count,
            item[0],
        ),
        reverse=True,
    )
    return tuple(item[0] for item in ordered[:8])


def _settings_from_values(values: tuple[str, ...]) -> RenderSettings:
    return RenderSettings(
        checkpoint=values[0],
        sampler=values[1],
        scheduler=values[2],
        steps=int(float(values[3])),
        cfg=float(values[4]),
        denoise=float(values[5]),
    )


def _parameter_applicable(
    parameter: GuidanceParameter,
    value: str,
    capabilities: RenderCapabilitySet | None,
) -> bool:
    if capabilities is None:
        return True
    if parameter is GuidanceParameter.CHECKPOINT:
        return value in capabilities.checkpoints
    if parameter is GuidanceParameter.SAMPLER:
        return value in capabilities.samplers
    if parameter is GuidanceParameter.SCHEDULER:
        return value in capabilities.schedulers
    return True


def _observed_recommendation_key(
    item: RenderRecommendation,
) -> tuple[bool, float, float, float, int, str]:
    evidence = item.evidence
    return (
        evidence.sufficiently_observed,
        evidence.lower_bound or 0.0,
        evidence.expected_success_rate,
        evidence.average_rating or 0.0,
        evidence.image_count,
        item.settings.key,
    )


def _parameter_guidance_key(
    item: ParameterGuidance, basis: GuidanceBasis
) -> tuple[float, float, int, str]:
    evidence = _guidance_score(item, basis)
    return (
        evidence.score,
        evidence.expected_success_rate,
        evidence.image_count,
        item.value,
    )


def _guidance_score(
    item: ParameterGuidance, basis: GuidanceBasis
) -> EvidenceScore:
    score = (
        item.observed if basis is GuidanceBasis.OBSERVED else item.predicted
    )
    assert score is not None
    return score


def _confidence(image_count: int) -> GuidanceConfidence:
    if image_count < MAIN_EFFECT_IMAGE_FLOOR:
        return GuidanceConfidence.INSUFFICIENT
    if image_count < 10:
        return GuidanceConfidence.LOW
    if image_count < 30:
        return GuidanceConfidence.MEDIUM
    return GuidanceConfidence.HIGH


def _rank_recommendations(
    recommendations: tuple[RenderRecommendation, ...],
) -> tuple[RenderRecommendation, ...]:
    ranks = _percentile_ranks(
        tuple(item.evidence.score for item in recommendations)
    )
    return tuple(
        replace(item, evidence=replace(item.evidence, relative_rank=rank))
        for item, rank in zip(recommendations, ranks, strict=True)
    )


def _rank_parameter_guidance(
    guidance: tuple[ParameterGuidance, ...],
) -> tuple[ParameterGuidance, ...]:
    output = list(guidance)
    for parameter in GuidanceParameter:
        indexes = [
            index
            for index, item in enumerate(output)
            if item.parameter is parameter
        ]
        for field_name in ("observed", "predicted"):
            scored = [
                (index, getattr(output[index], field_name))
                for index in indexes
                if getattr(output[index], field_name) is not None
            ]
            ranks = _percentile_ranks(
                tuple(score.score for _, score in scored if score is not None)
            )
            for (index, score), rank in zip(scored, ranks, strict=True):
                assert score is not None
                output[index] = replace(
                    output[index],
                    **{field_name: replace(score, relative_rank=rank)},
                )
    return tuple(output)


def _percentile_ranks(
    values: tuple[float, ...],
) -> tuple[float | None, ...]:
    if not values:
        return ()
    if len(values) == 1:
        return (None,)
    ordered = sorted(values)
    return tuple(ordered.index(value) / (len(ordered) - 1) for value in values)


def _shrinkage(image_count: int) -> float:
    return image_count / (image_count + SHRINKAGE_PRIOR)


def _logit(probability: float) -> float:
    bounded = min(max(float(probability), 1e-9), 1.0 - 1e-9)
    return math.log(bounded / (1.0 - bounded))


def _value_sort_key(value: str) -> tuple[int, float | str]:
    try:
        return (0, float(value))
    except ValueError:
        return (1, value)
