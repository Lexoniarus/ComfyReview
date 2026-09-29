"""Integration tests for canonical and legacy SQLite path relinking."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import OutputPair, ReviewImage, ReviewRecord
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqlitePathRelinker,
    SqliteReviewRepository,
)


def _record(path: Path) -> ReviewRecord:
    return ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=path.with_suffix(".png"),
                json_path=path,
            ),
            model_branch="sdxl",
            checkpoint="model.safetensors",
            combo_key="combo",
            steps=24,
            cfg=6.5,
            sampler="euler",
            scheduler="normal",
            denoise=1.0,
            loras_json="[]",
            positive_prompt="hero",
            negative_prompt="blur",
        ),
        rating=8,
        deleted=False,
    )


def test_canonical_relink_updates_live_paths_behind_views(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    old_json = tmp_path / "old" / "image.json"
    new_json = tmp_path / "new" / "image.json"
    SqliteReviewRepository(database_path).append(_record(old_json))
    relinker = SqlitePathRelinker(
        ratings_database_path=database_path,
        prompt_tokens_database_path=database_path,
        images_database_path=None,
        combo_database_path=None,
        arena_database_path=None,
    )

    relinker.relink(
        old_png_path=str(old_json.with_suffix(".png")),
        old_json_path=str(old_json),
        new_png_path=str(new_json.with_suffix(".png")),
        new_json_path=str(new_json),
    )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT png_path, json_path FROM images"
        ).fetchone() == (
            str(new_json.with_suffix(".png")),
            str(new_json),
        )
        assert connection.execute(
            "SELECT json_path FROM ratings"
        ).fetchone() == (str(new_json),)
        assert connection.execute(
            "SELECT DISTINCT json_path FROM tokens"
        ).fetchone() == (str(new_json),)


def test_legacy_relink_updates_physical_rating_and_token_tables(
    tmp_path: Path,
) -> None:
    ratings_path = tmp_path / "ratings.sqlite3"
    tokens_path = tmp_path / "tokens.sqlite3"
    with sqlite3.connect(ratings_path) as connection:
        connection.execute(
            "CREATE TABLE ratings(png_path TEXT, json_path TEXT)"
        )
        connection.execute(
            "INSERT INTO ratings VALUES ('old.png', 'old.json')"
        )
    with sqlite3.connect(tokens_path) as connection:
        connection.execute("CREATE TABLE tokens(json_path TEXT)")
        connection.execute("INSERT INTO tokens VALUES ('old.json')")
    relinker = SqlitePathRelinker(
        ratings_database_path=ratings_path,
        prompt_tokens_database_path=tokens_path,
        images_database_path=None,
        combo_database_path=None,
        arena_database_path=None,
    )

    relinker.relink(
        old_png_path="old.png",
        old_json_path="old.json",
        new_png_path="new.png",
        new_json_path="new.json",
    )

    with sqlite3.connect(ratings_path) as connection:
        assert connection.execute(
            "SELECT png_path, json_path FROM ratings"
        ).fetchone() == ("new.png", "new.json")
    with sqlite3.connect(tokens_path) as connection:
        assert connection.execute(
            "SELECT json_path FROM tokens"
        ).fetchone() == ("new.json",)
