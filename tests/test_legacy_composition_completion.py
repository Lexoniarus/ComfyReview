"""Characterization tests for historical prompt-composition evidence."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from comfyreview.application import (
    PromptComponent,
    PromptRenderer,
    PromptRevision,
    PromptSelection,
)
from comfyreview.repositories.sqlite import CanonicalSchemaManager


def _component(
    *,
    component_uid: str,
    kind: str,
    positive_text: str,
    negative_text: str,
) -> PromptComponent:
    revision_uid = f"revision-{component_uid}"
    return PromptComponent(
        component_uid=component_uid,
        kind=kind,
        component_key=component_uid,
        name=component_uid,
        tags=(),
        notes="",
        archived=False,
        latest_revision=PromptRevision(
            revision_uid=revision_uid,
            revision_number=1,
            positive_text=positive_text,
            negative_text=negative_text,
            content_hash=f"hash-{component_uid}",
        ),
    )


def test_prompt_renderer_defines_exact_historical_roundtrip_order() -> None:
    """Keep snapshot reconstruction tied to the production renderer."""
    character = _component(
        component_uid="character-aiko",
        kind="character",
        positive_text="silver hair",
        negative_text="multiple people",
    )
    scene = _component(
        component_uid="scene-rooftop",
        kind="scene",
        positive_text="rooftop",
        negative_text="",
    )
    lighting = _component(
        component_uid="lighting-sunset",
        kind="lighting",
        positive_text="golden light",
        negative_text="flat light",
    )

    rendered = PromptRenderer().render(
        PromptSelection((character, scene, lighting))
    )

    assert rendered.positive_text == "silver hair, rooftop, golden light"
    assert rendered.negative_text == "multiple people, flat light"
    assert rendered.revision_uids == (
        "revision-character-aiko",
        "revision-scene-rooftop",
        "revision-lighting-sunset",
    )


def test_canonical_schema_preserves_ordered_composition_membership(
    tmp_path: Path,
) -> None:
    """Characterize the v6 storage available to the completion import."""
    database_path = tmp_path / "canonical.sqlite3"
    CanonicalSchemaManager(database_path).prepare_startup()

    with sqlite3.connect(database_path) as connection:
        component_id = connection.execute(
            """
            INSERT INTO prompt_components(
                kind, component_key, name, component_uid
            ) VALUES ('character', 'aiko', 'Aiko', 'component-aiko')
            """
        ).lastrowid
        revision_id = connection.execute(
            """
            INSERT INTO prompt_revisions(
                revision_uid, component_id, revision_number,
                positive_text, negative_text, content_hash
            ) VALUES ('revision-aiko', ?, 1, 'silver hair', '', 'hash-aiko')
            """,
            (component_id,),
        ).lastrowid
        composition_id = connection.execute(
            "INSERT INTO prompt_compositions(composition_uid) "
            "VALUES ('composition-aiko')"
        ).lastrowid
        connection.execute(
            """
            INSERT INTO prompt_composition_revisions(
                composition_id, revision_id, slot, position
            ) VALUES (?, ?, 'character', 0)
            """,
            (composition_id, revision_id),
        )

        membership = connection.execute(
            """
            SELECT revision.revision_uid, membership.slot,
                   membership.position
            FROM prompt_composition_revisions AS membership
            JOIN prompt_revisions AS revision
                ON revision.id = membership.revision_id
            WHERE membership.composition_id = ?
            """,
            (composition_id,),
        ).fetchone()

    assert membership == ("revision-aiko", "character", 0)
