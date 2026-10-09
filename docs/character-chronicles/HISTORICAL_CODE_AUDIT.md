# Historischer Character-Chronicle-Code: Quellen- und Implementierungsaudit

**Dokumentklasse:** `HISTORICAL_EVIDENCE` – älterer, verworfener Chronicle-Arbeitsstand, keine neue Runtime.

**Untersucht:** 2026-10-09 · **Quelle:** vom Projektinhaber bereitgestellte lokale Datei `CharacterChronicle.zip`, SHA-256 `e8e2a7411904c6beaa46037adc247bcaa071281bca87e9df10153ec0aa5a2615`.

> **Nicht die heutige ComfyReview-Runtime und kein Vorschlag zur Wiederherstellung dieser Architektur.** Das ZIP ist ein **früherer, inzwischen verworfener Character-Chronicle-Arbeitsstand**. Er ermöglicht eine bisher fehlende Prüfung historischer Implementierungsbehauptungen. ComfyReview bleibt der **aktuelle, in Entwicklung befindliche Code**, aus dem langfristig durch POCs und Neubewertung Character Chronicles entstehen soll.

## Art und Grenzen der Quelle

- Das Archiv enthält einen Root-Ordner `CharacterChronicle/`, **6767 Archiv-Dateien** insgesamt, davon zahlreiche Git-Objekte. Ohne `.git/`, private `.env` und Editor-/Konfigurationsreste umfasst der sichtbare Software-/Dokumentbestand über **500 Dateien**, darunter **390 Python-Dateien**, ein Vite-/TypeScript-Frontend, historische Produkt-/Foundation-/Acceptance-Texte und Tests.
- Das enthaltene `.git/HEAD` zeigt `refs/heads/main` mit `8ca490a95316721242919e2f139475c66f09b483`. **Das ist nicht gleichbedeutend mit einem sauberen Commit-Snapshot**: Der Dateiinhalt stimmt bei **55** Git-indexierten Pfaden nicht mit dem gespeicherten Index-Blobhash überein (teilweise nur Zeilenenden), zusätzlich gibt es **13** nicht indexierte Dateien. Darunter liegen separate Card-Development-Spikes und Tests. Die unveränderte Quelle darf nicht einfach vollständig als `main@8ca490a` bezeichnet werden.
- Das Archiv enthält eine lokale **`.env`** und die vollständige `.git`-Ablage. **Keine** privaten Einstellungen, Git-Metadaten, Secrets oder der archivierte Code selbst werden mit dieser Dokumentationsänderung ins ComfyReview-Repository übernommen.
- **Keine SQLite-Laufzeitdatenbank** (`.db`, `.sqlite`, `.sqlite3`) ist im ZIP enthalten. Ein Live-Daten-Cutover lässt sich damit nicht rekonstruieren. Die Python-Dateien wurden ausschließlich **statisch** geprüft (390/390 mit `ast.parse` ohne Syntaxfehler); **keine alten Tests oder Dienste wurden ausgeführt**.

Alle folgenden Pfade beziehen sich auf den Root `CharacterChronicle/` **innerhalb des lokal bereitgestellten ZIP**. Sie sind **keine Links zu gegenwärtigen ComfyReview-Quelldateien**.

## Historisch vorhandene technische Implementierung

