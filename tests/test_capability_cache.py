"""Tests for the ComfyUI capability cache adapter."""

from __future__ import annotations

from pathlib import Path

from comfyreview.repositories.filesystem import JsonComfyUiCapabilityCache


def test_capability_cache_round_trips_mapping(tmp_path: Path) -> None:
    cache = JsonComfyUiCapabilityCache(tmp_path / "state" / "cache.json")

    assert cache.load() == {}
    cache.save({"samplers": ["euler"]})

    assert cache.load() == {"samplers": ["euler"]}


def test_capability_cache_rejects_invalid_or_non_object_json(
    tmp_path: Path,
) -> None:
    path = tmp_path / "cache.json"
    cache = JsonComfyUiCapabilityCache(path)

    path.write_text("invalid", encoding="utf-8")
    assert cache.load() == {}
    path.write_text("[]", encoding="utf-8")
    assert cache.load() == {}
