"""Route contracts for canonical Playground catalog mutations."""

from __future__ import annotations

import importlib
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from comfyreview.application import PromptCatalogValidationError

browse = importlib.import_module("routers.playground.browse")
hub = importlib.import_module("routers.playground.hub")


class _CatalogViews:
    def __init__(self, error: Exception | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    def list_items(self, *, kind: str, query: str):
        self.calls.append(("list", kind, query))
        return [
            {
                "id": "scene-a",
                "kind": "scene",
                "name": "Moon",
                "key": "moon",
                "tags": "night",
                "pos": "moon",
                "neg": "sun",
                "notes": "",
                "archived": False,
            }
        ]

    def create(self, **values: object):
        self.calls.append(("create", values))
        return self._result()

    def update(self, **values: object):
        self.calls.append(("update", values))
        return self._result()

    def set_archived(self, uid: str, *, archived: bool):
        self.calls.append(("archive", uid, archived))
        return self._result()

    def _result(self):
        if self.error is not None:
            raise self.error
        return SimpleNamespace(component_uid="scene-a")


def _request(views: _CatalogViews) -> Request:
    container = SimpleNamespace(prompt_catalog_views=views)
    application = SimpleNamespace(state=SimpleNamespace(container=container))
    return Request({"type": "http", "app": application})


def test_playground_catalog_browse_and_create_urls_render_v2_shell() -> None:
    views = _CatalogViews()
    response = browse.playground_browse(
        _request(views),
        kind="scene",
        q="moon",
    )
    create_response = browse.playground_create_page(
        _request(views),
        kind="pose",
    )

    assert response.template.name == "playground.html"
    assert create_response.template.name == "playground.html"
    assert set(response.context) == {"request"}
    assert set(create_response.context) == {"request"}
    assert views.calls == []


def test_playground_home_renders_canonical_generation_shell() -> None:
    response = hub.playground_home(_request(_CatalogViews()))

    assert response.template.name == "generations.html"
    assert set(response.context) == {"request"}


def test_playground_catalog_mutations_use_uids_and_compatible_redirects() -> (
    None
):
    views = _CatalogViews()
    request = _request(views)

    create_response = browse.playground_create(
        request,
        kind="scene",
        name="Moon",
        tags="night",
        pos="moon",
        neg="sun",
        notes="note",
    )
    update_response = browse.playground_update(
        request,
        item_id="scene-a",
        kind="scene",
        name="Moon 2",
        tags="night,blue",
        pos="blue moon",
        neg="sun",
        notes="note 2",
    )
    archive_response = browse.playground_delete(
        request,
        item_id="scene-a",
        kind="scene",
    )
    restore_response = browse.playground_restore(
        request,
        item_id="scene-a",
        kind="scene",
    )

    for response in (
        create_response,
        update_response,
        archive_response,
        restore_response,
    ):
        assert response.status_code == 303
        assert response.headers["location"] == "/playground/browse?kind=scene"
    assert views.calls[2] == ("archive", "scene-a", True)
    assert views.calls[3] == ("archive", "scene-a", False)


@pytest.mark.parametrize(
    ("error", "status"),
    (
        (PromptCatalogValidationError("invalid prompt"), 400),
        (KeyError("Unknown prompt component: scene-a"), 404),
    ),
)
def test_playground_catalog_routes_map_application_errors(
    error: Exception,
    status: int,
) -> None:
    with pytest.raises(HTTPException) as caught:
        browse.playground_delete(
            _request(_CatalogViews(error)),
            item_id="scene-a",
            kind="scene",
        )

    assert caught.value.status_code == status
