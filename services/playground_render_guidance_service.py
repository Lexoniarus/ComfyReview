"""Generator-facing orchestration for render evidence guidance."""

from __future__ import annotations

from typing import Protocol

from comfyreview.application import (
    RenderCapabilitySet,
    RenderGuidance,
    RenderGuidanceService,
    RenderSettings,
)
from services.playground_generator_ui.types import DiscoveryLists


class CapabilityDiscovery(Protocol):
    """Discover currently usable provider enums."""

    def discover(self) -> DiscoveryLists:
        """Return cached-or-live ComfyUI capabilities."""
        ...


class PlaygroundRenderGuidanceService:
    """Filter canonical render guidance against live provider capabilities."""

    def __init__(
        self,
        *,
        guidance: RenderGuidanceService,
        discovery: CapabilityDiscovery,
    ) -> None:
        self._guidance = guidance
        self._discovery = discovery

    def build(
        self, current: RenderSettings, *, model: str = ""
    ) -> RenderGuidance:
        """Return recommendations that the active provider can apply."""
        capabilities = self._discovery.discover()
        return self._guidance.build(
            current=current,
            capabilities=RenderCapabilitySet(
                checkpoints=tuple(capabilities.checkpoints),
                samplers=tuple(capabilities.samplers),
                schedulers=tuple(capabilities.schedulers),
            ),
            model=model,
        )
