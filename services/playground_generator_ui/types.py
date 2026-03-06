from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class DiscoveryLists:
    """ComfyUI discovery lists for the generator UI."""

    checkpoints: List[str]
    samplers: List[str]
    schedulers: List[str]
