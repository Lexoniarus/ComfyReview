"""Structured logging and request trace propagation for the legacy app."""

from __future__ import annotations

import json
import logging
import re
import time
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any, Final
from uuid import uuid4

from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TRACE_ID: ContextVar[str | None] = ContextVar("trace_id", default=None)
_REQUEST_ID_PATTERN: Final = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
_REQUEST_ID_HEADER: Final = b"x-request-id"
_LOG_FIELDS: Final = (
    "duration_ms",
    "error_category",
    "generation_id",
    "image_id",
    "job_id",
    "request_method",
    "request_path",
    "status_code",
)


def get_trace_id() -> str | None:
    """Return the trace ID bound to the current execution context."""
    return _TRACE_ID.get()


def normalize_request_id(value: str | None) -> str:
    """Return a safe caller-provided request ID or a generated UUID."""
    if value and _REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex


class JsonLogFormatter(logging.Formatter):
    """Format approved log fields as a stable JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize one log record without copying arbitrary extra fields."""
        timestamp = datetime.fromtimestamp(record.created, UTC)
        payload: dict[str, Any] = {
            "event": record.getMessage(),
            "level": record.levelname,
            "logger": record.name,
            "timestamp": timestamp.isoformat().replace("+00:00", "Z"),
            "trace_id": getattr(record, "trace_id", None) or get_trace_id(),
        }
        for field_name in _LOG_FIELDS:
            value = getattr(record, field_name, None)
            if value is not None:
                payload[field_name] = value
        if record.exc_info:
            exception_type = record.exc_info[0]
            if exception_type is not None:
                payload["exception_type"] = exception_type.__name__
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)


class _ComfyReviewHandler(logging.StreamHandler[Any]):
    pass


def configure_logging(level: int = logging.INFO) -> None:
    """Install the idempotent ComfyReview JSON handler on the root logger."""
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    for handler in root_logger.handlers:
        if isinstance(handler, _ComfyReviewHandler):
            handler.setLevel(level)
            return
    handler = _ComfyReviewHandler()
    handler.setLevel(level)
    handler.setFormatter(JsonLogFormatter())
    root_logger.addHandler(handler)


def _read_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name.lower() != _REQUEST_ID_HEADER:
            continue
        try:
            return value.decode("ascii")
        except UnicodeDecodeError:
            return None
    return None


def _response_headers(message: Message, trace_id: str) -> Message:
    copied_message = dict(message)
    headers = [
        (name, value)
        for name, value in message.get("headers", [])
        if name.lower() != _REQUEST_ID_HEADER
    ]
    headers.append((_REQUEST_ID_HEADER, trace_id.encode("ascii")))
    copied_message["headers"] = headers
    return copied_message


class RequestTracingMiddleware:
    """Propagate a safe trace ID through one HTTP ASGI request."""

    def __init__(self, app: ASGIApp) -> None:
        self._app = app
        self._logger = logging.getLogger("comfyreview.http")

    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
    ) -> None:
        if scope["type"] != "http":
            await self._app(scope, receive, send)
            return
        trace_id = normalize_request_id(_read_request_id(scope))
        token = _TRACE_ID.set(trace_id)
        started_at = time.perf_counter()
        status_code = 500

        async def send_with_trace(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = int(message["status"])
                message = _response_headers(message, trace_id)
            await send(message)

        request_fields = {
            "request_method": scope.get("method", ""),
            "request_path": scope.get("path", ""),
        }
        self._logger.info("http.request_started", extra=request_fields)
        try:
            await self._app(scope, receive, send_with_trace)
        except Exception as error:
            self._logger.exception(
                "http.request_failed",
                extra={
                    **request_fields,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        3,
                    ),
                    "error_category": type(error).__name__,
                },
            )
            raise
        else:
            self._logger.info(
                "http.request_completed",
                extra={
                    **request_fields,
                    "duration_ms": round(
                        (time.perf_counter() - started_at) * 1000,
                        3,
                    ),
                    "status_code": status_code,
                },
            )
        finally:
            _TRACE_ID.reset(token)
