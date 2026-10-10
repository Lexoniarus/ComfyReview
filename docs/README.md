# ComfyReview – Dokumentationsstart

**Stand:** 2026-10-10 · **Projekt:** ComfyReview wird aktiv weiterentwickelt und soll langfristig zu Character Chronicles werden. **Die Produktentwicklung ist nicht fertig und ihre technische Zukunft nicht festgeschrieben.**

## Projektzustand in drei Sätzen

**Heute:** ComfyReview ist die laufend überarbeitete ComfyUI-Review- und
Generator-Anwendung. **Schema v18 im Code** heißt nicht, dass die private
Datenbank bereits migriert und operativ abgenommen wurde. Der Card Battler
ist **aktiver POC**, kein vollständig spielbares Produkt.

**Zielrichtung:** Aus **derselben Codebasis** soll langfristig Character
Chronicles entstehen. Die **ungefähre**, durch POCs veränderbare
Entwicklungsorientierung lautet:
**Card Battler → Timeline → Social Network mit Charakter-Chats → Storyline →
Visual-Novel-Content zuletzt**. Timeline ist zunächst ein begrenzter sozialer
Slice, Social/Chat die breitere Plattform. **Die Welt ist fachlich
bestätigt:** Kobe/Japan ab 2032, zwei Academy-Jahre für Erwachsene,
eine etablierte globale Social- und Kartenkultur, persönliche Figuren
und eine langfristig storygetriebene VN. Die Academy ist **kein
optionaler Weltkontext**, aber auch keine zusätzliche verpflichtende
Implementierungsphase. [Bestätigte Welt](character-chronicles/vision/world.md) ·
[Entwicklungsbegründung](PROJECT_EVOLUTION.md) ·
[Gesamtvision](character-chronicles/vision/README.md).

**Vergangenheit:** Der frühere Character-Chronicles-Codeansatz wurde
verworfen. Seine 24 ausführlichen importierten Konzepte sind
**[Quellenmaterial](character-chronicles/sources/README.md)**.
Ihr **inhaltlicher Weltkern wurde inzwischen ausdrücklich als Ziel
bestätigt**; alte technische Verträge und mechanische Detailregeln
werden dadurch nicht automatisch wieder verbindlich.

## Welches Dokument ist wofür gültig?

| Geltung | Dokument | Hier findet man … |
| --- | --- | --- |
| **CURRENT_CODE** | [Implementation Audit](IMPLEMENTATION_AUDIT.md) | Nachweisbarer ComfyReview-Code an einem konkreten Commit; Grenzen seiner Aussagekraft |
| **CURRENT_STATUS** | [Projektstatus](project_status.md) als Gesamtübersicht; [Refactor-Abnahmestand](REFACTOR_PLAN.md) für den Refactor | Was heute belegt ist und welche Integrations-/Betriebsabnahmen im jeweiligen Bereich offen sind; **keine** historische Slice-Chronik |
| **IN_PROGRESS** | [Aktuelle Arbeiten](ACTIVE_WORK.md) und [POCs](pocs/README.md) | Generator-/Datenbank-Optimierung, derzeitiger Card-Battler-POC, nicht abgeschlossene Integration |
| **WORKING_DIRECTION** | [Projektentwicklung](PROJECT_EVOLUTION.md) | Warum Card Battler technisch zuerst und VN-Content zuletzt kommt – unabhängig von der bestätigten Spielwelt |
| **WORKING_VISION** | [Bestätigte Zielwelt](character-chronicles/vision/world.md), [Gesamtzielbild](character-chronicles/vision/README.md) | **Fachlich bestätigte Welt** und Spielebenen, aber keine übernommene historische Technik oder feste Releasephasen |
| **DECIDED_FOR_SCOPE** | [Bestätigte Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md) | Tatsächlich bestätigte Vorgaben mit konkretem Geltungsbereich; getrennt von Zielen, Präferenzen und unbeschlossenen Schutzvorschlägen |
| **OPEN** | [Offene Entscheidungen](OPEN_DECISIONS.md) | Was noch nicht entschieden oder operativ verifiziert ist |
| **CURRENT_TECH_REFERENCE** | [Architektur](ARCHITECTURE.md), [Datenarchitektur](DATA_ARCHITECTURE.md), [Frontend V2](FRONTEND_V2_DESIGN.md) | **ComfyReviews derzeitige Implementierungsverträge**, keine Architekturvorgabe für das spätere Spiel |
| **CURRENT_OPERATIONS** | [Betriebsübersicht](OPERATIONS.md); [Legacy Output Import](LEGACY_OUTPUT_IMPORT.md) als Spezialanleitung | Aktuelle CLI, Import, Recovery, `--replace`; **historische Daten** bedeuten nicht **historisch ungültige Kommandos** |
| **ENGINEERING_RULES** | [AGENTS](../AGENTS.md), [Coding Standards](CODING_STANDARDS.md) | Für Änderungen am gegenwärtigen ComfyReview-Code geltende Regeln |
| **GOVERNANCE** | [Dokumentationsleitfaden](DOCUMENTATION_GUIDE.md), [Decision Policy](DECISION_POLICY.md), [Abgleich alter CRCC-/POC-Einträge](DECISION_POC_RECONCILIATION.md) | Dokumentklassen, Entscheidungsregeln und nichtverbindliche Zuordnung der früher falsch platzierten Register |
| **SOURCE_MATERIAL** | [24 importierte Quelltexte](character-chronicles/sources/README.md) | Ausführliche Spielideen und frühere „verbindliche“ Verträge **nur als Quellen**, nicht als heutige Vorgaben |
| **HISTORICAL_EVIDENCE** | [Alter Chronicle-Code](character-chronicles/HISTORICAL_CODE_AUDIT.md), [historisches Archiv](archive/README.md) | Was früher vorhanden, geplant oder verworfen war – nicht was jetzt gebaut werden muss |
| **HISTORICAL_LOG** | [Archivierter Refactor-Verlauf](archive/refactor-slice-history-2026-10-09.md), [alte Status-/Operatorberichte](archive/project-status-log-2026-10-09.md) | **Ausschließlich frühere** Slices, Zeitpunkte, operative Berichte; kein heutiger Status |