| Damaliger Bereich | Sichtbare Quellbelege im ZIP | Evidenz und Grenze |
| --- | --- | --- |
| FastAPI-/vNext-HTTP-API | `app.py` registriert `routers/vnext_router.py`; der Router enthält **153 HTTP-Route-Dekoratoren** | **Code vorhanden und in damaliger App verdrahtet**; nicht dadurch real operativ abgenommen |
| Kampagnen und Bildentwicklung | `services/vnext/campaign.py`, `chronicle.py`, `campaign_action.py`, `trial_runtime.py` und passende Tests | Persistenz-/Director-/Review-/Trial-Methoden existierten tatsächlich, nicht bloß in Konzepten |
| Generator/ComfyUI | `generation_submission.py`, `image_pipeline.py`, `output_ingest.py`, `m6_pipeline.py`, `integrations/comfyui/` | Alte Generation-/Handoff-Runtime vorhanden; **nicht** mit dem jüngst überarbeiteten ComfyReview-Generator gleichsetzen |
| KI-/Lern-/Retrieval-Vorarbeiten | `adaptive_learning.py`, `learning_cycles.py`, `m6_pipeline.py`, `lm_studio.py`, `embeddings.py`, `reference_racks.py`, `orchestration.py` | Implementierungs- und Testcode vorhanden; **vollständig praktisch nachgewiesener Zwei-Zyklen-Loop nicht belegt** |
| Worker-/Prozessrollen | `services/vnext/runtime_process.py`, `worker_fencing.py`, `workers/` | Multi-Prozess-/Job-Grenzen im alten Code vorhanden; keine dauerhaft verbindliche Zieltopologie |
| SQLite | `stores/vnext_store.py` deklariert `SCHEMA_VERSION = 58`, Migrationspfade 52→58, weitere `stores/vnext_schema53.py` bis `vnext_schema58.py` | **Historischer vNext-Schema-Code**, **nicht** ComfyReview Canonical SQLite **v18**, keine nachgewiesene Live-DB |
| Frontend | `frontend_vnext/package.json`, `frontend_vnext/src/main.ts`, `screens.ts`, TS-/Playwright-Dateien | Tatsächliche **Vite-/TypeScript-Implementierung** in der damaligen Codebasis; heutiges ComfyReview nutzt eine andere Oberfläche |
| Card-Development-Spikes | `services/vnext/card_development_prompt.py`, `scripts/card_development_*_spike.py`, `tests/test_card_development_prompt.py` | **Zusätzliche nicht Git-indexierte Arbeitsdateien im Archiv** – separate Experimente, kein nachweislich gemergtes Produktfeature |
| Vollständige Academy/VN/Social/Game-Umsetzung | Umfangreiche Produkttexte und einzelne Runtime-Grundlagen | **Nicht** aus dem Quellbaum/den vorhandenen Tests als komplett fertig bewiesen; damalige Roadmap beschreibt M7–M9 und Chronicle-Slices weiterhin als Folgeschritte |

Eine Funktionsdefinition oder registrierte Route belegt Quellcode, aber **nicht** das Bestehen eines realen Abnahmelaufs mit privater Datenbank, ComfyUI/LM Studio, Spielertests und zwei vollständigen Review-Folgezyklen.

## Historischer Abnahme- und Defizitstand

- `README.md` (Stand: 2026-08-31) berichtet **M0–M5 abgenommen** und **M6.1–M6.7 automatisiert verifiziert**, setzt aber `M6_LEARNING_LOOP_PROVEN` als **nächsten noch offenen praktischen Produktbeweis**.
- `docs/mvp/acceptance/m6.7/02-rolling-loop.md` (Stand: 2026-09-12) enthält zahlreiche konkrete Test-/Migrationsnachweise, hält jedoch den **vollständigen Live-Zwei-Zyklen-Beleg** mehrfach ausdrücklich offen. Insbesondere nennen die späteren Ergänzungen `LIVE_VERIFICATION_PENDING` und teilweise `IMPLEMENTATION_IN_PROGRESS`; **kein** automatischer Test setzt den Nutzerabnahme-Marker.
- `docs/mvp/known-issues/m6-schema55-v10-loop-recovery.md` (Stand: 2026-09-14) nennt technische Fehlerursachen für die alte M6-Pipeline und den Status **FIX_IMPLEMENTED / LIVE_VERIFICATION_PENDING**.
- `docs/mvp/decisions/foundation-traceability-and-gaps.md` unterscheidet implementierte Grundfunktionen, offen gebliebene echte Live-Abnahmen und nachrangige Zielanforderungen.

Diese Dokumente sind **historische Selbstberichte mit überprüfbarem zugehörigem Code**, keine nachträglich durchgeführten Hardware-/Spielertests. Als Grund für die technische Verwerfung ist die Nutzerentscheidung zur **falschen Gesamtrichtung** maßgeblich; die ZIP allein beweist **nicht**, dass jeder POC technisch gescheitert wäre.

## Importierte Konzepte direkt mit dem Quellstand abgeglichen

Im ZIP stehen **25** Dateien unter `docs/mvp/product/`. Im Dokumenten-Commit `76d71f9` wurden **24** gleichnamige Produktdateien nach ComfyReview importiert. Die Git-Blobhash-Prüfung ergibt:

