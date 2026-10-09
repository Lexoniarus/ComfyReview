"""Behavior tests for native LM Studio v1 lifecycle communication."""

from __future__ import annotations

import io
import json
import urllib.error
import urllib.request
from collections import defaultdict
from email.message import Message

import pytest

from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelDescriptor,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelProvider,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)
from comfyreview.providers import (
    LmStudioJsonResponse,
    NativeLmStudioProvider,
    UrlLibLmStudioJsonTransport,
)


class _Transport:
    def __init__(self) -> None:
        self.responses: dict[
            tuple[str, str], list[LmStudioJsonResponse]
        ] = defaultdict(list)
        self.calls: list[tuple[str, str, object | None, float]] = []

    def add(
        self, method: str, path: str, status: int, payload: object
    ) -> None:
        self.responses[(method, path)].append(
            LmStudioJsonResponse(status, payload)
        )

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> LmStudioJsonResponse:
        self.calls.append((method, path, payload, timeout_seconds))
        return self.responses[(method, path)].pop(0)


def test_list_models_preserves_instances_and_sorts() -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/api/v1/models",
        200,
        {
            "models": [
                {"key": "z/model", "loaded_instances": []},
                {
                    "key": "a/model",
                    "loaded_instances": [
                        {"id": "instance-b", "config": {}},
                        {"id": "instance-a"},
                    ],
                    "quantization": {"name": "Q4"},
                },
            ]
        },
    )

    provider: LocalModelProvider = NativeLmStudioProvider(
        transport, request_timeout_seconds=7
    )
    models = provider.list_models()

    assert models == (
        LocalModelDescriptor(
            "a/model",
            (
                LocalModelInstance("a/model", "instance-a"),
                LocalModelInstance("a/model", "instance-b"),
            ),
        ),
        LocalModelDescriptor("z/model", ()),
    )
    assert transport.calls == [("GET", "/api/v1/models", None, 7.0)]


@pytest.mark.parametrize(
    "payload",
    (
        [],
        {},
        {"models": {}},
        {"models": [None]},
        {"models": [{"key": "model"}]},
    ),
)
def test_list_models_rejects_invalid_model_payload(payload: object) -> None:
    transport = _Transport()
    transport.add("GET", "/api/v1/models", 200, payload)

    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioProvider(transport).list_models()


@pytest.mark.parametrize("bad_key", (None, "", "  ", 5))
def test_list_models_rejects_invalid_model_key(bad_key: object) -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/api/v1/models",
        200,
        {"models": [{"key": bad_key, "loaded_instances": []}]},
    )

    with pytest.raises(LocalModelProtocolError, match="model key"):
        NativeLmStudioProvider(transport).list_models()


@pytest.mark.parametrize("bad_instances", (None, {}, "missing", [None]))
def test_list_models_rejects_bad_loaded_instances(
    bad_instances: object,
) -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/api/v1/models",
        200,
        {"models": [{"key": "model", "loaded_instances": bad_instances}]},
    )

    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioProvider(transport).list_models()


@pytest.mark.parametrize("bad_id", (None, "", "  ", 42))
def test_list_models_rejects_invalid_instance_ids(bad_id: object) -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/api/v1/models",
        200,
        {"models": [{"key": "model", "loaded_instances": [{"id": bad_id}]}]},
    )

    with pytest.raises(LocalModelProtocolError, match="instance id"):
        NativeLmStudioProvider(transport).list_models()


def test_list_models_rejects_non_success_http() -> None:
    transport = _Transport()
    transport.add("GET", "/api/v1/models", 503, {"error": "busy"})

    with pytest.raises(LocalModelProtocolError, match="HTTP 503"):
        NativeLmStudioProvider(transport).list_models()


def test_load_model_posts_only_id_and_uses_lifecycle_timeout() -> None:
    transport = _Transport()
    transport.add(
        "POST",
        "/api/v1/models/load",
        200,
        {"instance_id": "instance-4", "status": "loaded"},
    )

    result = NativeLmStudioProvider(
        transport,
        request_timeout_seconds=4,
        lifecycle_timeout_seconds=99,
    ).load_model("qwen/model")

    assert result == LocalModelInstance("qwen/model", "instance-4")
    assert transport.calls == [
        ("POST", "/api/v1/models/load", {"model": "qwen/model"}, 99.0)
    ]


@pytest.mark.parametrize("bad_id", ("", "  "))
def test_load_model_rejects_invalid_requested_id(bad_id: str) -> None:
    transport = _Transport()
    with pytest.raises(ValueError, match="model_id is required"):
        NativeLmStudioProvider(transport).load_model(bad_id)
    assert transport.calls == []


@pytest.mark.parametrize(
    "payload",
    (
        {},
        {"instance_id": None, "status": "loaded"},
        {"instance_id": " ", "status": "loaded"},
        {"instance_id": "inst"},
        {"instance_id": "inst", "status": "loading"},
        [],
    ),
)
def test_load_model_rejects_malformed_success(payload: object) -> None:
    transport = _Transport()
    transport.add("POST", "/api/v1/models/load", 200, payload)

    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioProvider(transport).load_model("model")


def test_load_model_normalizes_not_found_status() -> None:
    transport = _Transport()
    transport.add("POST", "/api/v1/models/load", 404, {"error": "no"})

    with pytest.raises(LocalModelUnavailableError):
        NativeLmStudioProvider(transport).load_model("model")


