"""Presentation contracts for migrated Frontend V2 shells."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.index_router import router as review_router
from routers.top_router import router as top_router
from templates import INDEX_HTML, TOP_PICTURES_HTML


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
    application.include_router(top_router)

    response = TestClient(application).get(
        "/top_pictures?mode=worst&scope=character-a"
    )

    assert response.status_code == 200
    assert 'data-v2-surface="top-worst"' in response.text
    assert "/static/css/v2/image-surfaces.css" in response.text


def test_review_template_and_url_use_the_v2_api_surface() -> None:
    rendered = INDEX_HTML.render()
    application = FastAPI()
    application.include_router(review_router)

    response = TestClient(application).get("/?scope=character-a")

    assert response.status_code == 200
    assert 'data-v2-surface="review"' in rendered
    assert "/static/js/entries/review.js" in rendered
    assert "/api/v2" not in rendered
    assert "<style" not in rendered
    assert "onclick=" not in rendered
    assert 'data-v2-surface="review"' in response.text
