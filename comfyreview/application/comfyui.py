"""Application-facing contracts for technical ComfyUI communication."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class ComfyUiError(RuntimeError):
    """Base class for normalized ComfyUI boundary failures."""


class ComfyUiTimeoutError(ComfyUiError):
    """Report that a bounded transport or wait deadline elapsed."""


class ComfyUiConnectionError(ComfyUiError):
    """Report that ComfyUI could not be reached."""


class ComfyUiRejectionError(ComfyUiError):
    """Report an explicit non-success response from ComfyUI."""


class ComfyUiNotFoundError(ComfyUiError):
    """Report that ComfyUI does not know the requested prompt ID."""


class ComfyUiProtocolError(ComfyUiError):
    """Report a malformed or unsupported ComfyUI response."""


@dataclass(frozen=True, slots=True)
class ComfyUiSubmission:
    """Identify one graph accepted by ComfyUI."""

    prompt_id: str


@dataclass(frozen=True, slots=True)
class ComfyUiJobStatus:
    """Describe one technical external job state."""

    prompt_id: str
    state: str
    completed: bool
    failed: bool
    message: str = ""


@dataclass(frozen=True, slots=True)
class ComfyUiOutputDescriptor:
    """Describe one raw output returned by one ComfyUI node."""

    node_id: str
    output_index: int
    filename: str
    subfolder: str
    storage_type: str


@dataclass(frozen=True, slots=True)
class ComfyUiCapabilities:
    """Contain technical node and enum capabilities reported by ComfyUI."""

    node_classes: tuple[str, ...]
    samplers: tuple[str, ...]
    schedulers: tuple[str, ...]
    checkpoints: tuple[str, ...]


class ComfyUiProvider(Protocol):
    """Submit compiled graphs and manage their external technical jobs."""

    def submit(self, compiled_graph: dict[str, Any]) -> ComfyUiSubmission:
        """Submit one already compiled graph."""
        ...

    def get_status(self, prompt_id: str) -> ComfyUiJobStatus:
        """Read the current external state for one prompt ID."""
        ...

    def wait_or_watch(
        self,
        prompt_id: str,
        *,
        timeout_seconds: float,
        poll_interval_seconds: float = 0.5,
    ) -> ComfyUiJobStatus:
        """Wait until a job completes or fails within a bounded deadline."""
        ...

    def fetch_outputs(
        self,
        prompt_id: str,
    ) -> tuple[ComfyUiOutputDescriptor, ...]:
        """Return raw technical output descriptors for a completed job."""
        ...

    def discover_capabilities(self) -> ComfyUiCapabilities:
        """Read node classes and enum values exposed by ComfyUI."""
        ...
