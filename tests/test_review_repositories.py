"""Integration tests for SQLite review persistence adapters."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    OutputPair,
    PromptProjection,
    ReviewImage,
    ReviewRecord,
)
from comfyreview.repositories.sqlite import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)
from tests.schema_helpers import initialize_legacy_database


def _review_record(json_path: Path, rating: int) -> ReviewRecord:
    return ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=json_path.with_suffix(".png"),
                json_path=json_path,
            ),
            model_branch="sdxl",
            checkpoint="model.safetensors",
            combo_key="combo",
            steps=24,
            cfg=6.5,
            sampler="euler",
            scheduler="normal",
            denoise=0.8,
            loras_json='[{"name":"style"}]',
            positive_prompt="hero, blue sky",
            negative_prompt="blur",
        ),
        rating=rating,
        deleted=False,
    )


def test_review_repository_assigns_exact_runs_and_compensates(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "ratings.sqlite3"
    initialize_legacy_database("ratings", database_path)
    repository = SqliteReviewRepository(database_path)
    record = _review_record(tmp_path / "image.json", 8)

    first = repository.append(record)
    second = repository.append(record)

    assert (first.run, second.run) == (1, 2)
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT id, run, rating_count, rating, model_branch, checkpoint,
                   combo_key, steps, cfg, sampler, scheduler, denoise,
                   loras_json, pos_prompt, neg_prompt
            FROM ratings
            WHERE id = ?
            """,
            (second.review_id,),
        ).fetchone()
    assert row == (
        second.review_id,
        2,
        2,
        8,
        "sdxl",
        "model.safetensors",
        "combo",
        24,
        6.5,
        "euler",
        "normal",
        0.8,
        '[{"name":"style"}]',
        "hero, blue sky",
        "blur",
    )

    repository.delete(second.review_id)

    with sqlite3.connect(database_path) as connection:
        remaining_ids = connection.execute(
            "SELECT id FROM ratings ORDER BY id"
        ).fetchall()
    assert remaining_ids == [(first.review_id,)]


def test_prompt_repository_writes_and_deletes_exact_run(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "prompt_tokens.sqlite3"
    initialize_legacy_database("prompt_tokens", database_path)
    repository = SqlitePromptRepository(database_path)
    projection = PromptProjection(
        json_path=tmp_path / "image.json",
        run=4,
        model_branch="sdxl",
        positive_prompt="hero, blue sky\n",
        negative_prompt="blur",
        rating=9,
        deleted=False,
    )

    repository.save(projection)
    repository.save(projection)

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            """
            SELECT run, model_branch, scope, token, rating, deleted
            FROM tokens
            ORDER BY id
            """
        ).fetchall()
    assert rows == [
        (4, "sdxl", "pos", "hero", 9, 0),
        (4, "sdxl", "pos", "blue sky", 9, 0),
        (4, "sdxl", "neg", "blur", 9, 0),
    ]

    repository.delete(projection.json_path, projection.run)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM tokens"
        ).fetchone() == (0,)


def test_projection_queue_coalesces_catchup_requests(tmp_path: Path) -> None:
    database_path = tmp_path / "mv_jobs.sqlite3"
    initialize_legacy_database("mv_queue", database_path)
    queue = LegacyProjectionJobQueue(database_path)

    assert queue.request_catchup() == queue.request_catchup()

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM mv_jobs"
        ).fetchone() == (1,)


@pytest.mark.parametrize(
    "adapter_factory",
    [
        SqliteReviewRepository,
        SqlitePromptRepository,
        LegacyProjectionJobQueue,
    ],
)
def test_review_adapters_do_not_create_missing_databases(
    tmp_path: Path,
    adapter_factory: (
        type[SqliteReviewRepository]
        | type[SqlitePromptRepository]
        | type[LegacyProjectionJobQueue]
    ),
) -> None:
    database_path = tmp_path / "missing.sqlite3"
    adapter = adapter_factory(database_path)

    with pytest.raises(FileNotFoundError):
        if isinstance(adapter, SqliteReviewRepository):
            adapter.append(_review_record(tmp_path / "image.json", 8))
        elif isinstance(adapter, SqlitePromptRepository):
            adapter.delete(tmp_path / "image.json", 1)
        else:
            adapter.request_catchup()

    assert not database_path.exists()
