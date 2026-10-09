# Academy-Run-Portfolios, Klasse und visuelle Beziehungskontexte

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für die übergeordnete visuelle Projektion
beider Academy-Jahre, der Klasse, einzelner Characters, Beziehungen und Ensembles

Stand: 10. September 2026

## Zweck

Dieses Dokument ordnet die in
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md)
definierten Bildkarten und Champion-Slots in den vollständigen Chronicle-Run
ein. Weder der vollständige Bildkartenbestand noch seine gemäß
Playground-Kombination und Availability aktuell spielbare Teilmenge ist die
oberste Ebene des Produkts. Zweijähriger Academy-Run, Cast,
Beziehungen, gemeinsame Szenen und Storyzeit bestimmen, welche visuellen
Portfolios existieren, welche Slots relevant werden und wie sie in Chronicle
und Characters sichtbar sind.

Die Portfolio-Hierarchie ist eine Projektion der Simulation. Sie besitzt keine
eigene Story-, Relationship-, Champion-, Stability- oder Assetautorität.

## Portfolio-Hierarchie

```text
ChronicleRun / AcademyRunVisualPortfolio
├─ SchoolYearVisualPortfolio[1..2]
│  └─ zeitgebundene Plan-, Event- und Momentprojektion des jeweiligen Jahres
├─ ClassRosterProjection
│  └─ CharacterPortfolio[]
│     ├─ CharacterVisualCanon
│     ├─ persistente Bildkarten
│     ├─ eigene ChampionSlots und Titelprojektion
│     ├─ Story-/Relationship-Projektionen
│     └─ historische Visual Moments aus beiden Jahren
├─ RelationshipPortfolio[]
│  ├─ ParticipantSet
│  ├─ RelationshipVisualContextRevision[]
│  └─ gemeinsame ChampionSlots und Story Moments
├─ EnsemblePortfolio[]
│  ├─ Class-/Club-/Event-Kontext
│  └─ gemeinsame Slots und MultiCharacterCompositionContracts
├─ SceneAssetPortfolio
└─ SchoolYearVisualPlanRevision[]
```

Das `AcademyRunVisualPortfolio` ist der runweite Besitzerrahmen. Die beiden
`SchoolYearVisualPortfolio`s sind zeitliche Teilprojektionen und keine
getrennten Sammlungen: Der Jahreswechsel dupliziert oder leert keine Bilder,
Karten, Titel, Relationship-Kontexte oder Character-Canon-Revisionen.

`CharacterPortfolio`, `RelationshipPortfolio`, `EnsemblePortfolio` und
`SceneAssetPortfolio` sind fachliche Besitzer unterschiedlicher Bilder und
Slots. Andere
Ansichten dürfen dieselbe Karte oder dasselbe Bild projizieren, ohne Besitz,
Evidenz oder Titel zu duplizieren.

Die Karte ist dabei die Projektion des persistenten Bildes; ein ChampionSlot ist
der davon getrennte Vergleichs- und Titelkontext. Ein gemeinsames Bild erscheint
als dieselbe gemeinsame Karte mit seinen kontextgebundenen Titeln und
Verwendungen, nicht als je eine neue Karte pro Slot oder Character.

## Besitz und Projektion

Ein Single-Character-Portrait, -Sprite oder -Outfit-Slot gehört genau einem
`CharacterPortfolio`. Ein gemeinsames Date-, Friendship-, Club-, Klassen- oder
Story-CG gehört dagegen dem passenden `RelationshipPortfolio` oder
`EnsemblePortfolio`.

Beispiel:

```text
Image 812
├─ RelationshipSlot: „Aiko und Kaori · Dach · Abendgespräch“
├─ Identity Observation für Aiko
├─ Identity Observation für Kaori
├─ Composition Observation für beide zusammen
├─ Story Moment im Oktober
├─ Projektion in Aikos Character-Ansicht
└─ Projektion in Kaoris Character-Ansicht
```

Das Bild und der gemeinsame Slot werden nicht für beide Characters dupliziert.
Participant-spezifische QA, gemeinsame Kompositionsevidenz, Titel und
VN-Verwendungen bleiben getrennte Beziehungen zum selben Quellbild.

Verbindliche Regeln:

