import json
import random
from datetime import datetime

from config import (
    ARENA_DB_PATH,
    DB_PATH,
    PROMPT_TOKENS_DB_PATH,
    MV_QUEUE_DB_PATH,
    IMAGES_DB_PATH,
)
import sqlite3
from stores.images_store import init_images_db
from arena_store import (
    ensure_schema as ensure_arena_schema,
    has_match as arena_has_match,
    insert_match as arena_insert_match,
)
from db_store import db, insert_or_update_rating
from meta_view import extract_prompts, extract_view
from services.rating_service import parse_float, parse_int, rating_avg_and_runs_for_json
from stores.mv_jobs_store import enqueue_job
from services.prompt_tokens_service import write_prompt_tokens_for_latest_run



def arena_target_ratings(avg_a: float, avg_b: float):
    # Zweck:
    # - erzeugt künstliche Bewertungsziele für Winner/Loser basierend auf deren Avg
    # - Winner bekommt avg+2 (max 10), Loser avg-2 (min 1)
    # Quelle:
    # - avg_a/avg_b aus ratings.sqlite3
    # Ziel:
    # - (winner_int, loser_int) für insert_or_update_rating

    high = max(avg_a, avg_b)
    low = min(avg_a, avg_b)

    winner_f = min(10.0, high + 2.0)
    loser_f = max(1.0, low - 2.0)

    winner_i = int(round(winner_f))
    loser_i = int(round(loser_f))

    winner_i = min(10, max(1, winner_i))
    loser_i = min(10, max(1, loser_i))
    return winner_i, loser_i


def find_item_by_json(items, json_path: str):
    # Zweck:
    # - findet Item (aus scan_output Liste) anhand json_path
    # Quelle:
    # - items aus scanner.scan_output()
    # Ziel:
    # - Item oder None
    jp = str(json_path)
    for it in items:
        if str(it.json_path) == jp:
            return it
    return None


def pick_arena_pair(items, scored):
    # Zweck:
    # - wählt zwei Kandidaten aus "scored" (Top Pool)
    # - verhindert doppelte Paarungen über arena.sqlite3 (arena_has_match)
    # Quelle:
    # - scored aus top_service.pick_top_candidates()
    # - arena DB (has_match)
    # Ziel:
    # - (left_it, right_it, left_avg, right_avg, left_runs, right_runs)

    def _direction_for(a_json: str, b_json: str):
        # Wenn (a,b) und (b,a) schon bewertet sind -> None
        ab = arena_has_match(ARENA_DB_PATH, a_json, b_json)
        ba = arena_has_match(ARENA_DB_PATH, b_json, a_json)
        if ab and ba:
            return None
        if ab and not ba:
            return (b_json, a_json)
        if ba and not ab:
            return (a_json, b_json)
        return (a_json, b_json)

    left_it = None
    right_it = None
    left_avg = None
    right_avg = None
    left_runs = 0
    right_runs = 0

    for _ in range(400):
        a_it, a_avg, a_n = random.choice(scored)
        b_it, b_avg, b_n = random.choice(scored)
        if str(a_it.json_path) == str(b_it.json_path):
            continue

        directed = _direction_for(str(a_it.json_path), str(b_it.json_path))
        if directed is None:
            continue

        left_json, right_json = directed
        left_it = find_item_by_json(items, left_json)
        right_it = find_item_by_json(items, right_json)
        if left_it is None or right_it is None:
            continue

        if str(a_it.json_path) == left_json:
            left_avg, left_runs = a_avg, a_n
            right_avg, right_runs = b_avg, b_n
        else:
            left_avg, left_runs = b_avg, b_n
            right_avg, right_runs = a_avg, a_n
        break

    return left_it, right_it, left_avg, right_avg, left_runs, right_runs


