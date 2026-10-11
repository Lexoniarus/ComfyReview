"""Worker-pass tests for development Candidate composition."""

from __future__ import annotations

from typing import cast

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupStatus,
)
from comfyreview.application.card_battler_candidate_processing import (
    CardCandidateCompositionCoordinator,
    DevelopmentCandidateGroupRepository,
    DevelopmentCardCandidateGroupProcessor,
)
from comfyreview.application.card_battler_development_groups import (
    CardDevelopmentCandidateComposer,
    CardDevelopmentCandidateGroupService,
    CardDevelopmentGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_candidate_groups import (
    SqliteCardCandidateGroupRepository,
)
from comfyreview.repositories.sqlite.card_battler_card_pool import (
    SqliteCardPoolRepository,
)
from tests.test_card_development_candidate_groups import (
    _Development,
    _Identities,
    _pool_card,
    _Presentations,
    _Seeds,
    _Visuals,
)
from tests.test_card_pool_repository import _ready_group


def test_development_processor_composes_without_analysis_or_mapping(
    tmp_path,
) -> None:
    ready = _ready_group(tmp_path)
    database_path = tmp_path / "card-runtime.sqlite3"
    cards = SqliteCardPoolRepository(database_path)
    card = cards.accept_initial_candidate(
        ready.group_id,
        ready.candidates[0].candidate_id,
        expected_revision=ready.revision,
        card_id="card-1",
    )
    groups = SqliteCardCandidateGroupRepository(database_path)
    reserved = CardDevelopmentCandidateGroupService(
        cards=cards,
        groups=groups,
        identities=_Identities(),
        seeds=_Seeds(),
    ).reserve("card-1", expected_revision=1)
    development = _Development()
    processor = DevelopmentCardCandidateGroupProcessor(
        groups=cast(DevelopmentCandidateGroupRepository, groups),
        cards=cards,
        composer=CardDevelopmentCandidateComposer(
            development=development,
            visual_projector=_Visuals(card.visual_recipe),
            presentation_realizer=_Presentations(card.presentation),
        ),
    )

    assert processor.process_next() is True
    assert processor.process_next() is False

    persisted = groups.get(reserved.group_id)
    assert persisted is not None
    assert persisted.status is CardCandidateGroupStatus.GENERATING
    assert len(development.calls) == 4
    assert all(call == card.state.card for call in development.calls)
    assert persisted.semantic_profile == card.semantic_profile
    assert persisted.imprint == card.state.identity.imprint


class _CompositionPass:
    def __init__(self, results, *, recovered=0) -> None:
        self.results = list(results)
        self.recovered = recovered
        self.calls = 0

    def recover_interrupted(self):
        return self.recovered

    def process_next(self):
        self.calls += 1
        return self.results.pop(0)


def test_composition_coordinator_prioritizes_initial_groups() -> None:
    initial = _CompositionPass((True, False), recovered=3)
    development = _CompositionPass((True,))
    coordinator = CardCandidateCompositionCoordinator(
        initial=initial,
        development=development,
    )

    assert coordinator.recover_interrupted() == 3
    assert coordinator.process_next() is True
    assert development.calls == 0
    assert coordinator.process_next() is True
    assert development.calls == 1


class _FailingDevelopmentGroups:
    def __init__(self, group) -> None:
        self.group = group
        self.failures: list[str] = []

    def claim_next_queued(self, kind):
        group, self.group = self.group, None
        return group

    def complete_development_composition(self, *args, **kwargs):
        raise AssertionError("composition must not complete")

    def fail_composition(
        self,
        group_id,
        *,
        expected_revision,
        failure_category,
    ):
        self.failures.append(failure_category)


class _CaptureGroups:
    @staticmethod
    def create(reserved):
        return reserved


class _CardQuery:
    def __init__(self, card) -> None:
        self.card = card

    def get(self, card_id):
        return self.card


class _FailingComposer:
    @staticmethod
    def compose(card, seeds):
        raise RuntimeError("composition failed")


@pytest.mark.parametrize(
    "mode, expected_failure",
    [
        ("missing-source", "ValueError"),
        ("stale-card", "ValueError"),
        ("composer", "RuntimeError"),
    ],
)
def test_development_processor_persists_controlled_failures(
    mode: str,
    expected_failure: str,
) -> None:
    card = _pool_card()
    group = CardDevelopmentCandidateGroupService(
        cards=_CardQuery(card),
        groups=cast(CardDevelopmentGroupRepository, _CaptureGroups()),
        identities=_Identities(),
        seeds=_Seeds(),
    ).reserve("card-1", expected_revision=1)
    if mode == "missing-source":
        object.__setattr__(group, "source_card_id", None)
    cards = _CardQuery(None if mode == "stale-card" else card)
    groups = _FailingDevelopmentGroups(group)
    composer = (
        _FailingComposer()
        if mode == "composer"
        else CardDevelopmentCandidateComposer(
            development=_Development(),
            visual_projector=_Visuals(card.visual_recipe),
            presentation_realizer=_Presentations(card.presentation),
        )
    )
    processor = DevelopmentCardCandidateGroupProcessor(
        groups=cast(DevelopmentCandidateGroupRepository, groups),
        cards=cards,
        composer=composer,  # type: ignore[arg-type]
    )

    assert processor.process_next() is True
    assert groups.failures == [expected_failure]
    assert processor.process_next() is False
