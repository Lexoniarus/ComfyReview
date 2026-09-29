"""Compatibility wrapper around the SQLite path-relink repository."""

from __future__ import annotations

from pathlib import Path

from comfyreview.repositories.sqlite.path_relink import SqlitePathRelinker


def relink_paths_after_move(
    *,
    ratings_db_path: Path | None,
    prompt_tokens_db_path: Path | None,
    images_db_path: Path | None,
    combo_prompts_db_path: Path | None,
    arena_db_path: Path | None,
    old_png_path: str,
    old_json_path: str,
    new_png_path: str,
    new_json_path: str,
) -> None:
    """Relink mutable storage paths after a successful output-pair move."""
    SqlitePathRelinker(
        ratings_database_path=ratings_db_path,
        prompt_tokens_database_path=prompt_tokens_db_path,
        images_database_path=images_db_path,
        combo_database_path=combo_prompts_db_path,
        arena_database_path=arena_db_path,
    ).relink(
        old_png_path=old_png_path,
        old_json_path=old_json_path,
        new_png_path=new_png_path,
        new_json_path=new_json_path,
    )
