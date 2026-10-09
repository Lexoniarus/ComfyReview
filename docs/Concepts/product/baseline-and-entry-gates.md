# Erreichte Baseline und Foundation-Übergabe

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 1. September 2026

## Zweck

Dieses Dokument beschreibt den erreichten bildzentrierten Ausgangspunkt und die
laufende Foundation-Arbeit. Die Chronicle-Erweiterung ist der zweite Abschnitt
desselben vollständigen MVP. `post-mvp` ist nur noch der stabile historische
Pfadname; die verbindlichen Begriffe stehen im [Ordnerindex](../README.md#verbindliche-terminologie).

## Beobachteter Bestand

Der aktuelle Arbeitsbaum besitzt bereits eine tragfähige bildzentrierte
vNext-Domäne:

| Bereich | Wiederverwendbarer Stand |
|---|---|
| Runtime | FastAPI-Server mit serverseitiger Progressionsautorität |
| Persistenz | SQLite, versionierte Snapshots, Idempotenz und append-only Chronicle Events |
| Generation | unveränderliche Generation Recipes, ComfyUI-Übergabe, Polling und Output-Ingest |
| Bildspiel | Vier-Seed-Attempts, Einzelreview, Batchreview, Fehlergründe und Retry |
| Questversorgung | drei vorgewärmte Supply-Slots pro aktueller Character-Campaign |
| Evidenz | getrennte Campaign-, Recipe-, Prompt-, Workflow- und Renderprofil-Evidenz |
| Dataset | Album-Membership, Coverage, unveränderliche Versionen und Export |
| Legacy-/Technikoberflächen | separate Render-Lab-, Rankings-, Delete-or-Live-, Arcade- und Playground-Workbench-Pfade; Implementierungsbestand, kein aktueller Game-Mode-Katalog |
| Browseroberfläche | Vite-/TypeScript-Frontend mit Character-, Album- und Nebenansichten |
| Tests | Python-Domain- und Integrationstests sowie TypeScript-/Playwright-Verträge vorhanden |

Der Character-Bereich bildet bereits eine brauchbare visuelle Basis. Die
heutige Hauptnavigation `Character`, `Album` und `Menü` ist dagegen noch kein
abgenommener Zielzustand: Album ist später ein Character-/LoRA-Unterbereich,
Resultprojektionen und Trial-Varianten benötigen eine fachliche Gruppierung,
Legacy gehört in Import/Diagnose und die Playground Workbench benötigt eine
verständliche Advanced-Einordnung. Die genannten Bestandsrouten dürfen nicht als
aktuelle Modi oder Zielseiten gelesen werden.

Die genaue Implementierungs- und Abnahmelage bleibt in
den [Foundation-Verträgen](../foundation/README.md) autoritativ. Die dort dokumentierten
Testergebnisse sind ein Snapshot und keine automatische Freigabe nach späteren
Änderungen.

## Noch nicht vorhandene MVP-Zieldomänen

Im beobachteten Code existieren noch keine vollständigen Runtime-Verträge für:

- `ChronicleRun` als zweijähriger Academy-Save mit mehreren Figuren,
- Prolog, Calendar, Day Instances und authored Story Graphs,
- Cast Assembly aus 32 geschlechtsspezifischen Schablonen,
- Personality-, Relationship-, Knowledge- und Character-Development-State,
- VN Scene Contracts und die vier unabhängigen Scene Gates,
- Visual Asset Resolver und unveränderliche Scene Visual Plans,
- parallele Questlinien, Challenger Cups und Title Matches,
- Character Speaker, Prompt Generator, Context Assembler und RAG,
- ratingbasierte automatische Recovery,
- Mehrfiguren-LoRA-Audit, Auffüllphase und NG+-Carry-over.

Diese Systeme werden ergänzt. Sie dürfen die bereits funktionierenden
Generation-, Review-, Evidenz- und Albumdomänen nicht als UI-seitige Kopien
neu implementieren.

## Foundation-Übergabepunkt

Zwischen Bildloop-Baseline und Chronicle-Ziel besteht kein separates
Produkt-Scope-Gate. M0–M9 härten die Foundation und erzeugen am Ende einen
`FOUNDATION_READY`-Checkpoint. Dieser benötigt mindestens:

1. einen benannten Commit oder unveränderlichen Baseline-Snapshot,
2. erfüllte Abnahmekriterien aus den Foundation-Verträgen,
3. grüne vereinbarte Python-, Frontend- und Browsertests,
4. einen erfolgreichen manuellen Kernloop-Playtest,
5. dokumentierte verbleibende Nicht-Blocker,
6. eine gesicherte Datenbank-Migrations- beziehungsweise Testdatenstrategie,
7. und dokumentierte Abhängigkeiten, damit Chronicle-Slices keine offenen
   Foundation-Verträge umgehen.

Dieser manuelle Kernloop-Playtest ist die praktische Gesamtfreigabe der
Foundation und kein Zwischen-Gate für M6.1 bis M6.7. Diese Teilslices werden
durch automatisierte Contract-, Persistenz-, Rebuild- und Browser-Smoke-Tests
geschlossen; die gemeinsame praktische Spielerabnahme erfolgt erst am
vollständigen `M6_LEARNING_LOOP_PROVEN`-Loop.

Zur Foundation-Übergabe gehört außerdem die Frontend-Konsolidierung aus
[`09-frontend-information-architecture.md`](frontend-information-architecture.md):

- fachlich nachvollziehbare Navigation,
- globale Content- und Generationseinstellungen,
- Einordnung von Album, Rankings, Workbench und Legacy,
- vollständige Loading-/Empty-/Error-/Blocked-Zustände,
- sowie ein dokumentierter Responsive- und Interaktionsplaytest.

Chronicle-Konzept-, Authoring-, Provider- und Schema-Spikes dürfen parallel
vorbereitet werden. Ein abhängiger Runtime-Slice gilt jedoch erst als fertig,
wenn seine benötigten Foundation-Verträge vorliegen.

## Baseline-Artefakt

Spätestens beim stabilen Übergang in die Chronicle-Slices wird ein
`MvpBaselineManifest` festgeschrieben:

```text
MvpBaselineManifest
├─ source_revision
├─ schema_version
├─ api_contract_hash
├─ prompt_contract_version
├─ workflow_versions[]
├─ automated_test_report
├─ manual_playtest_report
├─ accepted_known_gaps[]
└─ accepted_at
```

Jeder spätere Slice nennt, welche Baseline-Verträge er unverändert nutzt,
welche er erweitert und welche Migration er benötigt.

## Nicht-Ziele dieses Dokuments

- laufende Foundation-Arbeit zu bewerten,
- den aktuellen Arbeitsbaum als abgenommen zu erklären,
- bestehende MVP-Gaps neu zu priorisieren,
- oder ein zweites künstliches Produktgate einzuführen.
