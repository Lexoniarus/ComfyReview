# Dokumentation: gültiger Stand und Orientierung

**Status:** IMPLEMENTED (Dokumentationsindex) · **Stand:** 2026-10-09
**Geltungsbereich:** Repository ComfyReview, Branch `refactor/review-boundary` und seine künftige Evolution.

## In einem Absatz

**ComfyReview ist der aktuelle lokale Bildgenerierungs-, Review- und Curation-Bestand.** Diese Codebasis soll schrittweise **zu Character Chronicles weiterentwickelt** werden, nicht automatisch an ein getrenntes Spielprojekt übergeben werden. Die Reihenfolge lautet: **Card Battler → Timeline → Social Network mit Chat-Interaktion → Storyline → Visual-Novel-Content**. Die Reihenfolge ist die aktuelle Produktabsicht; Umfang und Umsetzung einzelner Stufen werden erst durch neue Entscheidungen, POCs und Abnahmen festgelegt. **Der frühere Character-Chronicles-Entwicklungsversuch wurde verworfen.** Seine Dokumente sind nur historisches Material und keine aktuell gültige Implementierungsspezifikation.

## Hier anfangen

| Frage | Maßgebliche Quelle |
| --- | --- |
| Was kann ComfyReview heute tatsächlich? | [Projektstatus](project_status.md), [Root-README](../README.md) und ausführbarer Code/Tests |
| Welche Entwicklungs- und Architekturregeln gelten? | [AGENTS.md](../AGENTS.md), [Architektur](ARCHITECTURE.md), [Datenarchitektur](DATA_ARCHITECTURE.md), [Coding Standards](CODING_STANDARDS.md) |
| Was ist die langfristige Produktreihenfolge? | [Roadmap](ROADMAP.md) |
| Welche Entscheidungen sind für den Neustart ausdrücklich bestätigt? | [Entscheidungsregister](DECISIONS.md) |
| Was ist offen und muss experimentell geprüft werden? | [POC-Register](POC_REGISTER.md) |
| Was ist das erste konkrete Ausbauziel? | [Card-Battler-Zielvertrag](CARD_BATTLER_TARGET.md) |
| Wo liegen Ideen des verworfenen Character Chronicles? | [Historisches Archiv](archive/character-chronicles-v1/README.md) |
| Welche alten ComfyReview-Anweisungen gelten nicht mehr? | [Technisches Legacy-Archiv](archive/comfyreview-legacy/README.md) |

## Verbindlichkeit und Vorrang

1. **IST-Zustand:** Für Aussagen über implementiertes Verhalten zählen der Code, reproduzierbare Tests und der abgeglichene [Projektstatus](project_status.md). Ein Architekturziel ist nicht schon durch Dokumentation implementiert. Bei Diskrepanz den Status korrigieren, nicht den Codezustand behaupten.
2. **Engineering:** [AGENTS.md](../AGENTS.md) und aktuelle Architektur-/Daten-/Qualitätsverträge regeln neue Änderungen innerhalb ihrer Zuständigkeit.
3. **Neustart und Produktumfang:** [Entscheidungsregister](DECISIONS.md) hält ausdrücklich bestätigte Scope-Entscheidungen; [Roadmap](ROADMAP.md) ordnet Phasen. Der [Card-Battler-Zielvertrag](CARD_BATTLER_TARGET.md) gilt nur für seinen beschränkten Teilbereich und lässt ausdrücklich genannte Detailfragen offen.
4. **Erkundung:** [POC-Register](POC_REGISTER.md) und [Zukunftsnotizen](future/README.md) sind noch keine Freigabe zur Implementierung. Ein POC-Ergebnis wird erst mit dokumentierter Entscheidung verbindlich.
5. **Historie:** Alles unter [archive/](archive/README.md), insbesondere der verworfene Chronicle-Versuch, hat **keine normative Wirkung**. Historische Begriffe wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“ und historische Schema-/Meilensteinangaben sind nicht auf ComfyReview übertragbar.

