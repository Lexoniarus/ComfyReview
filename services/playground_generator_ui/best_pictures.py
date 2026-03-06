from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from config import DB_PATH, MIN_RUNS, POOL_LIMIT, PROMPT_TOKENS_DB_PATH
from stores.prompt_tokens_match import fetch_best_match_preview


def _tokens_from_scene_selection(selection: Dict[str, Any]) -> List[str]:
    """Best picture tokens.

    vNext requires at least the scene. Today we use only the scene pos tokens because that
    is stable and avoids overfitting.
    """
    scene = (selection or {}).get("scene") or {}
    scene_pos = str(scene.get("pos") or "").strip()
    return [t.strip() for t in scene_pos.split(",") if t.strip()]


def resolve_best_picture_for_draft(
    draft: Dict[str, Any],
    *,
    prompt_tokens_db_path: Path = PROMPT_TOKENS_DB_PATH,
    ratings_db_path: Path = DB_PATH,
    min_runs: int = MIN_RUNS,
    pool_limit: int = POOL_LIMIT,
    png_to_url,
) -> Dict[str, Any]:
    """Resolve best picture for exactly one preview draft.

    This is used by lazy loading on the generator page.
    """
    d = dict(draft or {})
    sel = d.get("selection") or {}
    toks = _tokens_from_scene_selection(sel)

    if not toks:
        return {
            "status": "skip",
            "best_img_url": "",
            "best_avg": None,
            "best_runs": None,
            "best_hits": None,
            "retry": False,
            "retry_after_ms": 0,
        }

    try:
        best = fetch_best_match_preview(
            prompt_tokens_db_path,
            ratings_db_path,
            tokens=toks,
            scope="pos",
            min_hits=1,
            candidate_limit=int(pool_limit),
            min_runs=int(min_runs),
        )
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "best_img_url": "",
            "best_avg": None,
            "best_runs": None,
            "best_hits": None,
            "retry": True,
            "retry_after_ms": 2000,
        }

    if best and best.get("png_path"):
        png_path = Path(str(best.get("png_path") or ""))
        if png_path.exists():
            return {
                "status": "ok",
                "best_img_url": png_to_url(str(png_path)),
                "best_avg": best.get("avg_rating"),
                "best_runs": best.get("runs"),
                "best_hits": best.get("hits"),
                "retry": False,
                "retry_after_ms": 0,
            }

        # DB row exists but file is not present yet.
        return {
            "status": "pending",
            "best_img_url": "",
            "best_avg": None,
            "best_runs": None,
            "best_hits": None,
            "retry": True,
            "retry_after_ms": 1500,
        }

    # Nothing found yet. This can change while ratings/worker catches up.
    return {
        "status": "pending",
        "best_img_url": "",
        "best_avg": None,
        "best_runs": None,
        "best_hits": None,
        "retry": True,
        "retry_after_ms": 2000,
    }


def enrich_preview_with_best_pictures(
    drafts: List[Dict[str, Any]],
    *,
    prompt_tokens_db_path: Path = PROMPT_TOKENS_DB_PATH,
    ratings_db_path: Path = DB_PATH,
    min_runs: int = MIN_RUNS,
    pool_limit: int = POOL_LIMIT,
    png_to_url,
) -> List[Dict[str, Any]]:
    """Attach best image info to each draft, if matchable.

    Note: The generator page no longer calls this on full page render.
    It is kept for compatibility and for any other call sites.
    """
    out = [dict(x) for x in (drafts or [])]
    for d in out:
        res = resolve_best_picture_for_draft(
            d,
            prompt_tokens_db_path=prompt_tokens_db_path,
            ratings_db_path=ratings_db_path,
            min_runs=int(min_runs),
            pool_limit=int(pool_limit),
            png_to_url=png_to_url,
        )
        if res.get("status") == "ok" and res.get("best_img_url"):
            d["best_img_url"] = res.get("best_img_url") or ""
            d["best_avg"] = res.get("best_avg")
            d["best_runs"] = res.get("best_runs")
            d["best_hits"] = res.get("best_hits")
        else:
            d["best_img_url"] = ""
    return out
