"""Behavior tests for canonical curation and reversible file moves."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from comfyreview.application import (
    AssignCurationCommand,
    CurationAssignment,
    CurationImage,
    CurationMutationError,
    CurationResult,
    CurationService,
    CurationValidationError,
    InvalidOutputPathError,
)
from comfyreview.providers import LocalCurationFileManager
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteCurationRepository,
)


class _StagedMove:
    def __init__(self, *, rollback_error: Exception | None = None) -> None:
        self.png_path = Path("new.png")
        self.json_path: Path | None = None
        self.rollback_error = rollback_error
        self.rolled_back = False

    def rollback(self) -> None:
        self.rolled_back = True
        if self.rollback_error is not None:
            raise self.rollback_error


class _CurationFiles:
    def __init__(self, staged: _StagedMove) -> None:
        self.staged = staged

    def stage_move(
        self,
        image: CurationImage,
        set_key: str | None,
    ) -> _StagedMove:
        assert image.image_uid == "image"
        assert set_key == "scene"
        return self.staged


class _CurationRepository:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.assignment: CurationAssignment | None = None

    def get_live_image(self, image_uid: str) -> CurationImage:
        assert image_uid == "image"
        return CurationImage("image", Path("old.png"), None)

    def assign(self, assignment: CurationAssignment) -> CurationResult:
        self.assignment = assignment
        if self.error is not None:
            raise self.error
        return CurationResult(
            assignment.image_uid,
            assignment.png_path,
            assignment.json_path,
            assignment.set_key,
        )


def test_curation_service_assigns_by_stable_image_identity() -> None:
    staged = _StagedMove()
    repository = _CurationRepository()
    service = CurationService(
        repository=repository,
        files=_CurationFiles(staged),
        allowed_set_keys=("scene",),
    )

    result = service.assign(AssignCurationCommand("image", "scene"))

    assert result.image_uid == "image"
    assert result.set_key == "scene"
    assert repository.assignment is not None
    assert not staged.rolled_back


@pytest.mark.parametrize(
    "command",
    (
        AssignCurationCommand("", "scene"),
        AssignCurationCommand("image", "unknown"),
    ),
)
def test_curation_service_rejects_invalid_commands(
    command: AssignCurationCommand,
) -> None:
    service = CurationService(
        repository=_CurationRepository(),
        files=_CurationFiles(_StagedMove()),
        allowed_set_keys=("scene",),
    )

    with pytest.raises(CurationValidationError):
        service.assign(command)


def test_curation_service_rolls_back_after_database_failure() -> None:
    staged = _StagedMove()
    service = CurationService(
        repository=_CurationRepository(RuntimeError("database failed")),
        files=_CurationFiles(staged),
        allowed_set_keys=("scene",),
    )

    with pytest.raises(CurationMutationError, match="persist"):
        service.assign(AssignCurationCommand("image", "scene"))

    assert staged.rolled_back


def test_curation_service_surfaces_failed_compensation() -> None:
    staged = _StagedMove(rollback_error=RuntimeError("rollback failed"))
    service = CurationService(
        repository=_CurationRepository(RuntimeError("database failed")),
        files=_CurationFiles(staged),
        allowed_set_keys=("scene",),
    )

    with pytest.raises(CurationMutationError, match="rollback also failed"):
        service.assign(AssignCurationCommand("image", "scene"))


def _seed_image(database_path: Path, png_path: Path) -> None:
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('pos', 'pos', 'portrait')"
        )
        positive_id = int(
            connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        )
        connection.execute(
            "INSERT INTO prompts(scope, prompt_hash, text) "
            "VALUES ('neg', 'neg', '')"
        )
        negative_id = int(
            connection.execute("SELECT last_insert_rowid()").fetchone()[0]
        )
        cursor = connection.execute(
            """
            INSERT INTO generations(
                generation_uid, model_branch, checkpoint, combo_key,
                loras_json, positive_prompt_id, negative_prompt_id
            )
            VALUES ('generation', 'model', 'checkpoint', 'combo', '[]', ?, ?)
            """,
            (positive_id, negative_id),
        )
        generation_id = cursor.lastrowid
        assert generation_id is not None
        connection.execute(
            """
            INSERT INTO images(
                image_uid, generation_id, output_node_id, output_index,
                png_path, json_path
            )
            VALUES ('image', ?, 'node', 0, ?, NULL)
            """,
            (generation_id, str(png_path)),
        )


def test_curation_moves_sidecarless_image_and_commits_paths(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    source = output_root / "playground" / "Alice" / "image.png"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"png")
    collision = source.parent / "scene" / "image.png"
    collision.parent.mkdir(parents=True)
    collision.write_bytes(b"existing")
    database_path = tmp_path / "comfyreview.sqlite3"
    _seed_image(database_path, source)
    service = CurationService(
        repository=SqliteCurationRepository(database_path),
        files=LocalCurationFileManager(output_root),
        allowed_set_keys=("scene",),
    )

    result = service.assign(AssignCurationCommand("image", "scene"))

    assert result.png_path.name == "image_mv1.png"
    assert result.png_path.read_bytes() == b"png"
    assert result.json_path is None
    assert not source.exists()
    with sqlite3.connect(database_path) as connection:
        row = connection.execute(
            """
            SELECT image.png_path, assignment.set_key
            FROM images AS image
            JOIN curation_assignments AS assignment
                ON assignment.image_id = image.id
            WHERE image.image_uid = 'image'
            """
        ).fetchone()
    assert row == (str(result.png_path), "scene")


def test_local_curation_move_rejects_path_escape(tmp_path: Path) -> None:
    outside = tmp_path / "outside.png"
    outside.write_bytes(b"png")
    manager = LocalCurationFileManager(tmp_path / "output")

    with pytest.raises(InvalidOutputPathError):
        manager.stage_move(CurationImage("image", outside, None), "scene")
