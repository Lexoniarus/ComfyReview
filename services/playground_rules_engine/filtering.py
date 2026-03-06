from __future__ import annotations

from typing import Callable, List, Optional, Sequence, Set, Tuple

from services.playground_rules_engine.checks import check_excludes
from services.playground_rules_engine.config import ENFORCE_ADULT_TAG
from services.playground_rules_engine.rules import GATES
from services.playground_rules_engine.types import RuleViolation


def gate_allows_candidate(
    *,
    kind: str,
    candidate_tags: Set[str],
    active_tags: Set[str],
) -> Tuple[bool, Optional[RuleViolation]]:
    """
    Gate Check für einen Kandidaten eines bestimmten kind.
    """
    for gate_tag, required_active_tags, reason in GATES.get(kind, []):
        if not ENFORCE_ADULT_TAG and "adult" in required_active_tags:
            continue

        if gate_tag in candidate_tags:
            missing = required_active_tags - active_tags
            if missing:
                return False, RuleViolation(
                    code="gate_missing",
                    message=f"Gate blockt Kandidat: '{gate_tag}' braucht {sorted(missing)}. {reason}",
                    details={
                        "kind": kind,
                        "gate_tag": gate_tag,
                        "missing": ", ".join(sorted(missing)),
                        "reason": reason,
                    },
                )

    return True, None


def candidate_allowed_by_excludes(
    *,
    candidate_tags: Set[str],
    active_tags: Set[str],
) -> Tuple[bool, Optional[RuleViolation]]:
    """
    Schneller Vorfilter auf Basis von EXCLUDES.
    """
    combined = active_tags | candidate_tags
    violations = check_excludes(combined)
    if violations:
        return False, violations[0]
    return True, None


def filter_candidates(
    *,
    kind: str,
    candidates: Sequence[object],
    get_tags: Callable[[object], Set[str]],
    active_tags: Set[str],
) -> Tuple[List[object], List[RuleViolation]]:
    """
    Filtert eine Kandidatenliste vor einem Random Pick.

    Ablauf:
    - Für jeden Kandidaten:
      1) Gate Check
      2) Excludes Pre Check
    """
    allowed: List[object] = []
    reasons: List[RuleViolation] = []

    for c in candidates:
        ctags = get_tags(c)

        ok, v = gate_allows_candidate(kind=kind, candidate_tags=ctags, active_tags=active_tags)
        if not ok:
            reasons.append(v)  # type: ignore[arg-type]
            continue

        ok, v = candidate_allowed_by_excludes(candidate_tags=ctags, active_tags=active_tags)
        if not ok:
            reasons.append(v)  # type: ignore[arg-type]
            continue

        allowed.append(c)

    return allowed, reasons


def explain_violations(violations: Sequence[RuleViolation]) -> str:
    """
    Macht aus Violations eine lesbare Debug Ausgabe.
    """
    if not violations:
        return "Keine Regelverletzungen."
    return "\n".join([f"{v.code}: {v.message}" for v in violations])
