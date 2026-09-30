from __future__ import annotations

from typing import Any

from config import DEFAULT_MAX_TRIES


def character_name_from_id(
    characters: list[dict[str, Any]], character_id: int | None
) -> str:
    if character_id is None:
        return ""
    for c in characters:
        try:
            raw_id = c.get("id")
            if raw_id is not None and int(str(raw_id)) == int(character_id):
                return str(c.get("name") or c.get("key") or "").strip()
        except (TypeError, ValueError):
            continue
    return ""


def build_form_from_state(
    *, saved: dict[str, Any], defaults: dict[str, str]
) -> dict[str, Any]:
    """Build the generator page form model from saved state and workflow defaults."""

    saved = dict(saved or {})
    return {
        "character_id": str(saved.get("character_id", "")),
        "scene_id": str(saved.get("scene_id", "")),
        "outfit_id": str(saved.get("outfit_id", "")),
        "pose_id": str(saved.get("pose_id", "")),
        "expression_id": str(saved.get("expression_id", "")),
        "lighting_id": str(saved.get("lighting_id", "")),
        "modifier_id": str(saved.get("modifier_id", "")),
        "include_lighting": bool(saved.get("include_lighting", True)),
        "include_modifier": bool(saved.get("include_modifier", True)),
        "gen_seed": str(saved.get("gen_seed", "")),
        "comfy_seed": str(saved.get("comfy_seed", "")),
        "max_tries": int(saved.get("max_tries", DEFAULT_MAX_TRIES)),
        "batch_runs": str(saved.get("batch_runs", "")),
        "checkpoint_name": str(
            saved.get("checkpoint_name", defaults.get("checkpoint_name", ""))
        ),
        "sampler_name": str(
            saved.get("sampler_name", defaults.get("sampler_name", ""))
        ),
        "scheduler_name": str(
            saved.get("scheduler_name", defaults.get("scheduler_name", ""))
        ),
        "steps_min": str(
            saved.get(
                "steps_min", saved.get("steps", defaults.get("steps", ""))
            )
        ),
        "steps_max": str(
            saved.get(
                "steps_max", saved.get("steps", defaults.get("steps", ""))
            )
        ),
        "cfg_min": str(
            saved.get("cfg_min", saved.get("cfg", defaults.get("cfg", "")))
        ),
        "cfg_max": str(
            saved.get("cfg_max", saved.get("cfg", defaults.get("cfg", "")))
        ),
        "cfg_step": str(saved.get("cfg_step", "0.1")),
        "steps": str(saved.get("steps", defaults.get("steps", ""))),
        "cfg": str(saved.get("cfg", defaults.get("cfg", ""))),
        "denoise": str(saved.get("denoise", defaults.get("denoise", ""))),
    }


def build_head_state_from_post(
    *,
    character_id: int | None,
    scene_id: int | None,
    outfit_id: int | None,
    pose_id: int | None,
    expression_id: int | None,
    lighting_id: int | None,
    modifier_id: int | None,
    include_lighting: int | None,
    include_modifier: int | None,
    gen_seed: str | None,
    comfy_seed: str | None,
    max_tries: int,
    batch_runs: int | None,
    checkpoint_name: str | None,
    sampler_name: str | None,
    scheduler_name: str | None,
    steps_min: str | None,
    steps_max: str | None,
    cfg_min: str | None,
    cfg_max: str | None,
    cfg_step: str | None,
    steps: str | None,
    cfg: str | None,
    denoise: str | None,
) -> dict[str, Any]:
    """Persistable head state, used for the generator page."""

    return {
        "character_id": str(character_id or ""),
        "scene_id": str(scene_id or ""),
        "outfit_id": str(outfit_id or ""),
        "pose_id": str(pose_id or ""),
        "expression_id": str(expression_id or ""),
        "lighting_id": str(lighting_id or ""),
        "modifier_id": str(modifier_id or ""),
        "include_lighting": bool(int(include_lighting or 0)),
        "include_modifier": bool(int(include_modifier or 0)),
        "gen_seed": gen_seed or "",
        "comfy_seed": comfy_seed or "",
        "max_tries": int(max_tries),
        "batch_runs": batch_runs or "",
        "checkpoint_name": checkpoint_name or "",
        "sampler_name": sampler_name or "",
        "scheduler_name": scheduler_name or "",
        "steps_min": steps_min or "",
        "steps_max": steps_max or "",
        "cfg_min": cfg_min or "",
        "cfg_max": cfg_max or "",
        "cfg_step": cfg_step or "",
        "steps": steps or "",
        "cfg": cfg or "",
        "denoise": denoise or "",
    }
