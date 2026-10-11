"""Application contracts for the isolated Card Battler POC runtime store."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class CardBattlerRuntimeSchemaReport:
    """Describe validation or first-time creation of the POC runtime store."""

    initialized: bool
    schema_version: int


class CardBattlerRuntimeSchemaError(RuntimeError):
    """Report an unavailable, corrupt, or unsupported Card runtime store."""


class CardBattlerRuntimeSchemaLifecycle(Protocol):
    """Own the isolated Card runtime schema lifecycle."""

    def prepare_startup(self) -> CardBattlerRuntimeSchemaReport:
        """Create a missing v1 store or validate an existing one."""
        ...

    def validate(self) -> CardBattlerRuntimeSchemaReport:
        """Validate the existing store without mutating it."""
        ...