- Jeder Slot besitzt genau einen fachlichen Portfolio-Owner.
- Ein Character-Screen darf fremdbesessene gemeinsame Karten als
  `shared_context` projizieren, aber nicht als eigenen Slottitel zählen.
- Ein gemeinsamer Slot besitzt eine kanonisch sortierte Participant Set
  Signature und keine willkürliche Hauptfigur als technischen Besitzer.
- Dieselbe Beobachtung wird in mehreren Ansichten nur dargestellt und nicht
  mehrfach persistiert oder gezählt.
- Ein Relationship- oder Ensemble-Champion ersetzt keinen Single-Character-
  Champion und umgekehrt.

## SchoolYearVisualPlan

Der `SchoolYearVisualPlan` ist eine versionierte, rebuildbare Projektion aus:

- authored Calendar, Story Graph und erreichbaren Scene Contracts,
- bekanntem und noch unbekanntem Cast,
- CharacterVisualArcs und aktuellen Canon Revisionen,
- Relationship-, Route-, Knowledge- und Milestone-Zuständen,
- Scene-, Asset-, Play- und Ensemble-Gates,
- vorhandenen Portfolio-Slots, Bildern, Champions und AssetVersionen,
- Content Policy und zeitlicher Freigabe,
- sowie Rules- und Authoring-Revisionen.

Er materialisiert nicht zu Beginn alle theoretischen Kombinationen. Slots und
Requirements werden just-in-time erzeugt, sobald sie authored benötigt,
storyseitig erreichbar, durch Beziehung autorisiert oder als begrenzte Coverage
sinnvoll sind.

```text
authored future need
→ noch verborgen
→ zeitlich erreichbar
→ VisualRequirement / PortfolioSlot materialisiert
→ geplant | in Entwicklung | blockiert | bereit
→ in Szene verwendet
→ historischer Visual Moment
```

Die Projektion kennt Day-, Week-, Month-, Term-, School-Year- und vollständige
Academy-Run-Fenster. Ein
zukünftiger Slot darf intern vorgeplant werden, aber keine unbekannte Figur,
Route, Überraschung oder Beziehung im normalen Frontend spoilern.

Reale Renderzeit verändert keine Storyzeit. Ein blockierendes Requirement hält
den Storyübergang; optionale oder spätere Arbeit darf unter Backpressure im
Hintergrund fortgesetzt werden.

## Klassen- und Cast-Übersicht

`Characters` beginnt langfristig mit einer Class-/Cast-Roster-Projektion. Sie
ist weder globales Bilderranking noch technische Trainingsmatrix. Pro sichtbarer
Figur zeigt sie höchstens:

- bekannt, angedeutet oder noch unbekannt,
- aktuelles Signature-/Coverbild oder authored Placeholder,
- aktuellen Story-/Beziehungsbezug in verständlicher Form,
- nächsten erreichbaren visuellen Bedarf,
- groben Sammlungs-/Titelzustand aus Bildkarten, belegten Titeln, stabilen
  Kontexten und freigegebenen Assetverwendungen,
- aktive gemeinsame Relationship-/Ensemble-Kontexte,
- und direkten Einstieg in Character beziehungsweise relevanten Trial.

Die übergeordnete Academy-Run-Projektion zeigt:

- aktuelles Academy-Jahr, Monat beziehungsweise Term und Storyfenster,
- bekannte Characters und aktuelle Foki,
- unmittelbar kommende visuelle Voraussetzungen,
- Relationship-/Ensemble-Meilensteine mit bereits bekanntem Kontext,
- wiederverwendbare gemeinsame Assets,
- offene Class-/Event-/Ensemble-Blocker,
- sowie historische Story Moments des bisherigen Runs.

Sie zeigt keinen gemittelten „Klassen-Qualitätsscore“. Aggregationen bleiben
erklärbar, beispielsweise:

```text
12/16 Characters bekannt
7 Characters mit mindestens einem stabilen Kernslot
3 unmittelbar blockierende visuelle Voraussetzungen
2 gemeinsame Ensemblekarten in Entwicklung
1 Relationship-Moment für dieses Storyfenster bereit
```

Ein Character mit wenigen storyrelevanten Slots wird nicht als schlechter
behandelt als ein früh eingeführter Fokus-Character mit umfangreicher
Bildkartensammlung und vielen Titelkontexten.

