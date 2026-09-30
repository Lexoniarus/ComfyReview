"""Filesystem cache for discovered ComfyUI capabilities."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path


class JsonComfyUiCapabilityCache:
    """Persist the last usable ComfyUI capability response as JSON."""

    def __init__(self, path: Path) -> None:
        self._path = Path(path)

    def load(self) -> Mapping[str, object]:
        """Return cached capabilities or an empty mapping."""
        try:
            payload = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    def save(self, capabilities: Mapping[str, object]) -> None:
        """Persist one capability snapshot."""
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps(dict(capabilities), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
