"""
services/playground_generator.py

Playground Generator Service
============================

Ziel
Diese Datei erzeugt aus Playground Items (DB Einträge) eine gültige Kombination und daraus
einen finalen positiven und negativen Prompt.

Wichtig
Diese Datei ist Business Logik, nicht UI und nicht DB Schema.

Abhängigkeiten
1) services.playground_rules.py
   Enthält die komplette Regel Logik:
   - EXCLUDES
   - REQUIRES
   - REQUIRES_ANY
   - GATES
   plus Helper:
   - get_effective_tags(...)   DB Tags plus Derived Tags
   - filter_candidates(...)    Vorfilter für Random Kandidaten (Gates plus Excludes)
   - validate_selection(...)   finale Gesamtvalidierung

2) stores.playground_store.py
   Enthält DB Zugriff. Liefert Items als Dicts.
   Diese Datei bleibt reiner DB Layer und importiert nichts aus services.
   Deshalb arbeitet der Generator hier direkt mit den Store Funktionen und einem db_path.

Grundannahmen
- Ein Item ist ein kompletter Block.
  Scene ist komplett, Outfit ist komplett, Pose ist komplett, Expression ist komplett, Lighting komplett, Modifier komplett.

- Der Generator wählt pro Slot genau einen Block (oder überspringt Slot).
  Reihenfolge ist fest:
  character -> scene -> outfit -> pose -> expression -> lighting optional -> modifier optional

Warum Reihenfolge
- Gates und Rules hängen daran, dass bestimmte Tags schon aktiv sind.
  Beispiel:
  wind Modifier soll nur auswählbar sein, wenn skirt bereits aktiv ist.
  Das klappt nur, wenn Outfit vor Modifier gewählt wird.

Manual Picks vs Random Picks
- Character ist Pflicht und immer manuell (Dropdown)
- Alle anderen Slots können manuell oder random sein
- Manuelle Auswahl wird nicht vorab weggefiltert.
  Wenn sie unzulässig ist, soll man das als klare Regelverletzung sehen.
  Das ist besser für UI als stillschweigend anders zu picken.

Debugbarkeit
- Bei jedem Attempt wird Debug gesammelt.
- Wenn keine gültige Kombination gefunden wird, kann der Router diesen Debug ausgeben.

Prompt Join Regel
- pos und neg werden als vollständige Blöcke kombiniert.
- Trennung erfolgt durch Komma, weil ihr Tokens so pflegt.
"""

from __future__ import annotations

import random
from typing import Any, Dict, List, Optional, Set, Tuple

from services.playground_rules import (
    DEFAULT_MAX_TRIES,
    RuleViolation,
    explain_violations,
    filter_candidates,
    get_effective_tags,
    validate_selection,
)

from stores.playground_store import (
    get_item_by_id,
    get_items_by_kind,
)


ItemDict = Dict[str, Any]
SelectionDict = Dict[str, ItemDict]


# ============================================================================
# Helper: effektive Tags für ein Item Dict
# ============================================================================

def effective_tags(item: ItemDict) -> Set[str]:
    """
    Ermittelt effektive Tags für ein Item.

    Effektive Tags = DB tags plus Derived Tags

    Erwartete Felder im Dict:
    - kind
    - key
    - name
    - tags
    - pos
    - neg
    - notes
    """
    return get_effective_tags(
        kind=str(item.get("kind", "") or ""),
        key=str(item.get("key", "") or ""),
        name=str(item.get("name", "") or ""),
        tags=str(item.get("tags", "") or ""),
        pos=str(item.get("pos", "") or ""),
        neg=str(item.get("neg", "") or ""),
        notes=str(item.get("notes", "") or ""),
    )


# ============================================================================
# Helper: Prompt Join (Komma getrennt)
# ============================================================================

def _join_prompt_blocks(blocks: List[str]) -> str:
    """
    Vereinheitlicht das Join Verhalten.

    Vorgabe aus eurem System:
    - Tokens sind comma separated
    - Wir joinen komplette Blöcke ebenfalls mit Komma

    Hinweis
    Ein Block kann selbst schon Kommas enthalten, weil er aus Tokens besteht.
    Das ist ok, wir hängen nur einen weiteren Block an.
    """
    cleaned = [b.strip() for b in blocks if str(b or "").strip()]
    return ", ".join(cleaned)


