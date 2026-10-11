"""Typed SQLite row decoding for complete Card candidate groups."""

from __future__ import annotations

import sqlite3

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidate,
    CardCandidateGroup,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    CompleteCardCandidateArtifacts,
)
from comfyreview.application.card_battler_presentation import (
    CardPresentationResult,
    CardPresentationStatus,
)
from comfyreview.repositories.sqlite.card_battler_runtime_codec import (
    decode_card_spec,
    decode_imprint,
    decode_presentation,
    decode_semantic_profile,
    decode_visual_recipe,
)


def decode_candidate_group(
    row: sqlite3.Row,
    candidate_rows: list[sqlite3.Row],
) -> CardCandidateGroup:
    """Reconstruct one immutable group aggregate from ordered rows."""
    semantic_payload = row["semantic_profile_json"]
    imprint_payload = row["card_imprint_json"]
    return CardCandidateGroup(
        group_id=str(row["group_id"]),
        revision=int(row["revision"]),
        kind=CardCandidateGroupKind(str(row["kind"])),
        status=CardCandidateGroupStatus(str(row["status"])),
        source_image_uid=str(row["source_image_uid"]),
        source_content_hash=str(row["source_content_hash"]),
        reference_image_uid=str(row["reference_image_uid"]),
        reference_content_hash=str(row["reference_content_hash"]),
        group_seed=int(row["group_seed"]),
        candidates=tuple(_decode_candidate(item) for item in candidate_rows),
        semantic_profile=(
            None
            if semantic_payload is None
            else decode_semantic_profile(str(semantic_payload))
        ),
        imprint=(
            None
            if imprint_payload is None
            else decode_imprint(str(imprint_payload))
        ),
        source_card_id=(
            None
            if row["source_card_id"] is None
            else str(row["source_card_id"])
        ),
        source_card_revision=(
            None
            if row["source_card_revision"] is None
            else int(row["source_card_revision"])
        ),
        failure_category=(
            None
            if row["failure_category"] is None
            else str(row["failure_category"])
        ),
    )


def _decode_candidate(row: sqlite3.Row) -> CardCandidate:
    card_payload = row["structured_card_spec_json"]
    recipe_payload = row["visual_recipe_json"]
    status_payload = row["presentation_status"]
    presentation_payload = row["presentation_json"]
    artifact_payloads = (card_payload, recipe_payload, status_payload)
    if any(value is None for value in artifact_payloads) and any(
        value is not None for value in artifact_payloads
    ):
        raise ValueError("Candidate artifact columns are incomplete")
    materialization_seed = int(row["materialization_seed"])
    artifacts = None
    if card_payload is not None:
        presentation_status = CardPresentationStatus(str(status_payload))
        presentation = (
            None
            if presentation_payload is None
            else decode_presentation(str(presentation_payload))
        )
        artifacts = CompleteCardCandidateArtifacts(
            card=decode_card_spec(str(card_payload)),
            visual_recipe=decode_visual_recipe(str(recipe_payload)),
            presentation=CardPresentationResult(
                presentation,
                presentation_status,
            ),
            materialization_seed=materialization_seed,
            materialization_revision=str(row["materialization_revision"]),
        )
    return CardCandidate(
        candidate_id=str(row["candidate_id"]),
        group_id=str(row["group_id"]),
        group_revision=int(row["group_revision"]),
        slot_index=int(row["slot_index"]),
        status=CardCandidateStatus(str(row["status"])),
        materialization_seed=materialization_seed,
        artifacts=artifacts,
        generation_uid=(
            None
            if row["generation_uid"] is None
            else str(row["generation_uid"])
        ),
        recipe_hash=(
            None if row["recipe_hash"] is None else str(row["recipe_hash"])
        ),
        generation_policy_revision=(
            None
            if row["generation_policy_revision"] is None
            else str(row["generation_policy_revision"])
        ),
        failure_category=(
            None
            if row["failure_category"] is None
            else str(row["failure_category"])
        ),
        output_image_uid=(
            None
            if row["output_image_uid"] is None
            else str(row["output_image_uid"])
        ),
        output_content_hash=(
            None
            if row["output_content_hash"] is None
            else str(row["output_content_hash"])
        ),
    )
