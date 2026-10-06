"""Application service for persistent Playground generator settings."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from services.playground_generator_ui.ports import PlaygroundGeneratorState

_V2_STATE_KEY = "generator_v2"


class PlaygroundGeneratorSettingsService:
    """Preserve V2 generator settings alongside the legacy form state."""

    def __init__(self, state: PlaygroundGeneratorState) -> None:
        self._state = state

    def load(self) -> dict[str, Any]:
        """Return the current V2 state or migrate the legacy render values."""
        saved = self._state.load_head()
        current = saved.get(_V2_STATE_KEY)
        if isinstance(current, Mapping):
            return dict(current)
        return _legacy_state(saved)

    def save(self, settings: Mapping[str, object]) -> None:
        """Replace the V2 snapshot without discarding legacy state."""
        saved = self._state.load_head()
        saved[_V2_STATE_KEY] = dict(settings)
        self._state.save_head(saved)


def _legacy_state(saved: Mapping[str, Any]) -> dict[str, Any]:
    if not any(
        key in saved
        for key in (
            "checkpoint_name",
            "sampler_name",
            "scheduler_name",
            "steps_min",
            "cfg_min",
            "denoise",
        )
    ):
        return {}
    seed = _first_integer(saved.get("comfy_seed"), 1)
    return {
        "selections": [],
        "loras": [],
        "checkpoint": str(saved.get("checkpoint_name") or ""),
        "sampler": str(saved.get("sampler_name") or ""),
        "scheduler": str(saved.get("scheduler_name") or ""),
        "seed_mode": "fixed"
        if _has_seed(saved.get("comfy_seed"))
        else "random",
        "seed": seed,
        "steps_min": _number(saved.get("steps_min"), 24, integer=True),
        "steps_max": _number(
            saved.get("steps_max", saved.get("steps_min")), 24, integer=True
        ),
        "cfg_min": _number(saved.get("cfg_min"), 7.0),
        "cfg_max": _number(saved.get("cfg_max", saved.get("cfg_min")), 7.0),
        "cfg_step": _number(saved.get("cfg_step"), 0.1),
        "denoise": _number(saved.get("denoise"), 1.0),
        "batch_runs": _number(saved.get("batch_runs"), 1, integer=True),
        "aspect_format": "1:1",
        "resolution_class": "1080",
    }


def _has_seed(value: object) -> bool:
    return bool(str(value or "").strip())


def _first_integer(value: object, fallback: int) -> int:
    candidate = (
        str(value or "").split(",", maxsplit=1)[0].split("-", maxsplit=1)[0]
    )
    return int(_number(candidate, fallback, integer=True))


def _number(
    value: object, fallback: int | float, *, integer: bool = False
) -> int | float:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return fallback
    return int(number) if integer else number
