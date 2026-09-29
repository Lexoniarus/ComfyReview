"""Typed ports and results for application resource lifecycles."""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class LegacySchemaIssue:
    """Describe one structural problem in a configured legacy database."""

    database: str
    code: str
    detail: str


@dataclass(frozen=True)
class LegacySchemaReport:
    """Contain the complete result of a legacy schema operation."""

    issues: tuple[LegacySchemaIssue, ...] = ()
    initialized: tuple[str, ...] = ()
    upgraded: tuple[str, ...] = ()


class LegacySchemaValidationError(RuntimeError):
    """Signal that configured legacy databases cannot be used safely."""

    def __init__(self, report: LegacySchemaReport) -> None:
        self.report = report
        details = "; ".join(
            f"{issue.database}: {issue.detail}" for issue in report.issues
        )
        super().__init__(details or "Legacy schema validation failed")


class LegacySchemaLifecycle(Protocol):
    """Define startup validation and explicit legacy schema upgrades."""

    def prepare_startup(self) -> LegacySchemaReport:
        """Validate existing databases and initialize only missing files."""
        ...

    def validate(
        self,
        database_names: Collection[str] | None = None,
    ) -> LegacySchemaReport:
        """Inspect selected databases without mutating them."""
        ...

    def upgrade(
        self,
        database_names: Collection[str] | None = None,
        backup_directory: Path | None = None,
    ) -> LegacySchemaReport:
        """Back up and additively upgrade selected legacy databases."""
        ...


@dataclass(frozen=True)
class CanonicalSchemaReport:
    """Describe canonical database startup work."""

    initialized: bool = False
    schema_version: int = 0


class CanonicalSchemaLifecycle(Protocol):
    """Own validation and first-time creation of the canonical database."""

    def prepare_startup(self) -> CanonicalSchemaReport:
        """Validate or atomically create the canonical database."""
        ...


class WorkerRuntime(Protocol):
    """Define ownership of one long-lived background worker."""

    def start(self) -> None:
        """Start the worker once."""
        ...

    def stop(self, timeout_seconds: float) -> None:
        """Signal and await an orderly worker shutdown."""
        ...
