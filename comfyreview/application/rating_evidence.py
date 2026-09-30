"""Pure policies for weighting and classifying legacy review evidence."""

from __future__ import annotations

import math

SUCCESS_THRESHOLD_DEFAULT = 4
DELETE_WEIGHT_DEFAULT = 5


def _rating_weight_for_run(run: int) -> int:
    """Return the quadratic evidence weight for a one-based review run."""
    normalized_run = max(1, int(run or 1))
    return normalized_run * normalized_run


def _pass_min(run: int, base_pass_min: int) -> int:
    """Return the rating required to count as success for a review run."""
    normalized_run = max(1, int(run or 1))
    return min(10, int(base_pass_min) + normalized_run - 1)


def _fail_max(run: int) -> int:
    """Return the highest rating that counts as failure for a review run."""
    normalized_run = max(1, int(run or 1))
    return 0 if normalized_run <= 1 else min(10, normalized_run - 1)


def _delete_weight_for_run(run: int, base_delete_weight: int) -> int:
    """Return the decreasing failure weight assigned to a delete event."""
    normalized_run = max(1, int(run or 1))
    return max(1, int(base_delete_weight) - normalized_run + 1)


def _classify(
    *,
    run: int,
    rating: int | None,
    deleted: int,
    base_pass_min: int,
) -> bool | None:
    """Classify one legacy observation as success, failure, or neutral."""
    if int(deleted or 0) == 1:
        return False
    if rating is None:
        return None

    normalized_run = max(1, int(run or 1))
    normalized_rating = int(rating)
    if normalized_rating >= _pass_min(normalized_run, base_pass_min):
        return True
    if normalized_run > 1 and normalized_rating <= _fail_max(normalized_run):
        return False
    return None


def _sigmoid(value: float) -> float:
    """Convert a finite logit to a probability, tolerating overflow."""
    try:
        return 1.0 / (1.0 + math.exp(-value))
    except OverflowError:
        return 0.0


def _bayes_lb05(success: float, fail_weight: float) -> float:
    """Return the legacy conservative lower-bound proxy for evidence."""
    alpha = float(int(success) + 1)
    beta = float(int(fail_weight) + 1)
    mean = alpha / (alpha + beta)

    evidence_count = int(success) + int(fail_weight)
    if evidence_count <= 0:
        return 0.0

    variance = (alpha * beta) / (((alpha + beta) ** 2) * (alpha + beta + 1.0))
    standard_deviation = math.sqrt(max(0.0, variance))
    return float(mean - 1.645 * standard_deviation)
