# Bestätigte Rahmenbedingungen und Entscheidungsstand

**Dokumentklasse:** `DECIDED_FOR_SCOPE` · **Rolle:** Übersicht aktueller bestätigter Vorgaben, mit **separat gekennzeichneten unverbindlichen Präferenzen und CANDIDATE-Vorschlägen**. Enthält **scopebezogene** Entscheidungen und bewusste
Abgrenzung zu Präferenzen, POC-Zielen und technischen Vorschlägen.  
**Stand:** 2026-10-09 · **Produktentwicklung:** ComfyReview soll über POCs
langfristig zu Character Chronicles werden. **Keine** Abnahme einer
Implementierung und **kein** verbindlicher Gesamtarchitektur- oder Releaseplan.

Für die **Regeln zur Bestätigung neuer Entscheidungen** gilt
[Decision Policy](DECISION_POLICY.md). Die **noch offenen Fragen** stehen in
[Open Decisions](OPEN_DECISIONS.md). Historische „DECIDED“- oder M6-Verträge
werden **nicht** hierher übernommen, nur weil sie früher so benannt wurden.

## Bestätigte Vorgaben – DECIDED_FOR_SCOPE

### KI-API-Kosten: eine gemeinsame Monatsobergrenze

- **Geltungsbereich:** Sämtliche **kostenpflichtigen externen KI-API-Aufrufe**
  für die Entwicklung und spätere Nutzung von **ComfyReview → Character
  Chronicles**, ausdrücklich einschließlich **Card Battler**,
  Modellerprobungen, Tests, Prompt-/Modellvergleichen, gezielten
  Entwicklungsabfragen und späterer App-Nutzung.
- **Bestätigte Budgetgrenze:** **Insgesamt unter 10 € pro Monat** für
  **alle diese Aufrufe zusammen**. Kein separates Monatsbudget je Feature,
  Provider, Test oder Entwicklungsphase.
- **Nicht daraus ableiten:** Ein bestimmter Provider, Modelltyp,
  Datenbankschema, Abrechnungskalender, Messverfahren oder fertiger
  technischer Ausgabestopp ist dadurch **noch nicht implementiert oder
  entschieden**.
- **Geltung/Änderung:** Diese Budgetgrenze bleibt für den genannten Umfang
  relevant, bis der Projektinhaber sie ausdrücklich ändert; neue POCs
  erhalten nicht stillschweigend einen zweiten Kostentopf.

## Aktuelle Ziele und Arbeitspräferenzen – keine Architekturverträge

- **Kostenwunsch:** Möglichst **1–3 € pro Monat** statt Ausreizen der
  10-€-Obergrenze. Das ist ein **Optimierungsziel**, keine zweite harte Grenze.
- **Arbeitsweise:** Bevorzugt lokale Python-/SQL-/ComfyUI-/LM-Studio-
  Verarbeitung und künftig keine externen Coding-Agenten als regulärer
  Entwicklungsweg. Das legt **keine** bestimmte spätere App-Architektur
  oder obligatorische Modellwahl fest.
- **Modell-/Request-Effizienz:** Qualität **und** Gesamtkosten je
  erfolgreicher Aufgabe betrachten; knappen zielgerichteten Kontext
  und strukturierte Antworten bevorzugen, Tokenumfang reduzieren und
  unnötige Agenten-Schleifen vermeiden. Konkrete Provider-, Prompt- und
  Tokenlimits bleiben prüfbare Optionen.
- **Card-Battler-Erstversuch:** Der aktuelle
  [POC](pocs/card-battler.md#konkreter-erstversuch-eine-karte-von-der-bildwahl-bis-zur-sammlung)
  verwendet **ein Quellbild**, erstellt Karteninhalt und **vier passende
  Bildalternativen**, lässt **eine** auswählen und erlaubt später eine
  Entwicklung derselben Karte. **40 Karten** sind das erste Testdeck-Ziel,
  **nicht** die global beschlossene Deckgröße oder ein fertig
  implementierter Funktionsumfang.
- **Produktrichtung:** **Ungefähre Arbeitsorientierung:** Card Battler
  zuerst, danach Timeline, Social Network mit Charakter-Chats, Storyline
  und **VN-Content zuletzt**. Academy/Schuljahr ist ein möglicher
  Story-/Weltkontext, **keine zusätzlich beschlossene Pflichtphase**.
  Siehe [Project Evolution](PROJECT_EVOLUTION.md). Diese Orientierung
  ist eine **Arbeitspräferenz**, kein starrer Milestone- oder
  Architekturvertrag.

## Noch nicht beschlossene Schutzoptionen – CANDIDATE

Die folgenden Maßnahmen wurden als **Schutzstrategie vorgeschlagen**,
aber nicht als fertig implementierter Schutz oder feststehende Architektur
bestätigt:

- App-seitig neue **kostenpflichtige** Anfragen bereits bei
  **ungefähr 8 € erfassten Monatskosten** stoppen und einen Puffer
  von **ungefähr 2 €** für verzögerte Abrechnungen vorsehen.
- Ergänzende Budget-/Ausgabenbegrenzungen beim jeweiligen Provider.
- Auch kostenpflichtige **Entwicklungsabfragen außerhalb der App** in
  derselben Gesamtrechnung erfassen. **Eine App-Sperre allein kann
  solche externen Aufrufe nicht kontrollieren.**

Die tatsächliche Durchsetzung der bestätigten **unter-10-€-Grenze** ist
eine **offene technische und operative Aufgabe**. Aus diesem Text
folgt keine Behauptung, dass bereits eine Zählung, Sperre oder
Providerkontrolle existiert.

## Was offen bleibt – OPEN

**Nicht festgelegt** sind insbesondere genaue Provider-/Modellwahl,
Kosten- und Tokenmessung, Abrechnungs- und Fehlertoleranzmechanismen,
Automatisierung einer Sperre, App-Runtime und Datenhaltung für KI-Aufrufe.
Ebenso wenig entscheidet das Budget über Card-Battler-Regeln,
Social-/Academy-Systemarchitektur, VN-Renderer oder den Umgang mit
historischen Chronicle-Schemata.

**Pflege:** Bestätigte Rahmenbedingungen nur bei einer **ausdrücklichen
neuen, scopebezogenen Entscheidung** ändern. Experimentergebnisse gehören
zunächst in POC-Dokumente; technische Möglichkeiten bleiben
`CANDIDATE`, bis sie für einen konkreten Bereich bestätigt und
am Code/Verhalten geprüft wurden.
