# Herkunftsmatrix: Konzeptideen, ComfyReview-Code und frühere Chronicle-POCs

**Dokumentklasse:** `SOURCE_MATERIAL` · **Rolle:** Herkunfts- und Versionsindex; vergleicht importierte Quellen mit früherem und aktuellem Code, **kein** neuer Implementierungsauftrag.

**Vergleichsstand:** 2026-10-09 · **aktuelle ComfyReview-Codebasis vor Dokumentenimport:** [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32).

Das ist **kein Character-Chronicles-Implementierungsplan**. Die
inhaltliche [Kobe-/Academy-/Social-Zielwelt](../vision/world.md)
wurde inzwischen ausdrücklich bestätigt; technische Altverträge
bleiben historische Prüffälle. Die 24 Dokumente kamen mit dem reinen Konzept-Import [`76d71f9`](https://github.com/Lexoniarus/ComfyReview/commit/76d71f9c7723701664785aeaf07e0d7375a4f36a) hinzu. Mehrere Texte beschreiben **einen früheren, verworfenen Chronicle-Implementierungsstand**,
dessen Python-/TypeScript-Code, SQLite-Schemas, Tests, M4-/M6-/Foundation-
Abnahmeunterlagen **in der bereitgestellten `CharacterChronicle.zip`**
tatsächlich vorhanden sind. [Historisches Code- und Quellenaudit](../HISTORICAL_CODE_AUDIT.md).
Damit kann zwischen **damals in Code vorhanden** und **damals nur geplant**
unterschieden werden. Das wird **nicht** zur aktuellen ComfyReview-Codebasis
oder automatisch gültigen künftigen Architektur.

| Konzepttext | Sachlicher Bezug / wertvolle Anknüpfung | Vor einer Übernahme neu prüfen |
| --- | --- | --- |
| [Baseline/Entry-Gates](baseline-and-entry-gates.md) | Im historischen ZIP gab es wirklich Foundation-/Campaign-/Trial-Code, eine Vite-/TypeScript-Oberfläche und alte Acceptance-Dateien | Damalige Abnahme **getrennt** vom aktuellen ComfyReview-Code prüfen; technische Altarchitektur nicht automatisch übernehmen |
| [Card-Art](card-art-composition-and-rendering.md) | Kartendarstellung als Produktidee; aktuelle [Visual-Projektion](../../../comfyreview/application/card_battler_visual_projection.py) | Art-/Frame-Technologie und Workflow nicht voreilig fixieren |
| [Battler Board](card-battler-board-and-combat-foundation.md) | Konkrete Spielregelideen | Slot-/Kampfregeln im aktuellen POC prüfen, nicht als Pflicht |
| [Decks/Turns](card-battler-decks-turns-and-actions.md) | Spielmechanische Ziele | Deckgröße, Züge und persistierte Spielregeln erst mit POC entscheiden |
| [Effektgrammatik](card-battler-effect-grammar-and-llm-authoring.md) | Deterministische Mechaniken existieren im [ComfyReview-Prototyp](../../../comfyreview/application/card_battler_rules.py) | Alter Regel-/LLM-Vertrag ist keine bindende neue Engine |
| [Battler Runtime](card-battler-runtime-architecture.md) | Technische Architekturideen | Reducer, Phaser, Datenmodell und Endpunkte neu bewerten |
| [Zonen/Status/Opcodes](card-battler-zones-statuses-and-opcode-registry.md) | Strukturierte Effektfamilien | Ausführungsregeln nicht mit existierender Typisierung gleichsetzen |
| [Card Crafting](card-crafting-and-playground-combination-lifecycle.md) | [Playground](../../../routers/api_v2/playground.py) und Card-Mapping als Vorarbeit | Booster-, Crafting- und Lifecycle-Annahmen offen |
| [Champion Slots](champion-slots-and-character-decks.md) | Review/Arena als Erfahrung aus ComfyReview | Championship und Spielprogress nicht automatisch übernehmen |
| [Embeddings/LLM-Kontext](deck-building-embeddings-and-llm-context.md) | Interessante technische Versuche/Ideen | Altes Retrieval-/Datenmodell braucht neue Evidenz |
| [Frontend-IA](frontend-information-architecture.md) | Die im Konzept genannte alte Vite-/TypeScript-Oberfläche existiert im ZIP unter `frontend_vnext/src/` **als Code** | Nicht mit aktueller Jinja-/ES-Modul-UI oder verpflichtender zukünftiger Oberfläche gleichsetzen |
| [Game Modes](game-modes-and-guided-evidence.md) | Auswahl-/Bildspiel-Ideen und Arena-Erfahrung | Historische M6-Modes und Zustandsmaschinen nicht verpflichtend |
| [Generation Profiles/Trials](generation-profiles-and-trials.md) | ComfyUI-Generator als technische Vorarbeit | Alte Profil-/Trial-Architektur nicht aus dormant Tabellen ableiten |
| [LLM/RAG/Recovery](llm-rag-and-recovery.md) | Konkrete KI-/Recovery-Ideen | Altes Provider-/Worker-Konzept nicht übernehmen, bevor es getestet ist |
| [Network-first VN UI](network-first-vn-frontend-screen-map.md) | Präsentations- und Erlebnisvision | Frühere Screens und Reihenfolge nicht als aktuelle UI-Vorgabe verwenden |
| [Guardian/Monitoring](orchestration-guardian-and-monitoring.md) | Beobachtbarkeit und Arbeitskoordination als Ziele | Alte autonome Orchestrierungsarchitektur ist keine aktuelle Pflicht |
| [Player Voice](player-facing-terminology-and-voice.md) | Sprach- und Begriffsideen | Text-/UI-Hierarchie später ausdrücklich festlegen |
| [M6-Lernloop](rolling-m6-learning-loop.md) | Im ZIP existieren alte M6-Pipeline-/Learning-/LM-Studio-/Embedding-Services sowie Schema-v58-Code und Tests | Historische Acceptance markiert den **praktischen Zwei-Zyklen-Beweis weiter offen**; keine automatische aktuelle Implementierung oder Wiederverwendung |
| [School-Year Portfolios](school-year-visual-portfolios-and-relationship-contexts.md) | Academy-/Beziehungsvision | Datenautorität und Spielmechaniken müssen neu erarbeitet werden |
| [Story/Cast/Simulation](story-cast-and-simulation.md) | Story-/Charakter- und Simulationsideen | Keine automatische Bindung der alten Save-/Timeline-Architektur |
| [Target Architecture](target-architecture.md) | Lücken, Abhängigkeiten und Optionen sichtbar | Alte Services, Prozessarchitektur, SQLite-Schemata, Gates/Worker nicht als verpflichtend übernehmen |
| [Visual Assets/Quests](visual-assets-quests-and-gates.md) | Quests, VN-Assets und Pipeline-Hypothesen | Kein Beweis einer derzeit integrierten Matting- oder VN-Runtime |
| [VN/Social/Card-Loop](vn-social-platform-and-card-loop-concept.md) | Welt, Spielgefühl, Academy, Plattformkultur, persönlicher Karten-/Storyzusammenhang sind inzwischen als [Zielwelt](../vision/world.md) bestätigt | Detaillierte Karten-, Generator-, Kalender-, UI- und technische Runtime-Verträge sowie konkrete POC-Schritte nicht pauschal übernommen |
| [Year-End LoRA/NG+](year-end-lora-and-new-game-plus.md) | Inhaltliche Ergänzung zur Vision | Weder fertiges Training, NG+ noch beschlossene Implementierungsreihenfolge |

## Quellenlage und Versionsabweichungen

Das ZIP enthält **25 Produktdateien**, der ComfyReview-Dokumentenimport
**24**. **14** gleichnamige Dateien stimmen per Git-Blobhash **bytegenau**
überein, **10** weisen Unterschiede auf. Außerdem liegt das bislang nicht
importierte Dokument
`docs/mvp/product/historical-reference-bootstrap-and-evaluation.md` vor.

Auch die zuvor vermissten `docs/mvp/foundation/README.md`,
`adaptive-generation-learning.md`,
`initial-game-mode-state-machines.md`,
`docs/mvp/acceptance/m4/README.md`,
`docs/mvp/acceptance/m6.7/02-rolling-loop.md` und
die alte Traceability-/Gap-Matrix sind **im ZIP vorhanden**.
Diese historische Fassung wird **nicht** über die später importierte
Produktfassung geschrieben und **nicht** als gültige Architektur eingebucht.
[Exaktes Inventar](../HISTORICAL_CODE_AUDIT.md).

## Wiederverwendung ist eine Option, kein Automatismus

Die aktuelle ComfyReview-Codebasis unterstützt [Canonical SQLite v18](../../../comfyreview/repositories/sqlite/canonical_schema.py), [FastAPI APIs](../../../routers/api_v2/__init__.py) und [getestete Card-Battler-Algorithmen](../../../comfyreview/application/card_battler_development_service.py). **ComfyReview wird weiterentwickelt** und der Card Battler wird aktuell erprobt. Was davon später Character Chronicles dient, entscheidet sich durch POCs. Frühere Chronicle-Systeme können technische Erkenntnisse liefern, **auch wenn deren Architektur verworfen wurde**.

[Gesamtentwicklung](../../PROJECT_EVOLUTION.md) · [Entscheidungsregeln](../../DECISION_POLICY.md) · [aktueller Card-Battler-POC](../../pocs/card-battler.md).
