"""Behavior tests for the local output-image catalog provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from comfyreview.providers import LocalOutputImageCatalog


def _write_pair(
    output_root: Path,
    relative_path: str,
    metadata: object,
    *,
    encoding: str = "utf-8",
) -> tuple[Path, Path]:
    png_path = output_root / relative_path
    json_path = png_path.with_suffix(".json")
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(b"png")
    json_path.write_text(
        json.dumps(metadata, ensure_ascii=False),
        encoding=encoding,
    )
    return png_path, json_path


def test_catalog_returns_empty_for_missing_root_or_sidecar(
    tmp_path: Path,
) -> None:
    missing_catalog = LocalOutputImageCatalog(tmp_path / "missing")
    assert missing_catalog.list_images() == ()

    (tmp_path / "image.png").write_bytes(b"png")
    assert LocalOutputImageCatalog(tmp_path).list_images() == ()


def test_catalog_reads_metadata_and_preserves_stable_order(
    tmp_path: Path,
) -> None:
    bom_png, bom_json = _write_pair(
        tmp_path,
        "b/image.png",
        {
            "checkpoint": "models/äther.safetensors",
            "model_branch": "sdxl",
            "combo_key": "explicit",
        },
        encoding="utf-8-sig",
    )
    invalid_png = tmp_path / "a" / "image.png"
    invalid_png.parent.mkdir()
    invalid_png.write_bytes(b"png")
    invalid_json = invalid_png.with_suffix(".json")
    invalid_json.write_text("{invalid", encoding="utf-8")

    images = LocalOutputImageCatalog(tmp_path).list_images()

    assert [image.json_path for image in images] == [invalid_json, bom_json]
    assert images[0].meta == {}
    assert images[0].checkpoint == "unknown"
    assert images[1].png_path == bom_png
    assert images[1].checkpoint == "models/äther.safetensors"
    assert images[1].model_branch == "sdxl"
    assert images[1].combo_key == "explicit"


def test_catalog_treats_non_object_or_unreadable_sidecars_as_empty_metadata(
    tmp_path: Path,
) -> None:
    _write_pair(tmp_path, "array.png", ["not", "metadata"])
    directory_sidecar_png = tmp_path / "directory.png"
    directory_sidecar_png.write_bytes(b"png")
    directory_sidecar_png.with_suffix(".json").mkdir()

    images = LocalOutputImageCatalog(tmp_path).list_images()

    assert len(images) == 2
    assert all(image.meta == {} for image in images)


def test_catalog_ignores_internal_folders_and_collapses_playground_scope(
    tmp_path: Path,
) -> None:
    nested_png, _ = _write_pair(
        tmp_path,
        "playground/Aiko/portrait/night/image.png",
        {},
    )
    _write_pair(tmp_path, "_trash/deleted.png", {})
    _write_pair(tmp_path, "sets/_lora_export/exported.png", {})

    images = LocalOutputImageCatalog(tmp_path).list_images()

    assert len(images) == 1
    assert images[0].png_path == nested_png
    assert images[0].subdir == "playground/Aiko"


def test_catalog_infers_checkpoint_model_and_sampler_from_graph(
    tmp_path: Path,
) -> None:
    _write_pair(
        tmp_path,
        "image.png",
        {
            "prompt_graph": {
                "invalid": ["not-a-node"],
                "loader": {
                    "class_type": "CheckpointLoader",
                    "inputs": {"checkpoint": "folder/model.safetensors"},
                },
                "sampler": {
                    "class_type": "KSampler",
                    "inputs": {
                        "sampler_name": "euler",
                        "scheduler": "normal",
                        "steps": 24,
                        "cfg": 6.5,
                        "denoise": 0.8,
                    },
                },
            }
        },
    )

    [image] = LocalOutputImageCatalog(tmp_path).list_images()

    assert image.checkpoint == "folder/model.safetensors"
    assert image.model_branch == "model"
    assert image.combo_key == (
        "ckpt=folder/model.safetensors"
        "|sampler=euler|sched=normal|steps=24|cfg=6.5|denoise=0.8"
    )


@pytest.mark.parametrize(
    ("metadata", "expected_suffix"),
    [
        (
            {"chosen_line": "dpmpp_2m, karras, 30, 7.0"},
            "sampler=dpmpp_2m|sched=karras|steps=30|cfg=7.0|denoise=",
        ),
        (
            {
                "ksampler": {
                    "sampler": "heun",
                    "scheduler": "simple",
                    "steps": 12,
                    "cfg": 4,
                    "denoise": 1,
                }
            },
            "sampler=heun|sched=simple|steps=12|cfg=4|denoise=1",
        ),
    ],
)
def test_catalog_preserves_sampler_fallbacks(
    tmp_path: Path,
    metadata: dict[str, object],
    expected_suffix: str,
) -> None:
    _write_pair(tmp_path, "image.png", metadata)

    [image] = LocalOutputImageCatalog(tmp_path).list_images()

    assert image.combo_key == f"ckpt=unknown|{expected_suffix}"


def test_catalog_rejects_paths_that_resolve_outside_root(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    outside_png, _ = _write_pair(tmp_path, "outside/image.png", {})
    linked_png = output_root / "linked.png"
    try:
        os.symlink(outside_png, linked_png)
    except OSError:
        catalog = LocalOutputImageCatalog(output_root)
        assert not catalog._is_inside_root(outside_png, output_root.resolve())
        return
    linked_png.with_suffix(".json").write_text("{}", encoding="utf-8")

    assert LocalOutputImageCatalog(output_root).list_images() == ()
