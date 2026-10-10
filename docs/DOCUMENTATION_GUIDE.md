# Dokumentation: Realität, Experimente und Vision auseinanderhalten

**Dokumentklasse:** `GOVERNANCE` – Dokumentklassen und Verbindlichkeitsgrenzen.

**Stand:** 2026-10-09. ComfyReview wird weiterhin entwickelt und soll sich **langfristig zu Character Chronicles** entwickeln. Die Technik wird mit POCs überprüft; Konzepte werden nicht automatisch zum Implementierungsvertrag.

## Dokumentklassen, führende Stellen und Geltung

Die [Dokumentationslandkarte](README.md) ist die **führende
Zuständigkeitsübersicht**. Hier gelten dieselben Klassen; eine **Rolle** wie
„Index“, „Operatorbericht“ oder „Refactor-Abnahme“ ist **keine neue
Verbindlichkeitsstufe**.

| Dokumentklasse | Führende Dokumente | Bedeutung |
| --- | --- | --- |
| **CURRENT_CODE** | [Code-Ist-Audit](IMPLEMENTATION_AUDIT.md) | Nachweisbarer Code **am benannten Commit**, nicht automatisch operativ abgenommen |
| **CURRENT_STATUS** | [Projektstatus](project_status.md); [Refactor-Abnahme](REFACTOR_PLAN.md) nur im Teilbereich | Aktueller Status und offene Abnahmen, **nicht** alte Slice-Chronik |
| **IN_PROGRESS** | [Aktive Arbeit](ACTIVE_WORK.md), [POCs](pocs/README.md) | Laufende Entwicklung und Experimente, kein fertiges Product Outcome |
| **WORKING_DIRECTION** | [Projektentwicklung](PROJECT_EVOLUTION.md) | Prioritätsrichtung, keine starren Milestones |
| **WORKING_VISION** | [Bestätigte Zielwelt](character-chronicles/vision/world.md), [Gesamtvision](character-chronicles/vision/README.md) | Der Weltkern ist fachlich `DECIDED_FOR_SCOPE`; exakte technische Umsetzung ist noch offen |
| **DECIDED_FOR_SCOPE** | [Bestätigte Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md) | Bestätigte Vorgaben **nur im erklärten Geltungsbereich**; dort separat markierte Kandidaten bleiben offen |
| **OPEN** | [Offene Entscheidungen](OPEN_DECISIONS.md) | Nur ungelöste Entscheidungen, nicht zweiter Projektstatus |
| **CURRENT_TECH_REFERENCE** | [Architektur](ARCHITECTURE.md), [Datenarchitektur](DATA_ARCHITECTURE.md), [Frontend V2](FRONTEND_V2_DESIGN.md) | Technische Verträge für den **gegenwärtigen ComfyReview-Code**, nicht für jede spätere Chronicles-Version |
| **CURRENT_OPERATIONS** | [Operations](OPERATIONS.md), [Legacy-Output-Import](LEGACY_OUTPUT_IMPORT.md) als Detail | Heute gültige CLI und vorsichtige Wartungsverfahren, auch für historische Daten |
| **ENGINEERING_RULES** | [AGENTS](../AGENTS.md), [Coding Standards](CODING_STANDARDS.md) | Regeln für neuen/geänderten aktuellen Code |
| **GOVERNANCE** | Dieser Leitfaden, [Decision Policy](DECISION_POLICY.md) | Dokumenten- und Entscheidungsregeln |
| **SOURCE_MATERIAL** | [Importierte Quellen](character-chronicles/sources/README.md), [Herkunftsmatrix](character-chronicles/sources/SOURCE_RELATIONSHIP.md) | Frühere Texte und ihre Quellenzuordnung, **keine** aktive Spezifikation |
| **HISTORICAL_EVIDENCE** | [Alter Chronicle-Code-Audit](character-chronicles/HISTORICAL_CODE_AUDIT.md), [Archiv](archive/README.md) | Frühere Entwürfe, technische Nachweise, veraltete Vertragsaussagen |
| **HISTORICAL_LOG** | [Archivierter Refactor-Verlauf](archive/refactor-slice-history-2026-10-09.md), [frühere Operatorberichte](archive/project-status-log-2026-10-09.md) | Zeitgebundene damalige Slices/Operationen, **kein** aktueller Status |

