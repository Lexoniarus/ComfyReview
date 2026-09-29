import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    OutputPair,
    ReviewImage,
    ReviewRecord,
)
from comfyreview.repositories.sqlite import SqliteReviewRepository
from models import RatedItem
from services import arena_service, rating_submission_service
from services.curation_assignment_service import (
    CurationMutationError,
    CurationValidationError,
    assign_image_to_set,
)
from services.mv_worker_core import combo_pipeline, engine
from stores.images_store import upsert_image
from stores.mv_jobs_store import (
    enqueue_job,
    fetch_job,
    mark_running,
)
from stores.mv_state_store import get_state
from tests.schema_helpers import initialize_legacy_database


def _image_row(png_path: Path, json_path: Path, rating: float) -> dict:
    return {
        "png_path": str(png_path),
        "json_path": str(json_path),
        "avg_rating": rating,
        "runs": 1,
        "rating_count": 1,
        "last_run": 1,
        "model_branch": "model",
        "checkpoint": "checkpoint",
        "combo_key": "combo",
        "steps": 20,
        "cfg": 7.0,
        "sampler": "sampler",
        "scheduler": "scheduler",
        "denoise": 1.0,
        "loras_json": "[]",
        "pos_prompt": "positive",
        "neg_prompt": "negative",
        "last_updated": "2026-09-28 00:00:00",
    }


def test_delete_writes_tombstone_and_removes_pair(tmp_path, monkeypatch):
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    ratings_path = tmp_path / "ratings.sqlite3"
    prompt_tokens_path = tmp_path / "prompt_tokens.sqlite3"
    queue_path = tmp_path / "mv_jobs.sqlite3"
    initialize_legacy_database("ratings", ratings_path)
    initialize_legacy_database("prompt_tokens", prompt_tokens_path)
    initialize_legacy_database("mv_queue", queue_path)

    monkeypatch.setattr(
        rating_submission_service,
        "_read_meta_for_rating",
        lambda _path: ({}, "positive", "negative"),
    )

    rating_submission_service.submit_rating(
        ratings_db_path=ratings_path,
        prompt_tokens_db_path=prompt_tokens_path,
        mv_queue_db_path=queue_path,
        output_root=tmp_path,
        trash_root=tmp_path / "_trash",
        soft_delete_to_trash=False,
        rating=None,
        deleted=1,
        delete=1,
        combo_key="combo",
        model_branch="model",
        checkpoint="checkpoint",
        json_path=str(json_path),
        png_path=str(png_path),
        sampler=None,
        scheduler=None,
        steps=None,
        cfg=None,
        denoise=None,
        loras_json=None,
    )

    assert not png_path.exists()
    assert not json_path.exists()
    with sqlite3.connect(ratings_path) as connection:
        assert connection.execute(
            "SELECT deleted, rating FROM ratings ORDER BY id DESC LIMIT 1"
        ).fetchone() == (1, None)


def test_review_rejects_score_outside_supported_range(tmp_path):
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")

    with pytest.raises(rating_submission_service.ReviewValidationError):
        rating_submission_service.submit_rating(
            ratings_db_path=tmp_path / "ratings.sqlite3",
            prompt_tokens_db_path=tmp_path / "prompt_tokens.sqlite3",
            mv_queue_db_path=tmp_path / "mv_jobs.sqlite3",
            output_root=tmp_path,
            trash_root=tmp_path / "_trash",
            soft_delete_to_trash=True,
            rating=11,
            deleted=None,
            delete=None,
            combo_key="combo",
            model_branch="model",
            checkpoint="checkpoint",
            json_path=str(json_path),
            png_path=str(png_path),
            sampler=None,
            scheduler=None,
            steps=None,
            cfg=None,
            denoise=None,
            loras_json=None,
        )

    assert not (tmp_path / "ratings.sqlite3").exists()


