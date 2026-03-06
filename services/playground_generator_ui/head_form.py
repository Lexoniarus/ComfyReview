from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import DEFAULT_MAX_TRIES
from services.ui_state_service import load_json_state


def _safe_slug(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-zA-Z0-9_\-]", "", s)
    return s.strip("_")


def workflow_render_defaults(*, character_name: Optional[str] = None, character_id: Optional[int] = None) -> Dict[str, str]:
    """Read render defaults from workflow JSON files.

    Priority
    1) character specific workflow
    2) data/workflows/_default_character.json

    Note
    comfy_seed is intentionally not read from the workflow.
    """

    defaults: Dict[str, str] = {
        "checkpoint_name": "",
        "sampler_name": "",
        "scheduler_name": "",
        "steps": "",
        "cfg": "",
        "denoise": "",
    }

    wf_candidates: List[Path] = []
    if character_name:
        slug = _safe_slug(character_name)
        if slug:
            wf_candidates.extend(
                [
                    Path(f"data/workflows/{slug}.json"),
                    Path(f"data/workflows/characters/{slug}.json"),
                ]
            )
    if character_id is not None:
        wf_candidates.extend(
            [
                Path(f"data/workflows/{int(character_id)}.json"),
                Path(f"data/workflows/characters/{int(character_id)}.json"),
            ]
        )

    wf_candidates.append(Path("data/workflows/_default_character.json"))

    wf: Dict[str, Any] = {}
    for p in wf_candidates:
        wf = load_json_state(p) or {}
        if wf:
            break

    if not wf:
        return defaults

    for node in wf.values():
        if not isinstance(node, dict):
            continue
        inp = node.get("inputs") or {}
        if isinstance(inp, dict) and "ckpt_name" in inp:
            ck = inp.get("ckpt_name")
            if isinstance(ck, str) and ck.strip():
                defaults["checkpoint_name"] = ck.strip()
                break

    for node in wf.values():
        if not isinstance(node, dict):
            continue
        if node.get("class_type") != "KSampler":
            continue
        inp = node.get("inputs") or {}
        if not isinstance(inp, dict):
            continue

        st = inp.get("steps")
        cg = inp.get("cfg")
        dn = inp.get("denoise")
        smp = inp.get("sampler_name")
        sch = inp.get("scheduler")

        if st is not None:
            defaults["steps"] = str(st)
        if cg is not None:
            defaults["cfg"] = str(cg)
        if dn is not None:
            defaults["denoise"] = str(dn)

        if isinstance(smp, str) and smp.strip():
            defaults["sampler_name"] = smp.strip()
        if isinstance(sch, str) and sch.strip():
            defaults["scheduler_name"] = sch.strip()
        break

    return defaults


def character_name_from_id(characters: List[Dict[str, Any]], character_id: Optional[int]) -> str:
    if character_id is None:
        return ""
    for c in characters:
        try:
            if int(c.get("id")) == int(character_id):
                return str(c.get("name") or c.get("key") or "").strip()
        except Exception:
            continue
    return ""


def build_form_from_state(*, saved: Dict[str, Any], defaults: Dict[str, str]) -> Dict[str, Any]:
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
        "checkpoint_name": str(saved.get("checkpoint_name", defaults.get("checkpoint_name", ""))),
        "sampler_name": str(saved.get("sampler_name", defaults.get("sampler_name", ""))),
        "scheduler_name": str(saved.get("scheduler_name", defaults.get("scheduler_name", ""))),
        "steps_min": str(saved.get("steps_min", defaults.get("steps", ""))),
        "steps_max": str(saved.get("steps_max", defaults.get("steps", ""))),
        "cfg_min": str(saved.get("cfg_min", defaults.get("cfg", ""))),
        "cfg_max": str(saved.get("cfg_max", defaults.get("cfg", ""))),
        "cfg_step": str(saved.get("cfg_step", "0.1")),
        "steps": str(saved.get("steps", defaults.get("steps", ""))),
        "cfg": str(saved.get("cfg", defaults.get("cfg", ""))),
        "denoise": str(saved.get("denoise", defaults.get("denoise", ""))),
    }


def build_head_state_from_post(
    *,
    character_id: Optional[int],
    scene_id: Optional[int],
    outfit_id: Optional[int],
    pose_id: Optional[int],
    expression_id: Optional[int],
    lighting_id: Optional[int],
    modifier_id: Optional[int],
    include_lighting: Optional[int],
    include_modifier: Optional[int],
    gen_seed: Optional[str],
    comfy_seed: Optional[str],
    max_tries: int,
    batch_runs: Optional[int],
    checkpoint_name: Optional[str],
    sampler_name: Optional[str],
    scheduler_name: Optional[str],
    steps_min: Optional[str],
    steps_max: Optional[str],
    cfg_min: Optional[str],
    cfg_max: Optional[str],
    cfg_step: Optional[str],
    steps: Optional[str],
    cfg: Optional[str],
    denoise: Optional[str],
) -> Dict[str, Any]:
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
