from __future__ import annotations

from typing import Set


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

    Wie
    Wir leiten sehr wenige, sehr stabile Tags aus Textfeldern ab:
    key, name, pos, notes.

    Aktuelle Heuristiken (passend zu euren Daten):

    skirt
      Wenn irgendwo "skirt" vorkommt, setzen wir "skirt".

    adult_only
      Wenn notes "Character must be adult" enthalten, setzen wir "adult_only".

    lewd
      Wenn irgendwo "lewd" vorkommt, setzen wir "lewd".

    pool
      Wenn irgendwo "pool" vorkommt, setzen wir "pool".

    water_proxy
      Wenn irgendwo "beach" oder "pool" vorkommt, setzen wir "water_proxy".
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
    """
    base = parse_tags_csv(tags)
    derived = derive_tags_for_item(kind=kind, key=key, name=name, pos=pos, neg=neg, notes=notes)
    return base | derived
