# routers/playground/api.py
from __future__ import annotations

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from typing import Any, Dict, List

from config import (
    PLAYGROUND_DB_PATH,
    PROMPT_TOKENS_DB_PATH,
    DB_PATH,
)

from stores.playground_store import fetch_token_stats_for_tokens, get_item_by_id
from stores.prompt_tokens_match import fetch_best_match_preview

from ._shared import png_path_to_url

router = APIRouter()


def _split_tokens_csv(text: str) -> List[str]:
    if not text:
        return []
    t = str(text).replace("\n", " ")
    parts = [p.strip() for p in t.split(",")]
    return [p for p in parts if p]


@router.post("/playground/token_stats")
def playground_token_stats(payload: dict = Body(...)):
    tokens = payload.get("tokens") or []
    scope = payload.get("scope") or "pos"
    model_branch = payload.get("model_branch") or ""

    if not isinstance(tokens, list):
        return JSONResponse({"ok": False, "error": "tokens must be list"}, status_code=400)

    stats = fetch_token_stats_for_tokens(
        PROMPT_TOKENS_DB_PATH,
        tokens=[str(t) for t in tokens],
        scope=str(scope),
        model_branch=str(model_branch),
    )
    return JSONResponse({"ok": True, "stats": stats})


@router.post("/playground/api/previews")
def playground_api_previews(payload: dict = Body(...)):
    item_ids = payload.get("item_ids") or []
    scope = payload.get("scope") or "pos"
    min_hits = int(payload.get("min_hits") or 1)
    min_runs = int(payload.get("min_runs") or 0)
    model_branch = payload.get("model_branch") or ""

    if not isinstance(item_ids, list):
        return JSONResponse({"ok": False, "error": "item_ids must be list"}, status_code=400)

    out: Dict[str, Any] = {}

    for item_id in item_ids:
        try:
            iid = int(float(str(item_id)))
        except Exception:
            continue

        item = get_item_by_id(PLAYGROUND_DB_PATH, iid)
        if not item:
            out[str(item_id)] = None
            continue

        prompt = item.get("pos") if str(scope) == "pos" else item.get("neg")
        tokens = _split_tokens_csv(str(prompt or ""))

        best = fetch_best_match_preview(
            prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
            ratings_db_path=DB_PATH,
            tokens=tokens,
            scope=str(scope),
            min_hits=min_hits,
            model_branch=str(model_branch),
            min_runs=min_runs,
        )

        if best and best.get("png_path"):
            best = dict(best)
            best["url"] = png_path_to_url(str(best.get("png_path") or ""))

        out[str(item_id)] = best

    return JSONResponse(out)
