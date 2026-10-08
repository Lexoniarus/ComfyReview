"""Behavior tests for versioned global prompt policies."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import (
    ContentLevel,
    GlobalPromptPolicyApplicator,
    GlobalPromptPolicyRevision,
)
from comfyreview.domain import PromptAtomUsage
from comfyreview.repositories.sqlite import (
    CanonicalSchemaManager,
    SqliteGlobalPromptPolicyRepository,
)


def test_global_policy_preserves_component_weight_and_deduplicates_per_scope() -> (
    None
):
    quality = GlobalPromptPolicyRevision(
        policy_uid="quality-1",
        policy_key="quality",
        policy_type="quality",
        revision_number=1,
        name="Quality",
        content_level=None,
        positive_atoms=(PromptAtomUsage("Detailed", 1000),),
        negative_atoms=(
            PromptAtomUsage("bad anatomy", 1000),
            PromptAtomUsage("bad hands", 900),
        ),
    )

    applied = GlobalPromptPolicyApplicator().apply(
        (PromptAtomUsage(" detailed ", 1250),),
        (PromptAtomUsage("Bad   Anatomy", 1300),),
        (quality,),
    )

    assert applied.positive_atoms == (PromptAtomUsage(" detailed ", 1250),)
    assert applied.negative_atoms == (
        PromptAtomUsage("Bad   Anatomy", 1300),
        PromptAtomUsage("bad hands", 900),
    )
    assert applied.policy_uids == ("quality-1",)


def test_sqlite_policy_reader_selects_quality_and_enabled_content_profiles(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "comfyreview.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()
    with sqlite3.connect(database_path) as connection:
        atom_ids = {}
        for text in ("high quality", "suggestive", "explicit"):
            atom_ids[text] = connection.execute(
                "INSERT INTO prompt_atoms(canonical_text) VALUES (?) RETURNING id",
                (text,),
            ).fetchone()[0]
        policy_rows = (
            ("quality-1", "quality", "quality", 1, "Quality", None),
            (
                "suggestive-1",
                "suggestive",
                "content_profile",
                1,
                "Suggestive",
                "sexy",
            ),
            (
                "explicit-1",
                "explicit",
                "content_profile",
                1,
                "Explicit",
                "explicit",
            ),
        )
        for position, policy in enumerate(policy_rows):
            policy_id = connection.execute(
                """
                INSERT INTO global_prompt_policies(
                    policy_uid, policy_key, policy_type, revision_number,
                    name, content_level, active
                ) VALUES (?, ?, ?, ?, ?, ?, 1)
                RETURNING id
                """,
                policy,
            ).fetchone()[0]
            atom_text = ("high quality", "suggestive", "explicit")[position]
            connection.execute(
                """
                INSERT INTO global_prompt_policy_atom_usages(
                    policy_id, atom_id, scope, position, weight_milli
                ) VALUES (?, ?, 'pos', 0, 1000)
                """,
                (policy_id, atom_ids[atom_text]),
            )

    policies = SqliteGlobalPromptPolicyRepository(database_path).list_active(
        (ContentLevel.STANDARD, ContentLevel.SEXY)
    )

    assert tuple(policy.policy_uid for policy in policies) == (
        "quality-1",
        "suggestive-1",
    )
    assert policies[1].content_level is ContentLevel.SEXY
    assert policies[1].positive_atoms == (PromptAtomUsage("suggestive", 1000),)
