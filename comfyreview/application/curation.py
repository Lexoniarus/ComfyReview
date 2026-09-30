"""Application contracts and orchestration for canonical curation."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class CurationValidationError(ValueError):
    """Reject an invalid or stale curation command."""


class CurationMutationError(RuntimeError):
    """Report a curation mutation or compensation failure."""


@dataclass(frozen=True, slots=True)
class AssignCurationCommand:
    """Assign one stable image identity to a configured set."""

    image_uid: str
    set_key: str


@dataclass(frozen=True, slots=True)
class CurationImage:
    """Describe the current file attributes of a canonical image."""

    image_uid: str
    png_path: Path
    json_path: Path | None


@dataclass(frozen=True, slots=True)
class CurationAssignment:
    """Carry new path attributes and set assignment into persistence."""

    image_uid: str
    previous_png_path: Path
    previous_json_path: Path | None
    png_path: Path
    json_path: Path | None
    set_key: str | None


@dataclass(frozen=True, slots=True)
class CurationResult:
    """Describe the committed canonical curation state."""

    image_uid: str
    png_path: Path
    json_path: Path | None
    set_key: str | None


class StagedCurationMove(Protocol):
    """Expose one reversible filesystem move."""

    @property
    def png_path(self) -> Path:
        """Return the staged PNG destination."""
        ...

    @property
    def json_path(self) -> Path | None:
        """Return the staged sidecar destination when present."""
        ...

    def rollback(self) -> None:
        """Restore moved files to their original locations."""
        ...


class CurationFileManager(Protocol):
    """Move canonical output files outside a database transaction."""

    def stage_move(
        self,
        image: CurationImage,
        set_key: str | None,
    ) -> StagedCurationMove:
        """Move an image into its set folder reversibly."""
        ...


class CurationRepository(Protocol):
    """Read and atomically update canonical curation state."""

    def get_live_image(self, image_uid: str) -> CurationImage:
        """Return current paths for one live canonical image."""
        ...

    def assign(self, assignment: CurationAssignment) -> CurationResult:
        """Update image paths and its single assignment atomically."""
        ...


class CurationService:
    """Coordinate a reversible file move with canonical persistence."""

    def __init__(
        self,
        *,
        repository: CurationRepository,
        files: CurationFileManager,
        allowed_set_keys: tuple[str, ...],
    ) -> None:
        self._repository = repository
        self._files = files
        self._allowed_set_keys = frozenset(allowed_set_keys)
        self._logger = logging.getLogger("comfyreview.curation")

    def assign(self, command: AssignCurationCommand) -> CurationResult:
        """Move and assign one image, compensating any failed DB write."""
        image_uid = str(command.image_uid or "").strip()
        if not image_uid:
            raise CurationValidationError("image_uid is required")
        raw_set_key = str(command.set_key or "").strip()
        if raw_set_key not in {"", "unsorted", *self._allowed_set_keys}:
            raise CurationValidationError("Unknown curation set")
        set_key = None if raw_set_key in {"", "unsorted"} else raw_set_key

        image = self._repository.get_live_image(image_uid)
        staged = self._files.stage_move(image, set_key)
        assignment = CurationAssignment(
            image_uid=image.image_uid,
            previous_png_path=image.png_path,
            previous_json_path=image.json_path,
            png_path=staged.png_path,
            json_path=staged.json_path,
            set_key=set_key,
        )
        try:
            return self._repository.assign(assignment)
        except Exception as error:
            try:
                staged.rollback()
            except Exception as rollback_error:
                self._logger.exception(
                    "curation.compensation_failed",
                    extra={"error_category": "filesystem_rollback"},
                )
                raise CurationMutationError(
                    "Curation failed and file rollback also failed"
                ) from rollback_error
            raise CurationMutationError(
                "Could not persist canonical curation assignment"
            ) from error
