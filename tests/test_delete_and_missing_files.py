from pathlib import Path

import pytest

from comfyreview.application import (
    OutputImageReference,
    OutputPair,
    ReviewImage,
    ReviewMutationError,
    ReviewRecord,
    ReviewService,
    StoredReview,
    SubmitReviewCommand,
)
from comfyreview.providers import OutputFileUrlMapper
from services.output_file_service import (
    InvalidOutputPathError,
    OutputFileService,
    OutputMutationError,
)


class _FailingReviewRepository:
    def append(self, record: ReviewRecord) -> StoredReview:
        del record
        raise OSError("database is read-only")


class _ImageResolver:
    def __init__(self, png_path: Path, json_path: Path) -> None:
        self._png_path = png_path
        self._json_path = json_path

    def resolve(self, reference: OutputImageReference) -> ReviewImage:
        assert reference.image_uid == "image"
        return ReviewImage(
            pair=OutputPair(self._png_path, self._json_path),
            model_branch="model",
            checkpoint="checkpoint",
            combo_key="combo",
            steps=None,
            cfg=None,
            sampler=None,
            scheduler=None,
            denoise=None,
            loras_json="[]",
            positive_prompt="",
            negative_prompt="",
            image_uid="image",
            generation_uid="generation",
        )


def test_delete_keeps_files_when_rating_write_fails(tmp_path: Path) -> None:
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")

    service = ReviewService(
        image_resolver=_ImageResolver(png_path, json_path),
        reviews=_FailingReviewRepository(),
        deletions=OutputFileService(
            output_root=tmp_path,
            trash_root=tmp_path / "_trash",
        ),
        preserve_deleted_files=False,
    )

    with pytest.raises(ReviewMutationError, match="canonical_write"):
        service.submit(
            SubmitReviewCommand(
                image=OutputImageReference(image_uid="image"),
                rating=None,
                delete=True,
            )
        )

    assert png_path.is_file()
    assert json_path.is_file()


def test_output_file_url_mapper_rejects_missing_and_escaped_files(
    tmp_path: Path,
) -> None:
    mapper = OutputFileUrlMapper(tmp_path)
    existing = tmp_path / "character" / "image.png"
    existing.parent.mkdir()
    existing.write_bytes(b"png")

    assert mapper.existing_url(existing) == "/files/character/image.png"
    assert mapper.existing_url(tmp_path / "missing.png") == ""
    assert mapper.to_url(tmp_path.parent / "escaped.png") == ""
    assert mapper.url_exists("/files/../escaped.png") is False


def test_output_pair_rejects_path_outside_output_root(tmp_path):
    output_root = tmp_path / "output"
    output_root.mkdir()
    outside_png = tmp_path / "outside.png"
    outside_json = tmp_path / "outside.json"
    outside_png.write_bytes(b"png")
    outside_json.write_text("{}", encoding="utf-8")
    service = OutputFileService(
        output_root=output_root,
        trash_root=output_root / "_trash",
    )

    with pytest.raises(InvalidOutputPathError, match="outside OUTPUT_ROOT"):
        service.resolve_pair(
            png_path=str(outside_png),
            json_path=str(outside_json),
        )


def test_delete_staging_restores_png_when_sidecar_move_fails(
    tmp_path, monkeypatch
):
    output_root = tmp_path / "output"
    output_root.mkdir()
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    service = OutputFileService(
        output_root=output_root,
        trash_root=output_root / "_trash",
    )
    pair = service.resolve_pair(
        png_path=str(png_path), json_path=str(json_path)
    )
    real_move = __import__("shutil").move
    calls = 0

    def fail_second_move(source, destination):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("sidecar move failed")
        return real_move(source, destination)

    monkeypatch.setattr(
        "services.output_file_service.shutil.move", fail_second_move
    )

    with pytest.raises(OutputMutationError, match="Could not stage"):
        service.stage(pair)

    assert png_path.is_file()
    assert json_path.is_file()
