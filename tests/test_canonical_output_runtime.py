"""Integration tests for canonical output image runtime reads."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import OutputImageReference
from comfyreview.providers import CanonicalOutputImageCatalog
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteOutputImageRepository,
    connect_read_only,
)


def _insert_native_image(database_path: Path, png_path: Path) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos-native', 'hero')"
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg-native', 'blur')"
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid,
                model_branch,
                checkpoint,
                combo_key,
                seed,
                steps,
                cfg,
                sampler,
                scheduler,
                denoise,
                loras_json,
                positive_prompt_id,
                negative_prompt_id,
                source,
                status
            )
            VALUES (
                'generation-native',
                'sdxl',
                'native.safetensors',
                'native-combo',
                123,
                28,
                5.5,
                'euler',
                'normal',
                1.0,
                '[]',
                1,
                2,
                'native_api',
                'completed'
            )
            """
        )
        generation_id = connection.execute(
            "SELECT id FROM generations "
            "WHERE generation_uid = 'generation-native'"
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO images(
                image_uid,
                generation_id,
                output_node_id,
                output_index,
                png_path,
                json_path
            )
            VALUES (?, ?, ?, ?, ?, NULL)
            """,
            (
                "image-native",
                generation_id,
                "save-node",
                0,
                str(png_path),
            ),
        )


def test_repository_reads_sidecarless_canonical_image(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path = tmp_path / "output" / "native.png"
    png_path.parent.mkdir()
    png_path.write_bytes(b"png")
    _insert_native_image(database_path, png_path)

    repository = SqliteOutputImageRepository(database_path)
    [record] = repository.list_live_images()

    assert record.image_uid == "image-native"
    assert record.generation_uid == "generation-native"
    assert record.json_path is None
    assert repository.get_live_image("image-native") == record


def test_canonical_read_connection_rejects_writes(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    connection = connect_read_only(database_path)
    try:
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            connection.execute(
                "INSERT INTO review_clock(singleton_id, value) VALUES (2, 0)"
            )
    finally:
        connection.close()


def test_canonical_catalog_lists_and_resolves_without_sidecar(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    native_png = output_root / "native.png"
    native_png.write_bytes(b"png")
    _insert_native_image(database_path, native_png)

    repository = SqliteOutputImageRepository(database_path)
    catalog = CanonicalOutputImageCatalog(
        output_root=output_root,
        canonical_images=repository,
    )

    images = catalog.list_images()
    assert {item.png_path.name for item in images} == {"native.png"}
    native = next(item for item in images if item.image_uid == "image-native")
    assert native.json_path is None
    assert native.meta["pos_prompt"] == "hero"
    assert native.meta["seed"] == 123

    resolved = catalog.resolve(
        OutputImageReference.from_client_uid("image-native")
    )
    assert resolved.pair.json_path is None
    assert resolved.image_uid == "image-native"
    assert resolved.generation_uid == "generation-native"
