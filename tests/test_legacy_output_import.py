"""Integration tests for explicit audited legacy-output imports."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.__main__ import main
from comfyreview.importers import (
    LegacyOutputAuditor,
    LegacyOutputImporter,
    LegacyOutputImportValidationError,
)
from comfyreview.providers import LocalLegacyOutputImportSource
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
)
from comfyreview.repositories.sqlite.legacy_output_import import (
    SqliteLegacyOutputImportRepository,
)


class _Observer:
    def __init__(self) -> None:
        self.backups: list[Path] = []

    def backup_created(self, backup_path: Path) -> None:
        self.backups.append(backup_path)


def _importer(
    database_path: Path,
    *,
    observer: _Observer | None = None,
) -> LegacyOutputImporter:
    repository = SqliteLegacyOutputImportRepository(database_path)
    return LegacyOutputImporter(
        schema=CanonicalSchemaManager(database_path),
        source=LocalLegacyOutputImportSource(database_path),
        repository=repository,
        observer=observer,
    )


def _workflow() -> dict[str, object]:
    return {
        "loader": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
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
        "sampler": {
            "class_type": "KSampler",
            "inputs": {
                "seed": 123,
                "steps": 24,
                "cfg": 6.5,
                "sampler_name": "euler",
                "scheduler": "normal",
                "denoise": 1.0,
            },
        },
    }


def _workflow_with_linked_checkpoint() -> dict[str, object]:
    workflow = _workflow()
    loader = workflow["loader"]
    assert isinstance(loader, dict)
    loader["class_type"] = "RandomLoadCheckpoint"
    loader["inputs"] = {"ckpt_name": ["checkpoint-name", 0]}
    workflow["checkpoint-name"] = {
        "class_type": "PrimitiveString",
        "inputs": {"value": "model.safetensors"},
    }
    return workflow


def _write_source(output_root: Path) -> tuple[Path, Path]:
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    output_root.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(b"png-image")
    json_path.write_text(
        json.dumps(
            {
                "timestamp": "20260929_120000",
                "checkpoint": "model.safetensors",
                "model_base": "model",
                "ksampler": {
                    "seed": 123,
                    "steps": 24,
                    "cfg": 6.5,
                    "sampler": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                },
                "pos_prompt": "hero",
                "neg_prompt": "blur",
                "comfy_prompt_graph": _workflow(),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return png_path, json_path


def test_import_uses_sidecar_checkpoint_for_linked_workflow_input(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    database_path = tmp_path / "comfyreview.sqlite3"
    report_path = tmp_path / "audit.json"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    metadata["comfy_prompt_graph"] = _workflow_with_linked_checkpoint()
    json_path.write_text(json.dumps(metadata), encoding="utf-8")

    LegacyOutputAuditor(
        output_root=output_root,
        canonical_database_path=database_path,
    ).audit(report_path)

    records, excluded = LocalLegacyOutputImportSource(database_path).load(
        report_path
    )

    assert excluded == 0
    assert records[0].checkpoint == "model.safetensors"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _workflow_sha() -> str:
    return hashlib.sha256(
        json.dumps(
            _workflow(),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()


def _write_report(
    tmp_path: Path,
    output_root: Path,
    png_path: Path,
    json_path: Path,
    *,
    existing: bool = False,
) -> Path:
    report_path = tmp_path / "audit.json"
    report_path.write_text(
        json.dumps(
            {
                "format": "comfyreview-legacy-output-audit-v1",
                "output_root": str(output_root.resolve()),
                "canonical_database": str(
                    (tmp_path / "comfyreview.sqlite3").resolve()
                ),
                "summary": {
                    "png_seen": 1,
                    "png_ignored": 0,
                    "png_without_sidecar": 0,
                    "sidecar_pairs": 1,
                    "valid_sidecars": 1,
                    "invalid_sidecars": 0,
                    "full_graph_pairs": 1,
                    "partial_no_graph_pairs": 0,
                    "already_canonical": 1 if existing else 0,
                    "pairs_with_conflicts": 0,
                    "total_ksampler_stages": 1,
                    "unsupported_sampler_like_nodes": 0,
                    "generation_groups": 1,
                },
                "conflict_fields": {},
                "items": [
                    {
                        "png_path": png_path.name,
                        "json_path": json_path.name,
                        "png_sha256": _sha(png_path),
                        "sidecar_sha256": _sha(json_path),
                        "status": "full_graph",
                        "workflow_sha256": _workflow_sha(),
                        "candidate_generation_key": "group-one",
                        "canonical_image_uid": (
                            "existing-image" if existing else None
                        ),
                        "canonical_generation_uid": (
                            "existing-generation" if existing else None
                        ),
                        "graph": {
                            "checkpoint": "model.safetensors",
                            "ksampler_stages": [
                                {
                                    "node_id": "sampler",
                                    "stage_order": 0,
                                    "seed": 123,
                                    "steps": 24,
                                    "cfg": 6.5,
                                    "sampler": "euler",
                                    "scheduler": "normal",
                                    "denoise": 1.0,
                                }
                            ],
                            "loras": [],
                            "unsupported_sampler_like_nodes": [],
                        },
                        "conflicts": [],
                    }
                ],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return report_path


def _seed_existing(
    database_path: Path,
    png_path: Path,
    json_path: Path,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'existing-pos', 'hero')"
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'existing-neg', 'blur')"
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                positive_prompt_id, negative_prompt_id, source, status,
                comfy_prompt_id, submitted_at
            )
            VALUES (
                'existing-generation', 'old', 'old', 'old', 1, 2,
                'comfyui_api', 'running', 'prompt-123', '2026-09-29 12:00:00'
            )
            """
        )
        generation_id = connection.execute(
            "SELECT id FROM generations"
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            )
            VALUES ('existing-image', ?, 'save-node', 7, ?, ?)
            """,
            (generation_id, str(png_path), str(json_path)),
        )


def test_import_creates_full_provenance_and_backup(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )

    observer = _Observer()
    result = _importer(database_path, observer=observer).import_audit(
        report_path
    )

    assert result.new_images == 1
    assert result.enriched_images == 0
    assert result.new_generations == 1
    assert result.sampler_stages == 1
    assert result.excluded_without_sidecar == 0
    assert result.backup_path.is_file()
    assert observer.backups == [result.backup_path]
    with sqlite3.connect(database_path) as connection:
        generation = connection.execute(
            """
            SELECT generation_uid, source, checkpoint, seed,
                   workflow_hash, raw_metadata_json, workflow_json
            FROM generations
            """
        ).fetchone()
        image = connection.execute(
            """
            SELECT image_uid, output_node_id, output_index, png_path, json_path
            FROM images
            """
        ).fetchone()
        stages = connection.execute(
            "SELECT node_id, seed, steps FROM generation_sampler_stages"
        ).fetchall()
    assert generation[0] == "legacy-generation-group-one"
    assert generation[1:4] == ("legacy_sidecar", "model.safetensors", 123)
    assert generation[4]
    assert '"timestamp"' in generation[5]
    assert '"sampler"' in generation[6]
    assert image[0].startswith("legacy-image-")
    assert image[1:3] == ("legacy_sidecar", 0)
    assert image[3:] == (str(png_path.resolve()), str(json_path.resolve()))
    assert stages == [("sampler", 123, 24)]


def test_import_enriches_existing_identity_without_duplicate(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    _seed_existing(database_path, png_path, json_path)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
        existing=True,
    )

    result = _importer(database_path).import_audit(report_path)

    assert result.new_images == 0
    assert result.enriched_images == 1
    assert result.new_generations == 0
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM generations"
        ).fetchone() == (1,)
        assert connection.execute(
            "SELECT COUNT(*) FROM images"
        ).fetchone() == (1,)
        assert connection.execute(
            """
            SELECT workflow_hash, source, status, comfy_prompt_id,
                   submitted_at
            FROM generations
            """
        ).fetchone() == (
            _workflow_sha(),
            "comfyui_api",
            "running",
            "prompt-123",
            "2026-09-29 12:00:00",
        )
        assert connection.execute(
            "SELECT output_node_id, output_index FROM images"
        ).fetchone() == ("save-node", 7)


@pytest.mark.parametrize("existing", [False, True])
def test_import_persists_content_hash_without_replacing_output_slot(
    tmp_path: Path,
    existing: bool,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    if existing:
        _seed_existing(database_path, png_path, json_path)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
        existing=existing,
    )

    _importer(database_path).import_audit(report_path)

    with sqlite3.connect(database_path) as connection:
        image = connection.execute(
            "SELECT content_hash, output_node_id, output_index FROM images"
        ).fetchone()
    expected_slot = ("save-node", 7) if existing else ("legacy_sidecar", 0)
    assert image == (_sha(png_path), *expected_slot)


def test_import_rejects_source_changed_since_audit(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )
    png_path.write_bytes(b"changed")

    with pytest.raises(
        LegacyOutputImportValidationError,
        match="changed since audit",
    ):
        _importer(database_path).import_audit(report_path)

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM generations"
        ).fetchone() == (0,)


def test_import_rejects_audit_summary_tampering(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )
    payload = json.loads(report_path.read_text(encoding="utf-8"))
    payload["summary"]["full_graph_pairs"] = 2
    report_path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(
        LegacyOutputImportValidationError,
        match="summary does not match",
    ):
        _importer(database_path).import_audit(report_path)


def test_import_rejects_workflow_changed_after_audit(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    metadata["comfy_prompt_graph"]["sampler"]["inputs"]["seed"] = 999
    json_path.write_text(json.dumps(metadata), encoding="utf-8")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report["items"][0]["sidecar_sha256"] = _sha(json_path)
    report_path.write_text(json.dumps(report), encoding="utf-8")

    with pytest.raises(
        LegacyOutputImportValidationError,
        match="Workflow hash changed",
    ):
        _importer(database_path).import_audit(report_path)


def test_import_is_idempotent_for_one_audit_snapshot(tmp_path: Path) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )

    first = _importer(database_path).import_audit(report_path)
    second = _importer(database_path).import_audit(report_path)

    assert (first.new_images, first.enriched_images) == (1, 0)
    assert (second.new_images, second.enriched_images) == (0, 1)
    assert second.new_generations == 0
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM images"
        ).fetchone() == (1,)


def test_import_distinguishes_equal_pngs_from_distinct_generations(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    first_png, first_json = _write_source(output_root)
    second_png = output_root / "second.png"
    second_json = output_root / "second.json"
    second_png.write_bytes(first_png.read_bytes())
    metadata = json.loads(first_json.read_text(encoding="utf-8"))
    metadata["timestamp"] = "20260929_130000"
    second_json.write_text(json.dumps(metadata), encoding="utf-8")
    report_path = tmp_path / "audit.json"
    LegacyOutputAuditor(
        output_root=output_root,
        canonical_database_path=database_path,
    ).audit(report_path)

    result = _importer(database_path).import_audit(report_path)

    assert result.new_images == 2
    assert result.new_generations == 2
    with sqlite3.connect(database_path) as connection:
        image_uids = connection.execute(
            "SELECT image_uid FROM images ORDER BY image_uid"
        ).fetchall()
    assert len(image_uids) == 2
    assert image_uids[0] != image_uids[1]


def test_import_uses_rollback_without_unnecessary_restore(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )
    source = LocalLegacyOutputImportSource(database_path)
    records, excluded = source.load(report_path)
    repository = SqliteLegacyOutputImportRepository(database_path)
    observer = _Observer()

    def fail_generation(*_args: object, **_kwargs: object) -> int:
        raise RuntimeError("write failed")

    monkeypatch.setattr(repository, "_upsert_generation", fail_generation)
    monkeypatch.setattr(
        repository,
        "_restore_backup",
        lambda _path: pytest.fail("valid rollback must not restore a file"),
    )

    with pytest.raises(RuntimeError, match="write failed"):
        repository.import_records(
            records,
            excluded_without_sidecar=excluded,
            observer=observer,
        )

    assert len(observer.backups) == 1
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM generations"
        ).fetchone() == (0,)


def test_legacy_output_import_cli_reports_counts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    output_root = tmp_path / "output"
    CanonicalSchemaManager(database_path).prepare_startup()
    png_path, json_path = _write_source(output_root)
    report_path = _write_report(
        tmp_path,
        output_root,
        png_path,
        json_path,
    )
    monkeypatch.setenv("COMFYREVIEW_DATABASE", str(database_path))

    assert main(["legacy-output", "import", "--report", str(report_path)]) == 0
    captured = capsys.readouterr()
    output = json.loads(captured.out)
    progress = json.loads(captured.err)
    assert output["new_images"] == 1
    assert output["enriched_images"] == 0
    assert progress["event"] == "legacy_output_import.backup_created"
    assert progress["backup_path"] == output["backup_path"]
    assert Path(output["backup_path"]).is_file()