**Wichtig:** Eine **Dokumentklasse** ordnet den Gesamttext ein.
Ein **Aussagenstatus** wie `CANDIDATE`, `POC_RESULT`, `DECIDED_FOR_SCOPE`
oder `REJECTED` klassifiziert nur die jeweilige Aussage. Zitate aus
`SOURCE_MATERIAL` behalten selbst dann **keine aktuelle Verbindlichkeit**,
wenn sie in der Originalquelle „DECIDED“ heißen.

[Entscheidungsstatus ausführlich](DECISION_POLICY.md).

## Technischer Status versus Product Outcome

- **Code vorhanden:** Modul/Modell existiert.
- **Getesteter POC:** Tests belegen einen abgegrenzten Algorithmus oder Adapter.
- **Runtime-wired:** Service und Router/Frontend sind aktiv angebunden.
- **Automatisch geprüft:** CI/Entwicklertests haben einen benannten Commit
  getestet; das ist **keine** abschließende Nutzerabnahme.
- **Abschließend manuell getestet und abgenommen:** Der **Projektinhaber**
  hat die tatsächlichen UI-/Funktions-/Providerabläufe selbst getestet und
  die Abnahme ausdrücklich bestätigt; bei Datenmigrationen zusätzlich
  den konkreten privaten Datenbestand und die operativen Schritte.
- **Langfristige Vision:** ausdrücklich **keine** technische Fertigstellungsbehauptung.

