# ComfyReview – Dokumentationsstart

**Stand:** 2026-10-09 · **Projekt:** ComfyReview wird aktiv weiterentwickelt und soll langfristig zu Character Chronicles werden. **Die Produktentwicklung ist nicht fertig und ihre technische Zukunft nicht festgeschrieben.**

## Welches Dokument ist wofür gültig?

| Geltung | Dokument | Hier findet man … |
| --- | --- | --- |
| **CURRENT_CODE** | [Implementation Audit](IMPLEMENTATION_AUDIT.md) | Nachweisbarer ComfyReview-Code an einem konkreten Commit; Grenzen seiner Aussagekraft |
| **CURRENT_STATUS** | [Projektstatus](project_status.md) | Kurzüberblick: was verdrahtet ist, welche Abnahme fehlt, was nicht zum heutigen Code gehört |
| **IN_PROGRESS** | [Aktuelle Arbeiten](ACTIVE_WORK.md) und [POCs](pocs/README.md) | Generator-/Datenbank-Optimierung, derzeitiger Card-Battler-POC, nicht abgeschlossene Integration |
| **WORKING_DIRECTION** | [Projektentwicklung](PROJECT_EVOLUTION.md) | Warum Card Battler zuerst, danach Social/Chats, Academy/Schuljahr und die visuelle VN zuletzt |
| **WORKING_VISION** | [Character-Chronicles-Zielbild](character-chronicles/vision/README.md) | **Kurze, klar lesbare Produktziele** ohne alte technische Festlegungen |
| **OPEN** | [Offene Entscheidungen](OPEN_DECISIONS.md) | Was noch nicht entschieden oder operativ verifiziert ist |
| **CURRENT_TECH_REFERENCE** | [Architektur](ARCHITECTURE.md), [Datenarchitektur](DATA_ARCHITECTURE.md), [Frontend V2](FRONTEND_V2_DESIGN.md) | **ComfyReviews derzeitige Implementierungsverträge**, keine Architekturvorgabe für das spätere Spiel |
| **CURRENT_OPERATIONS** | [Datenbank-/Wartungsbefehle](OPERATIONS.md) | CLI, Import, Recovery und `--replace` mit separater Sicherheits-/Freigabegrenze |
| **ENGINEERING_RULES** | [AGENTS](../AGENTS.md), [Coding Standards](CODING_STANDARDS.md) | Für Änderungen am gegenwärtigen ComfyReview-Code geltende Regeln |
| **SOURCE_MATERIAL** | [24 importierte Quelltexte](character-chronicles/sources/README.md) | Ausführliche Spielideen und frühere „verbindliche“ Verträge **nur als Quellen**, nicht als heutige Vorgaben |
| **HISTORICAL_EVIDENCE** | [Alter Chronicle-Code](character-chronicles/HISTORICAL_CODE_AUDIT.md), [historisches Archiv](archive/README.md) | Was früher vorhanden, geplant oder verworfen war – nicht was jetzt gebaut werden muss |
| **HISTORICAL_LOG** | [Refactor-Verlauf](REFACTOR_PLAN.md) | Frühere technische Umsetzungsschritte; offene aktuelle Arbeit steht im Status/Active Work |

## Verzeichnisstruktur

```text
README.md                              Einstieg/Setup zum aktuellen ComfyReview
AGENTS.md                              Regeln für den aktuellen Code
docs/
  README.md                            Diese Zuständigkeits- und Statuskarte
  project_status.md                    CURRENT_STATUS
  IMPLEMENTATION_AUDIT.md             CURRENT_CODE / Testbelege
  ACTIVE_WORK.md                       IN_PROGRESS
  PROJECT_EVOLUTION.md                WORKING_DIRECTION
  OPERATIONS.md                       CURRENT_OPERATIONS (Migration/Import)
  OPEN_DECISIONS.md                   OPEN
  DECISION_POLICY.md                  Statusdefinitionen und Entscheidungsregeln
  ARCHITECTURE.md, DATA_ARCHITECTURE.md, ...  CURRENT_TECH_REFERENCE
  pocs/
    card-battler.md                    Laufender POC, kein fertig spielbares Produkt
  character-chronicles/
    vision/                            WORKING_VISION – kurze, aktuelle Zielbilder
      card-battler.md, social-network.md,
      academy-and-world.md, visual-novel.md
    sources/                           SOURCE_MATERIAL – 24 lange importierte Texte
    history/                           Frühere Gesamtentwürfe
    HISTORICAL_CODE_AUDIT.md          Verworfener alter Code-/Abnahmestand
  archive/                             Alte Status-, Betriebs- und Umsetzungsprotokolle
```

## Wichtigste Leseregel

**Nicht mit derselben Verbindlichkeit lesen:**

- `CURRENT_CODE` bedeutet **heute nachgewiesenen ComfyReview-Code** (Commit/Tests).
- `IN_PROGRESS` bedeutet **Arbeit/POC läuft**, nicht freigegeben.
- `WORKING_VISION` bedeutet **inhaltlich angestrebte Richtung**, keine beschlossene Detailarchitektur.
- `SOURCE_MATERIAL` und `HISTORICAL_*` enthalten absichtlich auch **alte, einander widersprechende „autoritative“ Aussagen**. Diese sind jetzt ausdrücklich **Originalquellen**, nicht aktiver Auftrag.

Für Regeln zur Einordnung und Bestätigung einzelner Entscheidungen: [Documentation Guide](DOCUMENTATION_GUIDE.md) und [Decision Policy](DECISION_POLICY.md). Für Installations- und Betriebsschritte: [Repository-README](../README.md).
