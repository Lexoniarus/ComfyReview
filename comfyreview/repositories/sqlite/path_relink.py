"""SQLite path relinking for canonical and transitional projection stores."""

from __future__ import annotations

import sqlite3
from pathlib import Path


class SqlitePathRelinker:
    """Relink mutable output paths without treating them as domain identity."""

    def __init__(
        self,
        *,
        ratings_database_path: Path | None,
        prompt_tokens_database_path: Path | None,
        images_database_path: Path | None,
        combo_database_path: Path | None,
        arena_database_path: Path | None,
    ) -> None:
        self._ratings_database_path = ratings_database_path
        self._prompt_tokens_database_path = prompt_tokens_database_path
        self._images_database_path = images_database_path
        self._combo_database_path = combo_database_path
        self._arena_database_path = arena_database_path

    def relink(
        self,
        *,
        old_png_path: str,
        old_json_path: str,
        new_png_path: str,
        new_json_path: str,
    ) -> None:
        """Update every configured store after one PNG/JSON pair move."""
        self._relink_ratings(
            old_png_path=old_png_path,
            old_json_path=old_json_path,
            new_png_path=new_png_path,
            new_json_path=new_json_path,
        )
        self._relink_prompt_tokens(
            old_json_path=old_json_path,
            new_json_path=new_json_path,
        )
        self._relink_images(
            old_png_path=old_png_path,
            old_json_path=old_json_path,
            new_png_path=new_png_path,
            new_json_path=new_json_path,
        )
        self._relink_combo(
            old_png_path=old_png_path,
            old_json_path=old_json_path,
            new_png_path=new_png_path,
            new_json_path=new_json_path,
        )
        self._relink_arena(
            old_json_path=old_json_path,
            new_json_path=new_json_path,
        )

    def _relink_ratings(
        self,
        *,
        old_png_path: str,
        old_json_path: str,
        new_png_path: str,
        new_json_path: str,
    ) -> None:
        path = self._existing(self._ratings_database_path)
        if path is None:
            return
        connection = sqlite3.connect(path)
        try:
            object_type = self._object_type(connection, "ratings")
            if object_type == "view" and self._is_canonical(connection):
                self._relink_canonical_image_paths(
                    connection,
                    old_png_path=old_png_path,
                    old_json_path=old_json_path,
                    new_png_path=new_png_path,
                    new_json_path=new_json_path,
                )
            elif object_type == "table":
                connection.execute(
                    """
                    UPDATE ratings
                    SET png_path = ?, json_path = ?
                    WHERE json_path = ? OR png_path = ?
                    """,
                    (
                        new_png_path,
                        new_json_path,
                        old_json_path,
                        old_png_path,
                    ),
                )
            connection.commit()
        finally:
            connection.close()

    def _relink_prompt_tokens(
        self,
        *,
        old_json_path: str,
        new_json_path: str,
    ) -> None:
        path = self._existing(self._prompt_tokens_database_path)
        if path is None:
            return
        connection = sqlite3.connect(path)
        try:
            if self._object_type(connection, "tokens") == "table":
                connection.execute(
                    "UPDATE tokens SET json_path = ? WHERE json_path = ?",
                    (new_json_path, old_json_path),
                )
                connection.commit()
        finally:
            connection.close()

    def _relink_images(
        self,
        *,
        old_png_path: str,
        old_json_path: str,
        new_png_path: str,
        new_json_path: str,
    ) -> None:
        path = self._existing(self._images_database_path)
        if path is None or path == self._ratings_database_path:
            return
        connection = sqlite3.connect(path)
        try:
            if self._object_type(connection, "images") != "table":
                return
            connection.execute(
                """
                UPDATE images
                SET png_path = ?, json_path = ?
                WHERE png_path = ? OR json_path = ?
                """,
                (
                    new_png_path,
                    new_json_path,
                    old_png_path,
                    old_json_path,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    def _relink_combo(
        self,
        *,
        old_png_path: str,
        old_json_path: str,
        new_png_path: str,
        new_json_path: str,
    ) -> None:
        path = self._existing(self._combo_database_path)
        if path is None:
            return
        connection = sqlite3.connect(path)
        try:
            if self._object_type(connection, "combo_prompts") == "table":
                connection.execute(
                    """
                    UPDATE combo_prompts
                    SET best_png_path = ?, best_json_path = ?
                    WHERE best_png_path = ? OR best_json_path = ?
                    """,
                    (
                        new_png_path,
                        new_json_path,
                        old_png_path,
                        old_json_path,
                    ),
                )
            if self._object_type(connection, "combo_best_images") == "table":
                connection.execute(
                    """
                    UPDATE combo_best_images
                    SET png_path = ?, json_path = ?
                    WHERE png_path = ? OR json_path = ?
                    """,
                    (
                        new_png_path,
                        new_json_path,
                        old_png_path,
                        old_json_path,
                    ),
                )
            connection.commit()
        finally:
            connection.close()

    def _relink_arena(
        self,
        *,
        old_json_path: str,
        new_json_path: str,
    ) -> None:
        path = self._existing(self._arena_database_path)
        if path is None:
            return
        connection = sqlite3.connect(path)
        try:
            if self._object_type(connection, "arena_matches") != "table":
                return
            connection.execute(
                """
                UPDATE arena_matches
                SET left_json = CASE
                        WHEN left_json = ? THEN ? ELSE left_json END,
                    right_json = CASE
                        WHEN right_json = ? THEN ? ELSE right_json END,
                    winner_json = CASE
                        WHEN winner_json = ? THEN ? ELSE winner_json END
                WHERE left_json = ? OR right_json = ? OR winner_json = ?
                """,
                (
                    old_json_path,
                    new_json_path,
                    old_json_path,
                    new_json_path,
                    old_json_path,
                    new_json_path,
                    old_json_path,
                    old_json_path,
                    old_json_path,
                ),
            )
            connection.commit()
        finally:
            connection.close()

    @staticmethod
    def _relink_canonical_image_paths(
        connection: sqlite3.Connection,
        *,
        old_png_path: str,
        old_json_path: str,
        new_png_path: str,
        new_json_path: str,
    ) -> None:
        for table in ("images", "deleted_images"):
            if SqlitePathRelinker._object_type(connection, table) != "table":
                continue
            connection.execute(
                f"""
                UPDATE {table}
                SET png_path = ?, json_path = ?
                WHERE png_path = ? OR json_path = ?
                """,
                (
                    new_png_path,
                    new_json_path,
                    old_png_path,
                    old_json_path,
                ),
            )

    @staticmethod
    def _object_type(
        connection: sqlite3.Connection,
        name: str,
    ) -> str | None:
        row = connection.execute(
            "SELECT type FROM sqlite_master WHERE name = ?",
            (name,),
        ).fetchone()
        return None if row is None else str(row[0])

    @staticmethod
    def _is_canonical(connection: sqlite3.Connection) -> bool:
        return (
            SqlitePathRelinker._object_type(
                connection,
                "schema_metadata",
            )
            == "table"
        )

    @staticmethod
    def _existing(path: Path | None) -> Path | None:
        if path is None:
            return None
        candidate = Path(path).resolve()
        return candidate if candidate.is_file() else None
