"""Cached Playground view of native ComfyUI capabilities."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application import ComfyUiError, ComfyUiProvider
from services.playground_generator_ui.types import DiscoveryLists
from services.ui_state_service import load_json_state, save_json_state


class PlaygroundDiscoveryService:
    """Serve native ComfyUI enum capabilities with a local fallback cache."""

    def __init__(self, provider: ComfyUiProvider, cache_path: Path) -> None:
        self._provider = provider
        self._cache_path = Path(cache_path)

    def discover(self) -> DiscoveryLists:
        """Return live capabilities or the last valid cached enum lists."""
        try:
            capabilities = self._provider.discover_capabilities()
        except ComfyUiError:
            return self._cached()
        result = DiscoveryLists(
            checkpoints=list(capabilities.checkpoints),
            samplers=list(capabilities.samplers),
            schedulers=list(capabilities.schedulers),
        )
        if result.checkpoints or result.samplers or result.schedulers:
            self._save(result)
            return result
        return self._cached()

    def _cached(self) -> DiscoveryLists:
        raw = load_json_state(self._cache_path)
        return DiscoveryLists(
            checkpoints=self._strings(raw.get("checkpoints")),
            samplers=self._strings(raw.get("samplers")),
            schedulers=self._strings(raw.get("schedulers")),
        )

    def _save(self, result: DiscoveryLists) -> None:
        try:
            save_json_state(
                self._cache_path,
                {
                    "checkpoints": result.checkpoints,
                    "samplers": result.samplers,
                    "schedulers": result.schedulers,
                },
            )
        except OSError:
            return

    @staticmethod
    def _strings(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [text for item in value if (text := str(item).strip())]
