"""Behavior tests for reversible output-file deletion."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application import OutputPair
from services.output_file_service import OutputFileService


def test_stage_and_rollback_supports_png_without_sidecar(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    trash_root = output_root / "_trash"
    output_root.mkdir()
    png_path = output_root / "native.png"
    png_path.write_bytes(b"png")

    service = OutputFileService(
        output_root=output_root,
        trash_root=trash_root,
    )
    staged = service.stage(
        OutputPair(
            png_path=png_path,
            json_path=None,
        )
    )

    assert not png_path.exists()
    assert staged.staged_pair.png_path.is_file()
    assert staged.staged_pair.json_path is None

    staged.rollback()

    assert png_path.is_file()
    assert not staged.staged_pair.png_path.exists()
