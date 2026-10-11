"""SQLite behavior tests for atomic Candidate acceptance into the pool."""

from __future__ import annotations

from pathlib import Path

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_card_pool import (
    CardCandidateAcceptanceService,
    CardPoolConflictError,
    InitialCardCandidateAcceptancePolicy,
)
from comfyreview.application.generation_outputs import GenerationOutput
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from tests.test_card_candidate_generation_policy import _composed_group
from tests.test_card_candidate_image_service import _Generations, _service


class _Identities:
    def new_card_id(self):
        return "card-1"


def _ready_group(tmp_path: Path):
    group = _composed_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    generations = _Generations(database_path)
    service, outputs = _service(tmp_path, generations)
    submitted = service.submit(
        group.group_id,
        expected_revision=group.revision,
    )
    output_root = tmp_path / "outputs"
    for candidate in submitted.candidates:
        assert candidate.generation_uid is not None
        generations.observed[candidate.generation_uid] = "completed"
        outputs.save_outputs(
            candidate.generation_uid,
            (
                GenerationOutput(
                    f"image-{candidate.slot_index}",
                    "primary",
                    "save",
                    0,
                    output_root
                    / "card-battler"
                    / f"candidate-{candidate.slot_index}.png",
                    f"hash-{candidate.slot_index}",
                ),
            ),
        )
    return service.synchronize(
        group.group_id,
        expected_revision=submitted.revision,
    )


def test_card_pool_accepts_one_candidate_and_completes_group_atomically(
    tmp_path: Path,
) -> None:
    ready = _ready_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    groups = SqliteCardCandidateGroupRepository(database_path)
    cards = SqliteCardPoolRepository(database_path)
    service = CardCandidateAcceptanceService(
        groups=groups,
        cards=cards,
        identities=_Identities(),
        policy=InitialCardCandidateAcceptancePolicy(),
    )

    accepted = service.accept(
        ready.group_id,
        ready.candidates[1].candidate_id,
        expected_revision=ready.revision,
    )
    accepted_artifacts = ready.candidates[1].artifacts
    assert accepted_artifacts is not None

    assert accepted.state.identity.card_id == "card-1"
    assert accepted.state.identity.source_image_uid == ready.source_image_uid
    assert accepted.semantic_profile == ready.semantic_profile
    assert accepted.state.card == accepted_artifacts.card
    assert accepted.visual_recipe == accepted_artifacts.visual_recipe
    assert accepted.state.active_image_uid == "image-1"
    assert cards.get("card-1") == accepted
    assert cards.get("missing") is None
    assert cards.list_cards() == (accepted,)

    completed = groups.get(ready.group_id)
    assert completed is not None
    assert completed.revision == ready.revision + 1
    assert completed.status is CardCandidateGroupStatus.COMPLETED
    assert [candidate.status for candidate in completed.candidates] == [
        CardCandidateStatus.REJECTED,
        CardCandidateStatus.ACCEPTED,
        CardCandidateStatus.REJECTED,
        CardCandidateStatus.REJECTED,
    ]


def test_card_pool_rolls_back_stale_or_duplicate_acceptance(
    tmp_path: Path,
) -> None:
    ready = _ready_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    groups = SqliteCardCandidateGroupRepository(database_path)
    cards = SqliteCardPoolRepository(database_path)

    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        cards.accept_initial_candidate(
            ready.group_id,
            ready.candidates[0].candidate_id,
            expected_revision=ready.revision - 1,
            card_id="card-stale",
        )
    assert cards.list_cards() == ()
    assert groups.get(ready.group_id) == ready

    cards.accept_initial_candidate(
        ready.group_id,
        ready.candidates[0].candidate_id,
        expected_revision=ready.revision,
        card_id="card-1",
    )
    completed = groups.get(ready.group_id)
    assert completed is not None
    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        cards.accept_initial_candidate(
            ready.group_id,
            ready.candidates[2].candidate_id,
            expected_revision=ready.revision,
            card_id="card-2",
        )
    assert groups.get(ready.group_id) == completed
    assert tuple(
        card.state.identity.card_id for card in cards.list_cards()
    ) == ("card-1",)
