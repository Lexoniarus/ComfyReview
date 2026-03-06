"""
services/playground_rules.py

Playground Rules Engine (Facade)
================================

Diese Datei bleibt als stabile Import-Adresse bestehen:

    from services.playground_rules import ...

Die eigentliche Implementierung ist in kleinere Module aufgeteilt unter:
    services/playground_rules_engine/

Ziel:
- gleiche Funktionalität wie vorher
- klarere Rollen
- kleinere Dateien
"""

from __future__ import annotations

from services.playground_rules_engine import (  # noqa: F401
    DEFAULT_MAX_TRIES,
    ENFORCE_ADULT_TAG,
    EXCLUDES,
    GATES,
    REQUIRES,
    REQUIRES_ANY,
    RuleViolation,
    candidate_allowed_by_excludes,
    check_excludes,
    check_requires,
    check_requires_any,
    derive_tags_for_item,
    explain_violations,
    filter_candidates,
    gate_allows_candidate,
    get_effective_tags,
    parse_tags_csv,
    validate_selection,
)

__all__ = [
    "DEFAULT_MAX_TRIES",
    "ENFORCE_ADULT_TAG",
    "RuleViolation",
    "parse_tags_csv",
    "derive_tags_for_item",
    "get_effective_tags",
    "EXCLUDES",
    "REQUIRES",
    "REQUIRES_ANY",
    "GATES",
    "check_excludes",
    "check_requires",
    "check_requires_any",
    "validate_selection",
    "gate_allows_candidate",
    "candidate_allowed_by_excludes",
    "filter_candidates",
    "explain_violations",
]
