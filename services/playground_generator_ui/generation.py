from __future__ import annotations

import math
import random
import time
from typing import Any

from comfyreview.application import (
    ManualPromptSelection,
    PlaygroundDraft,
    PlaygroundService,
    PromptSelectionCommand,
)
from services.playground_common.empty_placeholders import filter_random_items
from services.ui_state_service import safe_int

from .types import DiscoveryLists


def _split_csv(val: str | None) -> list[str]:
    if val is None:
        return []
    s = str(val).strip()
    if not s:
        return []
    return [p.strip() for p in s.split(",") if p.strip()]


def parse_sequence(spec: str | None, *, cast, default_step: float):
    """Parse numeric sequences from user input.

    Supported
    "" -> []
    "1,2,3" -> [1,2,3]
    "37-40" -> [37,38,39,40]
    "4.5-7.0:0.5" -> [4.5,5.0,...,7.0]
    """

    s = str(spec or "").strip()
    if not s:
        return []

    if "-" in s and "," not in s:
        left, right = s.split("-", 1)
        step = None
        if ":" in right:
            right, step_s = right.split(":", 1)
            step = float(step_s.strip())

        a = float(left.strip())
        b = float(right.strip())
        if step is None:
            step = float(default_step)
        if step <= 0:
            raise ValueError("step muss > 0 sein")

        out = []
        x = a
        while x <= b + (step * 0.0001):
            out.append(cast(x))
            x += step
        return out

    parts = [p.strip() for p in s.split(",") if p.strip()]
    return [cast(p) for p in parts]


def _shuffled_cycle(values: list[Any], *, count: int, rng) -> list[Any]:
    """Return length=count list by repeating shuffled copies of values."""
    if not values:
        return []
    if len(values) == 1:
        return [values[0] for _ in range(int(count))]
    out: list[Any] = []
    while len(out) < int(count):
        chunk = list(values)
        rng.shuffle(chunk)
        out.extend(chunk)
    return out[: int(count)]


def _stratified_pick_from_sorted(
    values: list[Any], *, count: int, rng
) -> list[Any]:
    """Pick values in a stratified way from an ordered list."""
    if not values:
        return []
    n = int(count)
    if n <= 1:
        return [rng.choice(values)]
    m = len(values)
    out: list[Any] = []
    for i in range(n):
        lo = int(math.floor(i * m / n))
        hi = int(math.floor((i + 1) * m / n)) - 1
        if hi < lo:
            hi = lo
        pick_idx = rng.randint(lo, hi) if hi >= lo else lo
        out.append(values[pick_idx])
    rng.shuffle(out)
    return out


def _stratified_int_range(a: int, b: int, *, count: int, rng) -> list[int]:
    if a > b:
        a, b = b, a
    # inclusive range
    values = list(range(int(a), int(b) + 1))
    return [
        int(x)
        for x in _stratified_pick_from_sorted(
            values, count=int(count), rng=rng
        )
    ]


def _float_steps(
    a: float, b: float, step: float, *, ndigits: int = 1
) -> list[float]:
    if a > b:
        a, b = b, a
    if step <= 0:
        step = 0.1
    out: list[float] = []
    x = float(a)
    # guard floating drift
    while x <= b + (step * 0.0001):
        out.append(round(float(x), ndigits))
        x += step
    return out


def _resolve_choice(
    *,
    raw_value: str | None,
    cycle: list[str],
    default_value: Any,
    idx: int,
    rng,
) -> str | None:
    parts = _split_csv(raw_value)
    if parts:
        return rng.choice(parts)

    if raw_value is None or str(raw_value).strip() == "":
        if cycle:
            return cycle[idx % len(cycle)]

    dv = str(default_value or "").strip()
    return dv or None


def _pick_random_character_id(characters: list[dict[str, Any]], rng) -> str:
    chars = filter_random_items(list(characters or []))
    if not chars:
        raise ValueError(
            "Keine Characters in der Playground DB gefunden (Empty wird nicht zufaellig genutzt)."
        )
    return str(rng.choice(chars)["id"])


def _subdir_for_character(character_name: str) -> str:
    return f"playground/{character_name.strip().replace(' ', '_')}"


