from __future__ import annotations

"""POST parsing helpers for the generator router.

We keep parsing/normalization in one place so the action handlers remain small.
"""

from typing import Any, Dict


def head_kwargs_from_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Extract kwargs accepted by ``build_head_state_from_post``."""

    keys = [
        "character_id",
        "scene_id",
        "outfit_id",
        "pose_id",
        "expression_id",
        "lighting_id",
        "modifier_id",
        "include_lighting",
        "include_modifier",
        "gen_seed",
        "comfy_seed",
        "max_tries",
        "batch_runs",
        "checkpoint_name",
        "sampler_name",
        "scheduler_name",
        "steps_min",
        "steps_max",
        "cfg_min",
        "cfg_max",
        "cfg_step",
        "steps",
        "cfg",
        "denoise",
    ]

    return {k: post.get(k) for k in keys}


def draft_update_kwargs_from_post(post: Dict[str, Any]) -> Dict[str, Any]:
    """Extract draft update kwargs accepted by ``update_draft``."""

    return {
        "draft_id": str(post.get("draft_id") or "").strip(),
        "seed": post.get("draft_seed"),
        "steps": post.get("draft_steps"),
        "cfg": post.get("draft_cfg"),
        "sampler": post.get("draft_sampler"),
        "scheduler": post.get("draft_scheduler"),
        "denoise": post.get("draft_denoise"),
        "checkpoint": post.get("draft_checkpoint"),
        "pos": post.get("draft_pos"),
        "neg": post.get("draft_neg"),
    }
