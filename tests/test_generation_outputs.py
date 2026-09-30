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
    GenerationOutput,
    GenerationOutputCollector,
    MissingGenerationOutputError,
    UnexpectedGenerationOutputError,
    generation_output_identity,
)
from comfyreview.providers import LocalGenerationOutputSource
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
        {"output_bindings": [{"role": "primary", "node_id": "save"}]},
    )
    repository = SqliteGenerationOutputRepository(database_path)
    output = GenerationOutput(
        "image-1", "primary", "save", 0, tmp_path / "image.png", "hash"
    )

    assert repository.expected_bindings("generation-1") == (
        CompiledOutputBinding("primary", "save"),
    )
    assert repository.save_outputs("generation-1", (output,)) == (output,)
    assert repository.save_outputs("generation-1", (output,)) == (output,)
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
