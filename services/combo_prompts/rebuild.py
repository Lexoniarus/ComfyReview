from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from stores.playground_store import list_items
from stores.combo_prompts_store import (
    init_combo_prompts_db,
    clear_combo_prompts,
    upsert_combo_prompt,
    upsert_combo_best_image,
    list_top_combo_prompts_with_images,
)

from .token_utils import combo_item_tokens, dedup_keep_order
from .images_index import build_images_token_index, combo_images_for_tokens
from .scoring import score_token_block


def ensure_combo_prompts_db(db_path: Path) -> None:
    init_combo_prompts_db(db_path)


def rebuild_combo_prompts(
    *,
    combo_db_path: Path,
    playground_db_path: Path,
    prompt_ratings_db_path: Path,
    images_db_path: Path,
    model_branch: str = "",
    max_combos_3: int = 200000,
    # Backward compat: older callers may still pass these.
    prompt_tokens_db_path: Optional[Path] = None,
    ratings_db_path: Optional[Path] = None,
    candidate_limit: int = 5000,
    hard_scope: str = "pos",
) -> Dict[str, Any]:
    """Atomic rebuild wrapper.

    Builds the combo DB into a temp file and swaps atomically.
    """

    combo_db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = combo_db_path.with_name(combo_db_path.name + ".tmp")
    if tmp_path.exists():
        try:
            tmp_path.unlink()
        except Exception:
            pass

    res = _rebuild_combo_prompts_into(
        combo_db_path=tmp_path,
        playground_db_path=playground_db_path,
        prompt_ratings_db_path=prompt_ratings_db_path,
        images_db_path=images_db_path,
        model_branch=model_branch,
        max_combos_3=max_combos_3,
    )

    os.replace(str(tmp_path), str(combo_db_path))
    res["atomic_swap"] = True
    return res


def get_top_combos_2(db_path: Path, limit: int = 3) -> List[Dict[str, Any]]:
    init_combo_prompts_db(db_path)
    return list_top_combo_prompts_with_images(db_path, combo_size=2, limit=int(limit))


def get_top_combos_3(db_path: Path, limit: int = 3) -> List[Dict[str, Any]]:
    init_combo_prompts_db(db_path)
    return list_top_combo_prompts_with_images(db_path, combo_size=3, limit=int(limit))


def _rebuild_combo_prompts_into(
    *,
    combo_db_path: Path,
    playground_db_path: Path,
    prompt_ratings_db_path: Path,
    images_db_path: Path,
    model_branch: str = "",
    max_combos_3: int = 200000,
) -> Dict[str, Any]:
    init_combo_prompts_db(combo_db_path)
    clear_combo_prompts(combo_db_path)

    idx = build_images_token_index(images_db_path=images_db_path, model_branch=str(model_branch or ""))
    pos_index: Dict[str, Set[str]] = idx["pos_index"]
    neg_index: Dict[str, Set[str]] = idx["neg_index"]
    images_by_png: Dict[str, Dict[str, Any]] = idx["images_by_png"]

    chars, scenes, outfits = _load_combo_sources(playground_db_path)
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    written_2 = _rebuild_combos_2(
        combo_db_path=combo_db_path,
        prompt_ratings_db_path=prompt_ratings_db_path,
        pos_index=pos_index,
        neg_index=neg_index,
        images_by_png=images_by_png,
        model_branch=str(model_branch or ""),
        chars=chars,
        scenes=scenes,
        now=now,
    )

    written_3 = _rebuild_combos_3(
        combo_db_path=combo_db_path,
        prompt_ratings_db_path=prompt_ratings_db_path,
        pos_index=pos_index,
        neg_index=neg_index,
        images_by_png=images_by_png,
        model_branch=str(model_branch or ""),
        chars=chars,
        scenes=scenes,
        outfits=outfits,
        now=now,
        max_combos_3=int(max_combos_3),
    )

    return {
        "written_2": int(written_2),
        "written_3": int(written_3),
        "chars": int(len(chars)),
        "scenes": int(len(scenes)),
        "outfits": int(len(outfits)),
    }


def _load_combo_sources(playground_db_path: Path) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    chars = list_items(playground_db_path, kind="character", q="", limit=10000)
    scenes = list_items(playground_db_path, kind="scene", q="", limit=10000)
    outfits = list_items(playground_db_path, kind="outfit", q="", limit=10000)
    return chars, scenes, outfits


def _rebuild_combos_2(
    *,
    combo_db_path: Path,
    prompt_ratings_db_path: Path,
    pos_index: Dict[str, Set[str]],
    neg_index: Dict[str, Set[str]],
    images_by_png: Dict[str, Dict[str, Any]],
    model_branch: str,
    chars: List[Dict[str, Any]],
    scenes: List[Dict[str, Any]],
    now: str,
) -> int:
    written = 0
    for c in chars:
        cpos, cneg = combo_item_tokens(c)
        for s in scenes:
            spos, sneg = combo_item_tokens(s)
            pos_tokens = dedup_keep_order(cpos + spos)
            neg_tokens = dedup_keep_order(cneg + sneg)

            combo_key = f"character:{int(c['id'])}|scene:{int(s['id'])}"
            label = f"{c.get('name','')} + {s.get('name','')}"

            _write_combo_row(
                combo_db_path=combo_db_path,
                prompt_ratings_db_path=prompt_ratings_db_path,
                pos_index=pos_index,
                neg_index=neg_index,
                images_by_png=images_by_png,
                model_branch=model_branch,
                combo_key=combo_key,
                combo_size=2,
                character_id=int(c["id"]),
                scene_id=int(s["id"]),
                outfit_id=None,
                label=label,
                pos_tokens=pos_tokens,
                neg_tokens=neg_tokens,
                now=now,
            )
            written += 1
    return int(written)


