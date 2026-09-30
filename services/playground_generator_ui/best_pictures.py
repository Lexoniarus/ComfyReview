"""Canonical best-picture lookup for one Playground preview draft."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from comfyreview.application import AnalyticsService

ImageUrlResolver = Callable[[str], str]


def resolve_best_picture_for_draft(
    draft: dict[str, Any],
    *,
    analytics: AnalyticsService,
    minimum_ratings: int,
    candidate_limit: int,
    image_url: ImageUrlResolver,
) -> dict[str, object]:
    """Return canonical rating evidence for one preview draft."""
    selection = draft.get("selection") or {}
    if not isinstance(selection, dict):
        selection = {}
    scene = selection.get("scene") or {}
    if not isinstance(scene, dict):
        scene = {}
    tokens = tuple(
        token
        for part in str(scene.get("pos") or "").split(",")
        if (token := part.strip())
    )
    if not tokens:
        return _empty_result("skip", retry=False, retry_after_ms=0)
    try:
        match = analytics.best_prompt_match(
            tokens,
            scope="pos",
            minimum_hits=1,
            minimum_ratings=minimum_ratings,
            candidate_limit=candidate_limit,
        )
    except Exception as error:
        result = _empty_result("error", retry=True, retry_after_ms=2000)
        result["error"] = str(error)
        return result
    if match is None:
        return _empty_result("pending", retry=True, retry_after_ms=2000)
    url = image_url(str(match.png_path))
    if not url:
        return _empty_result("pending", retry=True, retry_after_ms=1500)
    return {
        "status": "ok",
        "best_img_url": url,
        "best_avg": match.average_rating,
        "best_runs": match.rating_count,
        "best_hits": match.token_hits,
        "retry": False,
        "retry_after_ms": 0,
    }


def _empty_result(
    status: str,
    *,
    retry: bool,
    retry_after_ms: int,
) -> dict[str, object]:
    return {
        "status": status,
        "best_img_url": "",
        "best_avg": None,
        "best_runs": None,
        "best_hits": None,
        "retry": retry,
        "retry_after_ms": retry_after_ms,
    }
