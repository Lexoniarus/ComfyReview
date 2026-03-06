from __future__ import annotations

# Facade exports for the Playground Rules Engine (internal package)
from services.playground_rules_engine.config import DEFAULT_MAX_TRIES, ENFORCE_ADULT_TAG
from services.playground_rules_engine.types import RuleViolation
from services.playground_rules_engine.tagging import derive_tags_for_item, get_effective_tags, parse_tags_csv
from services.playground_rules_engine.rules import EXCLUDES, GATES, REQUIRES, REQUIRES_ANY
from services.playground_rules_engine.checks import check_excludes, check_requires, check_requires_any, validate_selection
from services.playground_rules_engine.filtering import (
    candidate_allowed_by_excludes,
    explain_violations,
    filter_candidates,
    gate_allows_candidate,
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
