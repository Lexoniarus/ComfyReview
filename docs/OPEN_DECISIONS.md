# Aktueller Status und offene Entscheidungen

**Dokumentklasse:** `OPEN` – noch ungeklärte Entscheidungen, keine zugewiesenen Meilensteine.

**Stand:** 2026-10-09. Diese Liste ist **kein Zeitplan** und kein von importierten Konzepten abgeleiteter Implementierungsauftrag.

**Bereits bestätigte Vorgaben** stehen ausdrücklich in den
[scopebezogenen Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md). Hier bleiben
**nur die noch offenen Entscheidungen und Implementierungsfragen**. So ist
das gemeinsame externe KI-API-Monatsbudget von **unter 10 €** bestätigt;
dessen technische Durchsetzung einschließlich eines möglichen App-Stopps
bei ungefähr 8 € **noch nicht** beschlossen oder als eingebaut belegt.

## Bestehende ComfyReview-Entwicklung

**ComfyReview wird aktiv weiterentwickelt.** Der Code vor dem Dokumentenimport ([`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32)) enthält FastAPI, SQLite Schema v18 **als Codevertrag**, Frontend V2, Review/Ranking/Arena/Curation, Playground, Prompt-/LoRA-Katalog, Analytics und ComfyUI-Generator. [Codebelege](IMPLEMENTATION_AUDIT.md).

**Gegenwärtige Arbeitsbereiche** (Nutzerstand, 2026-10-09):

- **Card Battler wird aktiv als POC entwickelt.** Technische Materialisierungs-/Entwicklungsbausteine und Tests liegen bereits im Repository, aber keine fertige spielbare Match-/Deck-UI. [POC-Status](pocs/card-battler.md).
- **Generator wurde jüngst überarbeitet.** Blueprint v4, Compiler, Lifecycle und API sind im Code vorhanden; zusätzliche Funktionserprobung und Verbesserungen bleiben möglich.
- **Datenbank/Katalog werden noch optimiert.** Schema v18, Audit- und Rebuild-Kommandos existieren; reale Katalogbereinigung, Rehearsal, Datenbank-Cutover und operative Akzeptanz dürfen ohne persönliche Artefakte nicht als abgeschlossen gemeldet werden.

Die [CI für die Codebaseline](https://github.com/Lexoniarus/ComfyReview/actions/runs/37769483557) war erfolgreich. CI-Belege ersetzen nicht die laufende Entwicklung oder reale Bedien-/Datenabnahme.

## Langfristige Richtung

ComfyReview **soll sich langfristig zu Character Chronicles entwickeln**. Die [Concept-Dokumente](character-chronicles/README.md) geben dafür inhaltliche Ideen: Welt, Story, Characters, Trials, Karten, visuelle Produktion, Sozialsysteme, Academy und New Game Plus. **Ob** und **wie** die vorgeschlagenen technischen Architekturen und Abläufe umgesetzt werden, muss sich erst in POCs und Entscheidungen zeigen.

Ein **früherer Character-Chronicles-Entwicklungsstand wurde wegen einer
unpassenden Richtung verworfen**. Der zugehörige Code liegt inzwischen
**als `CharacterChronicle.zip` vor und wurde statisch untersucht**:
alte Campaign-, Trial-, M6- und Worker-Implementierungen, Vite-/TypeScript-
Frontend und SQLite v58 waren tatsächlich im damaligen Arbeitsordner.
Die alten Acceptance-Texte kennzeichnen aber Live-/Zwei-Zyklen-Nachweise
weiterhin als **offen**.
[Historischer Code-Audit](character-chronicles/HISTORICAL_CODE_AUDIT.md).

Der alte Ansatz ist **Beweismaterial für getroffene und verworfene Entscheidungen**,
kein technischer Neubauauftrag. Dass etwas früher implementiert wurde,
macht es nicht automatisch zur passenden künftigen Architektur.

## Entwicklungspriorität – vom Projektinhaber klargestellt

Die über die POCs gewonnene **grobe Reihenfolge** ist nicht mehr
beliebig: **Card Battler → Social Network mit Timeline/Charakter-Chats →
Academy-/Schuljahresmechaniken → visuelle VN zuletzt**.
Social Network und Schuljahr dürfen sich in der Umsetzung überlappen.

**Begründung:** Der frühere Character-Chronicle-Code entstand, bevor
Card Battler, Worldbuilding und Academy als zusammenhängende Spielidee
konkret waren. Die visuelle VN bringt mit Figurenfreistellung und
Szenenkomposition zusätzliche technische Unsicherheiten mit sich und
soll deshalb **nicht** vor die tragfähige Gameplay-/Social-Basis gezogen
werden. Ein isolierter früher Techniktest solcher Risiken ist damit
nicht ausgeschlossen.

Diese Orientierung beschreibt **priorisierte Produktabhängigkeiten**,
nicht bereits beschlossene Arbeitspakete, Schemata, Termine,
Meilenstein-Gates oder endgültige Spielregeln.
[Begründung und Abgrenzung](PROJECT_EVOLUTION.md#gewonnene-reihenfolge-aus-den-bisherigen-versuchen).

## Entscheidungen, die bewusst offen bleiben

| Frage | Aktuelle Regel |
| --- | --- |
| Welche bisherigen ComfyReview-Komponenten bleiben auf dem Weg zu Character Chronicles erhalten? | Nach Bedarf und POC-Ergebnis entscheiden, nicht automatisch alles migrieren |
| Wie wird der Card Battler spielerseitig integriert? | **Aktiver POC**, keine voreilig festgeschriebene Architektursequenz |
| Wie wird die bereits beschlossene gemeinsame KI-API-Budgetobergrenze technisch eingehalten? | Geltung **unter 10 € im Monat** für Entwicklungs- und App-Aufrufe bestätigt; Erfassung, mögliche ca. 8-€-Sperre, Providerlimits und Aufrufe außerhalb der App sind noch **technische/operative Kandidaten**, kein nachgewiesener Schutz |
| Welche Teile der alten Card-Battler-Pläne passen noch? | Historische Ideen prüfen; alte „approved“-Markierungen übertragen keine aktuelle Autorität |
| Wie wird der Generator/Katalog zur weiteren Produktentwicklung genutzt? | Aktuellen Code und reales Datenmodell nachziehen; Cutover/Optimierung getrennt validieren |
| Welche früheren Character-Chronicles-Schemata/Orchestrierungen werden verworfen, ersetzt oder neu erprobt? | **Nicht** aus alten Texten importieren; POCs und aktuelles Zielbild maßgeblich |
| Was ist die exakte MVP-Grenze, Umsetzungsetappen- und Milestone-Reihenfolge? | Die **grobe Priorität** Card Battler → Social/Chats → Schuljahr → visuelle VN zuletzt ist klar; **exakte Meilensteine, Umfang, Abnahmen und technische Umsetzung bleiben offen** |
| Welche Inhalte der 24 Dokumente sind künftig verpflichtend? | Inhaltliche Sichtung und ausdrücklich begrenzte Entscheidungen nötig |

Nicht jeder offene Punkt muss sofort entschieden werden. Ein POC kann bewusst mehrere Optionen erproben oder ganz verworfen werden.

[Gesamtrichtung](PROJECT_EVOLUTION.md) · [aktive Arbeit](ACTIVE_WORK.md) · [Entscheidungsregeln](DECISION_POLICY.md).
