"""Presentation contracts for migrated Frontend V2 shells."""

import re
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from routers.arena_router import router as arena_router
from routers.index_router import router as review_router
from routers.playground.browse import router as playground_catalog_router
from routers.playground.generator import router as playground_generator_router
from routers.stats_router import router as analytics_router
from routers.top_router import router as top_router
from templates import ARENA_HTML, INDEX_HTML, TOP_PICTURES_HTML

ROOT = Path(__file__).resolve().parents[1]


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
    legacy_post = TestClient(application).post("/playground/generator")
    legacy_preview = TestClient(application).get(
        "/playground/generator/preview_draft_best",
        params={"draft_id": "legacy"},
    )

    assert response.status_code == 200
    assert 'data-v2-surface="playground"' in response.text
    assert "/static/js/entries/playground.js" in response.text
    assert "/static/css/v2/playground.css" in response.text
    assert "data-playground-workspace" in response.text
    assert 'data-workspace-step="setup"' in response.text
    assert 'data-workspace-step="variants"' in response.text
    assert "data-variant-board" in response.text
    assert "data-variant-inspector" in response.text
    assert "Varianten vorbereiten" in response.text
    assert "Auswahl generieren" in response.text
    assert "/api/v2" not in response.text
    assert "<style" not in response.text
    assert "onclick=" not in response.text
    assert "inline" not in response.text.casefold()
    assert legacy_post.status_code == 405
    assert legacy_preview.status_code == 404


def test_catalog_url_renders_the_revisioned_v2_shell() -> None:
    application = FastAPI()
    application.include_router(playground_catalog_router)

    response = TestClient(application).get("/playground/browse")

    assert response.status_code == 200
    assert 'data-v2-surface="catalog"' in response.text
    assert "/static/js/entries/catalog.js" in response.text
    assert "/static/css/v2/catalog.css" in response.text
    assert "/api/v2" not in response.text
    assert "<style" not in response.text


def test_all_analytics_urls_render_one_canonical_v2_shell() -> None:
    application = FastAPI()
    application.include_router(analytics_router)

    expected_sections = {
        "/recommendations": "overview",
        "/prompt_tokens": "scopes",
        "/param_stats": "parameters",
        "/stats": "combinations",
    }
    for path, section in expected_sections.items():
        response = TestClient(application).get(path)
        assert response.status_code == 200
        assert 'data-v2-surface="analytics"' in response.text
        assert f'data-section="{section}"' in response.text
        assert "/static/js/entries/analytics.js" in response.text
        assert "<style" not in response.text


def test_only_external_asset_v2_templates_remain() -> None:
    templates = sorted((ROOT / "templates").glob("*.html"))

    assert {path.name for path in templates} == {
        "_v2_base.html",
        "analytics.html",
        "arena.html",
        "generations.html",
        "index.html",
        "playground.html",
        "playground_generator.html",
        "playground_overview.html",
        "settings.html",
        "top_pictures.html",
    }
    for path in templates:
        source = path.read_text(encoding="utf-8")
        assert "<style" not in source
        assert " style=" not in source
        for script_tag in re.findall(r"<script\b[^>]*>", source):
            assert 'type="module"' in script_tag
            assert " src=" in script_tag
