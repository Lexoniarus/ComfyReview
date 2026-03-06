from __future__ import annotations

import shutil
from pathlib import Path
from typing import Iterable, Optional, Tuple

from services.context_filters import extract_character_from_subdir
from services.path_relink_service import relink_paths_after_move
from stores.curation_store import upsert_set_key


def normalize_set_key(set_key: str, *, allowed: Iterable[str]) -> Optional[str]:
    """Normalize a set key.

    Returns
    - None for unsorted
    - valid set_key string for allowed set keys
    """
    sk = str(set_key or "").strip()
    if not sk or sk == "unsorted":
        return None
    allowed_set = set(str(x).strip() for x in (allowed or []) if str(x).strip())
    return sk if sk in allowed_set else None


def _export_copy_to_subtier(
    *,
    output_root: Path,
    lora_export_root: Path,
    png_path: Path,
    json_path: Path,
    set_key: str,
) -> None:
    """Copy PNG+JSON into export folder structure.

    NOTE
    This is the legacy "copy export" variant. vNext now prefers in-place sorting
    inside OUTPUT_ROOT/playground/<Character>/<set_key>/.

    Zielpfad
    - <lora_export_root>/playground/<Character>/<set>/...
    - character_face -> character/face
    - character_body -> character/body
    """

    try:
        rel = png_path.parent.relative_to(output_root)
        subdir = str(rel).replace("\\", "/")
    except Exception:
        subdir = ""

    char = extract_character_from_subdir(subdir) or "unknown"

    segs = []
    if set_key == "character_face":
        segs = ["character", "face"]
    elif set_key == "character_body":
        segs = ["character", "body"]
    else:
        segs = [set_key]

    dest_dir = Path(lora_export_root) / "playground" / char
    for s in segs:
        dest_dir = dest_dir / s
    dest_dir.mkdir(parents=True, exist_ok=True)

    if png_path.exists():
        shutil.copy2(str(png_path), str(dest_dir / png_path.name))
    if json_path.exists():
        shutil.copy2(str(json_path), str(dest_dir / json_path.name))


def _derive_character_root(output_root: Path, png_path: Path) -> Tuple[Path, str]:
    """Return character root folder and character name.

    Expected structure:
      OUTPUT_ROOT/playground/<Character>/...

    Files may live in deeper set folders (scene/outfit/...), but character root
    stays OUTPUT_ROOT/playground/<Character>.
    """

    try:
        rel = png_path.parent.relative_to(output_root)
        subdir = str(rel).replace("\\", "/")
    except Exception:
        subdir = ""

    char = extract_character_from_subdir(subdir) or "unknown"

    try:
        rel_png = png_path.relative_to(output_root)
        parts = [p for p in rel_png.parts if p]
        if len(parts) >= 2 and str(parts[0]).lower() == "playground":
            return (output_root / "playground" / str(parts[1]), char)
    except Exception:
        pass

    return (png_path.parent, char)


def _dest_dir_for_set(character_root: Path, set_key: Optional[str]) -> Path:
    """Destination directory inside the character folder.

    Requirement:
    - create only simple group subfolders
    - set folders are direct children of the character root
    """
    if not set_key:
        return character_root
    return character_root / str(set_key)


def _pick_unique_dest_paths(dest_dir: Path, png_name: str) -> Tuple[Path, Path]:
    """Pick a non-colliding destination pair (png+json).

    Keeps base name when possible.
    If collision exists, appends _mvN.
    """

    dest_dir.mkdir(parents=True, exist_ok=True)

    base = Path(png_name).stem
    png_ext = Path(png_name).suffix or ".png"

    for i in range(0, 1000):
        suffix = "" if i == 0 else f"_mv{i}"
        dest_png = dest_dir / f"{base}{suffix}{png_ext}"
        dest_json = dest_dir / f"{base}{suffix}.json"
        if not dest_png.exists() and not dest_json.exists():
            return dest_png, dest_json

    # fallback
    return (dest_dir / f"{base}_mv999{png_ext}", dest_dir / f"{base}_mv999.json")


def _move_pair(png_path: Path, json_path: Path, dest_png: Path, dest_json: Path) -> None:
    dest_png.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(png_path), str(dest_png))
    shutil.move(str(json_path), str(dest_json))


def assign_image_to_set(
    *,
    curation_db_path: Path,
    output_root: Path,
    lora_export_root: Path,
    allowed_set_keys: Iterable[str],
    ratings_db_path: Optional[Path] = None,
    prompt_tokens_db_path: Optional[Path] = None,
    images_db_path: Optional[Path] = None,
    combo_prompts_db_path: Optional[Path] = None,
    png_path: str,
    json_path: str,
    set_key: str,
) -> None:
    """Assign a single image to exactly one curation set (or unsorted).

    vNext rule
    - single label per image (png_path -> set_key)

    Requirement
    - in-place sorting: create subfolders inside OUTPUT_ROOT/playground/<Character>/
      and move PNG+JSON there.
    - keep stable behavior: relink DB paths so existing ratings and views remain valid.
    """

    p = Path(str(png_path))
    j = Path(str(json_path))
    sk = normalize_set_key(set_key, allowed=allowed_set_keys)

    character_root, _ = _derive_character_root(Path(output_root), p)
    dest_dir = _dest_dir_for_set(character_root, sk)

    # already where it belongs
    if p.exists() and j.exists():
        try:
            if p.parent.resolve() == dest_dir.resolve():
                upsert_set_key(curation_db_path, png_path=str(p), set_key=sk)
                return
        except Exception:
            pass

    dest_png, dest_json = _pick_unique_dest_paths(dest_dir, p.name)

    old_png = str(p)
    old_json = str(j)

    _move_pair(p, j, dest_png, dest_json)

    new_png = str(dest_png)
    new_json = str(dest_json)

    relink_paths_after_move(
        ratings_db_path=ratings_db_path,
        prompt_tokens_db_path=prompt_tokens_db_path,
        images_db_path=images_db_path,
        combo_prompts_db_path=combo_prompts_db_path,
        old_png_path=old_png,
        old_json_path=old_json,
        new_png_path=new_png,
        new_json_path=new_json,
    )

    # mapping is stored on the NEW path, old path must be cleared
    upsert_set_key(curation_db_path, png_path=old_png, set_key=None)
    upsert_set_key(curation_db_path, png_path=new_png, set_key=sk)

    # Optional legacy export copy (currently not required)
    # if sk is not None:
    #     _export_copy_to_subtier(
    #         output_root=Path(output_root),
    #         lora_export_root=Path(lora_export_root),
    #         png_path=Path(new_png),
    #         json_path=Path(new_json),
    #         set_key=sk,
    #     )
