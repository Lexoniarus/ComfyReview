"""JSON endpoints used by the Playground catalog interface."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Request
from fastapi.responses import JSONResponse

from comfyreview.api import get_application_container
from config import DB_PATH, PROMPT_TOKENS_DB_PATH
from services.file_urls import existing_png_path_to_url
from stores.playground_store import fetch_token_stats_for_tokens
from stores.prompt_tokens_match import fetch_best_match_preview

router = APIRouter()


def _split_tokens_csv(text: str) -> list[str]:
    return [
        token
        for part in str(text or "").replace("\n", " ").split(",")
        if (token := part.strip())
    ]


@router.post("/playground/token_stats")
def playground_token_stats(
    payload: Annotated[dict[str, object], Body()],
) -> JSONResponse:
    """Return the current transitional token statistics response."""
    tokens = payload.get("tokens") or []
    scope = payload.get("scope") or "pos"
    model_branch = payload.get("model_branch") or ""
    if not isinstance(tokens, list):
        return JSONResponse(
            {"ok": False, "error": "tokens must be list"},
            status_code=400,
        )
    stats = fetch_token_stats_for_tokens(
        PROMPT_TOKENS_DB_PATH,
        tokens=[str(token) for token in tokens],
        scope=str(scope),
        model_branch=str(model_branch),
    )
    return JSONResponse({"ok": True, "stats": stats})


@router.post("/playground/api/previews")
def playground_api_previews(
    request: Request,
    payload: Annotated[dict[str, object], Body()],
) -> JSONResponse:
    """Resolve catalog UIDs before querying transitional preview evidence."""
    item_uids = payload.get("item_ids") or []
    if not isinstance(item_uids, list):
        return JSONResponse(
            {"ok": False, "error": "item_ids must be list"},
            status_code=400,
        )
    scope = str(payload.get("scope") or "pos")
    minimum_hits = _nonnegative_int(payload.get("min_hits"), default=1)
    minimum_runs = _nonnegative_int(payload.get("min_runs"), default=0)
    model_branch = str(payload.get("model_branch") or "")
    views = get_application_container(request).prompt_catalog_views
    output: dict[str, object] = {}
    for raw_uid in item_uids:
        component_uid = str(raw_uid or "").strip()
        try:
            tokens = views.prompt_tokens(component_uid, scope=scope)
        except (KeyError, ValueError):
            output[component_uid] = None
            continue
        best = fetch_best_match_preview(
            prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
            ratings_db_path=DB_PATH,
            tokens=tokens,
            scope=scope,
            min_hits=minimum_hits,
            model_branch=model_branch,
            min_runs=minimum_runs,
        )
        output[component_uid] = _preview_with_url(best)
    return JSONResponse(output)


def _nonnegative_int(value: object, *, default: int) -> int:
    try:
        return max(int(str(value)), 0)
    except (TypeError, ValueError):
        return default


def _preview_with_url(best: object) -> dict[str, object] | None:
    if not isinstance(best, dict) or not best.get("png_path"):
        return None
    preview = dict(best)
    preview["url"] = existing_png_path_to_url(
        str(preview.get("png_path") or "")
    )
    return preview if preview["url"] else None
