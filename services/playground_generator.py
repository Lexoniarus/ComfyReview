"""services/playground_generator.py

Facade for the Playground Generator business logic.

The implementation is split into small modules in:
  services/playground_generator_core/

Public API remains stable:
  - PlaygroundGenerator
  - build_prompts
  - effective_tags
  - ItemDict / SelectionDict
"""

from __future__ import annotations

from services.playground_generator_core.types import ItemDict, SelectionDict
from services.playground_generator_core.tags import effective_tags
from services.playground_generator_core.prompt_building import build_prompts
from services.playground_generator_core.generator import PlaygroundGenerator

__all__ = [
    "ItemDict",
    "SelectionDict",
    "effective_tags",
    "build_prompts",
    "PlaygroundGenerator",
]
