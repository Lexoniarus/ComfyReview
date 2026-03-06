from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Set, Tuple

from services.playground_rules_engine.config import ENFORCE_ADULT_TAG
from services.playground_rules_engine.exclude_index import EXCLUDE_INDEX
from services.playground_rules_engine.rules import REQUIRES, REQUIRES_ANY
from services.playground_rules_engine.types import RuleViolation


def check_excludes(active_tags: Set[str]) -> List[RuleViolation]:
    """
    Prüft EXCLUDES Regeln.
    Wenn eine Excludes Regel verletzt ist, ist die Kombination ungültig.
    """
    violations: List[RuleViolation] = []

    for t in active_tags:
        for other, reason in EXCLUDE_INDEX.get(t, []):
            if other in active_tags:
                violations.append(
                    RuleViolation(
                        code="exclude",
                        message=f"Excludes verletzt: '{t}' mit '{other}'. {reason}",
                        details={"tag": t, "other": other, "reason": reason},
                    )
                )

    # Dedup, weil symmetrisch geprüft wird
    dedup: Dict[Tuple[str, str], RuleViolation] = {}
    for v in violations:
        a = v.details["tag"]
        b = v.details["other"]
        key = tuple(sorted([a, b]))
        dedup[key] = v

    return list(dedup.values())


def check_requires(active_tags: Set[str]) -> List[RuleViolation]:
    """
    Prüft REQUIRES Regeln.
    Wenn Trigger Tag aktiv ist, müssen alle Required Tags ebenfalls aktiv sein.
    """
    violations: List[RuleViolation] = []

    for trigger, (required_set, reason) in REQUIRES.items():
        if trigger in active_tags:
            missing = required_set - active_tags
            if missing:
                violations.append(
                    RuleViolation(
                        code="require_missing",
                        message=f"Requires verletzt: '{trigger}' braucht {sorted(missing)}. {reason}",
                        details={
                            "trigger": trigger,
                            "missing": ", ".join(sorted(missing)),
                            "reason": reason,
                        },
                    )
                )

    return violations


def check_requires_any(active_tags: Set[str]) -> List[RuleViolation]:
    """
    Prüft REQUIRES_ANY Regeln.
    Wenn Trigger Tag aktiv ist, muss mindestens eine Gruppe erfüllt sein.
    """
    violations: List[RuleViolation] = []

    for trigger, (groups, reason) in REQUIRES_ANY.items():
        if trigger not in active_tags:
            continue

        # Eine Gruppe gilt als erfüllt, wenn alle Tags der Gruppe aktiv sind
        ok_any = any((g <= active_tags) for g in groups)
        if ok_any:
            continue

        groups_pretty = " OR ".join([str(sorted(g)) for g in groups])
        violations.append(
            RuleViolation(
                code="require_any_missing",
                message=f"RequiresAny verletzt: '{trigger}' braucht eine Gruppe: {groups_pretty}. {reason}",
                details={
                    "trigger": trigger,
                    "groups": groups_pretty,
                    "reason": reason,
                },
            )
        )

    return violations


def validate_selection(active_tags: Set[str]) -> List[RuleViolation]:
    """
    Validiert eine komplette Auswahl anhand aller Regeltypen.

    Rückgabe:
    - Leere Liste bedeutet gültig
    - Liste mit Einträgen bedeutet ungültig, jede Violation erklärt warum

    Adult Enforcement:
    - Wenn ENFORCE_ADULT_TAG False ist, ignorieren wir Verstöße, die nur adult betreffen.
    """
    out: List[RuleViolation] = []
    out.extend(check_excludes(active_tags))
    out.extend(check_requires(active_tags))
    out.extend(check_requires_any(active_tags))

    if not ENFORCE_ADULT_TAG:
        out = [
            v for v in out
            if not (
                (v.code in {"require_missing", "require_any_missing"} and "adult" in v.message)
            )
        ]

    return out
