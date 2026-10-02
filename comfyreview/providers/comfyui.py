"""Native technical ComfyUI provider with normalized failures."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol, cast

from comfyreview.application.comfyui import (
    ComfyUiCapabilities,
    ComfyUiConnectionError,
    ComfyUiJobStatus,
    ComfyUiNotFoundError,
    ComfyUiOutputDescriptor,
    ComfyUiProtocolError,
    ComfyUiRejectionError,
    ComfyUiSubmission,
    ComfyUiTimeoutError,
)


@dataclass(frozen=True, slots=True)
class JsonHttpResponse:
    """Carry a decoded HTTP response into the provider parser."""

    status_code: int
    payload: object


class JsonTransport(Protocol):
    """Exchange JSON with one configured HTTP service."""

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Return one decoded JSON response or raise a normalized failure."""
        ...


class UrlLibJsonTransport:
    """Own bounded urllib communication with one ComfyUI base URL."""

    def __init__(self, base_url: str) -> None:
        normalized = str(base_url or "").strip().rstrip("/")
        if not normalized:
            raise ValueError("base_url is required")
        self._base_url = normalized

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> JsonHttpResponse:
        """Send one JSON request with timeout and error normalization."""
        body = None
        headers = {"Accept": "application/json"}
        if payload is not None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            url=self._base_url + "/" + str(path or "").lstrip("/"),
            data=body,
            headers=headers,
            method=str(method).upper(),
        )
        try:
            with urllib.request.urlopen(
                request,
                timeout=max(float(timeout_seconds), 0.0),
            ) as response:
                return JsonHttpResponse(
                    status_code=int(response.status),
                    payload=self._decode(response.read()),
                )
        except urllib.error.HTTPError as error:
            return JsonHttpResponse(
                status_code=int(error.code),
                payload=self._decode(error.read()),
            )
        except TimeoutError as error:
            raise ComfyUiTimeoutError(
                "ComfyUI HTTP request timed out"
            ) from error
        except (urllib.error.URLError, OSError) as error:
            raise ComfyUiConnectionError(
                "Could not connect to ComfyUI"
            ) from error

    @staticmethod
    def _decode(raw: bytes) -> object:
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ComfyUiProtocolError(
                "ComfyUI returned invalid JSON"
            ) from error


