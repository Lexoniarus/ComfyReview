"""Behavior tests for the explicit catalog-normalization workflow."""

from __future__ import annotations

import json
import os
import socket
import sqlite3
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Any

import pytest

from comfyreview.__main__ import main
from comfyreview.application import OutputPair, ReviewImage, ReviewRecord
from comfyreview.application.prompt_catalog import prompt_revision_identity
from comfyreview.importers import (
    CatalogNormalizationAuditor,
    CatalogNormalizationRebuilder,
    CatalogNormalizationValidationError,
)
from comfyreview.importers.catalog_normalization import payload_sha256
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteReviewRepository,
)


def _insert_component(
    connection: sqlite3.Connection,
    *,
    uid: str,
    kind: str,
    name: str,
    atom: str,
) -> None:
    component_id = connection.execute(
        """
        INSERT INTO prompt_components(
            component_uid, kind, component_key, name
        ) VALUES (?, ?, ?, ?)
        """,
        (uid, kind, uid, name),
    ).lastrowid
    assert component_id is not None
    revision_id = connection.execute(
        """
        INSERT INTO prompt_revisions(
            revision_uid, component_id, revision_number,
            positive_text, negative_text, content_hash
        ) VALUES (?, ?, 1, ?, '', ?)
        """,
        (f"{uid}-revision", int(component_id), atom, f"{uid}-hash"),
    ).lastrowid
    assert revision_id is not None
    connection.execute(
        "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
        (atom,),
    )
    atom_id = connection.execute(
        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
        (atom,),
    ).fetchone()[0]
    connection.execute(
        """
        INSERT INTO prompt_revision_atom_usages(
            revision_id, atom_id, scope, position, weight_milli
        ) VALUES (?, ?, 'pos', 0, 1000)
        """,
        (int(revision_id), int(atom_id)),
    )


