from pathlib import Path

import pytest

from services import file_urls
from services import rating_submission_service
from services.playground_hub_service import _attach_urls
from services.combo_prompts import rebuild


def test_delete_keeps_files_when_rating_write_fails(tmp_path, monkeypatch):
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")

    monkeypatch.setattr(
        rating_submission_service,
        "_read_meta_for_rating",
        lambda _path: ({}, "", ""),
    )

    def fail_write(**_kwargs):
        raise OSError("database is read-only")

    monkeypatch.setattr(rating_submission_service, "_write_rating_row", fail_write)

    with pytest.raises(OSError, match="read-only"):
        rating_submission_service.submit_rating(
            ratings_db_path=tmp_path / "ratings.sqlite3",
            prompt_tokens_db_path=tmp_path / "prompt_tokens.sqlite3",
            mv_queue_db_path=tmp_path / "mv_jobs.sqlite3",
            output_root=tmp_path,
            trash_root=tmp_path / "_trash",
            soft_delete_to_trash=False,
            rating=None,
            deleted=None,
            delete=1,
            combo_key="",
            model_branch="",
            checkpoint="",
            json_path=str(json_path),
            png_path=str(png_path),
            sampler=None,
            scheduler=None,
            steps=None,
            cfg=None,
            denoise=None,
            loras_json=None,
        )

    assert png_path.is_file()
    assert json_path.is_file()


def test_existing_png_path_to_url_rejects_missing_file(tmp_path, monkeypatch):
    monkeypatch.setattr(file_urls, "OUTPUT_ROOT", tmp_path)
    existing = tmp_path / "character" / "image.png"
    existing.parent.mkdir()
    existing.write_bytes(b"png")

    assert file_urls.existing_png_path_to_url(str(existing)) == "/files/character/image.png"
    assert file_urls.existing_png_path_to_url(str(tmp_path / "missing.png")) == ""


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

    result = _attach_urls(rows, png_to_url=lambda path: f"url:{Path(path).name}")

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
            error.winerror = 32
            raise error
        real_replace(src, dst)

    monkeypatch.setattr(rebuild.os, "replace", flaky_replace)

    rebuild._replace_database_with_retry(source, target, attempts=3, delay_seconds=0)

    assert calls == 3
    assert target.read_bytes() == b"new"
