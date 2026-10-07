"""Filesystem provider for native ComfyUI output collection."""

from __future__ import annotations

import hashlib
from pathlib import Path

from comfyreview.application import (
    CollectedOutputFile,
    ComfyUiOutputDescriptor,
    DuplicateGenerationOutputError,
    GenerationOutputError,
    GenerationOutputRecoveryPlan,
    MissingGenerationOutputError,
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


class LocalGenerationOutputRecoverySource:
    """Discover one exact persisted PNG output without path heuristics."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = Path(output_root).resolve()

    def discover(
        self,
        plan: GenerationOutputRecoveryPlan,
    ) -> tuple[ComfyUiOutputDescriptor, ...]:
        """Return one unambiguous descriptor for one expected output node."""
        if len(plan.bindings) != 1:
            raise GenerationOutputError(
                "filesystem recovery requires exactly one output binding"
            )
        prefix = str(plan.filename_prefix or "").strip()
        if (
            not prefix
            or Path(prefix).name != prefix
            or "/" in prefix
            or "\\" in prefix
        ):
            raise GenerationOutputError(
                "filesystem recovery filename prefix is invalid"
            )
        directory = (
            self._output_root / str(plan.output_subdirectory or "")
        ).resolve()
        try:
            directory.relative_to(self._output_root)
        except ValueError as error:
            raise GenerationOutputError(
                "filesystem recovery directory escapes output root"
            ) from error
        matches = (
            tuple(
                sorted(
                    (
                        path
                        for path in directory.iterdir()
                        if path.is_file()
                        and path.suffix.lower() == ".png"
                        and path.name.startswith(prefix + "_")
                    ),
                    key=lambda path: path.name,
                )
            )
            if directory.is_dir()
            else ()
        )
        if not matches:
            raise MissingGenerationOutputError(
                "no exact filesystem recovery output was found"
            )
        if len(matches) != 1:
            raise DuplicateGenerationOutputError(
                "filesystem recovery output is ambiguous"
            )
        binding = plan.bindings[0]
        return (
            ComfyUiOutputDescriptor(
                node_id=binding.node_id,
                output_index=0,
                filename=matches[0].name,
                subfolder=matches[0]
                .parent.relative_to(self._output_root)
                .as_posix(),
                storage_type="output",
            ),
        )
