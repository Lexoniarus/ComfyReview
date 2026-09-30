"""JSON endpoints used by the Playground catalog interface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from comfyreview.api import get_application_container
from comfyreview.application import PromptMatchPreview
from services.file_urls import existing_png_path_to_url

router = APIRouter()


@router.post("/playground/token_stats")
def playground_token_stats(
    request: Request,
    payload: Annotated[dict[str, object], Body()],
) -> JSONResponse:
    """Return canonical token statistics for requested prompt atoms."""
    tokens = payload.get("tokens") or []
    scope = payload.get("scope") or "pos"
    model_branch = payload.get("model_branch") or ""
    if not isinstance(tokens, list):
        return JSONResponse(
            {"ok": False, "error": "tokens must be list"},
            status_code=400,
        )
    statistics = get_application_container(
        request
    ).analytics_service.token_statistics_for(
        tuple(str(token) for token in tokens),
        scope=str(scope),
        model_branch=str(model_branch),
    )
    stats = {
        token: {
            "n": item.sample_count,
            "mean": item.mean_score,
            "lb05": item.lower_bound,
        }
        for token, item in statistics.items()
    }
    return JSONResponse({"ok": True, "stats": stats})


@router.post("/playground/api/previews")
def playground_api_previews(
    request: Request,
    payload: Annotated[dict[str, object], Body()],
) -> JSONResponse:
    """Resolve catalog UIDs before querying canonical preview evidence."""
    item_uids = payload.get("item_ids") or []
    if not isinstance(item_uids, list):
        return JSONResponse(
            {"ok": False, "error": "item_ids must be list"},
            status_code=400,
        )
    scope = str(payload.get("scope") or "pos")
    container = get_application_container(request)
    minimum_hits = max(_nonnegative_int(payload.get("min_hits"), default=1), 1)
    minimum_runs = _nonnegative_int(
        payload.get("min_runs"),
        default=container.settings.minimum_runs,
    )
    model_branch = str(payload.get("model_branch") or "")
    views = container.prompt_catalog_views
    output: dict[str, object] = {}
    for raw_uid in item_uids:
        component_uid = str(raw_uid or "").strip()
        try:
            tokens = views.prompt_tokens(component_uid, scope=scope)
        except (KeyError, ValueError):
            output[component_uid] = None
            continue
        best = container.analytics_service.best_prompt_match(
            tuple(tokens),
            scope=scope,
            minimum_hits=minimum_hits,
            model_branch=model_branch,
            minimum_ratings=minimum_runs,
            candidate_limit=container.settings.pool_limit,
        )
        output[component_uid] = _preview_with_url(best)
    return JSONResponse(output)


def _nonnegative_int(value: object, *, default: int) -> int:
    try:
        return max(int(str(value)), 0)
    except (TypeError, ValueError):
        return default


def _preview_with_url(best: object) -> dict[str, object] | None:
    if not isinstance(best, PromptMatchPreview):
        return None
    url = existing_png_path_to_url(str(best.png_path))
    if not url:
        return None
    return {
        "json_path": str(best.json_path or ""),
        "png_path": str(best.png_path),
        "hits": best.token_hits,
        "avg_rating": best.average_rating,
        "runs": best.rating_count,
        "url": url,
    }
