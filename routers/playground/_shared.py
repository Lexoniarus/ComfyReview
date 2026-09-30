from __future__ import annotations

from pathlib import Path

# Persistierter Generator Zustand
GENERATOR_STATE_PATH = Path("data/ui_state/playground_generator_last.json")

# Transient Preview Batch State
GENERATOR_PREVIEW_STATE_PATH = Path(
    "data/ui_state/playground_generator_preview.json"
)
