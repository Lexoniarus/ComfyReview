from __future__ import annotations

import importlib
import inspect
import sqlite3
from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request

from comfyreview.application import (
    OutputImageReference,
    ReviewResult,
    ReviewService,
    SubmitReviewCommand,
)
from comfyreview.providers import LocalOutputImageCatalog
from comfyreview.repositories.sqlite import (
    LegacyProjectionJobQueue,
    SqlitePromptRepository,
    SqliteReviewRepository,
)
from services.output_file_service import OutputFileService
from tests.schema_helpers import initialize_legacy_database

index_router = importlib.import_module("routers.index_router")
top_router = importlib.import_module("routers.top_router")


def _create_review_databases(tmp_path: Path) -> tuple[Path, Path, Path]:
    ratings_path = tmp_path / "ratings.sqlite3"
    prompt_tokens_path = tmp_path / "prompt_tokens.sqlite3"
    queue_path = tmp_path / "mv_jobs.sqlite3"
    initialize_legacy_database("ratings", ratings_path)
    initialize_legacy_database("prompt_tokens", prompt_tokens_path)
    initialize_legacy_database("mv_queue", queue_path)
    return ratings_path, prompt_tokens_path, queue_path


def _submit_review(
    *,
    ratings_path: Path,
    prompt_tokens_path: Path,
    queue_path: Path,
    png_path: Path,
    json_path: Path,
    rating: int,
) -> None:
    catalog = LocalOutputImageCatalog(png_path.parent)
    ReviewService(
        image_resolver=catalog,
        reviews=SqliteReviewRepository(ratings_path),
        prompts=SqlitePromptRepository(prompt_tokens_path),
        jobs=LegacyProjectionJobQueue(queue_path),
        deletions=OutputFileService(
            output_root=png_path.parent,
            trash_root=png_path.parent / "_trash",
        ),
        preserve_deleted_files=True,
    ).submit(
        SubmitReviewCommand(
            image=OutputImageReference.from_client_paths(
                png_path=str(png_path),
                json_path=str(json_path),
            ),
            rating=rating,
        )
    )


def test_review_runs_project_prompts_and_coalesce_catchup(
    tmp_path: Path,
) -> None:
    ratings_path, prompt_tokens_path, queue_path = _create_review_databases(
        tmp_path
    )
    png_path = tmp_path / "image.png"
    json_path = tmp_path / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text(
        """{
            "steps": 24,
            "cfg": 6.5,
            "sampler": "euler",
            "scheduler": "normal",
            "denoise": 0.8,
            "checkpoint": "checkpoint-from-sidecar",
            "model_branch": "model-from-sidecar",
            "combo_key": "combo-from-sidecar",
            "pos_prompt": "hero, blue sky",
            "neg_prompt": "blur"
        }""",
        encoding="utf-8",
    )

    _submit_review(
        ratings_path=ratings_path,
        prompt_tokens_path=prompt_tokens_path,
        queue_path=queue_path,
        png_path=png_path,
        json_path=json_path,
        rating=7,
    )
    _submit_review(
        ratings_path=ratings_path,
        prompt_tokens_path=prompt_tokens_path,
        queue_path=queue_path,
        png_path=png_path,
        json_path=json_path,
        rating=9,
    )

    with sqlite3.connect(ratings_path) as connection:
        rows = connection.execute(
            """
            SELECT run, rating, model_branch, checkpoint, combo_key,
                   steps, cfg, sampler, scheduler, denoise, pos_prompt, neg_prompt
            FROM ratings
            ORDER BY run
            """
        ).fetchall()
    assert rows == [
        (
            1,
            7,
            "model-from-sidecar",
            "checkpoint-from-sidecar",
            "combo-from-sidecar",
            24,
            6.5,
            "euler",
            "normal",
            0.8,
            "hero, blue sky",
            "blur",
        ),
        (
            2,
            9,
            "model-from-sidecar",
            "checkpoint-from-sidecar",
            "combo-from-sidecar",
            24,
            6.5,
            "euler",
            "normal",
            0.8,
            "hero, blue sky",
            "blur",
        ),
    ]

    with sqlite3.connect(prompt_tokens_path) as connection:
        token_rows = connection.execute(
            """
            SELECT run, scope, token, rating, deleted
            FROM tokens
            ORDER BY run, id
            """
        ).fetchall()
    assert token_rows == [
        (1, "pos", "hero", 7, 0),
        (1, "pos", "blue sky", 7, 0),
        (1, "neg", "blur", 7, 0),
        (2, "pos", "hero", 9, 0),
        (2, "pos", "blue sky", 9, 0),
        (2, "neg", "blur", 9, 0),
    ]

    with sqlite3.connect(queue_path) as connection:
        queue_rows = connection.execute(
            "SELECT job_type, status FROM mv_jobs ORDER BY id"
        ).fetchall()
    assert queue_rows == [("catchup", "queued")]


def test_review_mutation_routes_keep_form_contracts() -> None:
    rate_parameters = set(inspect.signature(index_router.rate).parameters)
    top_delete_parameters = set(
        inspect.signature(top_router.top_delete).parameters
    )

    assert rate_parameters == {
        "request",
        "rating",
        "deleted",
        "delete",
        "combo_key",
        "model_branch",
        "checkpoint",
        "image_uid",
        "json_path",
        "png_path",
        "sampler",
        "scheduler",
        "steps",
        "cfg",
        "denoise",
        "loras_json",
        "filter_unrated",
        "filter_model",
        "filter_subdir",
        "filter_scope",
        "filter_character",
        "filter_set_key",
    }
    assert top_delete_parameters == {
        "request",
        "image_uid",
        "json_path",
        "png_path",
        "combo_key",
        "model_branch",
        "checkpoint",
        "filter_model",
        "filter_subdir",
        "filter_mode",
        "filter_set_key",
    }


class _SuccessfulReviewService:
    def submit(self, command: SubmitReviewCommand) -> ReviewResult:
        return ReviewResult(1, 1, command.delete, 1)


def _request() -> Request:
    container = SimpleNamespace(review_service=_SuccessfulReviewService())
    application = SimpleNamespace(state=SimpleNamespace(container=container))
    return Request({"type": "http", "app": application})


def test_review_mutation_routes_keep_success_redirects() -> None:

    rate_response = index_router.rate(
        request=_request(),
        rating=8,
        deleted=None,
        delete=None,
        combo_key="combo",
        model_branch="model",
        checkpoint="checkpoint",
        image_uid=None,
        json_path="image.json",
        png_path="image.png",
        sampler=None,
        scheduler=None,
        steps=None,
        cfg=None,
        denoise=None,
        loras_json=None,
        filter_unrated="0",
        filter_model="model",
        filter_subdir="folder",
        filter_scope=None,
        filter_character=None,
        filter_set_key="scene",
    )
    top_response = top_router.top_delete(
        request=_request(),
        image_uid="image",
        json_path="image.json",
        png_path="image.png",
        combo_key="combo",
        model_branch="model",
        checkpoint="checkpoint",
        filter_model="model",
        filter_subdir="folder",
        filter_mode="top",
        filter_set_key="scene",
    )

    assert rate_response.status_code == 303
    assert rate_response.headers["location"] == (
        "/?unrated=0&model=model&subdir=folder&set_key=scene"
    )
    assert top_response.status_code == 303
    assert top_response.headers["location"] == (
        "/top_pictures?model=model&mode=top&subdir=folder&set_key=scene"
    )
