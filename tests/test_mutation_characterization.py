"""Regression tests for the transitional projection worker runtime."""

from __future__ import annotations

import sqlite3

import pytest

from services.mv_worker_core import combo_pipeline, engine
from stores.mv_jobs_store import enqueue_job, fetch_job, mark_running
from stores.mv_state_store import get_state
from tests.schema_helpers import initialize_legacy_database


def test_combo_rebuild_failure_is_stored_and_raised(tmp_path, monkeypatch):
    state_path = tmp_path / "mv.sqlite3"
    initialize_legacy_database("mv_queue", state_path)
    get_state(state_path, aggregator_name="prompt_ratings")
    get_state(state_path, aggregator_name="images")
    get_state(state_path, aggregator_name="combo_prompts")
    from stores.mv_state_store import upsert_state

    for name in ("prompt_ratings", "images"):
        upsert_state(
            state_path,
            aggregator_name=name,
            last_processed_rating_id=5,
        )

    monkeypatch.setattr(
        combo_pipeline,
        "rebuild_combo_prompts",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("locked")),
    )

    with pytest.raises(combo_pipeline.ComboProjectionError):
        combo_pipeline.process_combo_prompts_once(
            state_db_path=state_path,
            prompt_ratings_db_path=tmp_path / "prompt_ratings.sqlite3",
            combo_db_path=tmp_path / "combo.sqlite3",
            playground_db_path=tmp_path / "playground.sqlite3",
            images_db_path=tmp_path / "images.sqlite3",
            target_rating_id=5,
        )

    state = get_state(state_path, aggregator_name="combo_prompts")
    assert state["last_error"] == "locked"


def test_worker_startup_recovers_abandoned_jobs_and_queues_one_catchup(
    tmp_path,
):
    queue_path = tmp_path / "mv_jobs.sqlite3"
    ratings_path = tmp_path / "ratings.sqlite3"
    initialize_legacy_database("mv_queue", queue_path)
    initialize_legacy_database("ratings", ratings_path)
    first_job = enqueue_job(queue_path, job_type="catchup")
    mark_running(queue_path, first_job)
    second_job = enqueue_job(queue_path, job_type="catchup")
    mark_running(queue_path, second_job)
    with sqlite3.connect(ratings_path) as connection:
        connection.execute(
            """
            INSERT INTO ratings(
                png_path, json_path, model_branch, checkpoint, combo_key,
                rating
            )
            VALUES ('image.png', 'image.json', 'model', 'checkpoint',
                    'combo', 8)
            """
        )

    recovered = engine.initialize_worker_state(
        queue_db_path=queue_path,
        state_db_path=queue_path,
        ratings_db_path=ratings_path,
        aggregators=("prompt_ratings", "combo_prompts", "images"),
    )

    assert recovered == 2
    with sqlite3.connect(queue_path) as connection:
        statuses = connection.execute(
            "SELECT status, COUNT(*) FROM mv_jobs GROUP BY status"
        ).fetchall()
    assert sorted(statuses) == [("failed", 2), ("queued", 1)]


def test_worker_marks_job_failed_when_combo_projection_raises(
    tmp_path, monkeypatch
):
    queue_path = tmp_path / "mv_jobs.sqlite3"
    initialize_legacy_database("mv_queue", queue_path)
    job_id = enqueue_job(queue_path, job_type="catchup")
    job = fetch_job(queue_path, job_id=job_id)
    assert job is not None
    monkeypatch.setattr(
        engine, "debounce_wait_for_catchup_job", lambda **_kwargs: None
    )
    monkeypatch.setattr(engine, "max_queued_job_id", lambda _path: job_id)
    monkeypatch.setattr(
        engine, "drain_until_frontier_stable", lambda **_kwargs: 5
    )
    monkeypatch.setattr(
        engine,
        "process_combo_prompts_once",
        lambda **_kwargs: (_ for _ in ()).throw(RuntimeError("combo failed")),
    )
    monkeypatch.setattr(engine.time, "sleep", lambda _seconds: None)

    engine.process_one_job(
        job=job,
        queue_db_path=queue_path,
        state_db_path=queue_path,
        ratings_db_path=tmp_path / "ratings.sqlite3",
        prompt_tokens_db_path=tmp_path / "tokens.sqlite3",
        prompt_ratings_db_path=tmp_path / "prompt_ratings.sqlite3",
        combo_db_path=tmp_path / "combo.sqlite3",
        playground_db_path=tmp_path / "playground.sqlite3",
        images_db_path=tmp_path / "images.sqlite3",
        poll_seconds=0,
        debounce_seconds=0,
        stop_event=None,
    )

    failed = fetch_job(queue_path, job_id=job_id)
    assert failed is not None
    assert failed["status"] == "failed"
    assert failed["error"] == "combo failed"
