"""Fake-transport tests for the stateless LM Studio chat boundary."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application.local_model_inference import (
    LocalInferenceProvider,
    LocalInferenceRequest,
    LocalInferenceUsage,
    LocalModelInferenceError,
)
from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)
from comfyreview.providers.lm_studio import LmStudioJsonResponse
from comfyreview.providers.lm_studio_inference import (
    NativeLmStudioInferenceProvider,
)

_IMAGE = "data:image/jpeg;base64,AA=="
_DEFAULT_ITEMS = object()


def _response(
    items: object = _DEFAULT_ITEMS,
    *,
    instance: object = "actual-instance-7",
    stats: object = None,
) -> LmStudioJsonResponse:
    body: dict[str, object] = {
        "model_instance_id": instance,
        "output": (
            [{"type": "message", "content": "response"}]
            if items is _DEFAULT_ITEMS
            else items
        ),
    }
    if stats is not None:
        body["stats"] = stats
    return LmStudioJsonResponse(200, body)


class _Transport:
    def __init__(self, response: LmStudioJsonResponse) -> None:
        self.response = response
        self.calls: list[tuple[str, str, object | None, float]] = []
        self.failure: Exception | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> LmStudioJsonResponse:
        self.calls.append((method, path, payload, timeout_seconds))
        if self.failure is not None:
            raise self.failure
        return self.response


def test_text_request_uses_exact_model_and_is_stateless() -> None:
    transport = _Transport(_response())
    provider: LocalInferenceProvider = NativeLmStudioInferenceProvider(
        transport, request_timeout_seconds=2.5
    )
    result = provider.infer(LocalInferenceRequest("org/exact-model", "Hi", 93))
    assert result.text == "response"
    assert result.model_instance_id == "actual-instance-7"
    assert result.usage is None
    assert transport.calls == [
        (
            "POST",
            "/api/v1/chat",
            {
                "model": "org/exact-model",
                "input": "Hi",
                "stream": False,
                "store": False,
                "max_output_tokens": 93,
            },
            2.5,
        )
    ]


def test_vision_request_passes_prepared_image_and_system_prompt() -> None:
    transport = _Transport(_response())
    request = LocalInferenceRequest(
        "org/vision-model",
        "Describe",
        25,
        system_prompt="Be concise",
        image_data_url=_IMAGE,
    )
    NativeLmStudioInferenceProvider(transport).infer(request)
    assert transport.calls == [
        (
            "POST",
            "/api/v1/chat",
            {
                "model": "org/vision-model",
                "input": [
                    {"type": "text", "content": "Describe"},
                    {"type": "image", "data_url": _IMAGE},
                ],
                "system_prompt": "Be concise",
                "stream": False,
                "store": False,
                "max_output_tokens": 25,
            },
            120.0,
        )
    ]


def test_output_order_reasoning_and_usage() -> None:
    transport = _Transport(
        _response(
            [
                {"type": "reasoning", "content": "secret thought"},
                {"type": "message", "content": "First"},
                {"type": "message", "content": "  "},
                {"type": "message", "content": "Second\n line"},
            ],
            stats={
                "input_tokens": 100,
                "total_output_tokens": 24,
                "reasoning_output_tokens": 10,
                "tokens_per_second": 40.0,
            },
        )
    )
    result = NativeLmStudioInferenceProvider(transport).infer(
        LocalInferenceRequest("model", "hello", 10)
    )
    assert result.text == "First\nSecond\n line"
    assert "secret thought" not in result.text
    assert result.usage == LocalInferenceUsage(100, 24, 10)


def test_usage_with_optional_reasoning_count() -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(
            _response(stats={"input_tokens": 2, "total_output_tokens": 3})
        )
    )
    result = provider.infer(LocalInferenceRequest("model", "query", 3))
    assert result.usage == LocalInferenceUsage(2, 3)


@pytest.mark.parametrize("bad", (None, "", " ", 4, " with spaces "))
def test_missing_or_malformed_instance_id_rejected(bad: object) -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(_response(instance=bad))
    )
    with pytest.raises(LocalModelProtocolError, match="model_instance_id"):
        provider.infer(LocalInferenceRequest("model", "hello", 12))


@pytest.mark.parametrize("bad", (None, {}, "text", 3, (), [None], ["str"]))
def test_bad_output_is_rejected(bad: object) -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(_response(items=bad))
    )
    with pytest.raises(LocalModelProtocolError):
        provider.infer(LocalInferenceRequest("model", "hello", 12))


@pytest.mark.parametrize("bad", (None, 123, [], {}))
def test_bad_message_content_is_rejected(bad: object) -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(_response(items=[{"type": "message", "content": bad}]))
    )
    with pytest.raises(LocalModelProtocolError, match="message text"):
        provider.infer(LocalInferenceRequest("model", "hello", 12))


@pytest.mark.parametrize("kind", ("tool_call", "invalid_tool_call", "other"))
def test_tool_calls_or_unknown_output_are_never_executed(kind: str) -> None:
    callback_called = False

    def unexpected_execution() -> None:
        nonlocal callback_called
        callback_called = True

    transport = _Transport(
        _response(
            items=[
                {"type": "message", "content": "usable text"},
                {"type": kind, "output": unexpected_execution},
            ]
        )
    )
    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "hello", 12)
        )
    assert not callback_called


def test_invalid_output_kind_is_rejected() -> None:
    transport = _Transport(_response(items=[{"type": []}]))
    with pytest.raises(LocalModelProtocolError, match="output type"):
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "hi", 12)
        )


def test_reasoning_only_and_blank_messages_are_rejected() -> None:
    for items in (
        [{"type": "reasoning", "content": "private"}],
        [{"type": "message", "content": "  "}],
    ):
        with pytest.raises(LocalModelProtocolError, match="no textual"):
            NativeLmStudioInferenceProvider(
                _Transport(_response(items=items))
            ).infer(LocalInferenceRequest("model", "hello", 12))


def test_invalid_reasoning_content_rejected() -> None:
    with pytest.raises(LocalModelProtocolError, match="reasoning"):
        NativeLmStudioInferenceProvider(
            _Transport(_response(items=[{"type": "reasoning"}]))
        ).infer(LocalInferenceRequest("model", "hi", 12))


@pytest.mark.parametrize("bad", (None, [], 3, "text"))
def test_bad_success_payload_rejected(bad: object) -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(LmStudioJsonResponse(200, bad))
    )
    with pytest.raises(LocalModelProtocolError):
        provider.infer(LocalInferenceRequest("model", "hello", 12))


@pytest.mark.parametrize("status", (0, 100, 301, 600, True))
def test_invalid_or_unexpected_http_status_rejected(status: object) -> None:
    provider = NativeLmStudioInferenceProvider(
        _Transport(LmStudioJsonResponse(cast(int, status), {}))
    )
    with pytest.raises(LocalModelProtocolError):
        provider.infer(LocalInferenceRequest("model", "hello", 12))


def test_invalid_transport_response_rejected() -> None:
    transport = _Transport(cast(LmStudioJsonResponse, None))
    with pytest.raises(LocalModelProtocolError, match="transport response"):
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "query", 10)
        )


@pytest.mark.parametrize(
    "status, error_type",
    (
        (404, LocalModelUnavailableError),
        (400, LocalModelInferenceError),
        (409, LocalModelInferenceError),
        (422, LocalModelInferenceError),
        (429, LocalModelInferenceError),
        (500, LocalModelError),
        (503, LocalModelError),
    ),
)
def test_http_errors_are_normalized(
    status: int, error_type: type[LocalModelError]
) -> None:
    transport = _Transport(
        LmStudioJsonResponse(status, {"error": "private information"})
    )
    with pytest.raises(error_type) as exc:
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "hello", 12)
        )
    assert "private information" not in str(exc.value)


@pytest.mark.parametrize(
    "bad_stats",
    (
        [],
        "text",
        5,
        {},
        {"input_tokens": 2},
        {"input_tokens": -1, "total_output_tokens": 3},
        {"input_tokens": 3, "total_output_tokens": True},
        {
            "input_tokens": 3,
            "total_output_tokens": 1,
            "reasoning_output_tokens": 2,
        },
    ),
)
def test_malformed_usage_is_rejected(bad_stats: object) -> None:
    transport = _Transport(_response(stats=bad_stats))
    with pytest.raises(LocalModelProtocolError, match="usage|token"):
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "hello", 12)
        )


@pytest.mark.parametrize(
    "value", (0, -1, float("inf"), float("nan"), True, "bad")
)
def test_timeout_must_be_positive_and_finite(value: object) -> None:
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        NativeLmStudioInferenceProvider(
            _Transport(_response()),
            request_timeout_seconds=cast(float, value),
        )


@pytest.mark.parametrize(
    "failure, expected",
    (
        (TimeoutError("timeout"), LocalModelTimeoutError),
        (OSError("offline"), LocalModelConnectionError),
        (LocalModelTimeoutError("already normalized"), LocalModelTimeoutError),
        (
            LocalModelConnectionError("already normalized"),
            LocalModelConnectionError,
        ),
    ),
)
def test_transport_failures_are_normalized(
    failure: Exception, expected: type[LocalModelError]
) -> None:
    transport = _Transport(_response())
    transport.failure = failure
    with pytest.raises(expected):
        NativeLmStudioInferenceProvider(transport).infer(
            LocalInferenceRequest("model", "query", 20)
        )
    assert len(transport.calls) == 1


def test_invalid_request_type_has_no_transport_calls() -> None:
    transport = _Transport(_response())
    provider = NativeLmStudioInferenceProvider(transport)
    with pytest.raises(TypeError):
        provider.infer(cast(LocalInferenceRequest, None))
    assert transport.calls == []


def test_adapter_requires_no_database_file_or_lifecycle_port() -> None:
    transport = _Transport(_response())
    NativeLmStudioInferenceProvider(transport).infer(
        LocalInferenceRequest("model", "query", 20)
    )
    assert {call[1] for call in transport.calls} == {"/api/v1/chat"}