def build_prompts(selection: SelectionDict) -> Dict[str, str]:
    """
    Baut finalen Output aus der Auswahl.

    Ergebnis:
    - positive: pos Blöcke in definierter Reihenfolge, per Komma verbunden
    - negative: neg Blöcke in definierter Reihenfolge, per Komma verbunden
    - notes: notes als Lesetext, getrennt mit " | "
    """
    order = ["character", "scene", "outfit", "pose", "expression", "lighting", "modifier"]

    pos_blocks: List[str] = []
    neg_blocks: List[str] = []
    notes_blocks: List[str] = []

    for kind in order:
        item = selection.get(kind)
        if not item:
            continue

        pos = str(item.get("pos", "") or "").strip()
        neg = str(item.get("neg", "") or "").strip()
        notes = str(item.get("notes", "") or "").strip()

        if pos:
            pos_blocks.append(pos)
        if neg:
            neg_blocks.append(neg)
        if notes:
            notes_blocks.append(notes)

    return {
        "positive": _join_prompt_blocks(pos_blocks),
        "negative": _join_prompt_blocks(neg_blocks),
        "notes": " | ".join([n for n in notes_blocks if n]),
    }


# ============================================================================
# Generator
# ============================================================================

class PlaygroundGenerator:
    """
    Generator Klasse

    Konstruktion
    - db_path wird übergeben, weil der Store so arbeitet.
    - Kein store Objekt erforderlich.

    ORDER
    - Reihenfolge der Slots
    - Diese Reihenfolge ist auch die Reihenfolge im Output
    """
    ORDER = ["character", "scene", "outfit", "pose", "expression", "lighting", "modifier"]

    def __init__(self, db_path):
        self.db_path = db_path

    def generate(
        self,
        *,
        character_id: int,
        manual_picks: Dict[str, Optional[int]],
        include_lighting: bool = True,
        include_modifier: bool = True,
        seed: Optional[int] = None,
        max_tries: int = DEFAULT_MAX_TRIES,
    ) -> Dict[str, Any]:
        """
        Erzeugt eine gültige Kombination.

        Parameter
        character_id
          Pflicht. Muss auf kind=character zeigen.

        manual_picks
          Pro Slot optional eine ID.
          None bedeutet random.

          Beispiel:
          {
            "scene": None,
            "outfit": 123,
            "pose": None,
            "expression": None,
            "lighting": None,
            "modifier": None
          }

        include_lighting
          Wenn False, wird lighting komplett übersprungen.

        include_modifier
          Wenn False, wird modifier komplett übersprungen.

        seed
          Optional. Reproduzierbare Random Auswahl.

        max_tries
          Wie oft wir versuchen eine gültige Kombination zu finden.
          Wenn Rules eng sind, braucht es mehrere attempts.

        Rückgabe
        {
          "selection": {kind: item_dict},
          "active_tags": [...],
          "positive": "...",
          "negative": "...",
          "notes": "...",
          "debug": {...}
        }

        Fehler
        RuntimeError wenn keine gültige Kombination gefunden wird.
        """
        rng = random.Random(seed)

        last_debug: Dict[str, Any] = {}

        for attempt in range(int(max_tries)):
            debug: Dict[str, Any] = {
                "attempt": attempt + 1,
                "max_tries": int(max_tries),
                "seed": seed,
                "reject_reason": "",
                "slot_debug": {},
                "violations_text": "",
            }

            selection: SelectionDict = {}

            # Slot 1: Character ist Pflicht und fix
            char_item = get_item_by_id(self.db_path, int(character_id))
            if not char_item:
                raise ValueError(f"character_id nicht gefunden: {character_id}")

            if str(char_item.get("kind", "")) != "character":
                raise ValueError(f"character_id ist kein character: id={character_id}")

            selection["character"] = char_item
            active_tags: Set[str] = set(effective_tags(char_item))

            # Slots 2..n: der Reihe nach
            for kind in self.ORDER[1:]:
                if kind == "lighting" and not include_lighting:
                    continue
                if kind == "modifier" and not include_modifier:
                    continue

                item, slot_info = self._pick_slot(
                    rng=rng,
                    kind=kind,
                    manual_id=manual_picks.get(kind),
                    active_tags=active_tags,
                )

                debug["slot_debug"][kind] = slot_info

                if item is None:
                    debug["reject_reason"] = f"no_candidates_for_{kind}"
                    break

                selection[kind] = item
                active_tags |= effective_tags(item)

            # Wenn Slot Loop abgebrochen wurde, nächster attempt
            if debug["reject_reason"]:
                last_debug = debug
                continue

            # Finale Regelprüfung für die komplette Auswahl
            violations = validate_selection(active_tags)
            if violations:
                debug["reject_reason"] = "final_validation_failed"
                debug["violations"] = [v.__dict__ for v in violations]
                debug["violations_text"] = explain_violations(violations)
                debug["active_tags"] = sorted(active_tags)
                last_debug = debug
                continue

            # Erfolg, Output bauen
            out = build_prompts(selection)
            debug["active_tags"] = sorted(active_tags)

            return {
                "selection": selection,
                "active_tags": sorted(active_tags),
                "positive": out["positive"],
                "negative": out["negative"],
                "notes": out["notes"],
                "debug": debug,
            }

        raise RuntimeError(
            "Keine gültige Kombination nach max_tries Versuchen gefunden. "
            f"Letzter Debug Stand: {last_debug}"
        )

    # ------------------------------------------------------------------------
    # Slot Pick
    # ------------------------------------------------------------------------

    def _pick_slot(
        self,
        *,
        rng: random.Random,
        kind: str,
        manual_id: Optional[int],
        active_tags: Set[str],
    ) -> Tuple[Optional[ItemDict], Dict[str, Any]]:
        """
        Pick Logik für einen Slot.

        Manual Pick
        - Wenn manual_id gesetzt ist, laden wir dieses Item.
        - Wir filtern es nicht mit Gates.
          Grund: UI soll sehen können, dass manuelle Kombinationen unzulässig sind,
          statt dass der Generator heimlich etwas anderes nimmt.

        Random Pick
        - Wir laden alle Kandidaten dieses kind aus der DB.
        - Dann Vorfilter über filter_candidates:
          Gates und Excludes werden angewandt.
        - Dann zufällige Auswahl aus allowed.

        Rückgabe
        item oder None
        slot_debug enthält Zahlen und einen kurzen Grund, falls nichts geht.
        """
        slot_debug: Dict[str, Any] = {
            "kind": kind,
            "manual": bool(manual_id),
            "manual_id": int(manual_id) if manual_id else None,
            "candidates_total": 0,
            "candidates_allowed": 0,
            "chosen_id": None,
            "chosen_name": None,
            "filtered_reasons_sample": [],
        }

        if manual_id:
            item = get_item_by_id(self.db_path, int(manual_id))
            if not item:
                raise ValueError(f"manual pick nicht gefunden: kind={kind} id={manual_id}")

            if str(item.get("kind", "")) != kind:
                raise ValueError(
                    f"manual pick kind mismatch: slot={kind} item.kind={item.get('kind')} id={manual_id}"
                )

            slot_debug["chosen_id"] = int(item.get("id"))
            slot_debug["chosen_name"] = str(item.get("name", "") or "")
            return item, slot_debug

        candidates = get_items_by_kind(self.db_path, kind)
        slot_debug["candidates_total"] = len(candidates)

        allowed, reasons = filter_candidates(
            kind=kind,
            candidates=candidates,
            get_tags=lambda it: effective_tags(it),
            active_tags=active_tags,
        )

        slot_debug["candidates_allowed"] = len(allowed)

        if reasons:
            slot_debug["filtered_reasons_sample"] = [r.__dict__ for r in reasons[:10]]

        if not allowed:
            return None, slot_debug

        chosen = rng.choice(allowed)
        slot_debug["chosen_id"] = int(chosen.get("id"))
        slot_debug["chosen_name"] = str(chosen.get("name", "") or "")

        return chosen, slot_debug