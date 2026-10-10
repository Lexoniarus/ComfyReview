# Bestätigte Rahmenbedingungen und Entscheidungsstand

**Dokumentklasse:** `DECIDED_FOR_SCOPE` · **Rolle:** Übersicht aktueller bestätigter Vorgaben, mit **separat gekennzeichneten unverbindlichen Präferenzen und CANDIDATE-Vorschlägen**. Enthält **scopebezogene** Entscheidungen und bewusste
Abgrenzung zu Präferenzen, POC-Zielen und technischen Vorschlägen.  
**Stand:** 2026-10-10 · **Produktentwicklung:** ComfyReview soll über POCs
langfristig zu Character Chronicles werden. **Keine** Abnahme einer
Implementierung und **kein** verbindlicher Gesamtarchitektur- oder Releaseplan.

Für die **Regeln zur Bestätigung neuer Entscheidungen** gilt
[Decision Policy](DECISION_POLICY.md). Die **noch offenen Fragen** stehen in
[Open Decisions](OPEN_DECISIONS.md). Historische „DECIDED“- oder M6-Verträge
werden **nicht** hierher übernommen, nur weil sie früher so benannt wurden.

## Bestätigte Vorgaben – DECIDED_FOR_SCOPE

### Kontinuierliche Produktentwicklung (kein automatisch bindender Technologiepfad)

**Geltungsbereich:** Das aktuelle, weiterhin entwickelte **ComfyReview**
soll schrittweise in Richtung **Character Chronicles** wachsen. Es wird
dadurch weder ein zweites unabhängig verpflichtendes Produkt noch ein
automatischer Repository-Split oder Big-Bang-Rebuild beschlossen. Die
übernommenen Bausteine, spätere App-Struktur und Technologie bleiben
jeweils anhand von POCs und konkreten Entscheidungen zu prüfen.
[Projektentwicklung](PROJECT_EVOLUTION.md) und
[historischer Entscheidungsabgleich](DECISION_POC_RECONCILIATION.md).

### Bestätigte Character-Chronicles-Welt – DECIDED_FOR_SCOPE

**Geltungsbereich:** Die **langfristige fachliche Zielwelt und das
angestrebte Spielerlebnis**, nicht die technische Implementierung.

- **Ort/Zeit/Genre:** Japan, Haupthandlungsort **Kobe**, Einstieg
  **2032**; bodenständige **animeorientierte Near Future** ohne
  Cyberpunk-, Fantasy- oder postapokalyptische Grundprämisse.
- **Academy:** Der volljährige Protagonist zieht neu nach Kobe und
  erlebt **zwei postsekundäre Academy-Jahre** unter jungen Erwachsenen.
  Academy, Wohnen, Stadt, Familie, Clubs, Freundschaften und Zukunft
  bilden das Lebensumfeld. Die Academy ist **kein optionaler
  Weltkontext**, aber auch **keine zusätzliche Technik-Releasephase**.
- **Figuren:** Eigenständige Menschen mit Biografien, Wissen,
  Beziehungen, Wohnorten und Zielen. Das ausführliche fachliche
  Zielbild umfasst **16 Fokusfiguren** und weitere soziale Nebenrollen;
  ihre konkrete Generierung und technische Persistenz bleibt zu erproben.
- **Gesellschaft:** Eine schon vor Spielbeginn etablierte,
  generationenprägende **globale Social- und Card-Battler-Kultur**.
  Posts, bildhaft dargestellte persönliche Momente, Karten,
  direkte/öffentliche Duelle und ihre sozialen Folgen gehören
  zusammen. Zustimmung zur Verwendung persönlicher Darstellungen
  und Grenzen ihrer Öffentlichkeit gehören zur Welt.
- **Spielerlebnis:** Die **storygetriebene VN mit Dating-Sim-Elementen**
  ist langfristig der emotionale Schwerpunkt. Karten, Network,
  Chats, Alltag und Wettbewerbe sind ineinandergreifende
  Aktivitäten; **Card Battler zuerst entwickeln** ist keine
  Entscheidung, ihn zum alleinigen Hauptziel des fertigen Spiels zu machen.

[Ausführliche aktuelle Weltvision](character-chronicles/vision/world.md)
übernimmt den fachlichen Weltkern der historischen Konzepte.
Der Weg über POCs, technische Architektur, UI, Kartendaten und
Regeldetails sowie einzelne konkrete Welt-Ausprägungen können
weiterentwickelt werden. **Weder Weltkern noch langfristige
Spielerabsicht werden durch technische POCs stillschweigend
abgewählt.** Änderungen am Weltziel bedürfen einer neuen
bewussten fachlichen Entscheidung; überlieferte Schema-/M6-,
Kalender- und Phasenverträge gelten dadurch nicht automatisch.

