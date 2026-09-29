from __future__ import annotations

import threading
import time
from pathlib import Path
from typing import Any

from services.mv_worker_core.combo_pipeline import process_combo_prompts_once
from services.mv_worker_core.debounce import debounce_wait_for_catchup_job
from services.mv_worker_core.images_pipeline import process_images_incremental
from services.mv_worker_core.prompt_ratings_pipeline import (
    process_prompt_ratings_incremental,
)
from services.mv_worker_core.ratings_io import max_queued_job_id, max_rating_id
from services.mv_worker_core.time_utils import utc_now_str
from stores.mv_jobs_store import (
    enqueue_job,
    fetch_job,
    fetch_next_queued,
    mark_all_queued_done,
    mark_done,
    mark_failed,
    mark_running,
    recover_abandoned_running_jobs,
)
from stores.mv_jobs_store import (
    ensure_schema as ensure_jobs_schema,
)
from stores.mv_state_store import (
    ensure_schema as ensure_state_schema,
)
from stores.mv_state_store import (
    get_state,
    upsert_state,
)


def ensure_initial_catchup_job(
    *,
    queue_db_path: Path,
    state_db_path: Path,
    ratings_db_path: Path,
    aggregators: tuple[str, ...],
) -> None:
    try:
        current_max = max_rating_id(ratings_db_path)
    except Exception:
        return
    if current_max <= 0:
        return

    behind = False
    for a in aggregators:
        st = get_state(state_db_path, aggregator_name=a)
        if int(st.get("last_processed_rating_id") or 0) < int(current_max):
            behind = True
            break
    if behind:
        enqueue_job(queue_db_path, job_type="catchup")


def initialize_worker_state(
    *,
    queue_db_path: Path,
    state_db_path: Path,
    ratings_db_path: Path,
    aggregators: tuple[str, ...],
) -> int:
    """Prepare schemas, recover abandoned work, and enqueue one catchup."""
    ensure_jobs_schema(queue_db_path)
    ensure_state_schema(state_db_path)
    recovered = recover_abandoned_running_jobs(queue_db_path)
    ensure_initial_catchup_job(
        queue_db_path=queue_db_path,
        state_db_path=state_db_path,
        ratings_db_path=ratings_db_path,
        aggregators=aggregators,
    )
    return recovered


def drain_until_frontier_stable(
    *,
    state_db_path: Path,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    images_db_path: Path,
    max_loops: int = 25,
) -> int:
    """Catch up prompt_ratings and images until ratings frontier is stable."""
    last_frontier = -1
    for _ in range(int(max_loops)):
        frontier = max_rating_id(ratings_db_path)
        if frontier <= 0:
            return 0

        process_prompt_ratings_incremental(
            state_db_path=state_db_path,
            ratings_db_path=ratings_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            up_to_rating_id=frontier,
        )
        process_images_incremental(
            state_db_path=state_db_path,
            ratings_db_path=ratings_db_path,
            images_db_path=images_db_path,
            up_to_rating_id=frontier,
        )

        new_frontier = max_rating_id(ratings_db_path)
        if new_frontier == frontier:
            return frontier
        last_frontier = new_frontier

    return max(last_frontier, 0)


def should_stop(stop_event: threading.Event | None) -> bool:
    return bool(stop_event is not None and stop_event.is_set())


def wait_for_next_queued_job(
    *,
    queue_db_path: Path,
    poll_seconds: float,
    stop_event: threading.Event | None,
) -> dict[str, Any] | None:
    """Block until we have a usable queued job or the worker should stop."""
    while True:
        if should_stop(stop_event):
            return None

        job = fetch_next_queued(queue_db_path)
        job_id = int((job or {}).get("id") or 0)
        if job and job_id > 0:
            return job

        time.sleep(float(poll_seconds))


def process_one_job(
    *,
    job: dict[str, Any],
    queue_db_path: Path,
    state_db_path: Path,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    combo_db_path: Path,
    playground_db_path: Path,
    images_db_path: Path,
    poll_seconds: float,
    debounce_seconds: int,
    stop_event: threading.Event | None,
) -> None:
    """Run exactly one queued job (currently only 'catchup' is used)."""
    job_id = int(job.get("id") or 0)
    job_type = str(job.get("job_type") or "catchup")

    if job_type == "catchup":
        debounce_wait_for_catchup_job(
            queue_db_path=queue_db_path,
            job_id=job_id,
            debounce_seconds=int(debounce_seconds),
            poll_seconds=float(poll_seconds),
            stop_event=stop_event,
        )

    job_after = fetch_job(queue_db_path, job_id=job_id)
    if not job_after or str(job_after.get("status")) != "queued":
        time.sleep(float(poll_seconds))
        return

    queued_snapshot_max_id = max_queued_job_id(queue_db_path)

    mark_running(queue_db_path, job_id)

    try:
        stable_frontier = drain_until_frontier_stable(
            state_db_path=state_db_path,
            ratings_db_path=ratings_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            images_db_path=images_db_path,
        )

        process_combo_prompts_once(
            state_db_path=state_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            combo_db_path=combo_db_path,
            playground_db_path=playground_db_path,
            images_db_path=images_db_path,
            target_rating_id=stable_frontier,
        )

        mark_done(queue_db_path, job_id)

        if queued_snapshot_max_id > 0:
            mark_all_queued_done(
                queue_db_path, up_to_job_id=queued_snapshot_max_id
            )

    except Exception as e:
        mark_failed(queue_db_path, job_id, str(e))
        for a in ("prompt_ratings", "combo_prompts", "images"):
            st = get_state(state_db_path, aggregator_name=a)
            upsert_state(
                state_db_path,
                aggregator_name=a,
                last_processed_rating_id=int(
                    st.get("last_processed_rating_id") or 0
                ),
                last_run_at=utc_now_str(),
                last_error=str(e),
            )
        time.sleep(float(poll_seconds))


def run_worker_loop(
    *,
    queue_db_path: Path,
    state_db_path: Path,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    combo_db_path: Path,
    playground_db_path: Path,
    images_db_path: Path,
    debounce_seconds: int,
    poll_seconds: float = 0.75,
    stop_event: threading.Event | None = None,
) -> None:
    aggregators: tuple[str, ...] = (
        "prompt_ratings",
        "combo_prompts",
        "images",
    )

    initialize_worker_state(
        queue_db_path=queue_db_path,
        state_db_path=state_db_path,
        ratings_db_path=ratings_db_path,
        aggregators=aggregators,
    )

    while True:
        if should_stop(stop_event):
            return

        job = wait_for_next_queued_job(
            queue_db_path=queue_db_path,
            poll_seconds=float(poll_seconds),
            stop_event=stop_event,
        )
        if not job:
            return

        process_one_job(
            job=job,
            queue_db_path=queue_db_path,
            state_db_path=state_db_path,
            ratings_db_path=ratings_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            combo_db_path=combo_db_path,
            playground_db_path=playground_db_path,
            images_db_path=images_db_path,
            poll_seconds=float(poll_seconds),
            debounce_seconds=int(debounce_seconds),
            stop_event=stop_event,
        )
