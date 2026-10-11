"""Behavior tests for Candidate-group catalog commands."""

from __future__ import annotations

from dataclasses import replace
from typing import cast

import pytest

from comfyreview.application.card_battler_candidate_group_catalog import (
    CardCandidateGroupCatalogService,
)
from comfyreview.application.card_battler_candidate_group_service import (
    InitialCardCandidateGroupService,
)
from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateGroup,
    CardCandidateGroupConflictError,
    CardCandidateGroupKind,
    CardCandidateGroupNotFoundError,
    CardCandidateGroupRepository,
    CardCandidateGroupStatus,
    CardCandidateStatus,
)
from tests.test_card_candidate_group_reservation import _Groups, _service


class _CatalogGroups:
    def __init__(self, group: CardCandidateGroup) -> None:
        self.group = group

    def list_groups(self):
        return (self.group,)

    def get(self, group_id):
        return self.group if group_id == self.group.group_id else None

    def reject(self, group_id, *, expected_revision):
        if (
            group_id != self.group.group_id
            or expected_revision != self.group.revision
            or self.group.status
            not in {
                CardCandidateGroupStatus.READY,
                CardCandidateGroupStatus.PARTIAL_FAILURE,
                CardCandidateGroupStatus.FAILED,
            }
        ):
            raise CardCandidateGroupConflictError("stale rejection")
        self.group = replace(
            self.group,
            revision=self.group.revision + 1,
            status=CardCandidateGroupStatus.REJECTED,
            candidates=tuple(
                replace(
                    candidate,
                    group_revision=self.group.revision + 1,
                    status=(
                        CardCandidateStatus.REJECTED
                        if candidate.status is CardCandidateStatus.COMPLETED
                        else candidate.status
                    ),
                )
                for candidate in self.group.candidates
            ),
        )
        return self.group


class _FreshInitialGroups:
    def __init__(self, group: CardCandidateGroup) -> None:
        self.group = group
        self.calls: list[str] = []

    def reserve(self, image_uid: str) -> CardCandidateGroup:
        self.calls.append(image_uid)
        return self.group


def _reserved_group() -> CardCandidateGroup:
    groups = _Groups()
    return _service(groups)[0].reserve("image-1")


def _terminal_group() -> CardCandidateGroup:
    group = _reserved_group()
    return replace(
        group,
        status=CardCandidateGroupStatus.FAILED,
        candidates=tuple(
            replace(candidate, status=CardCandidateStatus.FAILED)
            for candidate in group.candidates
        ),
    )


def test_group_catalog_lists_reads_and_rejects_terminal_groups() -> None:
    repository = _CatalogGroups(_terminal_group())
    initial = _FreshInitialGroups(_reserved_group())
    service = CardCandidateGroupCatalogService(
        groups=cast(CardCandidateGroupRepository, repository),
        initial_groups=cast(InitialCardCandidateGroupService, initial),
    )

    assert service.list_groups() == (repository.group,)
    assert service.get(repository.group.group_id) == repository.group

    rejected = service.reject(
        repository.group.group_id,
        expected_revision=repository.group.revision,
    )

    assert rejected.status is CardCandidateGroupStatus.REJECTED
    assert rejected.revision == 2
    with pytest.raises(CardCandidateGroupNotFoundError):
        service.get("missing")
    with pytest.raises(CardCandidateGroupConflictError, match="stale"):
        service.reject(rejected.group_id, expected_revision=1)


def test_group_catalog_retry_reserves_a_fresh_initial_analysis() -> None:
    old_group = _terminal_group()
    reserved = _reserved_group()
    fresh_group = replace(
        reserved,
        group_id="fresh-group",
        candidates=tuple(
            replace(candidate, group_id="fresh-group")
            for candidate in reserved.candidates
        ),
    )
    repository = _CatalogGroups(old_group)
    initial = _FreshInitialGroups(fresh_group)
    service = CardCandidateGroupCatalogService(
        groups=cast(CardCandidateGroupRepository, repository),
        initial_groups=cast(InitialCardCandidateGroupService, initial),
    )

    restarted = service.retry_initial(
        old_group.group_id,
        expected_revision=old_group.revision,
    )

    assert restarted.group_id == "fresh-group"
    assert initial.calls == [old_group.source_image_uid]
    assert repository.group.status is CardCandidateGroupStatus.REJECTED

    repository.group = replace(
        old_group,
        kind=CardCandidateGroupKind.DEVELOPMENT,
        source_card_id="card-1",
        source_card_revision=1,
    )
    with pytest.raises(CardCandidateGroupConflictError, match="initial"):
        service.retry_initial(
            repository.group.group_id,
            expected_revision=repository.group.revision,
        )
