"""HTTP contract tests for canonical review mutations."""

from __future__ import annotations

import importlib
import inspect
from types import SimpleNamespace

from starlette.requests import Request

from comfyreview.application import ReviewResult, SubmitReviewCommand

index_router = importlib.import_module("routers.index_router")
top_router = importlib.import_module("routers.top_router")


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
        return ReviewResult(1, 1, command.delete)


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
        image_uid="image",
        json_path="",
        png_path="",
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
        json_path="",
        png_path="",
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
