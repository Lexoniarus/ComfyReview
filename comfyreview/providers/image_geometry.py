"""Filesystem boundary for reading image dimensions."""

from __future__ import annotations

import struct
from pathlib import Path


class InvalidPngError(ValueError):
    """Report an unreadable or malformed PNG header."""


class PngHeaderDimensionReader:
    """Read PNG dimensions without decoding image pixels."""

    def __init__(self, output_root: Path | None = None) -> None:
        self._output_root = (
            Path(output_root).resolve(strict=False)
            if output_root is not None
            else None
        )

    def read(self, path: Path) -> tuple[int, int]:
        """Return width and height from a validated PNG IHDR chunk."""
        candidate = Path(path)
        if not candidate.is_absolute() and self._output_root is not None:
            candidate = self._output_root / candidate
        try:
            with candidate.open("rb") as stream:
                header = stream.read(24)
        except OSError as error:
            raise InvalidPngError(f"could not read PNG: {path}") from error
        if len(header) != 24 or header[:8] != b"\x89PNG\r\n\x1a\n":
            raise InvalidPngError(f"invalid PNG signature: {path}")
        if header[12:16] != b"IHDR":
            raise InvalidPngError(f"PNG has no IHDR header: {path}")
        width, height = struct.unpack(">II", header[16:24])
        if width < 1 or height < 1:
            raise InvalidPngError(f"PNG dimensions are invalid: {path}")
        return width, height
