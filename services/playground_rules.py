"""
services/playground_rules.py

Playground Rules Engine
=======================

Ziel
Diese Datei definiert die komplette Tag Logik für den Prompt Generator.

Wichtige Punkte
1) Keine DB Migration
   Wir ändern nicht die SQLite Struktur und wir müssen keine 200 plus Einträge anfassen.

2) Items sind komplette Blöcke
   Ein Scene Eintrag ist komplett, ein Outfit Eintrag ist komplett, Pose, Expression, Lighting, Modifier ebenso.
   Der Generator kombiniert nur komplette Blöcke miteinander.
   Es gibt keine Sub Assembly innerhalb eines Items.

3) Regeln laufen rein über Tags
   Der Generator liest Tags aus der DB (CSV) und ergänzt optional Derived Tags (Heuristiken),
   damit Regeln schon funktionieren, auch wenn Tags noch nicht perfekt gepflegt sind.

4) Drei Regeltypen plus eine ODER Variante
   EXCLUDES
     Zwei Tags dürfen nie gleichzeitig vorkommen. Beispiel school und lewd.

   REQUIRES
     Wenn Tag A aktiv ist, müssen auch Tags B und C aktiv sein. Beispiel wind braucht skirt.

   REQUIRES_ANY
     Wenn Tag A aktiv ist, muss mindestens eine von mehreren Tag Gruppen erfüllt sein.
     Beispiel swimwear braucht entweder water oder water_proxy.

   GATES
     Vorfilter beim Random Pick.
     Kandidaten werden gar nicht erst angeboten, wenn Voraussetzungen fehlen.
     Das reduziert Reject Looping und macht das System schneller und stabiler.

Wie ihr diese Datei pflegt
Ihr pflegt hauptsächlich diese vier Blöcke:
- EXCLUDES
- REQUIRES
- REQUIRES_ANY
- GATES

Wenn ihr neue Tags einführt, dann ergänzt ihr:
- zuerst GATES, damit Random Picks plausibel werden
- dann REQUIRES oder REQUIRES_ANY, wenn es harte Abhängigkeiten sind
- dann EXCLUDES, wenn es harte Unverträglichkeiten sind

Adult Only und Lewd
Viele eurer vorbereiteten Items enthalten Hinweise wie "Character must be adult."
Das wird als derived Tag "adult_only" erkannt.

Wenn ENFORCE_ADULT_TAG True ist, dann gilt:
- adult_only und lewd sind nur erlaubt, wenn der Character Tag "adult" besitzt.
Wenn ENFORCE_ADULT_TAG False ist, dann blocken wir das nicht.

Empfehlung
Lasst ENFORCE_ADULT_TAG an.
Das schützt euch vor inkonsistenten Kombinationen, solange die Characters noch als youthful angelegt sind.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Set, Tuple


# ============================================================================
# Konfig Flags
# ============================================================================

# Wenn True, dann sind lewd und adult-only Inhalte nur erlaubt,
# wenn der ausgewählte Charakter Tag "adult" besitzt.
ENFORCE_ADULT_TAG: bool = True

# Maximalversuche, falls ihr Reject Looping im Generator nutzt.
# Der Generator kann pro Slot oder pro kompletter Auswahl maximal so oft versuchen.
DEFAULT_MAX_TRIES: int = 200


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


# ============================================================================
# Tag Hilfsfunktionen
# ============================================================================

def parse_tags_csv(tags: str) -> Set[str]:
    """
    Erwartet Tags als CSV String mit Komma Trennung.
    Beispiel: "school, uniform, winter"
    """
    if not tags:
        return set()
    return {t.strip() for t in tags.split(",") if t.strip()}


def _lower_join(*parts: str) -> str:
    """
    Hilfsfunktion, um mehrere Textfelder zu einem lowercased Suchtext zu kombinieren.
    """
    return " ".join([p or "" for p in parts]).lower()


def derive_tags_for_item(
    *,
    kind: str,
    key: str,
    name: str,
    pos: str,
    neg: str,
    notes: str,
) -> Set[str]:
    """
    Derived Tags

    Warum
    Einige Regeln hängen an Tags, die in der DB eventuell noch nicht überall sauber gepflegt sind.
    Beispiel:
    Ein Outfit hat im pos Prompt "navy pleated skirt", aber das Tag "skirt" fehlt.
    Wind Modifier sagt aber "Requires skirt outfit".
    Ohne Derived Tags würdet ihr dann Wind Modifier nie korrekt filtern können.

    Wie
    Wir leiten sehr wenige, sehr stabile Tags aus Textfeldern ab:
    key, name, pos, notes.

    Aktuelle Heuristiken, passend zu euren Daten:

    skirt
      Wenn irgendwo "skirt" vorkommt, setzen wir "skirt".

    adult_only
      Wenn notes "Character must be adult" enthalten, setzen wir "adult_only".

    lewd
      Wenn irgendwo "lewd" vorkommt, setzen wir "lewd".
      Das ist eine Absicherung, falls jemand lewd nur in Notes schreibt.

    pool
      Wenn irgendwo "pool" vorkommt, setzen wir "pool".

    water_proxy
      Wenn irgendwo "beach" oder "pool" vorkommt, setzen wir "water_proxy".
      Das ist ein pragmatischer Brückentag, um Beach oder Pool Kontext als Wasser Kontext zu behandeln.
    """
    text = _lower_join(key, name, pos, notes)
    out: Set[str] = set()

    if "skirt" in text:
        out.add("skirt")

    if "character must be adult" in text:
        out.add("adult_only")

    if "lewd" in text:
        out.add("lewd")

    if "pool" in text:
        out.add("pool")

    if "beach" in text or "pool" in text:
        out.add("water_proxy")

    return out


def get_effective_tags(
    *,
    kind: str,
    key: str,
    name: str,
    tags: str,
    pos: str,
    neg: str,
    notes: str,
) -> Set[str]:
    """
    Effektive Tags = DB Tags + Derived Tags

    DB Tags sind die Basis.
    Derived Tags schließen Lücken, damit Rules sofort greifen.

    Später, wenn die DB perfekt getaggt ist, könnt ihr Derived Tags reduzieren.
    """
    base = parse_tags_csv(tags)
    derived = derive_tags_for_item(kind=kind, key=key, name=name, pos=pos, neg=neg, notes=notes)
    return base | derived


# ============================================================================
# Regeldefinitionen
# ============================================================================

# EXCLUDES
# Zwei Tags dürfen nie gleichzeitig aktiv sein.

# REQUIRES
# Wenn Trigger Tag aktiv ist, müssen alle Required Tags aktiv sein.

# REQUIRES_ANY
# Wenn Trigger Tag aktiv ist, muss mindestens eine Gruppe erfüllt sein.
# Eine Gruppe ist ein Set von Tags, die gemeinsam vorhanden sein müssen.
# Gruppen sind eine ODER Liste, innerhalb der Gruppe ist es UND.

# GATES
# Vorfilter beim Random Pick.
# Wenn Kandidat gate_tag hat, müssen required_active_tags bereits aktiv sein.
# Damit pickt der Generator Kandidaten gar nicht erst, die sicher scheitern würden.


# ============================================================================
# EXCLUDES Pack
# ============================================================================

EXCLUDES: List[Tuple[str, str, str]] = [
    # Schul Kontext und lewd Inhalte werden hart getrennt.
    ("school", "lewd", "Schul Kontext und lewd Inhalte werden hart getrennt."),

    # Studio und Minimal sind bei euch typischerweise Test Szenen.
    # Dort wollt ihr meistens keine lewd Inhalte, weil das Stabilitätstests verzerrt.
    ("studio", "lewd", "Studio Test Szenen sollen nicht mit lewd Content kombiniert werden."),
    ("minimal", "lewd", "Minimal Test Szenen sollen nicht mit lewd Content kombiniert werden."),

    # Wet Fabric Light Modifier Notes sagt "Avoid dramatic lighting."
    # Wir modellieren das als harte Unverträglichkeit.
    ("wet", "dramatic", "Wet Fabric soll nicht mit dramatischem Licht kombiniert werden, um Artefakte zu vermeiden."),

    # Optionaler Schutz: Slice of life mit lewd wirkt oft inhaltlich schief.
    # Wenn ihr das später als zu restriktiv empfindet, könnt ihr diese Regel entfernen.
    ("slice of life", "lewd", "Slice of life Szenen sollen nicht mit lewd Content kombiniert werden."),
]


# ============================================================================
# REQUIRES Pack
# ============================================================================

REQUIRES: Dict[str, Tuple[Set[str], str]] = {
    # Wind Lift Subtle Modifier
    # Notes: Requires skirt outfit.
    # Der Tag skirt kommt entweder direkt aus DB tags oder via derived tags.
    "wind": ({"skirt"}, "Wind Modifier ist nur erlaubt, wenn ein Rock Outfit aktiv ist (Tag skirt)."),

    # Rain
    # Wenn ein Modifier oder ein Scene Element rain trägt, soll die Szene auch rain tragen.
    # Damit vermeiden wir Rain Effekte in Sonnenszenen.
    "rain": ({"rain"}, "Rain Effekte oder Rain Modifier brauchen eine Scene, die ebenfalls Tag rain hat."),

    # Adult only Inhalte
    # Viele Items tragen Notes: Character must be adult.
    # Das wird als derived tag adult_only erkannt.
    # Wenn ENFORCE_ADULT_TAG True ist, ist adult_only nur erlaubt, wenn der Character Tag adult hat.
    "adult_only": ({"adult"}, "Adult-only Items sind nur erlaubt, wenn der Charakter Tag adult besitzt."),

    # Club Activities
    # In eurem neuen Szenen Pack sind Club Activities klar Schul Kontext.
    # Damit verhindern wir Club Kombinationen in komplett falschen Umgebungen.
    "club": ({"school"}, "Club Aktivitäten gehören in Schul Kontext (Tag school)."),

    # Kendo
    # Kendo ist in eurem Pack als School Sport Activity gedacht.
    # Wir verlangen school und sport.
    "kendo": ({"school", "sport"}, "Kendo ist als School Sport Activity gedacht (Tags school und sport)."),

    # Weitere School Activity Tags
    # Diese Tags sind bei euch klar Schul Kontexte, aber weniger streng als Kendo.
    "tech": ({"school"}, "Tech Activities gehören in Schul Kontext (Tag school)."),
    "music": ({"school"}, "Music Activities gehören in Schul Kontext (Tag school)."),
    "literature": ({"school"}, "Literature Activities gehören in Schul Kontext (Tag school)."),
    "art": ({"school"}, "Art Activities gehören in Schul Kontext (Tag school)."),
}


# ============================================================================
# REQUIRES_ANY Pack
# ============================================================================

REQUIRES_ANY: Dict[str, Tuple[List[Set[str]], str]] = {
    # Swimwear oder Beach Kontext
    # Notes sagen sinngemäß beach oder pool context only.
    # Sauber wäre: Scene hat water Tag.
    # Pragmatisch: water_proxy kann aus Outfit Notes beach oder pool abgeleitet werden.
    "swimwear": (
        [{"water"}, {"water_proxy"}],
        "Swimwear ist nur in Wasser Kontext erlaubt (Scene Tag water oder abgeleitetes water_proxy).",
    ),
    "beach": (
        [{"water"}, {"water_proxy"}],
        "Beach Outfits sind nur in Wasser Kontext erlaubt (Scene Tag water oder abgeleitetes water_proxy).",
    ),

    # Sport ist flexibel
    # Sport kann Schul Sport sein oder Outdoor Sport.
    # Deshalb reicht entweder school oder outdoor.
    "sport": (
        [{"school"}, {"outdoor"}],
        "Sport Inhalte brauchen entweder Schul Kontext oder Outdoor Kontext (Tag school oder outdoor).",
    ),

    # Festival
    # Festival kann tags festival tragen und optional night.
    "festival": (
        [{"festival"}, {"festival", "night"}],
        "Festival Inhalte sollen nur im Festival Kontext stattfinden (Tag festival, optional mit night).",
    ),

    # Mystery
    # Mystery ist oft night oder quiet, je nach euren Szenen.
    "mystery": (
        [{"night"}, {"quiet"}],
        "Mystery Inhalte brauchen meist Night oder Quiet Stimmung (Tag night oder quiet).",
    ),

    # Isekai und Fantasy
    # Isekai soll nicht aus Versehen in school slice of life landen.
    "isekai": (
        [{"fantasy"}],
        "Isekai Inhalte brauchen Fantasy Kontext (Tag fantasy).",
    ),
}


# ============================================================================
# GATES Pack
# ============================================================================

GATES: Dict[str, List[Tuple[str, Set[str], str]]] = {
    # Modifier Gates
    # Diese Regeln reduzieren Reject Looping, weil wir offensichtliche Fehlschläge verhindern.
    "modifier": [
        ("wind", {"skirt"}, "Wind Modifier nur dann picken, wenn ein Rock Outfit aktiv ist."),
        ("rain", {"rain"}, "Rain Modifier nur dann picken, wenn die Scene bereits rain ist."),
        ("club", {"school"}, "Club Modifier nur dann picken, wenn Schul Kontext aktiv ist."),
        ("kendo", {"school", "sport"}, "Kendo Modifier nur dann picken, wenn Schul Sport Kontext aktiv ist."),
    ],

    # Adult only und Lewd Gates
    # Diese Gates greifen nur, wenn ENFORCE_ADULT_TAG True ist.
    # Wenn ENFORCE_ADULT_TAG False ist, werden diese Gates ignoriert.
    "outfit": [
        ("adult_only", {"adult"}, "Adult-only Outfits nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Outfits nur dann picken, wenn der Charakter adult ist."),
    ],
    "pose": [
        ("adult_only", {"adult"}, "Adult-only Posen nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Posen nur dann picken, wenn der Charakter adult ist."),
    ],
    "expression": [
        ("adult_only", {"adult"}, "Adult-only Expression nur dann picken, wenn der Charakter adult ist."),
        ("lewd", {"adult"}, "Lewd Expression nur dann picken, wenn der Charakter adult ist."),
    ],

    # Lighting optional
    # Dramatic Lighting ist meist stabiler in night Kontext.
    # Wenn ihr das zu restriktiv findet, könnt ihr es entfernen.
    "lighting": [
        ("dramatic", {"night"}, "Dramatic Lighting bevorzugt nur in night Kontext picken."),
    ],
}


# ============================================================================
# Engine: Checks und Filter
# ============================================================================

def _build_exclude_index(excludes: Sequence[Tuple[str, str, str]]) -> Dict[str, List[Tuple[str, str]]]:
    """
    Baut ein Lookup:
    tag -> Liste von (other_tag, grund)
    Symmetrisch.
    """
    idx: Dict[str, List[Tuple[str, str]]] = {}
    for a, b, reason in excludes:
        idx.setdefault(a, []).append((b, reason))
        idx.setdefault(b, []).append((a, reason))
    return idx


_EXCLUDE_INDEX = _build_exclude_index(EXCLUDES)


def check_excludes(active_tags: Set[str]) -> List[RuleViolation]:
    """
    Prüft EXCLUDES Regeln.
    Wenn eine Excludes Regel verletzt ist, ist die Kombination ungültig.
    """
    violations: List[RuleViolation] = []

    for t in active_tags:
        for other, reason in _EXCLUDE_INDEX.get(t, []):
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

    Beispiel
    swimwear hat Gruppen [{water}, {water_proxy}]
    Das heißt, entweder water ist aktiv oder water_proxy ist aktiv.
    """
    violations: List[RuleViolation] = []

    for trigger, (groups, reason) in REQUIRES_ANY.items():
        if trigger not in active_tags:
            continue

        ok = False
        for group in groups:
            if group.issubset(active_tags):
                ok = True
                break

        if not ok:
            pretty_groups = ["{" + ", ".join(sorted(g)) + "}" for g in groups]
            violations.append(
                RuleViolation(
                    code="require_any_missing",
                    message=f"Requires Any verletzt: '{trigger}' braucht mindestens eine Gruppe aus {pretty_groups}. {reason}",
                    details={
                        "trigger": trigger,
                        "groups": " OR ".join(pretty_groups),
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


def gate_allows_candidate(
    *,
    kind: str,
    candidate_tags: Set[str],
    active_tags: Set[str],
) -> Tuple[bool, Optional[RuleViolation]]:
    """
    Gate Check für einen Kandidaten eines bestimmten kind.

    Logik:
    - Wenn Kandidat gate_tag besitzt, müssen required_active_tags schon aktiv sein.
    - Das ist ein Vorfilter für Random Picks.

    Beispiel
    candidate_tags enthält wind
    dann muss active_tags skirt enthalten, sonst blocken wir diesen Kandidaten.

    Adult Gates
    - Wenn ENFORCE_ADULT_TAG False ist, ignorieren wir Gates, die adult als Voraussetzung haben.
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
    Wenn candidate_tags zusammen mit active_tags schon eine Excludes Regel verletzen würden,
    dann ist der Kandidat für diesen Build nicht geeignet.

    Hinweis
    Dieser Check ist absichtlich nur EXCLUDES.
    REQUIRES und REQUIRES_ANY prüfen wir global nach dem Pick über validate_selection,
    oder wir bilden zusätzliche Gates, wenn wir es noch effizienter machen wollen.
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

    Rückgabe:
    - allowed: Kandidaten, die aktuell wählbar sind
    - reasons: Gründe, warum Kandidaten geblockt wurden

    Zweck:
    - Weniger Reject Looping
    - Bessere Debugbarkeit, weil man sehen kann, warum Kandidaten rausfliegen
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
    Das ist ideal für UI, Logs oder Fehlermeldungen im Generator.

    Beispiel Ausgabe:
    exclude: Excludes verletzt: 'school' mit 'lewd'. Schul Kontext und lewd Inhalte werden hart getrennt.
    """
    if not violations:
        return "Keine Regelverletzungen."
    return "\n".join([f"{v.code}: {v.message}" for v in violations])