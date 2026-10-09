# ComfyReview — Code-Ist-Zustand vor dem Dokumentenimport

**Dokumentklasse:** `CURRENT_CODE` – nachgewiesener ComfyReview-Code an einem benannten Commit, keine lokale Release-Abnahme.

**Codebaseline:** [`a5f4131bb76c1ff655892d287d19fcd401917d32`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32), 8. Oktober 2026  
**Inhaltlicher Import:** [`76d71f9c7723701664785aeaf07e0d7375a4f36a`](https://github.com/Lexoniarus/ComfyReview/commit/76d71f9c7723701664785aeaf07e0d7375a4f36a), 9. Oktober 2026  
**Prüfung:** 9. Oktober 2026  
**Umfang:** der gegenwärtige ComfyReview-Code. Die **langfristige
Entwicklung in Richtung Character Chronicles** ist ein Produktziel, aber
nicht als vollständig implementierte Runtime zu behaupten.

## Die zentrale Trennung

Ein GitHub-Commit-Vergleich `a5f4131...76d71f9` zeigt: 24 neue Konzeptdateien und einen früheren umfangreichen Entwurf sowie eine alte README-Verschiebung. **Es gab keine Änderungen am eigentlichen Anwendungscode.** Daher beschreibt dieses Dokument den **vorher bereits vorhandenen ComfyReview-Codebestand**. Die am 9. Oktober importierten Inhalte dürfen keine nachträglichen Aussagen über implementierte Funktionen, akzeptierte Architektur oder Entwicklungsphasen erzeugen.

ComfyReview wird **aktiv weiterentwickelt** und soll langfristig
zu Character Chronicles werden. Der Card Battler wird **jetzt als POC**
bearbeitet, der Generator wurde kürzlich überarbeitet und die
Datenbank/Katalogstruktur wird noch optimiert. Der dokumentierte
**frühere verworfene Character-Chronicles-Implementierungsstand** ist in
diesem ComfyReview-Codebaum **nicht als aktive Runtime** enthalten, liegt
aber jetzt als [historisch untersuchter ZIP-Codebestand](character-chronicles/HISTORICAL_CODE_AUDIT.md)
vor: mit echter Campaign-/Trial-/M6-Implementierung, Vite-/TypeScript-
Frontend und historischer SQLite-Schema-Version 58.
Dieser ältere Codebestand wird **nicht** mit ComfyReview-Schema v18
oder der langfristig noch offenen Produktarchitektur gleichgesetzt. Die
[Vision-/Quelltexte](character-chronicles/README.md) sind daher kein
Beweis für deren technische Reife oder für verbindliche Schritte des
heutigen Entwicklungswegs.

## Evidenzabstufung

| Status | Was die Evidenz tatsächlich belegt |
| --- | --- |
| **In ComfyReview eingebunden** | Code und aktive Application-Container-/Router-/UI-Verdrahtung sind sichtbar |
| **Getesteter ComfyReview-Prototyp** | Python-Klassen und Verhaltenstests existieren; ein nutzbarer End-to-End-Featureflow ist damit **nicht** belegt |
| **Historisch berichtete Operation** | In alten Dokumenten beschrieben; zugehörige private Daten, Hardware oder Abnahmeprotokolle liegen hier nicht vor |
| **Nicht nachgewiesen** | Das Repository enthält keine entsprechende aktive technische Funktionsgrenze; kein Befund über mögliche andere Projekte |

## Verifizierte ComfyReview-Anwendungsgrenzen

| Funktionsbereich | Quellcode- und Testbeleg | Beurteilung |
| --- | --- | --- |
| Settings, Lebenszyklus, FastAPI | [Konfiguration](../comfyreview/settings.py), [Bootstrap und Router](../comfyreview/bootstrap.py), [Tests](../tests/test_application_bootstrap.py) | Eingebunden |
| Canonical SQLite, Versionierung | [`SCHEMA_VERSION = 18`](../comfyreview/repositories/sqlite/canonical_schema.py), [Schema-Upgradetests](../tests/test_canonical_schema_upgrade.py) | Eingebunden |
| Review/Rating/Restore/Delete | [V2 API](../routers/api_v2/review.py), [Service](../comfyreview/application/reviews.py), [Tests](../tests/test_review_service.py) | Eingebunden |
| Ranking/Arena | [API](../routers/api_v2/arena.py), [Paarungslogik](../comfyreview/application/arena.py), [Tests](../tests/test_canonical_ranking_arena.py) | Eingebunden |
| Curation | [API](../routers/api_v2/curation.py), [Service](../comfyreview/application/curation.py), [Tests](../tests/test_canonical_curation.py) | Eingebunden |
| Katalog/Prompts/LoRAs | [Catalog API](../routers/api_v2/catalog.py), [Prompt Repository](../comfyreview/repositories/sqlite/prompt_catalog.py), [Tests](../tests/test_prompt_catalog.py) | Eingebunden |
| Playground/Guidance/Varianten | [API](../routers/api_v2/playground.py), [Variant Preparation](../comfyreview/application/playground_variants.py), [Tests](../tests/test_playground_variants.py) | Eingebunden |
| ComfyUI Generation/Reconcile | [Generation API](../routers/api_v2/generations.py), [Workflow-Compiler](../comfyreview/application/workflow_compilation.py), [Provider](../comfyreview/providers/comfyui.py), [Lifecycle](../comfyreview/application/generation_lifecycle.py), [Blueprint v4](../data/workflows/default-character/v4.json) | Eingebunden (ComfyUI selbst ist externer Dienst) |
| Analytics, Scopes | [Analytics API](../routers/api_v2/analytics.py), [Scopes API](../routers/api_v2/scopes.py), [Tests](../tests/test_canonical_analytics.py) | Eingebunden |
| Frontend V2 | [Jinja-Templates](../templates), [JS-Einstiegsmodule](../static/js/entries), [Browser-Tests](../frontend-e2e) | Eingebunden |
| Historische Imports | [Explizite CLI](../comfyreview/__main__.py), [Importadapter](../comfyreview/importers), [Tests](../tests/test_legacy_output_import.py) | Wartungsfunktion, **kein** automatischer Startup-Import |

### Bestehende Card-Battler-Vorarbeiten innerhalb von ComfyReview

**Vor dem Dokumenten-Commit vorhanden:**

- [Immutable Kartendaten und Mechaniken](../comfyreview/domain/card_battler) samt Verhaltenstests;
- [Read-only `card_battler.sqlite3`-Modelladapter](../comfyreview/repositories/sqlite/card_battler_model_resource.py) mit Schema-/Validierungstests;
- [Deterministisches SemanticImageProfile-zu-CardImprint-Mapping](../comfyreview/application/card_battler_mapping.py);
- [Stats/Mechanic-Materialisierung und Regeltext](../comfyreview/application/card_battler_rules.py);
- [Tier-/Trait-Entwicklungsalgorithmen](../comfyreview/application/card_battler_development_service.py) und [Golden-Path-Tests](../tests/test_card_battler_development_golden_path.py);
- [Visuelle Promptprojektion](../comfyreview/application/card_battler_visual_projection.py).

Der [Bootstrap](../comfyreview/bootstrap.py) konstruiert einen Model-Adapter und Mapper. **Weder** die [registrierten API-Router](../routers/api_v2/__init__.py) **noch** die Browser-Templates enthalten eine vollständige Card-Battler-Collection, Deckverwaltung, Match-/Combat-API oder spielbare PvE-Oberfläche. Das externe Model-DB-File ist zudem **nicht** als Produktionsressource committed, weshalb sein realer Datenstand hier nicht verifizierbar ist.

Der **bereits vor dem Import** verfasste [Card-Battler-Zielplan vom 2. Oktober 2026](archive/card-battler-target-2026-10-02.md) dokumentiert frühere **ComfyReview-Planung**, nicht einen durch die neuen Character-Chronicles-Texte bestätigten gemeinsamen Folgeplan. Seine damaligen „approved“-/Phasenformulierungen dürfen für den Neustart nicht übernommen werden, ohne neu entschieden zu werden.

## CI-Evidenz auf unverändertem Code

- [CI für die vorimportierte Codebaseline `a5f4131`](https://github.com/Lexoniarus/ComfyReview/actions/runs/37769483557) — erfolgreich, 2026-10-08.
- [Quality-CI für den Dokumenten-Commit `76d71f9`](https://github.com/Lexoniarus/ComfyReview/actions/runs/37901248379) — erfolgreich am 2026-10-09 auf Linux Python 3.11 / 3.14 sowie Windows Python 3.14. Der Linux-3.11-Job protokollierte **1.061 Python-Tests**, **181 Vitest-Tests** und **15 Playwright-Tests** bestanden; 100 % Python-Core-Statement-Coverage und 100 % Frontend-Statements/Funktionen/Zeilen (Frontend-Branch-Coverage 86,05 %).

Diese Angaben sind **Ergebnisse der konkreten GitHub-CI-Läufe**, **nicht** eigens hier gestartete lokale Tests oder Hardware-Smokes. Der Dokumenten-Commit testete denselben Anwendungscode wie die unmittelbar vorherige Baseline.

## Nicht als gegenwärtig nachgewiesen deklarieren

- Private Katalog-Mapping-Entscheidungen, Benutzerabnahme, Cutover/Rehearsal-SQLite-Daten, historische Live-Rowcounts und reale lokale ComfyUI-Tests ohne die ignorierten Artefakte.
- End-to-End Card Battler, nur weil reine Kartenalgorithmen getesteten Code besitzen.
- Der **vollständige langfristige Character-Chronicles-Zielumfang**:
  Academy, VN, Social, LLM/RAG/Guardian, M6, „Schema 47–58“ und NG+ sind
  nicht Bestandteil der geprüften ComfyReview-Runtime. Einige alte
  technische Aussagen stammen aus einem **historisch bereitgestellten
  Character-Chronicle-Arbeitsstand**. Sie wurden
  [getrennt als früherer Code verifiziert](character-chronicles/HISTORICAL_CODE_AUDIT.md);
  weder frühere Live-Abnahme noch künftige Architektur daraus ableiten.
- Eine Roadmap, Meilensteinabfolge oder automatische gemeinsame Code-/Datenbankentwicklung über die Projektgrenze hinweg.

Siehe [ComfyReview-Projektstatus](project_status.md), [offene Entscheidungen](OPEN_DECISIONS.md) und [Herkunft der importierten Konzepte](character-chronicles/sources/SOURCE_RELATIONSHIP.md).

## Prüfungsmethode und Grenzen

Basis waren der vollständige Dateibaum, Ausgangscommit-Diff, Code für Konfiguration, Zusammensetzung, Datenbank, aktive Router, zentrale Services/Provider, Frontend-Einstiegspunkte und vorhandene Tests sowie die zugehörigen CI-Joblogs. Dies belegt **technische Komponenten und Integration in ComfyReview**. Die 24 inhaltlichen Texte wurden thematisch und anhand ihrer technischen
Altannahmen eingeordnet, **nicht** als ausgeführter Code eines früheren
Chronicle-Versuchs und **nicht** als verbindlich genehmigter Bauplan der
fortlaufenden Entwicklung. Die aktive Card-Battler-POC-Arbeit und private
Datenbankoptimierung können weitergehen, ohne dass dieses Commit-basierte
Audit einen fertigen Product-Status behauptet.
