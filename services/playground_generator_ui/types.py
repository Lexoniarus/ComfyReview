from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DiscoveryLists:
    """ComfyUI discovery lists for the generator UI."""

    checkpoints: list[str]
    samplers: list[str]
    schedulers: list[str]
    loras: list[str]
