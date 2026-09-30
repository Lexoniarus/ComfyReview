"""Filesystem provider for native ComfyUI output collection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from comfyreview.application import (
    CollectedOutputFile,
    ComfyUiOutputDescriptor,
    GenerationOutputError,
)


class LocalGenerationOutputSource:
    """Resolve raw ComfyUI output descriptors inside the output root."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = Path(output_root).resolve()

    def resolve(
        self, descriptor: ComfyUiOutputDescriptor
    ) -> CollectedOutputFile:
        """Validate one output path and compute its SHA-256 content hash."""
        if descriptor.storage_type != "output":
            raise GenerationOutputError(
                f"unsupported ComfyUI storage type: {descriptor.storage_type}"
            )
        candidate = (
            self._output_root / descriptor.subfolder / descriptor.filename
        ).resolve()
        try:
            candidate.relative_to(self._output_root)
        except ValueError as error:
            raise GenerationOutputError(
                "ComfyUI output escapes output root"
            ) from error
        if not candidate.is_file():
            raise GenerationOutputError(
                f"ComfyUI output file is missing: {candidate.name}"
            )
        digest = hashlib.sha256()
        with candidate.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return CollectedOutputFile(candidate, digest.hexdigest())
