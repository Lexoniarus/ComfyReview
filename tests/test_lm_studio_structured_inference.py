"""Fake-transport tests for independently checked LM Studio JSON."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application.local_model_inference import (
    LocalInferenceRequest,
    LocalInferenceUsage,
    LocalModelInferenceError,
)
from comfyreview.application.local_model_structured_inference import (
    LocalModelStructuredOutputError,
    LocalStructuredInferenceProvider,
    LocalStructuredInferenceRequest,
)
from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)
from comfyreview.providers.lm_studio import LmStudioJsonResponse
from comfyreview.providers.lm_studio_structured_inference import (
    NativeLmStudioStructuredInferenceProvider,
)

_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {"name": {"type": "string"}},
    "required": ["name"],
    "additionalProperties": False,
}
_IMAGE = "data:image/png;base64,AA=="


def _request(*, image: str | None = None) -> LocalStructuredInferenceRequest:
    return LocalStructuredInferenceRequest(
        LocalInferenceRequest(
            "vendor/model-8b",
            "Identify the name",
            96,
            system_prompt="Return JSON",
            image_data_url=image,
        ),
        "person_name",
        _SCHEMA,
    )


def _response(
    content: object = '{"name":"Aiko"}',
    *,
    status: int = 200,
    finish: object = "stop",
    message: object = None,
    usage: object = None,
    reported_model: object = "vendor/model-8b",
) -> LmStudioJsonResponse:
    result: object = (
        {"role": "assistant", "content": content}
        if message is None
        else message
    )
    body: dict[str, object] = {
        "choices": [{"finish_reason": finish, "message": result}],
    }
    if reported_model is not None:
        body["model"] = reported_model
    if usage is not None:
        body["usage"] = usage
    return LmStudioJsonResponse(status, body)


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


def test_text_request_uses_schema_and_exact_model_without_lifecycle() -> None:
    transport = _Transport(_response())
    provider: LocalStructuredInferenceProvider = (
        NativeLmStudioStructuredInferenceProvider(
            transport, request_timeout_seconds=4.5
        )
    )
    result = provider.infer_structured(_request())
    assert result.value == {"name": "Aiko"}
    assert result.requested_model_id == "vendor/model-8b"
    assert result.reported_model_id == "vendor/model-8b"
    assert result.model_instance_id is None
    assert result.usage is None
    assert transport.calls == [
        (
            "POST",
            "/v1/chat/completions",
            {
                "model": "vendor/model-8b",
                "messages": [
                    {"role": "system", "content": "Return JSON"},
                    {"role": "user", "content": "Identify the name"},
                ],
                "response_format": {
                    "type": "json_schema",
                    "json_schema": {
                        "name": "person_name",
                        "strict": True,
                        "schema": _SCHEMA,
                    },
                },
                "max_tokens": 96,
                "stream": False,
            },
            4.5,
        )
    ]


def test_vision_request_has_openai_compatible_data_url() -> None:
    transport = _Transport(_response())
    NativeLmStudioStructuredInferenceProvider(transport).infer_structured(
        _request(image=_IMAGE)
    )
    payload = cast(dict[str, object], transport.calls[0][2])
    messages = cast(list[dict[str, object]], payload["messages"])
    assert messages[-1] == {
        "role": "user",
        "content": [
            {"type": "text", "text": "Identify the name"},
            {"type": "image_url", "image_url": {"url": _IMAGE}},
        ],
    }
    assert transport.calls[0][3] == 120.0


def test_request_without_system_prompt_uses_only_user_message() -> None:
    transport = _Transport(_response())
    request = LocalStructuredInferenceRequest(
        LocalInferenceRequest("model", "query", 5), "response", _SCHEMA
    )
    NativeLmStudioStructuredInferenceProvider(transport).infer_structured(
        request
    )
    payload = cast(dict[str, object], transport.calls[0][2])
    assert payload["messages"] == [{"role": "user", "content": "query"}]


def test_missing_model_does_not_fabricate_reported_or_instance_id() -> None:
    transport = _Transport(_response(reported_model=None))
    result = NativeLmStudioStructuredInferenceProvider(
        transport
    ).infer_structured(_request())
    assert result.reported_model_id is None
    assert result.model_instance_id is None


def test_differing_reported_model_is_not_silently_rewritten() -> None:
    result = NativeLmStudioStructuredInferenceProvider(
        _Transport(_response(reported_model="an/alias"))
    ).infer_structured(_request())
    assert result.requested_model_id == "vendor/model-8b"
    assert result.reported_model_id == "an/alias"


def test_completion_usage_is_normalized_when_available() -> None:
    stats: dict[str, object] = {
        "prompt_tokens": 42,
        "completion_tokens": 18,
        "completion_tokens_details": {"reasoning_tokens": 7},
        "total_tokens": 60,
    }
    result = NativeLmStudioStructuredInferenceProvider(
        _Transport(_response(usage=stats))
    ).infer_structured(_request())
    assert result.usage == LocalInferenceUsage(42, 18, 7)


def test_usage_can_omit_reasoning_details() -> None:
    result = NativeLmStudioStructuredInferenceProvider(
        _Transport(_response(usage={"prompt_tokens": 3, "completion_tokens": 4}))
    ).infer_structured(_request())
    assert result.usage == LocalInferenceUsage(3, 4)


@pytest.mark.parametrize(
    "bad",
    (
        "not-json",
        "```json\n{}\n```",
        "{",
        '{"name":"Aiko","name":"Kaori"}',
        '{"name":NaN}',
        '{"name":1e999}',
        '{"name":"Aiko"} extra',
    ),
)
def test_json_parsing_rejects_invalid_or_ambiguous_output(bad: str) -> None:
    with pytest.raises(LocalModelProtocolError, match="invalid structured"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(bad))).infer_structured(_request())


@pytest.mark.parametrize(
    "bad",
    ('{"name":3}', '{"name":"Aiko","extra":1}', "[]", "null"),
)
def test_schema_is_checked_independently_of_provider(bad: str) -> None:
    with pytest.raises(LocalModelStructuredOutputError, match="schema"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(bad))).infer_structured(_request())


def test_valid_local_reference_schema_is_checked() -> None:
    request = LocalStructuredInferenceRequest(
        LocalInferenceRequest("model", "query", 8),
        "referenced",
        {
            "$defs": {"word": {"type": "string"}},
            "type": "array",
            "items": {"$ref": "#/$defs/word"},
        },
    )
    result = NativeLmStudioStructuredInferenceProvider(
        _Transport(_response('["Aiko","Kaori"]'))
    ).infer_structured(request)
    assert result.value == ["Aiko", "Kaori"]


def test_missing_local_ref_is_normalized() -> None:
    request = LocalStructuredInferenceRequest(
        LocalInferenceRequest("model", "query", 8),
        "referenced",
        {"$ref": "#/$defs/unknown"},
    )
    with pytest.raises(LocalModelProtocolError, match="resolution failed"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response("{}"))).infer_structured(request)


@pytest.mark.parametrize(
    "bad",
    ("", "  ", None, 42, [], {}),
)
def test_missing_or_wrong_content_fails(bad: object) -> None:
    with pytest.raises(LocalModelProtocolError, match="JSON content"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(bad))).infer_structured(_request())


def test_oversized_json_response_rejected_before_parsing() -> None:
    with pytest.raises(LocalModelProtocolError, match="size limit"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response("x" * (128 * 1024 + 1)))).infer_structured(_request())


@pytest.mark.parametrize(
    "bad", ("length", "tool_calls", "content_filter", None)
)
def test_incomplete_or_nonstandard_finish_is_rejected(bad: object) -> None:
    with pytest.raises(LocalModelProtocolError, match="finish normally"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(finish=bad))).infer_structured(_request())


@pytest.mark.parametrize(
    "message",
    (
        {"role": "system", "content": "{}"},
        {"role": "assistant", "refusal": "not permitted", "content": "{}"},
        {"role": "assistant", "tool_calls": [], "content": "{}"},
        {"role": "assistant", "function_call": {}, "content": "{}"},
        {},
        [],
        5,
    ),
)
def test_non_assistant_refusals_and_tool_calls_rejected(
    message: object,
) -> None:
    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(message=message))).infer_structured(_request())


@pytest.mark.parametrize(
    "body",
    (
        None,
        [],
        5,
        {},
        {"choices": []},
        {"choices": [None]},
        {"choices": [{}, {}]},
        {"choices": [{"finish_reason": "stop"}]},
    ),
)
def test_malformed_completion_shape_rejected(body: object) -> None:
    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioStructuredInferenceProvider(_Transport(LmStudioJsonResponse(200, body))).infer_structured(_request())


@pytest.mark.parametrize("bad", ("", " bad ", True, 9))
def test_malformed_reported_model_rejected(bad: object) -> None:
    response = _response(reported_model=bad)
    with pytest.raises(LocalModelProtocolError, match="reported"):
        NativeLmStudioStructuredInferenceProvider(_Transport(response)).infer_structured(_request())


@pytest.mark.parametrize("status", (0, 100, 302, 600, True))
def test_bad_http_status_rejected(status: object) -> None:
    with pytest.raises(LocalModelProtocolError, match="HTTP status"):
        NativeLmStudioStructuredInferenceProvider(_Transport(LmStudioJsonResponse(cast(int, status), {}))).infer_structured(_request())


@pytest.mark.parametrize(
    "status, expected",
    (
        (404, LocalModelUnavailableError),
        (400, LocalModelInferenceError),
        (422, LocalModelInferenceError),
        (429, LocalModelInferenceError),
        (500, LocalModelError),
        (503, LocalModelError),
    ),
)
def test_http_failures_are_typed_without_leaking_private_payload(
    status: int, expected: type[LocalModelError]
) -> None:
    with pytest.raises(expected) as failure:
        NativeLmStudioStructuredInferenceProvider(_Transport(LmStudioJsonResponse(status, {"secret": "never"}))).infer_structured(_request())
    assert "never" not in str(failure.value)


@pytest.mark.parametrize(
    "bad",
    (
        {},
        "text",
        [],
        {"prompt_tokens": 2},
        {"prompt_tokens": -1, "completion_tokens": 1},
        {"prompt_tokens": True, "completion_tokens": 1},
        {"prompt_tokens": 2, "completion_tokens": 1,
         "completion_tokens_details": {"reasoning_tokens": 2}},
        {"prompt_tokens": 2, "completion_tokens": 1,
         "completion_tokens_details": []},
    ),
)
def test_bad_usage_is_normalized(bad: object) -> None:
    with pytest.raises(LocalModelProtocolError, match="usage|token"):
        NativeLmStudioStructuredInferenceProvider(_Transport(_response(usage=bad))).infer_structured(_request())


@pytest.mark.parametrize(
    "bad", (0, -1, True, "bad", float("nan"), float("inf"))
)
def test_timeout_must_be_positive_finite(bad: object) -> None:
    with pytest.raises(ValueError, match="request_timeout_seconds"):
        NativeLmStudioStructuredInferenceProvider(
            _Transport(_response()),
            request_timeout_seconds=cast(float, bad),
        )


@pytest.mark.parametrize(
    "error, expected",
    (
        (TimeoutError("timeout"), LocalModelTimeoutError),
        (OSError("offline"), LocalModelConnectionError),
        (LocalModelTimeoutError("normalized"), LocalModelTimeoutError),
        (LocalModelConnectionError("normalized"), LocalModelConnectionError),
    ),
)
def test_transport_failures_are_normalized(
    error: Exception, expected: type[LocalModelError]
) -> None:
    transport = _Transport(_response())
    transport.failure = error
    with pytest.raises(expected):
        NativeLmStudioStructuredInferenceProvider(transport).infer_structured(_request())
    assert len(transport.calls) == 1


def test_invalid_request_and_transport_result_rejected() -> None:
    transport = _Transport(_response())
    provider = NativeLmStudioStructuredInferenceProvider(transport)
    with pytest.raises(TypeError):
        provider.infer_structured(cast(LocalStructuredInferenceRequest, None))
    assert transport.calls == []
    broken = _Transport(cast(LmStudioJsonResponse, None))
    with pytest.raises(LocalModelProtocolError, match="transport response"):
        NativeLmStudioStructuredInferenceProvider(broken).infer_structured(_request())
