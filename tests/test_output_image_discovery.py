"""Characterization tests for legacy output-image discovery."""

from __future__ import annotations

import importlib
import inspect
import json
from pathlib import Path

from comfyreview.providers import LocalOutputImageCatalog

arena_router = importlib.import_module("routers.arena_router")
index_router = importlib.import_module("routers.index_router")
top_router = importlib.import_module("routers.top_router")


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


def test_scan_output_handles_missing_root_and_sidecar(tmp_path: Path) -> None:
    assert LocalOutputImageCatalog(tmp_path / "missing").list_images() == ()

    png_path = tmp_path / "without-sidecar.png"
    png_path.write_bytes(b"png")

    assert LocalOutputImageCatalog(tmp_path).list_images() == ()


def test_scan_output_reads_bom_and_keeps_invalid_sidecars(
    tmp_path: Path,
) -> None:
    bom_png, _ = _write_pair(
        tmp_path,
        "b-bom.png",
        {"checkpoint": "models/äther.safetensors"},
        encoding="utf-8-sig",
    )
    invalid_png = tmp_path / "a-invalid.png"
    invalid_png.write_bytes(b"png")
    invalid_png.with_suffix(".json").write_text("{invalid", encoding="utf-8")

    items = LocalOutputImageCatalog(tmp_path).list_images()

    assert [item.png_path for item in items] == [invalid_png, bom_png]
    assert items[0].meta == {}
    assert items[0].checkpoint == "unknown"
    assert items[1].checkpoint == "models/äther.safetensors"


def test_scan_output_ignores_internal_directories_and_collapses_playground_scope(
    tmp_path: Path,
) -> None:
    nested_png, _ = _write_pair(
        tmp_path,
        "playground/Aiko/portrait/night/image.png",
        {},
    )
    _write_pair(tmp_path, "_trash/deleted.png", {})
    _write_pair(tmp_path, "sets/_lora_export/exported.png", {})

    items = LocalOutputImageCatalog(tmp_path).list_images()

    assert len(items) == 1
    assert items[0].png_path == nested_png
    assert items[0].subdir == "playground/Aiko"


def test_scan_output_preserves_direct_metadata_values(tmp_path: Path) -> None:
    png_path, json_path = _write_pair(
        tmp_path,
        "review/image.png",
        {
            "checkpoint": "model.safetensors",
            "model_branch": "sdxl",
            "combo_key": "explicit-combination",
            "prompt": "private prompt remains raw boundary metadata",
        },
    )

    [item] = LocalOutputImageCatalog(tmp_path).list_images()

    assert item.png_path == png_path
    assert item.json_path == json_path
    assert item.subdir == "review"
    assert item.checkpoint == "model.safetensors"
    assert item.model_branch == "sdxl"
    assert item.combo_key == "explicit-combination"
    assert (
        item.meta["prompt"] == "private prompt remains raw boundary metadata"
    )


def test_scan_output_infers_checkpoint_model_and_combo_from_graph(
    tmp_path: Path,
) -> None:
    _write_pair(
        tmp_path,
        "image.png",
        {
            "comfy_prompt_graph": {
                "4": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {"ckpt_name": "folder/graph-model.safetensors"},
                },
                "8": {
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

    [item] = LocalOutputImageCatalog(tmp_path).list_images()

    assert item.checkpoint == "folder/graph-model.safetensors"
    assert item.model_branch == "graph-model"
    assert item.combo_key == (
        "ckpt=folder/graph-model.safetensors"
        "|sampler=euler|sched=normal|steps=24|cfg=6.5|denoise=0.8"
    )


def test_scan_output_uses_chosen_line_combo_fallback(tmp_path: Path) -> None:
    _write_pair(
        tmp_path,
        "image.png",
        {
            "ckpt_name": "chosen.safetensors",
            "chosen_line": "dpmpp_2m, karras, 30, 7.0",
        },
    )

    [item] = LocalOutputImageCatalog(tmp_path).list_images()

    assert item.combo_key == (
        "ckpt=chosen.safetensors"
        "|sampler=dpmpp_2m|sched=karras|steps=30|cfg=7.0|denoise="
    )


def test_output_read_routes_and_form_fields_keep_public_contract() -> None:
    assert index_router.index.__name__ == "index"
    assert top_router.top_pictures.__name__ == "top_pictures"
    assert arena_router.arena.__name__ == "arena"

    arena_result_parameters = inspect.signature(
        arena_router.arena_result
    ).parameters
    assert tuple(arena_result_parameters) == (
        "request",
        "winner_side",
        "left_json",
        "right_json",
        "model",
        "subdir",
        "mode",
        "set_key",
    )
