"""Lifecycle tests for the single-owner Card candidate worker."""

from __future__ import annotations

from threading import Event

import pytest

from comfyreview.application.card_battler_candidate_processing import (
    CardCandidateGroupWorker,
)


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
