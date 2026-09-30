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
from services import file_urls
from services.combo_prompts import rebuild
from services.output_file_service import (
    InvalidOutputPathError,
    OutputFileService,
    OutputMutationError,
)
from services.playground_hub_service import _attach_urls


class _FailingReviewRepository:
    def append(self, record: ReviewRecord) -> StoredReview:
        del record
        raise OSError("database is read-only")


class _UnusedJobQueue:
    def request_catchup(self) -> int:
        raise AssertionError("queue must not be called")


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
        jobs=_UnusedJobQueue(),
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


def test_existing_png_path_to_url_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(file_urls, "OUTPUT_ROOT", tmp_path)
    existing = tmp_path / "character" / "image.png"
    existing.parent.mkdir()
    existing.write_bytes(b"png")

    assert (
        file_urls.existing_png_path_to_url(str(existing))
        == "/files/character/image.png"
    )
    assert (
        file_urls.existing_png_path_to_url(str(tmp_path / "missing.png")) == ""
    )


def test_playground_dashboard_drops_missing_thumbnails(tmp_path):
    existing = tmp_path / "existing.png"
    existing.write_bytes(b"png")
    missing = tmp_path / "missing.png"

    rows = [
        {
            "best_png_path": str(missing),
            "best_images": [
                {"png_path": str(missing)},
                {"png_path": str(existing)},
            ],
        }
    ]

    result = _attach_urls(
        rows, png_to_url=lambda path: f"url:{Path(path).name}"
    )

    assert result[0]["best_url"] == ""
    assert result[0]["best_images"] == [
        {"png_path": str(existing), "url": "url:existing.png"}
    ]


def test_combo_database_replace_retries_windows_lock(tmp_path, monkeypatch):
    source = tmp_path / "combo.sqlite3.tmp"
    target = tmp_path / "combo.sqlite3"
    source.write_bytes(b"new")
    target.write_bytes(b"old")
    calls = 0
    real_replace = rebuild.os.replace

    def flaky_replace(src, dst):
        nonlocal calls
        calls += 1
        if calls < 3:
            error = PermissionError("locked")
            error.__dict__["winerror"] = 32
            raise error
        real_replace(src, dst)

    monkeypatch.setattr(rebuild.os, "replace", flaky_replace)

    rebuild._replace_database_with_retry(
        source, target, attempts=3, delay_seconds=0
    )

    assert calls == 3
    assert target.read_bytes() == b"new"


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