def test_curation_rejects_unknown_set_before_moving_files(tmp_path):
    output_root = tmp_path / "output"
    output_root.mkdir()
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")

    with pytest.raises(CurationValidationError, match="Unknown curation set"):
        assign_image_to_set(
            curation_db_path=tmp_path / "curation.sqlite3",
            output_root=output_root,
            lora_export_root=tmp_path / "export",
            allowed_set_keys=("scene",),
            png_path=str(png_path),
            json_path=str(json_path),
            set_key="unknown",
        )

    assert png_path.is_file()
    assert json_path.is_file()


def test_curation_moves_pair_and_relinks_paths(tmp_path, monkeypatch):
    output_root = tmp_path / "output"
    source_dir = output_root / "playground" / "Aiko"
    source_dir.mkdir(parents=True)
    png_path = source_dir / "image.png"
    json_path = source_dir / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    relink_calls = []
    curation_path = tmp_path / "curation.sqlite3"
    initialize_legacy_database("curation", curation_path)

    monkeypatch.setattr(
        "services.curation_assignment_service.relink_paths_after_move",
        lambda **kwargs: relink_calls.append(kwargs),
    )

    assign_image_to_set(
        curation_db_path=curation_path,
        output_root=output_root,
        lora_export_root=tmp_path / "export",
        allowed_set_keys=("scene",),
        png_path=str(png_path),
        json_path=str(json_path),
        set_key="scene",
    )

    moved_png = source_dir / "scene" / "image.png"
    moved_json = source_dir / "scene" / "image.json"
    assert moved_png.is_file()
    assert moved_json.is_file()
    assert len(relink_calls) == 1
    assert relink_calls[0]["new_png_path"] == str(moved_png)


def test_arena_result_records_match_and_two_ratings(tmp_path, monkeypatch):
    images_path = tmp_path / "images.sqlite3"
    arena_path = tmp_path / "arena.sqlite3"
    ratings_path = tmp_path / "ratings.sqlite3"
    prompt_tokens_path = tmp_path / "prompt_tokens.sqlite3"
    queue_path = tmp_path / "mv_jobs.sqlite3"
    left_png = tmp_path / "left.png"
    left_json = tmp_path / "left.json"
    right_png = tmp_path / "right.png"
    right_json = tmp_path / "right.json"
    for path in (left_png, right_png):
        path.write_bytes(b"png")
    for path in (left_json, right_json):
        path.write_text("{}", encoding="utf-8")

    initialize_legacy_database("images", images_path)
    initialize_legacy_database("arena", arena_path)
    initialize_legacy_database("ratings", ratings_path)
    initialize_legacy_database("prompt_tokens", prompt_tokens_path)
    initialize_legacy_database("mv_queue", queue_path)
    upsert_image(images_path, _image_row(left_png, left_json, 8.0))
    upsert_image(images_path, _image_row(right_png, right_json, 4.0))
    monkeypatch.setattr(arena_service, "IMAGES_DB_PATH", images_path)
    monkeypatch.setattr(arena_service, "ARENA_DB_PATH", arena_path)
    monkeypatch.setattr(arena_service, "DB_PATH", ratings_path)
    monkeypatch.setattr(
        arena_service, "PROMPT_TOKENS_DB_PATH", prompt_tokens_path
    )
    monkeypatch.setattr(arena_service, "MV_QUEUE_DB_PATH", queue_path)

    left = RatedItem(
        left_png, left_json, "", "model", "checkpoint", "combo", {}
    )
    right = RatedItem(
        right_png, right_json, "", "model", "checkpoint", "combo", {}
    )

    arena_service.insert_arena_result(
        left,
        right,
        str(left_json),
        str(right_json),
        "left",
    )

    with sqlite3.connect(arena_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM arena_matches"
            ).fetchone()[0]
            == 1
        )
    with sqlite3.connect(ratings_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
            == 2
        )


def test_arena_rejects_unknown_winner_side(tmp_path, monkeypatch):
    left_json = tmp_path / "left.json"
    right_json = tmp_path / "right.json"
    left = RatedItem(tmp_path / "left.png", left_json, "", "", "", "", {})
    right = RatedItem(tmp_path / "right.png", right_json, "", "", "", "", {})

    with pytest.raises(
        arena_service.ArenaValidationError, match="winner_side"
    ):
        arena_service.insert_arena_result(
            left,
            right,
            str(left_json),
            str(right_json),
            "invalid",
        )


