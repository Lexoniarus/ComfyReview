"""Business-policy tests for accepting complete Candidates into the pool."""

from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_card_pool import (
    CardCandidateAcceptanceService,
    CardPoolConflictError,
    CardPoolNotFoundError,
    InitialCardCandidateAcceptancePolicy,
)
from tests.test_card_candidate_generation_policy import _composed_group


class _Groups:
    def __init__(self, group) -> None:
        self.group = group

    def get(self, group_id):
        if self.group is None or self.group.group_id != group_id:
            return None
        return self.group


class _Cards:
    def __init__(self, result) -> None:
        self.result = result
        self.calls = []

    def accept_initial_candidate(
        self,
        group_id,
        candidate_id,
        *,
        expected_revision,
        card_id,
    ):
        self.calls.append((group_id, candidate_id, expected_revision, card_id))
        return self.result


class _Identities:
    def new_card_id(self):
        return "card-1"


def _ready_group(tmp_path):
    group = _composed_group(tmp_path)
    return replace(
        group,
        status=CardCandidateGroupStatus.READY,
        candidates=tuple(
            replace(
                candidate,
                status=CardCandidateStatus.COMPLETED,
                generation_uid=f"generation-{candidate.slot_index}",
                recipe_hash="recipe-hash",
                generation_policy_revision="generation-v1",
                output_image_uid=f"image-{candidate.slot_index}",
                output_content_hash=f"hash-{candidate.slot_index}",
            )
            for candidate in group.candidates
        ),
    )


def test_acceptance_policy_requires_terminal_group_and_completed_candidate(
    tmp_path,
) -> None:
    group = _ready_group(tmp_path)
    policy = InitialCardCandidateAcceptancePolicy()

    assert (
        policy.select(
            group,
            group.candidates[1].candidate_id,
            expected_revision=group.revision,
        )
        == group.candidates[1]
    )
    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        policy.select(
            group,
            group.candidates[1].candidate_id,
            expected_revision=group.revision - 1,
        )
    with pytest.raises(CardPoolConflictError, match="completed Candidate"):
        policy.select(
            replace(
                group,
                candidates=(
                    replace(
                        group.candidates[0],
                        status=CardCandidateStatus.FAILED,
                        generation_uid=None,
                        recipe_hash=None,
                        generation_policy_revision=None,
                        output_image_uid=None,
                        output_content_hash=None,
                    ),
                    *group.candidates[1:],
                ),
            ),
            group.candidates[0].candidate_id,
            expected_revision=group.revision,
        )


def test_acceptance_service_delegates_one_revision_safe_card_identity(
    tmp_path,
) -> None:
    group = _ready_group(tmp_path)
    expected = SimpleNamespace(state="confirmed")
    cards = _Cards(expected)
    service = CardCandidateAcceptanceService(
        groups=_Groups(group),
        cards=cards,
        identities=_Identities(),
        policy=InitialCardCandidateAcceptancePolicy(),
    )

    result = service.accept(
        group.group_id,
        group.candidates[2].candidate_id,
        expected_revision=group.revision,
    )

    assert result is expected
    assert cards.calls == [
        (
            group.group_id,
            group.candidates[2].candidate_id,
            group.revision,
            "card-1",
        )
    ]
    with pytest.raises(CardPoolNotFoundError):
        CardCandidateAcceptanceService(
            groups=_Groups(None),
            cards=cards,
            identities=_Identities(),
            policy=InitialCardCandidateAcceptancePolicy(),
        ).accept("missing", "candidate", expected_revision=1)