def generate_preview_drafts(
    *,
    head: dict[str, Any],
    characters: list[dict[str, Any]],
    discovery: DiscoveryLists,
    playground_service: PlaygroundService,
    render_defaults: dict[str, Any],
    default_max_attempts: int,
) -> list[dict[str, Any]]:
    """Generate preview drafts based on the head form."""

    spec = _parse_preview_head_spec(head, default_max_attempts)
    rng = _make_rng(spec["gen_seed_base"])
    cycles = _build_discovery_cycles(discovery, rng)

    base_id = int(time.time() * 1000)
    drafts: list[dict[str, Any]] = []

    for idx in range(spec["batch_runs"]):
        run_character_id = _resolve_run_character_id(
            fixed_character_id=spec["fixed_character_id"],
            characters=characters,
            rng=rng,
        )
        character_name, run_defaults, subdir = _load_character_defaults(
            characters=characters,
            character_id=run_character_id,
            render_defaults=render_defaults,
        )

        run_seed, run_steps, run_cfg, run_denoise = _resolve_render_settings(
            idx=idx,
            rng=rng,
            seed_seq=spec["seed_seq"],
            steps_seq=spec["steps_seq"],
            cfg_seq=spec["cfg_seq"],
            denoise_seq=spec["denoise_seq"],
            defaults=run_defaults,
        )

        prompt_draft = _generate_prompt_selection(
            playground_service=playground_service,
            character_id=run_character_id,
            manual_picks=spec["manual_picks"],
            include_lighting=spec["include_lighting"],
            include_modifier=spec["include_modifier"],
            gen_seed_base=spec["gen_seed_base"],
            idx=idx,
            max_tries=spec["max_tries"],
        )
        run_pos, run_neg = _require_prompts(prompt_draft)

        ck, smp, sch = _resolve_render_choices(
            head=head,
            cycles=cycles,
            defaults=run_defaults,
            idx=idx,
            rng=rng,
        )

        drafts.append(
            _build_preview_draft(
                base_id=base_id,
                idx=idx,
                selection=_selection_view(prompt_draft),
                character_name=character_name,
                subdir=subdir,
                seed=run_seed,
                steps=run_steps,
                cfg=run_cfg,
                denoise=run_denoise,
                checkpoint=ck,
                sampler=smp,
                scheduler=sch,
                prompt_positive=run_pos,
                prompt_negative=run_neg,
            )
        )

    return drafts


def _parse_preview_head_spec(
    head: dict[str, Any],
    default_max_attempts: int,
) -> dict[str, Any]:
    character_id = str(head.get("character_id") or "").strip()
    fixed_character_id = character_id or None

    manual_picks = {
        "scene": str(head.get("scene_id") or "").strip() or None,
        "outfit": str(head.get("outfit_id") or "").strip() or None,
        "pose": str(head.get("pose_id") or "").strip() or None,
        "expression": str(head.get("expression_id") or "").strip() or None,
        "lighting": str(head.get("lighting_id") or "").strip() or None,
        "modifier": str(head.get("modifier_id") or "").strip() or None,
    }

    include_lighting = bool(head.get("include_lighting", True))
    include_modifier = bool(head.get("include_modifier", True))

    max_tries = _safe_int_default(
        head.get("max_tries"),
        default_max_attempts,
    )
    batch_runs = max(1, _safe_int_default(head.get("batch_runs"), 1))

    seed_seq = parse_sequence(
        str(head.get("comfy_seed") or ""),
        cast=lambda x: int(float(x)),
        default_step=1,
    )

    # steps/cfg ranges should be stratified and random within the user-defined range.
    # Advanced seq fields are still supported for backwards compatibility but are not required by the UI.
    steps_min = _safe_int_or_none(head.get("steps_min"))
    steps_max = _safe_int_or_none(head.get("steps_max"))
    cfg_min = _safe_float_or_none(head.get("cfg_min"), ndigits=1)
    cfg_max = _safe_float_or_none(head.get("cfg_max"), ndigits=1)
    cfg_step = _safe_float_or_none(head.get("cfg_step"), ndigits=1) or 0.1

    legacy_steps_seq = parse_sequence(
        str(head.get("steps") or ""),
        cast=lambda x: int(float(x)),
        default_step=1,
    )
    legacy_cfg_seq = [
        round(float(x), 1)
        for x in parse_sequence(
            str(head.get("cfg") or ""),
            cast=lambda x: float(x),
            default_step=0.1,
        )
    ]
    denoise_seq = parse_sequence(
        str(head.get("denoise") or ""),
        cast=lambda x: float(x),
        default_step=0.05,
    )

    gen_seed_base = safe_int(str(head.get("gen_seed") or "").strip())

    # Build final per-run sequences for steps/cfg.
    # Priority:
    # 1) min/max range (stratified random)
    # 2) legacy seq (shuffled cycle)
    # 3) empty -> use workflow defaults
    rng = _make_rng(gen_seed_base)

    if steps_min is not None and steps_max is not None:
        steps_seq = _stratified_int_range(
            int(steps_min), int(steps_max), count=int(batch_runs), rng=rng
        )
    elif legacy_steps_seq:
        steps_seq = _shuffled_cycle(
            list(legacy_steps_seq), count=int(batch_runs), rng=rng
        )
    else:
        steps_seq = []

    if cfg_min is not None and cfg_max is not None:
        cfg_values = _float_steps(
            float(cfg_min), float(cfg_max), float(cfg_step), ndigits=1
        )
        cfg_seq = _stratified_pick_from_sorted(
            cfg_values, count=int(batch_runs), rng=rng
        )
    elif legacy_cfg_seq:
        cfg_seq = _shuffled_cycle(
            list(legacy_cfg_seq), count=int(batch_runs), rng=rng
        )
    else:
        cfg_seq = []

    return {
        "fixed_character_id": fixed_character_id,
        "manual_picks": manual_picks,
        "include_lighting": include_lighting,
        "include_modifier": include_modifier,
        "max_tries": int(max_tries),
        "batch_runs": int(batch_runs),
        "seed_seq": seed_seq,
        "steps_seq": steps_seq,
        "cfg_seq": cfg_seq,
        "denoise_seq": denoise_seq,
        "gen_seed_base": gen_seed_base,
    }


