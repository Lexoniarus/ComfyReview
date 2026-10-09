# Umgang mit Architektur-, Konzept- und POC-Entscheidungen

**Dokumentklasse:** `GOVERNANCE` – nur explizite, scopebezogene Entscheidungen sind bindend.

**Ziel:** Aus früheren Architektur-Sackgassen lernen, ohne sie durch Dokumentation dauerhaft mitzuschleppen. ComfyReview ist in Entwicklung; Character Chronicles ist die langfristige Richtung, **kein unveränderliches Pflichtenheft**.

## Für jede Aussage unterscheiden

**Aussagenstatus ist nicht Dokumentklasse.** Diese Tabelle ordnet einzelne
Entscheidungen, Hypothesen und Belege ein. Die **Dokumentklassen** und ihre
führenden Dateien stehen in der [Dokumentationslandkarte](README.md) und im
[Dokumentationsleitfaden](DOCUMENTATION_GUIDE.md). Eine aktuell markierte
Quelle oder ein Index kann historische `DECIDED`-Zitate enthalten, ohne
dass diese dadurch wieder gültig werden.

| Kennzeichnung | Bedeutung | Verbindlichkeit |
| --- | --- | --- |
| **CURRENT_CODE** | Verhalten ist an einem konkreten ComfyReview-Commit nachweisbar | Beschreibung des Ist-Codes; kann künftig refaktoriert werden |
| **IN_PROGRESS** | Entwicklung/POC/Refactor läuft; Ergebnis noch offen | Keine Produktabnahme |
| **POC_RESULT** | Experiment/Tests zeigen einen begrenzten Sachverhalt | Aussage nur innerhalb des geprüften Scopes |
| **VISION** | Gewünschtes Spielerlebnis, Narrativ, Funktion oder möglicher Zielzustand | Inhaltliche Orientierung; Ausführung und Priorität offen |
| **CANDIDATE** | Konkrete technische oder fachliche Option zur Prüfung | Nicht beschlossen |
| **DECIDED_FOR_SCOPE** | Für einen **benannten aktuellen Kontext** ausdrücklich getroffene Entscheidung mit Begründung | Nur für diesen Kontext verbindlich; kein globaler Altlastentransfer |
| **SUPERSEDED / REJECTED** | Frühere Annahme oder technische Lösung wurde ersetzt/verworfen | Historische Quelle; **nicht** in neue Architektur kopieren |
| **HISTORICAL_CLAIM** | Alter Implementierungs-/Abnahmebericht; inzwischen teilweise am Archivcode verifizierbar, aber ohne vollständige Live-Daten und Spielertests | Nur im damaligen Scope zitieren; keine heutige Produktfreigabe |

Ein bereits als „DECIDED“ oder „verbindlich“ markierter alter Entwurf bleibt zunächst **HISTORICAL_CLAIM**, bis geklärt ist, auf welchen damaligen Stand er sich bezog und ob er in der aktuellen Richtung noch passt.

## Aktuell bestätigte Rahmenbedingungen

Die [scopebezogenen bestätigten Vorgaben](CONFIRMED_CONSTRAINTS.md) stehen
getrennt von offenen Entscheidungen und historischen Konzeptverträgen.
**Inzwischen ausdrücklich bestätigt ist auch die inhaltliche
[Character-Chronicles-Zielwelt](character-chronicles/vision/world.md):**
Kobe/Japan ab 2032, zwei Academy-Jahre für Erwachsene, eine etablierte
globale Social-/Battler-Kultur, eigenständige Figuren und die langfristig
story- und beziehungsorientierte Gesamtspielabsicht. **Eine inhaltlich
bestätigte Welt ist nicht gleichbedeutend mit der Annahme historischer
M4-/M6-, UI-, Datenbank- oder Regelverträge.** Der Weg bleibt iterativ,
Weltänderungen brauchen eine neue ausdrückliche fachliche Entscheidung.
Daneben ist die **eine gemeinsame Monatsobergrenze von unter 10 €**
für externe KI-API-Aufrufe im ComfyReview-/Character-Chronicles-Vorhaben
festgehalten. Sie umfasst Entwicklungsexperimente und spätere Nutzung.
Ein vorgeschlagener App-seitiger Stopp bei ungefähr 8 € ist dagegen eine
**noch nicht bestätigte Schutzoption**, kein bereits bestehender Mechanismus.
Präferenzen und aktuelle POC-Ziele werden ausdrücklich **nicht** zu festen
Datenbank-, Provider- oder Spielregeln erklärt.

## Besondere Altlast: früherer Character-Chronicles-Stand

Es gab einen **verworfenen früheren Character-Chronicles-Implementierungsstand**. In importierten Dokumenten tauchen dazu ein Vite-/TypeScript-Frontend, Chronicle-Events, M6-Planung, Schema-44-bis-58-Aussagen und umfassende Guardian-/Orchestrierungsannahmen auf. Deren Quellcode befindet sich **nicht** im aktuellen ComfyReview-Tree,
liegt aber als [historischer Arbeitsstand in `CharacterChronicle.zip`](character-chronicles/HISTORICAL_CODE_AUDIT.md)
vor und wurde statisch geprüft. So sind die alte Campaign-/Trial-/M6-
Implementierung und das Vite-/TypeScript-Frontend tatsächlich belegbar.
Der praktische Gesamtbeweis und einzelne Live-Abnahmen waren trotzdem
laut den historischen Unterlagen **offen**.

**Technisch damals implementiert ≠ heute architektonisch sinnvoll.**

**Regel:** Fachliche Ideen dürfen zur erneuten Prüfung dienen. Alte Architektur, Persistenzverträge, Abnahmelogik und Release-/Gate-Reihenfolgen **nicht** ungeprüft übernehmen. Verwerfen eines technischen Ansatzes bedeutet nicht automatisch Verwerfen der narrativen/mechanischen Idee dahinter.

## Nur echte Entscheidungen festhalten

Eine spätere Architekturentscheidung sollte mindestens enthalten:

1. **Kontext/POC**, Datum und Problem (z. B. Card-Battler-Entwicklung im aktuellen ComfyReview-Code);
2. **Beobachtungen** und konkrete Code-/Test-/Bedienbelege;
3. **Alternativen**, auch „neu entwerfen / gar nicht übernehmen“;
4. **Entscheidung und Grenzen**, ausdrücklich bestätigt (oder klar **noch offen**);
5. **Revisit-Bedingung**: Wann und durch welchen neuen POC die Entscheidung wieder geprüft wird.

Es entsteht **nicht** allein durch Sortieren von Dokumenten ein verbindlicher Meilensteinplan. Konzeptumfang, MVP und genaue Reihenfolge für Character Chronicles sind nicht beschlossen.

## Bestehende Dokumente

- [ComfyReview-Ist-Code](IMPLEMENTATION_AUDIT.md)
- [Laufende Arbeiten](ACTIVE_WORK.md), [Card-Battler-POC](pocs/card-battler.md)
- [Character-Chronicles-Zielmaterial](character-chronicles/README.md)
- [Früherer Card-Battler-Zielplan](archive/card-battler-target-2026-10-02.md)
- [Bestätigte Rahmenbedingungen](CONFIRMED_CONSTRAINTS.md)
- [Abgleich der früher fehlplatzierten CRCC- und POC-IDs](DECISION_POC_RECONCILIATION.md) – Herkunft, keine neue Beschlussautorität
- [Status und offene Fragen](OPEN_DECISIONS.md)
