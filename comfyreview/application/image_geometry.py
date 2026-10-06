"""Rebuild orchestration for canonical image geometry projections."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from comfyreview.application.generation_geometry import (
    GenerationGeometryPolicy,
    ImageGeometryProjection,
)


@dataclass(frozen=True, slots=True)
class ImageGeometrySource:
    """Identify one canonical image and its current path attribute."""

    image_uid: str
    png_path: Path


@dataclass(frozen=True, slots=True)
class ImageGeometryDiagnostic:
    """Describe a source that could not be projected."""

    image_uid: str
    png_path: Path
    message: str


@dataclass(frozen=True, slots=True)
class ImageGeometryRebuildResult:
    """Summarize one atomic projection replacement."""

    projected: int
    diagnostics: tuple[ImageGeometryDiagnostic, ...]


class ImageDimensionReader(Protocol):
    """Read actual dimensions behind the filesystem boundary."""

    def read(self, path: Path) -> tuple[int, int]: ...


class ImageGeometryRepository(Protocol):
    """Persist a rebuildable projection in one short transaction."""

    def list_sources(self) -> tuple[ImageGeometrySource, ...]: ...

    def replace_all(
        self, projections: tuple[ImageGeometryProjection, ...]
    ) -> None: ...

    def upsert(self, projection: ImageGeometryProjection) -> None: ...


class ImageGeometryProjectionService:
    """Scan outside SQLite and atomically replace derived geometry."""

    def __init__(
        self,
        repository: ImageGeometryRepository,
        reader: ImageDimensionReader,
        policy: GenerationGeometryPolicy | None = None,
    ) -> None:
        self._repository = repository
        self._reader = reader
        self._policy = policy or GenerationGeometryPolicy()

    def rebuild(self) -> ImageGeometryRebuildResult:
        """Read all files before opening the repository write transaction."""
        projections: list[ImageGeometryProjection] = []
        diagnostics: list[ImageGeometryDiagnostic] = []
        for source in self._repository.list_sources():
            try:
                width, height = self._reader.read(source.png_path)
                projections.append(
                    self._policy.classify(source.image_uid, width, height)
                )
            except (OSError, ValueError) as error:
                diagnostics.append(
                    ImageGeometryDiagnostic(
                        image_uid=source.image_uid,
                        png_path=source.png_path,
                        message=str(error),
                    )
                )
        self._repository.replace_all(tuple(projections))
        return ImageGeometryRebuildResult(
            projected=len(projections), diagnostics=tuple(diagnostics)
        )

    def project(self, source: ImageGeometrySource) -> ImageGeometryProjection:
        """Project one successfully captured image and persist it."""
        width, height = self._reader.read(source.png_path)
        projection = self._policy.classify(source.image_uid, width, height)
        self._repository.upsert(projection)
        return projection
