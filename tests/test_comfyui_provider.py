"""Contract tests for the native technical ComfyUI provider."""

from __future__ import annotations

import io
import urllib.error
from collections import defaultdict
from email.message import Message

import pytest

from comfyreview.application import (
    ComfyUiConnectionError,
    ComfyUiNotFoundError,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    ComfyUiTimeoutError,
)
from comfyreview.providers import (
    JsonHttpResponse,
    NativeComfyUiProvider,
    UrlLibJsonTransport,
)


class _Transport:
    def __init__(self) -> None:
        self.responses: dict[tuple[str, str], list[JsonHttpResponse]] = (
            defaultdict(list)
        )
        self.calls: list[tuple[str, str, object | None, float]] = []

    def add(
        self, method: str, path: str, status: int, payload: object
    ) -> None:
        self.responses[(method, path)].append(
            JsonHttpResponse(status, payload)
        )

    def request(self, method, path, *, payload=None, timeout_seconds):
        self.calls.append((method, path, payload, timeout_seconds))
        return self.responses[(method, path)].pop(0)


def test_native_provider_submits_only_compiled_graph() -> None:
    transport = _Transport()
    transport.add("POST", "/prompt", 200, {"prompt_id": "prompt-1"})
    provider = NativeComfyUiProvider(transport, request_timeout_seconds=12)
    graph = {"1": {"inputs": {"text": "already compiled"}}}

    submission = provider.submit(graph)

    assert submission.prompt_id == "prompt-1"
    assert transport.calls == [("POST", "/prompt", {"prompt": graph}, 12.0)]


def test_native_provider_normalizes_submit_response_failures() -> None:
    missing = _Transport()
    missing.add("POST", "/prompt", 200, {})
    rejected = _Transport()
    rejected.add("POST", "/prompt", 400, {"error": "bad graph"})
    absent = _Transport()
    absent.add("POST", "/prompt", 404, {})

    with pytest.raises(ComfyUiProtocolError, match="no prompt_id"):
        NativeComfyUiProvider(missing).submit({})
    with pytest.raises(ComfyUiRejectionError, match="HTTP 400"):
        NativeComfyUiProvider(rejected).submit({})
    with pytest.raises(ComfyUiNotFoundError, match="returned 404"):
        NativeComfyUiProvider(absent).submit({})


@pytest.mark.parametrize(
    ("history_entry", "expected"),
    (
        ({"outputs": {"save": {"images": []}}}, ("completed", True, False)),
        (
            {"status": {"status_str": "error", "messages": ["failed"]}},
            ("failed", False, True),
        ),
        ({"status": {"status_str": "running"}}, ("running", False, False)),
    ),
)
def test_native_provider_reads_history_status(history_entry, expected) -> None:
    transport = _Transport()
    transport.add("GET", "/history/prompt-1", 200, {"prompt-1": history_entry})

    status = NativeComfyUiProvider(transport).get_status("prompt-1")

    assert (status.state, status.completed, status.failed) == expected


def test_native_provider_reads_queue_and_reports_unknown_prompt() -> None:
    running = _Transport()
    running.add("GET", "/history/running", 404, {})
    running.add("GET", "/queue", 200, {"queue_running": [[1, "running"]]})
    pending = _Transport()
    pending.add("GET", "/history/pending", 200, {})
    pending.add("GET", "/queue", 200, {"queue_pending": [[2, "pending"]]})
    missing = _Transport()
    missing.add("GET", "/history/missing", 200, {})
    missing.add("GET", "/queue", 200, {})

    assert (
        NativeComfyUiProvider(running).get_status("running").state == "running"
    )
    assert (
        NativeComfyUiProvider(pending).get_status("pending").state
        == "submitted"
    )
    with pytest.raises(ComfyUiNotFoundError, match="Unknown"):
        NativeComfyUiProvider(missing).get_status("missing")
    with pytest.raises(ValueError, match="prompt_id is required"):
        NativeComfyUiProvider(missing).get_status(" ")


def test_native_provider_waits_without_turning_timeout_into_failure() -> None:
    transport = _Transport()
    transport.add("GET", "/history/prompt-1", 200, {})
    transport.add("GET", "/queue", 200, {"queue_running": [[1, "prompt-1"]]})
    transport.add(
        "GET",
        "/history/prompt-1",
        200,
        {"prompt-1": {"outputs": {"save": {"images": []}}}},
    )
    times = iter((0.0, 0.1, 0.2))
    sleeps: list[float] = []
    provider = NativeComfyUiProvider(
        transport,
        monotonic=lambda: next(times),
        sleep=sleeps.append,
    )

    status = provider.wait_or_watch(
        "prompt-1",
        timeout_seconds=1,
        poll_interval_seconds=0.25,
    )

    assert status.completed is True
    assert sleeps == [0.25]

    timed_out = _Transport()
    timed_out.add("GET", "/history/prompt-2", 200, {})
    timed_out.add("GET", "/queue", 200, {"queue_pending": [[1, "prompt-2"]]})
    with pytest.raises(ComfyUiTimeoutError, match="did not finish"):
        NativeComfyUiProvider(
            timed_out,
            monotonic=lambda: 5.0,
            sleep=lambda seconds: None,
        ).wait_or_watch("prompt-2", timeout_seconds=0)


