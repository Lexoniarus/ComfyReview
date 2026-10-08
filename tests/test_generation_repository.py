"""SQLite and filesystem integration tests for native generation persistence."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from comfyreview.application import (
    GenerationCanvas,
    GenerationLoraSelection,
    GenerationOutputPolicy,
    GenerationPromptGroup,
    GenerationPromptSnapshot,
    GenerationRequest,
    GenerationSamplerSettings,
    PreparedGeneration,
    WorkflowCompiler,
)
from comfyreview.domain import prompt_atom_usages_from_text
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
            "latent": {"inputs": {"width": 1024, "height": 1024}},
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
            "image_width": {"node_id": "latent", "input_name": "width"},
            "image_height": {"node_id": "latent", "input_name": "height"},
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
            "hero, (smile:1.2)",
            "blur",
            (revision_uid,),
            positive_atoms=prompt_atom_usages_from_text("hero, (smile:1.2)"),
            negative_atoms=prompt_atom_usages_from_text("blur"),
            prompt_groups=(
                GenerationPromptGroup(
                    kind="character",
                    component_uid="component-1",
                    revision_uid=revision_uid,
                    position=0,
                    positive_atoms=prompt_atom_usages_from_text(
                        "hero, (smile:1.2)"
                    ),
                    negative_atoms=prompt_atom_usages_from_text("blur"),
                ),
            ),
            global_policy_revision_uids=("quality-1",),
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
        canvas=GenerationCanvas(768, 1152),
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
        connection.execute(
            """
            INSERT INTO global_prompt_policies(
                policy_uid, policy_key, policy_type, revision_number,
                name, active
            ) VALUES ('quality-1', 'quality', 'quality', 1, 'Quality', 1)
            """
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
                   raw_metadata_json, image_width, image_height
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
        prompt_groups = connection.execute(
            """
            SELECT prompt_group.kind, component.component_uid,
                   revision.revision_uid, prompt_group.candidate_id,
                   prompt_group.content_hash
            FROM generation_prompt_groups AS prompt_group
            JOIN prompt_components AS component
              ON component.id = prompt_group.component_id
            JOIN prompt_revisions AS revision
              ON revision.id = prompt_group.source_revision_id
            WHERE prompt_group.generation_id = (
                SELECT id FROM generations
                WHERE generation_uid = 'generation-native'
            )
            """
        ).fetchall()
        prompt_group_atoms = connection.execute(
            """
            SELECT usage.scope, usage.position, atom.canonical_text,
                   usage.weight_milli
            FROM generation_prompt_group_atom_usages AS usage
            JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
            JOIN generation_prompt_groups AS prompt_group
              ON prompt_group.id = usage.group_id
            WHERE prompt_group.generation_id = (
                SELECT id FROM generations
                WHERE generation_uid = 'generation-native'
            )
            ORDER BY CASE usage.scope WHEN 'pos' THEN 0 ELSE 1 END,
                     usage.position
            """
        ).fetchall()
        global_policies = connection.execute(
            """
            SELECT policy.policy_uid, usage.position
            FROM generation_global_prompt_policies AS usage
            JOIN global_prompt_policies AS policy ON policy.id = usage.policy_id
            WHERE usage.generation_id = (
                SELECT id FROM generations
                WHERE generation_uid = 'generation-native'
            )
            ORDER BY usage.position
            """
        ).fetchall()
    assert generation[:4] == (
        "native_comfyui",
        "completed",
        compiled.graph_hash,
        1,
    )
    assert json.loads(generation[4])["revision_uids"] == [revision_uid]
    assert json.loads(generation[4])["global_policy_revision_uids"] == [
        "quality-1"
    ]
    assert generation[5:] == (768, 1152)
    assert stages == [
        ("base_sampler", "sampler", 0),
        ("base_sampler", "sampler", 0),
    ]
    assert memberships == 3
    assert composition_memberships == [("character", 0, revision_uid)]
    assert loras == [(0, "style.safetensors", 800, 650)]
    assert len(prompt_groups) == 1
    assert global_policies == [("quality-1", 0)]
    assert prompt_groups[0][:4] == (
        "character",
        "component-1",
        revision_uid,
        None,
    )
    assert prompt_group_atoms == [
        ("pos", 0, "hero", 1000),
        ("pos", 1, "smile", 1200),
        ("neg", 0, "blur", 1000),
    ]


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


def test_generation_repository_rolls_back_mismatched_prompt_candidate(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    revision_uid = _catalog_revision(database_path)
    with sqlite3.connect(database_path) as connection:
        component_id, revision_id = connection.execute(
            """
            SELECT component.id, revision.id
            FROM prompt_components AS component
            JOIN prompt_revisions AS revision
              ON revision.component_id = component.id
            WHERE component.component_uid = 'component-1'
            """
        ).fetchone()
        connection.execute(
            """
            INSERT INTO prompt_component_candidates(
                candidate_uid, component_id, source_revision_id,
                candidate_type, content_hash
            ) VALUES ('candidate-wrong', ?, ?, 'manual', 'wrong-hash')
            """,
            (component_id, revision_id),
        )
    directory = tmp_path / "blueprints" / "portrait"
    directory.mkdir(parents=True)
    (directory / "v1.json").write_text(
        json.dumps(_blueprint_payload()), encoding="utf-8"
    )
    request = _request(revision_uid)
    group = replace(
        request.prompt.prompt_groups[0], candidate_uid="candidate-wrong"
    )
    request = replace(
        request,
        prompt=replace(request.prompt, prompt_groups=(group,)),
    )
    blueprint = JsonWorkflowBlueprintRepository(tmp_path / "blueprints").get(
        "portrait", 1
    )
    compiled = WorkflowCompiler().compile(blueprint, request)

    with pytest.raises(RuntimeError, match="candidate does not match"):
        SqliteGenerationRepository(database_path).prepare(
            PreparedGeneration("generation-invalid", request, compiled)
        )

    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM generations "
            "WHERE generation_uid = 'generation-invalid'"
        ).fetchone() == (0,)
