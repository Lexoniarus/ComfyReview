from __future__ import annotations

from pathlib import Path

from config import OUTPUT_ROOT


def png_path_to_url(png_path: str) -> str:
    """Build a /files URL from the real png_path."""
    p_raw = str(png_path or "").strip()
    if not p_raw:
        return ""

    if p_raw.startswith("/files/"):
        return p_raw

    root_s = str(OUTPUT_ROOT).replace("/", "\\").rstrip("\\")
    p_s = p_raw.replace("/", "\\")

    if p_s.lower().startswith((root_s + "\\").lower()):
        rel = p_s[len(root_s) + 1 :]
        rel = rel.replace("\\", "/")
        return "/files/" + rel

    rel = p_s.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    return "/files/" + rel


def existing_png_path_to_url(png_path: str) -> str:
    """Build a URL only when the referenced image still exists on disk."""
    path = str(png_path or "").strip()
    if not path:
        return ""
    try:
        if not Path(path).is_file():
            return ""
    except (OSError, ValueError):
        return ""
    return png_path_to_url(path)


def file_url_exists(url: str) -> bool:
    """Return whether a local /files URL still resolves below OUTPUT_ROOT."""
    value = str(url or "").strip()
    if not value:
        return False
    if value.startswith("/files/"):
        rel = value[len("/files/") :].replace("/", "\\")
        try:
            return (Path(OUTPUT_ROOT) / rel).is_file()
        except (OSError, ValueError):
            return False
    try:
        return Path(value).is_file()
    except (OSError, ValueError):
        return False
