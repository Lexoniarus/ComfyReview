"""Tests for the read-only legacy output provenance audit."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from comfyreview.__main__ import main
from comfyreview.importers import LegacyOutputAuditor
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _sidecar_payload() -> dict[str, object]:
    return {
        "timestamp": "20260929_120000",
        "checkpoint": "sidecar.safetensors",
        "ksampler": {
            "seed": 999,
            "steps": 28,
            "cfg": 6.0,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        },
        "pos_prompt": "different hero",
        "neg_prompt": "blur",
        "comfy_prompt_graph": {
            "loader": {
                "class_type": "RandomLoadCheckpoint",
                "inputs": {"ckpt_name": "graph.safetensors"},
            },
            "positive": {
                "class_type": "PrimitiveStringMultiline",
                "_meta": {"title": "Prompt"},
                "inputs": {"value": "hero"},
            },
            "negative": {
                "class_type": "PrimitiveStringMultiline",
                "_meta": {"title": "Negative Prompt"},
                "inputs": {"value": "blur"},
            },
            "sampler-a": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 123,
                    "steps": 28,
                    "cfg": 5.5,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
            },
            "sampler-b": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": 456,
                    "steps": 12,
                    "cfg": 4.0,
                    "sampler_name": "heun",
                    "scheduler": "simple",
                    "denoise": 0.5,
                },
            },
            "lora": {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": "style.safetensors",
                    "strength_model": 0.8,
                    "strength_clip": 0.6,
                },
            },
        },
    }


def _write_pair(output_root: Path, name: str) -> tuple[Path, Path]:
    png_path = output_root / f"{name}.png"
    json_path = output_root / f"{name}.json"
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(b"png")
    json_path.write_text(
        json.dumps(_sidecar_payload(), ensure_ascii=False),
        encoding="utf-8",
    )
    return png_path, json_path


def _register_canonical_image(
    database_path: Path,
    png_path: Path,
    json_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos-hash', 'hero')"
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg-hash', 'blur')"
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid,
                model_branch,
                checkpoint,
                combo_key,
                positive_prompt_id,
                negative_prompt_id
            )
            VALUES ('generation-existing', 'sdxl', 'graph.safetensors',
                    'combo', 1, 2)
            """
        )
        generation_id = connection.execute(
            "SELECT id FROM generations WHERE generation_uid = ?",
            ("generation-existing",),
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
            VALUES ('image-existing', ?, 'legacy_sidecar', 0, ?, ?)
            """,
            (generation_id, str(png_path), str(json_path)),
        )


def test_audit_uses_graph_truth_and_reports_conflicts(tmp_path: Path) -> None:
    output_root = tmp_path / "output"
    database_path = tmp_path / "comfyreview.sqlite3"
    report_path = tmp_path / "audit.json"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_pair(output_root, "image")
    _register_canonical_image(database_path, png_path, json_path)

    before = database_path.read_bytes()
    result = LegacyOutputAuditor(
        output_root=output_root,
        canonical_database_path=database_path,
    ).audit(report_path)
    after = database_path.read_bytes()

    assert before == after
    assert result.summary["sidecar_pairs"] == 1
    assert result.summary["full_graph_pairs"] == 1
    assert result.summary["already_canonical"] == 1
    assert result.summary["total_ksampler_stages"] == 2
    assert result.summary["pairs_with_conflicts"] == 1
    assert result.conflict_fields["checkpoint"] == 1
    assert result.conflict_fields["positive_prompt"] == 1
    assert result.conflict_fields["ksampler.seed"] == 1
    assert result.conflict_fields["ksampler.cfg"] == 1

    payload = json.loads(report_path.read_text(encoding="utf-8"))
    [item] = payload["items"]
    assert item["canonical_image_uid"] == "image-existing"
    assert item["graph"]["checkpoint"] == "graph.safetensors"
    assert len(item["graph"]["ksampler_stages"]) == 2
    assert item["graph"]["loras"][0]["name"] == "style.safetensors"
    assert item["candidate_generation_key"]


def test_audit_counts_missing_invalid_and_ignored_outputs(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    (output_root / "no-sidecar.png").write_bytes(b"png")
    invalid_png = output_root / "invalid.png"
    invalid_png.write_bytes(b"png")
    invalid_png.with_suffix(".json").write_text("{invalid", encoding="utf-8")

    trash = output_root / "_trash"
    trash.mkdir()
    (trash / "ignored.png").write_bytes(b"png")
    (trash / "ignored.json").write_text("{}", encoding="utf-8")

    result = LegacyOutputAuditor(
        output_root=output_root,
        canonical_database_path=database_path,
    ).audit(tmp_path / "audit.json")

    assert result.summary["png_seen"] == 3
    assert result.summary["png_ignored"] == 1
    assert result.summary["png_without_sidecar"] == 1
    assert result.summary["invalid_sidecars"] == 1


def test_legacy_output_audit_cli_writes_report(
    tmp_path: Path,
    capsys,
) -> None:
    output_root = tmp_path / "output"
    database_path = tmp_path / "comfyreview.sqlite3"
    report_path = tmp_path / "reports" / "audit.json"
    CanonicalSchemaManager(database_path).prepare_startup()
    _write_pair(output_root, "image")

    assert (
        main(
            [
                "legacy-output",
                "audit",
                "--output-root",
                str(output_root),
                "--database",
                str(database_path),
                "--report",
                str(report_path),
            ]
        )
        == 0
    )
    output = json.loads(capsys.readouterr().out)
    assert output["full_graph_pairs"] == 1
    assert output["report_path"] == str(report_path.resolve())
    assert report_path.is_file()
