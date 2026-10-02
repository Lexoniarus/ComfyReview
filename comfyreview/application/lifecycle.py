"""Typed ports and results for application resource lifecycles."""

from __future__ import annotations

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


@dataclass(frozen=True)
class CanonicalSchemaReport:
    """Describe canonical database validation or schema work."""

    initialized: bool = False
    schema_version: int = 0
    upgraded_from: int | None = None
    backup_path: Path | None = None
    warnings: tuple[str, ...] = ()


class CanonicalSchemaLifecycle(Protocol):
    """Own startup validation and first-time canonical database creation."""

    def prepare_startup(self) -> CanonicalSchemaReport:
        """Validate or atomically create the canonical database."""
        ...

    def validate(self) -> CanonicalSchemaReport:
        """Inspect the canonical database without mutating it."""
        ...
