"""Map validated output files to their mounted application URLs."""

from __future__ import annotations

from pathlib import Path, PurePosixPath


class OutputFileUrlMapper:
    """Resolve output paths and mounted URLs below one configured root."""

    def __init__(self, output_root: Path) -> None:
        self._output_root = Path(output_root).resolve(strict=False)

    def to_url(self, png_path: str | Path) -> str:
        """Return a mounted URL for a path contained by the output root."""
        value = str(png_path or "").strip()
        if not value:
            return ""
        if value.startswith("/files/"):
            return value if self.url_exists(value) else ""

        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = self._output_root / candidate
        try:
            relative = candidate.resolve(strict=False).relative_to(
                self._output_root
            )
        except (OSError, ValueError):
            return ""
        return f"/files/{relative.as_posix()}"

    def existing_url(self, png_path: str | Path) -> str:
        """Return a mounted URL only when the referenced file exists."""
        url = self.to_url(png_path)
        return url if url and self.url_exists(url) else ""

    def url_exists(self, url: str) -> bool:
        """Return whether a mounted URL resolves to a file below the root."""
        value = str(url or "").strip()
        if not value.startswith("/files/"):
            return False
        relative = PurePosixPath(value.removeprefix("/files/"))
        if relative.is_absolute() or ".." in relative.parts:
            return False
        try:
            candidate = (self._output_root / Path(*relative.parts)).resolve(
                strict=False
            )
            candidate.relative_to(self._output_root)
            return candidate.is_file()
        except (OSError, ValueError):
            return False
