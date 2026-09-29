"""Tests for the versioned diagnostic-baseline ratchet."""

from scripts.quality import _find_baseline_growth


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
