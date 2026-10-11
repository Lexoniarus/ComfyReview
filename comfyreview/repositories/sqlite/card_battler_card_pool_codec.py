"""Typed SQLite row decoding for confirmed POC Cards."""

from __future__ import annotations

import sqlite3

from comfyreview.application.card_battler_card_pool import CardPoolCard
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.domain.card_battler import CardIdentity, CardState
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    decode_card_spec,
    decode_imprint,
    decode_presentation,
    decode_semantic_profile,
    decode_visual_recipe,
)


def decode_pool_card(row: sqlite3.Row) -> CardPoolCard:
    """Reconstruct one current confirmed Card from its runtime row."""
    semantic_profile = decode_semantic_profile(
        str(row["semantic_profile_json"])
    )
    imprint = decode_imprint(str(row["card_imprint_json"]))
    identity = CardIdentity(
        card_id=str(row["card_id"]),
        source_image_uid=str(row["source_image_uid"]),
        source_content_hash=str(row["source_content_hash"]),
        semantic_revision=semantic_profile.semantic_revision,
        imprint=imprint,
    )
    presentation_payload = row["presentation_json"]
    return CardPoolCard(
        state=CardState(
            identity=identity,
            revision=int(row["revision"]),
            card=decode_card_spec(str(row["structured_card_spec_json"])),
            active_image_uid=str(row["active_image_uid"]),
            active_content_hash=str(row["active_content_hash"]),
            visual_tier=int(row["visual_tier"]),
        ),
        semantic_profile=semantic_profile,
        visual_recipe=decode_visual_recipe(str(row["visual_recipe_json"])),
        presentation=CardPresentationResult(
            (
                None
                if presentation_payload is None
                else decode_presentation(str(presentation_payload))
            ),
            CardPresentationStatus(str(row["presentation_status"])),
        ),
        accepted_group_id=str(row["accepted_group_id"]),
        accepted_candidate_id=str(row["accepted_candidate_id"]),
    )
