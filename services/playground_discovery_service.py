"""Cached Playground view of native ComfyUI capabilities."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from comfyreview.application import ComfyUiError, ComfyUiProvider
from services.playground_generator_ui.types import DiscoveryLists


class ComfyUiCapabilityCache(Protocol):
    """Store the last usable technical capability response."""

    def load(self) -> Mapping[str, object]:
        """Return cached capability values."""
        ...

    def save(self, capabilities: Mapping[str, object]) -> None:
        """Persist capability values."""
        ...


class PlaygroundDiscoveryService:
    """Serve native ComfyUI enum capabilities with a local fallback cache."""

    def __init__(
        self,
        provider: ComfyUiProvider,
        cache: ComfyUiCapabilityCache,
    ) -> None:
        self._provider = provider
        self._cache = cache

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
        raw = self._cache.load()
        return DiscoveryLists(
            checkpoints=self._strings(raw.get("checkpoints")),
            samplers=self._strings(raw.get("samplers")),
            schedulers=self._strings(raw.get("schedulers")),
        )

    def _save(self, result: DiscoveryLists) -> None:
        try:
            self._cache.save(
                {
                    "checkpoints": result.checkpoints,
                    "samplers": result.samplers,
                    "schedulers": result.schedulers,
                }
            )
        except OSError:
            return

    @staticmethod
    def _strings(value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        return [text for item in value if (text := str(item).strip())]