def _seed_rebuild_source(database: Path, tmp_path: Path) -> None:
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        positive_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'positive-hash', 'hero, fog') RETURNING id"
        ).fetchone()[0]
        negative_id = connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'negative-hash', 'blur') RETURNING id"
        ).fetchone()[0]
        for prompt_id, atom, position in (
            (positive_id, "hero", 0),
            (positive_id, "fog", 1),
            (negative_id, "blur", 0),
        ):
            atom_id = connection.execute(
                "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?) "
                "RETURNING id",
                (atom,),
            ).fetchone()
            if atom_id is None:
                atom_id = connection.execute(
                    "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                    (atom,),
                ).fetchone()
            connection.execute(
                "INSERT INTO prompt_memberships("
                "prompt_id, atom_id, position, weight_milli, raw_text"
                ") VALUES (?, ?, ?, 1000, ?)",
                (prompt_id, int(atom_id[0]), position, atom),
            )
        generation_id = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id
            ) VALUES ('generation-live', 'sdxl', 'model.safetensors', 'combo',
                      24, 6.5, 'euler', 'normal', 0.8, '[]', ?, ?)
            RETURNING id
            """,
            (positive_id, negative_id),
        ).fetchone()[0]
        image_path = tmp_path / "live.png"
        image_id = connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            ) VALUES ('image-live', ?, 'output', 0, ?, ?)
            RETURNING id
            """,
            (generation_id, str(image_path), str(tmp_path / "live.json")),
        ).fetchone()[0]
        _insert_component(
            connection,
            uid="hero-character",
            kind="character",
            name="Hero",
            atom="hero",
        )
        _insert_component(
            connection,
            uid="old-scene",
            kind="scene",
            name="Old scene",
            atom="fog",
        )
        old_scene_component_id, old_scene_revision_id = connection.execute(
            "SELECT component.id, revision.id "
            "FROM prompt_components AS component "
            "JOIN prompt_revisions AS revision "
            "ON revision.component_id = component.id "
            "WHERE component.component_uid = 'old-scene'"
        ).fetchone()
        old_scene_group_id = connection.execute(
            """
            INSERT INTO generation_prompt_groups(
                group_uid, generation_id, component_id,
                source_revision_id, kind, position, content_hash
            ) VALUES (
                'old-scene-generation-group', ?, ?, ?,
                'scene', 0, 'old-scene-hash'
            ) RETURNING id
            """,
            (
                generation_id,
                old_scene_component_id,
                old_scene_revision_id,
            ),
        ).fetchone()[0]
        old_scene_atom_id = connection.execute(
            "SELECT atom_id FROM prompt_revision_atom_usages "
            "WHERE revision_id = ?",
            (old_scene_revision_id,),
        ).fetchone()[0]
        connection.execute(
            "INSERT INTO generation_prompt_group_atom_usages("
            "group_id, atom_id, scope, position, weight_milli"
            ") VALUES (?, ?, 'pos', 0, 1000)",
            (old_scene_group_id, old_scene_atom_id),
        )
        composition_id = connection.execute(
            "INSERT INTO image_catalog_compositions("
            "composition_uid, image_id, version, source"
            ") VALUES ('source-composition', ?, 1, 'generation') RETURNING id",
            (image_id,),
        ).fetchone()[0]
        for position, revision_uid in enumerate(
            ("hero-character-revision", "old-scene-revision")
        ):
            revision_id = connection.execute(
                "SELECT id FROM prompt_revisions WHERE revision_uid = ?",
                (revision_uid,),
            ).fetchone()[0]
            connection.execute(
                "INSERT INTO image_catalog_composition_revisions("
                "composition_id, revision_id, position) VALUES (?, ?, ?)",
                (composition_id, revision_id, position),
            )
        connection.execute(
            "INSERT INTO current_image_catalog_compositions("
            "image_id, composition_id) VALUES (?, ?)",
            (image_id, composition_id),
        )

        deleted_generation = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                steps, cfg, sampler, scheduler, denoise, loras_json,
                positive_prompt_id, negative_prompt_id
            ) VALUES ('generation-deleted', 'sdxl', 'model.safetensors', 'combo',
                      24, 6.5, 'euler', 'normal', 0.8, '[]', ?, ?)
            RETURNING id
            """,
            (positive_id, negative_id),
        ).fetchone()[0]
        deleted_image_id = connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path, deleted_at
            ) VALUES ('image-deleted', ?, 'output', 0, ?, ?, datetime('now'))
            RETURNING id
            """,
            (
                deleted_generation,
                str(tmp_path / "deleted.png"),
                str(tmp_path / "deleted.json"),
            ),
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO review_events(
                event_uid, image_id, event_type, rating,
                source, source_key, sequence
            ) VALUES ('deleted-event', ?, 'delete', NULL,
                      'test', 'deleted-event', 1)
            """,
            (deleted_image_id,),
        )
        connection.execute(
            "INSERT INTO curation_assignments("
            "image_id, set_key, source, source_key"
            ") VALUES (?, 'old', 'test', 'deleted-curation')",
            (deleted_image_id,),
        )
        connection.execute(
            """
            INSERT INTO arena_matches(
                match_uid, left_image_id, right_image_id, winner_image_id,
                decision, source, source_key
            ) VALUES ('old-match', ?, ?, ?, 'left', 'test', 'old-match')
            """,
            (image_id, deleted_image_id, image_id),
        )
        connection.execute(
            "UPDATE review_clock SET value = 1 WHERE singleton_id = 1"
        )

    record = ReviewRecord(
        image=ReviewImage(
            pair=OutputPair(
                png_path=tmp_path / "live.png",
                json_path=tmp_path / "live.json",
            ),
            model_branch="sdxl",
            checkpoint="model.safetensors",
            combo_key="combo",
            steps=24,
            cfg=6.5,
            sampler="euler",
            scheduler="normal",
            denoise=0.8,
            loras_json="[]",
            positive_prompt="hero, fog",
            negative_prompt="blur",
            image_uid="image-live",
            generation_uid="generation-live",
        ),
        rating=8,
        deleted=False,
    )
    SqliteReviewRepository(database).append(record)


def _complete_rebuild_mapping(mapping_path: Path) -> str:
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    quality = next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )
    quality["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    for decision in mapping["source_components"]:
        decision["reviewed"] = True
        if decision["source_component_uid"] == "old-scene":
            decision["action"] = "replace"
            decision["target_component_uids"] = [
                f"normalized-{kind}"
                for kind in (
                    "scene",
                    "atmosphere",
                    "lighting",
                    "outfit",
                    "accessory",
                    "pose",
                    "expression",
                    "framing",
                    "camera_angle",
                    "optical_effect",
                )
            ]
    mapping["target_components"] = []
    revision_uids = []
    for kind in (
        "scene",
        "atmosphere",
        "lighting",
        "outfit",
        "accessory",
        "pose",
        "expression",
        "framing",
        "camera_angle",
        "optical_effect",
    ):
        component_uid = f"normalized-{kind}"
        text = "mist" if kind == "atmosphere" else f"normalized {kind}"
        revision_uid, _content_hash = prompt_revision_identity(
            component_uid, text, ""
        )
        revision_uids.append(revision_uid)
        atom = {
            "scope": "pos",
            "position": 0,
            "text": text,
            "weight_milli": 1000,
            "evidence_sources": [],
        }
        if kind == "atmosphere":
            atom["evidence_sources"] = [
                {
                    "component_uid": "old-scene",
                    "scope": "pos",
                    "text": "fog",
                    "relation": "synonym",
                }
            ]
        mapping["target_components"].append(
            {
                "component_uid": component_uid,
                "revision_uid": revision_uid,
                "revision_number": 1,
                "kind": kind,
                "component_key": f"normalized-{kind}",
                "name": f"Normalized {kind}",
                "tags": [],
                "notes": "normalized test fixture",
                "atoms": [atom],
            }
        )
    for image in mapping["image_compositions"]:
        image["reviewed"] = True
        image["revision_uids"] = [
            "hero-character-revision",
            *revision_uids,
        ]
    _write_mapping(mapping_path, mapping)
    return revision_uids[1]


def _write_mapping(mapping_path: Path, mapping: dict[str, Any]) -> None:
    mapping["mapping_sha256"] = payload_sha256(mapping, "mapping_sha256")
    mapping_path.write_text(
        json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )


def _unused_local_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _read_runtime_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=2.0) as response:
        payload: Any = json.loads(response.read().decode("utf-8"))
    assert isinstance(payload, dict)
    return payload


def _wait_for_main_runtime(
    process: subprocess.Popen[str],
    url: str,
) -> dict[str, Any]:
    deadline = time.monotonic() + 20.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            stdout, stderr = process.communicate()
            pytest.fail(
                "main.py exited before serving the rebuilt database:\n"
                f"stdout:\n{stdout}\nstderr:\n{stderr}"
            )
        try:
            return _read_runtime_json(url)
        except (OSError, json.JSONDecodeError):
            time.sleep(0.1)
    pytest.fail(
        "main.py did not expose the rebuilt database within 20 seconds"
    )


def test_catalog_normalization_audit_writes_hash_bound_mapping_draft(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        _insert_component(
            connection,
            uid="aiko",
            kind="character",
            name="Aiko",
            atom="aiko",
        )
        _insert_component(
            connection,
            uid="rooftop",
            kind="scene",
            name="Rooftop",
            atom="rooftop",
        )
        _insert_component(
            connection,
            uid="mixed",
            kind="modifier",
            name="Mixed",
            atom="rain or fog",
        )
    report_path = tmp_path / "reports" / "audit.json"
    mapping_path = tmp_path / "private" / "mapping.json"

    result = CatalogNormalizationAuditor(database).audit(
        report_path,
        mapping_path,
    )

    report = json.loads(report_path.read_text(encoding="utf-8"))
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    assert result.summary["components"] == 3
    assert result.summary["modifier_components"] == 1
    assert report["character_fingerprint"]["aiko_revision_counts"] == {
        "aiko": 1
    }
    decisions = {
        item["source_component_uid"]: item
        for item in mapping["source_components"]
    }
    assert decisions["rooftop"]["action"] == "review"
    assert decisions["rooftop"]["target_component_uids"] == []
    assert decisions["mixed"]["action"] == "review"
    assert mapping["complete"] is False
    assert mapping["target_components"] == []
    assert all(
        decision["reviewed"] is False
        for decision in mapping["source_components"]
    )
    assert all(
        composition["reviewed"] is False
        for composition in mapping["image_compositions"]
    )
    assert "defaulted_image_choices" not in mapping
    assert len(mapping["global_policies"]) == 6
    assert mapping["audit_sha256"] == report["audit_sha256"]

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="mapping already exists",
    ):
        CatalogNormalizationAuditor(database).audit(
            tmp_path / "other-report.json",
            mapping_path,
        )


def test_catalog_normalization_cli_uses_explicit_private_paths(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    report = tmp_path / "audit.json"
    mapping = tmp_path / "mapping.json"

    result = main(
        [
            "catalog-normalization",
            "audit",
            "--database",
            str(database),
            "--report",
            str(report),
            "--mapping",
            str(mapping),
        ]
    )

    assert result == 0
    output = json.loads(capsys.readouterr().out)
    assert output["report_path"] == str(report.resolve())
    assert output["mapping_path"] == str(mapping.resolve())


def test_catalog_audit_upgrades_snapshot_without_creating_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "source-v17.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        connection.execute("DROP INDEX idx_prompt_components_catalog_role")
        connection.execute(
            "ALTER TABLE prompt_components DROP COLUMN catalog_role"
        )
        connection.execute(
            "UPDATE schema_metadata SET value = '17' "
            "WHERE key = 'schema_version'"
        )
        connection.execute("PRAGMA user_version = 17")
        connection.commit()

    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_create_backup",
        lambda *_args: pytest.fail("audit must not create a backup"),
    )

    result = CatalogNormalizationAuditor(database).audit(
        tmp_path / "audit.json",
        tmp_path / "mapping.json",
    )

    assert result.summary["components"] == 0
    with sqlite3.connect(database) as connection:
        assert connection.execute("PRAGMA user_version").fetchone() == (17,)


def test_catalog_rebuild_preserves_safe_priors_and_resets_image_reviews(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    _seed_rebuild_source(database, tmp_path)
    source_before = database.read_bytes()
    with sqlite3.connect(database) as connection:
        character_promotions_before = connection.execute(
            "SELECT promotion.* FROM prompt_component_promotions AS promotion "
            "JOIN prompt_components AS component "
            "ON component.id = promotion.component_id "
            "WHERE component.kind = 'character' ORDER BY promotion.id"
        ).fetchall()
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    target_revision_uid = _complete_rebuild_mapping(mapping_path)
    output = tmp_path / "rebuilt.sqlite3"

    result = CatalogNormalizationRebuilder(database).rebuild(
        audit_path,
        mapping_path,
        output,
    )

    assert result.output_path == output.resolve()
    assert result.replaced_source is False
    assert result.live_images == 1
    assert result.removed_images == 1
    assert database.read_bytes() == source_before
    with sqlite3.connect(output) as connection:
        assert connection.execute(
            "SELECT image_uid FROM images"
        ).fetchall() == [("image-live",)]
        assert connection.execute(
            "SELECT COUNT(*) FROM review_events"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM arena_matches"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT COUNT(*) FROM curation_assignments"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT value FROM review_clock"
        ).fetchone() == (0,)
        assert connection.execute(
            "SELECT current_rating, rating_count FROM image_review_summary"
        ).fetchone() == (None, 0)
        assert connection.execute(
            """
            SELECT atom.canonical_text, baseline.sample_count,
                   baseline.rating_sum
            FROM atom_evidence_baselines AS baseline
            JOIN prompt_atoms AS atom ON atom.id = baseline.atom_id
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == ("mist", 1, 8.0)
        assert connection.execute(
            """
            SELECT atom.canonical_text, stats.sample_count, stats.rating_sum
            FROM atom_learning_stats AS stats
            JOIN prompt_atoms AS atom ON atom.id = stats.atom_id
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == ("mist", 1, 8.0)
        rebuilt_revision_uids = connection.execute(
            "SELECT revision.revision_uid "
            "FROM current_image_catalog_compositions AS current_catalog "
            "JOIN image_catalog_composition_revisions AS membership "
            "ON membership.composition_id = current_catalog.composition_id "
            "JOIN prompt_revisions AS revision "
            "ON revision.id = membership.revision_id "
            "ORDER BY membership.position"
        ).fetchall()
        assert rebuilt_revision_uids[0] == ("hero-character-revision",)
        assert len(rebuilt_revision_uids) == 11
        assert (target_revision_uid,) in rebuilt_revision_uids
        assert (
            connection.execute(
                "SELECT catalog_role, archived_at FROM prompt_components "
                "WHERE component_uid = 'old-scene'"
            ).fetchone()[0]
            == "generation_provenance"
        )
        assert (
            connection.execute(
                "SELECT promotion.* FROM prompt_component_promotions AS promotion "
                "JOIN prompt_components AS component "
                "ON component.id = promotion.component_id "
                "WHERE component.kind = 'character' ORDER BY promotion.id"
            ).fetchall()
            == character_promotions_before
        )
        assert connection.execute(
            "SELECT COUNT(*) FROM prompt_component_promotions AS promotion "
            "JOIN prompt_components AS component "
            "ON component.id = promotion.component_id "
            "WHERE component.kind != 'character' "
            "AND component.catalog_role = 'catalog' "
            "AND promotion.reason = 'catalog_cleanup_baseline'"
        ).fetchone() == (10,)
        assert connection.execute(
            "SELECT COUNT(*) FROM generation_global_prompt_policies "
            "WHERE generation_id = (SELECT id FROM generations "
            "WHERE generation_uid = 'generation-live')"
        ).fetchone() == (2,)

    SqliteReviewRepository(output).append(
        ReviewRecord(
            image=ReviewImage(
                pair=OutputPair(
                    png_path=tmp_path / "live.png",
                    json_path=tmp_path / "live.json",
                ),
                model_branch="sdxl",
                checkpoint="model.safetensors",
                combo_key="combo",
                steps=24,
                cfg=6.5,
                sampler="euler",
                scheduler="normal",
                denoise=0.8,
                loras_json="[]",
                positive_prompt="hero, fog",
                negative_prompt="blur",
                image_uid="image-live",
                generation_uid="generation-live",
            ),
            rating=9,
            deleted=False,
        )
    )
    with sqlite3.connect(output) as connection:
        assert connection.execute(
            """
            SELECT baseline.sample_count, baseline.rating_sum,
                   stats.sample_count, stats.rating_sum
            FROM atom_evidence_baselines AS baseline
            JOIN prompt_atoms AS atom ON atom.id = baseline.atom_id
            JOIN atom_learning_stats AS stats
              ON stats.atom_id = baseline.atom_id
             AND stats.scope = baseline.scope
             AND stats.model_branch = baseline.model_branch
             AND stats.weight_milli = baseline.weight_milli
            WHERE atom.canonical_text = 'mist'
            """
        ).fetchone() == (1, 8.0, 2, 17.0)


def test_rebuilt_database_runs_through_main_entrypoint(
    tmp_path: Path,
) -> None:
    repository_root = Path(__file__).resolve().parents[1]
    source = tmp_path / "source.sqlite3"
    _seed_rebuild_source(source, tmp_path)
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(source).audit(audit_path, mapping_path)
    _complete_rebuild_mapping(mapping_path)
    rebuilt = tmp_path / "rebuilt.sqlite3"
    CatalogNormalizationRebuilder(source).rebuild(
        audit_path,
        mapping_path,
        rebuilt,
    )
    port = _unused_local_port()
    environment = os.environ.copy()
    environment.update(
        {
            "COMFYREVIEW_DATABASE": str(rebuilt),
            "COMFYREVIEW_DATA_DIR": str(tmp_path / "runtime-data"),
            "COMFYREVIEW_OUTPUT_ROOT": str(tmp_path / "output"),
            "COMFYREVIEW_CARD_BATTLER_MODEL_DATABASE": str(
                tmp_path / "card-battler.sqlite3"
            ),
            "COMFYREVIEW_WORKFLOWS_DIR": str(
                repository_root / "data" / "workflows"
            ),
            "COMFYREVIEW_CHECKPOINTS_DIR": str(tmp_path / "checkpoints"),
            "COMFYREVIEW_COMFYUI_BASE_URL": "http://127.0.0.1:1",
            "COMFYREVIEW_HOST": "127.0.0.1",
            "COMFYREVIEW_PORT": str(port),
            "COMFYREVIEW_SSL_ENABLED": "false",
            "PYTHONUNBUFFERED": "1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, str(repository_root / "main.py")],
        cwd=repository_root,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        settings = _wait_for_main_runtime(
            process,
            f"{base_url}/api/v2/settings",
        )
        configuration = settings["runtime"]["configuration"]
        assert configuration["canonical_database_path"] == str(
            rebuilt.resolve()
        )
        assert configuration["schema_version"] == 18

        components = _read_runtime_json(
            f"{base_url}/api/v2/playground/components"
        )
        assert {
            component["kind"] for component in components["components"]
        } == {
            "character",
            "scene",
            "atmosphere",
            "lighting",
            "outfit",
            "accessory",
            "pose",
            "expression",
            "framing",
            "camera_angle",
            "optical_effect",
        }
        rankings = _read_runtime_json(f"{base_url}/api/v2/rankings")
        assert rankings["items"] == []
        assert rankings["total"] == 0
        with urllib.request.urlopen(f"{base_url}/", timeout=2.0) as response:
            assert response.status == 200
        with urllib.request.urlopen(
            f"{base_url}/playground/generator",
            timeout=2.0,
        ) as response:
            assert response.status == 200
    finally:
        if process.poll() is None:
            process.terminate()
        try:
            process.communicate(timeout=10.0)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate(timeout=10.0)


def test_catalog_rebuild_rejects_source_changes_after_audit(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    _write_mapping(mapping_path, mapping)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "INSERT INTO prompt_atoms(canonical_text) VALUES ('changed')"
        )

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="changed after catalog audit",
    ):
        CatalogNormalizationRebuilder(database).rebuild(
            audit_path,
            mapping_path,
            tmp_path / "output.sqlite3",
        )

    assert not (tmp_path / "output.sqlite3").exists()


def test_catalog_rebuild_can_atomically_replace_source_without_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database = tmp_path / "source.sqlite3"
    _seed_rebuild_source(database, tmp_path)
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    _complete_rebuild_mapping(mapping_path)
    output = tmp_path / "candidate.sqlite3"
    monkeypatch.setattr(
        CanonicalSchemaManager,
        "_create_backup",
        lambda *_args: pytest.fail("rebuild must not create a backup"),
    )

    result = CatalogNormalizationRebuilder(database).rebuild(
        audit_path,
        mapping_path,
        output,
        replace_source=True,
    )

    assert result.output_path == database.resolve()
    assert result.replaced_source is True
    assert not output.exists()
    assert CanonicalSchemaManager(database).validate().schema_version == 18
    with sqlite3.connect(database) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM global_prompt_policies WHERE active = 1"
        ).fetchone() == (6,)


def test_catalog_rebuild_rejects_or_alternatives_in_target_atoms(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    _seed_rebuild_source(database, tmp_path)
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    _complete_rebuild_mapping(mapping_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    target = mapping["target_components"][0]
    target["atoms"][0]["text"] = "mist or fog"
    target["revision_uid"] = prompt_revision_identity(
        target["component_uid"], "mist or fog", ""
    )[0]
    _write_mapping(mapping_path, mapping)

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="or-alternative",
    ):
        CatalogNormalizationRebuilder(database).rebuild(
            audit_path,
            mapping_path,
            tmp_path / "output.sqlite3",
        )


def test_catalog_rebuild_rejects_retained_non_character_components(
    tmp_path: Path,
) -> None:
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    with sqlite3.connect(database) as connection:
        _insert_component(
            connection,
            uid="ambiguous-outfit",
            kind="outfit",
            name="Ambiguous Outfit",
            atom="skirt or jeans",
        )
    audit_path = tmp_path / "audit.json"
    mapping_path = tmp_path / "mapping.json"
    CatalogNormalizationAuditor(database).audit(audit_path, mapping_path)
    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    mapping["complete"] = True
    mapping["source_components"][0].update(
        {
            "action": "keep",
            "target_component_uids": ["ambiguous-outfit"],
            "reviewed": True,
        }
    )
    next(
        item
        for item in mapping["global_policies"]
        if item["policy_type"] == "quality"
    )["atoms"] = [
        {
            "scope": "neg",
            "position": 0,
            "text": "bad anatomy",
            "weight_milli": 1000,
        }
    ]
    _write_mapping(mapping_path, mapping)

    with pytest.raises(
        CatalogNormalizationValidationError,
        match="Unresolved source component decision",
    ):
        CatalogNormalizationRebuilder(database).rebuild(
            audit_path,
            mapping_path,
            tmp_path / "output.sqlite3",
        )
