"""Combo prompts service.

Compatibility facade.

The MV worker and playground hub import these functions from
services.combo_prompts_service. For 0.0.5b we keep that stable, but the
implementation lives in smaller modules under services.combo_prompts.
"""

from __future__ import annotations

from services.combo_prompts.rebuild import (
    ensure_combo_prompts_db,
    get_top_combos_2,
    get_top_combos_3,
    rebuild_combo_prompts,
)

__all__ = [
    "ensure_combo_prompts_db",
    "get_top_combos_2",
    "get_top_combos_3",
    "rebuild_combo_prompts",
]
