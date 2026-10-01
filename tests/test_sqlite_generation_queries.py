"""SQLite integration tests for canonical generation lifecycle reads."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGenerationQueryRepository,
)


def test_sqlite_generation_queries_return_provenance_stages_and_outputs(
    tmp_path: Path,
) -> None:
    database_path = _seed_generation_database(tmp_path)
    repository = SqliteGenerationQueryRepository(database_path)

    page = repository.list_generations(
        status="completed",
        offset=0,
        limit=10,
    )
    empty = repository.list_generations(status="running", offset=0, limit=10)
    detail = repository.get_generation("generation-1")

    assert page.total == 1
    assert page.entries[0].blueprint_uid == "default-character"
    assert page.entries[0].blueprint_version == 1
    assert page.entries[0].output_count == 2
    assert empty.total == 0
    assert detail is not None
    assert detail.revision_uids == ("revision-character",)
    assert detail.sampler_stages[0].role == "base_sampler"
    assert [output.output_index for output in detail.outputs] == [0, 1]
    assert repository.get_generation("missing") is None


def test_sqlite_generation_queries_tolerate_legacy_metadata_shapes(
    tmp_path: Path,
) -> None:
    database_path = _seed_generation_database(tmp_path)
    connection = sqlite3.connect(database_path)
    try:
        connection.execute("UPDATE generations SET raw_metadata_json = '[1]'")
        connection.commit()
    finally:
        connection.close()

    summary = (
        SqliteGenerationQueryRepository(database_path)
        .list_generations(status="", offset=0, limit=10)
        .entries[0]
    )

    assert summary.blueprint_uid is None
    assert summary.blueprint_version is None


def _seed_generation_database(tmp_path: Path) -> Path:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    connection = sqlite3.connect(database_path)
    try:
        positive_id = int(
            connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) "
                "VALUES ('pos', 'pos-hash', 'positive') RETURNING id"
            ).fetchone()[0]
        )
        negative_id = int(
            connection.execute(
                "INSERT INTO prompts(scope, prompt_hash, text) "
                "VALUES ('neg', 'neg-hash', 'negative') RETURNING id"
            ).fetchone()[0]
        )
        component_id = int(
            connection.execute(
                "INSERT INTO prompt_components("
                "component_uid, kind, component_key, name, tags, notes"
                ") VALUES ('character-a', 'character', 'a', 'Aiko', '[]', '') "
                "RETURNING id"
            ).fetchone()[0]
        )
        revision_id = int(
            connection.execute(
                "INSERT INTO prompt_revisions("
                "revision_uid, component_id, revision_number, positive_text, "
                "negative_text, content_hash"
                ") VALUES ('revision-character', ?, 1, 'positive', '', 'hash') "
                "RETURNING id",
                (component_id,),
            ).fetchone()[0]
        )
        composition_id = int(
            connection.execute(
                "INSERT INTO prompt_compositions(composition_uid) "
                "VALUES ('composition-1') RETURNING id"
            ).fetchone()[0]
        )
        connection.execute(
            "INSERT INTO prompt_composition_revisions("
            "composition_id, revision_id, slot, position"
            ") VALUES (?, ?, 'character', 0)",
            (composition_id, revision_id),
        )
        generation_id = int(
            connection.execute(
                """
                INSERT INTO generations(
                    generation_uid, model_branch, checkpoint, combo_key,
                    seed, steps, cfg, sampler, scheduler, denoise, loras_json,
                    positive_prompt_id, negative_prompt_id, source,
                    raw_metadata_json, workflow_hash, comfy_prompt_id, status,
                    submitted_at, started_at, completed_at,
                    prompt_composition_id
                ) VALUES (
                    'generation-1', 'anime', 'model.safetensors', 'combo',
                    1, 20, 7.0, 'euler', 'normal', 1.0, '[]', ?, ?,
                    'native_comfyui',
                    '{"blueprint_uid":"default-character","blueprint_version":1}',
                    'graph-hash', 'prompt-1', 'completed', datetime('now'),
                    datetime('now'), datetime('now'), ?
                ) RETURNING id
                """,
                (positive_id, negative_id, composition_id),
            ).fetchone()[0]
        )
        connection.execute(
            """
            INSERT INTO generation_sampler_stages(
                generation_id, node_id, stage_order, role, seed, steps, cfg,
                sampler, scheduler, denoise, source
            ) VALUES (?, '12', 0, 'base_sampler', 1, 20, 7.0,
                      'euler', 'normal', 1.0, 'workflow_compiler')
            """,
            (generation_id,),
        )
        for output_index in (0, 1):
            connection.execute(
                """
                INSERT INTO images(
                    image_uid, generation_id, output_node_id, output_index,
                    png_path, json_path, output_role, content_hash
                ) VALUES (?, ?, '42', ?, ?, NULL, 'primary', ?)
                """,
                (
                    f"image-{output_index}",
                    generation_id,
                    output_index,
                    f"output/image-{output_index}.png",
                    f"hash-{output_index}",
                ),
            )
        connection.commit()
    finally:
        connection.close()
    return database_path