### Späterer fachlicher Meilenstein: Spielwelt und technische Bildproduktion

**Geltungsbereich:** Das langfristige Character-Chronicles-Spielerlebnis.
Dieser Meilenstein ist **für später vorgesehen**, nicht Teil der
Abnahme des aktuellen Card-Battler-Erstversuchs.

- **Bestätigtes fachliches Ziel:** Was in der fiktiven Welt wirklich
  passiert, was Figuren erleben und wie sie sich entwickeln, ist von
  der technischen Erzeugung, Bewertung und Verbesserung der
  dargestellten Bilder unterscheidbar.
- Eine Änderung an Prompt, Modell, LoRA, Workflow, Renderqualität
  oder visueller Projektion ist **für sich genommen kein Storyereignis**.
  Sie verändert nicht automatisch das kanonische Aussehen, die
  Erinnerungen, Beziehungen oder Vergangenheit einer Figur.
  Inhaltlich gewollte Veränderungen bleiben durch ausdrücklich
  vorgesehene Spiel-/Storyentscheidungen möglich.
- Die Bewertungen des **realen Spielers** dürfen die Bildproduktion
  verbessern, ohne dass der **Protagonist oder die Figuren in der
  Spielwelt** dadurch automatisch Wissen über die Technik erlangen.
  Auch eine spielerische Rückwirkung muss fachlich autorisiert sein.

**Verbindlich ist das spätere fachliche Abnahmeziel, nicht seine
technische Realisierung.** Weder ein konkretes World-State-Schema,
ein Modell-/Providervertrag, historische M6-Prozesse, eine zusätzliche
Pflichtphase noch eine Terminplanung werden dadurch festgelegt.
[Langfristiges Zielbild](character-chronicles/vision/README.md#späterer-fachlicher-meilenstein-spielwelt-und-bildproduktion)
und [offene Umsetzung](OPEN_DECISIONS.md).

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
- **Arbeitsweise:** Lokale Python-/SQL-/ComfyUI-/LM-Studio-
  Verarbeitung bevorzugen, wo sie zur Aufgabe passt. Die Auswahl von
  Entwicklungswerkzeugen bleibt offen und orientiert sich an Eignung,
  Qualität und Kosten. Daraus folgt keine bestimmte spätere
  App-Architektur oder obligatorische Modellwahl.
- **Modell-/Request-Effizienz:** Qualität **und** Gesamtkosten je
  erfolgreicher Aufgabe betrachten; knappen zielgerichteten Kontext
  und strukturierte Antworten bevorzugen, Tokenumfang reduzieren und
  unnötige Agenten-Schleifen vermeiden. Konkrete Provider-, Prompt- und
  Tokenlimits bleiben prüfbare Optionen.
- **ComfyReview-Entwicklungs-POC (jetzt):** Der
  [erste Kartenversuch](pocs/card-battler.md#konkreter-erstversuch-eine-karte-von-der-bildwahl-bis-zur-sammlung)
  nimmt **ein Quellbild**, leitet Karteninhalt ab und erzeugt **vier
  Bildalternativen**. Für die technische und kreative Erprobung darf der
  Nutzer **eine auswählen oder alle vier ablehnen und neu generieren**.
  Ablehnung erstellt keine Karte und verändert bei einer Entwicklung
  keine bereits bestätigte Karte. **40 Karten** sind das erste
  Testdeck-Ziel, nicht eine endgültige Deckgrößenregel.
- **Character Chronicles (späteres Spielerziel):** Für die
  Kartenentstehung soll **eine der vier angebotenen Bildvarianten
  ausgewählt** und übernommen werden. Die Möglichkeit, in ComfyReview
  alle vier zu verwerfen, ist eine **Entwicklungs-/POC-Funktion** und
  damit keine automatisch übernommene Regel des späteren Spiels.
  Weder POC noch Spielziel sind bereits als vollständige
  End-to-End-Funktion implementiert.
- **Produktrichtung:** **Ungefähre Arbeitsorientierung:** Card Battler
  zuerst, danach Timeline, Social Network mit Charakter-Chats, Storyline
  und **VN-Content zuletzt**. Die Academy ist **bestätigter
  Welt-/Storykontext**, aber keine zusätzlich beschlossene
  Implementierungsphase.
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
