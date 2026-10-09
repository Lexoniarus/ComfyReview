"""Validate immutable application-core local inference contracts."""

from __future__ import annotations

import base64
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from comfyreview.application.local_model_inference import (
    LocalInferenceRequest,
    LocalInferenceResult,
    LocalInferenceUsage,
    LocalModelInferenceError,
)
from comfyreview.application.local_models import LocalModelError

_IMAGE = "data:image/png;base64,AA=="


def test_request_is_immutable_and_conceals_private_inputs() -> None:
    request = LocalInferenceRequest(
        model_id="repo/model",
        user_text="Tell me",
        max_output_tokens=64,
        system_prompt="Help",
        image_data_url=_IMAGE,
    )
    assert request.model_id == "repo/model"
    assert request.image_data_url == _IMAGE
    assert "Tell me" not in repr(request)
    assert "Help" not in repr(request)
    assert "base64" not in repr(request)
    attribute = "model_id"
    with pytest.raises(FrozenInstanceError):
        setattr(request, attribute, "other")


@pytest.mark.parametrize("value", ("", "  ", " model ", None, 1, True))
def test_request_rejects_bad_model_identifiers(value: object) -> None:
    with pytest.raises(ValueError, match="model_id"):
        LocalInferenceRequest(cast(str, value), "query", 50)


@pytest.mark.parametrize("value", ("", "  ", None, 3))
def test_request_rejects_bad_user_text(value: object) -> None:
    with pytest.raises(ValueError, match="user_text"):
        LocalInferenceRequest("model", cast(str, value), 50)


@pytest.mark.parametrize("value", (0, -1, 8193, 3.3, True, "3"))
def test_request_rejects_unbounded_token_limits(value: object) -> None:
    with pytest.raises(ValueError, match="max_output_tokens"):
        LocalInferenceRequest("model", "query", cast(int, value))


@pytest.mark.parametrize("value", ("", " ", 4))
def test_request_rejects_bad_system_prompts(value: object) -> None:
    with pytest.raises(ValueError, match="system_prompt"):
        LocalInferenceRequest(
            "model", "query", 10, system_prompt=cast(str, value)
        )


@pytest.mark.parametrize(
    "value",
    (
        "https://example.org/image.png",
        "data:application/json;base64,AA==",
        "data:image/svg+xml;base64,AA==",
        "data:image/png;base64,",
        "data:image/png;base64,?",
        "data:image/png;base64,YWJ",
        "data:image/png;base64,AA==AAAA",
        "data:image/png;base64,AA==" + "\n",
        23,
    ),
)
def test_request_rejects_malformed_images(value: object) -> None:
    with pytest.raises(ValueError, match="image_data_url"):
        LocalInferenceRequest(
            "model", "query", 10, image_data_url=cast(str, value)
        )


def test_request_rejects_oversized_image_data_urls() -> None:
    image = b"\x00" * (16 * 1024 * 1024 + 1)
    encoded = base64.b64encode(image).decode("ascii")
    with pytest.raises(ValueError, match="size limit"):
        LocalInferenceRequest(
            "model",
            "query",
            10,
            image_data_url=f"data:image/png;base64,{encoded}",
        )
    with pytest.raises(ValueError, match="size limit"):
        LocalInferenceRequest(
            "model",
            "query",
            10,
            image_data_url="data:image/png;base64," + encoded + "AAAA",
        )


def test_request_accepts_supported_raster_data_urls() -> None:
    for subtype in ("png", "jpeg", "webp", "gif"):
        request = LocalInferenceRequest(
            "model",
            "query",
            8192,
            image_data_url=f"data:image/{subtype};base64,AA==",
        )
        assert request.image_data_url is not None


@pytest.mark.parametrize(
    "usage",
    (
        (-1, 2, None),
        (True, 2, None),
        (2, -1, None),
        (2, False, None),
        (2, 3, -1),
        (2, 3, True),
        (2, 3, 4),
    ),
)
def test_usage_rejects_invalid_token_counts(
    usage: tuple[object, object, object],
) -> None:
    with pytest.raises(ValueError):
        LocalInferenceUsage(
            cast(int, usage[0]),
            cast(int, usage[1]),
            cast(int | None, usage[2]),
        )


def test_usage_and_result_are_immutable() -> None:
    usage = LocalInferenceUsage(10, 8, 2)
    result = LocalInferenceResult("a reply", "instance-1", usage)
    assert result.text == "a reply"
    assert result.model_instance_id == "instance-1"
    assert result.usage == usage
    assert "a reply" not in repr(result)
    assert issubclass(LocalModelInferenceError, LocalModelError)
    attribute = "text"
    with pytest.raises(FrozenInstanceError):
        setattr(result, attribute, "modified")


@pytest.mark.parametrize("value", ("", "  ", None, 2))
def test_result_rejects_blank_or_invalid_text(value: object) -> None:
    with pytest.raises(ValueError, match="inference text"):
        LocalInferenceResult(cast(str, value), "instance-1")


@pytest.mark.parametrize("value", ("", " ", " instance ", None, 4))
def test_result_rejects_invalid_instance(value: object) -> None:
    with pytest.raises(ValueError, match="model_instance_id"):
        LocalInferenceResult("reply", cast(str, value))


def test_result_rejects_unvalidated_usage() -> None:
    with pytest.raises(ValueError, match="usage"):
        LocalInferenceResult("reply", "inst", cast(LocalInferenceUsage, {}))
