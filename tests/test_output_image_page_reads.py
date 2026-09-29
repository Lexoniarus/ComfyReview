"""Verify page-read services consume the output catalog port."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application import OutputImageReadModel
from services import arena_page_service, gallery_view_service
from services.context_filters import GalleryContext
from services.review_page_service import build_review_page_context


class _RecordingOutputImageCatalog:
    def __init__(self, images: tuple[OutputImageReadModel, ...] = ()) -> None:
        self._images = images
        self.calls = 0

    def list_images(self) -> tuple[OutputImageReadModel, ...]:
        self.calls += 1
        return self._images


class _RatingsConnection:
    def close(self) -> None:
        return None


class _LabelMatcher:
    def resolve(
        self,
        _prompt_text: str,
        *,
        include_lighting: bool,
    ) -> dict[str, object]:
        assert include_lighting
        return {}


def _gallery_context() -> GalleryContext:
    return GalleryContext(model="", subdir="", set_key="", mode="top")


def test_review_page_reads_images_from_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    from services import review_page_service

    catalog = _RecordingOutputImageCatalog()
    monkeypatch.setattr(
        review_page_service,
        "db",
        lambda _path: _RatingsConnection(),
    )
    monkeypatch.setattr(
        review_page_service,
        "get_rated_map",
        lambda _connection: {},
    )

    context = build_review_page_context(
        output_images=catalog,
        ratings_db_path=tmp_path / "ratings.sqlite3",
        playground_db_path=tmp_path / "playground.sqlite3",
        curation_db_path=tmp_path / "curation.sqlite3",
        unrated=1,
        model="",
        subdir="",
        set_key="",
    )

    assert catalog.calls == 1
    assert context["total"] == 0
    assert context["it"] is None


def test_top_page_reads_images_from_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    catalog = _RecordingOutputImageCatalog()
    monkeypatch.setattr(
        gallery_view_service,
        "build_ranked_pool",
        lambda *_args, **_kwargs: ([], {}),
    )
    monkeypatch.setattr(
        gallery_view_service,
        "get_playground_label_matcher",
        lambda _path: _LabelMatcher(),
    )

    view_model = gallery_view_service.build_top_pictures_page(
        output_images=catalog,
        playground_db_path=tmp_path / "playground.sqlite3",
        context=_gallery_context(),
        min_runs=3,
        limit=128,
    )

    assert catalog.calls == 1
    assert view_model["cards"] == []


def test_arena_page_reads_images_from_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    catalog = _RecordingOutputImageCatalog()
    monkeypatch.setattr(
        arena_page_service,
        "ensure_arena_schema",
        lambda _path: None,
    )
    monkeypatch.setattr(
        arena_page_service,
        "build_ranked_pool",
        lambda *_args, **_kwargs: ([], {}),
    )

    view_model = arena_page_service.build_arena_page_context(
        arena_db_path=tmp_path / "arena.sqlite3",
        output_images=catalog,
        playground_db_path=tmp_path / "playground.sqlite3",
        context=_gallery_context(),
        min_runs=3,
        pool_limit=128,
    )

    assert catalog.calls == 1
    assert view_model["left"] is None
    assert view_model["right"] is None
