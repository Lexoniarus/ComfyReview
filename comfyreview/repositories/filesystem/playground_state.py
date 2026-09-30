"""Filesystem persistence for server-owned Playground UI state."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any


class PlaygroundGeneratorStateRepository:
    """Own persisted generator form state and transient preview drafts."""

    def __init__(self, *, head_path: Path, preview_path: Path) -> None:
        self._head_path = Path(head_path)
        self._preview_path = Path(preview_path)

    def load_head(self) -> dict[str, Any]:
        """Return persisted form values or an empty state."""
        return self._read_object(self._head_path)

    def save_head(self, state: Mapping[str, object]) -> None:
        """Persist one form-state snapshot."""
        self._write_object(self._head_path, dict(state))

    def load_preview(self) -> list[dict[str, Any]]:
        """Return persisted preview drafts or an empty list."""
        payload = self._read_object(self._preview_path)
        drafts = payload.get("drafts")
        if not isinstance(drafts, list):
            return []
        return [dict(item) for item in drafts if isinstance(item, dict)]

    def save_preview(self, drafts: Sequence[Mapping[str, object]]) -> None:
        """Persist one preview-draft snapshot."""
        self._write_object(
            self._preview_path,
            {"drafts": [dict(item) for item in drafts]},
        )

    def clear_preview(self) -> None:
        """Persist an empty preview-draft snapshot."""
        self.save_preview(())

    @staticmethod
    def _read_object(path: Path) -> dict[str, Any]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError):
            return {}
        return payload if isinstance(payload, dict) else {}

    @staticmethod
    def _write_object(path: Path, payload: Mapping[str, object]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(dict(payload), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
