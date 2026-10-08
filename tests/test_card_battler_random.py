"""Golden behavior tests for Card Battler RNG domain separation."""

from __future__ import annotations

from collections.abc import Callable

import pytest

from comfyreview.application.card_battler_random import (
    DomainSeparatedCardRandom,
)


def _random() -> DomainSeparatedCardRandom:
    return DomainSeparatedCardRandom(
        (
            "image-1",
            "semantic-v1",
            "prototype@2",
            "semantic_imprint_mapping@2",
            "deterministic_rng@2",
            "42",
        )
    )


def test_domain_random_has_stable_independent_golden_vectors() -> None:
    random = _random()

    assert random.integer("stat-profile", modulo=1_000_000) == 818_617
    assert random.integer("stats", modulo=1_000_000) == 109_752
    assert random.integer("initial-trait", modulo=1_000_000) == 829_762
    assert random.integer("parameter:bonus", modulo=1_000_000) == 886_138
    assert random.integer("prompt:style", modulo=1_000_000) == 227_245
    assert random.integer("stats", modulo=1_000_000) == random.integer(
        "stats", modulo=1_000_000
    )


def test_weighted_choice_is_input_order_independent() -> None:
    random = _random()
    candidates = (("zeta", 200), ("alpha", 700), ("middle", 100))

    assert random.weighted_choice("initial-trait", candidates) == "middle"
    assert (
        random.weighted_choice("initial-trait", tuple(reversed(candidates)))
        == "middle"
    )
    assert random.integer("prompt:style", modulo=1000) == _random().integer(
        "prompt:style", modulo=1000
    )
    assert random.weighted_choice("stats", (("only", 1),)) == "only"


@pytest.mark.parametrize(
    "operation, message",
    (
        (lambda: DomainSeparatedCardRandom(()), "seed material"),
        (lambda: _random().integer("", modulo=2), "domain"),
        (lambda: _random().integer("stats", modulo=0), "modulo"),
        (lambda: _random().weighted_choice("stats", ()), "unique"),
        (
            lambda: _random().weighted_choice(
                "stats", (("same", 1), ("same", 2))
            ),
            "unique",
        ),
        (
            lambda: _random().weighted_choice("stats", (("alpha", 0),)),
            "positive",
        ),
    ),
)
def test_domain_random_rejects_invalid_inputs(
    operation: Callable[[], object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        operation()
