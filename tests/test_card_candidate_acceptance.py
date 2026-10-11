"""Business-policy tests for accepting complete Candidates into the pool."""

from __future__ import annotations

from dataclasses import replace

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupKind,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from comfyreview.application.card_battler_card_pool import (
    CardCandidateAcceptanceService,
    CardPoolCard,
    CardPoolConflictError,
    CardPoolNotFoundError,
    DevelopmentCardCandidateAcceptancePolicy,
    InitialCardCandidateAcceptancePolicy,
)
from tests.test_card_candidate_generation_policy import _composed_group
from tests.test_card_development_candidate_groups import (
    _Development,
    _pool_card,
)


class _Groups:
    def __init__(self, group) -> None:
        self.group = group

    def get(self, group_id):
        if self.group is None or self.group.group_id != group_id:
            return None
        return self.group


class _Cards:
    def __init__(self, result: CardPoolCard) -> None:
        self.result = result
        self.calls: list[tuple[str, str, int, str]] = []
        self.development_calls: list[tuple[str, str, int]] = []

    def accept_initial_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
        card_id: str,
    ) -> CardPoolCard:
        self.calls.append((group_id, candidate_id, expected_revision, card_id))
        return self.result

    def accept_development_candidate(
        self,
        group_id: str,
        candidate_id: str,
        *,
        expected_revision: int,
    ) -> CardPoolCard:
        self.development_calls.append(
            (group_id, candidate_id, expected_revision)
        )
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
    with pytest.raises(CardPoolConflictError, match="initial Candidate group"):
        policy.select(
            replace(
                group,
                kind=CardCandidateGroupKind.DEVELOPMENT,
                source_card_id="card-1",
                source_card_revision=1,
            ),
            group.candidates[0].candidate_id,
            expected_revision=group.revision,
        )
    with pytest.raises(CardPoolConflictError, match="comparison-ready"):
        policy.select(
            replace(group, status=CardCandidateGroupStatus.GENERATING),
            group.candidates[0].candidate_id,
            expected_revision=group.revision,
        )
    with pytest.raises(CardPoolNotFoundError):
        policy.select(group, "missing", expected_revision=group.revision)


def test_acceptance_service_delegates_one_revision_safe_card_identity(
    tmp_path,
) -> None:
    group = _ready_group(tmp_path)
    expected = _pool_card()
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


def test_development_acceptance_requires_exact_completed_action(
    tmp_path,
) -> None:
    initial = _ready_group(tmp_path)
    candidates = []
    for candidate in initial.candidates:
        assert candidate.artifacts is not None
        development = _Development().advance(candidate.artifacts.card)
        candidates.append(
            replace(
                candidate,
                artifacts=replace(
                    candidate.artifacts,
                    card=development.card,
                    visual_recipe=replace(
                        candidate.artifacts.visual_recipe,
                        tier_ordinal=development.card.tier_ordinal,
                    ),
                    development=development,
                ),
            )
        )
    group = replace(
        initial,
        kind=CardCandidateGroupKind.DEVELOPMENT,
        source_card_id="card-1",
        source_card_revision=1,
        candidates=tuple(candidates),
    )
    policy = DevelopmentCardCandidateAcceptancePolicy()

    assert (
        policy.select(
            group,
            group.candidates[0].candidate_id,
            expected_revision=group.revision,
        )
        == group.candidates[0]
    )
    with pytest.raises(CardPoolConflictError, match="revision is stale"):
        policy.select(
            group,
            group.candidates[0].candidate_id,
            expected_revision=group.revision - 1,
        )
    first_artifacts = group.candidates[0].artifacts
    assert first_artifacts is not None
    without_action = replace(
        group,
        candidates=(
            replace(
                group.candidates[0],
                artifacts=replace(
                    first_artifacts,
                    development=None,
                ),
            ),
            *group.candidates[1:],
        ),
    )
    with pytest.raises(CardPoolConflictError, match="Development Candidate"):
        policy.select(
            without_action,
            without_action.candidates[0].candidate_id,
            expected_revision=without_action.revision,
        )

    expected = _pool_card()
    cards = _Cards(expected)
    result = CardCandidateAcceptanceService(
        groups=_Groups(group),
        cards=cards,
        identities=_Identities(),
        policy=InitialCardCandidateAcceptancePolicy(),
        development_policy=policy,
    ).accept(
        group.group_id,
        group.candidates[2].candidate_id,
        expected_revision=group.revision,
    )
    assert result is expected
    assert cards.calls == []
    assert cards.development_calls == [
        (group.group_id, group.candidates[2].candidate_id, group.revision)
    ]

    with pytest.raises(CardPoolConflictError, match="source Card revision"):
        policy.select(
            initial,
            initial.candidates[0].candidate_id,
            expected_revision=initial.revision,
        )
    with pytest.raises(CardPoolConflictError, match="comparison-ready"):
        policy.select(
            replace(group, status=CardCandidateGroupStatus.GENERATING),
            group.candidates[0].candidate_id,
            expected_revision=group.revision,
        )
    with pytest.raises(CardPoolNotFoundError):
        policy.select(group, "missing", expected_revision=group.revision)


def test_confirmed_pool_card_validates_acceptance_provenance() -> None:
    card = _pool_card()

    with pytest.raises(ValueError, match="provenance"):
        replace(card, accepted_group_id="")
    with pytest.raises(ValueError, match="semantic provenance"):
        replace(
            card,
            semantic_profile=replace(
                card.semantic_profile,
                image_uid="other-image",
            ),
        )
    with pytest.raises(ValueError, match="Recipe tier"):
        replace(
            card,
            visual_recipe=replace(card.visual_recipe, tier_ordinal=2),
        )
