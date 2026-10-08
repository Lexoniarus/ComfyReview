"""Behavior and integration tests for native multi-output collection."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    CollectedOutputFile,
    ComfyUiOutputDescriptor,
    CompiledOutputBinding,
    DuplicateGenerationOutputError,
    GenerationGeometryPolicy,
    GenerationOutput,
    GenerationOutputCollector,
    GenerationOutputError,
    GenerationOutputRecoveryPlan,
    GenerationOutputRecoveryService,
    ImageGeometrySource,
    MissingGenerationOutputError,
    UnexpectedGenerationOutputError,
    generation_output_identity,
)
from comfyreview.providers import (
    LocalGenerationOutputRecoverySource,
    LocalGenerationOutputSource,
)
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGenerationOutputRepository,
)


class _ComfyUi:
    def __init__(self, outputs: tuple[ComfyUiOutputDescriptor, ...]) -> None:
        self.outputs = outputs

    def fetch_outputs(self, prompt_id):
        assert prompt_id == "prompt-1"
        return self.outputs

    def submit(self, compiled_graph):
        raise AssertionError(compiled_graph)

    def get_status(self, prompt_id):
        raise AssertionError(prompt_id)

    def wait_or_watch(
        self, prompt_id, *, timeout_seconds, poll_interval_seconds=0.5
    ):
        raise AssertionError(prompt_id)

    def discover_capabilities(self):
        raise AssertionError


class _Source:
    def resolve(self, descriptor):
        return CollectedOutputFile(
            Path(f"output/{descriptor.filename}"),
            f"hash-{descriptor.filename}",
        )


class _Repository:
    def __init__(self, bindings) -> None:
        self.bindings = bindings
        self.saved: tuple[GenerationOutput, ...] | None = None

    def expected_bindings(self, generation_uid):
        assert generation_uid == "generation-1"
        return self.bindings

    def save_outputs(self, generation_uid, outputs):
        assert generation_uid == "generation-1"
        self.saved = outputs
        return outputs

    def outputs_complete(self, generation_uid):
        assert generation_uid == "generation-1"
        return self.saved is not None

    def recovery_plan(self, generation_uid):
        assert generation_uid == "generation-1"
        return GenerationOutputRecoveryPlan(
            "recovery",
            "generation-1",
            self.bindings,
        )


class _Projection:
    def __init__(self) -> None:
        self.sources: list[ImageGeometrySource] = []

    def project(self, source: ImageGeometrySource):
        self.sources.append(source)
        return GenerationGeometryPolicy().classify(source.image_uid, 720, 1080)


class _RecoverySource:
    def discover(self, plan):
        assert plan.filename_prefix == "generation-1"
        return (_descriptor("save", 0, "generation-1_00001_.png"),)


def _descriptor(
    node_id: str, index: int, filename: str
) -> ComfyUiOutputDescriptor:
    return ComfyUiOutputDescriptor(node_id, index, filename, "", "output")


def test_output_collector_maps_expected_nodes_and_actual_batch_indexes() -> (
    None
):
    repository = _Repository(
        (
            CompiledOutputBinding("primary", "save-a"),
            CompiledOutputBinding("detail", "save-b"),
        )
    )
    projection = _Projection()
    collector = GenerationOutputCollector(
        comfyui=_ComfyUi(
            (
                _descriptor("save-a", 0, "a.png"),
                _descriptor("save-a", 1, "b.png"),
                _descriptor("save-b", 0, "c.png"),
            )
        ),
        source=_Source(),
        repository=repository,
        image_geometry=projection,
    )

    outputs = collector.collect("generation-1", "prompt-1")

    assert [
        (item.role, item.node_id, item.output_index) for item in outputs
    ] == [
        ("primary", "save-a", 0),
        ("primary", "save-a", 1),
        ("detail", "save-b", 0),
    ]
    assert outputs[0].image_uid == generation_output_identity(
        "generation-1", "save-a", 0, "hash-a.png"
    )
    assert projection.sources == [
        ImageGeometrySource(item.image_uid, item.path) for item in outputs
    ]


@pytest.mark.parametrize(
    ("bindings", "outputs", "error"),
    (
        ((), (), MissingGenerationOutputError),
        (
            (
                CompiledOutputBinding("primary", "save"),
                CompiledOutputBinding("detail", "save"),
            ),
            (),
            DuplicateGenerationOutputError,
        ),
        (
            (CompiledOutputBinding("primary", "save"),),
            (_descriptor("other", 0, "a.png"),),
            UnexpectedGenerationOutputError,
        ),
        (
            (CompiledOutputBinding("primary", "save"),),
            (
                _descriptor("save", 0, "a.png"),
                _descriptor("save", 0, "a.png"),
            ),
            DuplicateGenerationOutputError,
        ),
        (
            (
                CompiledOutputBinding("primary", "save-a"),
                CompiledOutputBinding("detail", "save-b"),
            ),
            (_descriptor("save-a", 0, "a.png"),),
            MissingGenerationOutputError,
        ),
    ),
)
def test_output_collector_rejects_invalid_provider_results(
    bindings,
    outputs,
    error,
) -> None:
    with pytest.raises(error):
        GenerationOutputCollector(
            comfyui=_ComfyUi(outputs),
            source=_Source(),
            repository=_Repository(bindings),
        ).collect("generation-1", "prompt-1")


def test_generation_output_identity_does_not_depend_on_path() -> None:
    assert generation_output_identity("generation", "save", 2, "hash") == (
        generation_output_identity("generation", "save", 2, "hash")
    )


def test_output_collector_reports_prior_atomic_collection() -> None:
    repository = _Repository((CompiledOutputBinding("primary", "save"),))
    collector = GenerationOutputCollector(
        comfyui=_ComfyUi(()),
        source=_Source(),
        repository=repository,
    )

    assert collector.outputs_complete("generation-1") is False
    repository.saved = (
        GenerationOutput(
            "image-1",
            "primary",
            "save",
            0,
            Path("output/image.png"),
            "hash",
        ),
    )
    assert collector.outputs_complete("generation-1") is True
    assert generation_output_identity("generation", "save", 2, "hash") != (
        generation_output_identity("generation", "save", 3, "hash")
    )


def test_local_output_source_validates_boundary_and_hashes_content(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    image_path = output_root / "set" / "image.png"
    image_path.parent.mkdir(parents=True)
    image_path.write_bytes(b"pixels")
    source = LocalGenerationOutputSource(output_root)

    result = source.resolve(
        ComfyUiOutputDescriptor("save", 0, "image.png", "set", "output")
    )

    assert result.path == image_path
    assert result.content_hash == hashlib.sha256(b"pixels").hexdigest()
    with pytest.raises(RuntimeError, match="storage type"):
        source.resolve(
            ComfyUiOutputDescriptor("save", 0, "image.png", "set", "temp")
        )
    with pytest.raises(RuntimeError, match="escapes"):
        source.resolve(
            ComfyUiOutputDescriptor("save", 0, "outside.png", "../", "output")
        )
    with pytest.raises(RuntimeError, match="missing"):
        source.resolve(
            ComfyUiOutputDescriptor("save", 0, "missing.png", "set", "output")
        )


def test_local_output_recovery_source_requires_one_exact_png(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    directory = output_root / "playground" / "Hero"
    directory.mkdir(parents=True)
    expected = directory / "generation-1_00001_.png"
    expected.write_bytes(b"png")
    (directory / "other.png").write_bytes(b"other")
    source = LocalGenerationOutputRecoverySource(output_root)
    plan = GenerationOutputRecoveryPlan(
        "playground/Hero",
        "generation-1",
        (CompiledOutputBinding("primary", "save"),),
    )

    descriptors = source.discover(plan)

    assert descriptors == (
        ComfyUiOutputDescriptor(
            "save",
            0,
            expected.name,
            "playground/Hero",
            "output",
        ),
    )
    (directory / "generation-1_00002_.png").write_bytes(b"duplicate")
    with pytest.raises(DuplicateGenerationOutputError, match="ambiguous"):
        source.discover(plan)
    with pytest.raises(GenerationOutputError, match="escapes"):
        source.discover(
            GenerationOutputRecoveryPlan(
                "../outside",
                "generation-1",
                plan.bindings,
            )
        )


def test_output_recovery_uses_canonical_collector_mapping() -> None:
    repository = _Repository((CompiledOutputBinding("primary", "save"),))
    collector = GenerationOutputCollector(
        comfyui=_ComfyUi(()),
        source=_Source(),
        repository=repository,
    )

    outputs = GenerationOutputRecoveryService(
        source=_RecoverySource(),
        repository=repository,
        collector=collector,
    ).recover("generation-1")

    assert outputs == repository.saved
    assert outputs[0].role == "primary"


def _generation(database_path: Path, metadata: object) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.executemany(
            "INSERT INTO prompts(scope, prompt_hash, text) VALUES (?, ?, ?)",
            (("pos", "pos", "hero"), ("neg", "neg", "blur")),
        )
        connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                loras_json, positive_prompt_id, negative_prompt_id,
                source, raw_metadata_json, status
            ) VALUES (
                'generation-1', 'sdxl', '', '', '[]', 1, 2,
                'native_comfyui', ?, 'completed'
            )
            """,
            (json.dumps(metadata),),
        )


