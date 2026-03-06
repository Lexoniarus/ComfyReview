import json

from config import DB_PATH
from db_store import db
from meta_view import extract_view
from services.rating_service import rating_avg_and_runs_for_json


def pick_top_candidates(items, min_runs: int = 3, limit: int = 128):
    # Zweck:
    # - nimmt Item-Liste (aus scan_output)
    # - liest pro Item avg + runs aus ratings.sqlite3
    # - filtert: avg muss existieren und runs >= min_runs
    # - sortiert nach (avg desc, runs desc)
    # - gibt max "limit" Kandidaten zurück
    #
    # Quelle:
    # - items: scanner.scan_output()
    # - DB: ratings.sqlite3
    # Ziel:
    # - scored list [(it, avg, runs), ...]

    con = db(DB_PATH)
    try:
        scored = []
        for it in items:
            avg, n = rating_avg_and_runs_for_json(con, str(it.json_path))
            if avg is None or n < min_runs:
                continue
            scored.append((it, avg, n))
        scored.sort(key=lambda t: (t[1], t[2]), reverse=True)
        return scored[:limit]
    finally:
        con.close()


def build_top_cards(top_items):
    # Zweck:
    # - baut aus scored Items eine Template-freundliche Kartenliste
    # Quelle:
    # - top_items: Ergebnis aus pick_top_candidates
    # - meta_view.extract_view(meta): liefert sampler/scheduler/steps/cfg/denoise
    # Ziel:
    # - cards list[dict] fürs Template TOP_PICTURES_HTML

    cards = []
    for it, avg, n in top_items:
        view = extract_view(it.meta)
        cards.append(
            {
                "img_url": f"/files/{it.subdir}/{it.png_path.name}",
                "json_path": str(it.json_path),
                "model_branch": it.model_branch,
                "checkpoint": it.checkpoint,
                "avg": float(avg),
                "runs": int(n),
                "sampler": view.get("sampler"),
                "scheduler": view.get("scheduler"),
                "steps": view.get("steps"),
                "cfg": view.get("cfg"),
                "denoise": view.get("denoise"),
                "png_path": str(it.png_path),
                "combo_key": str(getattr(it, "combo_key", "") or ""),
                "subdir": it.subdir,
            }
        )
    return cards