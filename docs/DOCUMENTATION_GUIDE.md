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
| **WORKING_VISION** | [Chronicles-Zielbild](character-chronicles/vision/README.md) | Fachliche Absicht, keine endgültige Technikentscheidung |
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
