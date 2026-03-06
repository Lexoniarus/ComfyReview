from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from stores.mv_state_store import get_state, upsert_state

from services.prompt_tokens_service import write_prompt_tokens_for_run
from services.prompt_ratings_service import update_prompt_ratings_for_runs

from services.mv_worker_core.time_utils import utc_now_str
from services.mv_worker_core.ratings_io import fetch_ratings_rows


def runs_with_tokens(
    prompt_tokens_db_path: Path,
    keys: List[tuple[str, int]],
    *,
    chunk_size: int = 200,
) -> Set[tuple[str, int]]:
    """Return set of (json_path, run) that already exist in tokens."""
    if not keys:
        return set()

    unique = list(
        dict.fromkeys([(str(jp), int(rn)) for jp, rn in keys if str(jp) and int(rn) > 0])
    )
    if not unique:
        return set()

    con = sqlite3.connect(prompt_tokens_db_path)
    con.row_factory = sqlite3.Row
    try:
        present: Set[tuple[str, int]] = set()
        for i in range(0, len(unique), chunk_size):
            chunk = unique[i : i + chunk_size]
            where = " OR ".join(["(json_path = ? AND run = ?)"] * len(chunk))
            args: List[Any] = []
            for jp, rn in chunk:
                args.extend([jp, rn])

            rows = con.execute(
                f"""
                SELECT json_path, run, COUNT(1) AS c
                FROM tokens
                WHERE {where}
                GROUP BY json_path, run
                """,
                args,
            ).fetchall()

            for r in rows:
                if int(r["c"] or 0) > 0:
                    present.add((str(r["json_path"]), int(r["run"] or 0)))

        return present
    finally:
        con.close()


def process_prompt_ratings_incremental(
    *,
    state_db_path: Path,
    ratings_db_path: Path,
    prompt_tokens_db_path: Path,
    prompt_ratings_db_path: Path,
    up_to_rating_id: int,
) -> int:
    """Catch up prompt_ratings from ratings incrementally up to a rating id."""
    st = get_state(state_db_path, aggregator_name="prompt_ratings")
    last = int(st.get("last_processed_rating_id") or 0)

    if last >= int(up_to_rating_id):
        upsert_state(
            state_db_path,
            aggregator_name="prompt_ratings",
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
    if not rows:
        upsert_state(
            state_db_path,
            aggregator_name="prompt_ratings",
            last_processed_rating_id=last,
            last_run_at=utc_now_str(),
            last_error=None,
        )
        return last

    keys: List[tuple[str, int]] = []
    for r in rows:
        jp = str(r.get("json_path") or "").strip()
        rn = int(r.get("run") or 0)
        if jp and rn > 0:
            keys.append((jp, rn))

    present = runs_with_tokens(prompt_tokens_db_path, keys)

    process_rows: List[Dict[str, Any]] = []
    missing_msg: Optional[str] = None

    for r in rows:
        rid = int(r.get("id") or 0)
        jp = str(r.get("json_path") or "").strip()
        rn = int(r.get("run") or 0)

        if not jp or rn <= 0:
            missing_msg = f"missing json_path/run for rating_id={rid} json_path={jp} run={rn}"
            break

        if (jp, rn) not in present:
            try:
                write_prompt_tokens_for_run(
                    prompt_tokens_db_path=prompt_tokens_db_path,
                    json_path=jp,
                    run=rn,
                    model_branch=str(r.get("model_branch") or ""),
                    pos_prompt=str(r.get("pos_prompt") or ""),
                    neg_prompt=str(r.get("neg_prompt") or ""),
                    rating=(int(r.get("rating")) if r.get("rating") is not None else None),
                    deleted=int(r.get("deleted") or 0),
                )
            except Exception as e:
                missing_msg = (
                    f"missing prompt_tokens for rating_id={rid} json_path={jp} run={rn} "
                    f"(heal failed: {e})"
                )
                break

            present = runs_with_tokens(prompt_tokens_db_path, [(jp, rn)]) | present
            if (jp, rn) not in present:
                missing_msg = (
                    f"missing prompt_tokens for rating_id={rid} json_path={jp} run={rn} "
                    f"(heal incomplete)"
                )
                break

        process_rows.append(r)

    if not process_rows:
        upsert_state(
            state_db_path,
            aggregator_name="prompt_ratings",
            last_processed_rating_id=last,
            last_run_at=utc_now_str(),
            last_error=missing_msg,
        )
        return last

    processed_id = int(process_rows[-1].get("id") or last)

    runs: List[Dict[str, Any]] = []
    seen: Set[tuple[str, int, str]] = set()
    for r in process_rows:
        jp = str(r.get("json_path") or "").strip()
        rn = int(r.get("run") or 0)
        mb = str(r.get("model_branch") or "").strip()
        key = (jp, rn, mb)
        if not jp or rn <= 0 or key in seen:
            continue
        seen.add(key)
        runs.append({"json_path": jp, "run": rn, "model_branch": mb})

    update_prompt_ratings_for_runs(
        prompt_tokens_db_path=prompt_tokens_db_path,
        prompt_ratings_db_path=prompt_ratings_db_path,
        runs=runs,
    )

    upsert_state(
        state_db_path,
        aggregator_name="prompt_ratings",
        last_processed_rating_id=processed_id,
        last_run_at=utc_now_str(),
        last_error=missing_msg,
    )
    return processed_id
