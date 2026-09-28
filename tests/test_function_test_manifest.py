"""Tests for public-callable discovery and behavior-test ownership."""

from __future__ import annotations

from pathlib import Path

from quality.callable_manifest import (
    discover_public_callables,
    validate_manifest,
)
from tests.function_test_manifest import FUNCTION_TEST_MANIFEST

ROOT = Path(__file__).resolve().parents[1]
SCOPE_PATH = ROOT / "quality" / "core_scope.txt"


def test_discovers_public_core_callables(tmp_path: Path) -> None:
    package = tmp_path / "sample"
    package.mkdir()
    (package / "module.py").write_text(
        "def visible():\n    return 1\n\n"
        "def _hidden():\n    return 2\n\n"
        "class Worker:\n"
        "    def run(self):\n        return 3\n"
        "    def _helper(self):\n        return 4\n",
        encoding="utf-8",
    )
    scope = tmp_path / "scope.txt"
    scope.write_text(
        "# comment\nmissing.py\nsample\nsample/module.py\n", encoding="utf-8"
    )

    assert discover_public_callables(tmp_path, scope) == {
        "sample.module:Worker.run",
        "sample.module:visible",
    }


def test_reports_invalid_manifest_entries(tmp_path: Path) -> None:
    tests_path = tmp_path / "tests"
    tests_path.mkdir()
    (tests_path / "test_sample.py").write_text(
        "class TestThing:\n"
        "    def test_method(self):\n"
        "        pass\n\n"
        "def test_plain():\n"
        "    pass\n",
        encoding="utf-8",
    )
    discovered = {"sample:present", "sample:missing"}
    manifest = {
        "sample:present": "tests/test_sample.py::TestThing::test_method",
        "sample:stale": "tests/test_sample.py::not_present",
    }

    errors = validate_manifest(tmp_path, manifest, discovered)

    assert errors == [
        "missing callables: sample:missing",
        "stale callables: sample:stale",
        (
            "invalid test node ids: "
            "sample:stale -> tests/test_sample.py::not_present"
        ),
    ]


def test_accepts_parameterized_test_node_id(tmp_path: Path) -> None:
    tests_path = tmp_path / "tests"
    tests_path.mkdir()
    (tests_path / "test_sample.py").write_text(
        "def test_value():\n    pass\n", encoding="utf-8"
    )
    discovered = {"sample:value"}
    manifest = {
        "sample:value": "tests/test_sample.py::test_value[case]",
    }

    assert validate_manifest(tmp_path, manifest, discovered) == []


def test_rejects_malformed_and_missing_test_node_ids(tmp_path: Path) -> None:
    discovered = {"sample:malformed", "sample:missing"}
    manifest = {
        "sample:malformed": "not-a-node-id",
        "sample:missing": "tests/test_missing.py::test_value",
    }

    assert validate_manifest(tmp_path, manifest, discovered) == [
        (
            "invalid test node ids: sample:malformed -> not-a-node-id, "
            "sample:missing -> tests/test_missing.py::test_value"
        )
    ]


def test_repository_manifest_is_complete() -> None:
    discovered = discover_public_callables(ROOT, SCOPE_PATH)

    assert validate_manifest(ROOT, FUNCTION_TEST_MANIFEST, discovered) == []
