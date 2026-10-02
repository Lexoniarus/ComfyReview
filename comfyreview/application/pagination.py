"""Typed pagination shared by bounded application queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class CollectionPage(Generic[T]):
    """Contain one deterministic page and its total result count."""

    entries: tuple[T, ...]
    total: int
    offset: int
    limit: int


def normalize_page(offset: int, limit: int) -> tuple[int, int]:
    """Return non-negative paging values with the public limit cap."""
    return max(int(offset), 0), min(max(int(limit), 1), 48)
