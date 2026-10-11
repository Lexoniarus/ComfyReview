"""Behavior and failure checks for the native LM Studio lifecycle provider."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from email.message import Message
from typing import cast

import pytest

from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)
from comfyreview.providers.lm_studio import (
    LmStudioJsonResponse,
    NativeLmStudioProvider,
    UrlLibLmStudioJsonTransport,
)


@dataclass
class _Response:
    status: int
    body: bytes

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.body


class _Transport:
    def __init__(self, responses: list[LmStudioJsonResponse]) -> None:
        self.responses = list(responses)
        self.calls: list[tuple[str, str, object | None, float]] = []

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> LmStudioJsonResponse:
        self.calls.append((method, path, payload, timeout_seconds))
        return self.responses.pop(0)


def test_authenticated_transport_sends_bounded_json(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[tuple[urllib.request.Request, float]] = []

    def respond(request: urllib.request.Request, timeout: float) -> _Response:
        observed.append((request, timeout))
        return _Response(200, b'{"ok": true}')

    monkeypatch.setattr(urllib.request, "urlopen", respond)
    transport = UrlLibLmStudioJsonTransport(
        "http://127.0.0.1:1234/", " secret-token "
    )

    response = transport.request(
        "post",
        "/api/v1/models/load",
        payload={"model": "vision"},
        timeout_seconds=6,
    )

    request, timeout = observed[0]
    assert response == LmStudioJsonResponse(200, {"ok": True})
    assert request.full_url == "http://127.0.0.1:1234/api/v1/models/load"
    assert request.method == "POST"
    assert request.get_header("Authorization") == "Bearer secret-token"
    assert request.get_header("Content-type") == "application/json"
    assert json.loads(cast(bytes, request.data)) == {"model": "vision"}
    assert timeout == 6


def test_transport_omits_empty_token_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[urllib.request.Request] = []

    def respond(request: urllib.request.Request, timeout: float) -> _Response:
        assert timeout == 5
        observed.append(request)
        return _Response(204, b"")

    monkeypatch.setattr(urllib.request, "urlopen", respond)
    response = UrlLibLmStudioJsonTransport("http://lm.test", " ").request(
        "GET", "models", timeout_seconds=5
    )

    assert response == LmStudioJsonResponse(204, {})
    assert observed[0].get_header("Authorization") is None
    assert observed[0].data is None


def test_transport_preserves_http_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = urllib.error.HTTPError(
        "http://lm.test/models",
        503,
        "unavailable",
        Message(),
        io.BytesIO(b'{"error": "busy"}'),
    )
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda _request, timeout: (_ for _ in ()).throw(error),
    )

    response = UrlLibLmStudioJsonTransport("http://lm.test").request(
        "GET", "/models", timeout_seconds=5
    )

    assert response == LmStudioJsonResponse(503, {"error": "busy"})


@pytest.mark.parametrize("raw", (b"{", b"\xff"))
def test_transport_rejects_invalid_json(
    monkeypatch: pytest.MonkeyPatch, raw: bytes
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda _request, timeout: _Response(200, raw),
    )

    with pytest.raises(LocalModelProtocolError, match="invalid JSON"):
        UrlLibLmStudioJsonTransport("http://lm.test").request(
            "GET", "/models", timeout_seconds=5
        )


@pytest.mark.parametrize(
    ("failure", "expected"),
    (
        (urllib.error.URLError(TimeoutError()), LocalModelTimeoutError),
        (urllib.error.URLError("offline"), LocalModelConnectionError),
        (TimeoutError(), LocalModelTimeoutError),
        (OSError("offline"), LocalModelConnectionError),
    ),
)
def test_transport_normalizes_connection_failures_without_token(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
    expected: type[Exception],
) -> None:
    monkeypatch.setattr(
        urllib.request,
        "urlopen",
        lambda _request, timeout: (_ for _ in ()).throw(failure),
    )

    with pytest.raises(expected) as captured:
        UrlLibLmStudioJsonTransport("http://lm.test", "private").request(
            "GET", "/models", timeout_seconds=5
        )

    assert "private" not in str(captured.value)


@pytest.mark.parametrize("timeout", (0, -1, float("inf"), float("nan")))
def test_transport_rejects_invalid_timeout(timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds"):
        UrlLibLmStudioJsonTransport("http://lm.test").request(
            "GET", "/models", timeout_seconds=timeout
        )


def test_transport_requires_base_url() -> None:
    with pytest.raises(ValueError, match="base_url"):
        UrlLibLmStudioJsonTransport(" ")


def test_provider_lists_models_and_instances_in_stable_order() -> None:
    transport = _Transport(
        [
            LmStudioJsonResponse(
                200,
                {
                    "models": [
                        {"key": "zeta", "loaded_instances": []},
                        {
                            "key": "Alpha",
                            "loaded_instances": [{"id": "two"}, {"id": "One"}],
                        },
                    ]
                },
            )
        ]
    )
    provider = NativeLmStudioProvider(transport, list_timeout_seconds=7)

    models = provider.list_models()

    assert tuple(model.model_id for model in models) == ("Alpha", "zeta")
    assert tuple(item.instance_id for item in models[0].loaded_instances) == (
        "One",
        "two",
    )
    assert transport.calls == [("GET", "/api/v1/models", None, 7.0)]


@pytest.mark.parametrize(
    ("response", "message"),
    (
        (LmStudioJsonResponse(503, {}), "HTTP 503"),
        (LmStudioJsonResponse(200, []), "JSON object"),
        (LmStudioJsonResponse(200, {}), "models must be a list"),
        (LmStudioJsonResponse(200, {"models": [[]]}), "JSON object"),
        (
            LmStudioJsonResponse(
                200, {"models": [{"key": " ", "loaded_instances": []}]}
            ),
            "model key",
        ),
        (
            LmStudioJsonResponse(200, {"models": [{"key": "a"}]}),
            "loaded_instances",
        ),
        (
            LmStudioJsonResponse(
                200,
                {"models": [{"key": "a", "loaded_instances": [[]]}]},
            ),
            "JSON object",
        ),
        (
            LmStudioJsonResponse(
                200,
                {"models": [{"key": "a", "loaded_instances": [{"id": 1}]}]},
            ),
            "instance id",
        ),
    ),
)
def test_provider_rejects_invalid_model_listing(
    response: LmStudioJsonResponse, message: str
) -> None:
    provider = NativeLmStudioProvider(_Transport([response]))

    with pytest.raises(LocalModelProtocolError, match=message):
        provider.list_models()


def test_provider_loads_and_unloads_with_separate_timeouts() -> None:
    transport = _Transport(
        [
            LmStudioJsonResponse(
                200, {"status": "loaded", "instance_id": "instance-1"}
            ),
            LmStudioJsonResponse(200, {"instance_id": "instance-1"}),
        ]
    )
    provider = NativeLmStudioProvider(
        transport, load_timeout_seconds=17, unload_timeout_seconds=9
    )

    instance = provider.load_model(" vision ")
    provider.unload_model(instance)

    assert instance == LocalModelInstance("vision", "instance-1")
    assert transport.calls == [
        ("POST", "/api/v1/models/load", {"model": "vision"}, 17.0),
        (
            "POST",
            "/api/v1/models/unload",
            {"instance_id": "instance-1"},
            9.0,
        ),
    ]


def test_provider_maps_missing_model_and_lifecycle_failure() -> None:
    provider = NativeLmStudioProvider(
        _Transport(
            [
                LmStudioJsonResponse(404, {}),
                LmStudioJsonResponse(500, {}),
            ]
        )
    )

    with pytest.raises(LocalModelUnavailableError, match="missing"):
        provider.load_model("missing")
    with pytest.raises(LocalModelLifecycleError, match="HTTP 500"):
        provider.load_model("broken")


@pytest.mark.parametrize(
    ("response", "message"),
    (
        (LmStudioJsonResponse(200, []), "JSON object"),
        (
            LmStudioJsonResponse(
                200, {"status": "loaded", "instance_id": " "}
            ),
            "instance id",
        ),
        (
            LmStudioJsonResponse(200, {"status": "other", "instance_id": "i"}),
            "loaded status",
        ),
    ),
)
def test_provider_rejects_invalid_load_response(
    response: LmStudioJsonResponse, message: str
) -> None:
    with pytest.raises(LocalModelProtocolError, match=message):
        NativeLmStudioProvider(_Transport([response])).load_model("model")


@pytest.mark.parametrize("model_id", ("", " ", None))
def test_provider_requires_model_id(model_id: object) -> None:
    with pytest.raises(ValueError, match="model_id"):
        NativeLmStudioProvider(_Transport([])).load_model(model_id)  # type: ignore[arg-type]


def test_provider_rejects_invalid_unload_responses() -> None:
    instance = LocalModelInstance("model", "instance-1")
    responses = (
        (LmStudioJsonResponse(500, {}), LocalModelLifecycleError, "HTTP 500"),
        (
            LmStudioJsonResponse(200, []),
            LocalModelProtocolError,
            "JSON object",
        ),
        (
            LmStudioJsonResponse(200, {"instance_id": "instance-2"}),
            LocalModelProtocolError,
            "another instance",
        ),
    )
    for response, error_type, message in responses:
        with pytest.raises(error_type, match=message):
            NativeLmStudioProvider(_Transport([response])).unload_model(
                instance
            )


def test_provider_requires_instance_id() -> None:
    with pytest.raises(ValueError, match="instance_id"):
        NativeLmStudioProvider(_Transport([])).unload_model(
            LocalModelInstance("model", " ")
        )


@pytest.mark.parametrize(
    "name",
    ("list_timeout_seconds", "load_timeout_seconds", "unload_timeout_seconds"),
)
def test_provider_requires_positive_finite_timeouts(name: str) -> None:
    with pytest.raises(ValueError, match=name):
        NativeLmStudioProvider(_Transport([]), **{name: float("nan")})
