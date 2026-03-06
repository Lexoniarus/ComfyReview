from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Set

from stores.mv_state_store import get_state, upsert_state

from services.images_service import update_image_for_png

from services.mv_worker_core.time_utils import utc_now_str
from services.mv_worker_core.ratings_io import fetch_ratings_rows


def process_images_incremental(
    *,
    state_db_path: Path,
    ratings_db_path: Path,
    images_db_path: Path,
    up_to_rating_id: int,
) -> int:
    st = get_state(state_db_path, aggregator_name="images")
    last = int(st.get("last_processed_rating_id") or 0)

    if last >= int(up_to_rating_id):
        upsert_state(
            state_db_path,
            aggregator_name="images",
            last_processed_rating_id=last,
            last_run_at=utc_now_str(),
            last_error=None,
        )
        return last

    rows = fetch_ratings_rows(
        ratings_db_path,
        start_id_exclusive=last,
        end_id_inclusive=up_to_rating_id,
    )

    seen: Set[str] = set()
    for r in rows:
        pp = str(r.get("png_path") or "").strip()
        if not pp or pp in seen:
            continue
        seen.add(pp)
        update_image_for_png(
            images_db_path=images_db_path,
            ratings_db_path=ratings_db_path,
            png_path=pp,
        )

    upsert_state(
        state_db_path,
        aggregator_name="images",
        last_processed_rating_id=int(up_to_rating_id),
        last_run_at=utc_now_str(),
        last_error=None,
    )
    return int(up_to_rating_id)
