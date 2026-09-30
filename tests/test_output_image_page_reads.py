"""Verify page-read services consume the output catalog port."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application import (
    ArenaService,
    OutputImageReadModel,
    RankingService,
)
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


class _LabelMatcher:
    def resolve(
        self,
        _prompt_text: str,
        *,
        include_lighting: bool,
    ) -> dict[str, object]:
        assert include_lighting
        return {}


class _RecordingRankingRepository:
    def __init__(self) -> None:
        self.calls = 0

    def list_ranked_images(self):
        self.calls += 1
        return ()


class _EmptyArenaRepository:
    def list_played_directions(self, image_uids):
        del image_uids
        return frozenset()

    def get_competitors(self, left_image_uid, right_image_uid):
        raise AssertionError((left_image_uid, right_image_uid))

    def save_decision(self, decision):
        raise AssertionError(decision)


def _gallery_context() -> GalleryContext:
    return GalleryContext(model="", subdir="", set_key="", mode="top")


def test_review_page_reads_images_from_catalog(
    tmp_path: Path,
) -> None:
    catalog = _RecordingOutputImageCatalog()

    context = build_review_page_context(
        output_images=catalog,
        playground_db_path=tmp_path / "playground.sqlite3",
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
    repository = _RecordingRankingRepository()
    rankings = RankingService(repository)
    monkeypatch.setattr(
        gallery_view_service,
        "get_playground_label_matcher",
        lambda _path: _LabelMatcher(),
    )

    view_model = gallery_view_service.build_top_pictures_page(
        ranking_service=rankings,
        playground_db_path=tmp_path / "playground.sqlite3",
        context=_gallery_context(),
        min_runs=3,
        limit=128,
    )

    assert repository.calls == 2
    assert view_model["cards"] == []


def test_arena_page_reads_images_from_catalog(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repository = _RecordingRankingRepository()
    rankings = RankingService(repository)
    arena = ArenaService(
        rankings=rankings,
        repository=_EmptyArenaRepository(),
    )

    view_model = arena_page_service.build_arena_page_context(
        ranking_service=rankings,
        arena_service=arena,
        playground_db_path=tmp_path / "playground.sqlite3",
        context=_gallery_context(),
        min_runs=3,
        pool_limit=128,
    )

    assert repository.calls == 3
    assert view_model["left"] is None
    assert view_model["right"] is None
