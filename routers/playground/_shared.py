from __future__ import annotations

from pathlib import Path

from services.file_urls import png_path_to_url

# Persistierter Generator Zustand
GENERATOR_STATE_PATH = Path("data/ui_state/playground_generator_last.json")

# Transient Preview Batch State
GENERATOR_PREVIEW_STATE_PATH = Path("data/ui_state/playground_generator_preview.json")

# Cache fuer Discovery Listen (Checkpoints, Samplers, Schedulers)
COMFY_DISCOVERY_CACHE_PATH = Path("data/ui_state/comfy_discovery_cache.json")
