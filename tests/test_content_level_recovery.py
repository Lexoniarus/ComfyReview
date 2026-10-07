"""Behavior tests for audited prompt content-level recovery."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import prompt_revision_identity
from comfyreview.domain import prompt_atom_usages_from_text
from comfyreview.importers import (
    ContentLevelAuditor,
    ContentLevelRecovery,
    ContentLevelRecoveryValidationError,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _fixture(tmp_path: Path) -> tuple[Path, Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    database = tmp_path / "source.sqlite3"
    CanonicalSchemaManager(database).prepare_startup()
    positive = "lace lingerie"
    negative = ""
    with sqlite3.connect(database) as connection:
        component = connection.execute(
            "INSERT INTO prompt_components(component_uid, kind, component_key, "
            "name, tags, notes) VALUES "
            "('component-1', 'outfit', 'lingerie', 'Lingerie', '[]', '')"
        )
        revision_uid, content_hash = prompt_revision_identity(
            "component-1", positive, negative
        )
        revision = connection.execute(
            "INSERT INTO prompt_revisions(revision_uid, component_id, "
            "revision_number, positive_text, negative_text, content_hash) "
            "VALUES (?, ?, 1, ?, ?, ?)",
            (
                revision_uid,
                int(component.lastrowid or 0),
                positive,
                negative,
                content_hash,
            ),
        )
        revision_id = int(revision.lastrowid or 0)
        for scope, snapshot in (("pos", positive), ("neg", negative)):
            for position, usage in enumerate(
                prompt_atom_usages_from_text(snapshot)
            ):
                connection.execute(
                    "INSERT OR IGNORE INTO prompt_atoms(canonical_text) VALUES (?)",
                    (usage.text,),
                )
                atom_id = int(
                    connection.execute(
                        "SELECT id FROM prompt_atoms WHERE canonical_text = ?",
                        (usage.text,),
                    ).fetchone()[0]
                )
                connection.execute(
                    "INSERT INTO prompt_revision_atom_usages("
                    "revision_id, atom_id, scope, position, weight_milli) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        revision_id,
                        atom_id,
                        scope,
                        position,
                        usage.weight_milli,
                    ),
                )
        composition = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-1')"
        )
        connection.execute(
            "INSERT INTO prompt_composition_revisions("
            "composition_id, revision_id, slot, position) VALUES (?, ?, 'outfit', 0)",
            (int(composition.lastrowid or 0), revision_id),
        )
        pos_id = _prompt(connection, "pos", positive)
        neg_id = _prompt(connection, "neg", negative)
        generation = connection.execute(
            "INSERT INTO generations(generation_uid, model_branch, checkpoint, "
            "combo_key, positive_prompt_id, negative_prompt_id, "
            "prompt_composition_id, inferred_content_level) "
            "VALUES ('generation-1', 'sdxl', 'model', 'combo', ?, ?, ?, 'standard')",
            (pos_id, neg_id, int(composition.lastrowid or 0)),
        )
        image = connection.execute(
            "INSERT INTO images(image_uid, generation_id, png_path, json_path) "
            "VALUES ('image-1', ?, 'image.png', 'image.json')",
            (int(generation.lastrowid or 0),),
        )
        event = connection.execute(
            "INSERT INTO image_content_level_events("
            "event_uid, image_id, content_level, source) "
            "VALUES ('event-1', ?, 'standard', 'test')",
            (int(image.lastrowid or 0),),
        )
        connection.execute(
            "INSERT INTO image_content_level_state("
            "image_id, event_id, override_content_level) "
            "VALUES (?, ?, 'standard')",
            (int(image.lastrowid or 0), int(event.lastrowid or 0)),
        )
    curation = tmp_path / "curation.json"
    curation.write_text(
        json.dumps(
            {
                "format_version": 1,
                "components": [
                    {
                        "component_uid": "component-1",
                        "revision_uid": revision_uid,
                        "content_hash": content_hash,
                        "content_level": "sexy",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    return database, curation, tmp_path / "audit.json"


def _prompt(connection: sqlite3.Connection, scope: str, text: str) -> int:
    digest = hashlib.sha256(text.encode()).hexdigest()
    cursor = connection.execute(
        "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
        (scope, digest, text),
    )
    return int(cursor.lastrowid or 0)


def test_content_level_recovery_is_complete_non_destructive_and_preserves_overrides(
    tmp_path: Path,
) -> None:
    database, curation, report = _fixture(tmp_path)
    source_before = database.read_bytes()

    audit = ContentLevelAuditor(database, curation).audit(report)
    output = tmp_path / "recovered.sqlite3"
    result = ContentLevelRecovery(database).recover(report, output)

    assert audit.summary == {
        "components": 1,
        "changed_components": 1,
        "generations": 1,
        "changed_generations": 1,
        "images": 1,
        "manual_overrides": 1,
        "inactive_lora_selections": 0,
    }
    assert database.read_bytes() == source_before
    assert result.reclassified_generations == 1
    assert result.preserved_overrides == 1
    assert CanonicalSchemaManager(output).validate().schema_version == 15
    with sqlite3.connect(output) as connection:
        assert "content_level_sexy" in json.loads(
            connection.execute(
                "SELECT tags FROM prompt_components"
            ).fetchone()[0]
        )
        assert (
            connection.execute(
                "SELECT inferred_content_level FROM generations"
            ).fetchone()[0]
            == "sexy"
        )
        assert (
            connection.execute(
                "SELECT override_content_level FROM image_content_level_state"
            ).fetchone()[0]
            == "standard"
        )


def test_content_level_recovery_removes_only_graph_inactive_loras(
    tmp_path: Path,
) -> None:
    database, curation, report = _fixture(tmp_path)
    curated = json.loads(curation.read_text(encoding="utf-8"))
    curated["components"][0]["content_level"] = "standard"
    curation.write_text(json.dumps(curated), encoding="utf-8")
    graph = {
        "loader": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": "model.safetensors"},
        },
        "inactive": {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": "unused.safetensors",
                "strength_model": 1,
                "strength_clip": 1,
            },
        },
        "sampler": {
            "class_type": "KSampler",
            "inputs": {"model": ["loader", 0]},
        },
    }
    raw_loras = [
        {
            "name": "unused.safetensors",
            "sm": 1,
            "sc": 1,
            "node_id": "inactive",
            "class_type": "LoraLoader",
        }
    ]
    with sqlite3.connect(database) as connection:
        generation_id = int(
            connection.execute(
                "SELECT id FROM generations WHERE generation_uid = 'generation-1'"
            ).fetchone()[0]
        )
        connection.execute(
            "UPDATE generations SET inferred_content_level = 'explicit', "
            "raw_metadata_json = ?, workflow_json = ?, loras_json = ? "
            "WHERE id = ?",
            (
                json.dumps({"comfy_prompt_graph": graph}),
                json.dumps(graph),
                json.dumps(raw_loras),
                generation_id,
            ),
        )
        connection.execute(
            "INSERT INTO generation_loras("
            "generation_id, position, lora_name, model_strength_milli, "
            "clip_strength_milli, content_level_snapshot) "
            "VALUES (?, 0, 'unused.safetensors', 1000, 1000, 'explicit')",
            (generation_id,),
        )

    before = database.read_bytes()
    audit = ContentLevelAuditor(database, curation).audit(report)
    output = tmp_path / "graph-recovered.sqlite3"
    result = ContentLevelRecovery(database).recover(report, output)

    assert database.read_bytes() == before
    assert audit.summary["inactive_lora_selections"] == 1
    assert result.removed_inactive_loras == 1
    assert result.reclassified_generations == 1
    with sqlite3.connect(output) as connection:
        assert (
            connection.execute(
                "SELECT COUNT(*) FROM generation_loras"
            ).fetchone()[0]
            == 0
        )
        generation = connection.execute(
            "SELECT inferred_content_level, loras_json FROM generations"
        ).fetchone()
        assert generation[0] == "standard"
        assert json.loads(generation[1]) == raw_loras


def test_content_level_recovery_rejects_incomplete_and_stale_evidence(
    tmp_path: Path,
) -> None:
    database, curation, report = _fixture(tmp_path)
    payload = json.loads(curation.read_text(encoding="utf-8"))
    payload["components"] = []
    curation.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(
        ContentLevelRecoveryValidationError, match="incomplete"
    ):
        ContentLevelAuditor(database, curation).audit(report)

    database, curation, report = _fixture(tmp_path / "stale")
    ContentLevelAuditor(database, curation).audit(report)
    with sqlite3.connect(database) as connection:
        connection.execute(
            "UPDATE prompt_components SET notes = 'changed' "
            "WHERE component_uid = 'component-1'"
        )
    with pytest.raises(ContentLevelRecoveryValidationError, match="changed"):
        ContentLevelRecovery(database).recover(
            report, tmp_path / "should-not-exist.sqlite3"
        )
