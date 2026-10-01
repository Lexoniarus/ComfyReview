"""Presentation contracts for migrated Frontend V2 shells."""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.arena_router import router as arena_router
from routers.index_router import router as review_router
from routers.playground.generator import router as playground_generator_router
from routers.top_router import router as top_router
from templates import ARENA_HTML, INDEX_HTML, TOP_PICTURES_HTML


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


def test_arena_template_and_url_use_uid_based_v2_controls() -> None:
    rendered = ARENA_HTML.render()
    application = FastAPI()
    application.include_router(arena_router)

    response = TestClient(application).get("/arena?scope=character-a")

    assert response.status_code == 200
    assert 'data-v2-surface="arena"' in rendered
    assert "/static/js/entries/arena.js" in rendered
    assert "left_image_uid" not in rendered
    assert "<style" not in rendered
    assert "onclick=" not in rendered
    assert 'data-v2-surface="arena"' in response.text


def test_playground_generator_url_renders_the_canonical_v2_shell() -> None:
    application = FastAPI()
    application.include_router(playground_generator_router)

    response = TestClient(application).get("/playground/generator")

    assert response.status_code == 200
    assert 'data-v2-surface="playground"' in response.text
    assert "/static/js/entries/playground.js" in response.text
    assert "/static/css/v2/playground.css" in response.text
    assert "/api/v2" not in response.text
    assert "inline" not in response.text.casefold()
