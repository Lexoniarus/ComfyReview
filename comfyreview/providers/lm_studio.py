"""Native LM Studio v1 model discovery and lifecycle communication."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol, cast

from comfyreview.application.local_models import (
    LocalModelConnectionError,
    LocalModelDescriptor,
    LocalModelInstance,
    LocalModelLifecycleError,
    LocalModelProtocolError,
    LocalModelTimeoutError,
    LocalModelUnavailableError,
)


@dataclass(frozen=True, slots=True)
class LmStudioJsonResponse:
    """Carry decoded HTTP status and JSON across the transport boundary."""

    status_code: int
    payload: object


class LmStudioJsonTransport(Protocol):
    """Exchange bounded JSON requests with one LM Studio server."""

    def request(
        self,
        method: str,
        path: str,
        *,
        payload: object | None = None,
        timeout_seconds: float,
    ) -> LmStudioJsonResponse:
        """Return a decoded response or normalized connection failure."""
        ...


class UrlLibLmStudioJsonTransport:
    """Own urllib communication without exposing HTTP exceptions."""

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
    ) -> LmStudioJsonResponse:
        """Send bounded JSON, preserving non-success status for mapping."""
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
                request, timeout=max(float(timeout_seconds), 0.0)
            ) as response:
                return LmStudioJsonResponse(
                    status_code=int(response.status),
                    payload=self._decode(response.read()),
                )
        except urllib.error.HTTPError as error:
            return LmStudioJsonResponse(
                status_code=int(error.code),
                payload=self._decode(error.read()),
            )
        except urllib.error.URLError as error:
            if isinstance(error.reason, TimeoutError):
                raise LocalModelTimeoutError(
                    "LM Studio HTTP request timed out"
                ) from error
            raise LocalModelConnectionError(
                "Could not connect to LM Studio"
            ) from error
        except TimeoutError as error:
            raise LocalModelTimeoutError(
                "LM Studio HTTP request timed out"
            ) from error
        except OSError as error:
            raise LocalModelConnectionError(
                "Could not connect to LM Studio"
            ) from error

    @staticmethod
    def _decode(raw: bytes) -> object:
        if not raw:
            return {}
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise LocalModelProtocolError(
                "LM Studio returned invalid JSON"
            ) from error


class NativeLmStudioProvider:
    """Normalize LM Studio's v1 lifecycle API into application values."""

    def __init__(
        self,
        transport: LmStudioJsonTransport,
        *,
        request_timeout_seconds: float = 120.0,
        lifecycle_timeout_seconds: float = 180.0,
    ) -> None:
        self._transport = transport
        self._request_timeout_seconds = max(
            float(request_timeout_seconds), 0.0
        )
        self._lifecycle_timeout_seconds = max(
            float(lifecycle_timeout_seconds), 0.0
        )

    def list_models(self) -> tuple[LocalModelDescriptor, ...]:
        """List available model keys and their concrete loaded instances."""
        response = self._transport.request(
            "GET",
            "/api/v1/models",
            timeout_seconds=self._request_timeout_seconds,
        )
        if not 200 <= response.status_code < 300:
            raise LocalModelProtocolError(
                f"LM Studio model listing returned HTTP {response.status_code}"
            )
        models = self._mapping(response.payload).get("models")
        if not isinstance(models, list):
            raise LocalModelProtocolError("LM Studio models must be a list")
        descriptors: list[LocalModelDescriptor] = []
        for raw_model in models:
            model = self._mapping(raw_model)
            model_id = self._identifier(model.get("key"), "model key")
            raw_instances = model.get("loaded_instances")
            if not isinstance(raw_instances, list):
                raise LocalModelProtocolError(
                    "LM Studio loaded_instances must be a list"
                )
            loaded = tuple(
                sorted(
                    (
                        LocalModelInstance(
                            model_id,
                            self._identifier(
                                self._mapping(raw_instance).get("id"),
                                "instance id",
                            ),
                        )
                        for raw_instance in raw_instances
                    ),
                    key=lambda item: (
                        item.instance_id.casefold(),
                        item.instance_id,
                    ),
                )
            )
            descriptors.append(LocalModelDescriptor(model_id, loaded))
        return tuple(
            sorted(
                descriptors,
                key=lambda item: (item.model_id.casefold(), item.model_id),
            )
        )

    def load_model(self, model_id: str) -> LocalModelInstance:
        """Load one named model and return the exact created instance ID."""
        if not isinstance(model_id, str) or not model_id.strip():
            raise ValueError("model_id is required")
        normalized = model_id.strip()
        response = self._transport.request(
            "POST",
            "/api/v1/models/load",
            payload={"model": normalized},
            timeout_seconds=self._lifecycle_timeout_seconds,
        )
        if response.status_code == 404:
            raise LocalModelUnavailableError(
                f"LM Studio model not found: {normalized}"
            )
        self._require_lifecycle_success(response, "load")
        payload = self._mapping(response.payload)
        instance_id = self._identifier(
            payload.get("instance_id"), "instance id"
        )
        if payload.get("status") != "loaded":
            raise LocalModelProtocolError(
                "LM Studio load response has no loaded status"
            )
        return LocalModelInstance(normalized, instance_id)

    def unload_model(self, instance: LocalModelInstance) -> None:
        """Unload precisely the given instance, never its whole model."""
        if (
            not isinstance(instance.instance_id, str)
            or not instance.instance_id.strip()
        ):
            raise ValueError("instance_id is required")
        instance_id = instance.instance_id.strip()
        response = self._transport.request(
            "POST",
            "/api/v1/models/unload",
            payload={"instance_id": instance_id},
            timeout_seconds=self._lifecycle_timeout_seconds,
        )
        self._require_lifecycle_success(response, "unload")
        returned_id = self._identifier(
            self._mapping(response.payload).get("instance_id"),
            "instance id",
        )
        if returned_id != instance_id:
            raise LocalModelProtocolError(
                "LM Studio unload response contains another instance id"
            )

    @staticmethod
    def _mapping(payload: object) -> dict[str, object]:
        if not isinstance(payload, dict):
            raise LocalModelProtocolError(
                "LM Studio response must be a JSON object"
            )
        return cast(dict[str, object], payload)

    @staticmethod
    def _identifier(value: object, label: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise LocalModelProtocolError(
                f"LM Studio {label} must be a nonempty string"
            )
        return value.strip()

    @staticmethod
    def _require_lifecycle_success(
        response: LmStudioJsonResponse, operation: str
    ) -> None:
        if not 200 <= response.status_code < 300:
            raise LocalModelLifecycleError(
                f"LM Studio {operation} returned HTTP {response.status_code}"
            )
