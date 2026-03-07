from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional


def relink_paths_after_move(
    *,
    ratings_db_path: Optional[Path],
    prompt_tokens_db_path: Optional[Path],
    images_db_path: Optional[Path],
    combo_prompts_db_path: Optional[Path],
    arena_db_path: Optional[Path],
    old_png_path: str,
    old_json_path: str,
    new_png_path: str,
    new_json_path: str,
) -> None:
    """Update DB references after moving a PNG+JSON pair.

    Why
    - We sort images on disk into set folders.
    - ratings.sqlite3 is the source of truth and stores paths.
    - Several MVs reference paths too.

    This function keeps stable behavior by relinking paths.
    """

    if ratings_db_path:
        _relink_ratings(ratings_db_path, old_png_path, old_json_path, new_png_path, new_json_path)
    if prompt_tokens_db_path:
        _relink_prompt_tokens(prompt_tokens_db_path, old_json_path, new_json_path)
    if images_db_path:
        _relink_images(images_db_path, old_png_path, old_json_path, new_png_path, new_json_path)
    if combo_prompts_db_path:
        _relink_combo_prompts(combo_prompts_db_path, old_png_path, old_json_path, new_png_path, new_json_path)
    if arena_db_path:
        _relink_arena(arena_db_path, old_json_path, new_json_path)


def _relink_ratings(
    db_path: Path,
    old_png: str,
    old_json: str,
    new_png: str,
    new_json: str,
) -> None:
    if not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            UPDATE ratings
            SET png_path = ?, json_path = ?
            WHERE json_path = ?
            """,
            (new_png, new_json, old_json),
        )
        # defensive: also update by png_path in case of partial mismatch
        con.execute(
            """
            UPDATE ratings
            SET png_path = ?, json_path = ?
            WHERE png_path = ?
            """,
            (new_png, new_json, old_png),
        )
        con.commit()
    finally:
        con.close()


def _relink_prompt_tokens(db_path: Path, old_json: str, new_json: str) -> None:
    if not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            UPDATE tokens
            SET json_path = ?
            WHERE json_path = ?
            """,
            (new_json, old_json),
        )
        con.commit()
    finally:
        con.close()


def _relink_images(
    db_path: Path,
    old_png: str,
    old_json: str,
    new_png: str,
    new_json: str,
) -> None:
    if not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path)
    try:
        # primary key png_path can be updated in SQLite if unique
        con.execute(
            """
            UPDATE images
            SET png_path = ?, json_path = ?
            WHERE png_path = ?
            """,
            (new_png, new_json, old_png),
        )
        # defensive: update by json_path too
        con.execute(
            """
            UPDATE images
            SET png_path = ?, json_path = ?
            WHERE json_path = ?
            """,
            (new_png, new_json, old_json),
        )
        con.commit()
    finally:
        con.close()


def _relink_combo_prompts(
    db_path: Path,
    old_png: str,
    old_json: str,
    new_png: str,
    new_json: str,
) -> None:
    if not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path)
    try:
        # combo_prompts: best_* pointers
        con.execute(
            """
            UPDATE combo_prompts
            SET best_png_path = ?, best_json_path = ?
            WHERE best_png_path = ? OR best_json_path = ?
            """,
            (new_png, new_json, old_png, old_json),
        )

        # combo_best_images: top3 list pointers
        con.execute(
            """
            UPDATE combo_best_images
            SET png_path = ?, json_path = ?
            WHERE png_path = ? OR json_path = ?
            """,
            (new_png, new_json, old_png, old_json),
        )
        con.commit()
    finally:
        con.close()


def _relink_arena(db_path: Path, old_json: str, new_json: str) -> None:
    if not Path(db_path).exists():
        return
    con = sqlite3.connect(db_path)
    try:
        con.execute(
            """
            UPDATE arena_matches
            SET left_json = CASE WHEN left_json = ? THEN ? ELSE left_json END,
                right_json = CASE WHEN right_json = ? THEN ? ELSE right_json END,
                winner_json = CASE WHEN winner_json = ? THEN ? ELSE winner_json END
            WHERE left_json = ? OR right_json = ? OR winner_json = ?
            """,
            (old_json, new_json, old_json, new_json, old_json, new_json, old_json, old_json, old_json),
        )
        con.commit()
    finally:
        con.close()
