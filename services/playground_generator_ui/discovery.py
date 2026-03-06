from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from services.comfy_client import ComfyClient
from services.ui_state_service import load_json_state, save_json_state

from .types import DiscoveryLists


def discover_comfy_lists(*, cache_path: Path, client: Optional[ComfyClient] = None) -> DiscoveryLists:
    """Return checkpoints, samplers, schedulers.

    Strategy
    1) Try live ComfyUI discovery
    2) If that fails, fallback to cache JSON
    3) If discovery worked, refresh cache
    """

    checkpoints: List[str] = []
    samplers: List[str] = []
    schedulers: List[str] = []

    live_ok = False
    try:
        c = client or ComfyClient()
        checkpoints = c.get_checkpoints() or []
        samplers = c.get_samplers() or []
        schedulers = c.get_schedulers() or []
        live_ok = bool(checkpoints or samplers or schedulers)
    except Exception:
        live_ok = False

    if live_ok:
        try:
            save_json_state(
                cache_path,
                {
                    "checkpoints": checkpoints,
                    "samplers": samplers,
                    "schedulers": schedulers,
                },
            )
        except Exception:
            pass
        return DiscoveryLists(checkpoints=checkpoints, samplers=samplers, schedulers=schedulers)

    cache = load_json_state(cache_path) or {}

    c0 = cache.get("checkpoints")
    if isinstance(c0, list):
        checkpoints = [str(x).strip() for x in c0 if str(x).strip()]

    s0 = cache.get("samplers")
    if isinstance(s0, list):
        samplers = [str(x).strip() for x in s0 if str(x).strip()]

    s1 = cache.get("schedulers")
    if isinstance(s1, list):
        schedulers = [str(x).strip() for x in s1 if str(x).strip()]

    return DiscoveryLists(checkpoints=checkpoints, samplers=samplers, schedulers=schedulers)
