from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple


@dataclass(frozen=True)
class GalleryContext:
    """Normalized vNext context for gallery-like pages.

    Fields
    model
    Empty string means all.

    subdir
    Empty string means all.

    set_key
    unsorted or a valid set key.

    mode
    top or worst.
    """

    model: str
    subdir: str
    set_key: str
    mode: str


def normalize_model(value: str) -> str:
    v = str(value or "").strip()
    return "" if v.lower() == "all" else v


def normalize_subdir(value: str) -> str:
    return str(value or "").strip()


def normalize_set_key(value: str) -> str:
    """Normalize curation set key.

    Empty string means "all sets" and must stay distinct from "unsorted".
    """
    v = str(value or "").strip()
    if not v:
        return ""
    return v


def normalize_mode(value: str, *, default: str = "top") -> str:
    v = str(value or default).strip().lower()
    return v if v in {"top", "worst"} else str(default).strip().lower()


def normalize_unrated_flag(value: int | str | None, *, default: int = 1) -> int:
    if value is None:
        return int(default)
    try:
        return 1 if int(value) == 1 else 0
    except Exception:
        return int(default)


def extract_character_from_subdir(subdir: str) -> str:
    """Derive character name from a scanner subdir."""
    s = str(subdir or "").replace("\\", "/").strip("/")
    parts = [p for p in s.split("/") if p]
    if len(parts) >= 2 and parts[0].lower() == "playground":
        return parts[1]
    return parts[-1] if parts else ""


def build_dropdown_lists(items: Iterable[Any]) -> Tuple[List[str], List[str], List[Dict[str, str]]]:
    """Build dropdown lists used across pages.

    Returns
    model_list
    subdir_list
    character_options
    """
    model_list = sorted({getattr(it, "model_branch", "") for it in items if getattr(it, "model_branch", "")})
    subdir_list = sorted({getattr(it, "subdir", "") for it in items if getattr(it, "subdir", "")})
    character_options = [{"value": sd, "label": extract_character_from_subdir(sd)} for sd in subdir_list]
    return model_list, subdir_list, character_options


def build_gallery_context(*, model: str, subdir: str, set_key: str, mode: str) -> GalleryContext:
    return GalleryContext(
        model=normalize_model(model),
        subdir=normalize_subdir(subdir),
        set_key=normalize_set_key(set_key),
        mode=normalize_mode(mode),
    )
