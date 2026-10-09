"""Regression contract for ComfyReview documentation authority and links."""

from scripts.check_documentation import find_documentation_issues


def test_active_documentation_links_and_archive_boundaries() -> None:
    """Keep navigable documents live and discarded Chronicle sources isolated."""
    assert find_documentation_issues() == []
