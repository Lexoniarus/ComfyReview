# Dokumentation: Realität, Experimente und Vision auseinanderhalten

**Dokumentklasse:** `GOVERNANCE` – Dokumentklassen und Verbindlichkeitsgrenzen.

**Stand:** 2026-10-09. ComfyReview wird weiterhin entwickelt und soll sich **langfristig zu Character Chronicles** entwickeln. Die Technik wird mit POCs überprüft; Konzepte werden nicht automatisch zum Implementierungsvertrag.

## Welche Dokumente beantworten welche Frage?

| Kategorie | Führende Dokumente | Bedeutung |
| --- | --- | --- |
| **CURRENT_CODE** | [Code-Ist-Audit](IMPLEMENTATION_AUDIT.md), [Architektur](ARCHITECTURE.md), [Datenarchitektur](DATA_ARCHITECTURE.md) | Funktion im ComfyReview-Branch mit Pfad/Commit nachweisbar |
| **IN_PROGRESS / POC** | [Aktive Arbeit](ACTIVE_WORK.md), [POCs](pocs/README.md) | Erprobung, Refactoring oder Betrieb im Fluss, nicht automatisch fertig |
| **VISION / CANDIDATE** | [Projektentwicklung](PROJECT_EVOLUTION.md), [Character Chronicles](character-chronicles/README.md) | Fachliche Ideen und prüfbare Möglichkeiten |
| **HISTORICAL / REJECTED / SUPERSEDED** | [Archiv](archive/README.md), [alter Chronicle-Code-Audit](character-chronicles/HISTORICAL_CODE_AUDIT.md), [früherer Entwurf](character-chronicles/history/full-mvp-draft-2026-08.md) | Frühere tatsächlich gebaute oder behauptete Lösungen, **keine** automatische heutige Vorgabe |
| **OPEN** | [Offene Entscheidungen](OPEN_DECISIONS.md) | Noch nicht geklärte Fragen, keine Milestone-Liste |

[Entscheidungsstatus ausführlich](DECISION_POLICY.md).

## Technischer Status versus Product Outcome

- **Code vorhanden:** Modul/Modell existiert.
- **Getesteter POC:** Tests belegen einen abgegrenzten Algorithmus oder Adapter.
- **Runtime-wired:** Service und Router/Frontend sind aktiv angebunden.
- **Operativ abgenommen:** Konkrete lokale Daten, Provider, Benutzer-/Releasefreigabe nachgewiesen.
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
- `docs/character-chronicles/sources/`: fachliche und technische **Quellen**, deren alte Autoritätsmetadaten nicht übernehmen.
- `docs/character-chronicles/vision/`: **kurze aktuelle fachliche Arbeitsvision** ohne alte technische Pflichtvertrags-Formulierungen.
- `docs/character-chronicles/sources/`: **importierte ausführliche Quelltexte**, Originalaussagen zur Verbindlichkeit gelten nur im damaligen Quellkontext.
- `docs/archive/`: alte Status-, Refactor- und README-Protokolle, ausdrücklich historisch.

Relative Markdown-Links vom Quellpfad aus prüfen; Archivtexte bei Anpassungen möglichst nicht semantisch überschreiben, sondern durch Kontext-Banner einordnen. CI-Ergebnisse nur mit Commit/Run zitieren; lokale Datenbank-/Hardware-Aussagen nicht aus Testcode extrapolieren. **Keine Meilensteine oder Design-Festlegungen erfinden**, solange das Experiment und die Entscheidung offen sind.

## Qualitätsprüfung dieser Bereinigung (2026-10-09)

Geprüft auf dem Dokumentationsbranch `docs/structure-and-status-2026-10-09`:

- **63 Markdown-Dateien**, 645 durch den einfachen Markdown-/Referenzlink-Scanner erfasste Linkangaben: **keine fehlenden relativen Dateiziele** im geprüften Git-Tree. Externe URLs und absolute GitHub-Heading-Anker wurden dadurch **nicht** umfassend validiert.
- Zwei erkennbar veraltete interne Überschriftenanker in importierten Quelltexten wurden repariert; die verbleibenden intern referenzierten Hauptkapitel (`gewonnene-reihenfolge-aus-den-bisherigen-versuchen` und `fehlende-vorgängerquellen`) sind im Zieltext vorhanden.
- Die **24 ausführlichen Konzepttexte** liegen ausschließlich unter `character-chronicles/sources/` als `SOURCE_MATERIAL`. Frühere „verbindlich“-Behauptungen werden jeweils ausdrücklich als **übernommene Quellenfassung** markiert, nicht als aktuelle Festlegung.
- Das aktuelle Zielbild liegt **getrennt** unter `character-chronicles/vision/`: Card Battler → Social/Chats → Academy/Schuljahr → visuelle VN zuletzt, mit POC-getriebener Anpassung.
- Aktuelle Implementierung/POC/Status/Datenbankbetrieb und lange historische Operator-/Refactor-/README-Protokolle haben **getrennte Dokumente und klare Zuständigkeiten**.
- Der Stand von ComfyReview ist ausdrücklich **nicht fertig**. Codeunterstützung für Schema v18 ist kein Beleg für private Live-DB-Cutover-Abnahme. Der frühere, verworfene Chronicle-Code ist als historische Quelle dokumentiert, nicht als aktuelle Architektur.

**Nicht als erledigt behauptet:** semantische Satz-für-Satz-Abnahme aller überlieferten, teils widersprüchlichen Quellen, fachliche Freigabe der gesamten künftigen Spielmechanik, GitHub-/externe Linkziele, Real-Hardware-/privater-Datenbank-Smoke oder ein neuer erfolgreicher CI-Lauf auf dem finalen Dokumentations-Commit. Die strukturelle Konsistenzprüfung ersetzt keine dieser Prüfungen.

Bei späteren Änderungen müssen die jeweiligen Dokumenttypen nach `CURRENT_CODE`, `IN_PROGRESS`, `WORKING_VISION` oder `SOURCE_MATERIAL` aktualisiert und die relativen Links erneut geprüft werden.
