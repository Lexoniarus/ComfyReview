"""Explicit offline import and audit adapters."""

from comfyreview.importers.legacy_outputs import (
    LegacyOutputAuditor,
    LegacyOutputAuditResult,
)

__all__ = [
    "LegacyOutputAuditResult",
    "LegacyOutputAuditor",
]
