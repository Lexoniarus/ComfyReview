from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4


class InvalidOutputPathError(ValueError):
    """Raised when a submitted path is not a valid ComfyUI output pair."""


class OutputPairNotFoundError(FileNotFoundError):
    """Raised when a submitted output pair no longer exists."""


class OutputMutationError(RuntimeError):
    """Raised when a filesystem mutation cannot be completed safely."""


@dataclass(frozen=True)
class OutputPair:
    """Validated PNG and JSON sidecar paths below one output root."""

    png_path: Path
    json_path: Path


@dataclass
class StagedDeletion:
    """A reversible move of an output pair into the configured trash root."""

    pair: OutputPair
    staged_pair: OutputPair
    completed: bool = False

    def rollback(self) -> None:
        """Restore both staged files to their original locations."""
        if self.completed:
            return
        try:
            self.pair.png_path.parent.mkdir(parents=True, exist_ok=True)
            self.pair.json_path.parent.mkdir(parents=True, exist_ok=True)
            if self.staged_pair.png_path.exists():
                shutil.move(str(self.staged_pair.png_path), str(self.pair.png_path))
            if self.staged_pair.json_path.exists():
                shutil.move(str(self.staged_pair.json_path), str(self.pair.json_path))
        except OSError as exc:
            raise OutputMutationError("Could not restore staged output files") from exc

    def finalize(self, *, preserve_in_trash: bool) -> None:
        """Finish the delete and optionally purge the staged files."""
        self.completed = True
        if preserve_in_trash:
            return
        for path in (self.staged_pair.png_path, self.staged_pair.json_path):
            try:
                path.unlink(missing_ok=True)
            except OSError:
                # The pair is already outside the live output tree. Keeping a
                # recoverable trash file is safer than failing after DB commit.
                continue


class OutputFileService:
    """Validate and mutate PNG/JSON pairs below a configured output root."""

    def __init__(self, *, output_root: Path, trash_root: Path) -> None:
        self._output_root = Path(output_root).resolve()
        self._trash_root = Path(trash_root).resolve()

    def resolve_pair(self, *, png_path: str, json_path: str) -> OutputPair:
        """Resolve an existing matching pair and reject paths outside the root."""
        try:
            png = Path(png_path).resolve(strict=False)
            sidecar = Path(json_path).resolve(strict=False)
            png.relative_to(self._output_root)
            sidecar.relative_to(self._output_root)
        except (OSError, ValueError) as exc:
            raise InvalidOutputPathError("Output path is outside OUTPUT_ROOT") from exc

        if png.suffix.lower() != ".png" or sidecar.suffix.lower() != ".json":
            raise InvalidOutputPathError("Expected a PNG and JSON sidecar pair")
        if png.parent != sidecar.parent or png.stem != sidecar.stem:
            raise InvalidOutputPathError("PNG and JSON sidecar do not match")
        if not png.is_file() or not sidecar.is_file():
            raise OutputPairNotFoundError("Output pair no longer exists")
        return OutputPair(png_path=png, json_path=sidecar)

    def stage_delete(self, pair: OutputPair) -> StagedDeletion:
        """Move a pair to a unique trash location and return a rollback handle."""
        relative_parent = pair.png_path.parent.relative_to(self._output_root)
        destination = self._trash_root / relative_parent
        destination.mkdir(parents=True, exist_ok=True)
        suffix = uuid4().hex
        staged_pair = OutputPair(
            png_path=destination / f"{pair.png_path.stem}.{suffix}.png",
            json_path=destination / f"{pair.json_path.stem}.{suffix}.json",
        )

        png_moved = False
        try:
            shutil.move(str(pair.png_path), str(staged_pair.png_path))
            png_moved = True
            shutil.move(str(pair.json_path), str(staged_pair.json_path))
        except OSError as exc:
            if png_moved and staged_pair.png_path.exists():
                try:
                    shutil.move(str(staged_pair.png_path), str(pair.png_path))
                except OSError as rollback_exc:
                    raise OutputMutationError(
                        "Delete staging failed and PNG rollback also failed"
                    ) from rollback_exc
            raise OutputMutationError("Could not stage output pair for deletion") from exc

        return StagedDeletion(pair=pair, staged_pair=staged_pair)
