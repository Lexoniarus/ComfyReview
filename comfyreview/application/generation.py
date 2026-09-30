"""Application contracts shared by prepared generation requests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class GenerationPromptSnapshot:
    """Keep rendered prompts and the exact catalog revisions used."""

    positive_text: str
    negative_text: str
    revision_uids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationSamplerSettings:
    """Describe one explicitly named sampler stage in a generation request."""

    role: str
    seed: int
    steps: int
    cfg: float
    sampler: str
    scheduler: str
    denoise: float


@dataclass(frozen=True, slots=True)
class GenerationOutputPolicy:
    """Carry output naming intent decided before workflow compilation."""

    output_subdirectory: str
    filename_prefix: str
    expected_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GenerationRequest:
    """Describe one prepared generation without workflow implementation."""

    prompt: GenerationPromptSnapshot
    blueprint_uid: str
    blueprint_version: int | None
    checkpoint: str | None
    sampler_stages: tuple[GenerationSamplerSettings, ...]
    output_policy: GenerationOutputPolicy
    reference_image: str | None = None


@dataclass(frozen=True, slots=True)
class GenerationSubmission:
    """Identify one accepted asynchronous generation request."""

    generation_uid: str
    status: str


class GenerationPort(Protocol):
    """Accept prepared generation work without exposing its implementation."""

    def submit(self, request: GenerationRequest) -> GenerationSubmission:
        """Submit one prepared request and return its canonical identity."""
        ...
