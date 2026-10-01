"""Presentation contracts for migrated Frontend V2 shells."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.top_router import router
from templates import TOP_PICTURES_HTML


def test_top_worst_template_is_a_script_free_jinja_shell() -> None:
    rendered = TOP_PICTURES_HTML.render()

    assert 'lang="de"' in rendered
    assert "Prüfen" in rendered
    assert "Top / Worst" in rendered
    assert "Unklassifiziert" not in rendered
    assert 'data-v2-surface="top-worst"' in rendered
    assert (
        '<script type="module" src="/static/js/entries/top-worst.js">'
        in rendered
    )
    assert "<style" not in rendered
    assert "onclick=" not in rendered


def test_top_pictures_url_renders_the_v2_reference_surface() -> None:
    application = FastAPI()
    application.include_router(router)

    response = TestClient(application).get(
        "/top_pictures?mode=worst&scope=character-a"
    )

    assert response.status_code == 200
    assert 'data-v2-surface="top-worst"' in response.text
    assert "/static/css/v2/top-worst.css" in response.text
