from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


# ============================================================================
# Datenmodell für Regelverstöße
# ============================================================================

@dataclass(frozen=True)
class RuleViolation:
    """
    Ein einzelner Regelverstoß.

    code:
      exclude
        Excludes Regel verletzt, also A kollidiert mit B.

      require_missing
        Requires Regel verletzt, also A verlangt bestimmte Tags, die fehlen.

      require_any_missing
        Requires Any verletzt, also A verlangt mindestens eine Gruppe, aber keine Gruppe ist erfüllt.

      gate_missing
        Gate blockt Kandidat schon vor dem Pick, weil Voraussetzungen fehlen.

    message
      Menschlich lesbare Erklärung.
      Diese Message kann später direkt in der UI angezeigt werden.

    details
      Strukturierte Zusatzinfos für Debug oder UI.
    """
    code: str
    message: str
    details: Dict[str, str]