def test_sqlite_output_repository_is_idempotent_and_detects_conflicts(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _generation(
        database_path,
        {
            "output_bindings": [{"role": "primary", "node_id": "save"}],
            "output_policy": {
                "output_subdirectory": "playground/Hero",
                "filename_prefix": "generation-1",
            },
        },
    )
    repository = SqliteGenerationOutputRepository(database_path)
    output = GenerationOutput(
        "image-1", "primary", "save", 0, tmp_path / "image.png", "hash"
    )

    assert repository.expected_bindings("generation-1") == (
        CompiledOutputBinding("primary", "save"),
    )
    assert repository.recovery_plan("generation-1") == (
        GenerationOutputRecoveryPlan(
            "playground/Hero",
            "generation-1",
            (CompiledOutputBinding("primary", "save"),),
        )
    )
    assert repository.save_outputs("generation-1", (output,)) == (output,)
    assert repository.save_outputs("generation-1", (output,)) == (output,)
    assert repository.outputs_complete("generation-1") is True
    with sqlite3.connect(database_path) as connection:
        assert connection.execute(
            "SELECT output_role, content_hash FROM images"
        ).fetchone() == ("primary", "hash")
    with pytest.raises(RuntimeError, match="identity conflict"):
        repository.save_outputs(
            "generation-1",
            (
                GenerationOutput(
                    "other", "primary", "save", 0, output.path, "hash"
                ),
            ),
        )
    with pytest.raises(KeyError, match="Unknown generation"):
        repository.expected_bindings("missing")


def test_sqlite_output_repository_rejects_invalid_binding_payload(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _generation(database_path, {"output_bindings": {}})

    with pytest.raises(RuntimeError, match="bindings are invalid"):
        SqliteGenerationOutputRepository(database_path).expected_bindings(
            "generation-1"
        )


def test_output_save_initializes_but_never_replaces_current_catalog_composition(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _generation(
        database_path,
        {"output_bindings": [{"role": "primary", "node_id": "save"}]},
    )
    with sqlite3.connect(database_path) as connection:
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                component_uid, kind, component_key, name, tags, notes
            ) VALUES ('character-a', 'character', 'character-a',
                      'Aiko', '[]', '')
            RETURNING id
            """
        ).fetchone()[0]
        revision_id = connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('character-a-1', ?, 1, 'Aiko', '', 'character-a-1')
            RETURNING id
            """,
            (component_id,),
        ).fetchone()[0]
        composition_id = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('generation-composition') RETURNING id"
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, 'character', 0)
            """,
            (composition_id, revision_id),
        )
        connection.execute(
            "UPDATE generations SET prompt_composition_id = ? WHERE id = 1",
            (composition_id,),
        )

    repository = SqliteGenerationOutputRepository(database_path)
    output = GenerationOutput(
        "image-1", "primary", "save", 0, tmp_path / "image.png", "hash"
    )
    repository.save_outputs("generation-1", (output,))

    with sqlite3.connect(database_path) as connection:
        generated_composition_id = connection.execute(
            "SELECT composition_id FROM current_image_catalog_compositions"
        ).fetchone()[0]
        editorial_composition_id = connection.execute(
            """
            INSERT INTO image_catalog_compositions(
                composition_uid, image_id, version, source
            ) VALUES ('editorial-image-1', 1, 2, 'editorial')
            RETURNING id
            """
        ).fetchone()[0]
        connection.execute(
            """
            INSERT INTO image_catalog_composition_revisions(
                composition_id, revision_id, position
            ) VALUES (?, ?, 0)
            """,
            (editorial_composition_id, revision_id),
        )
        connection.execute(
            """
            UPDATE current_image_catalog_compositions
            SET composition_id = ? WHERE image_id = 1
            """,
            (editorial_composition_id,),
        )

    repository.save_outputs("generation-1", (output,))

    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute(
                "SELECT composition_id FROM current_image_catalog_compositions"
            ).fetchone()[0]
            == editorial_composition_id
        )
        assert editorial_composition_id != generated_composition_id


def test_sqlite_output_repository_requires_every_expected_node(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    _generation(
        database_path,
        {
            "output_bindings": [
                {"role": "primary", "node_id": "save-a"},
                {"role": "detail", "node_id": "save-b"},
            ]
        },
    )
    repository = SqliteGenerationOutputRepository(database_path)

    assert repository.outputs_complete("generation-1") is False
    repository.save_outputs(
        "generation-1",
        (
            GenerationOutput(
                "image-1",
                "primary",
                "save-a",
                0,
                tmp_path / "image.png",
                "hash",
            ),
        ),
    )
    assert repository.outputs_complete("generation-1") is False