def _safe_int_default(value: Any, default: int) -> int:
    try:
        return int(value)
    except Exception:
        try:
            return int(float(str(value).strip()))
        except Exception:
            return int(default)


def _make_rng(gen_seed_base: int | None):
    return (
        random.Random(gen_seed_base) if gen_seed_base is not None else random
    )


def _build_discovery_cycles(
    discovery: DiscoveryLists, rng
) -> dict[str, list[str]]:
    checkpoint_cycle = list(discovery.checkpoints)
    sampler_cycle = list(discovery.samplers)
    scheduler_cycle = list(discovery.schedulers)
    if checkpoint_cycle:
        rng.shuffle(checkpoint_cycle)
    if sampler_cycle:
        rng.shuffle(sampler_cycle)
    if scheduler_cycle:
        rng.shuffle(scheduler_cycle)
    return {
        "checkpoint": checkpoint_cycle,
        "sampler": sampler_cycle,
        "scheduler": scheduler_cycle,
    }


def _resolve_run_character_id(
    *, fixed_character_id: str | None, characters: list[dict[str, Any]], rng
) -> str:
    if fixed_character_id is not None:
        return fixed_character_id
    return _pick_random_character_id(characters, rng)


def _load_character_defaults(
    *,
    characters: list[dict[str, Any]],
    character_id: str,
    render_defaults: dict[str, Any],
) -> tuple[str, dict[str, Any], str]:
    char_item = next(
        (
            item
            for item in characters
            if str(item.get("id") or "").strip() == character_id
        ),
        None,
    )
    if not char_item:
        raise ValueError(f"character_id nicht gefunden: {character_id}")

    character_name = str(
        char_item.get("name") or char_item.get("key") or ""
    ).strip()
    if not character_name:
        raise ValueError(
            "character_name ist leer (name/key fehlt im character item)."
        )

    return (
        character_name,
        dict(render_defaults),
        _subdir_for_character(character_name),
    )


def _resolve_render_settings(
    *,
    idx: int,
    rng,
    seed_seq: list[int],
    steps_seq: list[int],
    cfg_seq: list[float],
    denoise_seq: list[float],
    defaults: dict[str, Any],
) -> tuple[int, int | None, float | None, float | None]:
    run_seed = (
        seed_seq[idx % len(seed_seq)]
        if seed_seq
        else int(rng.randint(0, 2**31 - 1))
    )
    run_steps = (
        steps_seq[idx % len(steps_seq)]
        if steps_seq
        else _safe_int_or_none(defaults.get("steps"))
    )
    run_cfg = (
        cfg_seq[idx % len(cfg_seq)]
        if cfg_seq
        else _safe_float_or_none(defaults.get("cfg"), ndigits=1)
    )
    run_denoise = (
        denoise_seq[idx % len(denoise_seq)]
        if denoise_seq
        else _safe_float_or_none(defaults.get("denoise"), ndigits=None)
    )
    return run_seed, run_steps, run_cfg, run_denoise


