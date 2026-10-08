"""SQLite reader for active global prompt-policy revisions."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application.global_prompt_policy import (
    GlobalPromptPolicyRevision,
)
from comfyreview.application.workspace_settings import ContentLevel
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite.connection import connect_read_only


class SqliteGlobalPromptPolicyRepository:
    """Read versioned quality and enabled content policies in stable order."""

    def __init__(self, database_path: Path) -> None:
        self._database_path = Path(database_path)

    def list_active(
        self,
        enabled_content_levels: tuple[ContentLevel, ...],
    ) -> tuple[GlobalPromptPolicyRevision, ...]:
        """Return active quality plus explicitly enabled content profiles."""
        enabled = tuple(level.value for level in enabled_content_levels)
        placeholders = ", ".join("?" for _level in enabled)
        content_filter = (
            f"OR policy.content_level IN ({placeholders})" if enabled else ""
        )
        with connect_read_only(self._database_path, rows=True) as connection:
            policies = connection.execute(
                f"""
                SELECT policy.id, policy.policy_uid, policy.policy_key,
                       policy.policy_type, policy.revision_number,
                       policy.name, policy.content_level
                FROM global_prompt_policies AS policy
                WHERE policy.active = 1
                  AND (policy.policy_type = 'quality' {content_filter})
                ORDER BY CASE policy.policy_type
                    WHEN 'quality' THEN 0 ELSE 1 END,
                    CASE policy.content_level
                    WHEN 'standard' THEN 0 WHEN 'sexy' THEN 1
                    WHEN 'lewd' THEN 2 WHEN 'nude' THEN 3
                    WHEN 'explicit' THEN 4 ELSE 5 END,
                    policy.policy_key, policy.revision_number
                """,
                enabled,
            ).fetchall()
            result: list[GlobalPromptPolicyRevision] = []
            for policy in policies:
                atoms = connection.execute(
                    """
                    SELECT usage.scope, atom.canonical_text,
                           usage.weight_milli
                    FROM global_prompt_policy_atom_usages AS usage
                    JOIN prompt_atoms AS atom ON atom.id = usage.atom_id
                    WHERE usage.policy_id = ?
                    ORDER BY usage.scope, usage.position
                    """,
                    (int(policy["id"]),),
                ).fetchall()
                result.append(
                    GlobalPromptPolicyRevision(
                        policy_uid=str(policy["policy_uid"]),
                        policy_key=str(policy["policy_key"]),
                        policy_type=str(policy["policy_type"]),
                        revision_number=int(policy["revision_number"]),
                        name=str(policy["name"]),
                        content_level=(
                            ContentLevel(str(policy["content_level"]))
                            if policy["content_level"] is not None
                            else None
                        ),
                        positive_atoms=self._atoms(atoms, "pos"),
                        negative_atoms=self._atoms(atoms, "neg"),
                    )
                )
        return tuple(result)

    @staticmethod
    def _atoms(
        rows: list[sqlite3.Row], scope: str
    ) -> tuple[PromptAtomUsage, ...]:
        return tuple(
            PromptAtomUsage(
                str(row["canonical_text"]), int(row["weight_milli"])
            )
            for row in rows
            if str(row["scope"]) == scope
        )
