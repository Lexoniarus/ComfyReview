"""Explicit write import of a previously audited legacy output tree."""

from __future__ import annotations

from pathlib import Path

from comfyreview.application import CanonicalSchemaLifecycle
from comfyreview.importers.legacy_models import (
    LegacyOutputImportObserver,
    LegacyOutputImportRepository,
    LegacyOutputImportResult,
    LegacyOutputImportSource,
)


class LegacyOutputImporter:
    """Verify an audit snapshot and atomically import its full-graph outputs."""

    def __init__(
        self,
        *,
        schema: CanonicalSchemaLifecycle,
        source: LegacyOutputImportSource,
        repository: LegacyOutputImportRepository,
        observer: LegacyOutputImportObserver | None = None,
    ) -> None:
        self._schema = schema
        self._source = source
        self._repository = repository
        self._observer = observer

    def import_audit(
        self,
        report_path: Path,
        *,
        backup_directory: Path | None = None,
    ) -> LegacyOutputImportResult:
        """Import one verified audit snapshot without modifying source files."""
        self._schema.validate()
        records, excluded_without_sidecar = self._source.load(report_path)
        self._repository.validate_records(records)
        return self._repository.import_records(
            records,
            excluded_without_sidecar=excluded_without_sidecar,
            backup_directory=backup_directory,
            observer=self._observer,
        )
