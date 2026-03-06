from __future__ import annotations

from pathlib import Path

from stores.mv_state_store import get_state, upsert_state

from services.combo_prompts_service import rebuild_combo_prompts

from services.mv_worker_core.time_utils import utc_now_str


def process_combo_prompts_once(
    *,
    state_db_path: Path,
    prompt_ratings_db_path: Path,
    combo_db_path: Path,
    playground_db_path: Path,
    images_db_path: Path,
    target_rating_id: int,
) -> int:
    target = int(target_rating_id or 0)

    st_prompt = get_state(state_db_path, aggregator_name="prompt_ratings")
    prompt_last = int(st_prompt.get("last_processed_rating_id") or 0)

    st_images = get_state(state_db_path, aggregator_name="images")
    images_last = int(st_images.get("last_processed_rating_id") or 0)

    st_combo = get_state(state_db_path, aggregator_name="combo_prompts")
    last_combo = int(st_combo.get("last_processed_rating_id") or 0)

    if target <= 0:
        upsert_state(
            state_db_path,
            aggregator_name="combo_prompts",
            last_processed_rating_id=last_combo,
            last_run_at=utc_now_str(),
            last_error=None,
        )
        return last_combo

    if prompt_last < target or images_last < target:
        upsert_state(
            state_db_path,
            aggregator_name="combo_prompts",
            last_processed_rating_id=last_combo,
            last_run_at=utc_now_str(),
            last_error=None,
        )
        return last_combo

    if last_combo >= target:
        upsert_state(
            state_db_path,
            aggregator_name="combo_prompts",
            last_processed_rating_id=last_combo,
            last_run_at=utc_now_str(),
            last_error=None,
        )
        return last_combo

    upsert_state(
        state_db_path,
        aggregator_name="combo_prompts",
        last_processed_rating_id=last_combo,
        last_run_at=utc_now_str(),
        last_error=None,
    )

    try:
        rebuild_combo_prompts(
            combo_db_path=combo_db_path,
            playground_db_path=playground_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            images_db_path=images_db_path,
        )
    except Exception as e:
        upsert_state(
            state_db_path,
            aggregator_name="combo_prompts",
            last_processed_rating_id=last_combo,
            last_run_at=utc_now_str(),
            last_error=str(e),
        )
        return last_combo

    upsert_state(
        state_db_path,
        aggregator_name="combo_prompts",
        last_processed_rating_id=target,
        last_run_at=utc_now_str(),
        last_error=None,
    )
    return target
