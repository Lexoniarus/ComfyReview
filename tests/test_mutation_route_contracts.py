"""HTTP-boundary contracts for review, curation, and Arena mutations."""

from __future__ import annotations

import importlib
import sqlite3
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from comfyreview.application import (
    ArenaMutationError,
    ArenaResult,
    ArenaValidationError,
    InvalidOutputPathError,
    OutputPairNotFoundError,
    ReviewMutationError,
    ReviewResult,
    ReviewService,
    ReviewValidationError,
    SubmitReviewCommand,
)
from comfyreview.providers import LocalOutputImageCatalog
from comfyreview.repositories.sqlite import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)
from models import RatedItem
from services.output_file_service import OutputFileService
from tests.schema_helpers import initialize_legacy_database

arena_router = importlib.import_module("routers.arena_router")
index_router = importlib.import_module("routers.index_router")
top_router = importlib.import_module("routers.top_router")


class _OutputImageCatalog:
    def __init__(self, items: list[RatedItem]) -> None:
        self._items = items

    def list_images(self) -> tuple[RatedItem, ...]:
        return tuple(self._items)


class _RouteReviewService:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        if self._error is not None:
            raise self._error
        return ReviewResult(
            review_id=1,
            run=1,
            deleted=command.delete,
            job_id=1,
        )


class _RouteArenaService:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    def record_decision(self, command):
        if self._error is not None:
            raise self._error
        return ArenaResult(
            match_uid="match",
            winner_image_uid=(
                command.left_image_uid
                if command.winner_side == "left"
                else command.right_image_uid
            ),
            winner_rating=10,
            loser_rating=1,
        )


def _request(
    *,
    items: list[RatedItem] | None = None,
    review_service: object | None = None,
    arena_service: object | None = None,
) -> Request:
    container = SimpleNamespace(
        output_images=_OutputImageCatalog(items or []),
        review_service=review_service or _RouteReviewService(),
        arena_service=arena_service or _RouteArenaService(),
    )
    application = SimpleNamespace(
        state=SimpleNamespace(container=container),
    )
    return Request({"type": "http", "app": application})


def _review_form(
    png_path: Path,
    json_path: Path,
    *,
    rating: int = 5,
) -> dict[str, object]:
    return {
        "rating": rating,
        "combo_key": "client-combo",
        "model_branch": "client-model",
        "checkpoint": "client-checkpoint",
        "json_path": str(json_path),
        "png_path": str(png_path),
    }


def _call_review(
    form: dict[str, object],
    *,
    review_service: object,
):
    rating = form["rating"]
    assert isinstance(rating, int)
    return index_router.rate(
        request=_request(review_service=review_service),
        rating=rating,
        deleted=None,
        delete=None,
        combo_key=str(form["combo_key"]),
        model_branch=str(form["model_branch"]),
        checkpoint=str(form["checkpoint"]),
        json_path=str(form["json_path"]),
        png_path=str(form["png_path"]),
        sampler="client-sampler",
        scheduler="client-scheduler",
        steps="999",
        cfg="999",
        denoise="999",
        loras_json='[{"client":true}]',
        filter_unrated=None,
        filter_model=None,
        filter_subdir=None,
        filter_scope=None,
        filter_character=None,
        filter_set_key=None,
    )


@pytest.mark.parametrize(
    ("error", "expected_status"),
    [
        (ReviewValidationError("invalid"), 400),
        (InvalidOutputPathError("outside"), 400),
        (OutputPairNotFoundError("missing"), 404),
        (ReviewMutationError("failed"), 500),
    ],
)
def test_review_route_maps_application_errors(
    tmp_path: Path,
    error: Exception,
    expected_status: int,
) -> None:
    with pytest.raises(HTTPException) as caught:
        _call_review(
            _review_form(tmp_path / "image.png", tmp_path / "image.json"),
            review_service=_RouteReviewService(error),
        )

    assert caught.value.status_code == expected_status
    assert caught.value.detail == str(error)