- **14/24 sind byteidentisch.** Insbesondere viele Card-Battler-, Chronicle-Netzwerk-, M6-Lernloop- und Orchestrierungsdokumente.
- **10/24 unterscheiden sich** vom ZIP-Stand: `baseline-and-entry-gates.md`, `frontend-information-architecture.md`, `game-modes-and-guided-evidence.md`, `generation-profiles-and-trials.md`, `llm-rag-and-recovery.md`, `player-facing-terminology-and-voice.md`, `story-cast-and-simulation.md`, `target-architecture.md`, `visual-assets-quests-and-gates.md` und `year-end-lora-and-new-game-plus.md`.
- **Zusätzlich nur im ZIP-Produktordner:** `docs/mvp/product/historical-reference-bootstrap-and-evaluation.md`. Es wurde nicht unter den 24 Dateien in ComfyReview importiert.

**Konsequenz:** Die späteren importierten Texte **nicht** aus dem älteren ZIP ersetzen. Eine Byte-Differenz beweist eine abweichende Fassung, nicht für sich allein, welche Produktentscheidung inhaltlich gültig ist.

## Zuvor als fehlend bezeichnete Quellen sind jetzt lokalisierbar

Die Dateien sind **im ZIP vorhanden**, aber **nicht** im laufenden ComfyReview-Git-Tree:

| Referenz aus importierten Konzepten | Originalpfad in `CharacterChronicle.zip` |
| --- | --- |
| Foundation-Grundlage | `docs/mvp/foundation/README.md` |
| Adaptives Lernen | `docs/mvp/foundation/adaptive-generation-learning.md` |
| Game-Mode-State-Machines | `docs/mvp/foundation/initial-game-mode-state-machines.md` |
| M4-Abnahme | `docs/mvp/acceptance/m4/README.md` |
| M6.7-Lern-/Live-Nachweis | `docs/mvp/acceptance/m6.7/02-rolling-loop.md` |
| Historische Referenzbewertung | `docs/mvp/product/historical-reference-bootstrap-and-evaluation.md` |
| Entscheidungs-/Gap-Matrix | `docs/mvp/decisions/foundation-traceability-and-gaps.md` |
| Gesamte frühere Roadmap | `docs/mvp/roadmap.md` |

Damit ist die **Herkunftslücke für diese Dateien geklärt**. Es besteht weiterhin **keine Verpflichtung**, die alten Architektur-/Acceptance-Dokumente als aktuelle Verträge zu kopieren. Sie sollten **nur bei konkretem Vergleichsbedarf** aus der ursprünglichen Quelle geprüft und mit `HISTORICAL` / `REJECTED` / `POC_RESULT` eingeordnet werden.

## Konsequenzen für die fortlaufende Entwicklung

1. **ComfyReview aktuell** bleibt der gültige Implementierungs-Ist-Stand – insbesondere [Generator- und DB-Arbeit](../ACTIVE_WORK.md) sowie [aktiver Card-Battler-POC](../pocs/card-battler.md).
2. **Character Chronicles** bleibt die langfristige Vision, **keine losgelöste unbekannte Zweit-App** und **keine automatische Wiederherstellung des ZIP-Codes**.
3. Alte Vite-/TypeScript-Shell, M6-Guardian-/Worker-Lanes, Schema 58, technische Review-/Gate-Ketten und feste Ausbaureihenfolgen sind **historische Optionen/Verwerfungsgegenstände**, nicht Default-Architektur. Fachliche Ideen können separat weiterbestehen.
4. **Nicht sensible Originalquellen sollen nur dann** in aktuelle Dokumente übernommen werden, wenn eine konkrete neue Entscheidung die Relevanz begründet und die Provenienz klar bleibt.
5. Über den realen Nutzen, die damalige Akzeptanz und die Ursachen einzelner Fehler lässt sich aus statischem Code plus historischen Selbstberichten **nicht alles** entscheiden. Für einen neuen POC braucht es neue Evidenz.

[Produktentwicklung](../PROJECT_EVOLUTION.md) · [Entscheidungsregeln](../DECISION_POLICY.md) · [Herkunftsmatrix der 24 Konzepte](sources/SOURCE_RELATIONSHIP.md).
