"""JSON presenters for canonical render guidance."""

from __future__ import annotations

from collections.abc import Callable

from comfyreview.application import (
    EvidenceScore,
    ParameterGuidance,
    RenderGuidance,
    RenderGuidancePage,
    RenderRecommendation,
    RenderSettings,
)


def guidance_response(guidance: RenderGuidance) -> dict[str, object]:
    """Translate one complete guidance result to JSON-safe values."""
    return {
        "model_version": guidance.model_version,
        "stability_image_floor": guidance.stability_image_floor,
        "coverage": {
            "image_count": guidance.coverage.image_count,
            "review_count": guidance.coverage.review_count,
            "observed_setup_count": guidance.coverage.observed_setup_count,
            "stable_setup_count": guidance.coverage.stable_setup_count,
            "modeled_value_counts": {
                parameter.value: count
                for parameter, count in guidance.coverage.modeled_value_counts
            },
        },
        "current": {
            "observed": recommendation_response(guidance.current_observed),
            "predicted": recommendation_response(guidance.current_predicted),
        },
        "recommendations": {
            "observed_setup": recommendation_response(guidance.observed_setup),
            "observed_parameters": recommendation_response(
                guidance.observed_parameters
            ),
            "predicted_setup": recommendation_response(
                guidance.predicted_setup
            ),
            "predicted_parameters": recommendation_response(
                guidance.predicted_parameters
            ),
        },
        "parameter_values": [
            parameter_response(item) for item in guidance.parameter_values
        ],
        "observed_setups": [
            recommendation_response(item) for item in guidance.observed_setups
        ],
        "predicted_setups": [
            recommendation_response(item) for item in guidance.predicted_setups
        ],
    }


def guidance_page_response(
    page: RenderGuidancePage,
    image_url: Callable[[str], str] | None = None,
) -> dict[str, object]:
    """Translate one Analytics page without moving scoring to HTTP."""
    items: list[dict[str, object] | None] = []
    for entry in page.entries:
        if isinstance(entry, RenderRecommendation):
            items.append(recommendation_response(entry, image_url=image_url))
        else:
            items.append(parameter_response(entry, image_url=image_url))
    return {
        "model_version": page.model_version,
        "basis": page.basis.value,
        "scope": page.scope.value,
        "parameter": page.parameter.value if page.parameter else None,
        "items": [item for item in items if item is not None],
        "total": page.total,
        "sufficiently_observed_total": page.sufficiently_observed_total,
        "filtered_total": page.filtered_total,
        "offset": page.offset,
        "limit": page.limit,
        "coverage": {
            "image_count": page.coverage.image_count,
            "review_count": page.coverage.review_count,
            "observed_setup_count": page.coverage.observed_setup_count,
            "stable_setup_count": page.coverage.stable_setup_count,
            "modeled_value_counts": {
                parameter.value: count
                for parameter, count in page.coverage.modeled_value_counts
            },
        },
    }


def recommendation_response(
    recommendation: RenderRecommendation | None,
    *,
    image_url: Callable[[str], str] | None = None,
) -> dict[str, object] | None:
    """Translate one optional complete recommendation."""
    if recommendation is None:
        return None
    return {
        "settings": settings_response(recommendation.settings),
        "evidence": score_response(recommendation.evidence),
        "applicable": recommendation.applicable,
        "best_images": evidence_images(recommendation.image_uids, image_url),
    }


def parameter_response(
    item: ParameterGuidance,
    *,
    image_url: Callable[[str], str] | None = None,
) -> dict[str, object]:
    """Translate one parameter value with both evidence layers."""
    return {
        "parameter": item.parameter.value,
        "value": item.value,
        "observed": score_response(item.observed),
        "predicted": score_response(item.predicted),
        "applicable": item.applicable,
        "best_images": evidence_images(item.image_uids, image_url),
    }


def settings_response(settings: RenderSettings) -> dict[str, object]:
    """Translate optimizer-controlled settings only."""
    return {
        "checkpoint": settings.checkpoint,
        "sampler": settings.sampler,
        "scheduler": settings.scheduler,
        "steps": settings.steps,
        "cfg": settings.cfg,
        "denoise": settings.denoise,
    }


def score_response(score: EvidenceScore | None) -> dict[str, object] | None:
    """Translate evidence without hiding support or provenance."""
    if score is None:
        return None
    return {
        "source": score.source.value,
        "score": score.score,
        "expected_success_rate": score.expected_success_rate,
        "lower_bound": score.lower_bound,
        "average_rating": score.average_rating,
        "image_count": score.image_count,
        "review_count": score.review_count,
        "confidence": score.confidence.value,
        "sufficiently_observed": score.sufficiently_observed,
        "jointly_observed": score.jointly_observed,
        "relative_rank": score.relative_rank,
    }


def evidence_images(
    image_uids: tuple[str, ...],
    image_url: Callable[[str], str] | None,
) -> list[dict[str, object]]:
    """Translate stable evidence identities without leaking file paths."""
    if image_url is None:
        return []
    return [
        {"image_uid": image_uid, "url": image_url(image_uid)}
        for image_uid in image_uids
    ]
