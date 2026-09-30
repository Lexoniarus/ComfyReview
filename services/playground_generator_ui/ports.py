"""Ports owned by the server-rendered Playground generator UI."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Protocol


class PlaygroundGeneratorState(Protocol):
    """Persist server-owned form state and preview drafts."""

    def load_head(self) -> dict[str, Any]:
        """Return persisted form values."""
        ...

    def save_head(self, state: Mapping[str, object]) -> None:
        """Persist form values."""
        ...

    def load_preview(self) -> list[dict[str, Any]]:
        """Return persisted preview drafts."""
        ...

    def save_preview(self, drafts: Sequence[Mapping[str, object]]) -> None:
        """Persist preview drafts."""
        ...

    def clear_preview(self) -> None:
        """Clear persisted preview drafts."""
        ...
