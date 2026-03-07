from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

from config import CURATION_SET_KEYS, OUTPUT_ROOT

_EMPTY_CHARACTER_NAMES = {"empty"}
_ALLOWED_SET_KEYS = {str(x).strip() for x in (CURATION_SET_KEYS or []) if str(x).strip()}


@dataclass(frozen=True)
class GalleryContext:
    """Normalized vNext context for gallery-like pages.

    Fields
    model
    Empty string means all.

    subdir
    Empty string means all normal characters (Empty excluded by semantics).

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


def _split_path_parts(value: str) -> List[str]:
    s = str(value or "").replace("\\", "/").strip("/")
    return [p for p in s.split("/") if p]


def normalize_subdir(value: str) -> str:
    return str(value or "").replace("\\", "/").strip().strip("/")


def normalize_scope_subdir(value: str) -> str:
    """Normalize a scope subdir.

    Important semantic split:
    - scope/subdir is the character context
    - physical set folders may exist deeper on disk

    Therefore any playground path deeper than ``playground/<Character>`` collapses back
    to that character scope.
    """
    s = normalize_subdir(value)
    parts = _split_path_parts(s)
    if len(parts) >= 2 and parts[0].lower() == "playground":
        return f"playground/{parts[1]}"
    return s


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
    parts = _split_path_parts(subdir)
    if len(parts) >= 2 and parts[0].lower() == "playground":
        return parts[1]
    return parts[-1] if parts else ""


def is_empty_character_name(value: str) -> bool:
    return str(value or "").strip().lower() in _EMPTY_CHARACTER_NAMES


def is_empty_character_subdir(subdir: str) -> bool:
    return is_empty_character_name(extract_character_from_subdir(subdir))


def matches_character_scope(*, item_subdir: str, selected_subdir: str) -> bool:
    """Character filter semantics.

    - explicit character: exact scope match, including Empty
    - selected_subdir='' (All): include all normal characters, exclude Empty
    """
    selected = normalize_scope_subdir(selected_subdir)
    item = normalize_scope_subdir(item_subdir)
    if selected:
        return item == selected
    return not is_empty_character_subdir(item)


def infer_set_key_from_png_path(png_path: str) -> Optional[str]:
    """Infer the effective curation set from the real physical PNG path.

    This is a conservative fallback used only when the curation mapping for the current
    path is missing. Scope/subdir is intentionally NOT used here.
    """
    parts = _split_path_parts(png_path)
    root_parts = _split_path_parts(str(OUTPUT_ROOT))

    rel_parts = parts
    if root_parts and len(parts) >= len(root_parts):
        lhs = [p.lower() for p in parts[: len(root_parts)]]
        rhs = [p.lower() for p in root_parts]
        if lhs == rhs:
            rel_parts = parts[len(root_parts) :]

    if len(rel_parts) < 3:
        return None
    if str(rel_parts[0]).lower() != "playground":
        return None

    candidate = str(rel_parts[2]).strip()
    return candidate if candidate in _ALLOWED_SET_KEYS else None


def resolve_assigned_set_key(*, png_path: str, assigned_set_key: Optional[str]) -> Optional[str]:
    """Return the effective single-set assignment for one image.

    Priority:
    1) curation DB mapping for the current png_path
    2) physical path fallback (playground/<Character>/<set>/file.png)
    """
    sk = normalize_set_key(str(assigned_set_key or ""))
    if sk and sk != "unsorted":
        return sk
    return infer_set_key_from_png_path(str(png_path or ""))


def matches_set_filter(*, selected_set_key: str, assigned_set_key: Optional[str], png_path: str) -> bool:
    """Set filter semantics on the same image inventory.

    - selected_set_key=''        -> all sets + unsorted
    - selected_set_key='unsorted'-> only items without a real set assignment
    - selected_set_key='<set>'   -> exactly that effective set
    """
    selected = normalize_set_key(selected_set_key)
    if not selected:
        return True

    effective = resolve_assigned_set_key(png_path=str(png_path or ""), assigned_set_key=assigned_set_key)
    if selected == "unsorted":
        return not effective
    return effective == selected


def build_dropdown_lists(items: Iterable[Any]) -> Tuple[List[str], List[str], List[Dict[str, str]]]:
    """Build dropdown lists used across pages.

    Returns
    model_list
    subdir_list
    character_options
    """
    model_list = sorted({getattr(it, "model_branch", "") for it in items if getattr(it, "model_branch", "")})
    subdir_list = sorted({normalize_scope_subdir(getattr(it, "subdir", "")) for it in items if getattr(it, "subdir", "")})
    character_options = [{"value": sd, "label": extract_character_from_subdir(sd)} for sd in subdir_list]
    return model_list, subdir_list, character_options


def build_gallery_context(*, model: str, subdir: str, set_key: str, mode: str) -> GalleryContext:
    return GalleryContext(
        model=normalize_model(model),
        subdir=normalize_scope_subdir(subdir),
        set_key=normalize_set_key(set_key),
        mode=normalize_mode(mode),
    )
