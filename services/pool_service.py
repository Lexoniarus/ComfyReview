from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

from config import DB_PATH, IMAGES_DB_PATH, CURATION_DB_PATH, MIN_RUNS, POOL_LIMIT
from services.context_filters import extract_character_from_subdir as _extract_character_from_subdir
from stores.curation_store import fetch_set_map
from stores.images_store import init_images_db
from stores.ratings_state_store import fetch_latest_deleted_by_png_paths


@dataclass
class ScoredItem:
    # scanner.Item
    it: any
    avg: float
    runs: int
    pos_prompt: str


def _fetch_scores_by_png_paths(db_path: Path, png_paths: List[str]) -> Dict[str, Dict[str, object]]:
    """Bulk fetch from images.sqlite3 for given png_paths."""
    init_images_db(db_path)
    paths = [str(p) for p in (png_paths or []) if str(p).strip()]
    if not paths:
        return {}

    out: Dict[str, Dict[str, object]] = {}
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        chunk_size = 900
        for i in range(0, len(paths), chunk_size):
            chunk = paths[i : i + chunk_size]
            qmarks = ",".join(["?"] * len(chunk))
            rows = con.execute(
                f"SELECT png_path, avg_rating, runs, pos_prompt FROM images WHERE png_path IN ({qmarks})",
                chunk,
            ).fetchall()
            for r in rows:
                out[str(r["png_path"])] = {
                    "avg": float(r["avg_rating"]) if r["avg_rating"] is not None else None,
                    "runs": int(r["runs"] or 0),
                    "pos_prompt": str(r["pos_prompt"] or ""),
                }
        return out
    finally:
        con.close()


def build_ranked_pool(
    items: List[any],
    *,
    mode: str = "top",
    set_key: str = "",
    subdir: str = "",
    min_runs: int = MIN_RUNS,
    limit: int = POOL_LIMIT,
) -> Tuple[List[ScoredItem], Dict[str, Optional[str]]]:
    """Return ranked scored items according to vNext rules.

    vNext KORREKTUR:
    - Kein separates "Scope playground/character" mehr.
    - Subdir ist der Scope. Leer bedeutet "alle".

    Returns
    - ranked list[ScoredItem] limited to `limit`
    - curation map (png_path -> set_key or None)
    """
    mode = str(mode or "top").lower().strip()
    if mode not in {"top", "worst"}:
        mode = "top"

    set_key = str(set_key or "").strip()
    subdir = str(subdir or "").strip()

    items_f = list(items)
    if subdir:
        items_f = [it for it in items_f if str(getattr(it, "subdir", "")) == subdir]

    png_paths = [str(it.png_path) for it in items_f]
    scores = _fetch_scores_by_png_paths(IMAGES_DB_PATH, png_paths)
    curation_map = fetch_set_map(CURATION_DB_PATH, png_paths)

    # vNext Invariant: deleted images must never leak into pools.
    # ratings.sqlite3 contains the authoritative *latest* deleted state.
    deleted_map = fetch_latest_deleted_by_png_paths(DB_PATH, png_paths)

    scored: List[ScoredItem] = []
    for it in items_f:
        p = str(it.png_path)
        if int(deleted_map.get(p, 0) or 0) == 1:
            continue
        sc = scores.get(p)
        if not sc:
            continue
        avg = sc.get("avg")
        runs = int(sc.get("runs") or 0)
        if avg is None:
            continue
        if runs < int(min_runs or 0):
            continue

        assigned = curation_map.get(p)
        if set_key:
            if set_key == "unsorted":
                if assigned:
                    continue
            else:
                if assigned != set_key:
                    continue

        scored.append(
            ScoredItem(
                it=it,
                avg=float(avg),
                runs=runs,
                pos_prompt=str(sc.get("pos_prompt") or ""),
            )
        )
    # Ranking (vNext)
    # - top:   avg DESC, tie runs DESC
    # - worst: avg ASC,  tie runs DESC
    if mode == "top":
        scored.sort(key=lambda x: (-float(x.avg), -int(x.runs)))
    else:
        scored.sort(key=lambda x: (float(x.avg), -int(x.runs)))
    return scored[: int(limit or POOL_LIMIT)], curation_map


def list_characters_from_items(items: Iterable[any]) -> List[str]:
    chars = set()
    for it in items:
        c = _extract_character_from_subdir(getattr(it, "subdir", ""))
        if c:
            chars.add(c)
    return sorted(chars)


def extract_character_from_subdir(subdir: str) -> str:
    return _extract_character_from_subdir(subdir)