def test_review_route_ignores_client_metadata_and_uses_sidecar(
    tmp_path: Path,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text(
        """{
            "checkpoint": "server-checkpoint",
            "model_branch": "server-model",
            "combo_key": "server-combo",
            "steps": 24,
            "cfg": 6.5,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 0.8,
            "pos_prompt": "server positive",
            "neg_prompt": "server negative"
        }""",
        encoding="utf-8",
    )
    ratings_path = tmp_path / "ratings.sqlite3"
    prompts_path = tmp_path / "prompt_tokens.sqlite3"
    queue_path = tmp_path / "mv_jobs.sqlite3"
    initialize_legacy_database("ratings", ratings_path)
    initialize_legacy_database("prompt_tokens", prompts_path)
    initialize_legacy_database("mv_queue", queue_path)
    catalog = LocalOutputImageCatalog(output_root)
    service = ReviewService(
        image_resolver=catalog,
        reviews=SqliteReviewRepository(ratings_path),
        prompts=SqlitePromptRepository(prompts_path),
        jobs=LegacyProjectionJobQueue(queue_path),
        deletions=OutputFileService(
            output_root=output_root,
            trash_root=output_root / "_trash",
        ),
        preserve_deleted_files=True,
    )

    response = _call_review(
        _review_form(png_path, json_path, rating=8),
        review_service=service,
    )

    assert response.status_code == 303
    with sqlite3.connect(ratings_path) as connection:
        row = connection.execute(
            """
            SELECT model_branch, checkpoint, combo_key, steps, cfg, sampler,
                   scheduler, denoise, loras_json, pos_prompt, neg_prompt
            FROM ratings
            """
        ).fetchone()
    assert row == (
        "server-model",
        "server-checkpoint",
        "server-combo",
        24,
        6.5,
        "euler",
        "normal",
        0.8,
        "[]",
        "server positive",
        "server negative",
    )


def test_top_delete_route_maps_mutation_error(tmp_path: Path) -> None:
    with pytest.raises(HTTPException) as caught:
        top_router.top_delete(
            request=_request(
                review_service=_RouteReviewService(
                    ReviewMutationError("failed")
                )
            ),
            json_path=str(tmp_path / "image.json"),
            png_path=str(tmp_path / "image.png"),
            combo_key="client-combo",
            model_branch="client-model",
            checkpoint="client-checkpoint",
            filter_model="",
            filter_subdir="",
            filter_mode="top",
            filter_set_key="",
        )

    assert caught.value.status_code == 500


def test_curation_route_returns_400_for_unknown_set(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    output_root = tmp_path / "output"
    output_root.mkdir()
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(top_router, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(top_router, "CURATION_SET_KEYS", ("scene",))
    monkeypatch.setattr(
        top_router,
        "CURATION_DB_PATH",
        tmp_path / "curation.sqlite3",
    )

    with pytest.raises(HTTPException) as caught:
        top_router.assign_set(
            png_path=str(png_path),
            json_path=str(json_path),
            set_key="unknown",
            model="",
            mode="top",
            subdir="",
            view_set_key="",
        )

    assert caught.value.status_code == 400


def test_arena_route_maps_validation_and_mutation_errors(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    del monkeypatch, tmp_path
    with pytest.raises(HTTPException) as caught:
        arena_router.arena_result(
            request=_request(
                arena_service=_RouteArenaService(
                    ArenaValidationError("invalid")
                )
            ),
            winner_side="invalid",
            left_image_uid="left",
            right_image_uid="right",
            model="",
            subdir="",
            mode="top",
            set_key="",
        )
    assert caught.value.status_code == 400

    with pytest.raises(HTTPException) as caught:
        arena_router.arena_result(
            request=_request(
                arena_service=_RouteArenaService(ArenaMutationError("failed"))
            ),
            winner_side="left",
            left_image_uid="left",
            right_image_uid="right",
            model="",
            subdir="",
            mode="top",
            set_key="",
        )
    assert caught.value.status_code == 500