class NativeComfyUiProvider:
    """Manage compiled graphs without knowing their semantic roles."""

    def __init__(
        self,
        transport: JsonTransport,
        *,
        request_timeout_seconds: float = 30.0,
        monotonic: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._transport = transport
        self._request_timeout_seconds = max(
            float(request_timeout_seconds), 0.0
        )
        self._monotonic = monotonic
        self._sleep = sleep

    def submit(self, compiled_graph: dict[str, Any]) -> ComfyUiSubmission:
        """Submit one already compiled graph and return its prompt ID."""
        response = self._transport.request(
            "POST",
            "/prompt",
            payload={"prompt": compiled_graph},
            timeout_seconds=self._request_timeout_seconds,
        )
        self._require_success(response, operation="submit")
        payload = self._mapping(response.payload)
        prompt_id = str(payload.get("prompt_id") or "").strip()
        if not prompt_id:
            raise ComfyUiProtocolError(
                "ComfyUI submit response has no prompt_id"
            )
        return ComfyUiSubmission(prompt_id)

    def get_status(self, prompt_id: str) -> ComfyUiJobStatus:
        """Read history and queue state for one prompt ID."""
        normalized = self._prompt_id(prompt_id)
        history = self._history(normalized)
        entry = history.get(normalized)
        if isinstance(entry, dict):
            return self._history_status(normalized, entry)
        queue_response = self._transport.request(
            "GET",
            "/queue",
            timeout_seconds=self._request_timeout_seconds,
        )
        self._require_success(queue_response, operation="queue")
        queue = self._mapping(queue_response.payload)
        if self._queued_prompt(queue, normalized, "queue_running"):
            return ComfyUiJobStatus(normalized, "running", False, False)
        if self._queued_prompt(queue, normalized, "queue_pending"):
            return ComfyUiJobStatus(normalized, "submitted", False, False)
        raise ComfyUiNotFoundError(f"Unknown ComfyUI prompt_id: {normalized}")

    def wait_or_watch(
        self,
        prompt_id: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float = 0.5,
    ) -> ComfyUiJobStatus:
        """Poll one technical job until it reaches a terminal state."""
        timeout = max(float(timeout_seconds), 0.0)
        interval = max(float(poll_interval_seconds), 0.0)
        deadline = self._monotonic() + timeout
        while True:
            status = self.get_status(prompt_id)
            if status.completed or status.failed:
                return status
            if self._monotonic() >= deadline:
                raise ComfyUiTimeoutError(
                    f"ComfyUI prompt {status.prompt_id} did not finish before timeout"
                )
            self._sleep(interval)

    def fetch_outputs(
        self,
        prompt_id: str,
    ) -> tuple[ComfyUiOutputDescriptor, ...]:
        """Return every image descriptor from every completed output node."""
        normalized = self._prompt_id(prompt_id)
        entry = self._history(normalized).get(normalized)
        if not isinstance(entry, dict):
            raise ComfyUiNotFoundError(
                f"Unknown ComfyUI prompt_id: {normalized}"
            )
        status = self._history_status(normalized, entry)
        if status.failed:
            raise ComfyUiRejectionError(
                status.message or f"ComfyUI prompt {normalized} failed"
            )
        if not status.completed:
            return ()
        outputs = entry.get("outputs")
        if not isinstance(outputs, dict):
            raise ComfyUiProtocolError("ComfyUI history outputs are invalid")
        descriptors: list[ComfyUiOutputDescriptor] = []
        for node_id, raw_output in outputs.items():
            if not isinstance(raw_output, dict):
                raise ComfyUiProtocolError("ComfyUI node output is invalid")
            images = raw_output.get("images", [])
            if not isinstance(images, list):
                raise ComfyUiProtocolError("ComfyUI image output is invalid")
            for output_index, image in enumerate(images):
                if not isinstance(image, dict):
                    raise ComfyUiProtocolError(
                        "ComfyUI image descriptor is invalid"
                    )
                filename = str(image.get("filename") or "").strip()
                if not filename:
                    raise ComfyUiProtocolError(
                        "ComfyUI image filename is missing"
                    )
                descriptors.append(
                    ComfyUiOutputDescriptor(
                        node_id=str(node_id),
                        output_index=output_index,
                        filename=filename,
                        subfolder=str(image.get("subfolder") or ""),
                        storage_type=str(image.get("type") or "output"),
                    )
                )
        return tuple(descriptors)

    def discover_capabilities(self) -> ComfyUiCapabilities:
        """Parse technical node classes and known enum inputs."""
        response = self._transport.request(
            "GET",
            "/object_info",
            timeout_seconds=self._request_timeout_seconds,
        )
        self._require_success(response, operation="capability discovery")
        objects = self._mapping(response.payload)
        sampler_info = objects.get("KSampler")
        samplers = self._enum_values(sampler_info, "sampler_name")
        schedulers = self._enum_values(sampler_info, "scheduler")
        checkpoints: tuple[str, ...] = ()
        for class_name in (
            "CheckpointLoaderSimple",
            "CheckpointLoader",
            "RandomLoadCheckpoint",
        ):
            values = self._enum_values(objects.get(class_name), "ckpt_name")
            if values:
                checkpoints = values
                break
        loras = self._enum_values(objects.get("LoraLoader"), "lora_name")
        return ComfyUiCapabilities(
            node_classes=tuple(sorted(str(key) for key in objects)),
            samplers=samplers,
            schedulers=schedulers,
            checkpoints=checkpoints,
            loras=loras,
        )

    def _history(self, prompt_id: str) -> dict[str, Any]:
        response = self._transport.request(
            "GET",
            f"/history/{prompt_id}",
            timeout_seconds=self._request_timeout_seconds,
        )
        if response.status_code == 404:
            return {}
        self._require_success(response, operation="history")
        return self._mapping(response.payload)

    @staticmethod
    def _history_status(
        prompt_id: str,
        entry: dict[str, Any],
    ) -> ComfyUiJobStatus:
        status = entry.get("status")
        status_mapping = status if isinstance(status, dict) else {}
        status_text = str(status_mapping.get("status_str") or "").lower()
        completed = bool(status_mapping.get("completed")) or bool(
            entry.get("outputs")
        )
        failed = status_text in {"error", "failed"}
        messages = status_mapping.get("messages")
        message = ""
        if isinstance(messages, list) and messages:
            message = str(messages[-1])
        state = "failed" if failed else "completed" if completed else "running"
        return ComfyUiJobStatus(prompt_id, state, completed, failed, message)

    @staticmethod
    def _queued_prompt(
        queue: dict[str, Any],
        prompt_id: str,
        key: str,
    ) -> bool:
        entries = queue.get(key)
        if not isinstance(entries, list):
            return False
        return any(
            isinstance(entry, list)
            and len(entry) > 1
            and str(entry[1]) == prompt_id
            for entry in entries
        )

    @staticmethod
    def _enum_values(raw_info: object, input_name: str) -> tuple[str, ...]:
        if not isinstance(raw_info, dict):
            return ()
        inputs = raw_info.get("input")
        if not isinstance(inputs, dict):
            return ()
        for group_name in ("required", "optional"):
            group = inputs.get(group_name)
            if not isinstance(group, dict) or input_name not in group:
                continue
            raw_values = group[input_name]
            if isinstance(raw_values, list) and raw_values:
                candidates = (
                    raw_values[0]
                    if isinstance(raw_values[0], list)
                    else raw_values
                )
                return tuple(
                    sorted(
                        {
                            value
                            for item in candidates
                            if (value := str(item).strip())
                        },
                        key=str.casefold,
                    )
                )
        return ()

    @staticmethod
    def _require_success(
        response: JsonHttpResponse, *, operation: str
    ) -> None:
        if 200 <= response.status_code < 300:
            return
        if response.status_code == 404:
            raise ComfyUiNotFoundError(f"ComfyUI {operation} returned 404")
        raise ComfyUiRejectionError(
            f"ComfyUI {operation} returned HTTP {response.status_code}"
        )

    @staticmethod
    def _mapping(payload: object) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ComfyUiProtocolError(
                "ComfyUI response must be a JSON object"
            )
        return cast(dict[str, Any], payload)

    @staticmethod
    def _prompt_id(prompt_id: str) -> str:
        normalized = str(prompt_id or "").strip()
        if not normalized:
            raise ValueError("prompt_id is required")
        return normalized
