"""Immutable contracts for bounded local text and vision inference."""

from __future__ import annotations

import base64
import binascii
from dataclasses import dataclass, field
from typing import Protocol

from comfyreview.application.local_models import LocalModelError

_MAX_OUTPUT_TOKENS = 8192
_MAX_IMAGE_BYTES = 16 * 1024 * 1024
_IMAGE_PREFIXES = (
    "data:image/png;base64,",
    "data:image/jpeg;base64,",
    "data:image/webp;base64,",
    "data:image/gif;base64,",
)


class LocalModelInferenceError(LocalModelError):
    """Report an explicit rejection of a local inference request."""


def _validate_image_data_url(value: str) -> None:
    """Validate a bounded, base64-encoded raster image data URL."""
    prefix = next((p for p in _IMAGE_PREFIXES if value.startswith(p)), None)
    if prefix is None:
        raise ValueError("image_data_url must be a base64 image data URL")
    encoded = value[len(prefix) :]
    if not encoded or len(encoded) > 4 * ((_MAX_IMAGE_BYTES + 2) // 3):
        raise ValueError("image_data_url is empty or exceeds the size limit")
    try:
        image = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as error:
        raise ValueError("image_data_url contains invalid base64") from error
    if not image or len(image) > _MAX_IMAGE_BYTES:
        raise ValueError("image_data_url is empty or exceeds the size limit")


@dataclass(frozen=True, slots=True)
class LocalInferenceRequest:
    """Request one stateless, token-bounded local inference operation."""

    model_id: str
    user_text: str = field(repr=False)
    max_output_tokens: int
    system_prompt: str | None = field(default=None, repr=False)
    image_data_url: str | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        if (
            not isinstance(self.model_id, str)
            or not self.model_id
            or self.model_id != self.model_id.strip()
        ):
            raise ValueError("model_id must be a nonempty exact identifier")
        if not isinstance(self.user_text, str) or not self.user_text.strip():
            raise ValueError("user_text must be nonempty")
        if (
            type(self.max_output_tokens) is not int
            or not 1 <= self.max_output_tokens <= _MAX_OUTPUT_TOKENS
        ):
            raise ValueError(
                "max_output_tokens is outside the supported range"
            )
        if self.system_prompt is not None and (
            not isinstance(self.system_prompt, str)
            or not self.system_prompt.strip()
        ):
            raise ValueError("system_prompt must be nonempty if provided")
        if self.image_data_url is not None:
            if not isinstance(self.image_data_url, str):
                raise ValueError("image_data_url must be a string")
            _validate_image_data_url(self.image_data_url)


@dataclass(frozen=True, slots=True)
class LocalInferenceUsage:
    """Contain validated LM Studio token counters, when reported."""

    input_tokens: int
    total_output_tokens: int
    reasoning_output_tokens: int | None = None

    def __post_init__(self) -> None:
        if (
            type(self.input_tokens) is not int
            or self.input_tokens < 0
            or type(self.total_output_tokens) is not int
            or self.total_output_tokens < 0
        ):
            raise ValueError("token counts must be nonnegative integers")
        if self.reasoning_output_tokens is not None and (
            type(self.reasoning_output_tokens) is not int
            or self.reasoning_output_tokens < 0
            or self.reasoning_output_tokens > self.total_output_tokens
        ):
            raise ValueError("reasoning token count is invalid")


@dataclass(frozen=True, slots=True)
class LocalInferenceResult:
    """Expose validated answer text and the reported serving instance."""

    text: str = field(repr=False)
    model_instance_id: str
    usage: LocalInferenceUsage | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.text, str) or not self.text.strip():
            raise ValueError("inference text must be nonempty")
        if (
            not isinstance(self.model_instance_id, str)
            or not self.model_instance_id
            or self.model_instance_id != self.model_instance_id.strip()
        ):
            raise ValueError("model_instance_id must be a nonempty identifier")
        if self.usage is not None and not isinstance(
            self.usage, LocalInferenceUsage
        ):
            raise ValueError("usage must be validated token counters")


class LocalInferenceProvider(Protocol):
    """Accept typed inference requests without owning a model lifecycle."""

    def infer(self, request: LocalInferenceRequest) -> LocalInferenceResult:
        """Return a validated local-model answer and instance provenance."""
        ...
