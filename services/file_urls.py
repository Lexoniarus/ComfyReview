from __future__ import annotations

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
