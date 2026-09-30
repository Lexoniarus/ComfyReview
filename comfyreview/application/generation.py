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
class GenerationRequest:
    """Describe one prepared generation without workflow implementation."""

    prompt: GenerationPromptSnapshot
    checkpoint: str | None
    sampler: str | None
    scheduler: str | None
    seed: int
    steps: int | None
    cfg: float | None
    denoise: float | None
    output_subdirectory: str


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