def test_arena_compensates_match_and_first_rating_on_failure(
    tmp_path, monkeypatch
):
    images_path = tmp_path / "images.sqlite3"
    arena_path = tmp_path / "arena.sqlite3"
    ratings_path = tmp_path / "ratings.sqlite3"
    prompt_tokens_path = tmp_path / "prompt_tokens.sqlite3"
    left_png = tmp_path / "left.png"
    left_json = tmp_path / "left.json"
    right_png = tmp_path / "right.png"
    right_json = tmp_path / "right.json"
    initialize_legacy_database("images", images_path)
    initialize_legacy_database("arena", arena_path)
    initialize_legacy_database("ratings", ratings_path)
    initialize_legacy_database("prompt_tokens", prompt_tokens_path)
    upsert_image(images_path, _image_row(left_png, left_json, 8.0))
    upsert_image(images_path, _image_row(right_png, right_json, 4.0))
    monkeypatch.setattr(arena_service, "IMAGES_DB_PATH", images_path)
    monkeypatch.setattr(arena_service, "ARENA_DB_PATH", arena_path)
    monkeypatch.setattr(arena_service, "DB_PATH", ratings_path)
    monkeypatch.setattr(
        arena_service, "PROMPT_TOKENS_DB_PATH", prompt_tokens_path
    )
    real_append = SqliteReviewRepository.append
    calls = 0

    def fail_second_rating(repository, record):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("second rating failed")
        return real_append(repository, record)

    monkeypatch.setattr(SqliteReviewRepository, "append", fail_second_rating)
    left = RatedItem(
        left_png, left_json, "", "model", "checkpoint", "combo", {}
    )
    right = RatedItem(
        right_png, right_json, "", "model", "checkpoint", "combo", {}
    )

    with pytest.raises(arena_service.ArenaMutationError):
        arena_service.insert_arena_result(
            left,
            right,
            str(left_json),
            str(right_json),
            "left",
        )

    with sqlite3.connect(arena_path) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM arena_matches"
            ).fetchone()[0]
            == 0
        )
    with sqlite3.connect(ratings_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM ratings").fetchone()[0]
            == 0
        )


def test_curation_restores_files_when_relink_fails(tmp_path, monkeypatch):
    output_root = tmp_path / "output"
    source_dir = output_root / "playground" / "Aiko"
    source_dir.mkdir(parents=True)
    png_path = source_dir / "image.png"
    json_path = source_dir / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    calls = 0
    curation_path = tmp_path / "curation.sqlite3"
    initialize_legacy_database("curation", curation_path)

    def fail_first_relink(**_kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("relink failed")

    monkeypatch.setattr(
        "services.curation_assignment_service.relink_paths_after_move",
        fail_first_relink,
    )

    with pytest.raises(CurationMutationError, match="Could not assign"):
        assign_image_to_set(
            curation_db_path=curation_path,
            output_root=output_root,
            lora_export_root=tmp_path / "export",
            allowed_set_keys=("scene",),
            png_path=str(png_path),
            json_path=str(json_path),
            set_key="scene",
        )

    assert png_path.is_file()
    assert json_path.is_file()
    assert not (source_dir / "scene" / "image.png").exists()


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
    SqliteReviewRepository(ratings_path).append(
        ReviewRecord(
            image=ReviewImage(
                pair=OutputPair(
                    png_path=Path("image.png"),
                    json_path=Path("image.json"),
                ),
                model_branch="model",
                checkpoint="checkpoint",
                combo_key="combo",
                steps=20,
                cfg=7.0,
                sampler="sampler",
                scheduler="scheduler",
                denoise=1.0,
                loras_json="[]",
                positive_prompt="positive",
                negative_prompt="negative",
            ),
            rating=8,
            deleted=False,
        )
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
