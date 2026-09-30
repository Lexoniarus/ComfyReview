"""Behavior tests for the legacy-compatible review evidence policy."""

from __future__ import annotations

from comfyreview.application.rating_evidence import (
    _bayes_lb05,
    _classify,
    _delete_weight_for_run,
    _fail_max,
    _pass_min,
    _rating_weight_for_run,
    _sigmoid,
)


def test_review_evidence_weights_and_thresholds_are_run_aware() -> None:
    assert _rating_weight_for_run(0) == 1
    assert _rating_weight_for_run(3) == 9
    assert _pass_min(1, 4) == 4
    assert _pass_min(20, 4) == 10
    assert _fail_max(1) == 0
    assert _fail_max(4) == 3
    assert _delete_weight_for_run(1, 5) == 5
    assert _delete_weight_for_run(20, 5) == 1


def test_review_evidence_classifies_success_failure_and_neutral() -> None:
    assert _classify(run=1, rating=10, deleted=1, base_pass_min=4) is False
    assert _classify(run=1, rating=None, deleted=0, base_pass_min=4) is None
    assert _classify(run=1, rating=4, deleted=0, base_pass_min=4) is True
    assert _classify(run=2, rating=1, deleted=0, base_pass_min=4) is False
    assert _classify(run=2, rating=3, deleted=0, base_pass_min=4) is None


def test_review_evidence_probability_helpers_handle_boundaries() -> None:
    assert _sigmoid(0.0) == 0.5
    assert _sigmoid(-1000.0) == 0.0
    assert _bayes_lb05(0.0, 0.0) == 0.0
    assert _bayes_lb05(10.0, 0.0) > _bayes_lb05(1.0, 9.0)
