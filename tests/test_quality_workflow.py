"""Regression tests for the shared GitHub Actions quality workflow."""

from __future__ import annotations

from pathlib import Path

WORKFLOW_PATH = Path(".github/workflows/quality.yml")


def test_quality_workflow_avoids_duplicate_feature_branch_runs() -> None:
    """Run feature commits through PR CI and direct pushes on stable branches."""
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert (
        "push:\n"
        "    branches:\n"
        "      - master\n"
        "      - refactor/review-boundary\n"
        "  pull_request:\n"
    ) in workflow
    assert (
        "concurrency:\n"
        "  group: quality-${{ github.event.pull_request.number || github.ref }}\n"
        "  cancel-in-progress: true\n"
    ) in workflow
