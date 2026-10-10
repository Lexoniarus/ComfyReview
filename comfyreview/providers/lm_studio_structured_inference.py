"""Schema-constrained LM Studio chat completions via the shared transport."""

from __future__ import annotations

import json
from math import isfinite
from typing import cast

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError

from comfyreview.application.local_model_inference import (
    LocalInferenceUsage,
    LocalModelInferenceError,
)
from comfyreview.application.local_model_structured_inference import (
    JsonValue,
    LocalModelStructuredOutputError,
    LocalStructuredInferenceRequest,
    LocalStructuredInferenceResult,
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

_MAX_RESPONSE_BYTES = 128 * 1024


def _reject_nonfinite(value: str) -> None:
    raise ValueError("Non-finite JSON number")


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    document: dict[str, object] = {}
    for key, value in pairs:
        if key in document:
            raise ValueError("Duplicate JSON object key")
        document[key] = value
    return document


class NativeLmStudioStructuredInferenceProvider:
    """Generate schema-constrained JSON and validate it independently."""

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
            raise ValueError("request_timeout_seconds must be positive and finite")
        self._transport = transport
        self._request_timeout_seconds = float(request_timeout_seconds)

    def infer_structured(
        self, request: LocalStructuredInferenceRequest
    ) -> LocalStructuredInferenceResult:
        """Return checked JSON; OpenAI-compatible API has no instance ID."""
        if not isinstance(request, LocalStructuredInferenceRequest):
            raise TypeError("request must be LocalStructuredInferenceRequest")
        inference = request.inference
        user_content: str | list[dict[str, object]] = inference.user_text
        if inference.image_data_url is not None:
            user_content = [
                {"type": "text", "text": inference.user_text},
                {
                    "type": "image_url",
                    "image_url": {"url": inference.image_data_url},
                },
            ]
        messages: list[dict[str, object]] = []
        if inference.system_prompt is not None:
            messages.append(
                {"role": "system", "content": inference.system_prompt}
            )
        messages.append({"role": "user", "content": user_content})
        payload: dict[str, object] = {
            "model": inference.model_id,
            "messages": messages,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": request.schema_name,
                    "strict": True,
                    "schema": request.schema_document(),
                },
            },
            "max_tokens": inference.max_output_tokens,
            "stream": False,
        }
        try:
            response = self._transport.request(
                "POST",
                "/v1/chat/completions",
                payload=payload,
                timeout_seconds=self._request_timeout_seconds,
            )
        except LocalModelError:
            raise
        except TimeoutError as error:
            raise LocalModelTimeoutError("LM Studio structured inference timed out") from error
        except OSError as error:
            raise LocalModelConnectionError("Could not connect to LM Studio for structured inference") from error
        return self._normalize_response(response, request)

    @staticmethod
    def _normalize_response(
        response: LmStudioJsonResponse,
        request: LocalStructuredInferenceRequest,
    ) -> LocalStructuredInferenceResult:
        if not isinstance(response, LmStudioJsonResponse):
            raise LocalModelProtocolError("Invalid LM Studio structured transport response")
        status = response.status_code
        if type(status) is not int or not 100 <= status <= 599:
            raise LocalModelProtocolError("Invalid LM Studio HTTP status")
        if status == 404:
            raise LocalModelUnavailableError("LM Studio model is unavailable (HTTP 404)")
        if 400 <= status < 500:
            raise LocalModelInferenceError(
                f"LM Studio rejected structured inference (HTTP {status})"
            )
        if status >= 500:
            raise LocalModelError(
                f"LM Studio structured inference failed (HTTP {status})"
            )
        if not 200 <= status < 300:
            raise LocalModelProtocolError("Unexpected LM Studio HTTP status")
        body = response.payload
        if not isinstance(body, dict):
            raise LocalModelProtocolError("LM Studio completion must be a JSON object")
        data = cast(dict[str, object], body)
        raw_model = data.get("model")
        if raw_model is None:
            reported_model: str | None = None
        elif (
            not isinstance(raw_model, str)
            or not raw_model
            or raw_model != raw_model.strip()
        ):
            raise LocalModelProtocolError("Invalid reported LM Studio model")
        else:
            reported_model = raw_model
        choices = data.get("choices")
        if not isinstance(choices, list) or len(choices) != 1:
            raise LocalModelProtocolError("LM Studio completion must contain one choice")
        choice = choices[0]
        if not isinstance(choice, dict):
            raise LocalModelProtocolError("Invalid LM Studio choice")
        item = cast(dict[str, object], choice)
        if item.get("finish_reason") != "stop":
            raise LocalModelProtocolError("LM Studio completion did not finish normally")
        message = item.get("message")
        if not isinstance(message, dict):
            raise LocalModelProtocolError("Invalid LM Studio assistant message")
        result_message = cast(dict[str, object], message)
        if result_message.get("role") != "assistant":
            raise LocalModelProtocolError("Invalid LM Studio assistant role")
        if result_message.get("refusal") is not None:
            raise LocalModelProtocolError("LM Studio refused structured output")
        if result_message.get("tool_calls") is not None or (
            result_message.get("function_call") is not None
        ):
            raise LocalModelProtocolError("Unexpected tool call in structured inference")
        content = result_message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise LocalModelProtocolError("Missing structured JSON content")
        if len(content.encode("utf-8")) > _MAX_RESPONSE_BYTES:
            raise LocalModelProtocolError("Structured JSON exceeds size limit")
        try:
            value = cast(
                JsonValue,
                json.loads(
                    content,
                    parse_constant=_reject_nonfinite,
                    object_pairs_hook=_unique_object,
                ),
            )
            json.dumps(value, allow_nan=False)
        except (ValueError, TypeError) as error:
            raise LocalModelProtocolError("LM Studio returned invalid structured JSON") from error
        try:
            Draft202012Validator(request.schema_document()).validate(value)
        except ValidationError as error:
            raise LocalModelStructuredOutputError("LM Studio JSON does not match the requested schema") from error
        except Exception as error:
            # Invalid or cyclic references must not escape as raw errors.
            raise LocalModelProtocolError("LM Studio JSON schema resolution failed") from error
        return LocalStructuredInferenceResult(
            requested_model_id=request.inference.model_id,
            reported_model_id=reported_model,
            document=value,
            usage=NativeLmStudioStructuredInferenceProvider._usage(
                data.get("usage")
            ),
        )

    @staticmethod
    def _usage(raw: object) -> LocalInferenceUsage | None:
        if raw is None:
            return None
        if not isinstance(raw, dict):
            raise LocalModelProtocolError("Invalid LM Studio usage statistics")
        usage = cast(dict[str, object], raw)
        details = usage.get("completion_tokens_details")
        if details is not None and not isinstance(details, dict):
            raise LocalModelProtocolError("Invalid LM Studio usage details")
        reasoning: object = None
        if isinstance(details, dict):
            reasoning = cast(dict[str, object], details).get(
                "reasoning_tokens"
            )
        try:
            return LocalInferenceUsage(
                input_tokens=cast(int, usage.get("prompt_tokens")),
                total_output_tokens=cast(
                    int, usage.get("completion_tokens")
                ),
                reasoning_output_tokens=cast(int | None, reasoning),
            )
        except ValueError as error:
            raise LocalModelProtocolError("Invalid LM Studio token counters") from error
