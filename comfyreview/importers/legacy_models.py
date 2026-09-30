"""Typed records used by the explicit legacy-output write import."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class LegacyOutputImportValidationError(ValueError):
    """Reject an audit snapshot or source tree that is not import-safe."""


class LegacyOutputImportRecoveryError(RuntimeError):
    """Report an import failure whose backup recovery also failed."""


@dataclass(frozen=True, slots=True)
class LegacySamplerStageImport:
    """Describe one historical standard KSampler stage."""

    node_id: str
    stage_order: int
    seed: int | None
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None


@dataclass(frozen=True, slots=True)
class LegacyImageImport:
    """Describe one historical image and its preserved generation facts."""

    image_uid: str
    generation_uid: str
    png_path: Path
    json_path: Path
    output_index: int
    model_branch: str
    checkpoint: str
    combo_key: str
    seed: int | None
    steps: int | None
    cfg: float | None
    sampler: str | None
    scheduler: str | None
    denoise: float | None
    loras_json: str
    positive_prompt: str
    negative_prompt: str
    raw_metadata_json: str
    workflow_json: str
    workflow_hash: str
    sampler_stages: tuple[LegacySamplerStageImport, ...]
    output_node_id: str = "legacy_sidecar"
    existing_image_uid: str | None = None
    existing_generation_uid: str | None = None


@dataclass(frozen=True, slots=True)
class LegacyOutputImportResult:
    """Summarize one committed legacy-output import."""

    backup_path: Path
    new_images: int
    enriched_images: int
    new_generations: int
    sampler_stages: int
    excluded_without_sidecar: int


class LegacyOutputImportSource(Protocol):
    """Load and revalidate one immutable legacy-output audit snapshot."""

    def load(
        self,
        report_path: Path,
    ) -> tuple[tuple[LegacyImageImport, ...], int]:
        """Return verified records and the excluded sidecarless count."""
        ...


class LegacyOutputImportObserver(Protocol):
    """Observe externally relevant phases of an offline import."""

    def backup_created(self, backup_path: Path) -> None:
        """Report the backup path before the first database write."""
        ...


class LegacyOutputImportRepository(Protocol):
    """Validate and atomically persist verified legacy output records."""

    def validate_records(
        self,
        records: tuple[LegacyImageImport, ...],
    ) -> None:
        """Reject stale canonical mappings or identity collisions."""
        ...

    def import_records(
        self,
        records: tuple[LegacyImageImport, ...],
        *,
        excluded_without_sidecar: int,
        backup_directory: Path | None = None,
        observer: LegacyOutputImportObserver | None = None,
    ) -> LegacyOutputImportResult:
        """Persist all records in one transaction after creating a backup."""
        ...
