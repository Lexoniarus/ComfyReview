"""Reservation tests for persistent four-Card candidate groups."""

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

import pytest

from comfyreview.application.card_battler_candidate_group_service import (
    CardCandidateGroupIdentitySource,
    CardCandidateGroupSeedSource,
    CardCandidateSourceEligibilityError,
    InitialCardCandidateGroupService,
)
from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroupRepository,
    CardCandidateGroupStatus,
    CardCandidateStatus,
    candidate_materialization_seeds,
)
from comfyreview.application.card_battler_preview import (
    CardSourceEligibilityPolicy,
)
from comfyreview.application.card_battler_semantics import (
    CardSourceImageProvider,
)
from comfyreview.application.image_queries import ImageContextQueryService
from comfyreview.application.workspace_settings import ContentLevel
from tests.test_card_battler_session_service import _source


class _ImageContexts:
    def __init__(self, level: ContentLevel) -> None:
        self._level = level

    def get_image(self, image_uid):
        return SimpleNamespace(
            image_uid=image_uid,
            content=SimpleNamespace(effective_level=self._level),
        )


class _SourceImages:
    def __init__(self, *, unavailable: bool = False) -> None:
        self._unavailable = unavailable
        self.calls = 0

    def load(self, image_uid):
        self.calls += 1
        if self._unavailable:
            raise FileNotFoundError(image_uid)
        return _source()


class _Identities:
    def new_group_id(self):
        return "group-1"

    def candidate_id(self, group_id, slot_index):
        return f"{group_id}-candidate-{slot_index}"


class _Seeds:
    def new_seed(self):
        return 71


class _Groups:
    def __init__(self) -> None:
        self.created = []

    def create(self, group):
        self.created.append(group)
        return group

    def get(self, group_id):
        return next(
            (item for item in self.created if item.group_id == group_id),
            None,
        )


def _service(
    groups,
    *,
    level: ContentLevel = ContentLevel.STANDARD,
    unavailable: bool = False,
) -> tuple[InitialCardCandidateGroupService, _SourceImages]:
    sources = _SourceImages(unavailable=unavailable)
    return (
        InitialCardCandidateGroupService(
            image_contexts=cast(
                ImageContextQueryService,
                _ImageContexts(level),
            ),
            source_images=cast(CardSourceImageProvider, sources),
            eligibility=CardSourceEligibilityPolicy(),
            groups=cast(CardCandidateGroupRepository, groups),
            identities=cast(CardCandidateGroupIdentitySource, _Identities()),
            seeds=cast(CardCandidateGroupSeedSource, _Seeds()),
        ),
        sources,
    )


def test_candidate_seed_derivation_is_stable_and_group_separated() -> None:
    first = candidate_materialization_seeds("image-1", 71)

    assert first == candidate_materialization_seeds("image-1", 71)
    assert len(first) == len(set(first)) == 4
    assert first != candidate_materialization_seeds("image-1", 72)
    with pytest.raises(ValueError, match="identity is required"):
        candidate_materialization_seeds(" ", 71)


def test_initial_group_reservation_does_not_run_analysis_or_mapping() -> None:
    groups = _Groups()
    service, sources = _service(groups)

    group = service.reserve("image-1")

    assert sources.calls == 1
    assert group.status is CardCandidateGroupStatus.QUEUED
    assert group.semantic_profile is None
    assert group.imprint is None
    assert tuple(item.slot_index for item in group.candidates) == (0, 1, 2, 3)
    assert all(
        item.status is CardCandidateStatus.QUEUED for item in group.candidates
    )
    assert tuple(item.materialization_seed for item in group.candidates) == (
        candidate_materialization_seeds("image-1", 71)
    )


@pytest.mark.parametrize(
    "level, unavailable, message",
    [
        (ContentLevel.SEXY, False, "content_level"),
        (ContentLevel.STANDARD, True, "source_unavailable"),
    ],
)
def test_initial_group_reservation_rejects_ineligible_or_missing_sources(
    level: ContentLevel,
    unavailable: bool,
    message: str,
) -> None:
    service, _ = _service(
        _Groups(),
        level=level,
        unavailable=unavailable,
    )

    with pytest.raises(CardCandidateSourceEligibilityError, match=message):
        service.reserve("image-1")
