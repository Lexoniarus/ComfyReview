"""Explicit test helpers for creating isolated legacy databases."""

from __future__ import annotations

from pathlib import Path

from comfyreview.repositories.sqlite import LegacySchemaManager
from comfyreview.settings import load_settings

_PATH_ENVIRONMENT = {
    "ratings": "COMFYREVIEW_RATINGS_DB",
    "prompt_tokens": "COMFYREVIEW_PROMPT_TOKENS_DB",
    "arena": "COMFYREVIEW_ARENA_DB",
    "curation": "COMFYREVIEW_CURATION_DB",
    "playground": "COMFYREVIEW_PLAYGROUND_DB",
    "combo_prompts": "COMFYREVIEW_COMBO_DB",
    "images": "COMFYREVIEW_IMAGES_DB",
    "prompt_ratings": "COMFYREVIEW_PROMPT_RATINGS_DB",
    "mv_queue": "COMFYREVIEW_MV_QUEUE_DB",
}


def initialize_legacy_database(name: str, path: Path) -> None:
    """Create one named legacy database through the explicit schema manager."""
    environment_name = _PATH_ENVIRONMENT[name]
    settings = load_settings(
        base_directory=path.parent,
        environ={environment_name: str(path)},
    )
    LegacySchemaManager(settings).upgrade(
        [name],
        backup_directory=path.parent / "backups",
    )