def _safe_int_or_none(value: Any) -> int | None:
    try:
        v = str(value).strip()
        if not v:
            return None
        return int(float(v))
    except Exception:
        return None


def _safe_float_or_none(value: Any, *, ndigits: int | None) -> float | None:
    try:
        v = str(value).strip().replace(",", ".")
        if not v:
            return None
        f = float(v)
        return round(f, ndigits) if ndigits is not None else f
    except Exception:
        return None


def _generate_prompt_selection(
    *,
    playground_service: PlaygroundService,
    character_id: str,
    manual_picks: dict[str, str | None],
    include_lighting: bool,
    include_modifier: bool,
    gen_seed_base: int | None,
    idx: int,
    max_tries: int,
) -> PlaygroundDraft:
    gen_run_seed = (
        (int(gen_seed_base) + int(idx)) if gen_seed_base is not None else None
    )
    manual_selections = tuple(
        ManualPromptSelection(
            kind=kind,
            component_uid=component_id,
        )
        for kind, component_id in manual_picks.items()
        if component_id is not None
    )
    return playground_service.prepare_draft(
        PromptSelectionCommand(
            character_component_uid=character_id,
            manual_selections=manual_selections,
            include_lighting=bool(include_lighting),
            include_modifier=bool(include_modifier),
            seed=gen_run_seed,
            max_attempts=int(max_tries),
        )
    )


def _selection_view(draft: PlaygroundDraft) -> dict[str, Any]:
    return {
        component.kind: {
            "component_uid": component.component_uid,
            "revision_uid": component.latest_revision.revision_uid,
            "kind": component.kind,
            "key": component.component_key,
            "name": component.name,
            "tags": list(component.tags),
            "pos": component.latest_revision.positive_text,
            "neg": component.latest_revision.negative_text,
            "notes": component.notes,
        }
        for component in draft.selection.components
    }


def _require_prompts(draft: PlaygroundDraft) -> tuple[str, str]:
    run_pos = draft.prompt.positive_text.strip()
    run_neg = draft.prompt.negative_text.strip()
    if not run_pos or not run_neg:
        raise ValueError(
            "Generator hat leere Prompts geliefert (positive/negative)."
        )
    return run_pos, run_neg


def _resolve_render_choices(
    *,
    head: dict[str, Any],
    cycles: dict[str, list[str]],
    defaults: dict[str, Any],
    idx: int,
    rng,
) -> tuple[str | None, str | None, str | None]:
    ck = _resolve_choice(
        raw_value=str(head.get("checkpoint_name") or ""),
        cycle=cycles.get("checkpoint") or [],
        default_value=defaults.get("checkpoint_name"),
        idx=idx,
        rng=rng,
    )
    smp = _resolve_choice(
        raw_value=str(head.get("sampler_name") or ""),
        cycle=cycles.get("sampler") or [],
        default_value=defaults.get("sampler_name"),
        idx=idx,
        rng=rng,
    )
    sch = _resolve_choice(
        raw_value=str(head.get("scheduler_name") or ""),
        cycle=cycles.get("scheduler") or [],
        default_value=defaults.get("scheduler_name"),
        idx=idx,
        rng=rng,
    )
    return ck, smp, sch


def _build_preview_draft(
    *,
    base_id: int,
    idx: int,
    selection: dict[str, Any],
    character_name: str,
    subdir: str,
    seed: int,
    steps: int | None,
    cfg: float | None,
    denoise: float | None,
    checkpoint: str | None,
    sampler: str | None,
    scheduler: str | None,
    prompt_positive: str,
    prompt_negative: str,
) -> dict[str, Any]:
    return {
        "draft_id": f"{base_id}_{idx}",
        "selection": selection,
        "character_name": character_name,
        "scene_name": str((selection.get("scene") or {}).get("name") or ""),
        "outfit_name": str((selection.get("outfit") or {}).get("name") or ""),
        "pose_name": str((selection.get("pose") or {}).get("name") or ""),
        "expression_name": str(
            (selection.get("expression") or {}).get("name") or ""
        ),
        "light_name": str((selection.get("lighting") or {}).get("name") or ""),
        "modifier_name": str(
            (selection.get("modifier") or {}).get("name") or ""
        ),
        "seed": seed,
        "steps": steps,
        "cfg": cfg,
        "sampler": sampler,
        "scheduler": scheduler,
        "denoise": denoise,
        "checkpoint": checkpoint,
        "prompt_positive": prompt_positive,
        "prompt_negative": prompt_negative,
        "subdir": subdir,
    }
