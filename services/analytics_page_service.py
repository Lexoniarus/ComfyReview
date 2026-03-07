from __future__ import annotations

from typing import Any, Dict, List

from config import DB_PATH, IMAGES_DB_PATH, PROMPT_RATINGS_DB_PATH
from db_store import (
    DELETE_WEIGHT_DEFAULT,
    SUCCESS_THRESHOLD_DEFAULT,
    fetch_calculated_best_cases,
    fetch_combo_stats,
    fetch_param_stats,
    fetch_recommendations,
    list_models_from_db,
)
from services.context_filters import normalize_model
from services.file_urls import png_path_to_url
from stores.images_store import fetch_best_images_by_combo_keys, fetch_best_images_by_param_values
from stores.prompt_ratings_store import fetch_prompt_ratings_stats


def load_model_dropdown_list() -> List[str]:
    """Dropdown-Liste der vorhandenen Modelle aus ratings.sqlite3."""

    return list_models_from_db(DB_PATH)


def _attach_best_images_to_combo_rows(rows: List[Dict[str, Any]], model: str) -> None:
    combo_keys = [str(r.get("combo_key") or "") for r in rows if r.get("combo_key")]
    if not combo_keys:
        return

    best_map = fetch_best_images_by_combo_keys(
        IMAGES_DB_PATH,
        combo_keys,
        model_branch=model,
        limit_per=3,
    )

    for r in rows:
        ck = str(r.get("combo_key") or "")
        imgs = best_map.get(ck, [])
        r["best_images"] = [
            {
                "url": png_path_to_url(str(i.get("png_path") or "")),
                "avg_rating": i.get("avg_rating"),
                "runs": i.get("runs"),
            }
            for i in imgs
            if i.get("png_path")
        ]


def build_stats_page_context(
    *,
    model: str = "",
    min_n: int = 8,
    limit: int = 200,
    t: int = SUCCESS_THRESHOLD_DEFAULT,
    dw: float = DELETE_WEIGHT_DEFAULT,
) -> Dict[str, Any]:
    """Baut den Template-Context für /stats."""

    model = normalize_model(model)

    rows = fetch_combo_stats(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        limit=int(limit),
        success_threshold=int(t),
        delete_weight=float(dw),
    )

    _attach_best_images_to_combo_rows(rows, model)

    return {
        "rows": rows,
        "model": model,
        "min_n": min_n,
        "limit": limit,
        "t": t,
        "dw": dw,
        "model_list": load_model_dropdown_list(),
    }


def build_recommendations_page_context(
    *,
    model: str = "",
    min_n: int = 5,
    limit: int = 200,
    t: int = SUCCESS_THRESHOLD_DEFAULT,
    dw: int = DELETE_WEIGHT_DEFAULT,
    min_lb: float = 0.5,
    approx_min_n: int = 8,
    approx_limit: int = 80,
) -> Dict[str, Any]:
    """Baut den Template-Context für /recommendations."""

    model = normalize_model(model)

    rec = fetch_recommendations(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        limit=int(limit),
        success_threshold=int(t),
        delete_weight=int(dw),
        min_lb=float(min_lb),
        approx_min_n=int(approx_min_n),
        approx_limit=int(approx_limit),
    )

    stable = rec.get("stable", [])
    avoid = rec.get("avoid", [])
    approx = rec.get("approx")
    if not isinstance(approx, dict):
        approx = {"base": None, "rows": [], "notes": ""}

    return {
        "stable": stable,
        "avoid": avoid,
        "approx": approx,
        "model": model,
        "min_n": min_n,
        "limit": limit,
        "t": t,
        "dw": dw,
        "min_lb": min_lb,
        "approx_min_n": approx_min_n,
        "approx_limit": approx_limit,
        "model_list": load_model_dropdown_list(),
    }


def _build_param_sections(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    title_map = {
        "checkpoint": "Checkpoint",
        "steps": "Steps",
        "cfg": "CFG",
        "sampler": "Sampler",
        "scheduler": "Scheduler",
    }

    sections: List[Dict[str, Any]] = []
    for feat in ("checkpoint", "steps", "cfg", "sampler", "scheduler"):
        feat_rows = [r for r in rows if r.get("feat") == feat]
        sections.append({"key": feat, "title": title_map.get(feat, feat), "rows": feat_rows})
    return sections


def _attach_best_images_to_param_sections(sections: List[Dict[str, Any]], model: str) -> None:
    for sec in sections:
        vals = [r.get("value") for r in sec.get("rows", []) if r.get("value") is not None]
        if not vals:
            continue

        best_map = fetch_best_images_by_param_values(
            IMAGES_DB_PATH,
            feat=sec["key"],
            values=vals,
            model_branch=model,
            limit_per=3,
        )

        for r in sec.get("rows", []):
            key = str(r.get("value"))
            imgs = best_map.get(key, [])
            r["best_images"] = [
                {
                    "url": png_path_to_url(str(i.get("png_path") or "")),
                    "avg_rating": i.get("avg_rating"),
                    "runs": i.get("runs"),
                }
                for i in imgs
                if i.get("png_path")
            ]


def build_param_stats_page_context(
    *,
    model: str = "",
    min_n: int = 10,
    t: int = SUCCESS_THRESHOLD_DEFAULT,
    dw: int = DELETE_WEIGHT_DEFAULT,
) -> Dict[str, Any]:
    """Baut den Template-Context für /param_stats."""

    model = normalize_model(model)

    rows = fetch_param_stats(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        success_threshold=int(t),
        delete_weight=int(dw),
    )

    sections = _build_param_sections(rows)
    _attach_best_images_to_param_sections(sections, model)

    best = fetch_calculated_best_cases(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        success_threshold=int(t),
        delete_weight=int(dw),
        limit=200,
    )

    best_tested = fetch_combo_stats(
        DB_PATH,
        model=model,
        min_n=int(min_n),
        limit=200,
        success_threshold=int(t),
        delete_weight=int(dw),
    )

    return {
        "stats": sections,
        "best": best,
        "best_tested": best_tested,
        "model": model,
        "min_n": min_n,
        "t": t,
        "dw": dw,
        "model_list": load_model_dropdown_list(),
    }


def build_prompt_tokens_page_context(
    *,
    model: str = "",
    scope: str = "pos",
    min_n: int = 8,
    limit: int = 200,
) -> Dict[str, Any]:
    """Baut den Template-Context für /prompt_tokens."""

    model = normalize_model(model)

    rows = fetch_prompt_ratings_stats(
        PROMPT_RATINGS_DB_PATH,
        model=model,
        scope=scope,
        min_n=min_n,
        limit=limit,
    )

    return {
        "rows": rows,
        "model": model,
        "scope": scope,
        "min_n": min_n,
        "limit": limit,
        "model_list": load_model_dropdown_list(),
    }