def test_load_model_normalizes_conflict_status() -> None:
    transport = _Transport()
    transport.add("POST", "/api/v1/models/load", 409, {"error": "no"})

    with pytest.raises(LocalModelLifecycleError):
        NativeLmStudioProvider(transport).load_model("model")


def test_unload_model_targets_exact_instance() -> None:
    transport = _Transport()
    transport.add(
        "POST",
        "/api/v1/models/unload",
        200,
        {"instance_id": "instance-b"},
    )
    instance = LocalModelInstance("qwen/model", "instance-b")

    NativeLmStudioProvider(
        transport, lifecycle_timeout_seconds=45
    ).unload_model(instance)
    assert transport.calls == [
        (
            "POST",
            "/api/v1/models/unload",
            {"instance_id": "instance-b"},
            45.0,
        )
    ]


@pytest.mark.parametrize(
    "payload",
    ({}, {"instance_id": "other"}, {"instance_id": ""}, []),
)
def test_unload_model_rejects_mismatched_or_malformed_response(
    payload: object,
) -> None:
    transport = _Transport()
    transport.add("POST", "/api/v1/models/unload", 200, payload)

    with pytest.raises(LocalModelProtocolError):
        NativeLmStudioProvider(transport).unload_model(
            LocalModelInstance("model", "instance-1")
        )


@pytest.mark.parametrize("status", (404, 409, 503))
def test_unload_model_rejects_non_success(status: int) -> None:
    transport = _Transport()
    transport.add("POST", "/api/v1/models/unload", status, {})

    with pytest.raises(LocalModelLifecycleError, match=f"HTTP {status}"):
        NativeLmStudioProvider(transport).unload_model(
            LocalModelInstance("model", "instance-1")
        )


def test_unload_model_rejects_missing_id_before_request() -> None:
    transport = _Transport()
    with pytest.raises(ValueError, match="instance_id is required"):
        NativeLmStudioProvider(transport).unload_model(
            LocalModelInstance("model", " ")
        )
    assert transport.calls == []


class _Response:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self.raw = raw
        self.status = status

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self.raw


def test_urllib_transport_normalizes_base_url_and_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="base_url is required"):
        UrlLibLmStudioJsonTransport(" ")

    recorded: list[tuple[str, str, bytes | None, float, str]] = []

    def fake_urlopen(
        request: urllib.request.Request, timeout: float
    ) -> _Response:
        request_data = request.data
        assert isinstance(request_data, bytes)

        recorded.append(
            (
                request.get_method(),
                request.full_url,
                request_data,
                timeout,
                request.headers.get("Content-type", ""),
            )
        )
        return _Response(b'{"ok": true}')

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = UrlLibLmStudioJsonTransport(" http://localhost:1234/// ")
    result = transport.request(
        "POST",
        "/api/v1/models/load",
        payload={"model": "qwen/model"},
        timeout_seconds=12,
    )

    assert result == LmStudioJsonResponse(200, {"ok": True})
    assert recorded == [
        (
            "POST",
            "http://localhost:1234/api/v1/models/load",
            json.dumps({"model": "qwen/model"}).encode("utf-8"),
            12.0,
            "application/json",
        )
    ]


@pytest.mark.parametrize(
    "failure",
    (
        TimeoutError("timeout"),
        urllib.error.URLError(TimeoutError("timeout")),
    ),
)
def test_urllib_transport_normalizes_timeouts(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    def fake_urlopen(
        request: urllib.request.Request, timeout: float
    ) -> _Response:
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = UrlLibLmStudioJsonTransport("http://localhost:1234")

    with pytest.raises(LocalModelTimeoutError):
        transport.request("GET", "/api/v1/models", timeout_seconds=1)


@pytest.mark.parametrize(
    "failure",
    (urllib.error.URLError("no connection"), OSError("socket error")),
)
def test_urllib_transport_normalizes_connection_failures(
    monkeypatch: pytest.MonkeyPatch,
    failure: BaseException,
) -> None:
    def fake_urlopen(
        request: urllib.request.Request, timeout: float
    ) -> _Response:
        raise failure

    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)
    transport = UrlLibLmStudioJsonTransport("http://localhost:1234")

    with pytest.raises(LocalModelConnectionError):
        transport.request("GET", "/api/v1/models", timeout_seconds=1)


@pytest.mark.parametrize("body", (b"not-json", b"\xff", b"[] trailing"))
def test_urllib_transport_normalizes_invalid_json(
    monkeypatch: pytest.MonkeyPatch,
    body: bytes,
) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(body),
    )

    with pytest.raises(LocalModelProtocolError, match="invalid JSON"):
        UrlLibLmStudioJsonTransport("http://localhost:1234").request(
            "GET", "/api/v1/models", timeout_seconds=1
        )


def test_urllib_transport_returns_http_error_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    error = urllib.error.HTTPError(
        "http://localhost/api/v1/models/load",
        404,
        "not found",
        Message(),
        io.BytesIO(b'{"error": "missing model"}'),
    )

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(error),
    )
    transport = UrlLibLmStudioJsonTransport("http://localhost:1234")

    assert transport.request(
        "POST",
        "/api/v1/models/load",
        payload={"model": "absent"},
        timeout_seconds=9,
    ) == LmStudioJsonResponse(404, {"error": "missing model"})


def test_urllib_transport_accepts_empty_json_body(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(b""),
    )

    transport = UrlLibLmStudioJsonTransport("http://localhost:1234")
    response = transport.request("GET", "/api/v1/models", timeout_seconds=1)
    assert response == LmStudioJsonResponse(200, {})