## Verzeichnisstruktur

```text
README.md                              Einstieg/Setup zum aktuellen ComfyReview
AGENTS.md                              Regeln für den aktuellen Code
docs/
  README.md                            Diese Zuständigkeits- und Statuskarte
  project_status.md                    CURRENT_STATUS
  IMPLEMENTATION_AUDIT.md             CURRENT_CODE / Testbelege
  ACTIVE_WORK.md                       IN_PROGRESS
  REFACTOR_PLAN.md                     CURRENT_STATUS (Refactor-Abnahme)
  PROJECT_EVOLUTION.md                WORKING_DIRECTION
  OPERATIONS.md                       CURRENT_OPERATIONS (führende Betriebsübersicht)
  LEGACY_OUTPUT_IMPORT.md             CURRENT_OPERATIONS (historischer Output-Import)
  OPEN_DECISIONS.md                   OPEN
  CONFIRMED_CONSTRAINTS.md           DECIDED_FOR_SCOPE / Präferenzen / Optionen
  DECISION_POLICY.md                  GOVERNANCE – Entscheidungsregeln
  DECISION_POC_RECONCILIATION.md      GOVERNANCE – historischer ID-Abgleich (keine zweite Roadmap)
  DOCUMENTATION_GUIDE.md              GOVERNANCE – Dokumentklassen
  ARCHITECTURE.md, DATA_ARCHITECTURE.md, ...  CURRENT_TECH_REFERENCE
  pocs/
    card-battler.md                    Laufender POC, kein fertig spielbares Produkt
  character-chronicles/
    vision/                            WORKING_VISION – bestätigte Zielwelt und weitere Bereiche
      world.md                         bestätigte Weltprämisse, gesellschaftlicher/erzählerischer Rahmen
      card-battler.md, timeline.md, social-network.md,
      storyline.md, academy-and-world.md (Weltkontext),
      visual-novel.md
    sources/                           SOURCE_MATERIAL – 24 lange importierte Texte
    history/                           Frühere Gesamtentwürfe
    HISTORICAL_CODE_AUDIT.md          Verworfener alter Code-/Abnahmestand
  archive/                             HISTORICAL_EVIDENCE/HISTORICAL_LOG
    refactor-slice-history-2026-10-09.md  HISTORICAL_LOG (nicht REFACTOR_PLAN.md)
```

## Wichtigste Leseregel

**Nicht mit derselben Verbindlichkeit lesen:**

- `CURRENT_CODE` bedeutet **an einem konkreten Commit nachgewiesenen ComfyReview-Code** (nicht automatisch eine spätere Laufzeit-/Release-Abnahme).
- `IN_PROGRESS` bedeutet **Arbeit/POC läuft**, nicht freigegeben.
- `WORKING_VISION` beschreibt die fachliche Produktvision. **Der
  Weltkern von Character Chronicles ist ausdrücklich als Ziel bestätigt**;
  technische Details und die Umsetzung sind keine beschlossene
  Gesamtarchitektur.
- `DECIDED_FOR_SCOPE` ist **nur für den benannten Bereich verbindlich**; Zielwerte und als `CANDIDATE` markierte Umsetzungsvorschläge sind das nicht.
- `SOURCE_MATERIAL` und `HISTORICAL_*` enthalten absichtlich auch **alte, einander widersprechende „autoritative“ Aussagen**. Diese sind jetzt ausdrücklich **Originalquellen**, nicht aktiver Auftrag.

**Zuständigkeit:** Der [Projektstatus](project_status.md) führt den allgemeinen heutigen Code-/Abnahmestand, [REFACTOR_PLAN.md](REFACTOR_PLAN.md) nur den spezifischen Refactor-Abnahmestand, [ACTIVE_WORK.md](ACTIVE_WORK.md) die laufenden POCs, [OPEN_DECISIONS.md](OPEN_DECISIONS.md) ausschließlich offene Entscheidungen und [OPERATIONS.md](OPERATIONS.md) die aktuellen Betriebsverfahren. Historische Berichte gehören ins [Archiv](archive/README.md), nicht in aktuelle Statusangaben.

Diese **Dokumentklassen** beschreiben die Geltung des Dokuments. Kennzeichnungen einzelner **Aussagen** wie `CANDIDATE`, `POC_RESULT` und `DECIDED_FOR_SCOPE` sind in der [Decision Policy](DECISION_POLICY.md) erklärt; ein Quellen- oder Indexdokument macht seine historischen Zitate dadurch nicht bindend.

Für Regeln zur Einordnung und Bestätigung einzelner Entscheidungen: [Documentation Guide](DOCUMENTATION_GUIDE.md) und [Decision Policy](DECISION_POLICY.md). Für Installations- und Betriebsschritte: [Repository-README](../README.md).
