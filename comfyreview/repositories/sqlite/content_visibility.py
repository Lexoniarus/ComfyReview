"""Shared SQLite predicate for workspace content visibility."""

from __future__ import annotations

import re

_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def content_visibility_predicate(
    generation_alias: str = "generation",
    image_alias: str | None = "image",
) -> str:
    """Return SQL for the effective image level and workspace policy."""
    if not _SQL_IDENTIFIER.fullmatch(generation_alias):
        raise ValueError("generation alias must be a SQL identifier")
    if image_alias is not None and not _SQL_IDENTIFIER.fullmatch(image_alias):
        raise ValueError("image alias must be a SQL identifier")
    if image_alias is None:
        override = f"""
            SELECT state.override_content_level
            FROM images AS content_image
            JOIN image_content_level_state AS state
              ON state.image_id = content_image.id
            WHERE content_image.generation_id = {generation_alias}.id
            ORDER BY content_image.id
            LIMIT 1
        """
    else:
        override = f"""
            SELECT state.override_content_level
            FROM image_content_level_state AS state
            WHERE state.image_id = {image_alias}.id
        """
    return f"""
        EXISTS (
            SELECT 1
            FROM workspace_content_levels AS enabled_content
            WHERE enabled_content.singleton_id = 1
              AND enabled_content.level = COALESCE(
                  ({override}),
                  {generation_alias}.inferred_content_level
              )
        )
    """
