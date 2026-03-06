from __future__ import annotations

import sqlite3
from typing import Any, Dict, List

from config import DB_PATH

from stores.mv_state_store import list_states
from services.combo_prompts_service import ensure_combo_prompts_db, get_top_combos_2, get_top_combos_3


def build_playground_dashboard_context(
    *,
    combo_db_path,
    mv_queue_db_path,
    ratings_db_path=DB_PATH,
    default_max_tries: int,
    png_to_url,
) -> Dict[str, Any]:
    """Build context for the playground dashboard page."""

    ensure_combo_prompts_db(combo_db_path)

    top2 = _attach_urls(get_top_combos_2(combo_db_path, limit=8), png_to_url=png_to_url)
    top3 = _attach_urls(get_top_combos_3(combo_db_path, limit=8), png_to_url=png_to_url)

    max_id = _max_rating_id(ratings_db_path)
    mv_status = _build_mv_status(mv_queue_db_path=mv_queue_db_path, max_rating_id=max_id)

    return {
        "top2": top2,
        "top3": top3,
        "default_max_tries": int(default_max_tries),
        "max_rating_id": int(max_id),
        "mv_status": mv_status,
    }


def _max_rating_id(db_path) -> int:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        row = con.execute("SELECT COALESCE(MAX(id), 0) AS m FROM ratings").fetchone()
        return int(row["m"] or 0)
    finally:
        con.close()


def _pending(max_id: int, last_processed: int) -> int:
    try:
        return int(max_id) - int(last_processed)
    except Exception:
        return 0


def _attach_urls(rows: List[Dict[str, Any]], *, png_to_url) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for r0 in rows or []:
        r = dict(r0)

        best_png = str(r.get("best_png_path") or "")
        r["best_url"] = png_to_url(best_png) if best_png else ""

        best_images = []
        for bi0 in (r.get("best_images") or []):
            bi = dict(bi0)
            bi_png = str(bi.get("png_path") or "")
            bi["url"] = png_to_url(bi_png) if bi_png else ""
            best_images.append(bi)
        r["best_images"] = best_images

        out.append(r)
    return out


def _build_mv_status(*, mv_queue_db_path, max_rating_id: int) -> List[Dict[str, Any]]:
    states = list_states(mv_queue_db_path)
    st_map = {str(s.get("aggregator_name")): s for s in (states or [])}

    def _state_row(name: str) -> Dict[str, Any]:
        s = st_map.get(name) or {}
        lp = int(s.get("last_processed_rating_id") or 0)
        return {
            "name": name,
            "last_processed_rating_id": lp,
            "last_run_at": s.get("last_run_at"),
            "last_error": s.get("last_error"),
            "pending": _pending(int(max_rating_id), lp),
        }

    return [
        _state_row("prompt_ratings"),
        _state_row("combo_prompts"),
        _state_row("images"),
    ]
