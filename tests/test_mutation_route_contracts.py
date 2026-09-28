import importlib
from pathlib import Path

import pytest
from fastapi import HTTPException

from models import RatedItem
from services.arena_service import ArenaMutationError, ArenaValidationError


arena_router = importlib.import_module("routers.arena_router")
index_router = importlib.import_module("routers.index_router")
top_router = importlib.import_module("routers.top_router")


def _review_form(png_path: Path, json_path: Path, *, rating: int = 5) -> dict:
    return {
        "rating": str(rating),
        "combo_key": "combo",
        "model_branch": "model",
        "checkpoint": "checkpoint",
        "json_path": str(json_path),
        "png_path": str(png_path),
    }


def _call_review(form: dict):
    return index_router.rate(
        rating=int(form["rating"]),
        deleted=None,
        delete=None,
        combo_key=form["combo_key"],
        model_branch=form["model_branch"],
        checkpoint=form["checkpoint"],
        json_path=form["json_path"],
        png_path=form["png_path"],
        sampler=None,
        scheduler=None,
        steps=None,
        cfg=None,
        denoise=None,
        loras_json=None,
        filter_unrated=None,
        filter_model=None,
        filter_subdir=None,
        filter_scope=None,
        filter_character=None,
        filter_set_key=None,
    )


def test_review_route_returns_400_for_invalid_score(tmp_path, monkeypatch):
    monkeypatch.setattr(index_router, "OUTPUT_ROOT", tmp_path)
    with pytest.raises(HTTPException) as caught:
        _call_review(
            _review_form(tmp_path / "image.png", tmp_path / "image.json", rating=11)
        )

    assert caught.value.status_code == 400
    assert caught.value.detail == "rating must be between 1 and 10"


def test_review_route_returns_400_for_path_outside_output_root(tmp_path, monkeypatch):
    output_root = tmp_path / "output"
    output_root.mkdir()
    outside_png = tmp_path / "image.png"
    outside_json = tmp_path / "image.json"
    outside_png.write_bytes(b"png")
    outside_json.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(index_router, "OUTPUT_ROOT", output_root)

    with pytest.raises(HTTPException) as caught:
        _call_review(_review_form(outside_png, outside_json))

    assert caught.value.status_code == 400


def test_review_route_returns_404_for_missing_output_pair(tmp_path, monkeypatch):
    monkeypatch.setattr(index_router, "OUTPUT_ROOT", tmp_path)
    with pytest.raises(HTTPException) as caught:
        _call_review(_review_form(tmp_path / "image.png", tmp_path / "image.json"))

    assert caught.value.status_code == 404


def test_curation_route_returns_400_for_unknown_set(tmp_path, monkeypatch):
    output_root = tmp_path / "output"
    output_root.mkdir()
    png_path = output_root / "image.png"
    json_path = output_root / "image.json"
    png_path.write_bytes(b"png")
    json_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(top_router, "OUTPUT_ROOT", output_root)
    monkeypatch.setattr(top_router, "CURATION_SET_KEYS", ("scene",))
    monkeypatch.setattr(top_router, "CURATION_DB_PATH", tmp_path / "curation.sqlite3")

    with pytest.raises(HTTPException) as caught:
        top_router.assign_set(
            png_path=str(png_path),
            json_path=str(json_path),
            set_key="unknown",
            model="",
            mode="top",
            subdir="",
            view_set_key="",
        )

    assert caught.value.status_code == 400


def test_arena_route_maps_validation_and_mutation_errors(monkeypatch, tmp_path):
    left = RatedItem(tmp_path / "left.png", tmp_path / "left.json", "", "", "", "", {})
    right = RatedItem(tmp_path / "right.png", tmp_path / "right.json", "", "", "", "", {})
    monkeypatch.setattr(arena_router, "ensure_arena_schema", lambda _path: None)
    monkeypatch.setattr(arena_router, "scan_output", lambda _root: [left, right])
    monkeypatch.setattr(
        arena_router,
        "insert_arena_result",
        lambda *_args: (_ for _ in ()).throw(ArenaValidationError("invalid")),
    )
    with pytest.raises(HTTPException) as caught:
        arena_router.arena_result(
            winner_side="invalid",
            left_json=str(left.json_path),
            right_json=str(right.json_path),
            model="",
            subdir="",
            mode="top",
            set_key="",
        )
    assert caught.value.status_code == 400

    monkeypatch.setattr(
        arena_router,
        "insert_arena_result",
        lambda *_args: (_ for _ in ()).throw(ArenaMutationError("failed")),
    )
    with pytest.raises(HTTPException) as caught:
        arena_router.arena_result(
            winner_side="left",
            left_json=str(left.json_path),
            right_json=str(right.json_path),
            model="",
            subdir="",
            mode="top",
            set_key="",
        )
    assert caught.value.status_code == 500