def _rebuild_combos_3(
    *,
    combo_db_path: Path,
    prompt_ratings_db_path: Path,
    pos_index: Dict[str, Set[str]],
    neg_index: Dict[str, Set[str]],
    images_by_png: Dict[str, Dict[str, Any]],
    model_branch: str,
    chars: List[Dict[str, Any]],
    scenes: List[Dict[str, Any]],
    outfits: List[Dict[str, Any]],
    now: str,
    max_combos_3: int,
) -> int:
    combos_3 = int(len(chars)) * int(len(scenes)) * int(len(outfits))
    if combos_3 > int(max_combos_3):
        raise ValueError(
            f"3er Kombis zu gross: {combos_3} > {int(max_combos_3)}. Bitte Outfits/Scenes reduzieren oder max_combos_3 erhoehen."
        )

    written = 0
    for c in chars:
        cpos, cneg = combo_item_tokens(c)
        for s in scenes:
            spos, sneg = combo_item_tokens(s)
            for o in outfits:
                opos, oneg = combo_item_tokens(o)

                pos_tokens = dedup_keep_order(cpos + spos + opos)
                neg_tokens = dedup_keep_order(cneg + sneg + oneg)

                combo_key = f"character:{int(c['id'])}|scene:{int(s['id'])}|outfit:{int(o['id'])}"
                label = f"{c.get('name','')} + {s.get('name','')} + {o.get('name','')}"

                _write_combo_row(
                    combo_db_path=combo_db_path,
                    prompt_ratings_db_path=prompt_ratings_db_path,
                    pos_index=pos_index,
                    neg_index=neg_index,
                    images_by_png=images_by_png,
                    model_branch=model_branch,
                    combo_key=combo_key,
                    combo_size=3,
                    character_id=int(c["id"]),
                    scene_id=int(s["id"]),
                    outfit_id=int(o["id"]),
                    label=label,
                    pos_tokens=pos_tokens,
                    neg_tokens=neg_tokens,
                    now=now,
                )
                written += 1

    return int(written)


def _write_combo_row(
    *,
    combo_db_path: Path,
    prompt_ratings_db_path: Path,
    pos_index: Dict[str, Set[str]],
    neg_index: Dict[str, Set[str]],
    images_by_png: Dict[str, Dict[str, Any]],
    model_branch: str,
    combo_key: str,
    combo_size: int,
    character_id: int,
    scene_id: int,
    outfit_id: Optional[int],
    label: str,
    pos_tokens: List[str],
    neg_tokens: List[str],
    now: str,
) -> None:
    pos_stats = score_token_block(
        prompt_ratings_db_path=prompt_ratings_db_path,
        scope="pos",
        tokens=pos_tokens,
        model_branch=str(model_branch or ""),
    )
    neg_stats = score_token_block(
        prompt_ratings_db_path=prompt_ratings_db_path,
        scope="neg",
        tokens=neg_tokens,
        model_branch=str(model_branch or ""),
    )

    combo_calc = combo_images_for_tokens(
        pos_index=pos_index,
        neg_index=neg_index,
        images_by_png=images_by_png,
        pos_tokens=pos_tokens,
        neg_tokens=neg_tokens,
    )

    best3 = combo_calc.get("best3") or []
    best1 = best3[0] if best3 else None

    _write_combo_best_images(combo_db_path, combo_key, best3)

    upsert_combo_prompt(
        combo_db_path,
        {
            "combo_key": combo_key,
            "combo_size": int(combo_size),
            "character_id": int(character_id),
            "scene_id": int(scene_id),
            "outfit_id": int(outfit_id) if outfit_id is not None else None,
            "label": label,
            "pos_tokens": ",".join(pos_tokens),
            "neg_tokens": ",".join(neg_tokens),
            "score": combo_calc.get("combo_avg_rating"),
            "coverage": pos_stats.get("coverage"),
            "stability": 0.0,
            "best_json_path": best1.get("json_path") if best1 else None,
            "best_png_path": best1.get("png_path") if best1 else None,
            "best_avg_rating": best1.get("avg_rating") if best1 else None,
            "best_runs": int(best1.get("runs") or 0) if best1 else 0,
            "best_hits": int(len(set(pos_tokens))),
            "combo_avg_rating": combo_calc.get("combo_avg_rating"),
            "combo_image_count": int(combo_calc.get("combo_image_count") or 0),
            "combo_total_runs": int(combo_calc.get("combo_total_runs") or 0),
            "combo_pos_avg_rating": pos_stats.get("avg"),
            "combo_pos_runs": int(pos_stats.get("runs") or 0),
            "combo_pos_total_tokens": int(pos_stats.get("total_tokens") or 0),
            "combo_pos_rated_tokens": int(pos_stats.get("rated_tokens") or 0),
            "combo_pos_coverage": float(pos_stats.get("coverage") or 0.0),
            "combo_neg_avg_rating": neg_stats.get("avg"),
            "combo_neg_runs": int(neg_stats.get("runs") or 0),
            "combo_neg_total_tokens": int(neg_stats.get("total_tokens") or 0),
            "combo_neg_rated_tokens": int(neg_stats.get("rated_tokens") or 0),
            "combo_neg_coverage": float(neg_stats.get("coverage") or 0.0),
            "last_updated": now,
        },
    )


def _write_combo_best_images(combo_db_path: Path, combo_key: str, best3: List[Dict[str, Any]]) -> None:
    for rank, b in enumerate(best3, start=1):
        upsert_combo_best_image(
            combo_db_path,
            {
                "combo_key": combo_key,
                "rank": int(rank),
                "png_path": b.get("png_path"),
                "json_path": b.get("json_path"),
                "avg_rating": b.get("avg_rating"),
                "runs": int(b.get("runs") or 0),
            },
        )
