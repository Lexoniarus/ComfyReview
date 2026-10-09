# Offene Entscheidungen – ComfyReview → Character Chronicles

**Dokumentklasse:** `OPEN` – noch ungeklärte Entscheidungen, keine zugewiesenen Meilensteine.

**Stand:** 2026-10-09. Diese Liste ist **kein Zeitplan** und kein von importierten Konzepten abgeleiteter Implementierungsauftrag.

**Bereits bestätigte Vorgaben** stehen ausdrücklich in den
[scopebezogenen Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md). Hier bleiben
**nur die noch offenen Entscheidungen und Implementierungsfragen**. So ist
das gemeinsame externe KI-API-Monatsbudget von **unter 10 €** bestätigt;
dessen technische Durchsetzung einschließlich eines möglichen App-Stopps
bei ungefähr 8 € **noch nicht** beschlossen oder als eingebaut belegt.

## Zuständigkeit und Kontext (keine zweite Statusübersicht)

Dieses Dokument enthält **nur noch offene Entscheidungen und offene technische
Umsetzungen**. Es ist weder Implementierungs-Audit noch Arbeitsstatus,
verbindlicher Produktvertrag, Betriebsanleitung oder historisches Protokoll:

- **Nachgewiesener Code und aktuelle Abnahmen:** [Projektstatus](project_status.md)
  und [Implementation Audit](IMPLEMENTATION_AUDIT.md).
- **Gerade laufende Arbeit:** [Active Work](ACTIVE_WORK.md) und
  [Card-Battler-POC](pocs/card-battler.md). Dort ist der konkrete erste
  Kartenablauf einschließlich 40-Karten-Testziel dokumentiert, ohne
  abgeschlossene Spielfunktion zu behaupten.
- **Entwicklungspriorität und langfristige Vision:**
  [Project Evolution](PROJECT_EVOLUTION.md) und
  [Character Chronicles](character-chronicles/vision/README.md). Die grobe
  Orientierung **Card Battler → Timeline → Social Network mit Chat →
  Storyline → VN-Content zuletzt** ist geklärt; Academy/Schuljahr bleibt
  ein möglicher Story-/Weltkontext, **keine zusätzliche Pflichtphase**.
  Detailmeilensteine und Technik sind nicht festgelegt.
- **Bestätigte Vorgaben:** [Confirmed Constraints](CONFIRMED_CONSTRAINTS.md).
  Das **gemeinsame KI-API-Monatsbudget unter 10 €** ist bestätigt;
  konkrete Messung und etwaige ~8-€-Sperre sind weiter offen.
- **Verworfener früherer Chronicle-Code:**
  [historischer Code-Audit](character-chronicles/HISTORICAL_CODE_AUDIT.md).
  Seine Architektur ist kein neuer Implementierungsauftrag.

Eine bestätigte Vorgabe bleibt in ihrem benannten Scope verbindlich,
selbst wenn **ihre technische Umsetzung** in der folgenden Tabelle offen ist.
Alte `DECIDED`-Formulierungen in importierten Quellen sind dagegen
**nicht** automatisch bestätigte Vorgaben.

## Entscheidungen, die bewusst offen bleiben

| Frage | Aktuelle Regel |
| --- | --- |
| Welche bisherigen ComfyReview-Komponenten bleiben auf dem Weg zu Character Chronicles erhalten? | Nach Bedarf und POC-Ergebnis entscheiden, nicht automatisch alles migrieren |
| Wie wird der Card Battler spielerseitig integriert? | **Aktiver POC**, keine voreilig festgeschriebene Architektursequenz |
| Was ist die erste **Timeline**-Funktion, bevor die größere Social-Plattform entsteht? | Nutzerablauf, Inhalte und Persistenz noch im POC eingrenzen; **kein** verpflichtender unabhängiger Release |
| Welche **Social-Network- und Chat-Interaktionen** sollen auf den Timeline-Slice folgen? | Figureninteraktion, Kontext und technische LLM-/Daten-Grenzen offen; alte Network-Verträge sind nicht übernommen |
| Wie wird die **Storyline** aufgebaut und welche Rolle spielt Academy/Schuljahr? | Ereignisse, Figuren, Entscheidungen und Progression werden neu geprüft; kein altes zweijähriges Campaign-Schema als Pflicht |
| Wie wird die bereits beschlossene gemeinsame KI-API-Budgetobergrenze technisch eingehalten? | Geltung **unter 10 € im Monat** für Entwicklungs- und App-Aufrufe bestätigt; Erfassung, mögliche ca. 8-€-Sperre, Providerlimits und Aufrufe außerhalb der App sind noch **technische/operative Kandidaten**, kein nachgewiesener Schutz |
| Welche Teile der alten Card-Battler-Pläne passen noch? | Historische Ideen prüfen; alte „approved“-Markierungen übertragen keine aktuelle Autorität |
| Wie wird der Generator/Katalog zur weiteren Produktentwicklung genutzt? | Aktuellen Code und reales Datenmodell nachziehen; Cutover/Optimierung getrennt validieren |
| Welche früheren Character-Chronicles-Schemata/Orchestrierungen werden verworfen, ersetzt oder neu erprobt? | **Nicht** aus alten Texten importieren; POCs und aktuelles Zielbild maßgeblich |
| Was ist die exakte MVP-Grenze, Umsetzungsetappen- und Milestone-Reihenfolge? | Die **ungefähre Priorität** Card Battler → Timeline → Social Network mit Chat → Storyline → VN-Content zuletzt ist klar; **exakte Meilensteine, Umfang, Abnahmen und technische Umsetzung bleiben offen**. Academy/Schuljahr ist möglicher Storykontext, kein fixiertes Extra-Gate |
| Welche Inhalte der 24 Dokumente sind künftig verpflichtend? | Inhaltliche Sichtung und ausdrücklich begrenzte Entscheidungen nötig |

Nicht jeder offene Punkt muss sofort entschieden werden. Ein POC kann bewusst mehrere Optionen erproben oder ganz verworfen werden.

[Gesamtrichtung](PROJECT_EVOLUTION.md) · [aktive Arbeit](ACTIVE_WORK.md) · [Entscheidungsregeln](DECISION_POLICY.md).
