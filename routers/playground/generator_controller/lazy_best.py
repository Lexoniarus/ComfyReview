from __future__ import annotations

"""Lazy best-picture resolution for generator preview drafts."""

from fastapi.responses import JSONResponse

from routers.playground._shared import GENERATOR_PREVIEW_STATE_PATH, png_path_to_url

from services.playground_generator_ui_service import load_preview_state, save_preview_state
from services.playground_generator_ui.best_pictures import resolve_best_picture_for_draft


def resolve_best_for_draft(draft_id: str) -> JSONResponse:
    preview = load_preview_state(GENERATOR_PREVIEW_STATE_PATH) or []
    draft_id_s = str(draft_id or "").strip()
    if not draft_id_s:
        return JSONResponse({"status": "error", "error": "missing draft_id"}, status_code=400)

    d = None
    for x in preview:
        if str((x or {}).get("draft_id") or "").strip() == draft_id_s:
            d = x
            break

    if d is None:
        return JSONResponse({"status": "error", "error": "draft not found"}, status_code=404)

    # Fast path if already resolved.
    if str((d or {}).get("best_img_url") or "").strip():
        return JSONResponse(
            {
                "status": "ok",
                "best_img_url": d.get("best_img_url") or "",
                "best_avg": d.get("best_avg"),
                "best_runs": d.get("best_runs"),
                "best_hits": d.get("best_hits"),
                "retry": False,
            }
        )

    res = resolve_best_picture_for_draft(d, png_to_url=png_path_to_url)

    # Persist into preview state if we got a definitive answer.
    if res.get("status") == "ok" and res.get("best_img_url"):
        for x in preview:
            if str((x or {}).get("draft_id") or "").strip() == draft_id_s:
                x["best_img_url"] = res.get("best_img_url") or ""
                x["best_avg"] = res.get("best_avg")
                x["best_runs"] = res.get("best_runs")
                x["best_hits"] = res.get("best_hits")
                break
        try:
            save_preview_state(GENERATOR_PREVIEW_STATE_PATH, preview)
        except Exception:
            pass

    return JSONResponse(res)