def insert_arena_result(left_it, right_it, left_json: str, right_json: str, winner_side: str):
    # Zweck:
    # - schreibt Match in arena.sqlite3
    # - schreibt zwei Ratings in ratings.sqlite3:
    #   winner_target und loser_target
    # Quelle:
    # - left/right Items aus scan_output
    # - avg Werte aus ratings.sqlite3
    # Ziel:
    # - arena.sqlite3: Match gespeichert
    # - ratings.sqlite3: 2 neue rating Runs

    # vNext: avg values should come from images.sqlite3 (score MV, keyed by png_path).
    # Fallback to ratings aggregation only if MV row is missing.
    def _avg_from_images(png_path: str):
        init_images_db(IMAGES_DB_PATH)
        con2 = sqlite3.connect(IMAGES_DB_PATH)
        con2.row_factory = sqlite3.Row
        try:
            r = con2.execute(
                "SELECT avg_rating FROM images WHERE png_path = ? LIMIT 1",
                [str(png_path)],
            ).fetchone()
            if r and r["avg_rating"] is not None:
                return float(r["avg_rating"])
        finally:
            con2.close()
        return None

    left_avg = _avg_from_images(str(left_it.png_path))
    right_avg = _avg_from_images(str(right_it.png_path))

    if left_avg is None or right_avg is None:
        con = db(DB_PATH)
        try:
            left_avg, _ = rating_avg_and_runs_for_json(con, str(left_it.json_path))
            right_avg, _ = rating_avg_and_runs_for_json(con, str(right_it.json_path))
        finally:
            con.close()

    if left_avg is None or right_avg is None:
        return

    winner_target, loser_target = arena_target_ratings(float(left_avg), float(right_avg))

    if winner_side == "left":
        winner_it, loser_it = left_it, right_it
        winner_json = left_json
    else:
        winner_it, loser_it = right_it, left_it
        winner_json = right_json

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        arena_insert_match(
            ARENA_DB_PATH,
            left_json=left_json,
            right_json=right_json,
            winner_json=winner_json,
            created_at=now,
            run=None,
        )
    except Exception:
        pass

    def _insert_int_rating(it, rating_int: int):
        # Zweck:
        # - nimmt ein Item, extrahiert view + prompts
        # - schreibt einen Rating Run in ratings.sqlite3
        view = extract_view(it.meta)
        pos_prompt, neg_prompt, _ = extract_prompts(it.meta)

        loras_json_v = "[]"
        try:
            loras_json_v = json.dumps(view.get("loras", []), ensure_ascii=False)
        except Exception:
            loras_json_v = "[]"

        insert_or_update_rating(
            DB_PATH,
            png_path=str(it.png_path),
            json_path=str(it.json_path),
            model_branch=str(it.model_branch or ""),
            checkpoint=str(it.checkpoint or ""),
            combo_key=str(getattr(it, "combo_key", "") or ""),
            rating=int(rating_int),
            deleted=0,
            steps=parse_int(view.get("steps")),
            cfg=parse_float(view.get("cfg")),
            sampler=str(view.get("sampler")) if view.get("sampler") is not None else None,
            scheduler=str(view.get("scheduler")) if view.get("scheduler") is not None else None,
            denoise=parse_float(view.get("denoise")),
            loras_json=loras_json_v,
            pos_prompt=pos_prompt,
            neg_prompt=neg_prompt,
        )
        # Rohdaten Update: prompt_tokens pro Run schreiben (kein MV)
        try:
            write_prompt_tokens_for_latest_run(
                ratings_db_path=DB_PATH,
                prompt_tokens_db_path=PROMPT_TOKENS_DB_PATH,
                json_path=str(it.json_path),
                model_branch=str(it.model_branch or ""),
                pos_prompt=str(pos_prompt or ""),
                neg_prompt=str(neg_prompt or ""),
                rating=int(rating_int),
                deleted=0,
            )
        except Exception as e:
            print(f"prompt_tokens write failed after arena rating: {e}")

        # Queue Trigger: Worker Catchup
        try:
            enqueue_job(MV_QUEUE_DB_PATH, job_type="catchup")
        except Exception as e:
            print(f"enqueue mv_job failed after arena rating: {e}")

    _insert_int_rating(winner_it, winner_target)
    _insert_int_rating(loser_it, loser_target)