def test_native_provider_collects_all_output_nodes_and_batch_indexes() -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/history/prompt-1",
        200,
        {
            "prompt-1": {
                "outputs": {
                    "save-a": {
                        "images": [
                            {
                                "filename": "a.png",
                                "subfolder": "set",
                                "type": "output",
                            },
                            {
                                "filename": "b.png",
                                "subfolder": "set",
                                "type": "output",
                            },
                        ]
                    },
                    "save-b": {"images": [{"filename": "c.png"}]},
                }
            }
        },
    )

    outputs = NativeComfyUiProvider(transport).fetch_outputs("prompt-1")

    assert [
        (item.node_id, item.output_index, item.filename) for item in outputs
    ] == [
        ("save-a", 0, "a.png"),
        ("save-a", 1, "b.png"),
        ("save-b", 0, "c.png"),
    ]


@pytest.mark.parametrize(
    ("entry", "error"),
    (
        ({"status": {"status_str": "error"}}, ComfyUiRejectionError),
        (
            {"status": {"completed": True}, "outputs": []},
            ComfyUiProtocolError,
        ),
        ({"outputs": {"save": []}}, ComfyUiProtocolError),
        ({"outputs": {"save": {"images": {}}}}, ComfyUiProtocolError),
        ({"outputs": {"save": {"images": ["bad"]}}}, ComfyUiProtocolError),
        ({"outputs": {"save": {"images": [{}]}}}, ComfyUiProtocolError),
    ),
)
def test_native_provider_rejects_invalid_or_failed_outputs(
    entry, error
) -> None:
    transport = _Transport()
    transport.add("GET", "/history/prompt-1", 200, {"prompt-1": entry})
    with pytest.raises(error):
        NativeComfyUiProvider(transport).fetch_outputs("prompt-1")


def test_native_provider_handles_missing_and_incomplete_outputs() -> None:
    missing = _Transport()
    missing.add("GET", "/history/missing", 200, {})
    running = _Transport()
    running.add(
        "GET",
        "/history/running",
        200,
        {"running": {"status": {"status_str": "running"}}},
    )

    with pytest.raises(ComfyUiNotFoundError):
        NativeComfyUiProvider(missing).fetch_outputs("missing")
    assert NativeComfyUiProvider(running).fetch_outputs("running") == ()


def test_native_provider_discovers_technical_capabilities() -> None:
    transport = _Transport()
    transport.add(
        "GET",
        "/object_info",
        200,
        {
            "KSampler": {
                "input": {
                    "required": {"sampler_name": [["euler", "dpmpp"]]},
                    "optional": {"scheduler": ["normal", "karras"]},
                }
            },
            "CheckpointLoaderSimple": {
                "input": {
                    "required": {
                        "ckpt_name": [["b.safetensors", "a.safetensors"]]
                    }
                }
            },
            "SaveImage": {"input": {}},
        },
    )

    capabilities = NativeComfyUiProvider(transport).discover_capabilities()

    assert capabilities.node_classes == (
        "CheckpointLoaderSimple",
        "KSampler",
        "SaveImage",
    )
    assert capabilities.samplers == ("dpmpp", "euler")
    assert capabilities.schedulers == ("karras", "normal")
    assert capabilities.checkpoints == ("a.safetensors", "b.safetensors")


class _Response:
    def __init__(self, raw: bytes, status: int = 200) -> None:
        self._raw = raw
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return None

    def read(self):
        return self._raw


def test_urllib_transport_decodes_and_normalizes_failures(monkeypatch) -> None:
    with pytest.raises(ValueError, match="base_url is required"):
        UrlLibJsonTransport(" ")
    transport = UrlLibJsonTransport("http://localhost:8188/")
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(b'{"ok": true}'),
    )
    assert transport.request("GET", "/test", timeout_seconds=2).payload == {
        "ok": True
    }

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(TimeoutError()),
    )
    with pytest.raises(ComfyUiTimeoutError):
        transport.request("GET", "/test", timeout_seconds=2)
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(
            urllib.error.URLError("down")
        ),
    )
    with pytest.raises(ComfyUiConnectionError):
        transport.request("GET", "/test", timeout_seconds=2)

    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: _Response(b"not-json"),
    )
    with pytest.raises(ComfyUiProtocolError):
        transport.request("GET", "/test", timeout_seconds=2)

    error = urllib.error.HTTPError(
        "http://localhost/test",
        409,
        "conflict",
        Message(),
        io.BytesIO(b'{"error": "conflict"}'),
    )
    monkeypatch.setattr(
        "urllib.request.urlopen",
        lambda request, timeout: (_ for _ in ()).throw(error),
    )
    response = transport.request(
        "POST", "/test", payload={}, timeout_seconds=2
    )
    assert response.status_code == 409
    assert response.payload == {"error": "conflict"}
