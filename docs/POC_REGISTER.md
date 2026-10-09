# POC- und offene-Fragen-Register

**Dokumentrolle:** Register künftiger Experimente · **Status:** PROPOSED
**Geltungsbereich:** neue Phasen gemäß [Roadmap](ROADMAP.md) · **Stand:** 2026-10-09

## Zweck

Ein **Proof of Concept (POC)** prüft eine Hypothese und gibt Entscheidungsevidenz. Er ist **weder eine freigegebene Produktfunktion noch ein Architekturvertrag**, selbst wenn seine Tests erfolgreich sind. Erst eine neue [Entscheidung](DECISIONS.md) macht ein Ergebnis verbindlich.

**Statusvokabular für Experimente:** CANDIDATE (noch nicht beauftragt), PLANNED, IN_PROGRESS, VALIDATED, FAILED, CLOSED. Alle unten genannten Vorschläge sind zurzeit **CANDIDATE** – es werden keine Resultate behauptet.

## Kandidaten nach Phasen

| POC-ID | Phase | Prüffrage / Hypothese | Möglicher Nachweis | Status |
| --- | --- | --- | --- | --- |
| **POC-001** | 1 Card Battler | Lässt sich der minimale serverautoritativ-deterministische Spielkern mit stabilen Card-/Deck-Revisionen nachvollziehbar spielen und replayen? | reproduzierbare Match-Tests, illegal/stale command und Replay-Nachweis | CANDIDATE |
| **POC-002** | 1 Card Battler | Welche Kartenkunst-/Darstellungspipeline ist bedienbar und mit den aktuellen Bildern vereinbar? | interaktiver Prototyp, deterministischer Render-Beleg und UX-Abnahme | CANDIDATE |
| **POC-003** | 2 Timeline | Welcher Timeline-Begriff und welcher zeitliche Zustand ergeben tatsächlich den gewünschten Spielnutzen? | testbarer Interaktions-/Datenprototyp nach Scope-Klärung | CANDIDATE |
| **POC-004** | 3 Social + Chat | Wie müssen Posts, Chat-Interaktionen und zuständige State-/Providergrenzen zusammenspielen? | Vertical Slice, persistente Zustandsübergänge, Fehler- und Recovery-Fälle | CANDIDATE |
| **POC-005** | 4 Storyline | Wie können Storyentscheidungen deterministisch versioniert und in die vorherigen Phasen integriert werden? | Story-State-Slice mit Reproduzierbarkeit und Rückwirkungstests | CANDIDATE |
| **POC-006** | 5 VN-Content | Welche VN-Asset- und Content-Ausspielpipeline erfüllt die spätere UX? | eigener Inhalts-/Asset-Prototyp; **kein vorgezogener Content-Commit** | CANDIDATE |

## Pflichtformular für einen tatsächlich gestarteten POC

Beim Start eines POCs einen Eintrag oder verlinktes Einzelblatt mit diesen Feldern erstellen:

- **Owner / Datum / Phase** und konkrete nicht zu überschreitende Scope-Grenze
- **Hypothese, Alternativen, überprüfbare Erfolgskriterien und Risiken**
- **Versuchsaufbau und reproduzierbarer Test-/UI-Nachweis**
- **Ergebnis:** Beobachtung getrennt von Interpretation; auch Fehlschläge festhalten
- **Entscheidung danach:** CRCC-ID oder explizit „weiter OPEN“; keine stillschweigende Produktionsübernahme
- **Rückbau / Integration:** temporäre Prototypen dürfen keine zweite persistente Wahrheit schaffen

Weitere, im Verlauf entstandene POCs sind ausdrücklich erwartet; dieses Register ist **keine vollständige Featureliste** und keine Terminplanung.
