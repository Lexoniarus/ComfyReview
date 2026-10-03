"""Shared SQLite predicate for workspace content visibility."""

from __future__ import annotations

import re

from comfyreview.application.workspace_settings import CONTENT_LEVEL_TAGS

_SQL_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def content_visibility_predicate(generation_alias: str = "generation") -> str:
    """Return SQL that rejects compositions above enabled content levels."""
    if not _SQL_IDENTIFIER.fullmatch(generation_alias):
        raise ValueError("generation alias must be a SQL identifier")
    rules = " UNION ALL ".join(
        f"SELECT '{tag}' AS tag, '{level.value}' AS level"
        for tag, level in CONTENT_LEVEL_TAGS.items()
    )
    return f"""
        NOT EXISTS (
            SELECT 1
            FROM prompt_composition_revisions AS content_membership
            JOIN prompt_revisions AS content_revision
              ON content_revision.id = content_membership.revision_id
            JOIN prompt_components AS content_component
              ON content_component.id = content_revision.component_id
            JOIN json_each(
                CASE
                    WHEN json_valid(content_component.tags)
                    THEN content_component.tags
                    ELSE '[]'
                END
            ) AS content_tag
            JOIN ({rules}) AS content_rule
              ON content_rule.tag = lower(CAST(content_tag.value AS TEXT))
            LEFT JOIN workspace_content_levels AS enabled_content
              ON enabled_content.level = content_rule.level
            WHERE content_membership.composition_id =
                  {generation_alias}.prompt_composition_id
              AND enabled_content.level IS NULL
        )
    """