Den technischen Ist-Zustand des Dokumenten-Imports gegen [`a5f4131`](https://github.com/Lexoniarus/ComfyReview/commit/a5f4131bb76c1ff655892d287d19fcd401917d32) prüfen; [`76d71f9`](https://github.com/Lexoniarus/ComfyReview/commit/76d71f9c7723701664785aeaf07e0d7375a4f36a) fügte Inhalte ohne Änderung der Anwendungsmodule hinzu. Der Branch entwickelt sich anschließend weiter: Einen früheren Commit nicht endlos als „heute aktuell“ zitieren, wenn neue Commits vorliegen.

## Keine Architektur-Altlasten automatisch mitschleppen

Es gab einen **früheren, verworfenen Character-Chronicles-Implementierungsansatz**.
Dessen Code und die zuvor fehlenden Foundation-/M4-/M6.7-Unterlagen liegen
jetzt im bereitgestellten `CharacterChronicle.zip` tatsächlich vor.
[Historische technische Bestandsaufnahme](character-chronicles/HISTORICAL_CODE_AUDIT.md).
Das Archiv enthält **auch `.env` und `.git`**, daher keinesfalls
vollständig ins aktuelle Repository übernehmen. Selbst nachweisbarer
damaliger Code wird **nicht** automatisch heutiger ComfyReview-Code
oder eine verbindliche Character-Chronicles-Architektur.

 Die importierten Kapitel enthalten dazu alte UI-/Schemata-/M6-/Orchestrierungs-/Abnahmeaussagen. Ihre damaligen „DECIDED“, „autoritativer Vertrag“ oder „Baseline abgeschlossen“ sind **keine automatisch gültigen Festlegungen**. Der frühere Code ist in diesem ComfyReview-Branch nicht als aktuelle Implementierung vorhanden.

Trenne **Idee/Spielerlebnis**, **technische Hypothese**, **POC-Ergebnis**, **abgesagte Architektur** und **für einen konkreten aktuellen Scope bestätigte Entscheidung**. Auch ComfyReviews aktuelle Schichten-, Browser- und Datenbankentscheidungen gelten für den **gegenwärtigen Code**, nicht zwingend unverändert für Character Chronicles.

Eine neue, bindende Entscheidung braucht einen konkreten Scope, Alternativen, Belege, Entscheidung und Revisit-Kriterium. Sie darf einen alten Vertrag ablehnen oder ersetzen. Siehe [Decision Policy](DECISION_POLICY.md).

## Schreibregeln

- Root `README.md`: praktikabler ComfyReview-Einstieg; nicht das umfangreiche Zukunftskonzept.
- `docs/project_status.md`: tatsächlicher Source-Status plus ausdrücklich offene Abnahmen.
- `docs/ARCHITECTURE.md` und `docs/DATA_ARCHITECTURE.md`: implementierter Code und aktuelle Grenzen.
- `docs/REFACTOR_PLAN.md`: knapper Refactor-/Abnahmestand; kompletter Slice-Verlauf nur im Archiv.
- `docs/OPERATIONS.md`: CLI/Import/DB-Upgrade-Prozeduren; **nicht** als angeblich ausgeführte Migration lesen.
- `docs/ACTIVE_WORK.md`: laufende Entwicklung von Generator, Datenbank/Katalog und POCs.
- `docs/character-chronicles/vision/`: **bestätigte fachliche Zielwelt**
  in `world.md` und aktuelle Arbeitsvision für die Spielbereiche.
  Keine automatische Wiederaufnahme alter technischer Pflichtverträge.
- `docs/character-chronicles/sources/`: **importierte ausführliche Quelltexte** und Herkunftsindex; alte Autoritätsmetadaten und Verbindlichkeitsbehauptungen gelten nur im damaligen Quellkontext.
- `docs/archive/`: alte Status-, Refactor- und README-Protokolle, ausdrücklich historisch.

Relative Markdown-Links vom Quellpfad aus prüfen; Archivtexte bei Anpassungen möglichst nicht semantisch überschreiben, sondern durch Kontext-Banner einordnen. CI-Ergebnisse nur mit Commit/Run zitieren; lokale Datenbank-/Hardware-Aussagen nicht aus Testcode extrapolieren. **Keine Meilensteine oder Design-Festlegungen erfinden**, solange das Experiment und die Entscheidung offen sind.

## Laufende automatisierte Dokumentationsprüfung

Für die **aktuelle** Dokumentationsstruktur steht
[`scripts/check_documentation.py`](../scripts/check_documentation.py)
zur Verfügung:

```bash
python scripts/check_documentation.py
python -m pytest tests/test_documentation_links.py
```

Die Prüfung ist über
[`tests/test_documentation_links.py`](../tests/test_documentation_links.py)
in das reguläre Pytest-/Quality-Gate eingebunden. Sie prüft
**alle gegenwärtigen Markdown-Navigationsverweise** im Root und unter
`docs/`, relative Dateiziele und Kapitelanker, 24 sichtbare
`SOURCE_MATERIAL`-Warnungen sowie die Grenze vor dem übernommenen
Originaltext. **Bei den 24 historischen Quellen wird nur der aktuelle
Vorspann geprüft**; darin enthaltene ursprüngliche Foundation-/M4-/M6-
Links werden nicht als defekte aktuelle Navigation eingestuft. Das
historische Textarchiv unter `docs/archive/` wird ebenfalls nicht
als aktiver Dokumentationsinhalt ausgewertet, seine Indexseiten jedoch schon.

Zusätzlich vergleichen die Tests die **24 übernommenen Fachtext-Originalkörper**
und **fünf historische Archiv-Originalfassungen** mit den Git-Blob-Hashes
des Ausgangsstands `76d71f9`. Warnbanner und aktuelle Einordnungen dürfen
angepasst werden; der historische Originaltext einschließlich seiner alten
Verweise darf nicht stillschweigend verändert werden. Die Checks dienen der
Herkunftstreue, **nicht** der fachlichen Freigabe historischer Aussagen.

Diese Prüfung ersetzt **keine semantische Fachfreigabe**,
keine Prüfung externer URLs und keine Abnahme von Anwendung,
Provider oder privater Datenbank. Ergebnisse gelten nur für den
jeweils geprüften Commit.

## Qualitätsprüfung der ursprünglichen Branch-Bereinigung (2026-10-09)

**Zeitgebundener Prüfbericht:** Die folgenden Mengen und Linkergebnisse
beziehen sich auf den **zuvor geprüften Dokumentations-Head**. Sie sind
nicht automatisch ein neuer Testnachweis für jede spätere
Änderung an `docs/structure-and-status-2026-10-09`. Nach
Aktualisierungen müssen aktive Links und Quellgrenzen erneut überprüft
und die Ergebnisse dem zugehörigen Commit zugeordnet werden.

Geprüft auf dem Dokumentationsbranch `docs/structure-and-status-2026-10-09`:

- **65 im PR geänderte Markdown-Dateien** plus eine archivierte TXT-Datei
  wurden am PR-Head erneut geprüft (nicht mit einem vollständigen
  Repository-Dateibaum-Audit verwechseln). Der einfache Markdown-Scanner
  erfasste **704 Inline-Linkangaben**. Alle relativen `.md`-/`.txt`-Links
  außerhalb der historischen Originaltexte zeigen auf vorhandene Ziele.
  **10 historische Linkverweise in den importierten Originaltexten** zeigen
  bewusst noch auf frühere Foundation-, M4-/M6- und Referenzdateien, die
  **nicht** im aktuellen Repository vorliegen. Diese Verweise sind im
  [Quellenindex](character-chronicles/sources/README.md) eingeordnet;
  sie wurden **nicht** durch Links auf aktuelle Produktdokumente ersetzt.
- Von **7 erfassten Kapitelanker-Links** führen die **4 aktuellen** zu
  existierenden Überschriften. Die **3 historischen** bleiben
  originalgetreu; zwei verweisen auf heute fehlende Überschriften und
  einer auf eine nicht im Repository vorhandene historische Datei.
  Externe URLs und beliebige Code-/Asset-Links sind damit **nicht**
  vollständig geprüft.
- Die zwölf früher vorgenommenen Umleitungen in **neun importierten
  Quelltexten** wurden zurückgenommen. Ihre ursprünglichen Referenztexte
  bleiben erhalten; die historischen Quelllinks dürfen **nicht** zur
  heutigen Vision oder aktuellen Implementierung umgedeutet werden.
  Die neue
  [Canonical-DB-Archivquelle](archive/canonical-data-operator-evidence-2026-10-01-to-07.md)
  bewahrt historische Live-Zahlen und source-spezifische Inventare, statt
  diese in `CURRENT_TECH_REFERENCE` als heutige Invarianten zu führen.
  Die aktive Architektur verweist auf den archivierten Projection Audit,
  die aktuelle Datenarchitektur auf Blueprint v4.
- Die **24 ausführlichen Konzepttexte** liegen ausschließlich unter `character-chronicles/sources/` als `SOURCE_MATERIAL`. Frühere „verbindlich“-Behauptungen werden jeweils ausdrücklich als **übernommene Quellenfassung** markiert, nicht als aktuelle Festlegung.
- Die bestätigte **Character-Chronicles-Zielwelt** (Kobe ab 2032,
  zwei erwachsene Academy-Jahre, globale Social-/Battler-Kultur und
  VN als langfristiger erzählerischer Kern) steht unter
  `character-chronicles/vision/world.md`. Die ungefähre
  **Implementierungsorientierung** bleibt Card Battler → Timeline →
  Social/Chat → Storyline → VN-Content zuletzt. Die Academy ist
  keine zusätzlich beschlossene **technische** Pflichtphase. Die Orientierung ist POC-getrieben und nicht starr.
- Aktuelle Implementierung/POC/Status/Datenbankbetrieb und lange historische Operator-/Refactor-/README-Protokolle haben **getrennte Dokumente und klare Zuständigkeiten**.
- Der Stand von ComfyReview ist ausdrücklich **nicht fertig**. Codeunterstützung für Schema v18 ist kein Beleg für private Live-DB-Cutover-Abnahme. Der frühere, verworfene Chronicle-Code ist als historische Quelle dokumentiert, nicht als aktuelle Architektur.

**Nicht als erledigt behauptet:** semantische Satz-für-Satz-Abnahme
aller überlieferten, teils widersprüchlichen Quellen; fachliche
Freigabe der gesamten künftigen Spielmechanik; umfassende Validierung
externer URLs, Code-/Asset-Links und GitHub-Heading-Anker; Real-Hardware-
oder privater-Datenbank-Smoke; und **CI-Erfolg für den endgültigen
Dokumentations-Head**, solange für genau dessen Commit kein erfolgreicher
Workflow nachgewiesen ist. Die strukturelle Konsistenzprüfung ersetzt
keine dieser Prüfungen.

Bei späteren Änderungen müssen die jeweiligen Dokumenttypen nach `CURRENT_CODE`, `IN_PROGRESS`, `WORKING_VISION` oder `SOURCE_MATERIAL` aktualisiert und die relativen Links erneut geprüft werden.