**Bei Widersprüchen**: aktive Entscheidung/aktuellen Produktvertrag gegen historische Aussage prüfen; Geschichte nicht automatisch übernehmen. Besteht zwischen zwei aktuellen Dokumenten ein echter Konflikt, bis zur ausdrücklich dokumentierten Klärung keine der strittigen Detailvarianten als implizit entschieden darstellen.

## Statussprache für aktive Dokumente

| Kennzeichnung | Exakte Bedeutung |
| --- | --- |
| **IMPLEMENTED** | Im aktuellen Repository nachweisbar umgesetzt; Beleg bzw. Test benennen |
| **APPROVED_TARGET** | Für den genannten Bereich ausdrücklich beschlossen, jedoch noch kein vollständiges Laufzeitverhalten |
| **PROPOSED** | Diskussionsvorschlag ohne verbindliche Entscheidung |
| **POC** | Experiment/Hypothese; Ergebnis und Annahme getrennt halten |
| **DEFERRED** | Späterer Umfang, derzeit nicht zur Implementierung freigegeben |
| **ARCHIVED** | Historischer Inhalt, kein gültiger Produkt-/Architekturvertrag |
| **REJECTED** | Ausdrücklich verworfene Variante, nicht erneut stillschweigend übernehmen |

**Pflicht bei neuen oder wesentlich bearbeiteten Dokumenten:** Titel, Dokumentrolle, Status, Geltungsbereich/Phase, Stand, explizite Abgrenzungen und Link zum zuständigen Entscheidungs- oder Implementierungsnachweis. Eine Aussage wie „Plan steht“ ersetzt keine Abnahme. Historische Quellen nur als solche referenzieren.

## Aktuelle technische Dokumentation

- [Architektur](ARCHITECTURE.md) und [Datenarchitektur](DATA_ARCHITECTURE.md) – aktueller Code-/Laufzeitvertrag
- [Refactor-Plan](REFACTOR_PLAN.md) und [Projektstatus](project_status.md) – Fortschritt und ausstehende Abnahmen des aktuellen Bestands
- [Frontend V2](FRONTEND_V2_DESIGN.md) – bestehende ComfyReview-Oberfläche, **nicht** die spätere Chronicle-UI
- [Generation Runtime](GENERATION_RUNTIME_PLAN.md), [Canonical Review Storage](CANONICAL_REVIEW_STORAGE.md), [Projection Audit](PROJECTION_AUDIT.md), [Legacy Output Import](LEGACY_OUTPUT_IMPORT.md) – technische Teilverträge
- [Structured Prompt Bundles Work Order](STRUCTURED_PROMPT_BUNDLES_WORK_ORDER.md) – historischer, als implementiert ausgewiesener Arbeitsauftrag; für den aktuellen Gesamtstatus Projektstatus/Code prüfen

## Produktentwicklung und Archiv

- [Geplante Schritte](ROADMAP.md), [Entscheidungen](DECISIONS.md), [POCs](POC_REGISTER.md)
- [Card Battler](CARD_BATTLER_TARGET.md): aktiver, begrenzter Zielvertrag. Es gibt bereits Modell-/Entwicklungsbausteine, aber noch **keinen vollständig spielbaren PvE-Card-Battler**.
- [Spätere Phasen](future/README.md): bewusst offene Platzhalter für Timeline, Social/Chat, Storyline und VN-Content.
- [Archiv des verworfenen Character-Chronicles-Versuchs](archive/character-chronicles-v1/README.md): keine aktuelle Freigabe, keine neuen Schemas oder Roadmap daraus ableiten.

## Dokumentationsprüfung

```bash
python scripts/check_documentation.py
```

Der lokale Check überprüft Verweise in **aktiven Markdown-Dateien** und die Archivmarkierungen. Veraltete Querverweise **innerhalb** der originalgetreu erhaltenen Archivtexte werden bewusst nicht als aktive Navigation behandelt; ihre fehlenden historischen Ziele sind im [Archivindex](archive/character-chronicles-v1/README.md) erläutert.
