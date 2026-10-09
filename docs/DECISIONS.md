# Entscheidungen des ComfyReview-/Character-Chronicles-Neustarts

**Dokumentrolle:** aktives Entscheidungsregister · **Status:** IMPLEMENTED (Register)
**Geltungsbereich:** Produktgrenzen und Entwicklungsreihenfolge ab 2026-10-09
**Hinweis:** Nur ausdrücklich erfasste Entscheidungen sind aktuell verbindlich. Die historischen DEC-/PM-/M-Signaturen aus dem [alten Character-Chronicles-Archiv](archive/character-chronicles-v1/README.md) besitzen hier **keine Gültigkeit**.

## Status von Entscheidungen

- **ACTIVE:** ausdrücklich bestätigt; gilt nur für die angegebene Ebene und Phase.
- **OPEN:** wichtige Frage ohne endgültige Festlegung; keine implizite Default-Entscheidung.
- **SUPERSEDED:** durch eine neu benannte Entscheidung ersetzt; Historie bleibt.
- **REJECTED:** ausdrücklich nicht weiterverfolgt; nicht ohne neue Entscheidung reaktivieren.

## Aktive Entscheidungen

| ID | Datum | Status | Entscheidung und Geltung |
| --- | --- | --- | --- |
| **CRCC-001** | 2026-10-09 | ACTIVE | ComfyReview ist die bestehende Implementierungsbasis und wird **schrittweise zu Character Chronicles weiterentwickelt**. Ein separates Übergabeprojekt, eine komplette Neuentwicklung oder ein Repository-Split werden damit **nicht** festgelegt. |
| **CRCC-002** | 2026-10-09 | ACTIVE | Die beabsichtigte Phasenreihenfolge ist **Card Battler → Timeline → Social Network einschließlich Chat-Interaktion → Storyline → VN-Content**. Der laufende ComfyReview-Refactor ist die vorgelagerte technische Ausgangsbasis. Detaillierter Scope und Termine sind nicht beschlossen. |
| **CRCC-003** | 2026-10-09 | ACTIVE | Der frühere Character-Chronicles-Entwicklungsversuch ist **verworfen**. Alle zugehörigen Verträge werden im Archiv bewahrt, nicht als aktuelle Anforderungen ausgeführt. Jede Wiederverwendung benötigt eine neue, explizite Entscheidung, auch wenn der alte Text „DECIDED“, „MVP“, „Autorität“ oder „implementiert“ behauptet. |
| **CRCC-004** | 2026-10-09 | ACTIVE | Auf dem Entwicklungsweg folgen weitere POCs und Entscheidungen. Ungeklärte Details bleiben ausdrücklich OPEN. Ein POC liefert Evidenz, aber genehmigt seine eigene Produktionsübernahme nicht. |
| **CRCC-005** | 2026-10-09 | ACTIVE | Die **eigentliche VN-Content-Entwicklung steht am Ende**. Technische Vorbereitungen davor sind nur als ausdrücklich begründete Schnittstellen-/POC-Arbeit zulässig, nicht als vorgezogene VN-Content-Phase. |
| **CRCC-006** | 2026-10-09 | ACTIVE (bestehender beschränkter Zielvertrag) | Der [ComfyReview Card-Battler-Zielvertrag](CARD_BATTLER_TARGET.md) ist die Arbeitsgrundlage **für Phase 1**, nicht das komplette alte Character-Chronicles-Kartenspiel. Er wird entlang von Implementierung, POC-Ergebnissen und neuen Entscheidungen kalibriert. Seine offen gelassenen Regelparameter bleiben offen. |

**Quelle CRCC-001 bis CRCC-005:** explizite aktuelle Produktausrichtung des Projektverantwortlichen beim Dokumentationsneustart. **Quelle CRCC-006:** bereits dokumentierte aktive ComfyReview-Card-Battler-Zielgrenze; durch den Neustart in die Phasenroadmap eingeordnet.

## Offene Entscheidungen (keine Implementierungsfreigabe)

| ID | Status | Frage | Nächster Nachweis |
| --- | --- | --- | --- |
| **OPEN-001** | OPEN | Card-Battler-Deckgröße, Board-/Turnregeln, OpCodes, Balance, Legendary und Art-Pipeline für den ersten spielbaren Prototyp? | begrenzte POCs und revisionsgebundene Rules-Entscheidung; siehe [Card-Battler-Ziel](CARD_BATTLER_TARGET.md) |
| **OPEN-002** | OPEN | Was genau bedeutet „Timeline“ für Spieleraktionen, Datenmodell und Darstellung in Phase 2? | Scope-Entwurf und POC |
| **OPEN-003** | OPEN | Welche Social-Network- und Chat-Funktionen sind für Phase 3 notwendig und welche Persistenz-/Moderationsgrenzen gelten? | Scope- und Interaktionsprototyp |
| **OPEN-004** | OPEN | Wie werden Storyline, Entscheidungen und Zustandsübergänge für Phase 4 modelliert? | gesonderter Story-State-Prototyp |
| **OPEN-005** | OPEN | Welche VN-Assets, Content-Produktionswege, Ausspiel-/Lokalisierungsmechanismen sind für Phase 5 nötig? | erst phasengerecht entscheiden |
| **OPEN-006** | OPEN | Produktname, Deployment, eventuelle zusätzliche Module oder spätere Abspaltung? | gesonderte Architekturentscheidung; kein automatischer „Reuse in other repository“-Schritt |

## Entscheidungsprozess

1. **Frage/Alternativen** eingrenzen, bestehende technische Grenze und relevante frühere Quelle nennen.
2. **Belege** sammeln (POC, Tests, UX-Feedback); Unterschiede zwischen IST, Annahme und Vorschlag markieren.
3. **Entscheidung** als neue CRCC-ID mit Datum, Geltungsbereich, Status, Begründung und Auswirkungen eintragen.
4. **Zielvertrag** nur danach aktualisieren; alte Archivtexte bleiben unverändert.
5. **Änderungen** über SUPERSEDED mit Verweis nachvollziehbar halten; nicht still ersetzen.

Ein Archivdokument wird nie durch bloßes Verlinken oder Kopieren seiner Statusformulierung wieder gültig. Geltung entsteht allein durch eine neue Entscheidung plus aktualisierten aktiven Zielvertrag.
