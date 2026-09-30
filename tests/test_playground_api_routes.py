"""Contracts for Playground JSON routes using canonical catalog identities."""

from __future__ import annotations

import importlib
import json
from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request

from comfyreview.application import PromptMatchPreview, PromptTokenStatistic

api = importlib.import_module("routers.playground.api")


class _Views:
    def prompt_tokens(self, uid: str, *, scope: str) -> list[str]:
        if uid == "missing":
            raise KeyError(uid)
        if scope not in {"pos", "neg"}:
            raise ValueError(scope)
        return ["moon", "city"]


class _Analytics:
    def __init__(self, match: PromptMatchPreview | None = None) -> None:
        self.match = match
        self.calls: list[
            tuple[str, tuple[tuple[str, ...], dict[str, object]]]
        ] = []

    def token_statistics_for(
        self,
        tokens: tuple[str, ...],
        **values: object,
    ) -> dict[str, PromptTokenStatistic]:
        self.calls.append(("statistics", (tokens, values)))
        return {tokens[0]: PromptTokenStatistic(tokens[0], 1, 8.0, 7.0)}

    def best_prompt_match(
        self,
        tokens: tuple[str, ...],
        **values: object,
    ) -> PromptMatchPreview | None:
        self.calls.append(("match", (tokens, values)))
        return self.match


def _request(analytics: _Analytics | None = None) -> Request:
    container = SimpleNamespace(
        prompt_catalog_views=_Views(),
        analytics_service=analytics or _Analytics(),
        settings=SimpleNamespace(minimum_runs=3, pool_limit=128),
    )
    application = SimpleNamespace(state=SimpleNamespace(container=container))
    return Request({"type": "http", "app": application})


def _json(response) -> object:
    return json.loads(response.body.decode("utf-8"))


def test_token_statistics_validates_payload_and_delegates() -> None:
    analytics = _Analytics()
    request = _request(analytics)

    invalid = api.playground_token_stats(request, {"tokens": "moon"})
    response = api.playground_token_stats(
        request, {"tokens": ["moon"], "scope": "neg", "model_branch": "sdxl"}
    )

    assert invalid.status_code == 400
    assert _json(response) == {
        "ok": True,
        "stats": {"moon": {"n": 1, "mean": 8.0, "lb05": 7.0}},
    }
    assert analytics.calls == [
        (
            "statistics",
            (("moon",), {"scope": "neg", "model_branch": "sdxl"}),
        )
    ]


def test_preview_route_resolves_stable_uids_and_maps_urls(monkeypatch) -> None:
    analytics = _Analytics(
        PromptMatchPreview(
            Path("output/image.json"),
            Path("output/image.png"),
            2,
            8.0,
            4,
        )
    )
    monkeypatch.setattr(
        api,
        "existing_png_path_to_url",
        lambda path: f"/files/{path.replace(chr(92), '/')}",
    )

    response = api.playground_api_previews(
        _request(analytics),
        {
            "item_ids": ["component-a", "missing"],
            "scope": "pos",
            "min_hits": "bad",
            "min_runs": -2,
        },
    )

    assert _json(response) == {
        "component-a": {
            "png_path": str(Path("output/image.png")),
            "json_path": str(Path("output/image.json")),
            "hits": 2,
            "avg_rating": 8.0,
            "runs": 4,
            "url": "/files/output/image.png",
        },
        "missing": None,
    }
    _, (tokens, options) = analytics.calls[0]
    assert tokens == ("moon", "city")
    assert options["minimum_hits"] == 1
    assert options["minimum_ratings"] == 0


def test_preview_route_rejects_non_list_ids_and_missing_files(
    monkeypatch,
) -> None:
    invalid = api.playground_api_previews(
        _request(),
        {"item_ids": "component-a"},
    )
    analytics = _Analytics(
        PromptMatchPreview(None, Path("missing.png"), 1, None, 0)
    )
    monkeypatch.setattr(api, "existing_png_path_to_url", lambda _path: None)
    missing = api.playground_api_previews(
        _request(analytics),
        {"item_ids": ["component-a"]},
    )

    assert invalid.status_code == 400
    assert _json(missing) == {"component-a": None}
