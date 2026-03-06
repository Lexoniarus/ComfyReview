from __future__ import annotations

import threading
from pathlib import Path

from services.mv_worker_core.engine import run_worker_loop


def start_worker_thread(
    *,
    queue_db_path: Path,
    state_db_path: Path,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    combo_db_path: Path,
    playground_db_path: Path,
    images_db_path: Path,
) -> threading.Thread:
    """Start the MV worker thread.

    Public entrypoint kept stable to match 0.0.5a behavior.
    """
    t = threading.Thread(
        target=run_worker_loop,
        kwargs=dict(
            queue_db_path=queue_db_path,
            state_db_path=state_db_path,
            ratings_db_path=ratings_db_path,
            prompt_tokens_db_path=prompt_tokens_db_path,
            prompt_ratings_db_path=prompt_ratings_db_path,
            combo_db_path=combo_db_path,
            playground_db_path=playground_db_path,
            images_db_path=images_db_path,
        ),
        daemon=True,
        name="mv_worker",
    )
    t.start()
    return t
