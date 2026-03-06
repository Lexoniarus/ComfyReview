from __future__ import annotations

from typing import Any, Dict, List, Optional


def remove_draft(drafts: List[Dict[str, Any]], draft_id: str) -> List[Dict[str, Any]]:
    did = str(draft_id or "").strip()
    if not did:
        return list(drafts or [])
    return [d for d in (drafts or []) if str(d.get("draft_id")) != did]


def update_draft(
    drafts: List[Dict[str, Any]],
    *,
    draft_id: str,
    seed: Optional[str] = None,
    steps: Optional[str] = None,
    cfg: Optional[str] = None,
    sampler: Optional[str] = None,
    scheduler: Optional[str] = None,
    denoise: Optional[str] = None,
    checkpoint: Optional[str] = None,
    pos: Optional[str] = None,
    neg: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Update a single draft in memory.

    This only changes preview state.
    Head state is intentionally not touched.
    """

    did = str(draft_id or "").strip()
    if not did:
        return list(drafts or [])

    out = [dict(x) for x in (drafts or [])]
    for d in out:
        if str(d.get("draft_id")) != did:
            continue

        if pos is not None:
            d["prompt_positive"] = str(pos)
        if neg is not None:
            d["prompt_negative"] = str(neg)

        if checkpoint is not None:
            d["checkpoint"] = str(checkpoint or "").strip() or None
        if sampler is not None:
            d["sampler"] = str(sampler or "").strip() or None
        if scheduler is not None:
            d["scheduler"] = str(scheduler or "").strip() or None

        try:
            if seed is not None and str(seed).strip():
                d["seed"] = int(float(str(seed)))
        except Exception:
            pass
        try:
            if steps is not None and str(steps).strip():
                d["steps"] = int(float(str(steps)))
        except Exception:
            pass
        try:
            if cfg is not None and str(cfg).strip():
                d["cfg"] = round(float(str(cfg)), 1)
        except Exception:
            pass
        try:
            if denoise is not None and str(denoise).strip():
                d["denoise"] = float(str(denoise))
        except Exception:
            pass

        break

    return out
