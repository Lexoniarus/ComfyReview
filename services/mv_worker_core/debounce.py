from __future__ import annotations

import time
import threading
from pathlib import Path
from typing import Optional

from stores.mv_jobs_store import fetch_job

from services.mv_worker_core.time_utils import parse_utc_ts_to_epoch


def debounce_wait_for_catchup_job(
    *,
    queue_db_path: Path,
    job_id: int,
    debounce_seconds: int,
    poll_seconds: float,
    stop_event: Optional[threading.Event],
) -> None:
    """Debounce: wait for a quiet window before starting heavy work.

    Rule
    - A queued catchup job has a touched_at timestamp.
    - Each new rating "touches" the same queued job (see enqueue_job).
    - The worker starts only after (now - touched_at) >= debounce_seconds.
    """
    debounce_seconds = int(debounce_seconds or 0)
    if debounce_seconds <= 0:
        return

    while True:
        if stop_event is not None and stop_event.is_set():
            return

        job = fetch_job(queue_db_path, job_id=int(job_id))
        if not job:
            return
        if str(job.get("status")) != "queued":
            return

        touched = str(job.get("touched_at") or job.get("created_at") or "")
        touched_epoch = parse_utc_ts_to_epoch(touched)
        if touched_epoch is None:
            return

        age = time.time() - float(touched_epoch)
        remaining = float(debounce_seconds) - float(age)
        if remaining <= 0:
            return

        sleep_s = min(float(poll_seconds), max(0.2, remaining))
        time.sleep(sleep_s)