## RelationshipVisualContext

Eine Beziehung wird nicht als bloßer numerischer Filter über Bildkartensammlung
oder Titelübersicht gelegt. Für visuelle Wirkung besitzt sie eine versionierte
`RelationshipVisualContextRevision` mit mindestens:

- kanonischem Participant Set,
- Relationship- und Knowledge-Snapshot,
- Relationshipklasse und authored Milestone,
- Storyzeit und zulässigem Scene-/Activity-Korridor,
- erlaubtem Content Scope und Intimacy-Korridor,
- relevanten Character Canon Revisionen,
- gemeinsamer Expected Composition,
- participant-spezifischen Identity-/Outfit-Anforderungen,
- erlaubten gemeinsamen und individuellen Varied Axes,
- sowie Source Story Contract und Visibility Policy.

Relationship State darf:

- neue gemeinsame VisualRequirements und ChampionSlots materialisieren,
- Priorität und zeitliche Relevanz bereits erlaubter Slots beeinflussen,
- Copy, Kontext und sichtbare Bedeutung einer Karte verändern,
- sowie bestimmen, welche gemeinsamen Momente im jeweiligen Character-Kontext
  erscheinen.

Relationship State darf nicht:

- ein Bild ohne Spielerentscheidung qualifizieren,
- einen Champion, SignatureChampion oder Stable-Status vergeben,
- Character Canon direkt ändern,
- technische QA oder AssetReadiness überspringen,
- visuelle Präferenz-, Prompt-, Recipe-, Evolution- oder Champion-Evidence
  erzeugen,
- eine charactereigene visuelle Gruppe öffnen oder ihren Änderungswiderstand
  senken,
- alte Bilder rückwirkend in einen anderen Storyzeitpunkt umdeuten,
- oder Evidenz aus einer anderen Beziehung beziehungsweise Participant Set
  übernehmen.

Hohe Beziehung kann authored gemeinsame Storymomente, VisualRequirements und
Slots öffnen oder priorisieren. Sie senkt jedoch keinen visuellen
Änderungswiderstand und wählt weder konkrete Optik noch Prompt-, Recipe- oder
Evolutionsrichtung. Qualifier, Comparison Context, Cup, Title Match, Stability
Trial und Asset Gate bleiben vollständig im Booster-/Bildspiel-System.

## Mehrfiguren- und Ensemblekarten

Ein gemeinsamer Slot verwendet einen `MultiCharacterCompositionContract` und
prüft mindestens:

- jede sichtbare Character Identity separat,
- Outfit und Canon Revision pro Participant,
- Position, Blickrichtung, Pose-Interaktion und Occlusion pro Bildslot,
- gemeinsame Scene-, Lighting- und Composition-Erfüllung,
- Identity Bleeding und falsche Participant-Zuordnung,
- sowie zulässigen Fallback auf komponierte Einzelassets.

Ein Keep oder Favorite kann dabei für einzelne Participants positiv und für die
gemeinsame Komposition negativ sein. Der Quelloutput bleibt sichtbar und
mehrfach auswertbar; nur die jeweilige Slotqualifikation folgt ihrem vollständigen
Contract.

## Frontend-Zuständigkeit

```text
Chronicle
→ Academy-Jahr und -Zeit, nächster Storyschritt, kommende Visual Needs und Blocker

Characters / Klasse
→ Cast-Roster, bekannte Figuren, grober visueller und relationaler Zustand

Character Detail
→ eigene Bildkartensammlung, getrennte Titelübersicht, Bildkarrieren, Canon,
  Storyentwicklung und projizierte gemeinsame Relationship-/Ensemblekarten

Relationship-/Moment-Ansicht
→ gemeinsamer Kontext, Participant Set, gemeinsame Karten und Story Moments

Trials
→ tatsächliche Bewertungs-, Vergleichs-, Stability-, Recovery- und Cup-Runtimes
```

Keine dieser Ansichten berechnet ihren Zustand selbst. Sie konsumieren dieselbe
serverseitige Portfolio-, Slot-, Relationship-, Gate- und
SchoolYearVisualPlan-Projektion.

## Verbindung zum Orchestration Guardian

