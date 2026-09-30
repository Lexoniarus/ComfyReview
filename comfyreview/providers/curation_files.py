"""Local filesystem provider for reversible curation moves."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path

from comfyreview.application import (
    CurationImage,
    InvalidOutputPathError,
    OutputMutationError,
    OutputPairNotFoundError,
)


@dataclass(slots=True)
class LocalStagedCurationMove:
    """Represent one completed but reversible local file move."""

    source_png_path: Path
    source_json_path: Path | None
    png_path: Path
    json_path: Path | None
    moved: bool

    def rollback(self) -> None:
        """Restore both files after a failed canonical update."""
        if not self.moved:
            return
        png_restored = False
        try:
            self.source_png_path.parent.mkdir(parents=True, exist_ok=True)
            if self.png_path.is_file():
                shutil.move(str(self.png_path), str(self.source_png_path))
                png_restored = True
            if (
                self.source_json_path is not None
                and self.json_path is not None
                and self.json_path.is_file()
            ):
                shutil.move(
                    str(self.json_path),
                    str(self.source_json_path),
                )
        except OSError as error:
            if png_restored:
                try:
                    shutil.move(str(self.source_png_path), str(self.png_path))
                except OSError:
                    pass
            raise OutputMutationError(
                "Could not roll back the curation move"
            ) from error


class LocalCurationFileManager:
    """Move output files within a configured output boundary."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = Path(output_root).resolve(strict=False)

    def stage_move(
        self,
        image: CurationImage,
        set_key: str | None,
    ) -> LocalStagedCurationMove:
        """Move PNG and optional sidecar into one character set folder."""
        source_png = self._inside_root(image.png_path)
        source_json = (
            self._inside_root(image.json_path)
            if image.json_path is not None
            else None
        )
        if source_png.suffix.lower() != ".png":
            raise InvalidOutputPathError("Expected a canonical PNG path")
        if not source_png.is_file():
            raise OutputPairNotFoundError("Canonical PNG no longer exists")
        if source_json is not None:
            if (
                source_json.suffix.lower() != ".json"
                or source_json.parent != source_png.parent
                or source_json.stem != source_png.stem
            ):
                raise InvalidOutputPathError(
                    "Canonical sidecar does not match its PNG"
                )
            if not source_json.is_file():
                raise OutputPairNotFoundError(
                    "Canonical sidecar no longer exists"
                )

        character_root = self._character_root(source_png)
        destination_directory = (
            character_root if set_key is None else character_root / set_key
        )
        if source_png.parent == destination_directory:
            return LocalStagedCurationMove(
                source_png_path=source_png,
                source_json_path=source_json,
                png_path=source_png,
                json_path=source_json,
                moved=False,
            )

        destination_png, destination_json = self._destination_paths(
            destination_directory,
            source_png,
            source_json,
        )
        destination_directory.mkdir(parents=True, exist_ok=True)
        png_moved = False
        try:
            shutil.move(str(source_png), str(destination_png))
            png_moved = True
            if source_json is not None and destination_json is not None:
                shutil.move(str(source_json), str(destination_json))
        except OSError as error:
            if png_moved and destination_png.is_file():
                try:
                    shutil.move(str(destination_png), str(source_png))
                except OSError as rollback_error:
                    raise OutputMutationError(
                        "Curation move and PNG rollback both failed"
                    ) from rollback_error
            raise OutputMutationError(
                "Could not move canonical image"
            ) from error
        return LocalStagedCurationMove(
            source_png_path=source_png,
            source_json_path=source_json,
            png_path=destination_png,
            json_path=destination_json,
            moved=True,
        )

    def _inside_root(self, path: Path) -> Path:
        candidate = (
            path if path.is_absolute() else self._output_root / path
        ).resolve(strict=False)
        try:
            candidate.relative_to(self._output_root)
        except ValueError as error:
            raise InvalidOutputPathError(
                "Canonical output path is outside OUTPUT_ROOT"
            ) from error
        return candidate

    def _character_root(self, png_path: Path) -> Path:
        relative = png_path.relative_to(self._output_root)
        parts = relative.parts
        if len(parts) >= 3 and parts[0].lower() == "playground":
            return self._output_root / parts[0] / parts[1]
        return png_path.parent

    @staticmethod
    def _destination_paths(
        directory: Path,
        source_png: Path,
        source_json: Path | None,
    ) -> tuple[Path, Path | None]:
        for index in range(1000):
            suffix = "" if index == 0 else f"_mv{index}"
            destination_png = directory / (
                f"{source_png.stem}{suffix}{source_png.suffix}"
            )
            destination_json = (
                directory / f"{source_png.stem}{suffix}.json"
                if source_json is not None
                else None
            )
            if destination_png.exists():
                continue
            if destination_json is not None and destination_json.exists():
                continue
            return destination_png, destination_json
        raise OutputMutationError("No collision-free curation path available")
