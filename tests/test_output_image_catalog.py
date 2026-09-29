"""Behavior tests for the local output-image catalog provider."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from comfyreview.application import (
    InvalidOutputPathError,
    OutputImageReference,
    OutputPairNotFoundError,
)
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


def test_review_resolution_uses_authoritative_sidecar_metadata(
    tmp_path: Path,
) -> None:
    png_path, json_path = _write_pair(
        tmp_path,
        "image.png",
        {
            "checkpoint": "server-model.safetensors",
            "model_branch": "server-branch",
            "combo_key": "server-combo",
            "ksampler": {
                "sampler": "euler",
                "scheduler": "normal",
                "steps": "24",
                "cfg": "6,5",
                "denoise": "0.8",
            },
            "pos_prompt": "hero",
            "neg_prompt": "blur",
            "loras": [{"name": "style.safetensors", "sm": 0.7}],
        },
    )

    image = LocalOutputImageCatalog(tmp_path).resolve(
        OutputImageReference(png_path=png_path, json_path=json_path)
    )

    assert image.checkpoint == "server-model.safetensors"
    assert image.model_branch == "server-branch"
    assert image.combo_key == "server-combo"
    assert (image.steps, image.cfg, image.denoise) == (24, 6.5, 0.8)
    assert (image.sampler, image.scheduler) == ("euler", "normal")
    assert (image.positive_prompt, image.negative_prompt) == ("hero", "blur")
    assert json.loads(image.loras_json) == [
        {"name": "style.safetensors", "sm": 0.7}
    ]


def test_review_resolution_normalizes_graph_loras_and_invalid_values(
    tmp_path: Path,
) -> None:
    png_path, json_path = _write_pair(
        tmp_path,
        "image.png",
        {
            "steps": "not-an-int",
            "cfg": "not-a-float",
            "loras": object().__class__.__name__,
            "comfy_prompt_graph": {
                "lora": {
                    "class_type": "LoraLoader",
                    "inputs": {
                        "lora_name": "graph-style.safetensors",
                        "strength_model": 0.8,
                        "strength_clip": 0.6,
                    },
                }
            },
        },
    )

    image = LocalOutputImageCatalog(tmp_path).resolve(
        OutputImageReference(png_path=png_path, json_path=json_path)
    )

    assert image.steps is None
    assert image.cfg is None
    assert json.loads(image.loras_json) == [
        {"name": "graph-style.safetensors", "sm": 0.8, "sc": 0.6}
    ]


def test_review_resolution_accepts_invalid_sidecar_as_empty_metadata(
    tmp_path: Path,
) -> None:
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{invalid", encoding="utf-8")

    image = LocalOutputImageCatalog(tmp_path).resolve(
        OutputImageReference(png_path=png_path, json_path=json_path)
    )

    assert image.checkpoint == "unknown"
    assert image.model_branch == "unknown"
    assert image.positive_prompt == ""
    assert image.loras_json == "[]"


def test_review_resolution_rejects_escape_internal_and_mismatched_paths(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    outside_png, outside_json = _write_pair(tmp_path, "outside/image.png", {})
    trash_png, trash_json = _write_pair(
        output_root,
        "_trash/image.png",
        {},
    )
    valid_png, _valid_json = _write_pair(output_root, "valid.png", {})
    catalog = LocalOutputImageCatalog(output_root)

    with pytest.raises(InvalidOutputPathError, match="outside"):
        catalog.resolve(
            OutputImageReference(
                png_path=outside_png,
                json_path=outside_json,
            )
        )
    with pytest.raises(InvalidOutputPathError, match="Invalid"):
        catalog.resolve(
            OutputImageReference(png_path=trash_png, json_path=trash_json)
        )
    with pytest.raises(InvalidOutputPathError, match="Invalid"):
        catalog.resolve(
            OutputImageReference(
                png_path=valid_png,
                json_path=valid_png.with_name("other.json"),
            )
        )


def test_review_resolution_reports_missing_pair(tmp_path: Path) -> None:
    catalog = LocalOutputImageCatalog(tmp_path)

    with pytest.raises(OutputPairNotFoundError, match="no longer exists"):
        catalog.resolve(
            OutputImageReference(
                png_path=tmp_path / "missing.png",
                json_path=tmp_path / "missing.json",
            )
        )
