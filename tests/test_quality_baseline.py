"""Tests for the versioned diagnostic-baseline and targeted quality modes."""

from scripts.quality import (
    _find_baseline_growth,
    targeted_test_nodes,
)


def test_diagnostic_baseline_can_shrink() -> None:
    previous = {
        "tools": {
            "ruff": {"ruff|legacy.py|F401": 2},
            "mypy": {"mypy|legacy.py|arg-type": 1},
        }
    }
    current = {
        "tools": {
            "ruff": {"ruff|legacy.py|F401": 1},
            "mypy": {},
        }
    }

    assert _find_baseline_growth(current, previous) == []


def test_diagnostic_baseline_cannot_grow() -> None:
    previous = {"tools": {"ruff": {"ruff|legacy.py|F401": 1}}}
    current = {
        "tools": {
            "ruff": {
                "ruff|legacy.py|F401": 2,
                "ruff|legacy.py|F821": 1,
            },
            "mypy": {"mypy|legacy.py|arg-type": 1},
        }
    }

    assert _find_baseline_growth(current, previous) == [
        "mypy|legacy.py|arg-type: 1 > 0",
        "ruff|legacy.py|F401: 2 > 1",
        "ruff|legacy.py|F821: 1 > 0",
    ]


def test_targeted_tests_include_contracts_and_remove_duplicates() -> None:
    assert targeted_test_nodes(
        [
            "tests/test_review_service.py::test_review_service_submits_rating_in_order",
            "tests/test_architecture.py",
        ]
    ) == (
        "tests/test_architecture.py",
        "tests/test_function_test_manifest.py",
        "tests/test_review_service.py::test_review_service_submits_rating_in_order",
    )
