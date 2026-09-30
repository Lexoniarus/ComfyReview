"""Tests for server-owned Playground generator state."""

from __future__ import annotations

from pathlib import Path

from comfyreview.repositories.filesystem import (
    PlaygroundGeneratorStateRepository,
)


def _repository(tmp_path: Path) -> PlaygroundGeneratorStateRepository:
    return PlaygroundGeneratorStateRepository(
        head_path=tmp_path / "state" / "head.json",
        preview_path=tmp_path / "state" / "preview.json",
    )


def test_state_repository_round_trips_head_and_preview(tmp_path: Path) -> None:
    repository = _repository(tmp_path)

    repository.save_head({"character_id": "character-1"})
    repository.save_preview(({"draft_id": "draft-1"},))

    assert repository.load_head() == {"character_id": "character-1"}
    assert repository.load_preview() == [{"draft_id": "draft-1"}]

    repository.clear_preview()
    assert repository.load_preview() == []


def test_state_repository_treats_missing_and_invalid_state_as_empty(
    tmp_path: Path,
) -> None:
    repository = _repository(tmp_path)
    assert repository.load_head() == {}
    assert repository.load_preview() == []

    head_path = tmp_path / "state" / "head.json"
    preview_path = tmp_path / "state" / "preview.json"
    head_path.parent.mkdir(parents=True)
    head_path.write_text("[]", encoding="utf-8")
    preview_path.write_text(
        '{"drafts": [1, {"draft_id": "valid"}]}',
        encoding="utf-8",
    )

    assert repository.load_head() == {}
    assert repository.load_preview() == [{"draft_id": "valid"}]