Der runweite `SchoolYearVisualPlan` und die Portfolios liefern begründete Bedarfe an den
Domain Planner. Der Guardian aus
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md)
entscheidet anschließend nur, welcher bereits autorisierte maschinelle Schritt
unter den aktuellen Abhängigkeiten und Ressourcen als Nächstes ausgeführt werden
darf.

Priorisierung berücksichtigt:

- unmittelbar blockierenden Storybedarf,
- zeitliche Nähe im SchoolYearVisualPlan,
- bekannte statt noch verborgene Characters und Kontexte,
- Character-, Relationship- und Ensemble-Fairness,
- wiederverwendbare bestehende Bilder vor unnötiger Neugenerierung,
- aktive unvollständige Spieler- oder Maschinenabläufe,
- sowie Backpressure, Capability und Recovery.

Weder Relationship-Nähe noch aktuelle Fokusfigur darf andere erforderliche
Characters dauerhaft verhungern lassen.

## Persistenz-Mindestmodell

Der Zielvertrag benötigt mindestens folgende Entitäten oder gleichwertige
normalisierte Verträge:

- `visual_portfolios` mit `character | relationship | ensemble | scene`,
- `portfolio_participants`,
- `academy_run_visual_portfolios` und ihre genau zwei
  `school_year_visual_portfolios`,
- `school_year_visual_plan_revisions`,
- `school_year_visual_plan_items`,
- `relationship_visual_context_revisions`,
- `ensemble_visual_context_revisions`,
- `portfolio_slot_bindings`,
- `visual_moment_bindings`,
- sowie rebuildbare Class-, Character-, Relationship- und Timeline-
  Projektionen.

`ChampionSlot` erhält genau eine `portfolio_id`. Bestehende `character_id`-
Felder dürfen für Single-Character-Slots als beschleunigter Lookup bestehen,
ersetzen aber den allgemeinen Owner-Vertrag nicht.

## Abgrenzung zum implementierten Stand

Der aktuelle Foundation- und Frontend-Stand besitzt Campaign-/Character-
Ansichten, Album-/Championbilder, Relationship-Zielverträge, Castplanung,
Scene-/Ensemble-Gates und Multi-Character-Planung als einzelne Bausteine. Eine
gemeinsame `AcademyRunVisualPortfolio`-Projektion mit zwei Jahresansichten, Relationship-/Ensemble-
Portfolio-Owner und die dazugehörige Class-/Timeline-UI sind noch nicht
implementiert. Diese Spezifikation ist Zielvertrag und wird als Gap geführt.

## Testbare Invarianten

1. Jeder ChampionSlot besitzt genau einen Portfolio-Owner.
2. Ein gemeinsamer Slot verwendet ein kanonisches Participant Set und keine
   willkürliche Hauptfigur als Owner.
3. Dasselbe gemeinsame Bild wird in zwei Character-Ansichten nicht dupliziert
   oder doppelt gezählt.
4. Relationship State kann einen Slot öffnen, aber kein Bild qualifizieren oder
   einen Titel vergeben.
5. Relationship- und Ensemble-Champions verändern keine Single-Character-Titel.
6. Jede sichtbare Figur eines Multi-Character-Bildes besitzt eigene Identity-
   und Canon-QA.
7. SchoolYearVisualPlan-Rebuild mit demselben Event-High-Watermark erzeugt
   dieselben sichtbaren und verborgenen Items.
8. Verborgene Characters, Routes und Relationship-Momente leaken nicht über
   Slotnamen, Queue, Deckzahlen oder Blockercopy.
9. Reale Renderzeit verändert keine Storyzeit.
10. Ein früheres Visual Moment bleibt an damalige Canon-, Relationship- und
    Storyrevisionen gebunden.
11. Class-Aggregationen vergleichen Characters nicht über einen ungebundenen
    Qualitätsscore.
12. Aktiver Fokus und hohe Beziehung dürfen keinen anderen erforderlichen
    Character dauerhaft aus der Orchestrierungsfairness verdrängen.
13. Der Übergang in Academy-Jahr 2 erhält sämtliche runweiten Portfolio-,
    Karten-, Titel-, Relationship- und Canon-Identitäten und erzeugt weder
    Abschlussaudit noch NG+-Freigabe.
