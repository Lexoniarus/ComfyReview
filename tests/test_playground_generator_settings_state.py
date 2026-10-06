"""Behavior tests for persistent V2 Playground generator settings."""

from __future__ import annotations

from collections.abc import Mapping

from services.playground_generator_ui.settings_state import (
    PlaygroundGeneratorSettingsService,
)


class _StateRepository:
    def __init__(self, head: Mapping[str, object] | None = None) -> None:
        self.head = dict(head or {})

    def load_head(self) -> dict[str, object]:
        return dict(self.head)

    def save_head(self, state: Mapping[str, object]) -> None:
        self.head = dict(state)

    def load_preview(self) -> list[dict[str, object]]:
        return []

    def save_preview(self, drafts) -> None:
        del drafts

    def clear_preview(self) -> None:
        return None


def test_generator_settings_migrate_legacy_render_values() -> None:
    repository = _StateRepository(
        {
            "checkpoint_name": "model.safetensors",
            "sampler_name": "euler",
            "scheduler_name": "normal",
            "comfy_seed": "37-40",
            "steps_min": "28",
            "steps_max": "32",
            "cfg_min": "6.5",
            "cfg_max": "7.5",
            "cfg_step": "0.25",
            "denoise": "0.9",
            "batch_runs": 4,
        }
    )

    settings = PlaygroundGeneratorSettingsService(repository).load()

    assert settings == {
        "selections": [],
        "loras": [],
        "checkpoint": "model.safetensors",
        "sampler": "euler",
        "scheduler": "normal",
        "seed_mode": "fixed",
        "seed": 37,
        "steps_min": 28,
        "steps_max": 32,
        "cfg_min": 6.5,
        "cfg_max": 7.5,
        "cfg_step": 0.25,
        "denoise": 0.9,
        "batch_runs": 4,
        "aspect_format": "1:1",
        "resolution_class": "1080",
    }


def test_generator_settings_round_trip_without_discarding_legacy_state() -> (
    None
):
    repository = _StateRepository({"character_id": "legacy-character"})
    service = PlaygroundGeneratorSettingsService(repository)
    settings = {
        "checkpoint": "model.safetensors",
        "selections": [{"kind": "scene", "mode": "off"}],
    }

    assert service.load() == {}

    service.save(settings)

    assert service.load() == settings
    assert repository.head["character_id"] == "legacy-character"
