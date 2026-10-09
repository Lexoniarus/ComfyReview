# Projektstatus – ComfyReview

**Dokumentklasse:** `CURRENT_STATUS` · **Code-Referenz:** [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32), 2026-10-08 (vor dem reinen Dokumentenimport) · **Dokumentationsprüfung:** 2026-10-09.

**ComfyReview ist die aktive, weiterhin entwickelte Anwendung**, nicht ein abgeschlossenes Produkt. Langfristig soll daraus Character Chronicles entstehen; die konkreten technischen Schritte ergeben sich iterativ aus POCs. Für die nächsten Themen und offene Arbeiten gilt [Active Work](ACTIVE_WORK.md), für die langfristige Richtung [Project Evolution](PROJECT_EVOLUTION.md).

## Im geprüften Anwendungscode tatsächlich eingebunden

| Gebiet | Status und Nachweis |
| --- | --- |
| Backend und Konfiguration | FastAPI, getypte Konfiguration und App-Lifecycle: [Bootstrap](../comfyreview/bootstrap.py), [Settings](../comfyreview/settings.py) |
| Canonical SQLite | **Schema v18 ist im Code implementiert** einschließlich expliziter Migrationen/Validierung: [Schema](../comfyreview/repositories/sqlite/canonical_schema.py). **Das beweist keinen vollzogenen privaten Datenbank-Cutover.** |
| Bildreview und Bestand | Review/Rating, Ranking, Arena, Curation sowie Archiv-/Löschhistorie sind in [V2-Routern](../routers/api_v2/__init__.py) und Services verdrahtet |
| Playground/Generator | Generator, Blueprint v4, Workflow-Compiler, ComfyUI-Provider, Lifecycle, Reconcile und Output-Collection sind implementiert: [Generation](../comfyreview/application/generation.py), [Lifecycle](../comfyreview/application/generation_lifecycle.py) |
| Katalog und Auswertung | Prompt-/LoRA-Katalog, Varianten/Guidance, Analytics, Settings; [API-Router](../routers/api_v2/__init__.py) und [Katalog-Persistenz](../comfyreview/repositories/sqlite/prompt_catalog.py) |
| Oberfläche | ComfyReview Frontend V2 (Jinja und native JavaScript-Module): [Templates](../templates) und [JS-Einstiegspunkte](../static/js/entries) |

Diese Feststellungen bezeichnen **vorhandenen und eingebundenen Code**, nicht die endgültige Produktabnahme. Details und konkrete Tests: [Implementation Audit](IMPLEMENTATION_AUDIT.md).

## Noch in Entwicklung oder offen

| Thema | Tatsächliche Einordnung |
| --- | --- |
| **Card Battler** | **Aktiver POC in ComfyReview.** Getestete Karten-/Trait-/Mechanik-/Visual-Prompt-Algorithmen existieren; kein vollständig integrierter, spielbarer Karten-/Deck-/PvE-Match-Flow in der geprüften API/UI. [POC](pocs/card-battler.md) |
| **Generator** | Jüngst stark überarbeitet. Die vorhandenen Services sind angebunden, aber weitere Bedien-/Provider-Abnahmen und Änderungen sind möglich |
| **Katalog und Datenbank** | Normalisierung/Rebuild, Schema und Testabdeckung sind umgesetzt. Die **private reale Datenbank**, redaktionelle Mappings, operativer `--replace`-Cutover und Akzeptanz sind davon getrennt und nicht aus Git als vollständig abgeschlossen nachweisbar |
| **Abnahme und Integration** | Manuelle visuelle/operative Akzeptanz und die Integration der Refactor-Basis in `master` sind eigene Entscheidungen |
| **Langfristiges Character Chronicles** | **Grobe Orientierung:** Card Battler → Timeline → Social Network mit Charakter-Chats → Storyline → VN-Content **zuletzt**. Academy/Schuljahr ist mögliche Story-/Weltgestaltung, keine gesondert beschlossene Pflichtphase. **Keine** heute implementierte vollständige Spiel-, Social- oder VN-Runtime und **kein** fester Milestone-/Technikplan. [Vision](character-chronicles/vision/README.md) |

Externe Versuche oder private lokale Daten werden **nicht** als angebundene ComfyReview-Funktionen ausgegeben.

## Was die automatisierte Qualität wirklich belegt

Die [CI für die codegleiche Vorimport-Basis](https://github.com/Lexoniarus/ComfyReview/actions/runs/37769483557) war erfolgreich. Auch der [Quality-Workflow für den nur dokumentarisch erweiterten Commit `76d71f9`](https://github.com/Lexoniarus/ComfyReview/actions/runs/37901248379) war erfolgreich (Linux Python 3.11/3.14, Windows Python 3.14). Der Linux-Python-3.11-Lauf meldete **1.061 Python-Tests, 181 Vitest-Tests und 15 Playwright-Tests bestanden**.

Das sind **commitbezogene CI-Ergebnisse**, keine heutige Messung des lokalen SQLite-Datenbestandes und keine neue ComfyUI-Hardwareabnahme. Für neue Code-Commits muss der Status neu geprüft werden.

## Historische Protokolle und Herkunft

Alte Meldungen über reale Schema-v9/v12/v14/v16-Upgrades, persönliche Datenmengen, LoRA-Audits, Smokes und Backup-/Cutover-Schritte stehen im [archivierten ausführlichen Statusprotokoll](archive/project-status-log-2026-10-09.md). **Sie werden hier bewusst nicht als aktuelle Datenbankzahlen wiederholt.**

Der tatsächliche verworfene frühere Character-Chronicle-Code und dessen damalige Abnahme sind [separat dokumentiert](character-chronicles/HISTORICAL_CODE_AUDIT.md). Alte technische Spezifikationen werden dadurch **nicht** zur Zielarchitektur der laufenden Produktentwicklung.

[Dokumentationsübersicht](README.md) · [offene Entscheidungen](OPEN_DECISIONS.md) · [Belegstufen und Geltungsregeln](DOCUMENTATION_GUIDE.md).
