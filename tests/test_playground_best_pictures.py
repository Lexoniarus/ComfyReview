"""Behavior tests for canonical Playground best-picture lookup."""

from __future__ import annotations

from pathlib import Path
from typing import cast

from comfyreview.application import AnalyticsService, PromptMatchPreview
from services.playground_generator_ui.best_pictures import (
    resolve_best_picture_for_draft,
)


class _Analytics:
    def __init__(
        self,
        result: PromptMatchPreview | None = None,
        error: Exception | None = None,
    ) -> None:
        self.result = result
        self.error = error
        self.calls: list[tuple[tuple[str, ...], dict[str, object]]] = []

    def best_prompt_match(self, tokens, **values):
        self.calls.append((tokens, values))
        if self.error is not None:
            raise self.error
        return self.result


def _resolve(
    analytics: _Analytics,
    draft: dict[str, object],
    *,
    image_url=lambda path: f"/files/{path}",
) -> dict[str, object]:
    return resolve_best_picture_for_draft(
        draft,
        analytics=cast(AnalyticsService, analytics),
        minimum_ratings=3,
        candidate_limit=128,
        image_url=image_url,
    )


def test_best_picture_lookup_uses_scene_atoms_and_canonical_match() -> None:
    analytics = _Analytics(
        PromptMatchPreview(None, Path("image.png"), 2, 8.5, 4)
    )

    result = _resolve(
        analytics,
        {"selection": {"scene": {"pos": " moon, city "}}},
    )

    assert result == {
        "status": "ok",
        "best_img_url": "/files/image.png",
        "best_avg": 8.5,
        "best_runs": 4,
        "best_hits": 2,
        "retry": False,
        "retry_after_ms": 0,
    }
    assert analytics.calls == [
        (
            ("moon", "city"),
            {
                "scope": "pos",
                "minimum_hits": 1,
                "minimum_ratings": 3,
                "candidate_limit": 128,
            },
        )
    ]


def test_best_picture_lookup_reports_skip_pending_and_error() -> None:
    assert _resolve(_Analytics(), {"selection": {}})["status"] == "skip"
    assert (
        _resolve(
            _Analytics(),
            {"selection": {"scene": {"pos": "moon"}}},
        )["status"]
        == "pending"
    )
    missing_url = _resolve(
        _Analytics(PromptMatchPreview(None, Path("missing.png"), 1, None, 0)),
        {"selection": {"scene": {"pos": "moon"}}},
        image_url=lambda _path: "",
    )
    assert missing_url["retry_after_ms"] == 1500
    failed = _resolve(
        _Analytics(error=RuntimeError("unavailable")),
        {"selection": {"scene": {"pos": "moon"}}},
    )
    assert failed["status"] == "error"
    assert failed["error"] == "unavailable"
