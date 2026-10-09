# ComfyReview-Refactor: Code und offene Abnahmen

**Dokumentklasse:** `CURRENT_STATUS` · **Teilbereich:** aktueller Refactor-/Abnahmestand · **Referenz-Code:** [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32) (2026-10-08).  
**Der Dateiname `REFACTOR_PLAN.md` bleibt für vorhandene Verweise erhalten, ist aber kein aktiver Milestone-Plan.** Dieses Dokument ist die **führende aktuelle Übersicht nur für Refactor-Grenzen und noch offene Abnahmen**. Den allgemeinen Ist-Status führt [project_status.md](project_status.md), laufende POCs führt [ACTIVE_WORK.md](ACTIVE_WORK.md). Die **historische Chronik** liegt ausschließlich im [archivierten Refactor-Slice-Verlauf](archive/refactor-slice-history-2026-10-09.md).

## Technischer Ist-Stand

Der Branch `refactor/review-boundary` enthält die aktuelle ComfyReview-Refactor-Implementierung mit FastAPI-Kompositionswurzel, einem **im Code unterstützten Canonical SQLite Schema v18**, Canonical Review/Arena/Curation, Playground/Generator, Prompt-/LoRA-Katalog, Analytics, Frontend V2 und zugehörigen Tests.

Der Generator wurde zuletzt erheblich überarbeitet (Blueprint v4, Workflow-Compiler, Lifecycle und Output-Reconcile). Die Katalog-/Datenbanknormalisierung hat implementierte Prüf- und Rebuild-Werkzeuge. **Implementiertes Schema, Tests und Rehearsal sind nicht dieselbe Sache wie die Abnahme einer persönlichen Live-Datenbank.**

[Code und API-Belege](IMPLEMENTATION_AUDIT.md) · [Aktueller Status](project_status.md) · [Laufende Arbeit](ACTIVE_WORK.md).

## Offene technische und operative Akzeptanz

| Grenze | Aktuelle Aussage |
| --- | --- |
| **Code-/Test-Basis** | Die [CI auf codegleichem Dokumentencommit `76d71f9`](https://github.com/Lexoniarus/ComfyReview/actions/runs/37901248379) war erfolgreich. Jeder neuere Code-Commit braucht eigene Prüfungen. |
| **Private Normalisierung** | Audit, Editorial Mapping, Rebuild, Schema-v18-Ziel und separate Rehearsal können mit vorhandenen Werkzeugen vorbereitet werden. Ob/wann die reale DB akzeptiert und mit `--replace` umgestellt wurde, ist ohne die private Quelle/Reports **nicht unabhängig nachgewiesen**. |
| **Daten-/Rollback-Sicherheit** | Änderungen nur mit Hash-/Schema-Prüfung, eigenständiger validierter Ausgabedatei und bewusster Installationsentscheidung; historische operative Berichte ersetzen keine neue Sicherung. |
| **Manuelle Bedien-/Provider-Abnahme** | Reale ComfyUI-Funktion, visuelle Oberfläche, neue Generator-/Katalogflows und Bedienerakzeptanz sind vom automatisierten Codebeleg zu unterscheiden. |
| **Integration in `master`** | Separate Entscheidung und Review; das Vorhandensein auf dem Refactor-Branch ist kein veröffentlichter Release. |

## Unverändert geltende ComfyReview-Technikprinzipien

- Eine schreibbare kanonische Datenautorität je fachlichem Fakt; keine stillen Dual-Writes.
- Stabile UIDs statt Dateipfade als relationale Identität.
- SQL in Repositories bzw. expliziten Offline-Migrationsadaptern; kein externer API-/Datei-I/O während einer SQLite-Schreibtransaktion.
- Explizite Datenbankschemata/Migrationen mit Validierung und Backup statt stiller Startup-Upgrades.
- Aktive Source-/Testbelege und CI-Prüfungen für Änderungen; Operator-/UI-Abnahme separat.
- Die [Engineering-Regeln](../AGENTS.md) gelten für den **aktuellen ComfyReview-Code**, nicht pauschal für die zukünftige Character-Chronicles-Architektur.

## Nicht mit dem Refactor verwechseln

Der **Card Battler wird gerade als POC entwickelt** und ist kein abgeschlossener Bestandteil dieser Refactor-Abnahme. [POC](pocs/card-battler.md).  
**Character Chronicles** ist die langfristige Produktrichtung – **Card Battler zuerst, danach Social/Timeline/Charakter-Chats, Academy/Schuljahr und visuelle VN zuletzt**. Das ist eine priorisierte Arbeitsrichtung, kein durch historische Slices automatisch gültiger Architektur-/Milestonevertrag. [Zielbild](character-chronicles/vision/README.md).

Vergangene Rehearsals, lokale Smoke-Ergebnisse und einzelne historische Commit-Slices sind in der [vollständigen Refactor-Chronik](archive/refactor-slice-history-2026-10-09.md) lesbar, aber ausdrücklich **HISTORICAL_LOG**.
