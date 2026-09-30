"""Application boundary for idempotent native generation output collection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from comfyreview.application.comfyui import (
    ComfyUiOutputDescriptor,
    ComfyUiProvider,
)
from comfyreview.application.workflow_compilation import CompiledOutputBinding


class GenerationOutputError(RuntimeError):
    """Base class for invalid or failed output collection."""


class MissingGenerationOutputError(GenerationOutputError):
    """Report an expected output node that produced no image."""


class UnexpectedGenerationOutputError(GenerationOutputError):
    """Report an image produced by an unbound output node."""


class DuplicateGenerationOutputError(GenerationOutputError):
    """Report duplicate output identity within one ComfyUI response."""


@dataclass(frozen=True, slots=True)
class CollectedOutputFile:
    """Describe one provider-validated output file and its content identity."""

    path: Path
    content_hash: str


@dataclass(frozen=True, slots=True)
class GenerationOutput:
    """Describe one canonical image emitted by one graph node and batch index."""

    image_uid: str
    role: str
    node_id: str
    output_index: int
    path: Path
    content_hash: str


class GenerationOutputSource(Protocol):
    """Resolve and hash one raw ComfyUI output descriptor."""

    def resolve(
        self, descriptor: ComfyUiOutputDescriptor
    ) -> CollectedOutputFile:
        """Return one validated local output file."""
        ...


class GenerationOutputRepository(Protocol):
    """Read expected bindings and persist canonical outputs atomically."""

    def expected_bindings(
        self,
        generation_uid: str,
    ) -> tuple[CompiledOutputBinding, ...]:
        """Return output roles compiled for one generation."""
        ...

    def save_outputs(
        self,
        generation_uid: str,
        outputs: tuple[GenerationOutput, ...],
    ) -> tuple[GenerationOutput, ...]:
        """Idempotently persist every collected output in one transaction."""
        ...

    def outputs_complete(self, generation_uid: str) -> bool:
        """Return whether all expected role/node bindings have outputs."""
        ...


def generation_output_identity(
    generation_uid: str,
    node_id: str,
    output_index: int,
    content_hash: str,
) -> str:
    """Return stable content-backed identity independent of the file path."""
    payload = (
        f"{generation_uid}\0{node_id}\0{int(output_index)}\0{content_hash}"
    )
    return "image-" + hashlib.sha256(payload.encode()).hexdigest()


class GenerationOutputCollector:
    """Map raw provider outputs to expected roles and persist them once."""

    def __init__(
        self,
        *,
        comfyui: ComfyUiProvider,
        source: GenerationOutputSource,
        repository: GenerationOutputRepository,
    ) -> None:
        self._comfyui = comfyui
        self._source = source
        self._repository = repository

    def collect(
        self,
        generation_uid: str,
        prompt_id: str,
    ) -> tuple[GenerationOutput, ...]:
        """Collect all expected outputs and reject missing or unexpected nodes."""
        bindings = self._repository.expected_bindings(generation_uid)
        roles_by_node = self._roles_by_node(bindings)
        descriptors = self._comfyui.fetch_outputs(prompt_id)
        self._validate_descriptors(roles_by_node, descriptors)
        outputs: list[GenerationOutput] = []
        for descriptor in descriptors:
            collected = self._source.resolve(descriptor)
            outputs.append(
                GenerationOutput(
                    image_uid=generation_output_identity(
                        generation_uid,
                        descriptor.node_id,
                        descriptor.output_index,
                        collected.content_hash,
                    ),
                    role=roles_by_node[descriptor.node_id],
                    node_id=descriptor.node_id,
                    output_index=descriptor.output_index,
                    path=collected.path,
                    content_hash=collected.content_hash,
                )
            )
        return self._repository.save_outputs(generation_uid, tuple(outputs))

    def outputs_complete(self, generation_uid: str) -> bool:
        """Return whether a prior atomic collection stored every binding."""
        return self._repository.outputs_complete(generation_uid)

    @staticmethod
    def _roles_by_node(
        bindings: tuple[CompiledOutputBinding, ...],
    ) -> dict[str, str]:
        roles: dict[str, str] = {}
        for binding in bindings:
            if binding.node_id in roles:
                raise DuplicateGenerationOutputError(
                    f"multiple output roles bind node {binding.node_id}"
                )
            roles[binding.node_id] = binding.role
        if not roles:
            raise MissingGenerationOutputError(
                "generation has no expected outputs"
            )
        return roles

    @staticmethod
    def _validate_descriptors(
        roles_by_node: dict[str, str],
        descriptors: tuple[ComfyUiOutputDescriptor, ...],
    ) -> None:
        keys: set[tuple[str, int]] = set()
        seen_nodes: set[str] = set()
        for descriptor in descriptors:
            if descriptor.node_id not in roles_by_node:
                raise UnexpectedGenerationOutputError(
                    f"unexpected output node {descriptor.node_id}"
                )
            key = (descriptor.node_id, descriptor.output_index)
            if key in keys:
                raise DuplicateGenerationOutputError(
                    f"duplicate output {descriptor.node_id}:{descriptor.output_index}"
                )
            keys.add(key)
            seen_nodes.add(descriptor.node_id)
        missing = set(roles_by_node) - seen_nodes
        if missing:
            raise MissingGenerationOutputError(
                "missing output nodes: " + ", ".join(sorted(missing))
            )
