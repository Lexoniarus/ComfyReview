"""Lifecycle tests for the single-owner Card candidate worker."""

from __future__ import annotations

from dataclasses import dataclass, replace
from threading import Event

import pytest

from comfyreview.application.card_battler_candidate_groups import (
    CardCandidateStatus,
)
from comfyreview.application.card_battler_candidate_processing import (
    CardCandidateGroupLifecycleProcessor,
    CardCandidateGroupWorker,
)
from tests.test_card_candidate_generation_policy import _composed_group


class _Processor:
    def __init__(self, *, fail_recovery: bool = False) -> None:
        self.fail_recovery = fail_recovery
        self.recovery_calls = 0
        self.process_calls = 0
        self.processed = Event()

    def recover_interrupted(self):
        self.recovery_calls += 1
        if self.fail_recovery:
            raise RuntimeError("recovery failed")
        return 1

    def process_next(self):
        self.process_calls += 1
        self.processed.set()
        return False


def test_candidate_group_worker_owns_one_recovering_thread() -> None:
    processor = _Processor()
    worker = CardCandidateGroupWorker(processor, poll_interval_seconds=0.05)

    worker.start()
    worker.start()
    assert processor.processed.wait(timeout=1.0)

    assert worker.stop(timeout_seconds=1.0) is True
    assert worker.stop(timeout_seconds=1.0) is True
    assert processor.recovery_calls == 1
    assert processor.process_calls >= 1


def test_candidate_group_worker_does_not_start_after_recovery_failure() -> (
    None
):
    processor = _Processor(fail_recovery=True)
    worker = CardCandidateGroupWorker(processor)

    with pytest.raises(RuntimeError, match="recovery failed"):
        worker.start()

    assert worker.stop() is True
    assert processor.process_calls == 0


class _LifecycleComposition:
    def __init__(self, processed: bool) -> None:
        self.processed = processed

    def recover_interrupted(self):
        return 2

    def process_next(self):
        return self.processed


class _LifecycleGroups:
    def __init__(self, *groups) -> None:
        self.groups = groups

    def generating_groups(self):
        return self.groups


@dataclass(frozen=True)
class _Revision:
    revision: int


class _LifecycleImages:
    def __init__(self, *, revision_changed: bool = True) -> None:
        self.revision_changed = revision_changed
        self.submitted: list[tuple[str, int]] = []
        self.synchronized: list[tuple[str, int]] = []

    def submit(self, group_id: str, *, expected_revision: int) -> object:
        self.submitted.append((group_id, expected_revision))
        return None

    def synchronize(
        self,
        group_id: str,
        *,
        expected_revision: int,
    ) -> _Revision:
        self.synchronized.append((group_id, expected_revision))
        increment = 1 if self.revision_changed else 0
        return _Revision(expected_revision + increment)


def test_lifecycle_processor_dispatches_composition_submission_and_polling(
    tmp_path,
) -> None:
    group = _composed_group(tmp_path)
    images = _LifecycleImages()
    composition = _LifecycleComposition(True)
    lifecycle = CardCandidateGroupLifecycleProcessor(
        composition=composition,
        groups=_LifecycleGroups(group),
        images=images,
    )

    assert lifecycle.recover_interrupted() == 2
    assert lifecycle.process_next() is True
    assert images.submitted == []

    composition.processed = False
    assert lifecycle.process_next() is True
    assert images.submitted == [(group.group_id, group.revision)]

    submitted = replace(
        group,
        candidates=tuple(
            replace(
                candidate,
                status=CardCandidateStatus.SUBMITTED,
                generation_uid=f"generation-{candidate.slot_index}",
                recipe_hash="recipe-hash",
                generation_policy_revision="generation-v1",
            )
            for candidate in group.candidates
        ),
    )
    groups = _LifecycleGroups(submitted)
    lifecycle = CardCandidateGroupLifecycleProcessor(
        composition=composition,
        groups=groups,
        images=images,
    )

    assert lifecycle.process_next() is True
    assert images.synchronized[-1] == (group.group_id, group.revision)
    images.revision_changed = False
    assert lifecycle.process_next() is False

    second = replace(
        submitted,
        group_id="group-2",
        candidates=tuple(
            replace(
                candidate,
                candidate_id=f"group-2-candidate-{candidate.slot_index}",
                group_id="group-2",
            )
            for candidate in submitted.candidates
        ),
    )
    lifecycle = CardCandidateGroupLifecycleProcessor(
        composition=composition,
        groups=_LifecycleGroups(submitted, second),
        images=images,
    )

    assert lifecycle.process_next() is False
    assert lifecycle.process_next() is False
    assert [item[0] for item in images.synchronized[-2:]] == [
        group.group_id,
        second.group_id,
    ]
