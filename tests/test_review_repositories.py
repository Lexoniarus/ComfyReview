"""Integration tests for canonical SQLite review persistence adapters."""

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
    CanonicalSchemaManager,
    CanonicalSchemaValidationError,
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)
from tests.schema_helpers import initialize_legacy_database


def _review_record(
    json_path: Path,
    rating: int | None,
    *,
    deleted: bool = False,
) -> ReviewRecord:
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
            positive_prompt="(hero:1.25), blue sky",
            negative_prompt="blur",
        ),
        rating=rating,
        deleted=deleted,
    )


def test_canonical_schema_initializes_once_and_exposes_compatibility_views(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    manager = CanonicalSchemaManager(database_path)

    first = manager.prepare_startup()
    second = manager.prepare_startup()

    assert first.initialized is True
    assert first.schema_version == 3
    assert second.initialized is False
    with sqlite3.connect(database_path) as connection:
        objects = dict(
            connection.execute(
                "SELECT name, type FROM sqlite_master "
                "WHERE name IN ('ratings', 'tokens')"
            ).fetchall()
        )
    assert objects == {"ratings": "view", "tokens": "view"}


def test_canonical_schema_rejects_unknown_existing_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    with sqlite3.connect(database_path) as connection:
        connection.execute("CREATE TABLE unrelated(id INTEGER PRIMARY KEY)")

    with pytest.raises(CanonicalSchemaValidationError):
        CanonicalSchemaManager(database_path).prepare_startup()


def test_review_repository_replaces_rating_without_token_journal_growth(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteReviewRepository(database_path)
    record = _review_record(tmp_path / "image.json", 7)

    first = repository.append(record)
    second = repository.append(_review_record(tmp_path / "image.json", 9))

    assert second.run > first.run
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM image_reviews"
            ).fetchone()[0]
            == 1
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM prompt_atoms").fetchone()[
                0
            ]
            == 3
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM prompt_memberships"
            ).fetchone()[0]
            == 3
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM tokens").fetchone()[0]
            == 3
        )
        review = connection.execute(
            "SELECT rating, version FROM image_reviews"
        ).fetchone()
        assert (review["rating"], review["version"]) == (9, second.run)
        hero = connection.execute(
            """
            SELECT atom.canonical_text, stats.weight_milli,
                   stats.sample_count, stats.rating_sum
            FROM atom_learning_stats AS stats
            JOIN prompt_atoms AS atom ON atom.id = stats.atom_id
            WHERE atom.canonical_text = 'hero'
            """
        ).fetchone()
    assert tuple(hero) == ("hero", 1250, 1, 9.0)


def test_delete_removes_live_link_and_keeps_one_negative_observation(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteReviewRepository(database_path)
    repository.append(_review_record(tmp_path / "image.json", 8))

    deleted = repository.append(
        _review_record(tmp_path / "image.json", None, deleted=True)
    )

    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        assert (
            connection.execute("SELECT COUNT(*) FROM images").fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM image_reviews"
            ).fetchone()[0]
            == 0
        )
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM deleted_images"
            ).fetchone()[0]
            == 1
        )
        compatibility = connection.execute(
            "SELECT rating, deleted, run FROM ratings"
        ).fetchone()
        stats = connection.execute(
            """
            SELECT DISTINCT sample_count, rating_sum, deleted_count
            FROM atom_learning_stats
            """
        ).fetchall()
    assert tuple(compatibility) == (None, 1, deleted.run)
    assert [tuple(row) for row in stats] == [(1, 0.0, 1)]


def test_reappearing_generation_replaces_delete_evidence(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteReviewRepository(database_path)
    path = tmp_path / "image.json"
    repository.append(_review_record(path, 8))
    repository.append(_review_record(path, None, deleted=True))

    repository.append(_review_record(path, 9))

    with sqlite3.connect(database_path) as connection:
        stats = connection.execute(
            """
            SELECT DISTINCT sample_count, rating_sum, deleted_count
            FROM atom_learning_stats
            """
        ).fetchall()
        assert connection.execute(
            "SELECT COUNT(*) FROM deleted_images"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT rating FROM image_reviews"
        ).fetchone() == (9,)
    assert stats == [(1, 9.0, 0)]


def test_review_repository_delete_reverses_current_rating_contribution(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteReviewRepository(database_path)
    stored = repository.append(_review_record(tmp_path / "image.json", 6))

    repository.delete(stored.review_id)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM image_reviews"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM atom_learning_stats"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM render_learning_stats"
        ).fetchone() == (0,)


def test_prompt_repository_is_compatibility_noop(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqlitePromptRepository(database_path)
    projection = PromptProjection(
        json_path=tmp_path / "image.json",
        run=4,
        model_branch="sdxl",
        positive_prompt="hero",
        negative_prompt="blur",
        rating=9,
        deleted=False,
    )

    repository.save(projection)
    repository.delete(projection.json_path, projection.run)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_atoms"
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
    [SqliteReviewRepository, SqlitePromptRepository],
)
def test_review_adapters_do_not_create_missing_database(
    tmp_path: Path,
    adapter_factory: (
        type[SqliteReviewRepository] | type[SqlitePromptRepository]
    ),
) -> None:
    database_path = tmp_path / "missing.sqlite3"
    adapter = adapter_factory(database_path)

    with pytest.raises(FileNotFoundError):
        if isinstance(adapter, SqliteReviewRepository):
            adapter.append(_review_record(tmp_path / "image.json", 8))
        else:
            adapter.delete(tmp_path / "image.json", 1)

    assert not database_path.exists()
