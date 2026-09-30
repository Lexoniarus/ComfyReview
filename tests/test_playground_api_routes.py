"""Contracts for Playground JSON routes using canonical catalog identities."""

from __future__ import annotations

import importlib
import json
from types import SimpleNamespace

from starlette.requests import Request

api = importlib.import_module("routers.playground.api")


class _Views:
    def prompt_tokens(self, uid: str, *, scope: str) -> list[str]:
        if uid == "missing":
            raise KeyError(uid)
        if scope not in {"pos", "neg"}:
            raise ValueError(scope)
        return ["moon", "city"]


def _request() -> Request:
    container = SimpleNamespace(prompt_catalog_views=_Views())
    application = SimpleNamespace(state=SimpleNamespace(container=container))
    return Request({"type": "http", "app": application})


def _json(response) -> object:
    return json.loads(response.body.decode("utf-8"))


def test_token_statistics_validates_payload_and_delegates(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fetch_stats(_path: object, **values: object) -> dict[str, object]:
        calls.append(values)
        return {"moon": {"n": 1}}

    monkeypatch.setattr(
        api,
        "fetch_token_stats_for_tokens",
        fetch_stats,
    )

    invalid = api.playground_token_stats({"tokens": "moon"})
    response = api.playground_token_stats(
        {"tokens": ["moon"], "scope": "neg", "model_branch": "sdxl"}
    )

    assert invalid.status_code == 400
    assert _json(response) == {"ok": True, "stats": {"moon": {"n": 1}}}
    assert calls == [
        {"tokens": ["moon"], "scope": "neg", "model_branch": "sdxl"}
    ]


def test_preview_route_resolves_stable_uids_and_maps_urls(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fetch_preview(**values: object) -> dict[str, object]:
        calls.append(values)
        return {"png_path": "output/image.png", "hits": 2}

    monkeypatch.setattr(
        api,
        "fetch_best_match_preview",
        fetch_preview,
    )
    monkeypatch.setattr(
        api,
        "existing_png_path_to_url",
        lambda path: f"/files/{path}",
    )

    response = api.playground_api_previews(
        _request(),
        {
            "item_ids": ["component-a", "missing"],
            "scope": "pos",
            "min_hits": "bad",
            "min_runs": -2,
        },
    )

    assert _json(response) == {
        "component-a": {
            "png_path": "output/image.png",
            "hits": 2,
            "url": "/files/output/image.png",
        },
        "missing": None,
    }
    assert calls[0]["tokens"] == ["moon", "city"]
    assert calls[0]["min_hits"] == 1
    assert calls[0]["min_runs"] == 0


def test_preview_route_rejects_non_list_ids_and_missing_files(
    monkeypatch,
) -> None:
    invalid = api.playground_api_previews(
        _request(),
        {"item_ids": "component-a"},
    )
    monkeypatch.setattr(
        api,
        "fetch_best_match_preview",
        lambda **_values: {"png_path": "missing.png"},
    )
    monkeypatch.setattr(api, "existing_png_path_to_url", lambda _path: None)
    missing = api.playground_api_previews(
        _request(),
        {"item_ids": ["component-a"]},
    )

    assert invalid.status_code == 400
    assert _json(missing) == {"component-a": None}
