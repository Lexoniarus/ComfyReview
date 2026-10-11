"""SQLite lifecycle tests for persisted Card development groups."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
)
from comfyreview.application.card_battler_card_pool import (
    CardPoolConflictError,
)
from comfyreview.application.card_battler_development_groups import (
    CardDevelopmentCandidateComposer,
    CardDevelopmentCandidateGroupService,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from tests.test_card_candidate_image_service import _Generations
from tests.test_card_candidate_image_service import _service as _image_service
from tests.test_card_development_candidate_groups import (
    _Development,
    _Identities,
    _Presentations,
    _Seeds,
    _Visuals,
)
from tests.test_card_pool_repository import _ready_group


def _accepted_card(tmp_path: Path):
    ready = _ready_group(tmp_path)
    cards = SqliteCardPoolRepository(tmp_path / "card-runtime.sqlite3")
    return cards.accept_initial_candidate(
        ready.group_id,
        ready.candidates[0].candidate_id,
        expected_revision=ready.revision,
        card_id="card-1",
    )


class _AcceptedReferenceImages:
    def load(self, group):
        return SimpleNamespace(
            image_uid=group.reference_image_uid,
            content_hash=group.reference_content_hash,
        )


def test_development_group_round_trips_source_dna_and_exact_actions(
    tmp_path: Path,
) -> None:
    card = _accepted_card(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    groups = SqliteCardCandidateGroupRepository(database_path)
    reservation = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    )
    reserved = reservation.reserve("card-1", expected_revision=1)

    assert groups.get(reserved.group_id) == reserved
    assert groups.claim_next_queued() is None
    claimed = groups.claim_next_queued(CardCandidateGroupKind.DEVELOPMENT)
    assert claimed is not None
    composer = CardDevelopmentCandidateComposer(
        development=_Development(),
        visual_projector=_Visuals(card.visual_recipe),
        presentation_realizer=_Presentations(card.presentation),
    )
    composition = composer.compose(
        card,
        tuple(
            candidate.materialization_seed for candidate in claimed.candidates
        ),
    )

    persisted = groups.complete_development_composition(
        claimed.group_id,
        expected_revision=claimed.revision,
        candidates=composition.candidates,
    )

    assert persisted.status is CardCandidateGroupStatus.GENERATING
    assert persisted.semantic_profile == card.semantic_profile
    assert persisted.imprint == card.state.identity.imprint
    assert persisted.source_card_id == "card-1"
    assert all(
        candidate.artifacts is not None
        and candidate.artifacts.development is not None
        and candidate.artifacts.card.tier_ordinal == 2
        for candidate in persisted.candidates
    )


def test_development_group_rejects_stale_source_card_atomically(
    tmp_path: Path,
) -> None:
    card = _accepted_card(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    groups = SqliteCardCandidateGroupRepository(database_path)
    reserved = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    ).reserve("card-1", expected_revision=1)
    claimed = groups.claim_next_queued(CardCandidateGroupKind.DEVELOPMENT)
    assert claimed is not None
    composition = CardDevelopmentCandidateComposer(
        development=_Development(),
        visual_projector=_Visuals(card.visual_recipe),
        presentation_realizer=_Presentations(card.presentation),
    ).compose(
        card,
        tuple(
            candidate.materialization_seed for candidate in claimed.candidates
        ),
    )

    with pytest.raises(CardCandidateGroupConflictError, match="stale"):
        groups.complete_development_composition(
            reserved.group_id,
            expected_revision=reserved.revision,
            candidates=composition.candidates,
        )

    assert groups.get(claimed.group_id) == claimed


def test_development_accept_replaces_state_but_retains_identity_dna(
    tmp_path: Path,
) -> None:
    card = _accepted_card(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    groups = SqliteCardCandidateGroupRepository(database_path)
    reserved = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    ).reserve("card-1", expected_revision=1)
    claimed = groups.claim_next_queued(CardCandidateGroupKind.DEVELOPMENT)
    assert claimed is not None
    composition = CardDevelopmentCandidateComposer(
        development=_Development(),
        visual_projector=_Visuals(card.visual_recipe),
        presentation_realizer=_Presentations(card.presentation),
    ).compose(
        card,
        tuple(
            candidate.materialization_seed for candidate in claimed.candidates
        ),
    )
    generating = groups.complete_development_composition(
        claimed.group_id,
        expected_revision=claimed.revision,
        candidates=composition.candidates,
    )
    generations = _Generations(
        database_path,
        prefix="development-generation",
    )
    images, outputs = _image_service(
        tmp_path,
        generations,
        reference_images=_AcceptedReferenceImages(),
    )
    submitted = images.submit(
        generating.group_id,
        expected_revision=generating.revision,
    )
    output_root = tmp_path / "outputs"
    for candidate in submitted.candidates:
        assert candidate.generation_uid is not None
        generations.observed[candidate.generation_uid] = "completed"
        outputs.save_outputs(
            candidate.generation_uid,
            (
                GenerationOutput(
                    f"development-image-{candidate.slot_index}",
                    "primary",
                    "save",
                    0,
                    output_root
                    / "card-battler"
                    / f"development-{candidate.slot_index}.png",
                    f"development-hash-{candidate.slot_index}",
                ),
            ),
        )
    ready = images.synchronize(
        submitted.group_id,
        expected_revision=submitted.revision,
    )

    developed = cards.accept_development_candidate(
        ready.group_id,
        ready.candidates[2].candidate_id,
        expected_revision=ready.revision,
    )

    assert developed.state.identity == card.state.identity
    assert developed.state.revision == 2
    assert developed.state.card.tier_ordinal == 2
    assert developed.state.active_image_uid == "development-image-2"
    assert developed.semantic_profile == card.semantic_profile
    assert developed.accepted_group_id == reserved.group_id
    completed = groups.get(ready.group_id)
    assert completed is not None
    assert completed.status is CardCandidateGroupStatus.COMPLETED

    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        cards.accept_development_candidate(
            ready.group_id,
            ready.candidates[1].candidate_id,
            expected_revision=ready.revision,
        )
    assert cards.get("card-1") == developed
