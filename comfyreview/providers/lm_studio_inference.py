"""Native LM Studio v1 chat inference via the existing JSON transport."""

from __future__ import annotations

from math import isfinite
from typing import cast

from comfyreview.application.local_model_inference import (
    LocalInferenceRequest,
    LocalInferenceResult,
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
from comfyreview.providers.lm_studio import (
    LmStudioJsonResponse,
    LmStudioJsonTransport,
)


class NativeLmStudioInferenceProvider:
    """Perform bounded text or image-assisted native chat inference."""

    def __init__(
        self,
        transport: LmStudioJsonTransport,
        *,
        request_timeout_seconds: float = 120.0,
    ) -> None:
        if (
            isinstance(request_timeout_seconds, bool)
            or not isinstance(request_timeout_seconds, (int, float))
            or not isfinite(request_timeout_seconds)
            or request_timeout_seconds <= 0
        ):
            raise ValueError(
                "request_timeout_seconds must be positive and finite"
            )
        self._transport = transport
        self._request_timeout_seconds = float(request_timeout_seconds)

    def infer(self, request: LocalInferenceRequest) -> LocalInferenceResult:
        """Send one stateless request and normalize the complete response."""
        if not isinstance(request, LocalInferenceRequest):
            raise TypeError("request must be LocalInferenceRequest")
        input_value: str | list[dict[str, str]] = request.user_text
        if request.image_data_url is not None:
            input_value = [
                {"type": "text", "content": request.user_text},
                {"type": "image", "data_url": request.image_data_url},
            ]
        payload: dict[str, object] = {
            "model": request.model_id,
            "input": input_value,
            "stream": False,
            "store": False,
            "max_output_tokens": request.max_output_tokens,
        }
        if request.system_prompt is not None:
            payload["system_prompt"] = request.system_prompt
        try:
            response = self._transport.request(
                "POST",
                "/api/v1/chat",
                payload=payload,
                timeout_seconds=self._request_timeout_seconds,
            )
        except LocalModelError:
            raise
        except TimeoutError as error:
            raise LocalModelTimeoutError(
                "LM Studio inference timed out"
            ) from error
        except OSError as error:
            raise LocalModelConnectionError(
                "Could not connect to LM Studio for inference"
            ) from error
        return self._normalize_response(response)

    @staticmethod
    def _normalize_response(
        response: LmStudioJsonResponse,
    ) -> LocalInferenceResult:
        if not isinstance(response, LmStudioJsonResponse):
            raise LocalModelProtocolError(
                "Invalid LM Studio transport response"
            )
        status = response.status_code
        if type(status) is not int or not 100 <= status <= 599:
            raise LocalModelProtocolError("Invalid LM Studio HTTP status")
        if status == 404:
            raise LocalModelUnavailableError(
                "LM Studio model is unavailable for inference (HTTP 404)"
            )
        if 400 <= status < 500:
            raise LocalModelInferenceError(
                f"LM Studio rejected inference (HTTP {status})"
            )
        if status >= 500:
            raise LocalModelError(
                f"LM Studio inference failed (HTTP {status})"
            )
        if not 200 <= status < 300:
            raise LocalModelProtocolError("Unexpected LM Studio HTTP status")
        body = response.payload
        if not isinstance(body, dict):
            raise LocalModelProtocolError(
                "LM Studio chat must be a JSON object"
            )
        data = cast(dict[str, object], body)
        instance_id = data.get("model_instance_id")
        if (
            not isinstance(instance_id, str)
            or not instance_id
            or instance_id != instance_id.strip()
        ):
            raise LocalModelProtocolError(
                "Invalid LM Studio model_instance_id"
            )
        output = data.get("output")
        if not isinstance(output, list):
            raise LocalModelProtocolError("LM Studio output must be an array")
        messages: list[str] = []
        for entry in output:
            if not isinstance(entry, dict):
                raise LocalModelProtocolError("Invalid LM Studio output item")
            item = cast(dict[str, object], entry)
            item_type = item.get("type")
            if not isinstance(item_type, str):
                raise LocalModelProtocolError("Invalid LM Studio output type")
            if item_type == "message":
                content = item.get("content")
                if not isinstance(content, str):
                    raise LocalModelProtocolError(
                        "Invalid LM Studio message text"
                    )
                if content.strip():
                    messages.append(content.strip())
            elif item_type == "reasoning":
                if not isinstance(item.get("content"), str):
                    raise LocalModelProtocolError(
                        "Invalid LM Studio reasoning item"
                    )
            elif item_type in {"tool_call", "invalid_tool_call"}:
                raise LocalModelProtocolError(
                    "Unexpected tool call in LM Studio inference"
                )
            else:
                raise LocalModelProtocolError("Unknown LM Studio output item")
        if not messages:
            raise LocalModelProtocolError(
                "LM Studio produced no textual message"
            )
        return LocalInferenceResult(
            text="\n".join(messages),
            model_instance_id=instance_id,
            usage=NativeLmStudioInferenceProvider._usage(data.get("stats")),
        )

    @staticmethod
    def _usage(raw: object) -> LocalInferenceUsage | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise LocalModelProtocolError("Invalid LM Studio usage statistics")
        stats = cast(dict[str, object], raw)
        try:
            return LocalInferenceUsage(
                input_tokens=cast(int, stats.get("input_tokens")),
                total_output_tokens=cast(
                    int, stats.get("total_output_tokens")
                ),
                reasoning_output_tokens=cast(
                    int | None, stats.get("reasoning_output_tokens")
                ),
            )
        except ValueError as error:
            raise LocalModelProtocolError(
                "Invalid LM Studio token counters"
            ) from error
