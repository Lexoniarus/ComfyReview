"""SQLite and filesystem integration tests for native generation persistence."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    GenerationLoraSelection,
    GenerationOutputPolicy,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    PreparedGeneration,
    WorkflowCompiler,
)
from comfyreview.repositories.filesystem import JsonWorkflowBlueprintRepository
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGenerationRepository,
)


def _blueprint_payload() -> dict[str, object]:
    return {
        "blueprint_uid": "portrait",
        "version": 1,
        "graph": {
            "positive": {"inputs": {"text": "", "clip": ["checkpoint", 1]}},
            "negative": {"inputs": {"text": ""}},
            "checkpoint": {"inputs": {"ckpt_name": ""}},
            "sampler": {
                "inputs": {
                    "seed": 1,
                    "steps": 1,
                    "cfg": 1.0,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["checkpoint", 0],
                }
            },
            "save": {"inputs": {"subfolder": "", "prefix": ""}},
        },
        "role_bindings": {
            "positive_prompt": {"node_id": "positive", "input_name": "text"},
            "negative_prompt": {"node_id": "negative", "input_name": "text"},
            "checkpoint": {
                "node_id": "checkpoint",
                "input_name": "ckpt_name",
            },
            "base_sampler": {"node_id": "sampler"},
            "output_subdirectory": {
                "node_id": "save",
                "input_name": "subfolder",
            },
            "filename_prefix": {"node_id": "save", "input_name": "prefix"},
        },
        "output_bindings": [{"role": "primary", "node_id": "save"}],
        "sampler_roles": ["base_sampler"],
        "capability_requirements": ["SaveImage"],
        "lora_chain_binding": {
            "model_source": {"node_id": "checkpoint", "output_index": 0},
            "clip_source": {"node_id": "checkpoint", "output_index": 1},
            "model_targets": [{"node_id": "sampler", "input_name": "model"}],
            "clip_targets": [{"node_id": "positive", "input_name": "clip"}],
        },
    }


def _request(revision_uid: str) -> GenerationRequest:
    return GenerationRequest(
        prompt=GenerationPromptSnapshot(
            "hero, (smile:1.2)", "blur", (revision_uid,)
        ),
        blueprint_uid="portrait",
        blueprint_version=1,
        model_branch="sdxl",
        combo_key="character:1|scene:2",
        checkpoint="model.safetensors",
        sampler_stages=(
            GenerationSamplerSettings(
                "base_sampler", 42, 24, 6.5, "euler", "normal", 0.8
            ),
        ),
        output_policy=GenerationOutputPolicy(
            "playground/Hero", "hero_", ("primary",)
        ),
        loras=(GenerationLoraSelection("style.safetensors", 800, 650, 0),),
    )


def _catalog_revision(database_path: Path) -> str:
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name, tags, notes
            ) VALUES ('component-1', 'character', 'hero', 'Hero', '[]', '')
            """
        )
        revision_uid = "revision-1"
        connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES (?, ?, 1, 'hero', 'blur', 'hash')
            """,
            (revision_uid, cursor.lastrowid),
        )
    return revision_uid


def test_json_blueprint_repository_loads_latest_explicit_mapping(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "portrait"
    directory.mkdir()
    (directory / "v1.json").write_text(
        json.dumps(_blueprint_payload()), encoding="utf-8"
    )
    second = {**_blueprint_payload(), "version": 2}
    (directory / "v2.json").write_text(json.dumps(second), encoding="utf-8")
    repository = JsonWorkflowBlueprintRepository(tmp_path)

    assert repository.get("portrait", None).version == 2
    assert (
        repository.get("portrait", 1).role_bindings["base_sampler"].node_id
        == "sampler"
    )


@pytest.mark.parametrize(
    ("uid", "version", "message"),
    (
        ("../escape", 1, "blueprint_uid is invalid"),
        ("portrait", 0, "version must be positive"),
        ("missing", None, "No workflow blueprint versions"),
    ),
)
def test_json_blueprint_repository_rejects_invalid_selection(
    tmp_path: Path,
    uid: str,
    version: int | None,
    message: str,
) -> None:
    with pytest.raises((KeyError, ValueError), match=message):
        JsonWorkflowBlueprintRepository(tmp_path).get(uid, version)


def test_generation_repository_persists_reproducible_request_and_lifecycle(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    revision_uid = _catalog_revision(database_path)
    directory = tmp_path / "blueprints" / "portrait"
    directory.mkdir(parents=True)
    (directory / "v1.json").write_text(
        json.dumps(_blueprint_payload()), encoding="utf-8"
    )
    blueprint = JsonWorkflowBlueprintRepository(tmp_path / "blueprints").get(
        "portrait", 1
    )
    request = _request(revision_uid)
    compiled = WorkflowCompiler().compile(blueprint, request)
    repository = SqliteGenerationRepository(database_path)

    assert (
        repository.prepare(
            PreparedGeneration("generation-native", request, compiled)
        ).status
        == "prepared"
    )
    assert (
        repository.mark_submitting("generation-native").status == "submitting"
    )
    submitted = repository.mark_submitted("generation-native", "prompt-1")
    assert submitted.prompt_id == "prompt-1"
    assert repository.mark_running("generation-native").status == "running"
    assert repository.mark_completed("generation-native").status == "completed"

    repository.prepare(
        PreparedGeneration("generation-reconcile", request, compiled)
    )
    repository.mark_submitting("generation-reconcile")
    ambiguous = repository.mark_reconciliation_required(
        "generation-reconcile",
        None,
        "submit_timeout",
    )
    assert ambiguous.prompt_id is None
    assigned = repository.mark_reconciliation_required(
        "generation-reconcile",
        "prompt-2",
        "operator_prompt_id_assigned",
    )
    assert assigned.prompt_id == "prompt-2"
    assert (
        repository.mark_completed("generation-reconcile").status == "completed"
    )

    with sqlite3.connect(database_path) as connection:
        generation = connection.execute(
            """
            SELECT source, status, workflow_hash, prompt_composition_id,
                   raw_metadata_json
            FROM generations WHERE generation_uid = 'generation-native'
            """
        ).fetchone()
        stages = connection.execute(
            "SELECT role, node_id, stage_order FROM generation_sampler_stages"
        ).fetchall()
        memberships = connection.execute(
            "SELECT COUNT(*) FROM prompt_memberships"
        ).fetchone()[0]
        composition_memberships = connection.execute(
            """
            SELECT membership.slot, membership.position,
                   revision.revision_uid
            FROM prompt_composition_revisions AS membership
            JOIN prompt_revisions AS revision
                ON revision.id = membership.revision_id
            ORDER BY membership.position
            """
        ).fetchall()
        loras = connection.execute(
            "SELECT position, lora_name, model_strength_milli, "
            "clip_strength_milli FROM generation_loras "
            "WHERE generation_id = (SELECT id FROM generations "
            "WHERE generation_uid = 'generation-native')"
        ).fetchall()
    assert generation[:4] == (
        "native_comfyui",
        "completed",
        compiled.graph_hash,
        1,
    )
    assert json.loads(generation[4])["revision_uids"] == [revision_uid]
    assert stages == [
        ("base_sampler", "sampler", 0),
        ("base_sampler", "sampler", 0),
    ]
    assert memberships == 3
    assert composition_memberships == [("character", 0, revision_uid)]
    assert loras == [(0, "style.safetensors", 800, 650)]


def test_generation_repository_enforces_transitions_and_missing_database(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    repository = SqliteGenerationRepository(database_path)
    with pytest.raises(KeyError, match="Unknown generation"):
        repository.get("missing")
    with pytest.raises(FileNotFoundError):
        SqliteGenerationRepository(tmp_path / "missing.sqlite3").get("missing")
