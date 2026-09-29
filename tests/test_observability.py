"""Behavior tests for structured logs and HTTP request tracing."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.types import Message, Receive, Scope, Send

from services.observability import (
    JsonLogFormatter,
    RequestTracingMiddleware,
    configure_logging,
    get_trace_id,
    normalize_request_id,
)


@contextmanager
def _preserve_root_logging() -> Iterator[logging.Logger]:
    root_logger = logging.getLogger()
    handlers = list(root_logger.handlers)
    level = root_logger.level
    try:
        yield root_logger
    finally:
        root_logger.handlers[:] = handlers
        root_logger.setLevel(level)


def _build_test_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestTracingMiddleware)

    @app.get("/trace")
    def trace() -> dict[str, str | None]:
        return {"trace_id": get_trace_id()}

    @app.get("/controlled-error")
    def controlled_error() -> None:
        raise HTTPException(status_code=400, detail="invalid")

    return app


def test_normalizes_request_ids() -> None:
    assert normalize_request_id("caller-123:abc") == "caller-123:abc"
    generated = {
        normalize_request_id(None),
        normalize_request_id("contains a space"),
        normalize_request_id("x" * 129),
        normalize_request_id("line\nbreak"),
    }
    assert len(generated) == 4
    assert all(re.fullmatch(r"[0-9a-f]{32}", value) for value in generated)


def test_request_id_is_returned_for_success_and_controlled_error() -> None:
    with TestClient(_build_test_app()) as client:
        success = client.get("/trace", headers={"X-Request-ID": "known.id"})
        failure = client.get(
            "/controlled-error",
            headers={"X-Request-ID": "controlled:error"},
        )

    assert success.status_code == 200
    assert success.headers["X-Request-ID"] == "known.id"
    assert success.json() == {"trace_id": "known.id"}
    assert failure.status_code == 400
    assert failure.headers["X-Request-ID"] == "controlled:error"


def test_invalid_request_id_is_replaced() -> None:
    with TestClient(_build_test_app()) as client:
        response = client.get(
            "/trace",
            headers={"X-Request-ID": "contains a space"},
        )
        response_without_header = client.get("/trace")

    generated = response.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
    assert response.json() == {"trace_id": generated}
    generated_without_header = response_without_header.headers["X-Request-ID"]
    assert re.fullmatch(r"[0-9a-f]{32}", generated_without_header)


def test_request_context_is_isolated() -> None:
    with TestClient(_build_test_app()) as client:
        first = client.get("/trace", headers={"X-Request-ID": "first"})
        second = client.get("/trace", headers={"X-Request-ID": "second"})

    assert first.json() == {"trace_id": "first"}
    assert second.json() == {"trace_id": "second"}
    assert get_trace_id() is None


def test_json_formatter_uses_approved_fields() -> None:
    formatter = JsonLogFormatter()
    record = logging.LogRecord(
        name="comfyreview.test",
        level=logging.ERROR,
        pathname=__file__,
        lineno=1,
        msg="generation.failed",
        args=(),
        exc_info=None,
    )
    record.trace_id = "trace-1"
    record.status_code = 500
    record.private_prompt = "must not be logged"

    payload: dict[str, Any] = json.loads(formatter.format(record))

    assert payload["event"] == "generation.failed"
    assert payload["trace_id"] == "trace-1"
    assert payload["status_code"] == 500
    assert payload["timestamp"].endswith("Z")
    assert "private_prompt" not in payload
    assert "must not be logged" not in json.dumps(payload)


def test_json_formatter_records_exception_type() -> None:
    formatter = JsonLogFormatter()
    try:
        raise ValueError("private details")
    except ValueError:
        record = logging.LogRecord(
            name="comfyreview.test",
            level=logging.ERROR,
            pathname=__file__,
            lineno=1,
            msg="request.failed",
            args=(),
            exc_info=sys.exc_info(),
        )

    payload = json.loads(formatter.format(record))

    assert payload["exception_type"] == "ValueError"
    assert "private details" not in json.dumps(payload)


def test_configure_logging_is_idempotent() -> None:
    with _preserve_root_logging() as root_logger:
        root_logger.handlers.clear()

        configure_logging(logging.DEBUG)
        configure_logging(logging.WARNING)

        tagged_handlers = [
            handler
            for handler in root_logger.handlers
            if isinstance(handler.formatter, JsonLogFormatter)
        ]
        assert len(tagged_handlers) == 1
        assert tagged_handlers[0].level == logging.WARNING
        assert root_logger.level == logging.WARNING


def test_middleware_resets_context_after_unhandled_error() -> None:
    async def failing_app(
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        assert get_trace_id() == "failure-id"
        raise RuntimeError("boom")

    async def receive() -> Message:
        return {"type": "http.request"}

    async def send(message: Message) -> None:
        del message

    async def run_request() -> None:
        middleware = RequestTracingMiddleware(failing_app)
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/failure",
            "headers": [(b"x-request-id", b"failure-id")],
        }
        try:
            await middleware(scope, receive, send)
        except RuntimeError:
            pass

    asyncio.run(run_request())

    assert get_trace_id() is None


def test_middleware_passes_through_non_http_scope() -> None:
    received_scope: dict[str, Any] = {}

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        received_scope.update(scope)

    async def receive() -> Message:
        return {"type": "lifespan.startup"}

    async def send(message: Message) -> None:
        del message

    async def run_request() -> Scope:
        middleware = RequestTracingMiddleware(app)
        scope: Scope = {"type": "lifespan"}
        await middleware(scope, receive, send)
        return scope

    scope = asyncio.run(run_request())

    assert received_scope == scope


def test_non_ascii_request_id_is_replaced_in_response() -> None:
    sent_messages: list[Message] = []

    async def app(scope: Scope, receive: Receive, send: Send) -> None:
        await send(
            {
                "type": "http.response.start",
                "status": 204,
                "headers": [(b"x-request-id", b"old")],
            }
        )
        await send({"type": "http.response.body", "body": b""})

    async def receive() -> Message:
        return {"type": "http.request"}

    async def send(message: Message) -> None:
        sent_messages.append(message)

    async def run_request() -> None:
        middleware = RequestTracingMiddleware(app)
        scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/non-ascii",
            "headers": [(b"x-request-id", b"\xff")],
        }
        await middleware(scope, receive, send)

    asyncio.run(run_request())

    response_headers = dict(sent_messages[0]["headers"])
    generated = response_headers[b"x-request-id"].decode("ascii")
    assert re.fullmatch(r"[0-9a-f]{32}", generated)
