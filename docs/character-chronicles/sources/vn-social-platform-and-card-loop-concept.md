# Welt, VN, Social-Plattform und Bildkarten-Loop

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `PRODUCT_AND_WORLD_VISION`  
**Worum es geht:** Weltprämisse, Academy, Network, Social, Karten und VN als umfassendes Spielerlebnis.  
**Aktueller Referenzpunkt:** [fachlich bestätigte Zielwelt](../vision/world.md) · [Gesamtvision](../vision/README.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

**Fachlicher Geltungsabgleich (2026-10-10):** Die Weltprämisse mit Kobe ab 2032, den zwei Academy-Jahren, einer etablierten Social-/Battler-Kultur und eigenständigen Figuren ist heute als **Zielvision bestätigt**. Dieser Originaltext bleibt trotzdem eine historische Quelle: Frühere genaue Kalender-, UI-, M6-, Datenbank- und Kartenregelverträge werden nicht pauschal übernommen. Maßgeblich für den heutigen Beschluss ist die [aktuelle Weltbeschreibung](../vision/world.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: gemeinsamer Arbeitsrahmen für World Canon, Storyrahmen und
Spielerprojektion

Autorität: **WORKING FRAME**; kein abschließender Story-, Simulations- oder
Card-Battler-Vertrag

Stand: 14. September 2026

## Zweck und Geltungsgrenze

Dieses Dokument hält den vorläufigen World Core und den erzählerischen
Zusammenhang zwischen Visual Novel, Dating Sim, Social-Media-Plattform,
Bildgenerierung, Trials und Card Battler fest. Es dient zunächst dazu,

- Zeitpunkt, realen Handlungsort und technische Alltagswelt festzulegen,
- festen World Core und generierten Save World Canon zu trennen,
- die durch den Spieler beeinflusste Academy in den persönlichen Content- und
  M6-Lernloop einzuordnen,
- spielerseitiges Wording für die Bildspiele herzuleiten,
- die Bildspiele als Teile desselben Spiels zu inszenieren,
- und ihre Screenabläufe auf den späteren Gesamtloop auszurichten.

Es entscheidet noch nicht die konkrete Haupthandlung, Character-Arcs, die
vollständige Geschichte und Funktionsweise der Plattform, die Regeln des Card
Battlers oder die genaue Wirkung eines Duells auf Beziehungen und
VN-Fortschritt. Kartenentstehung, Playground-Kombinationsbindung, temporäre
Keep-Spielbarkeit, randomisierte Favorite-/Champion-Verbesserung, bildloses
Base Deck und Kartenentwicklung bis Legendary sind inzwischen im autoritativen
[`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md)
entschieden. Bestehende autoritative Verträge zu Evidenz, Generierung, Trials,
Keep/Favorite/Reject, Championtiteln und Assetfreigabe bleiben unverändert.

Insbesondere ist die Social-Plattform die **spielerische Projektion und
narrative Anbindung** eines technischen Vorgangs. Ein sichtbarer Post ersetzt
weder den versionierten Generation Contract noch Character-, Story-, Prompt-,
Recipe-, Modell-, Seed- oder Evidence-Provenienz im Backend.

## Vier getrennte Ebenen desselben Ablaufs

Der sichtbare Kartenloop erklärt innerhalb der Fiktion nicht die Entstehung der
VN-Welt oder ihrer Figuren. Er bildet die spielerseitige Handlungsschicht für
einen technischen Lern- und Produktionsprozess:

```text
Realer Spieler
└─ steuert und erlebt den Protagonisten

VN- und World Canon
└─ Figuren, Aussehen, Beziehungen und Ereignisse sind innerhalb der Welt real

Diegetische Plattformhandlung
└─ Protagonist reagiert auf Posts, öffnet Booster, wählt Bildkarten und battlet

Technische Produktionsschicht
└─ dieselben Bildentscheidungen erzeugen gescopte Preference Evidence
   und können spätere VN-Bilder sowie Assetentscheidungen verbessern
```

Für Figuren innerhalb der VN verändert ein Bildreview weder ihr reales
Aussehen noch die Vergangenheit. Sie wissen nicht, dass die Entscheidung des
realen Spielers zusätzlich Character-, Outfit-, Place-, Composition- oder
Asset-Lernen speist. Innerhalb der Fiktion kuratiert der Protagonist lediglich
generierte Darstellungen für seine persönliche Kartensammlung.

Die anfängliche Generierung von Academy und Characters gehört ebenfalls nicht
zur In-World-Plattformhandlung. Was durch Prolog-Evidence pro Save entsteht,
ist für den Protagonisten anschließend einfach seine reale Academy und sein
reales Umfeld. Eine spätere verbesserte VN-Darstellung ist eine Veränderung der
Spielprojektion, kein körperlicher Wandel und kein automatisch neues
Storyereignis.

Der fiktionale Plattformvertrag muss daher nur plausibel erklären, warum ein
Nutzer mehrere Darstellungen eines erlaubten Posts erzeugt, auswählt und als
Karte verwendet. Er muss weder den M6-Lernvertrag noch die technische
VN-Assetproduktion innerhalb der Story offenlegen.

## Weltprämisse und Zeitpunkt

Der bestätigte Arbeitsrahmen ist eine bodenständige Near-Future-Welt über beide
Academy-Jahre 2032/33 und 2033/34. Der Prolog beginnt Ende März 2032; der
spielbare Zeitraum läuft vom Eintritt im April 2032 bis zum Abschluss im März
2034. Die Welt ist weder Cyberpunk noch
postapokalyptisch und setzt zunächst keine übernatürliche Ebene voraus.

Smartphones, öffentlicher Verkehr, Messenger, Social Media, generative Medien
und persönliche lokale Modelle gehören zum Alltag. Die Gesellschaft besitzt
mehrjährige Erfahrung mit generativen Bildern und den damit verbundenen Fragen
nach Authentizität, Zustimmung, Urheberschaft und Selbstdarstellung. Die Technik
kann stilisierte Darstellungen erzeugen; sie liest weder Gedanken noch
objektive Erinnerungen und sagt keine Zukunft voraus.

Der Calendar-Vertrag bildet beide Academy-Jahre ab:

- vierundzwanzig In-Game-Monate in zwei Zyklen von April bis März,
- vierzehn spielbare `DayInstance`s pro Monat,
- insgesamt 336 verdichtete Storytage,
- sowie 48 authored Special Slots, davon 24 pro Academy-Jahr.

Eine `DayInstance` ist kein lückenlos abgebildeter realer Kalendertag. Sie darf
mehrere ereignisarme Tage durch Montage verdichten. Reale Render-, Queue- oder
Wartezeit verändert keine Storyzeit.

## Fester World Core und generierter Save World Canon

Die Welt besitzt drei getrennte Ebenen:

```text
Fester äußerer World Core
└─ Japan, realer Ort, Zeitpunkt, Makrotechnik, Plattformexistenz und Grundregeln

Generierter Save World Canon
└─ Academy, Campus, Uniform, wiederkehrende Schulorte und lokale Ausprägungen

Persönlicher Plattform- und Bildkartenbestand
└─ relevante Figuren, Posts, Momente, Bilder, Karten, Decks und Bewertungen
```

Der äußere World Core schafft Verlässlichkeit zwischen Runs. Der generierte
Save World Canon ermöglicht eine durch den Spieler beeinflusste konkrete
Academy. Der persönliche Plattform- und Bildkartenbestand entsteht
ausschließlich aus dem jeweiligen Run und wird nicht als fertige
Inhaltsdatenbank ausgeliefert.

### Anime-Fokus, persönlicher Stil und Generator

Der verbindliche visuelle Produktfokus ist **Anime**, nicht ein einziges vorab
festgelegtes Anime-Subgenre, ein unveränderlicher Renderlook oder ein bestimmter
Bildgenerator. Der konkrete Stil gehört zur bewerteten visuellen
Produktionsschicht: Prolog-Evidence erzeugt erste begrenzte Stilpräferenzen;
anschließend dürfen ausschließlich Booster-/Bildbewertungen persönliche
Stil-Evidence ergänzen und kontrollierte Style Trials auslösen.

```text
semantischer World-, Character- und Asset-Canon
+ aktive AnimeStyleCoreRevision und persönliche Style-Evidence
+ versioniertes GenerationRecipe mit WorkflowFamily und ModelProfile
= vier visuelle Kandidaten
→ Spielerbewertung, Challenge und Promotion
→ bestätigte VisualAssetRevision
```

Pro `SaveGenerationProfile` existiert zu jedem Zeitpunkt eine aktive,
versionierte Anime Style Core Revision als Konsistenzanker. Das bedeutet nicht,
dass das Produkt allen Saves
denselben Look vorschreibt. Eine bewertete Child-Revision darf beispielsweise
Linienführung, Shading, Farbwirkung, Detailgrad, Proportionstendenzen,
Hintergrundbehandlung oder Inszenierung innerhalb des Anime-Fokus verändern.
Ein qualifizierter anderer Workflow oder ein kompatibles anderes Bildmodell
kann deutlich andere Kandidaten erzeugen und deshalb eine neue Stilrichtung
eröffnen. Der technische Wechsel selbst ist aber noch keine Präferenz und keine
Promotion; maßgeblich bleibt die vergleichbare Bewertung durch den Spieler.

Semantischer Canon und visueller Stil bleiben getrennt. Ein Style-, Modell- oder
Workflowwechsel darf weder Campusstruktur, Figurenbiografie noch die Bedeutung
eines Ortes umschreiben. Bereits bestätigte Bilder behalten ihre Provenienz und
historische Gültigkeit; zukünftige Darstellungen verwenden erst nach
bestandener Challenge die neue Revision. Innerhalb der Fiktion ist diese
Produktionsentwicklung unsichtbar: Für die Figuren hat die Welt nicht ihren
Zeichenstil gewechselt.

Die Trennung gilt insbesondere für folgende Bereiche:

| Bereich | Fester Rahmen | Pro Save generiert oder materialisiert |
|---|---|---|
| Zeit | beide Academy-Jahre 2032/33 und 2033/34, April 2032 bis März 2034 | konkrete Day- und Eventvarianten sowie der Übergang zwischen den Jahren |
| Ort | Japan und realer Haupthandlungsort | Academy-Campus und fiktive private Orte |
| Institution | erwachsene Senior-Academy-Kategorie | Name, Profil, Architektur, Uniform und Regeln |
| Plattform | mehrjährig gewachsenes Social Network | relevanter persönlicher Feed und Social Graph |
| Technik | generative Momentdarstellung ist etabliert, aber nicht allwissend | persönliche Komponenten, Recipes und visuelles Lernen |
| Karten | persistente Darstellungen gebundener Momente | konkrete Bilder, Beschreibungen, Titel und Decks |
| Wahrheit | Canon, Wissen, Belief, Post und Bild bleiben getrennt | konkrete Facts, Knowledge Records und Gerüchte |

## Realer Handlungsort

Als konkrete Arbeitsrichtung dient Kobe in der Präfektur Hyōgo. Kobe bietet
innerhalb derselben realen Stadt Hafen und Küste, dichtes Zentrum, Einkaufs- und
Ausgehviertel, historische und moderne Architektur, Hanglagen, Wohngebiete und
die Rokko-/Maya-Naturräume. Dadurch können die im Prolog vorgesehenen Achsen
`traditional | modern`, `urban | nature`, `quiet | lively` und
`coastal | hillside` innerhalb derselben realen Stadt auftreten.

Reale Stadtteile, Verkehrsachsen und öffentliche Orte dürfen als World Facts
verwendet werden. Die Academy selbst liegt auf einem fiktiven privaten Campus
innerhalb des realen Stadtgebiets. Der Prolog darf bestimmen, welche
Kobe-kompatible Campusausprägung der Save erhält; er darf die reale Geografie
nicht umschreiben.

Vor dem autoritativen World Contract bleiben die konkrete Campuslage, die
zulässigen realen Ortsanker und die Grenze zwischen realem Stadtfakt und
generiertem privatem Place Asset noch gemeinsam zu authoren.

## Generative Senior Academy

### Institutioneller Korridor

Die konkrete Academy wird nicht als fertiger Name, Campus, Uniformsatz oder
Inhaltskatalog ausgeliefert. Sie entsteht pro Save aus Spielerinput und
derselben persönlichen, leeren Content- und M6-Lernarchitektur, die auch
Character-, Outfit-, Place- und Bildkartenentwicklung trägt.

Als Arbeitsrichtung gilt eine private zweijährige postsekundäre Senior Academy.
Sie verbindet eine feste Jahrgangs- und Klassenstruktur mit spezialisierten
Wahlbereichen und der größeren Selbstständigkeit eines Colleges. Der
Protagonist zieht für seinen Eintritt in das erste Academy-Jahr nach Kobe und
durchläuft dort beide Jahre.

Die Academy-Kategorie ist eine seit den späten 2020er-Jahren etablierte
japanische postsekundäre Bildungsform und keine einmalige Sonderkonstruktion
dieses Campus. Sie richtet sich regulär an junge Erwachsene nach dem
Schulabschluss, umfasst zwei Studienjahre und verbindet:

- feste Cohorts, Homeroom und einen gemeinsamen Jahreskalender,
- allgemeinbildende, kreative und spezialisierte Wahlbereiche,
- Clubs, Schülervertretung, Festivals, Prüfungen und Abschluss,
- mehr persönliche Freiheit als eine Oberschule,
- aber mehr gemeinsamen Campusalltag als eine typische Universität,
- sowie anerkannte Credits, durch die ein Wechsel in das zweite Jahr möglich
  bleibt.

Private Träger dürfen im Rahmen dieser Bildungsform verbindliche
Academy-Kleidung beziehungsweise Uniformen, eigene Traditionen und ein starkes
Campusprofil führen. Gesellschaftlich gilt die Academy als normale Alternative
zu Universität und klassischer Berufsschule, nicht als remediale Einrichtung
oder Ausbildungsschiene der Social-Plattform. Ihre Ausbildung besitzt einen
eigenen Wert; Plattform und Battler sind Teil der Lebenswelt ihrer Studierenden,
nicht ihr institutioneller Daseinszweck.

Der feste Korridor garantiert unabhängig von ihrer generierten Ausprägung:

- jeder regulär eintretende Studierende ist am ersten Academy-Tag mindestens
  18 Jahre alt; damit sind insbesondere alle Fokus- und möglichen
  Romancefiguren bereits zu Storybeginn volljährig,
- die Academy besitzt Klassen beziehungsweise Cohorts, Wahlbereiche, Clubs,
  Schülervertretung, Prüfungen und einen Abschluss,
- eine gemeinsame Academy-Kleidung oder Uniform ist institutionell plausibel,
- der April-bis-März-Kalender bleibt anwendbar,
- der Campus besitzt die funktionalen Rollen, die authored Storytemplates
  benötigen,
- und der spielseitige Gender-Korridor der 16 Fokusfiguren beschreibt nicht die
  demografische Zusammensetzung der gesamten Academy.

Die genaue amtliche Bezeichnung dieser Bildungskategorie, ihre gesetzliche
Entstehung, das Altersband oberhalb der verbindlichen Eintrittsgrenze und die
Namen der beiden Jahrgänge bleiben zu konkretisieren.

### Bestätigte institutionelle Arbeitsform

Die Kategorie ist als reformierte Variante des japanischen Junior College und
nicht als vollständig neue Bildungsstufe zu verstehen. Eine Bildungsreform
Ende der 2020er-Jahre reagierte auf den Bedarf nach einem Weg zwischen
vierjähriger Universität, eng zugeschnittener Berufsausbildung und einem
unmittelbaren Eintritt in das Arbeitsleben. Bis 2032 ist diese Form anerkannt
und gesellschaftlich vertraut, nicht mehr experimentell.

Ihr Abschluss ist ein staatlich anerkannter zweijähriger Associate-Abschluss.
Er kann je nach Folgeziel für ein weiteres Studium angerechnet werden, zwingt
aber weder zu einer Universität noch zu einem bestimmten Beruf. Die Aufnahme
setzt regulär einen Schulabschluss und Volljährigkeit spätestens am ersten
Academy-Tag voraus. Ein Einstieg in das zweite Jahr ist nach Prüfung
kompatibler Credits institutionell möglich, bildet aber nicht den Einstieg des
Protagonisten.

Die konkrete Academy besitzt als Größenkorridor ungefähr 600 bis 800
Studierende, davon etwa 300 bis 400 pro Jahrgang. Eine Cohort umfasst ungefähr
24 bis 30 Personen. Die Einrichtung ist koedukativ, regional angesehen und
selektiv, aber weder gesellschaftlich abgeschottet noch eine Eliteanstalt. Die
16 Fokusfiguren bilden lediglich den spielrelevanten Ausschnitt ihrer
heterogenen Studierendenschaft.

Jeder Studierende gehört gleichzeitig zu drei sozialen Strukturen:

1. einer festen Cohort für Homeroom, gemeinsame Kernveranstaltungen,
   Organisation und Klassenvertretung,
2. einem persönlichen Wahlbereich für fachliche, kulturelle oder kreative
   Vertiefung,
3. sowie freiwilligen jahrgangsübergreifenden Clubs und Aktivitäten.

Das erste Jahr betont Orientierung und gemeinsame Grundlagen. Das zweite Jahr
erlaubt mehr Vertiefung, Verantwortung und ein persönliches Abschlussprojekt.
Der Protagonist tritt gemeinsam mit seiner Cohort in das erste Jahr ein. Der
Übergang ins zweite Jahr erhält bestehende Beziehungen, Memories, Karten- und
Visualzustände, verschiebt aber Rollen, Wahlbereiche, Verantwortung und
Abschlussdruck. Er ist ein Story-Meilenstein und kein Run-Ende.

### Funktion der beiden Academy-Jahre

Beide Jahre besitzen denselben April-bis-März-Grundkalender, aber eine andere
soziale Funktion. Das ist World-Rahmen für generierte Storyvarianten und keine
fest vorgeschriebene Route:

| Phase | Institutionelle Funktion | Typische soziale Möglichkeiten |
|---|---|---|
| Jahr 1 · April bis Sommer | Eintritt, Cohortbildung, Grundlagen, Wahlbereichs- und Cluborientierung | erste Nähe, erste Rivalität, neue Alltagsgruppen und Erkundung von Kobe |
| Jahr 1 · Herbst bis März | belastbarer Campusalltag, erste größere Projekte, Prüfungen und etablierte Rollen | vertiefte Freundschaften, erste Dates, Konflikte zwischen Gruppen und erste selbst getragene Events |
| Jahresübergang | Leistungsstand, Wahlbestätigung, mögliche Rollen- und Wohnänderungen | bestehende Bindungen werden neu eingeordnet, aber nicht zurückgesetzt |
| Jahr 2 · April bis Sommer | Spezialisierung, Verantwortung, Mentoring und Projektleitung | reifere Beziehungen, sichtbare Konsequenzen früherer Entscheidungen und stärkere öffentliche Rollen |
| Jahr 2 · Herbst bis März | Abschlussprojekt, Zukunftsentscheidung, Übergabe von Ämtern und Graduation | Route-Payoffs, Abschiede, gemeinsame Zukunftsfragen und Endings |

Die feste Cohort bleibt grundsätzlich über beide Jahre erkennbar. Wahlbereiche,
Projektgruppen, Clubämter, Nebenrollen und einzelne Wohnbindungen dürfen sich
am Jahresübergang authorisiert ändern. Dadurch entstehen neue Begegnungsachsen,
ohne den randomisierten Cast oder seine bisherige Geschichte neu zu würfeln.
Jedes Academy-Jahr besitzt 168 `DayInstance`s und 24 Special Slots; erst beide
Jahre zusammen bilden den vollständigen 336-Tage-Run.

Ein normaler Werktag verwendet als World- und Storykorridor:

```text
08:45        kurze Cohort-/Homeroom-Zeit
09:00–12:20  gemeinsame Seminare und Kernmodule
12:20–13:20  Mittagspause
13:20–16:30  Wahlbereiche, Studios oder Projekte
ab 16:30     Clubs, selbstorganisierte Arbeit, Stadt und Nebenjobs
```

Freitage dürfen einen stärkeren Projekt-, Beratungs- oder Gemeinschaftsfokus
besitzen. Samstage sind grundsätzlich frei, können aber Festivals, Turniere,
Exkursionen und besondere Academy-Veranstaltungen tragen. Dieser Rhythmus ist
kein lückenlos simulierter Stundenplan, sondern ein verlässlicher Satz
erzählerischer Tagesfenster.

Die gemeinsame Academy-Kleidung ist reguläre Kleidung dieser privaten
Hochschulform und keine fortgesetzte Oberschuluniform. Sie ist an normalen
Lehrtagen und bei offiziellen Auftritten verbindlich, besitzt Sommer-, Winter-
und Zeremonialvarianten und erlaubt begrenzte persönliche Kombinationen.
Projekt-, Club-, Freizeit- und Wochenendkontexte schaffen bewusst Raum für
andere Outfits.

Die Academy ist kein Internat. Ein Teil der Studierenden pendelt aus Kobe und
der Kansai-Region, andere leben bei Familie, allein, in WGs oder in vermittelten
Residences. Der Protagonist erhält wegen seines Umzugs zum Academy-Eintritt
einen Platz in einer Academy-nahen Residence außerhalb des Campus. Dort gelten Ruhe-, Sicherheits-
und Gästeregeln, aber keine kindliche Ausgangssperre. Campus, Residence,
individuelle Wohnorte und Stadt bleiben dadurch getrennte soziale Räume.

Der Battler ist weder Unterrichtsfach noch institutioneller Zweck. Die Academy
darf Plattformnutzung im Unterricht begrenzen, Posts aus nicht öffentlichen
Räumen regeln, ein freiwilliges Battler-Angebot oder einen Club zulassen und
lokale Veranstaltungen ausrichten. Lehrkräfte und Verwaltung besitzen keine
einheitliche Haltung zur Plattform. Ihre Aufgabe besteht darin, mit einer von
der Plattform geprägten erwachsenen Generation umzugehen, nicht diese Kultur
selbst hervorzubringen.

### Generativer Ablauf

Der Spieler baut die Academy nicht in einem technischen Editor. Authored
Prologinteraktionen im persönlichen Asset-unabhängigen Network-Opening erzeugen
begrenzte Preference Evidence und direkte Requirements.
Daraus entstehen strukturierte Academy- und World-Intents. Erst validierte
Vorschläge werden materialisiert und anschließend durch tatsächliche
Bildgenerierung, Spielerbewertung und Asset-/Canon-Gates visuell konkretisiert.

```text
PrologueAnswerReceipts
→ gescopte PreferenceEvidenceEvents
→ VisualTasteProfileRevision und direkte Requirements
→ AcademyIntent und WorldCanonDraft
→ strukturierter AcademyDesignProposal
→ deterministische Schema-, Konflikt- und Realitätsprüfung
→ WorldCanonVersion und AcademyCanonRevision
→ Place-, Uniform- und Campus-VisualRequirements
→ M6-Vierergruppen, Trials und Spieler-Evidence
→ bestätigte visuelle Academy-, Uniform- und Place-Revisions
```

Ein sichtbarer Antworttext wird nicht als Promptfragment übernommen. Ein
Bildoutput darf keine Schulregel, historische Tatsache oder räumliche Funktion
allein durch seine Darstellung erfinden. Semantischer Canon, visuelle
Darstellung und konkrete Assetfreigabe bleiben getrennte Revisionen.

Innerhalb des festen Korridors dürfen mindestens folgende Inhalte pro Save neu
entstehen:

- Academy-Name und plausible Kurzform,
- Gründungsprofil, öffentliche Reputation und Selbstbild,
- fachliche beziehungsweise kulturelle Schwerpunktsetzung,
- Kobe-kompatible Campuslage,
- Architektur- und Materialfamilien,
- Campusstruktur und Bindung funktionaler Ortsrollen,
- Schulfarben, Wappen und wiederkehrende Motive,
- `UniformBlueprintRevision` einschließlich saisonaler Varianten,
- konkrete Räume, Treffpunkte und wiederkehrende Wege,
- Club- und Wahlbereichsausprägungen innerhalb authored Funktionsslots,
- lokale Regeln und institutioneller Umgang mit der globalen Plattform,
- sowie sichtbare Academy-Traditionen.

Die Academy hat die Plattform weder geschaffen noch als gemeinsames Projekt
eingeführt. Ihre generierten Traditionen und Regeln dürfen Ursprung,
Funktionsweise und globale Geschichte der Plattform nicht umschreiben.

## Räumliches Spielweltmodell

Die VN besitzt keine frei begehbare Welt und benötigt keine kontinuierliche
Weltkarte. Sie verwendet einen festen, überschaubaren Katalog funktionaler
Ortsrollen. Ein `PlaceGraph` verbindet versionierte `PlaceNode`s über plausible
Wege, Storyzeit, Erreichbarkeit und Anwesenheit. Die konkrete Architektur und
Darstellung wird pro Save generiert; Funktion, Anschlussregeln und
Storyverwendung bleiben authored und validierbar.

Ortsdauer, sozialer Kontext und nutzbare Funktionen sind unabhängige Achsen und
keine gegenseitig ausschließenden Ortsklassen:

```text
PlaceNode
├─ place_id und place_canon_revision_id
├─ persistence_kind: permanent | character_linked | temporary
├─ context_kind: residence | academy | neighborhood | transit | city | private_home
├─ owner_character_id oder null
├─ function_roles[]
├─ capabilities[]
│  ├─ social | study | club | date | private_retreat
│  └─ private_match | casual_battle | practice_battle |
│     local_public_battle | arena_battle | broadcast
├─ access_contract_id
├─ travel_edges[] mit Zeit- und Verfügbarkeitsregeln
└─ aktive VisualBundleRevision oder noch nicht materialisiert
```

Die klassischen VN-Orte bilden immer das Rückgrat. Character-Wohnorte,
Battler-Fähigkeiten und zeitlich begrenzte Eventorte ergänzen dieses Rückgrat
additiv. Ein Café kann deshalb zugleich permanenter Stadtort, Date-Schauplatz
und lokaler Battler-Treffpunkt sein; ein Character Home kann bei erlaubtem
Anlass ein privates Match tragen. Nur ein tatsächlich spezialisierter Hub oder
eine Arena benötigt einen eigenen primären Battler-Ort.

### Dauerhafte World Anchors

Jeder Save bindet mindestens folgende funktionale Gruppen:

- das Zimmer des Protagonisten und gemeinsame Bereiche seiner Residence,
- Academy-Eingang, zentrale Außenfläche, Cohort-/Kernraum, Wahlbereich oder
  Studio, gemeinsamer Aufenthaltsbereich, Bibliothek beziehungsweise
  Projektbereich, ruhiger Treffpunkt, Clubbereich und großer
  Veranstaltungsraum,
- Residence-/Academy-Viertel, Station und wiederkehrender Pendelweg,
- sowie einen urbanen, einen Hafen-/Küsten- und einen Hang-/Naturkontext in
  Kobe.

Mehrere Funktionen dürfen auf demselben physischen Campus oder in demselben
Stadtbereich liegen, benötigen aber getrennte Scene- und Access Contracts. Die
endgültige Zahl der permanenten Slots und zulässigen Unterräume bleibt noch zu
authoren; sie wird nicht pro Save unbegrenzt erweitert.

### Wohnorte der Fokusfiguren

Jede der 16 Fokusfiguren erhält im `CharacterCanonDossier` eine versionierte
`CharacterResidenceBinding`. Sie bindet für jeden Storyzeitpunkt genau einen
aktiven primären Wohnanker, darf aber zusätzliche, frühere und bereits bekannte
Wohnorte referenzieren:

```text
CharacterResidenceBinding
├─ character_id
├─ primary_home_place_id
├─ additional_home_place_ids[]
├─ previous_home_place_ids[]
├─ valid_from und valid_until
└─ residence_knowledge_and_access_policy
```

Damit bleiben getrennte Elternhäuser, Academy-Residence unter der Woche,
Familienwohnen am Wochenende, mehrere Haushalte und ein tatsächlich gespielter
Umzug darstellbar, ohne dass eine Figur gleichzeitig zwei ungeklärte
Hauptwohnsitze besitzt. Mehrere Figuren dürfen dieselbe Residence, WG, Familie
oder dasselbe Gebäude teilen; die Zahl physisch verschiedener Wohnorte kann
deshalb kleiner als 16 sein. Plausible Wohnformen umfassen Familie, Verwandte,
Academy-vermittelte Residence, WG, eigene kleine Wohnung und Pendeln aus einem
anderen Teil der Kobe-/Kansai-Region. Die Auswahl folgt Lebensgeschichte,
Finanzen, Verantwortung, Alter, Fahrtzeit und Social Graph statt Personality-
oder Genderstereotypen.

Ein Home Anchor wird stufenweise sichtbar:

```text
Wohnkontext und ungefährer Stadtbereich
→ öffentlicher Annäherungsraum oder Gebäudeaußenansicht
→ Schwelle beziehungsweise gemeinsamer Empfangsraum
→ private Wohn- und Character-Räume nur durch passende Storyfreigabe
```

Der Wohnort existiert als Canon auch dann, wenn der Spieler ihn nie besucht.
Ein konkretes Interior Asset wird erst materialisiert, wenn ein erreichbarer
Scene Contract es benötigt. Beziehung allein teleportiert den Protagonisten
nicht dorthin; Einladung, gemeinsamer Anlass, Wissen, Zeit und Erreichbarkeit
bleiben erforderlich.

### Battler-Fähigkeiten und Öffentlichkeitsstufen

Weil der Battler Teil der generationsprägenden Alltagskultur ist, darf er nicht
nur als ortloses Menü erscheinen. Gleichzeitig benötigt nicht jedes Match
einen Spezialschauplatz. Die `capabilities` vorhandener oder dedizierter
`PlaceNode`s unterscheiden:

1. private mobile Matches im eigenen Zimmer, in einem Character-Wohnkontext
   oder an einem anderen nicht öffentlichen Ort,
2. beiläufige direkte Duelle an normalen sozialen Orten über gekoppelte Geräte,
3. einen freiwilligen Academy-Club- oder Practice-Kontext,
4. mindestens einen wiederkehrenden lokalen Battler-Treffpunkt in Kobe mit
   geeigneten Tischen, Displays oder Projektionen,
5. sowie größere öffentliche Cup- und Arena-Kontexte als wiederkehrende oder
   zeitlich begrenzte Event Places.

Battler-Funktion und sozialer Ort dürfen sich überschneiden: Ein Café,
Freizeittreff, Clubraum oder öffentlicher Platz kann eine Matchausstattung
besitzen, ohne ausschließlich dem Battler zu dienen. Dedizierte Orte sollen
eine lokale Community, Rivalen, Zuschauer, Verabredungen und Gespräche vor und
nach Matches tragen und damit auch VN-/Dating-Sim-Schauplätze sein.

Jeder Matchkontext bindet eine Sichtbarkeitsstufe:

```text
private
→ nur Spieler und Gegenspieler erleben Kartenverwendung und Match

co_present
→ benannte Anwesende können das Match tatsächlich mitbekommen

local_audience
→ kleiner realer Zuschauerkreis am Ort

public_or_broadcast
→ authored öffentliches beziehungsweise übertragenes Ereignis
```

Diese Stufe bestimmt Präsentationsgröße, zulässige Knowledge-Ausbreitung und
mögliche kleine soziale Folgen. Sie ändert keine Kartenregeln und macht ein
gewöhnliches Match nicht automatisch zu einem öffentlichen Storyereignis.

### Auswahl und Materialisierung

Der Spieler bewegt keinen Avatar frei durch diese Räume. Ein Day-/Time-Slot
zeigt eine begrenzte Auswahl aktuell erreichbarer Aktivitäten oder Orte;
authored Storyszenen dürfen einen plausiblen Ortswechsel direkt binden. Nur
tatsächlich bekannte Informationen dürfen verraten, wer sich voraussichtlich
an einem Ziel aufhält.

Erreichbarkeit eines Ortes, verfügbare Aktivität und verfügbare VN-Szene sind
drei getrennte Projektionen:

```text
PlaceAccessState
→ Darf und kann der Protagonist jetzt an diesem Ort sein?

PlaceActivityAvailability
→ Welche figurenbezogenen Routine-, Lern-, Arbeits-, Freizeit- oder
  Battler-Aktivitäten sind dort aktuell möglich?

SceneAvailability
→ Welcher konkrete VN-SceneContract ist dort aufgrund von Story,
  Teilnehmenden, Knowledge und vollständigen Visual Requirements spielbar?
```

Die bloße Anwesenheit an einem `PlaceNode` erzeugt keine Begegnung und keine
VN-Szene. Ein erreichbarer Orts-Hub darf ausschließlich figurenbezogene
Nicht-VN-Aktivitäten anbieten. Das ist insbesondere zu Beginn wichtig, wenn
der Ort bereits ein freigegebenes Background-/Hub-Bundle besitzt, aber
Character-, Outfit- oder Expression-Assets möglicher Begegnungen noch fehlen.
Figurenbezug verlangt keine sichtbare Anwesenheit: Eine Figur kann direkt
anwesend, remote beteiligt, asynchron verbunden oder der konkrete bekannte
Anlass der Aktivität sein.

Nicht-VN-Aktivitäten können beispielsweise gemeinsames oder für eine Figur
erledigtes Lernen, Arbeit mit einem bekannten Kollegenkontext, eine von einer
Figur angeregte Erkundung, Einkauf für oder mit jemandem, Clubpraxis und ein
direktes oder asynchrones Battler-Training umfassen. Sie besitzen einen authored
`PlaceActivityContract`, mindestens einen `CharacterActivityBinding`, einen
Zeitverbrauch, zulässige kleine Outcomes und eigene Assetanforderungen. Reine
Network-, Deck-, Kalender- und Reisehandlungen sind zeitfreie System-
beziehungsweise Navigationsaktionen und keine `PlaceActivity`.

Jeder Activity Contract enthält mindestens eine mögliche Post-Perspektive.
Nach Abschluss entsteht daraus ein `ActivityOutcomeContext` mit einem oder
mehreren `PostOpportunityContract`s für zulässige Autoren. Der bloße
Figurenbezug schreibt noch keine Beziehung, gemeinsame Erinnerung oder
Character Knowledge; dafür muss die Figur gemäß Binding tatsächlich direkt
oder remote beteiligt sein und der Outcome Contract den Effekt erlauben. Eine
Aktivität darf einen späteren Scene Contract vorbereiten oder entdecken, ist
aber nicht selbst rückwirkend eine VN-Szene.

Eine Post Opportunity ist kein erzwungener Sofortpost. Sie hält fest, wer aus
welcher subjektiven Perspektive über die Aktivität posten könnte, welche Fakten
bekannt und darstellbar sind, welcher Sichtbarkeitskorridor gilt und ob der
Beitrag grundsätzlich packfähig sein darf. Personality, Privacy, aktiver
Plattformstatus und Feed-Pacing entscheiden anschließend über tatsächliche
Veröffentlichung. Ein veröffentlichter packfähiger Post kann über die normale
Reaction wieder einen `BoosterIntent` eröffnen.

Neue private Unterräume, Character-Wohnorte und Eventorte werden ausschließlich
aus einem validierten `PlaceContract` materialisiert. Ein Szenen-LLM oder
Bildgenerator darf keinen zusätzlichen Wohnort, Clubraum, Battler-Treffpunkt
oder Reiseknoten allein durch improvisierten Text beziehungsweise ein Bild in
den World Canon schreiben.

## VN als generierte soziale Welt

Der 16-Personality-Cast bildet den tief simulierten Kern der Dating Sim, aber
nicht die vollständige Bevölkerung ihrer Storywelt. Der Protagonist begegnet
genau 16 persistenten Fokusfiguren mit vollständiger Character-, Friendship-,
Romance-, Knowledge- und visueller Entwicklung. Darüber hinaus existieren
wiederkehrende und situative Storyfiguren wie Familie, Lehrkräfte,
Academy-Personal, weitere Studierende, Residence-Kontakte, Clubmitglieder,
Rivalen und Plattformakteure. Deren Simulations- und Assettiefe richtet sich
nach ihrer narrativen Funktion; sie werden nicht künstlich in den 16er-Fokuscast
eingerechnet.

Jeder Run besetzt alle 16 Base Personality Profiles genau einmal neu. Die
standardisierte Mutter-/Umzugskonversation des Prologs ermittelt über authored
Fragen eine gewichtete Nähe des Spielers zu diesen Profilen. Daraus entsteht
eine bevorzugte frühe Begegnungsreihenfolge, aber weder eine feste Route noch
ein verkleinerter Cast.

Davon getrennt randomisiert der Save innerhalb fester Plausibilitäts- und
Diversity-Grenzen, welche konkrete Person jedes Profil verkörpert: Name,
Aussehen, Klasse oder Parallelklasse, Wahlbereich, gemeinsame oder getrennte
Kurse, Club-, Residence-, Stadt-, Plattform- und Battler-Kontexte sowie
vorausgehende Social Edges. Ein Personality Profile besitzt keinen festen
Schulplatz und keine stereotype optische oder soziale Rolle. Das frühe
Encounter Ranking sucht im anschließend erzeugten Weltzustand passende
Begegnungshooks für die spielernahen Profile.

```text
standardisierte Mutter-Konversation
→ gewichtete Player-/Personality-Affinität
→ EarlyEncounterRanking

16 feste Profile + Academy-Schema + Social-Graph-Regeln + Save Seed
→ neue Namen, Optiken, Platzierungen und Beziehungen
→ stabiler persönlicher Cast dieses Runs
```

Zur konkreten Person gehört zusätzlich eine randomisierte, aber kohärente
Lebensgeschichte. Ein `CharacterGenesisRecipe` kombiniert Werte, Anime-
Rollenfragmente, Herkunft, Familie, Wohnen, prägende Erlebnisse, erlernte
Verhaltensweisen, Interessen, Fähigkeiten, frühere Freundschafts- und
Beziehungserfahrung, gegenwärtigen Druck, Zukunftsziel, persönliche Grenzen und
den Umgang mit Plattform und Battler. Das Personality Profile gewichtet deren
Plausibilität, schreibt sie aber nicht stereotyp vor.

Überraschende Kombinationen bleiben erwünscht, wenn die Recipe sie kausal
erklärt: Ein Merkmal kann zum Profile passen, durch Erfahrung angepasst sein,
als bewusster Gegenpunkt wirken oder eine öffentliche Maske darstellen. Vor der
Materialisierung prüft ein gemeinsamer Coherence Validator Biografie,
Zeitlichkeit, Academy-/Wohnrealität, Social Edges, Knowledge, Cast-Diversität
und sensible Inhalte. Das validierte `CharacterCanonDossier` wird anschließend
stabiler Save Canon und speist Director, LLM und RAG nur gemäß Wissen und Reveal
Policy. Biografische Wahrheit wird nicht erst während eines Dialogs passend
hinzuerfunden.

Der zweijährige Academy-Run besteht nicht aus einer vollständig vorab geschriebenen
Dialogdatenbank. Fest authoriert und versioniert sind Kalender, Academy-
Rhythmus, soziale Eventklassen, erreichbare Orte, Rollen, Teilnehmerregeln,
Character- und Relationship-Grenzen, Knowledge, mögliche Intents,
Wirkungskorridore sowie Plattform- und Card-Battler-Anlässe. Ein lokales LLM
erzeugt daraus die konkrete VN-Variante: Dialog, Erzählertext, Nachrichten,
Posts, kleine Handlungen und emotionale Ausprägung.

```text
fester World Core und generierter Save Canon
+ DayInstance, sozialer Anlass und verfügbare Figuren
+ Personality, Relationship, Knowledge und frühere Ereignisse
+ validierter Spielerintent
= begrenzter SceneRealizationContract
→ konkrete LLM-generierte VN-, Chat-, Nachrichten- oder Postvariante
→ deterministische Validierung und begrenzter State-Outcome
```

An ausgewählten Beziehungs- und Storybeats kann der Spieler seinen spontanen
Reaktionsimpuls über ein kurzes Minispiel ausdrücken. Dieses Minispiel bestimmt
nicht den fertigen Satz und schreibt keinen Canon. Es liefert dem Storysystem
einen strukturierten Intent – etwa Annäherung, Zurückhaltung, Unterstützung,
Neugier, Humor oder Konfrontation samt zulässiger emotionaler Färbung –, aus dem
das LLM eine zur Figur und Situation passende Reaktion realisiert. Name,
konkreter Ablauf, Häufigkeit und genaue Impulsgrammatik bleiben zu definieren.

Große Route-, Relationship-, Knowledge- und Calendar-Übergänge bleiben
vertraglich gebunden. Die generative Freiheit liegt in der konkreten
Ausgestaltung einer erlaubten Situation, nicht in einem freien Umschreiben der
Welt. Dadurch können dieselben Schul-, Sozial-, Plattform- und Battlerrahmen pro
Save und State deutlich verschiedene Storyvarianten tragen, ohne dass die VN
ihre Kontinuität verliert.

## Globale Social-Plattform

Die Plattform ist unabhängig von Academy und Schule über mehrere Jahre
entstanden. Im Jahr 2032 ist sie in Japan und international gesellschaftlicher
Mainstream – vergleichbar mit der heutigen Stellung großer Social-, Video- und
Messenger-Plattformen. Ob sie formal weltweit dominiert oder aus Spielsicht
lediglich weltweit verfügbar ist, wird mit ihrer Geschichte konkretisiert.

Die Welt ist dabei nicht als unveränderte Gegenwart mit einer zusätzlichen App
gedacht. Die Plattform ist das soziale Betriebssystem einer Generation und hat
Alltag, öffentliche Räume, Umgangsformen, Veranstaltungen und Erwartungen an
Selbstdarstellung sichtbar geprägt. In dieser strukturellen Bedeutung dient
eine stark durch ihr zentrales System geformte Anime-Welt als Referenz: nicht
durch Full-Dive, Fantasy oder eine Todesmechanik, sondern durch eine
allgegenwärtige gemeinsame Kultur mit eigener Sprache, eigenen Ritualen,
Stars, Konflikten und gesellschaftlichen Institutionen.

Ihre kulturelle Größenordnung entspricht einem generationenprägenden
Massenphänomen und nicht einem populären Nischen-E-Sport. Fast jeder junge
Mensch kennt Plattform, Grundbegriffe, berühmte Matches und prägende
Champions, auch wenn nicht jeder aktiv battlet. Erwachsene, Schulen, Medien,
Geschäfte und Veranstalter können die Kultur nicht ignorieren. Die
Plattformgeneration ist mit ihr aufgewachsen, ähnlich wie reale Generationen
mit einer weltweit verständlichen Sammel- und Battler-Marke aufgewachsen sind.
Diese Referenz beschreibt Reichweite und kulturelle Selbstverständlichkeit,
nicht die Übernahme vorgefertigter Monster, Karten oder Berufsmodelle.

Sie verbindet mehrere heute getrennte Nutzungsformen:

- Profile und soziale Verbindungen,
- öffentlichen und eingeschränkt sichtbaren Feed,
- kurze Alltagsbeiträge,
- private Kommunikation,
- generative Momentdarstellungen,
- persistente Bildkarten und persönliche Sammlungen,
- Decks und schnelle Card-Battler-Matches,
- öffentliche Cups, Titel und saisonale Wettbewerbspfade,
- sowie öffentliche Creator-, Fan- und Championflächen.

Nicht jeder Nutzer verwendet alle Funktionen. Feed-Nutzer, private Nutzer,
Creator, dargestellte Personen, Sammler und aktive Battler sind überlappende,
aber nicht identische Rollen. Die Plattform ist im normalen Alltag so bekannt,
dass Figuren ihre Grundfunktionen nicht wie eine neue Erfindung erklären.

Die Plattform ist kulturell zentral, aber keine allzuständige Super-App. Ihr
fester Kern endet bei sozialer Identität, Kommunikation, Feed, generativer
Momentdarstellung, persönlicher Kartensammlung, Battler und den zugehörigen
Creator-/Eventflächen. Staatliche Identität, Banking, allgemeine
Schulverwaltung, Verkehr und unverwandte Lebensdienste bleiben eigenständige
Systeme. Man kann die Plattform verlassen und weiterhin am gesellschaftlichen
Alltag teilnehmen; für die mit ihr aufgewachsene Generation bedeutet dies aber
einen spürbaren Verlust sozialer Sichtbarkeit und gemeinsamer Kultur.

Ihre gesellschaftliche Macht beruht damit nicht auf technischer
Unentbehrlichkeit, sondern darauf, dass sehr viele Menschen Freundschaften,
Erinnerungen, Selbstdarstellung und spielerische Identität über sie organisieren.

Sie besitzt 2032 bereits etablierte Champions, Plattformstars,
Umgangsformen, Kontroversen, Nutzergenerationen, Wettbewerbe und Gegenkulturen.
Name, Ursprungsland, Unternehmen, Geschäftsmodell und genaue Ausgestaltung der
einzelnen Entwicklungsschritte bleiben Teil der nächsten gemeinsamen
Konkretisierung. Die grobe Zeitleiste bis 2032 ist unten als Arbeitsrahmen
gesetzt.

### Organisch gewachsenes Gesamtsystem

Als Arbeitsrichtung entstand der Card Battler nicht als beliebig angehängtes
Minispiel. Die Plattform entwickelte sich schrittweise aus sozialer
Kommunikation und dem realen Kontaktnetz ihrer Nutzer:

```text
Messenger, Anwesenheit und reale Kontakte
→ Profile, Alltagsbeiträge und Feed
→ generative Darstellungen geposteter Momente
→ persönliche Bildkarten und Sammlungen
→ informelle Community-Vergleiche und Duelle
→ offizieller Card Battler, Cups und Championkultur
```

Der Card Battler war ursprünglich keine Funktion des Plattformbetreibers. Ein
kleines unabhängiges Team nutzte die freigegebenen Social- und
Generierungsschnittstellen, um aus persönlichen Bildkarten ein eingebettetes
Social Game zu bauen. Das Spiel verbreitete sich innerhalb kurzer Zeit so
stark, dass es zunächst offiziell unterstützt und anschließend vollständig in
die Plattform integriert wurde. Plattform und Battler bleiben deshalb in
Sprache, Teilnahme und Identität unterscheidbare Bereiche, obwohl die jüngere
Generation sie als nahezu untrennbares Gesamtsystem erlebt.

Damit verbindet sie die soziale Direktheit früher Messenger mit der
netzwerkgebundenen Spielekultur früher Social-Media-Plattformen, wird aber zu
einem eigenständigen Anime-World-System weitergedacht. Auslöser, technische
Sprünge und wirtschaftliche Interessen der frühen Entwicklung sind noch zu
konkretisieren; der Vorreform-Vorfall und die anschließende Quellenreform sind
dagegen gesetzt.

### Bestätigte Arbeitszeitleiste

Die Funktionsentwicklung erfolgt in einer kurzen frühen Wachstumsphase. Der
fertige Battler ist zum Spielzeitpunkt dennoch seit vielen Jahren etabliert:

| Jahr | Entwicklung |
|---|---|
| 2021 | Start als kombinierter Messenger und identitätsgebundenes Social Network |
| 2022 | Einführung generativer Interpretationen von Posts; erster großer Wachstumsschub |
| 2023 | persönliche Bildkarten; ein unabhängiges Team veröffentlicht darauf aufbauend einen schnell wachsenden Social Card Battler |
| 2024 | offizielle Unterstützung, Integration beziehungsweise Übernahme und Beginn der ersten regulären Saison |
| 2025 | internationaler Mainstream-Durchbruch, große Cups und breite öffentliche Sichtbarkeit |
| 2027 | ein öffentlich übertragener Vorreform-Championship-Vorfall macht die unzureichende Zustimmung bei persönlichen Minderjährigenkarten zum generationenweiten Konflikt |
| 2028 | die reformierte Trennung aus allgemeinem Battlerzugang, jugendgeeigneten Kartenquellen und volljährigen persönlichen Karten wird zum Plattformstandard |
| 2032 | neunte Battler-Saison mit mehreren Championgenerationen, historischen Metawechseln und nostalgischer Frühkultur |

### Der Vorreform-Championship-Vorfall

Der auslösende Vorfall war kein technischer Kontrollverlust und keine geheime
KI-Manipulation. Er entstand daraus, dass die frühe Plattform rechtlich grobe
Accountzustimmung mit sozial verstandener Zustimmung zu jeder späteren
Verwendung gleichsetzte.

Eine minderjährige Nachwuchs-Battlerin erzeugte aus einem nur klein geteilten
Schulmoment eine persönliche Karte, auf der eine zweite minderjährige Person
deutlich erkennbar war. Über mehrere Booster, Challenges und Titel entstanden
weitere generierte Darstellungen desselben Motivs. Als die Karte in einer
öffentlich übertragenen Championship weit aufstieg, wurden nicht nur die
Spielkarte, sondern die Varianten und die erkennbare Mitperson Teil von
Berichterstattung, Fan-Copy, Memes und öffentlicher Spekulation.

Die Beteiligten hatten den damaligen allgemeinen Plattformbedingungen formal
zugestimmt. Die Mitperson hatte jedoch weder der späteren Reichweite noch der
wiederholten Generierung, dem Wettkampfstatus oder der dauerhaften Verbindung
ihrer Identität mit diesem Moment bewusst zugestimmt. Der gesellschaftliche
Kern des Falls lautete deshalb:

> Die Erlaubnis, in einem sichtbaren Bild vorzukommen, ist nicht automatisch
> die Erlaubnis, als spielbare Identität öffentlich zu zirkulieren.

Die anschließende Plattformreform etablierte vier bis 2032 selbstverständliche
Grundsätze:

- allgemeiner Battlerzugang und personenbezogene Kartenfreigabe sind getrennt,
- persönliche Karten sind erst ab verifiziertem Alter 18 zulässig,
- jede erkennbare Person benötigt eine eigene zweckgebundene Freigabe,
- und private Sammlung, Sichtbarkeit im direkten Match sowie öffentliche
  Übertragung bilden unterschiedliche Reichweitenstufen.

Die Namen der Beteiligten, der spätere Lebensweg der Mitperson und die genaue
Championship-Marke bleiben vorerst ungesetzt. Der Vorfall selbst, sein Ablauf
und seine regulatorische Wirkung sind fester World Core. Dadurch kann die
Story unterschiedliche Erinnerungen und Deutungen verwenden, ohne das reale
Leid der betroffenen Person als Sammellore oder Überraschungsroute auszubeuten.

Die Academy-Kohorte des Jahres 2032 war beim Aufstieg des Battlers noch im
Kindesalter. Sie kennt ihn daher als selbstverständlichen Teil ihrer Jugend,
obwohl einzelne Figuren nie aktiv gespielt, später aufgehört oder sehr
unterschiedliche Erfahrungen mit ihm gemacht haben. Erwachsene können sich
dagegen noch an eine Plattform ohne Bildkarten und Battler erinnern.

Den Vorreform-Vorfall erlebte diese Kohorte bereits bewusst über News,
Schulgespräche, Familienreaktionen, Memes oder die spätere offizielle
Aufarbeitung. Eine Figur kann die Reform als überfälligen Schutz, Verlust der
wilden Frühkultur, bloße Unternehmens-PR oder persönlichen Wendepunkt lesen.
Keine dieser Haltungen folgt automatisch aus Personality oder Battlerstärke.

### Persönliche Motive, universelle Regelgrammatik

Es existiert kein globaler Katalog vorgefertigter Figurenkarten. Bild,
Quellpost, dargestellte Personen und soziale Herkunft jeder Karte sind
persönlich. Weltweit gemeinsam und unmittelbar lesbar sind dagegen der
universelle Figurenkartengrundkörper, Kosten, Kampfmodi, Regelprimitive,
Effektfamilien, Slots, Favorite-/Championkennzeichen und
Präsentationskonventionen.

```text
persönlicher Post und einzigartiges Bild
+ weltweit standardisierte und budgetierte Regelgrammatik
→ individuelle, aber global verständliche Spielkarte
```

Dadurch kann ein Spieler die Strategie eines Champions studieren, dessen Deck
aber nicht kopieren. Sichtbare Motive dürfen Namen, Card Lore und Effektidee
inspirieren; sie verleihen der real dargestellten Person keine
übernatürlichen Fähigkeiten. Die gemeinsame Regelgrammatik statt eines
gemeinsamen Figurenkatalogs trägt die generationenweite Wiedererkennbarkeit.

### Aufmerksamkeit oder Karteninteresse

Die Verbindung von sichtbarer Post-Reaction und möglichem privatem Booster ist
seit der frühen Battler-Zeit ein gesellschaftlicher Grundkonflikt: Reagiert
jemand aus ehrlichem Interesse oder hauptsächlich, um Kartenmaterial zu
erhalten? In der Plattformkultur existieren deshalb Debatten und informelle
Begriffe für mindestens folgende Verhaltensweisen:

- wahlloses `Reaction Farming` zur Maximierung möglicher Booster,
- gezieltes `Card Fishing` durch besonders kartenattraktiv inszenierte Posts,
- oberflächliches `Deck Networking` zum Erweitern des nutzbaren Social Graph,
- offen battlerorientierte Accounts und Posts,
- sowie bewusst sozial gehaltene Nutzung ohne Battler-Teilnahme.

Missbrauch in der frühen Wachstumsphase ist eine plausible Ursache dafür, dass
Karten nur aus einem aktiven, verifizierten realen sozialen Umfeld entstehen
dürfen. Gemeinsame Institutionen und bestätigte Kontakte beweisen dabei keine
Freundschaft; sie begrenzen lediglich die spielbare Herkunft und erschweren
automatisiertes Kontakt- und Boosterfarming.

Die Reaction ist sofort sichtbar, während Generation, Review und verworfene
Kandidaten zunächst privat bleiben. Der Postautor erfährt erst durch eine
bewusste Veröffentlichung oder sichtbare Kartenverwendung, welche Darstellung
der reagierende Nutzer tatsächlich behalten hat. Damit kann derselbe soziale
Moment zeitversetzt eine zweite Bedeutung erhalten.

### Getrennte Formen von Status

Soziale Reichweite, visuelles Kartenprestige und spielerischer Battler-Rang
sind in der Welt getrennte Statusachsen. Eine bekannte Person kann den Battler
kaum nutzen; ein starker Battler kann einen kleinen privaten Social Graph
besitzen; eine vielbeachtete Sammlung garantiert keine taktische Stärke.

Viele Kontakte erhöhen mögliche Vielfalt, aber nicht automatisch die rohe
Stärke eines Decks. Kartenregeln und Augments bleiben budgetiert, Deckplätze
begrenzt und Wettbewerbe regelgebunden. Ein kleiner, über längere Zeit
entwickelter sozialer Kreis muss konkurrenzfähig bleiben. Beziehungen und
erlebte Kontexte öffnen neue Kombinationen und strategische Möglichkeiten,
ersetzen aber weder Bildauswahl noch Deckbau und Matchentscheidungen.

### Sichtbare Folgen für Alltag und Stadt

Auch Nichtspieler begegnen der Plattform ständig. Posts, Karten und Matches
sind Gegenstand alltäglicher Gespräche; lokale Cups und größere Begegnungen
können in Cafés, Geschäften, Veranstaltungsorten oder auf öffentlichen Screens
sichtbar sein. Creator-, Fan- und Championkultur erzeugen Trends, bekannte
Namen, Kontroversen, Gegenbewegungen und regionale Szenen. Kobe erhält dadurch
eine lokale Plattformkultur, ohne Ursprung oder Zentrum des globalen Netzwerks
sein zu müssen.

Eine Karte ist in dieser Gesellschaft nicht nur ein Spielgegenstand. Ihre
sichtbare Verwendung kann wie die öffentliche Weiterverarbeitung eines
gemeinsamen Fotos, Erlebnisses oder kreativen Beitrags verstanden werden. Das
erklärt, warum Karten gleichzeitig sammelbar und spielbar sind und dennoch
soziale Bedeutung besitzen.

Matches besitzen mehrere gesellschaftlich etablierte Größenstufen:

- beiläufige mobile Matches über Smartphone oder Tablet,
- direkte lokale Duelle über gekoppelte Geräte,
- größere Präsentationen an Battler-Tischen und Displays in Clubs, Cafés,
  Geschäften und anderen Treffpunkten,
- sowie öffentlich inszenierte Cups mit großflächiger Karten-, Angriffs- und
  Effektprojektion für Zuschauer.

Die Technik bleibt eine plausible Near-Future-Erweiterung heutiger Geräte und
ist weder Full-Dive noch eine zweite begehbare Realität. Die gestufte
Präsentation erlaubt trotzdem, dass ein wichtiges Duell die visuelle und
gesellschaftliche Größe einer Anime-Episode erreicht. Academy und Stadt
benötigen deshalb Regeln, Flächen und Veranstaltungskalender für eine Kultur,
die längst vor Ankunft des Protagonisten existiert.

Die Allgegenwart verändert den Startpunkt des Protagonisten: Er muss die
Plattformkultur und ihre Grundregeln nicht erst kennenlernen. Sein leerer
Kartenbestand markiert nicht kulturelle Ahnungslosigkeit, sondern den Eintritt
in einen neuen aktiven Social Graph und einen noch unentwickelten persönlichen
Kartenkontext in Kobe.

Welche Tätigkeiten rund um Plattform, Produktion und Wettbewerb tatsächlich
formale Berufe, bezahlte Nebenrollen, institutionelle Funktionen oder reine
Fankultur sind, ist ausdrücklich noch nicht entschieden. Die World-Richtung
setzt keine ausgearbeitete Plattform-Arbeitswelt und keine automatische
Karriere für erfolgreiche Spieler voraus.

Academy-spezifisch generierbar sind ausschließlich lokale Reaktionen auf diese
bereits bestehende Plattform, beispielsweise:

- Regeln zur Nutzung im Unterricht und auf dem Campus,
- Umgang mit sichtbaren Academy-Orten und Uniformen in öffentlichen Posts,
- offizielle, tolerierte oder unerwünschte Card-Battler-Gruppen,
- lokale Turniere und Treffpunkte,
- sowie unterschiedliche Haltungen von Verwaltung, Lehrkräften und
  Studierenden.

## Leere Runtime trotz globaler Plattform

Die Plattform darf innerhalb der Fiktion eine globale Historie und sehr große
Bestände besitzen. Diese Hintergrundrealität ist nicht mit dem persönlichen
Runtime-Store des Spiels identisch.

Ein neuer Save enthält keine ausgelieferten konkreten:

- Character-, Academy-, Outfit-, Place- oder Momentkomponenten,
- persönlichen Posts und Karten,
- Prompt- und Combozeilen,
- Spielerbewertungen oder Confidence-Projektionen,
- Bild- oder Textvektoren,
- aus einer globalen Live-Plattform übernommenen fremden Decks oder
  historischen Plattformfeeds.

Ausgeliefert werden ausschließlich contentneutrale Schemas, Grammatikregeln,
Rollen, Validatoren, öffentliche World-Core-Fakten und Authoringverträge.
Relevante konkrete Plattforminhalte werden just-in-time materialisiert, sobald
Figuren, Posts, Rivalen oder Wettbewerbe in den Wahrnehmungs- und Storyraum des
aktuellen Saves gelangen.

Der Start ohne persönliche Bildkarten folgt aus dem Umzug, dem neuen aktiven
sozialen Umfeld und dem Beginn dieser persönlichen Academy-Chronicle. Die
Plattform vernetzt angemeldete Nutzer automatisch mit ihrem verifizierten realen
Umfeld, insbesondere Schule, Academy, Arbeit und anderen institutionellen
Zugehörigkeiten. Persönliche Karten können nur aus Posts von Personen im aktiven
persönlichen Netzwerk entstehen. Beim Eintritt in Kobe besitzt der Protagonist
daher noch keine Karten aus seinem neuen Umfeld und beginnt den spielrelevanten
Bildkartenbestand bei null. Das schwache bildlose Standard-Base-Deck gehört
nicht zu diesem persönlichen Bildbestand und ermöglicht dennoch frühe Duelle.

Ein bereits zuvor vorhandener allgemeiner Plattformaccount ist damit
vereinbar. Frühere Kontakte oder Karten gehören nicht zum aktiven sozialen und
spielerischen Kontext dieses Runs und werden weder ausgeliefert noch technisch
materialisiert. Die normale Storycopy erklärt diesen Zustand als neues Umfeld
und neuen Kartenbestand, nicht als leere Datenbank oder technische Migration.

Der Protagonist kann Champions, Turniere und Battler-Regeln deshalb schon seit
Jahren kennen und als Minderjähriger sogar mit Standard- oder öffentlichen
Eventkarten gespielt haben. Mit Academy-Eintritt beginnt jedoch sein erster
persönlicher, personenbezogener Kartenbestand im neuen erwachsenen Umfeld. Der
Run behauptet nicht, dass die Plattform oder das Spiel für ihn neu erfunden
wurde; neu sind sein konkurrenzfähiges persönliches Deck und die Menschen, aus
deren einwilligungsfähigen Posts es wachsen kann.

### Network-first sichtbare Runtime

Die leere persönliche Runtime besitzt außerdem noch keine freigegebenen
Hintergründe für Home, Academy oder andere Orts-Hubs. Bis mindestens das
Home-Bundle spielbereit ist, bildet das Network daher die bildschirmfüllende
Hauptoberfläche. Der Spieler erlebt dies als Nutzung seines Accounts im neuen
sozialen Umfeld und nicht als technischen Platzhalter.

Sobald ein aktueller Ort mit seinem benötigten Visual Bundle existiert, wird
dieser Ort zum Hauptscreen zwischen VN-Szenen. Das Network bleibt als
Geräteansicht erreichbar und kann auf kleinen Displays weiterhin den ganzen
Bildschirm einnehmen. Weitere Orte werden erst sichtbar oder betretbar, wenn
ihre visuellen Voraussetzungen rechtzeitig materialisiert wurden. Die VN ist
in beiden Phasen der erzählerische Oberbau; Network und Ort sind verschiedene
operative Blickzustände innerhalb derselben Story.

Der Network-only-Prolog vor Schulbeginn ist damit die verbindliche
Spieleröffnung. Seine genaue Länge ist noch nicht entschieden. Er verwendet
keine persönliche VN-Bühne; die erste echte VN-Szene darf erst nach deren
Visual-Bundle- und Scene-Asset-Freigaben öffnen. Die konkreten Zustände,
Screen-IDs und Rückwege definiert die
[`Network-first VN-Frontend Screen Map`](network-first-vn-frontend-screen-map.md).

## Bestätigter grober Rahmen

1. Der Core-Spielmodus und das langfristige Motivationssystem sind eine
   storygetriebene Visual Novel mit Dating-Sim-Elementen über einen
   verdichteten zweijährigen japanischen Academy-Run. Neue Szenen,
   Beziehungen, Figurenentwicklung und
   persönliche Storyfolgen sind die zentrale Belohnung des Gesamtloops.
2. Der Spieler spielt und steuert eine eigene Figur innerhalb dieses
   Academy-Runs und erlebt die VN in First-Person-Perspektive. Das ist kein
   Isekai-Rahmen und keine von der Academy-Zeit losgelöste äußere Spielerfigur.
3. Eine über Jahre gewachsene globale Social-Media-Plattform verbindet
   VN-Alltag, öffentliche Posts, private Kommunikation und das
   Bildkartenspiel. Sie ist weder Academy-spezifisch noch zu Beginn der Story
   neu oder geheim. Als soziales Betriebssystem einer Generation prägt sie
   öffentliche Räume, Umgangsformen, Events und Jugendkultur der Welt. Ihre
   Bekanntheit und kulturelle Lesbarkeit entsprechen einem
   generationenprägenden globalen Massenphänomen; aktive Battler bleiben
   dennoch nur eine Teilmenge aller Plattformnutzer.
4. Figuren posten über ihren Alltag. Nach einem konkreten VN-Ereignis verfasst
   jede beteiligte und auf der Plattform angemeldete Figur einen eigenen Post
   aus ihrer persönlichen emotionalen Perspektive. Mehrere Posts dürfen daher
   dasselbe objektive Ereignis unterschiedlich rahmen.
5. Ein Booster enthält genau vier Kartenresultate für neue Darstellungen
   desselben gebundenen Kartenmotivs. Nach der gültigen Bewertung werden immer
   vier Karten enthüllt: Reject erzeugt eine neue bildlose Standardkarte; Keep
   oder Favorite branden bevorzugt eine vorhandene freie Standardkarte des
   gewählten Decks und erzeugen nur bei fehlendem freien Körper eine neue
   CardIdentity. Mehrere Booster desselben Motivs können später
   Challenger-Aufbau und einen 16er-Cup speisen.
6. Die VN erzeugt durch neue Situationen, Beziehungen, Outfits, Tätigkeiten,
   Orte und Stimmungen bessere beziehungsweise vielfältigere Kartenkontexte.
   Karten- und Duellfortschritt eröffnet umgekehrt neue Begegnungen,
   Rivalitäten und VN-Situationen. Die Verbindung ist bidirektional.
7. Der Card Battler ist ein in die VN-Welt eingebettetes Kurzzeitbelohnungs- und
   Kurzzeitmotivationssystem. Er liefert schnelle Fortschrittssignale,
   Konkurrenz, Sammlung und Variation zwischen langfristigen VN-Freigaben,
   bleibt aber der VN und ihrer Figurenmotivation untergeordnet.
8. Andere Figuren können innerhalb der Fiktion ebenfalls Nutzer der Plattform
   und gegnerische Kartenspieler sein. Technisch als PvE gespielte Gegner
   erscheinen storyseitig als Mitschüler, Rivalen oder andere benannte Nutzer,
   nicht als abstrakte KI-Gegner.
9. Die konkrete Academy, ihre Uniform, Campusästhetik und wiederkehrenden Orte
   entstehen pro Save aus Prolog-Evidence, strukturierten Vorschlägen,
   deterministischer Validierung und dem bestehenden M6-Bildloop. Sie werden
   nicht als fertige Inhaltsdatenbank ausgeliefert.
10. Eine weltweit vorhandene Plattform berechtigt nicht zum Ausliefern oder
    impliziten Laden globaler Nutzer-, Post-, Karten-, Prompt- oder Bilddaten.
    Der persönliche Runtime-Katalog bleibt bei einem neuen Save inhaltlich leer.
11. Der Spieler reagiert auf einen Post mit genau einer von fünf sichtbaren
    Reactions. Die Reaction ist ein kleiner unmittelbarer sozialer
    Beziehungsmoment und kann auf einem packfähigen Post einen BoosterIntent
    eröffnen. Die anschließende Bildbewertung bleibt davon getrennt.
12. Reject, Keep, Favorite, ein technisches Ausbleiben einer Karte und Delete
    or Live verändern keine Beziehung. Erst die spätere sichtbare Verwendung
    einer entstandenen Karte ist ein zweiter, eigener und kontextabhängiger
    Beziehungsmoment.

## Gemeinsamer erzählerischer Loop

```text
DayInstance, Ort, Tätigkeit und verfügbare soziale Begegnungen
  → Spielerchoice oder optionaler Reaktionsimpuls
  → validierte, LLM-realisierte VN-Szene und Beziehungserlebnis
  → eigener Social-Post jeder beteiligten Figur mit eigener emotionaler Haltung
  → sichtbare Post-Reaction und unmittelbarer kleiner Beziehungseffekt
  → bei packfähigem Post: Kartenmotiv und erster Booster
  → vier Kartenbilder innerhalb einer Trial-Spielvariante bewerten
  → vier Kartenresultate: Reject bleibt bildlos, Keep/Favorite binden das Bild
  → gegebenenfalls weitere Booster desselben Motivs
  → Challenger-Aufbau, 16er-Cup und Kombinationschampion
  → aktuell spielbare persönliche Karten und Deck-Readiness
  → sichtbare Kartenverwendung mit eigenem Relationship Context
  → Duell, Rivalität oder Plattformfortschritt
  → neue VN-Begegnung, neuer Kontext oder neuer Post
```

Die Pfeile beschreiben keine zwingende Einzelschritt-Kette für jeden Post.
Nicht jeder Feed-Eintrag muss ein Pack erzeugen, nicht jedes Pack muss sofort
zu einem Duell führen und nicht jeder VN-Fortschritt darf durch einen Sieg
gesperrt sein. Das spätere Pacing muss verhindern, dass der emotionale
VN-Verlauf durch permanente Drops und Pflichtkämpfe verdrängt wird.

### Motivationshierarchie

Die Systeme besitzen bewusst unterschiedliche zeitliche Funktionen:

```text
Langzeitmotivation
└─ VN, Dating Sim, Beziehungen, Character-Arcs, beide Academy-Jahre und Endings

Mittelfristige Motivation
└─ neue soziale Kontexte, Posts, visuelle Entwicklung, Kartenmotive und Rivalen

Kurzzeitmotivation
└─ Boosteröffnung, Bildentscheidung, Kartenfortschritt, Deckbau und Matches
```

Die VN ist nicht nur der Kontext für die übrigen Systeme, sondern deren
eigentliche langfristige Belohnung. Der Spieler entwickelt Bilder, Karten und
kurze Wettbewerbspfade, um anschließend Figuren und gemeinsame Situationen in
einer reicheren, persönlicheren und visuell verlässlicheren VN weiterzuerleben.
Der Card Battler überbrückt längere Entwicklungswege mit schnell verständlichen
Zielen und unmittelbarem Feedback. Er darf weder zum gleichrangigen Endzweck
werden noch die emotionale Auszahlung einer Beziehung durch bloße Zahlen,
Raritäten oder Siege ersetzen.

Die VN ist dabei nicht bloß ein Lieferant für Kartenmaterial. Ein erlebter
Moment erhält in der Plattform eine zweite, spielbare Ausdrucksform. Das
Bildspiel klärt, welche Darstellung dieses Moments als Karte Bestand hat; der
Card Battler trägt ausgewählte Konflikte, Rivalitäten und Belohnungsspitzen
derselben Geschichte.

## Posts, Reactions und Beziehung

### Posts aus Alltag und VN-Ereignissen

Figuren posten aus ihrem Alltag und nicht nur dann, wenn das Spiel einen
Booster benötigt. Nach einem konkreten VN-Ereignis verfasst jede beteiligte und
auf der Plattform aktive Figur einen eigenen Beitrag. Der Post bildet ihre
subjektive emotionale Haltung ab, nicht eine neutrale Zusammenfassung der
Szene. Dasselbe Ereignis kann deshalb einen begeisterten Post von Figur A,
einen verletzten Post von Figur B und einen ausweichend-neutralen Post von
Figur C hervorbringen.

Alltagsposts können ebenso aus abgeschlossenen `PlaceActivityContract`s
entstehen. Jede Aktivität besitzt mindestens einen Character-Bezug und
garantiert mindestens eine mögliche, aber nicht zwingend veröffentlichte
Post-Perspektive. Dadurch bleibt auch eine Nicht-VN-Aktivität an den Social
Loop angeschlossen:

```text
PlaceActivityContract
→ ActivityOutcomeContext
→ mindestens ein PostOpportunityContract
→ optional materialisierter Post
→ sichtbare Reaction
→ falls packfähig: BoosterIntent
```

Eine daraus entstehende Karte bleibt nachvollziehbar an ihren Quellpost, dessen
Autor, die beteiligten beziehungsweise dargestellten Figuren, das
Storyereignis, die emotionale Rahmung und die gewählte Reaction gebunden. Die
Karte behauptet damit nicht, die objektiv wahre Version des Ereignisses zu
zeigen.

### Fünf gegenseitig ausschließende Reactions

Der Spieler kann auf einen Post mit genau einer der folgenden sichtbaren
Reactions antworten:

| Reaction | Primäre soziale Aussage |
|---|---|
| `thumbs_up` | Zustimmung oder positive Bewertung des Beitrags |
| `thumbs_down` | Ablehnung oder negative Bewertung des Beitrags |
| `happy` | positive emotionale Resonanz oder geteilte Freude |
| `sad` | Mitgefühl oder geteilte negative Emotion |
| `neutral` | Kenntnisnahme, Zurückhaltung oder bewusst offene Haltung |

Die primäre UI darf dafür `👍`, `👎`, `🙂`, `😢` und `😐` verwenden, benötigt
aber eindeutige zugängliche Labels und Tooltips. Eine Reaction hat zwei
voneinander getrennte mögliche Folgen:

1. Als sichtbare soziale Antwort ist sie ein kleiner unmittelbarer
   Beziehungsmoment gegenüber dem Autor des Posts.
2. Bei einem packfähigen Post kann sie einen versionierten `BoosterIntent`
   eröffnen. Das bedeutet nicht, dass der Booster sofort oder zwingend
   ausgespielt werden muss; Zeitpunkt und Pacing bleiben Aufgabe des
   Schedulers.

Die Reaction ist weder Bildrating noch direkte Promptanweisung. Sie darf die
emotionale und erzählerische Lesart des Moments sowie seine Packfähigkeit
beeinflussen, aber weder Aussehen, Stil, Promptfragmente, Gewichte, visuelle
Hypothesen noch Character Canon setzen. Die visuelle Präferenz des Spielers
wird nach dem eng begrenzten Prolog-Bootstrap ausschließlich durch Booster und
die darin gebundenen M6-Bildspiele, Reviews, Begründungen und Vergleiche erfasst
und geschärft.

```text
PostReaction
├─ authored SocialOutcome → kleiner unmittelbarer Beziehungseffekt
└─ falls packfähig: BoosterIntent → Generation Context → M6-Bildreview
                                              └─ Visual Preference Evidence
```

### Harte Grenze zwischen Social- und Visual-Entwicklung

Direktnachrichten, Gruppenchat, VN-Dialog, Posts und Post-Reactions dürfen
Erfahrung, Knowledge, Beliefs, Relationship, Tension, Social Edges und spätere
Scene-Varianten verändern. Das gilt ausdrücklich auch für Beziehungen und
Wissensverbreitung zwischen den Figuren untereinander. Kein solcher sozialer
Input erzeugt visuelle Preference Evidence, Prompt-/Recipe-Credit, eine
Evolution Challenge oder eine Character-Canon-Änderung.

Ein sozialer Outcome kann einen authored Storykontext freischalten und dadurch
einen neuen Darstellungsbedarf erzeugen. Eine Einladung zum Sommerfest darf
beispielsweise eine Szene mit Festival-Outfit erforderlich machen. Wie Figur,
Outfit, Ort und Moment aussehen und welche Darstellung gewinnt, entscheidet
aber ausschließlich der nachgelagerte Booster-/Bildspiel-Loop.

```text
Chat, Post und Reaction
→ Social-/Knowledge-/Relationship-State
→ authored Storykontext und gegebenenfalls Darstellungsbedarf

Booster und Bildspiele
→ Visual Preference Evidence
→ Prompt-/Recipe-Lernen, Assetauswahl und kontrollierte visuelle Entwicklung
```

### Getrennte Beziehungsmomente

Die soziale Reaction und die spätere Verwendung einer Karte sind zwei eigene
Beziehungsmomente. Die dazwischenliegenden privaten Bild- und
Sammlungsentscheidungen sind keine Beziehungsmomente:

| Handlung | Beziehungseffekt |
|---|---|
| sichtbare Reaction auf einen Post | kleiner, unmittelbarer authored Effekt gegenüber dem Postautor |
| `Favorite`, `Keep` oder `Reject` im Bildreview | keiner |
| alle Kandidaten abgelehnt und vier bildlose Standardkarten entstanden | keiner |
| Karte nur gesammelt oder ins Deck gelegt | keiner |
| `Delete or Live` | keiner |
| Karte in einem privaten Match verwendet | zunächst nur gegenüber dem Gegenspieler sichtbar; kein automatischer Effekt auf abwesende Figuren |
| Gegenspieler erzählt oder postet später von der Verwendung | möglicher kleiner authored Effekt, sobald eine betroffene Figur glaubwürdig davon erfährt |
| Karte in einem öffentlichen, gestreamten oder gemeinsam besuchten Match verwendet | möglicher kleiner authored Effekt auf tatsächlich anwesende oder nachweislich informierte betroffene Figuren |

Der zweite Effekt kann stärker sein, ist aber nicht pauschal positiv oder
negativ. Er hängt mindestens vom Quellpost und seiner Haltung, der dargestellten
Figur, dem konkreten Kartenbild, der ursprünglichen Reaction, Gegner,
Öffentlichkeit und Bedeutung des Einsatzes, dem aktuellen Beziehungszustand
und dem Wissen der Figur ab. Eine positive Karte aus einem negativen Post kann
für die betroffene Figur ebenso unangenehm sein wie eine negative Darstellung
eines für sie schönen Moments.

Boosteröffnung, Bildreview, Kartenenthüllung, Sammlung und Deckbau sind privat.
In einem gewöhnlichen direkten Match kennen zunächst nur Besitzer und
Gegenspieler die tatsächlich ausgespielten Karten. Die dargestellte Figur wird
nicht durch die Plattform automatisch informiert. Der Gegenspieler darf das
Erlebte später weitererzählen oder im Rahmen seiner Sichtbarkeitsrechte posten;
erst dieses neue glaubwürdige Kenntnisereignis kann weitere Figuren erreichen.
Bei einem öffentlichen, gestreamten oder gemeinsam besuchten Match ist der
Kenntniskreis entsprechend größer, aber niemals automatisch die gesamte
Plattformöffentlichkeit.

Die grundsätzliche Teilnahme- und Darstellungszustimmung erlaubt die
Kartenverwendung, garantiert aber keine positive emotionale Reaktion darauf.
Ohne glaubwürdiges Kenntnisereignis entsteht kein Beziehungseffekt. Auch mit
Kenntnis bleibt die Dating-Sim-Wirkung bewusst klein und authoriert: kurze
Reaktionen, Gesprächsvarianten, leichte Zu- oder Abneigung und gelegentliche
Folgesituationen statt großer automatischer Routenwechsel. Um Beziehungs-
Farming zu vermeiden, zählen nur erstmalige bedeutsame Enthüllungen, neue
Öffentlichkeitsstufen oder besondere Meilensteine, nicht jede wiederholte
mechanische Ausspielung derselben Karte.

## Getrenntes mentales Modell für Post und Booster

Ein Post bindet spielerseitig mindestens:

- den Autor und dessen emotionale Rahmung,
- die dargestellte beziehungsweise beteiligte Figur oder Figurengruppe,
- den erzählerischen Anlass,
- sichtbare Elemente wie Ort, Outfit, Tätigkeit und Stimmung,
- sowie Zeitpunkt, Beziehungen und gewählte Reaction.

Ein Post ist Story-, Kommunikations- und Herkunftsobjekt. Er ist nicht selbst
der Booster und nicht jeder Post ist packfähig. Ein packfähiger Post darf ein
versioniertes Kartenmotiv für eine Playground-Kombination und daraus einen
ersten Booster eröffnen.

Ein Booster ist in der Welt tatsächlich ein versiegeltes Pack aus genau vier
Kartenresultaten. Beim Öffnen erhalten vier Slots je eine neu erzeugte
Darstellung desselben Kartenmotivs. Nach der Bewertung werden alle vier als
Karten enthüllt. Keep/Favorite entwickeln bevorzugt vorhandene freie
Standardkarten des gewählten Decks; Rejects werden als neue bildlose
Standardkarten der Sammlung zugeordnet. Vier Rejects sind daher kein leeres
Pack, sondern vier neue bildlose Standardkarten. Die verworfenen Bilder
liefern negative visuelle Evidence und keine neuen visuellen Challenger; ein technisch fehlendes
oder unbewertbares Bild ist dagegen kein Reject und muss ersetzt werden, bevor
der Booster abgeschlossen ist.

Die längere Entwicklung eines Kartenmotivs ist eine Folge mehrerer einzelner
Booster. `Boosterfolge` dient dafür nur als Arbeitsbegriff: Abhängig von
Ergebnissen und offenem Challenger-Bedarf können weitere Packs desselben Motivs
erscheinen und schließlich den Kombinations-Cup derselben
Figur-/Outfit-/Ort-Bindung speisen. Damit bleibt die vertraute Erwartung „ein
Booster enthält Karten“ erhalten, ohne den länger laufenden Bildvergleich mit
einem einzelnen Pack gleichzusetzen.

Beispiel:

```text
VN-Ereignis
  Aiko und der Spieler verbringen einen Sonntagnachmittag in der Shopping Mall.

Post
  „Eigentlich wollte ich nur kurz mitkommen. War dann doch ein ziemlich guter
  Sonntag.“

Kartenmotiv
  Aiko · Shopping Mall · Sonntagsoutfit

erster Booster
  vier kontrolliert variierte Darstellungen dieser Playground-Kombination
  → Reject erzeugt neuen bildlosen Standard
  → Keep/Favorite branden bevorzugt freie Standardkörper des Zieldecks
  → fehlt ein freier Körper, entsteht eine neue und sofort gebrandete Karte
  → alle vier Slots liefern Kartenresultate; nur Keep/Favorite werden Bildkarten
  → nur geeignete Keeps/Favorites füllen den Challenger-Pool

weitere Booster desselben Kartenmotivs
  → sechzehn unterschiedliche Challenger eröffnen den 16er-Cup
  → Sieger beziehungsweise Title-Match bestimmt den Kombinationschampion
```

Der sichtbare Post ist nicht zwingend der wortwörtliche Prompt. Serverseitig
muss der Booster zusätzlich auf dem autoritativen Character-, Story- und
Generation Context beruhen. Eine freie Caption darf keine Identität, Canon-
Revision, Playground-Kombination, Promptregel oder technische Versuchsachse
erfinden.

## Qualitätsversprechen, Bildchallenge und Legendary

Die zentrale sichtbare Bewertungsfrage lautet:

> Welche Darstellung dieser Figur in genau dieser Situation bevorzuge ich?

Die Plattform verspricht dabei nicht bloß dekorative Varianten. Sie soll im
Rahmen des gewählten visuellen Stils zunehmend treffende, glaubwürdige und
hochwertige Darstellungen derselben gebundenen Figur-/Outfit-/Situations-
Kombination erzeugen. `Realistisch` bedeutet hier vor allem Wiedererkennbarkeit,
Plausibilität, Kontexttreue und überzeugende Bildqualität; es erzwingt keinen
fotorealistischen Stil und keine vermeintlich objektive Erinnerung.

Der aktuelle Kombinationschampion darf deshalb durch neue, kontrolliert
variierte Bildkandidaten wiederholt herausgefordert werden:

```text
bestehende bevorzugte Darstellung
→ neue Booster mit unabhängigen Kartenbildern derselben Kombination
→ Review und Challenger-Qualifikation
→ 16er-Cup
→ Cup-Sieger gegen aktuellen Champion
→ bisheriges Bild bestätigt oder durch bevorzugten Challenger ersetzt
→ nächste verbesserte Generierungs- und Challenge-Runde
```

Das Bild einer bestehenden Karte wird dabei niemals still verbessert oder
überschrieben. Gewinnt ein neues Bild, entsteht beziehungsweise gewinnt eine
andere CardIdentity den Championplatz. Gewinnt der Amtsinhaber, bleibt er
Champion und erhält den regelgültigen eigenen Entwicklungsfortschritt. So
bleiben tatsächliche Bildentwicklung, Vergleichshistorie und Kartenprovenienz
sichtbar.

`Legendary` ist keine zufällig gezogene Seltenheit und kein Synonym für einen
einmaligen Favorite-Klick. Die Stufe belegt, dass genau diese Karte über viele
regelgültige Booster-/Cup-Erfolge und Championbegegnungen hinweg gegen zahlreiche
unabhängige Mitbewerber bestanden hat. Wiederholungen derselben Kandidaten,
leichte Farm-Matches oder normale Card-Battler-Siege dürfen diesen Nachweis
nicht ersetzen.

Die Erstbewertung bestimmt dabei die Startposition und nicht den endgültigen
Wert einer Karte: Reject lässt den Kartenkörper bildlos auf Standard, Keep
brandet ihn mindestens als Common Level 1 und Favorite mindestens als Rare
Level 1. Die Standardkarte aus einem Reject ist eine reale persönliche
Spielkarte, aber keine Bildkarte und deshalb kein visueller Challenger.

Die Bezeichnung der Leiter von `Common` bis `Legendary` ist ein historisch aus
Sammelkartenspielen übernommenes Plattform-Branding. Da jede persönliche
Bildkarte ohnehin einzigartig ist, bezeichnet sie keine Druckauflage und keine
zufällige Dropwahrscheinlichkeit, sondern den erarbeiteten Bewährungs- und
Entwicklungsgrad. Legendary-Karten sind selten, weil der dafür erforderliche
Vergleichsweg lang und anspruchsvoll ist.

Championstatus, Legendary-Entwicklungsstand und aktuelle persönliche Präferenz
bleiben trotzdem getrennt. Eine Legendary-Karte kann später ihren
Championplatz verlieren und als historisch bewährte ehemalige Titelkarte
Legendary bleiben; ein neuer Sieger ist zunächst der aktuell bevorzugte
Champion, ohne dadurch die langjährige Bewährung seines Vorgängers zu erben.
Der Card Battler verwendet diese Kartenstände und erzeugt selbst keine neue
Bildpräferenz, keinen Visual Champion und keine Assetfreigabe. Regelgültige
Verwendung darf jedoch `CardBattleExperience` derselben CardIdentity schreiben
und dadurch eine eigene Kartenentwicklung vorbereiten. Diese
`CardBattleEvolution` ist vom Wettbewerb neuer Darstellungen im Visual Circuit
streng getrennt und kann den dort erforderlichen Vergleichsnachweis für
Legendary niemals ersetzen.

## Memory, Kampferfahrung und irreversible Kartenmythologie

Eine persönliche Bildkarte besitzt einen unveränderlichen Ursprung: den
Quellpost, den erlebten Moment, das bestätigte Ursprungsbild und die erste
gebildete Kartenrevision. Die Welt behandelt diesen Zusammenhang als ihr
`Memory`. Es ist keine objektive Aufzeichnung des Geschehenen, sondern die
konkrete Darstellung, die der Kartenbesitzer in diesem Moment angenommen hat.

> Eine Bildkarte konserviert eine Erinnerung nur so lange, bis man beginnt,
> mit ihr zu kämpfen.

Wird eine solche Karte in regelgültigen Matches tatsächlich eingesetzt,
sammelt sie Kampferfahrung. Dabei zählen nachvollziehbare Spielereignisse wie
Ausspielen, Verteidigen, Angreifen, Trait-Nutzung, entscheidende Wendepunkte und
der Kontext eines Rivalen-, Liga- oder Cupmatches. Bloßes Vorzeigen, sofortige
Aufgabe, abgesprochene Wiederholung oder andere Farmmuster zählen nicht oder
werden durch eine versionierte Anti-Farm-Policy begrenzt.

Erreicht die Karte eine Entwicklungsschwelle, darf aus ihrer bis dahin
angesammelten Laufbahn eine neue aktive Spielform entstehen:

```text
unveränderliches Ursprungsmemory
→ regelgültige Verwendung und CardBattleExperience
→ reproduzierbarer CardBattleExperienceDigest
→ Entwicklungsschwelle
→ vier visuelle Evolutionskandidaten
→ menschliche Auswahl im gesonderten Evolution Trial
→ neue aktive Revision derselben CardIdentity
```

Die Darstellung entfernt sich mit jeder angenommenen Entwicklung kontrolliert
vom wörtlichen Moment und nähert sich einer anime-typischen, spielerischen
Mythologisierung: zuerst durch kleine Motive, dann durch stärkere Pose,
Rahmung, Symbolik und Kampfdynamik bis zu einer ikonischen Legendary-Fassung.
Figur und Ursprung müssen wiedererkennbar bleiben. Fantastische Elemente dieser
Kartenkunst sind Kartenmythologie und werden niemals rückwirkend zu VN-Canon,
CharacterVisualCanon oder einer Behauptung darüber, was damals wirklich
geschehen ist.

Der Ursprung wird nie überschrieben. Frühere Formen bleiben mit ihrer
Matchgeschichte sichtbar. Nimmt der Besitzer eine Evolution an, ist jedoch nur
noch die neue höchste Revision aktiv spielbar; ein freies Umschalten auf eine
frühere Form oder ein exaktes Duplizieren derselben Ursprungsdarstellung würde
die Entscheidung entwerten und ist ausgeschlossen. Wer an einer Kartenform
hängt, kann sie auf diesem Stand bewahren oder aus dem aktiven Wettkampf
zurückziehen. Dann verzichtet er auf die stärkere Form, nicht auf die
Erinnerung. Werden alle vier Evolutionskandidaten abgelehnt, bleibt die bisherige
aktive Revision unverändert und ein späterer neuer Versuch ist möglich.

Mechanische Entwicklung und visuelle Erklärung bleiben dabei serverseitig
getrennt. Der Server entscheidet über Erfahrung, Schwelle, Rarity, Werte und
Traits. Eine LLM darf nur aus einem begrenzten Experience Digest und den
feststehenden Regeln passende Bildkandidaten sowie erklärende Karten-Copy
vorschlagen. Die menschliche Auswahl entscheidet über die Darstellung, nicht
über frei erfundene Stärke.

Battle Experience allein macht keine Karte Legendary. Die Höchststufe verlangt
sowohl eine belastbare Kartenlaufbahn als auch den bereits festgelegten
visuellen Bewährungsnachweis gegen viele unabhängige Challenger. Normales
Matchgrinding kann weder Booster-/Cup-Historie noch Championbegegnungen
simulieren. Umgekehrt bleibt eine visuell erfolgreiche, aber nie eingesetzte
Karte nah an ihrem Ursprungsmemory und erreicht nicht allein durch
Kuratorenerfolge die vollständig mythologisierte Legendary-Form.

Damit entsteht der gewünschte soziale und emotionale Konflikt. Ein Full Deck
zeigt nicht bloß Wohlstand oder Spielstärke, sondern bis zu vierzig persönliche
Momente, deren Besitzer bereit war, sie durch Wettbewerb verändern zu lassen.
Bekannte Profis besitzen öffentlich erinnerte Kartenlaufbahnen; Fans vergleichen
frühe und aktuelle Formen, bewahrte Karten können feierlich zurückkehren, und
Sponsoren können Druck erzeugen, eine emotional wichtige Karte weiterzuentwickeln.
Rechtliche Freigabe der dargestellten Person und ihre spätere emotionale
Reaktion auf Verwendung oder Evolution bleiben verschiedene Zustände. Eine
Beziehungsfolge entsteht nur, wenn sie die konkrete Verwendung oder neue Form
nach den Sichtbarkeits- und Wissensregeln tatsächlich wahrnimmt.

## Zwei Wettbewerbsformen: Visual Circuit und Battle Circuit

Bis zur endgültigen In-World-Benennung dienen `Visual Circuit` und
`Battle Circuit` als klar unterscheidbare Arbeitsbegriffe. Beide verwenden
Bildkarten und können wie Wettbewerbe inszeniert werden, beantworten aber
verschiedene Fragen:

| | Visual Circuit | Battle Circuit |
|---|---|---|
| Leitfrage | Welche Darstellung trifft dieses gebundene Kartenmotiv für den Besitzer am besten? | Welcher Spieler gewinnt mit seinem Deck nach den Battler-Regeln? |
| Teilnehmer | kompatible Bildkarten beziehungsweise neue Bildkandidaten derselben Kombination | zwei Spieler und ihre regelgültigen Decks |
| Entscheider | der reale Spieler als Präferenzautorität des Protagonisten | deterministische Matchsimulation aufgrund der Spielerzüge |
| typische Form | Boosteröffnung mit vier Karten, Ranking, A/B-Auswahl, 16er-Bildbracket und Titelvergleich | Casual Match, Ranked Match, lokales Turnier und saisonaler Cup |
| verändert | Bild-Evidence, Challenger-/Bildtitel und visueller Bewährungsnachweis | Matchresultat, Spieler-/Saisonrang, CardBattleExperience und gegebenenfalls Storykontext |
| verändert nicht | Battler-Rang und öffentliches Spielerturnier | Bildbewertung, Visual Champion, Favorite, Assetfreigabe oder allein den Legendary-Nachweis |
| soziale Sichtbarkeit | grundsätzlich privater Kurations- und Entwicklungsprozess | je nach Matchtyp direkt, geteilt, gestreamt oder öffentlich inszeniert |

Der Visual Circuit darf spielerisch wie ein Turnier aussehen, besitzt aber
keinen fremden menschlichen Gegner. Der Besitzer lässt neue Darstellungen eines
Motivs gegeneinander antreten und bestimmt seinen bevorzugten Sieger. Die
einzelne Boosteröffnung erzeugt zunächst vier Karten; erst geeignete
Keep-/Favorite-Karten treten in diesem visuellen Wettbewerb an. Der
Battle Circuit beginnt erst dort, wo regelgültige Karten in einem Deck gegen
einen anderen Spieler eingesetzt werden. Er darf Kampferfahrung schreiben und
damit einen getrennten Evolution Trial freischalten; der laufende Matchsnapshot
selbst bleibt eingefroren und verändert keine Karte mitten im Duell.

Auch Titel benötigen deshalb immer einen qualifizierenden Kontext:

- `Visual Champion` beziehungsweise intern `SlotChampion`: aktuell bevorzugte
  Darstellung eines konkreten Kartenmotivs,
- `Legendary`: langfristig erarbeitete Entwicklungsstufe derselben CardIdentity,
- `Battler Champion`: Sieger eines öffentlichen Spieler- oder Saisonwettbewerbs,
- `Signature Champion`: repräsentative Karte eines Character-Portfolios nach
  eigenem Auswahlvertrag.

Ein „Cup“ ohne Zusatz ist in der späteren normalen Copy zu vermeiden. Ein
Bildbracket im Visual Circuit und ein öffentlicher Battler-Cup dürfen weder
sprachlich noch über Belohnungen, Ranglisten oder Beziehungseffekte miteinander
verwechselt werden. Die endgültigen Eigennamen sollen erst aus Plattformmarke,
Battler-Fantasie und visueller Inszenierung abgeleitet werden.

## Ableitung für Bildspiele und Frontend

Der Social-/Booster-Rahmen liegt **um** die bestehenden Spielmodi und verändert
nicht heimlich deren Evidenzvertrag:

| Spielerischer Moment | Geeignete Projektion | Fachlicher Vertrag bleibt |
|---|---|---|
| Auf einen Post reagieren | genau eine der fünf Reactions zeigen; sozialen Effekt und möglichen Packzugang erklären | `PostReactionReceipt`, authored Relationship Outcome und `BoosterIntent` bleiben getrennt |
| Ein Booster wird eröffnet | Quellpost, Kartenmotiv und genau vier zunächst bildlose Kartenkörper zeigen | versionierter Story-, Generation- und Combination Context |
| Vier neue Bilder beurteilen | die vier Kartenbilder in eine vorgelagerte Trial-Spielvariante führen | Qualifier, Ranking, Arena oder Ten-Point Calibration mit vollständiger Human Evidence |
| Bewertung abschließen | genau vier Kartenresultate enthüllen; Reject lässt eine bildlose Standardkarte, Keep brandet mindestens Common, Favorite mindestens Rare | Booster-Kartenkörper, bei Keep/Favorite persistente Image Identity, gebundener Craft Seed und validierte CardRulesRevision |
| Behaltene Karten gegeneinander führen | Cup, Title Match oder späterer Card Battler | vorhandene Qualification, Pairwise Evidence und Championtitel |
| Eine Kartenbeschreibung prüfen | Beschreibung zwei bereits behaltenen Karten zuordnen | getrennte DescriptionMatchEvidence ohne Kartenpromotion |
| Ein Bild endgültig entfernen | bewusste Sammlungs-/Cleanup-Entscheidung | Delete or Live; Reject löscht nicht automatisch |
| Eine Karte sichtbar verwenden | Match-, Gegner-, Quellpost- und Figurenkontext binden | eigener `CardUsageEvent`, idempotente Kampferfahrung und gegebenenfalls authored Relationship Outcome; kein Review- oder Champion-Write |

Ein Booster ist damit ein erzählerischer Herkunfts- und Belohnungsrahmen für
genau vier neue Kartenresultate, **kein zusätzlicher technischer Game Mode**.
`Trials` bleibt der gemeinsame Spielbereich; die konkrete Spielvariante
bestimmt, wie der Spieler die vier Kartenbilder bewertet. Post, Kartenmotiv,
einzelner Booster, Boosterfolge, Challenger-Pool und 16er-Cup bleiben getrennte
Entitäten desselben Wegs.

Diese Vier-Spielkarten-Zusage bezeichnet einen regulären Battle-Booster.
Adult-Content kann später in einem getrennten, ausdrücklich freigeschalteten
Bereich desselben Networks ebenfalls als Booster inszeniert werden. Ein solcher
Adult-Booster nutzt weiterhin Bildspiele und liefert gescopte Bild-Evidence,
erzeugt aber keine CardIdentity, keine Deckkarte und keine Cup- oder
Champion-Eligibility. Gestaltung, Bezeichnung und Ergebnisbildschirm müssen ihn
deshalb klar vom Battle-Booster unterscheiden; seine spätere VN-Funktion bleibt
ein eigener Vertrag.

Die regulären visuellen 16er-Cups sind immer charactergebunden. Ihr Titelkontext
besteht aus `Character + 1 Aspekt`, `Character + 2 Aspekte` oder `Character + 3
Aspekte`. Aspektkombinationen ohne Character existieren im Card-/Championpfad
nicht. Dasselbe Bild darf zu mehreren kompatiblen Granularitäten passen und
mehrere Titel gewinnen, bleibt dabei aber dieselbe Bild- und Spielkarte.

Der diegetische Booster-Rahmen darf unterschiedliche technische
`GenerationFocus`- und Assetfragen tragen, ohne sie storyseitig gleichzusetzen.
Ein sichtbarer Kandidat kann beispielsweise gleichzeitig als Kartenbild
beurteilt werden und gescopte Evidence zu Character Identity, Outfit, Scene
oder Composition liefern. Ob er später für Portrait, Sprite, Story-CG oder eine
andere VN-Assetrolle geeignet ist, benötigt dennoch eine eigene Qualifikation
und Freigabe.

Verbindlich getrennt bleiben:

| Ebene | Bedeutung |
|---|---|
| Diegetic Card Context | Warum der Protagonist dieses Bild innerhalb der Plattform sieht und auswählt |
| Generation Focus | Welche kontrollierte technische oder visuelle Frage der Batch untersucht |
| Human Preference Evidence | Was die reale Spielerentscheidung im erlaubten Scope über visuelle Präferenz aussagt |
| Card Crafting | Wie jeder Boosterplatz genau eine CardIdentity erhält und Keep/Favorite zusätzlich das bewertete Bild als Branding binden |
| Asset Qualification | Ob dasselbe Bild oder eine Ableitung eine konkrete VN-Rolle erfüllen darf |

Eine starke Karte ist deshalb nicht automatisch ein geeignetes VN-Sprite oder
Story-CG. Umgekehrt darf ein visuell nützliches Character- oder Place-Bild als
schlichte Karte bestehen. Kartenbezogene Effekte, Rahmen und dramatische
Komposition dürfen Character-Identity-Evidence nicht kontaminieren;
übertragbar sind nur ausdrücklich kompatible, gescopte Beobachtungen.

Die bildlose Standardkarte besitzt nur ATK, DEF und ein mögliches Kampfprofil,
aber noch keinen Trait und keinen Effekttext. Mit dem ersten Level Up entsteht
der erste mechanische Trait. Sobald ein Bild gebunden ist, erklärt die
Kartenfassung die bereits feststehenden Traits über das sichtbare Handeln, die
Figur oder den Moment im Bild. Diese Einbettung darf atmosphärisch und
anime-typisch sein, aber weder die Battler-Regel verändern noch neue
VN-Wahrheit schaffen.

## Card Battler, Saison und Championmotivation

Der Card Battler ist keine Academy-Erfindung, sondern ein etablierter Teil der
globalen Plattformkultur. Er erzeugt kurzfristigen Wettbewerb, Status,
Rivalitäten, Creator- und Fankultur sowie gemeinsame soziale Anlässe. Ein
Plattformaccount erzwingt keine Teilnahme: Figuren dürfen reine Feed-Nutzer,
Creator, dargestellte Personen, Sammler, aktive Battler oder bewusste
Nichtnutzer sein.

Der Card Battler verwendet die gemäß CharacterChampionSignature,
Championbelegung und Availability aktuell spielbare Teilmenge derselben
persistenten Bildkarten und erzeugt keine zweite unabhängige Bildsammlung. Ein neuer Save beginnt mit
einem schwachen bildlosen Standard-Base-Deck. Rejects lassen zusätzliche
Kartenkörper bildlos auf Standard, Keeps branden sie mindestens als Common
Level 1 und Favorites mindestens als Rare Level 1. Booster-/Cup-Siege,
Championerfolge und bestätigte Kampferfahrung entwickeln dieselbe Karte über
Uncommon, Rare, Super und Ultra; Legendary wird erst bei gemeinsam erfülltem
Visual- und Battle-Nachweis materialisiert. Serverseitig bestätigte
Deck-Readiness bleibt für jedes Match verbindlich.
Kontextgebundene Championtitel einzelner Karten müssen von späteren Deck-,
Spieler- und Saisontiteln sprachlich und fachlich getrennt bleiben.

### Eine gemeinsame Ligakultur mit gemischten Decks

Die Plattform besitzt keinen getrennten Wettbewerb für bildlose, öffentliche
und persönliche Karten. Alle zulässigen Kartenquellen treffen in demselben
Regel-, Ranglisten-, Liga- und Cup-Ökosystem aufeinander. Die Quellenregeln
entscheiden, was ein Account besitzen und einsetzen darf; sie erzeugen keine
gesellschaftlich abgetrennte Spielklasse.

Der Normalfall ist ein gemischtes Deck. Die meisten Nutzer spielen überwiegend
mit verlässlichen bildlosen Standardkarten, ergänzen einzelne öffentliche
Eventeditionen und besitzen nur wenige persönliche Bildkarten. Persönliche
Karten bieten individuellere Entwicklung und stärkere erzählerische Bindung,
sind aber weder automatisch überlegen noch Voraussetzung für ein
wettbewerbsfähiges Deck. Ihre Erstellung, Pflege und Entwicklung kosten Zeit;
hohe Rarities besitzen anspruchsvollere Ausspielhürden. Ein Full Deck aus
vierzig Bildkarten ist deshalb selten, prestigeträchtig und biografisch
aussagekräftig, aber nicht zwingend die optimale Strategie.

Die etablierte Wettbewerbspyramide dient bis zur endgültigen In-World-Benennung
als verbindlicher Rahmen:

```text
plattformweite Ranked Ladder
→ Community- und lokale Ligen
→ Kobe-Stadtliga
→ Kansai-Regionalliga
→ nationale Liga
→ internationale Premier-/Crown-Ebene
```

Eine Liga bildet eine fortlaufende Saison mit Tabelle, Auf- und Abstieg oder
Qualifikation. Cups sind davon getrennte K.-o.-Ereignisse, die auch unabhängig
von einer vollständigen Ligakarriere zugänglich sein können. Duelle bleiben
1-gegen-1; auf höheren Ebenen können Teams Spieler beschäftigen und melden,
während offene Cups weiterhin Einzelpersonen einen sichtbaren Weg nach oben
geben. Minderjährige gehören derselben Kultur und denselben grundsätzlich
erreichbaren Wettbewerben an, spielen aber aufgrund des Quellenvertrags nur
mit Standard- und öffentlichen Eventkarten.

`BattlerRating`, `SeasonStanding`, öffentliche Reichweite und persönlicher
Relationship State sind voneinander getrennt. Ein Influencer kann schwach
spielen, ein Spitzenprofi sozial unscheinbar sein und eine Academy-Figur ohne
Battlerambition trotzdem zentral für die VN bleiben. Profis finanzieren sich je
nach Ebene durch Teamgehalt, Ligateilnahme, Preisgeld, Sponsoring, Medien- und
Creatorerlöse sowie Auftritte. Konkrete Summen, Saisondauer,
Qualifikationsquoten und Eigennamen bleiben offen. Weder die Academy noch der
16er-Cast werden dadurch zu einer verpflichtenden E-Sport-Ausbildung; die
Ligakultur ist ein allgegenwärtiger möglicher Lebensweg und Storyraum.

### Singleplayer-Network und Gegnerkreise

Der vollständige Produktpfad bleibt Singleplayer. Ein spielerseitig als
`Online-Match` inszeniertes Duell bedeutet ausschließlich, dass der Protagonist
innerhalb der fiktionalen Plattform gegen einen anderen Nutzeraccount antritt.
Technisch wird jeder Gegenspieler als serverseitig simulierter PvE-NPC geführt;
es gibt keine Verbindung zu realen Spielern, kein menschliches Matchmaking und
keinen fremden Live-Datenbestand. Die Gegnerlogik bleibt deterministisch und
verwendet keine Story- oder Karten-LLM für Live-Entscheidungen.

Es existieren zwei getrennte Gegnerkreise:

- Figuren des festen 16er-Story-Casts können abhängig von ihrer authored
  `battler_stance` Nichtspieler, neugierige Einsteiger, Casual-Spieler, aktive
  Battler oder wettbewerbsorientierte Rivalen sein. Nur innerhalb dieses Casts
  entstehen persistente Rivalry States und daraus folgende VN-Arcs.
- zufällig vermittelte Remote-NPCs repräsentieren die breite
  Plattformbevölkerung. Sie besitzen einen leichten, save-lokalen Account-,
  Deck-, Geschmacks- und Kartenhistorienvertrag, werden aber nicht zu neuen
  Rivalen oder zusätzlichen Fokusfiguren außerhalb des 16er-Casts.

Ein Story-Character muss nicht battlen. Authored Entwicklung darf eine Figur
zum Einstieg bewegen, ihren Ausstieg begründen oder einen Beziehungspfad
eröffnen, auf dem der Protagonist bewusst nicht spielt. Für gleichzeitig
bestehende Rivalitäten gibt es keine harte mechanische Höchstzahl. Der Story
Director begrenzt stattdessen aktive Rivalry Beats, Eskalationen und
Folgeszenen so, dass jede Rivalität innerhalb des VN-Kontexts plausibel bleibt.

### Alters- und Kartenquellenvertrag

Social Network und Card Battler sind nicht pauschal ab 18. Minderjährige dürfen
Accounts führen, dem Plattformspiel folgen und mit einem regelgültigen Bestand
aus bildlosen Standardkarten sowie offiziell freigegebenen öffentlichen
Eventeditionen spielen. Erst die personenbezogene Kartenfunktion ist an eine
verifizierte Volljährigkeit gebunden.

```text
CardProvenance
├─ blank_standard
│  └─ für alle zulässigen Accounts; keine dargestellte Person
├─ public_event
│  └─ offiziell freigegebene PublicCardEdition; keine private Postherkunft
└─ personal_post
   └─ nur für verifizierte volljährige Besitzer und vollständig
      einwilligungsfähige, verifizierte volljährige erkennbare Personen
```

Für einen minderjährigen Account sind Erzeugung, Branding, Besitz und aktive
Verwendung von `personal_post`-Karten gesperrt. Die Sperre betrifft die
Kartenquelle und nicht den gesamten Battler. Öffentliche Eventeditionen
durchlaufen einen eigenen Rechte- und Content-Approval-Vertrag, gehören nicht
zum persönlichen Post-/Booster-/Visual-Circuit und erzeugen weder
PlayerPreferenceEvidence noch Relationship Outcomes. Sie geben jüngeren
Spielern einen bildgetragenen Sammlungs- und Spielpfad, ohne private Personen
zu Kartenmotiven zu machen.

Eine persönliche Kartenfreigabe verlangt zum Zeitpunkt des Quellposts und der
Generierung Volljährigkeit und wirksame Battler-Einwilligung aller erkennbar
dargestellten Personen. Sobald eine erkennbare Person minderjährig,
altersunverifiziert oder nicht wirksam einwilligend ist, darf aus dem Post kein
persönlicher Battle-Booster entstehen. Die Plattform darf dieses Verbot weder
durch Zuschneiden noch durch spätere Volljährigkeit rückwirkend umgehen;
Posts und Bilder aus der Zeit vor dem 18. Geburtstag bleiben für persönliche
Spielkarten unzulässig.

Da alle Studierenden bei Academy-Eintritt volljährig sind, steht dem gesamten
spielrelevanten Academy-Cast der persönliche Post- und Bildkartenloop vom
ersten Storytag an grundsätzlich offen. Ob eine konkrete Figur teilnimmt oder
einem konkreten Post zustimmt, bleibt weiterhin ihr eigener Plattform- und
Storyzustand.

### Konkrete Kartenfiguren und öffentliche Editionen

Jede Bildkarte besitzt genau eine konkrete primäre `CardSubjectIdentity`.
Zulässige Subjekte sind eine Person aus einem erlaubten sozialen Kontext, eine
fiktionale Person des öffentlichen Interesses, ein bekannter Battler oder
Performer, ein konkretes Tier, Maskottchen oder anderes identifizierbares
Creature. Die bildlose Standardkarte bleibt strukturell eine universelle
Figurenkarte, behauptet aber noch keine dargestellte Person oder Situation.

Offizielle öffentliche Events dürfen save-lokale `PublicCardEdition`s erzeugen,
die viele Accounts besitzen können. Ein Event wie `Hol dir den Dinosaurier` bindet
einen konkreten Dinosaurier als Kartenfigur; Ort, Event und anwesende Menge
bilden den kontrollierten Kontext. Andere Personen dürfen nur dann als
erkennbare Haupt- oder Mitfiguren auftreten, wenn der entsprechende Mehrfiguren-
und Rechtevertrag der öffentlichen Edition erfüllt ist. Ein solches Event
benötigt keine bestimmte Relationship- oder zweite Storyfigur als
Teilnahmevoraussetzung und ist kein `PlaceActivityContract` des Protagonisten.

Eine öffentliche Edition teilt Bild-, Herkunfts- und Ausgaberevision. Jeder
besitzende Account erhält dennoch eine eigene `CardIdentity`; mehrere Accounts
teilen weder Ownership noch matchlokalen Zustand. Öffentliche Editionen sind
damit eine frühe Brücke zwischen bildlosen Standarddecks und seltenen
persönlichen Momentkarten. Ihre genaue Rarity-, Entwicklungs- und
Verteilungslogik bleibt ein eigener Folgeentscheid.

### Core-Idee: Monsters & Heroes und gemischte Packs

Der Ziel-Battler verbindet zwei verständliche Kartenfantasien innerhalb
desselben universellen Figurenkarten- und Rulesets:

- `Hero` bezeichnet eine Karte mit einer konkreten Person oder charakterhaften
  Figur als Hauptsubjekt. Persönliche Heroes können aus erlaubten Posts,
  Erinnerungen, Favorites, Champions und späteren Evolutionen entstehen.
- `Monster` bezeichnet eine konkrete benannte Kreatur, ein Tier, Maskottchen
  oder anderes world-authored Creature, das insbesondere über öffentliche,
  offiziell freigegebene Editionen vielen Accounts zugänglich sein kann.

`Hero | Monster` ist zunächst eine Subjekt- und Spielerfantasie, kein zweiter
mechanischer Kartentyp. Beide bleiben Figurenkarten mit ATK, DEF, Feldmodus und
Traits. Die Subjektart ist außerdem von der Herkunft getrennt: Eine öffentliche
Edition kann einen öffentlichen Hero oder ein Monster zeigen, während eine
persönliche Karte weiterhin ihrem consent- und disclosuregebundenen
Quellkontext folgt. Bildlose Standards besitzen noch keine solche dargestellte
Subjektart.

Der Arbeitstitel `Monsters & Heroes` beschreibt diese In-World-Kartenkultur und
kann später Name des Battlers oder einer seiner Varianten werden. Er ist noch
kein final freigegebener Produkt-, Marken- oder Plattformname.

Im Zielsystem dürfen Packs unterschiedliche Karten- und Craftinganlässe
miteinander mischen. Ein gemeinsam geöffnetes Pack kann beispielsweise
öffentliche Monster, eigene Heroes, freigegebene Heroes eines Freundes oder
andere zulässige öffentliche Figuren enthalten. Dadurch besitzen Pack Openings
auch dann eine gemeinsame verständliche Spannung, wenn die Beteiligten nicht
alle dargestellten Personen persönlich kennen. Monster bilden den breiten
geteilten Kartenbestand; persönliche Heroes bewahren den einzigartigen
Story-, Memory- und Entwicklungswert.

Pack Opening und Bildbewertung sind dabei nicht dasselbe. Das Opening enthüllt
und inszeniert den Packinhalt. Erst ein nachgelagerter, nur wo benötigter
Card-Crafting- beziehungsweise Evolutionsschritt zeigt Bildkandidaten und erhebt
eine dafür autorisierte Bewertung. Ein Spieler kann im späteren Zielsystem ein
Pack für oder mit einem Freund öffnen und gegebenenfalls an der Entwicklung
einer fremden CardIdentity mitwirken. Eigentum, Offenlegung, Bewertungsautorität
und Entwicklungswirkung dürfen daraus jedoch nicht implizit abgeleitet werden.

Mindestens folgende Rollen müssen vor diesem Ausbau getrennt definiert werden:

```text
pack_owner
pack_opener
invited_evaluator
viewer_or_community
card_owner
development_recipient
```

Der bestehende öffentliche Streamvertrag bleibt bis dahin unverändert:
Community-Reaktionen entwickeln keine Karte und ersetzen keine
Besitzerentscheidung. Ob und unter welchen Bedingungen eine ausdrücklich
eingeladene gemeinsame Freundesbewertung dagegen autoritative Crafting-
Evidence oder einen Entwicklungsschritt liefern darf, ist ein späterer
Produkt-, Consent- und Receipt-Vertrag.

Ebenfalls noch nicht festgelegt sind Packzusammensetzung und Seltenheiten,
Anteil von Heroes und Monsters, Erwerbswirkung aller vier Slots,
Duplikatbehandlung, Monsterentwicklung, alternative Kartenkunst,
Freundesberechtigungen, Disclosure-UI und die genaue Beziehung zwischen
Packresultat und nachgelagertem Vierer-Bildspiel. Diese offenen Mechaniken
ändern nicht die gesetzte Core-Idea: öffentliche Monsters und persönliche oder
öffentliche Heroes teilen dasselbe Spiel, und gemischte Pack Openings bilden
ihre zentrale soziale Inszenierung.

Persönliche Karten eines Remote-NPCs dürfen grundsätzlich keine Figuren aus
dem bekannten sozialen Umfeld des Protagonisten verwenden. Eine Überschneidung
ist nur mit einer tatsächlich materialisierten Social-Graph-Verbindung
zulässig. Kennen zwei Accounts dieselbe Person, dürfen sie unterschiedliche
CardIdentities aus getrennten Quellposts und persönlichen Ereignissen besitzen.
Die jeweilige Kartenfassung zeigt die Sicht ihres Besitzers. Ein begrenzter
`CardDisclosureContext` bestimmt, wie viel Name, Beziehung, Ort, Anlass und
emotionale Einordnung aus dem privaten Ereignis in Bild, Titel, Flavor und
Effekterklärung preisgegeben werden darf; vollständige Memory- oder
Relationship-Wahrheit erreicht die Karten-LLM nicht.

### Stream-Pack-Openings, Human-in-the-loop und Gegner-Vorproduktion

Keine generierte Bildbindung eines Spielers, Story-Characters, Remote-NPCs oder
öffentlichen Events wird ohne Human-in-the-loop als spielbar bestätigt. Die
Prüfung fremder persönlicher Karten erscheint im normalen Spielerflow jedoch
nicht als Moderationsauftrag oder technische Review-Queue. Sie wird als echter
Network-Content materialisiert: Der Protagonist schaut live oder zeitversetzt
ein Pack Opening eines gefolgten Streamers, einen Gastauftritt beziehungsweise
eine Kollaboration oder ein gezielt mit ihm geteiltes Opening und reagiert auf
die vier sichtbaren Kartenkandidaten.

Diese eine ehrliche Spielerhandlung erzeugt getrennte Receipts:

- Das `CardContentApprovalReceipt` bestätigt die technische und inhaltliche
  Verwendbarkeit der tatsächlich betrachteten Kandidaten. Ein Melden oder eine
  erkennbare Unbrauchbarkeit bleibt eine eigene Aktion und wird nicht als
  Geschmacksurteil maskiert.
- Das `CommunityPackReactionReceipt` hält die sichtbare Reaktion des
  Protagonisten sowie gegebenenfalls seine bevorzugte Darstellung fest. Sie ist
  Community-Feedback, keine Keep-/Favorite-/Reject-Entscheidung für den Besitzer
  und keine PlayerPreferenceEvidence des persönlichen Visual Circuits.
- Erst danach trifft ein reproduzierbarer `NpcDraftReceipt` anhand des
  eingefrorenen NPC-Geschmacksprofils die persönliche Keep-, Favorite- oder
  Reject-Entscheidung des Kartenbesitzers. Sie darf ausdrücklich von der
  Reaktion des Protagonisten und vom simulierten Community-Ergebnis abweichen.

Weil der Protagonist den Stream tatsächlich gesehen hat, entsteht begrenztes
Wissen: Er kennt die öffentlich oder gezielt geteilte Kartenfassung und genau
die dabei offengelegten Angaben. Daraus folgt weder vollständiges Wissen über
den privaten Quellmoment noch eine objektive Relationship- oder Ereigniswahrheit.
Der `CardDisclosureContext` begrenzt deshalb bereits vor dem Stream Bild, Name,
Ort, Anlass, Chat- und Karten-Copy. Eine persönliche NPC-Karte, deren Opening
weder öffentlich noch für den Protagonisten sichtbar geteilt wurde, gelangt
nicht in den ihm sichtbaren Gegnerpool. Nicht streamende Accounts verwenden
solange Standardkarten und öffentliche Editionen oder qualifizieren persönliche
Karten über einen Gast- beziehungsweise Kollaborationsauftritt.

Für eine vollständig abgeschlossene Community-Teilnahme entsteht ein
persistiertes `EventTicketRewardReceipt`. Event-Tickets führen zu öffentlichen
Events und deren ausdrücklich freigegebenen Eventboostern; sie übertragen keine
persönliche Karte des Streamers, erhöhen keine Kartenwerte und ersetzen weder
BattlerRating noch Relationship. Ticketmenge, Einlösungskosten, Eventkatalog und
Schutz vor reinem Abarbeiten bleiben eine versionierte Reward-Kalibrierung.

Die Gegnerproduktion beginnt parallel zum frühen Network-/Prologlauf. Jeder
Gegner besitzt sofort ein regelgültiges bildloses 40er-Standarddeck; im
Hintergrund werden öffentliche Editionen und persönliche Stream-Booster je
vorgesehenem Gegner vorbereitet. Bildbindungen werden erst nach sichtbarem
Opening, Human-Freigabe und NPC-Draft in künftige Deckrevisionen aufgenommen.
Random-Matches dürfen zunächst bildlose gegen bildlose oder nur teilweise
gebrandete Decks führen. Matchmaking öffnet ringweise, sobald ein erster kleiner
Gegnerpool seine deklarierte Deck- und Content-Readiness erfüllt; weitere
Gegner, Streamtermine und Bildbindungen folgen asynchron. Exakte Poolgrößen,
Mindestzahlen persönlicher Karten, Prewarm-Reihenfolge, Streamfrequenz und
Event-Ticket-Kalibrierung bleiben vor dem zugehörigen Vertical Slice festzulegen.

Sein erster verbindlicher Spielkern verwendet pro Spieler zwei universelle
Front- und drei universelle Back-Slots, offene und verdeckte Karten sowie drei
Angriffslinien. Die genaue Geometrie, Guard-Reihenfolge und Reveal-Auflösung
stehen in
[`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md).
Alle regulären Spielkarten verwenden denselben Figurenkartengrundkörper mit
Angriffs- und Verteidigungswert. Offen/verdeckte Lage sowie Angriffs-/
Verteidigungsmodus sind unabhängige Zustände. Das Branding durch Figur,
Situation, Bildbeschreibung und Entwicklungsstand ergänzt fallen-,
verteidigungs-, support- oder zauberartige Fähigkeitsmodule. Kosten, Phasen,
Kampfzahlen, Effektbudgets, Kartenzonen, Status und der initiale
Fähigkeitskatalog sind inzwischen in den spezialisierten Battler-Verträgen
verbindlich. Das aktive Deck umfasst exakt 40 einzigartige CardIdentities;
Sammlung und mehrere
gespeicherte Decklisten dürfen darüber hinausgehen. Ziehphase und die beiden
Hauptphasen mit jeweils zwei normalen Ausspielhandlungen stehen in
[`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md).

Einmalige Reveal-Effekte, gebundene Wirkungen auf andere Figuren,
spielergerichtete Effekte, Fallen, Support/Auren und aktivierte zauberartige
Fähigkeiten folgen der gemeinsamen
[`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md).
Friedhof, Active-player-Pflichttrigger, Targets, Status und Opcodekatalog stehen
in
[`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md).
Der Server bestimmt die vollständige regelgültige Fähigkeit; die lokale LLM
darf anhand der Bildbeschreibung ausschließlich erklären, wie dieser Effekt
durch die sichtbare Figur, Situation und Bildhandlung ausgedrückt wird.

Jede Keep-Karte besitzt bereits vollständige randomisierte Grundwerte und ein
bildbezogenes Branding. Favorite, Booster-/Cup-Erfolg und
Kombinationschampion verbessern dieselbe CardIdentity über getrennte,
reproduzierbare Entwicklungsschritte. Sobald eine exakte
CharacterChampionSignature ihren Champion besitzt, bleiben reine Keeps dieser
Signatur Challenger, sind aber keine zusätzlichen aktiven Battler-Karten. Ein
Titel in einer anderen 1er-, 2er- oder 3er-Granularität besetzt diesen Slot
nicht. Card-Battler-Siege und -Niederlagen verändern Disposition,
Favorite-Verlustserien und Championzustände nicht. Regelgültige Verwendung
schreibt jedoch post-match Kampferfahrung und kann die getrennte irreversible
Battle Evolution derselben CardIdentity vorbereiten.

Ein verifiziert volljähriger Nutzer kann zusätzlich zur allgemeinen
Battler-Teilnahme die personenbezogene Kartenfunktion aktivieren und damit die
grundlegende Einwilligung erteilen, dass aus packfähigen Posts berechtigter
volljähriger Personen im aktiven sozialen Netzwerk Bilder generiert, daraus
persönliche Karten gebildet und diese im Battler verwendet werden dürfen. Die
konkrete Karte gehört dem reagierenden Spieler. Bei Posts
mit mehreren dargestellten Personen, eingeschränkter Sichtbarkeit, einem
Widerruf oder einem Plattformausstieg sind zusätzliche Zustimmungs- und
Availability-Regeln erforderlich. Rechtliche Erlaubnis und emotionale
Zustimmung einer Figur bleiben ausdrücklich verschiedene Dinge.

Als gesellschaftlicher Grundvertrag gilt zusätzlich:

- Battler-Zugang und Einwilligung in personenbezogene Karten sind zwei
  getrennte Zustände; die zweite Option existiert erst ab verifiziertem Alter
  18,
- persönliche Karten sind accountgebunden und nicht handelbar oder frei
  übertragbar,
- der Kartenbesitzer besitzt die konkrete Spielkarte, aber keine
  uneingeschränkten Bild- oder Persönlichkeitsrechte an der dargestellten Figur,
- private Sammlung und privates Spiel fallen unter die grundlegende
  Battler-Einwilligung,
- öffentliche Übertragung, große Turnierprojektion oder kommerzielle Nutzung
  kann eine weitergehende Freigabe aller erkennbar dargestellten Personen
  verlangen,
- Kontaktabbruch löscht eine gemeinsame Vergangenheit nicht automatisch, kann
  aber Sichtbarkeit, neue Generierung und aktive Kartennutzung einschränken,
- ein wirksamer Widerruf kann das ImageBranding deaktivieren, ohne die
  historische Match- und Kartenherkunft zu leugnen; der regeltechnische
  Kartenkörper darf bildlos fortbestehen,
- und die sichtbare Verwendung einer persönlichen Karte wird kulturell ähnlich
  sensibel behandelt wie das erneute öffentliche Teilen eines gemeinsamen
  Fotos oder Erlebnisses.

Erwachsener Content gehört vollständig außerhalb des regulären Battle-Pfads.
Er darf in einem getrennten, ausdrücklich freigeschalteten Network-Bereich als
eigener Post- oder Booster-Rahmen inszeniert werden und Bildspiele sowie
gescopte Bild-Evidence nutzen. Er erzeugt jedoch keine CardIdentity, keine
Deckkarte und keine Challenger-, Champion- oder Card-Battler-Eligibility. Der
separate VN-/Belohnungspfad besitzt eigene Sichtbarkeits-, Zustimmungs-,
Speicher-, Gestaltungs- und Freigabeverträge.

Der höchste Wettbewerb benötigt eine starke, international verständliche
Motivation. Reines Preisgeld ist nicht die bevorzugte Kernbelohnung. Als
Arbeitsrichtung dient ein übergeordneter Crown-Titel mit professionellem
Creator-Zugang und einem `Spotlight`-Produktionsplatz: Die Plattform realisiert
gemeinsam mit dem Champion und allen zustimmungspflichtigen Beteiligten ein Werk
auf Grundlage des Siegerdecks, beispielsweise einen Kurzfilm, eine Ausstellung,
ein Musikvideo, einen interaktiven Raum oder eine große öffentliche
Inszenierung.

Damit verbindet der Hauptpreis Status, kreative Verwirklichung, Zugang,
öffentliche Sichtbarkeit und die Chance, einen persönlich bedeutsamen Moment zu
prägen. Unterschiedliche Figuren können ihn aus unterschiedlichen Gründen
anstreben. Ob daraus eine berufliche Perspektive entstehen kann oder soll, ist
noch nicht entschieden. Wettbewerbsstufen, Titelname, genauer Preis,
Austragungsrhythmus, Monetarisierung und Folgen für VN-Chancen bleiben offen.

## Vorläufiges Wording

Bis zur gemeinsamen Benennungsrunde können folgende Begriffe als konsistente
Arbeitsrichtung dienen:

| Gegenstand | Spielerischer Arbeitsbegriff | Nicht in der primären Copy |
|---|---|---|
| storyseitiger Ursprung | Post, Beitrag, Moment | Prompt, Datensatz, Input Record |
| soziale Antwort auf einen Post | 👍, 👎, 🙂, 😢 oder 😐 | Bildrating, Reviewentscheidung, Promptsteuerung |
| gebundener Inhalt des Packs | Kartenmotiv, Moment, Kontext | Generation Focus, Expected Composition |
| einzelnes Pack aus vier Karten | Booster | Batch, Attempt, Generation Job |
| längerer Weg desselben Kartenmotivs | Boosterfolge (Arbeitsbegriff) | Campaign, Candidate Pipeline |
| neue generierte Vierergruppe | vier Kartenbilder eines Boosters | Output Batch, Generation Job |
| einzelnes noch ungeprüftes Bild | Kartenkandidat | Output, Sample, Ingest Item |
| spielerische Beurteilung | Trial, Bildrunde, Karten prüfen | Review Pipeline, Evidence Collection |
| Karte mit gebundenem Keep-/Favorite-Bild | Bildkarte | Image Row, Asset Candidate |
| technischer Lerngewinn | visuelle Entwicklung, verlässlichere Darstellung | Confidence Update, LoRA-Readiness, Credit |
| späterer schneller Wettbewerb | Duell, Match, Cup, Titelkampf | Pairwise Evaluation, PvE-Job |

Mögliche Übergangstexte sind beispielsweise:

- „Aus diesem Post ist ein neues Kartenmotiv entstanden.“
- „Ein neuer Booster für Aiko ist bereit.“
- „Dieser Booster enthält vier Darstellungen desselben Moments.“
- „Prüfe, welche Darstellungen Aiko und den Moment wirklich treffen.“
- „Vier Karten wurden deiner Sammlung hinzugefügt.“
- „Reject – das Bild wird nicht übernommen. Du erhältst eine Standardkarte.“
- „Favorite – diese Darstellung trifft das Kartenmotiv besonders gut.“
- „Keep – Common. Diese Darstellung ist ein Challenger.“
- „Für diese Kombination gibt es bereits einen Champion. Diese Keep-Karte kann
  ihn herausfordern, aber nicht zusätzlich aktiv gespielt werden.“

Die Beispiele sind noch keine finale Copy. Insbesondere müssen `Boosterfolge`,
die genauen Dispositionserklärungen und die Tonalität der
Plattformstimme im Frontend-Review gemeinsam festgelegt werden.

## Sprachliche und gestalterische Leitplanken

- Der normale Spielerflow spricht über Posts, Momente, Booster, Karten und
  Figuren; technische Bildoptimierung bleibt in Advanced und Diagnose.
- Jede Trial-Stage zeigt eindeutig, aus welchem Post beziehungsweise
  Kartenmotiv die aktuell geprüfte Darstellung stammt.
- Während einer Einzelbildentscheidung bleibt genau diese Karte der sichtbare
  Fokus. Postkontext und Auftrag dürfen helfen, aber das Bild nicht verdrängen.
- Die Bildbewertung darf nicht behaupten, dass der Spieler die Vergangenheit
  einer Figur oder eine objektive Erinnerung auswählt. Bewertet wird eine
  Darstellung in einem gebundenen Kontext.
- Eine Post-Reaction ist sozialer Input und gegebenenfalls Zugang zu einem
  Booster. Sie ist kein Qualitäts-, Ähnlichkeits- oder Attraktivitätsrating des
  später generierten Bildes.
- Nur die sichtbare Post-Reaction und eine sichtbar gewordene, authorierte
  Kartenverwendung dürfen Relationship Outcomes erzeugen. Bildreview,
  technisches Ausbleiben einer Karte, `Reject` und `Delete or Live` dürfen das
  nicht.
- Reject, Keep und Favorite sind visuelle Bewertungen und bestimmen zugleich,
  ob der Kartenkörper bildlos bleibt oder mit welcher Startseltenheit sein
  Bild-Branding beginnt; sie vergeben aber keinen Championtitel. Nur
  Keep/Favorite qualifizieren das Bild zunächst als visuellen Challenger; eine
  Keep-Karte darf gemäß Playground-Kombinations- und Availability-Vertrag nur
  vorläufig aktiv spielbar sein.
- Bildlose Standardkarten besitzen noch keine Traits und keinen Effekttext.
  Bildkarten dürfen ihre bereits materialisierten Traits kontextuell über
  Figur, Situation und Bildhandlung erklären; das LLM erhält dadurch keine
  Regel- oder Canonautorität.
- Der Card Battler darf die VN motivieren und rhythmisieren, aber Beziehungen
  nicht auf Rohwerte oder Siege reduzieren.
- Maschinenbeschreibung, lokalisierte Kartenbeschreibung, Social-Post und
  technischer Prompt bleiben unterscheidbare Inhalte mit eigener Provenienz.
- Erwachsener Content bleibt außerhalb regulärer Battle-Posts und
  Battle-Booster sowie vollständig außerhalb von Spielkarten, Bildkarten,
  Decks, Visual Circuit und Card Battler. Sein eigener freigeschalteter
  Network-Bereich darf eine distinct Post-/Booster-Inszenierung verwenden,
  ohne daraus Kartenstatus abzuleiten.

## Worldbuilding-Arbeitsprogramm

Eine vollständige Weltbeschreibung bedeutet hier nicht, beliebige Politik oder
ferne Länder enzyklopädisch auszuarbeiten. Verbindlich konkretisiert werden alle
Weltschichten, die Alltag, Figurenentscheidungen, VN-Situationen, Plattform oder
Battler berühren können:

| Weltschicht | Bereits gesetzter Kern | Noch zu vertiefen |
|---|---|---|
| Gesellschaft 2032 | bodenständige Near Future; generative Medien sind Alltag | weitere sichtbare Unterschiede zur Gegenwart und bewusste Grenzen des Fortschritts |
| Bildungssystem | reformierte zweijährige Junior-College-Form; Eintritt erst ab 18, beide Jahre sind Spielzeit, anerkannter Associate-Abschluss und möglicher Credit-Transfer | amtliche Bezeichnung, genaue Rechtsform, Credit-Details und Jahrgangsnamen |
| Konkrete Academy | private, generierte Institution mit 600–800 Studierenden, Cohorts, Wahlbereichen, Clubs, gemeinsamer Academy-Kleidung und nicht-internatsgebundenem Wohnmodell | endgültiger Funktionsslot-Katalog, Generatorgrenzen und lokale Regelvarianten |
| Räumliche Spielwelt | begrenzter PlaceGraph statt Open World; klassische VN-Orte plus Character-Wohnbindungen, Battler-Fähigkeiten, Nicht-VN-Aktivitäten und Eventorte | endgültige Slotzahl, Capability-/Activity-Verteilung, zusätzliche/historische Wohnanker und Identität des lokalen Kobe-Battler-Hubs |
| Kobe | realer Haupthandlungsort mit fiktivem Privatcampus | Campuslage, Wohnort, Pendelwege, feste Ortsanker, Jahreszeiten und lokale Risiken |
| Plattformidentität | global etablierter sozialer Kulturraum mit Wachstumsphase 2021–2025 und Quellenreform 2027/28 | Name, Ursprung, Eigentümer, Führung und genauer globaler Dominanzgrad |
| Plattformgrenzen | Social-, Feed-, Kommunikations-, Bildkarten- und Battler-System; keine Universal-App | genaue Schnittstellen zu Schule, Medien, Handel und öffentlichem Raum |
| Identität und Social Graph | reale institutionelle und persönliche Verbindungen begrenzen Kartenherkunft | Verifikation, Freiwilligkeit, Privatheit, Blockieren und Kontaktende |
| Posts und Sichtbarkeit | Alltagsposts und subjektive Posts nach VN-Ereignissen | Zielgruppen, Gruppenposts, packfähige Posts, Frequenz und soziale Etikette |
| Kartenrechte | accountgebunden, nicht frei handelbar; Minderjährige nur mit Standard-/Public-Event-Karten; persönliche Karten verlangen volljährige Beteiligte und Zustimmung | Widerrufsfolgen, weitergehende öffentliche Nutzung und Streitbeilegung |
| Battler-Kultur | generationenprägend, aber freiwillig; eine gemeinsame Ligapyramide für gemischte Decks von Ranked über lokale, Kobe-, Kansai- und nationale bis internationale Ebene; Liga und Cups bleiben getrennt | konkrete Saisonstruktur, Qualifikationsquoten, Teams, Stars, Medien, Zuschauerrituale und Gegenkulturen |
| Öffentliche Infrastruktur | mobile Duelle bis zu öffentlichen Projektionen | Verbreitung von Tischen, Shops, Arenen, Übertragungen und lokalen Kobe-Orten |
| Wirtschaft | persönliche Karten dürfen nicht käuflich zu Pay-to-win werden; Profis können durch Teams, Liga, Preisgeld, Sponsoring, Medien, Creatorerlöse und Auftritte leben | genaue Summen, Verteilung, Abos, Werbung und Plattformanteil |
| Recht und Kontroversen | der Vorreform-Championship-Vorfall von 2027 führt 2028 zu Alters-, Quellen- und Reichweitenstufen | weitere Moderationspraxis, Streitbeilegung und regionale Unterschiede |
| Generationen | junge Kohorte ist mit dem Battler aufgewachsen; Ältere kennen die Vor-Battler-Zeit | Eltern-, Lehrkraft-, Arbeitgeber- und Medienhaltungen |
| Welt außerhalb Japans | internationaler Mainstream | Dominanzgrad, Konkurrenten, Interoperabilität und regionale Spielkulturen |
| Sprache und Rituale | gemeinsame Regelgrammatik und bekannte Championkultur | Alltagsbegriffe, Gesten, Statussymbole, Tabus, Nostalgie und Fankultur |
| Protagonistenstart | volljähriger Neueintritt ins erste Academy-Jahr; kulturell kundig, in Kobe ohne persönlichen lokalen Bildkartenbestand | vorherige Nutzung, Accountgeschichte und glaubwürdige Abgrenzung alter Kontakte |

Die sinnvolle Vertiefungsreihenfolge lautet:

1. Academy-Kategorie und alltägliche Lebensform,
2. Kobe-Geografie, Wohnen und Bewegungsräume,
3. Plattformunternehmen, Kernfunktionen und Social Graph,
4. Zustimmung, Recht, Geschäftsmodell und Moderation,
5. Battler-Ligen, öffentliche Infrastruktur und Championbelohnung,
6. Generationenkonflikte, Subkulturen, Sprache und Rituale,
7. erst danach die endgültigen Eigennamen von Academy, Plattform und Battler.

## Noch offene World-, Story- und Produktfragen

Vor einem verbindlichen VN-/Plattform-/Card-Battler-Schnitt sind insbesondere
zu entscheiden:

1. In welcher authored Form die Spielerfigur die für Aktivitäten vorgesehenen
   Post Opportunities selbst veröffentlicht oder verwirft. Dass der
   Protagonist grundsätzlich als zulässiger Autor auftreten kann, ist gesetzt;
   beteiligte Plattformfiguren verfassen nach einem VN-Ereignis weiterhin ihre
   eigene subjektive Fassung.
2. Welche Posts packfähig sind, wie `BoosterIntent` und Scheduler
   zusammenspielen und wie verhindert wird, dass jeder Feedpost den
   VN-Rhythmus mit einem Pflicht-Booster unterbricht.
3. Wie heißen Plattform und Kartenbereich, wo entstanden sie, wem gehören sie
   und wie wurden frühes Wachstum, Vorreform-Vorfall und Reform in ihrer
   offiziellen Selbstdarstellung gerahmt?
4. Welche weitergehenden Widerrufs- und Streitfolgen nach einer bereits
   rechtmäßig erzeugten persönlichen Karte gelten; die Alters- und
   Mehrpersonenfreigabe vor ihrer Erzeugung ist bereits gesetzt.
5. Welche konkreten VN-Chancen erzeugen Duelle, und welche Storypfade dürfen
   ausdrücklich nicht an Kampfsiege gebunden werden?
6. Wie verhalten sich öffentlicher Post, private Nachricht, maschinelle
   Bildbeschreibung und finale lokalisierte Karten-Copy zueinander?
7. Wie viele einzelne Booster eine Boosterfolge typischerweise umfasst, wie ihr
   Fortschritt gegenüber dem gemeinsamen Challenger-Pool angezeigt wird und
   wann ein weiterer Post ein neues statt desselben Kartenmotiv eröffnet.
8. Wie frühere Kontakte oder Karten außerhalb Kobes in der Welt erklärt
   werden, ohne sie in den aktiven sozialen und spielerischen Runtime-Bestand
   des neuen Saves zu laden.
9. Welche realen Kobe-Orte sind fester World Canon, in welchem Stadtbereich
   darf die generierte Academy liegen und welche Campusmerkmale dürfen durch den
   Prolog variieren?
10. Wie lautet die genaue amtliche Bezeichnung und Rechtsform der bereits als
    zweijährige Erwachsenen-Academy gesetzten Kategorie, wie funktionieren
    Credits und Jahrgangsnamen, und welche finalen Felder,
    Funktionsslots und Validatoren umfasst der `AcademyDesignProposal`?
11. Welche weitergehenden Freigaben für Streams, große Turniere und
    kommerzielle Inszenierungen gelten. Booster, Review, Sammlung und Deckbau
    sind privat; direkte Matches zeigen Karten zunächst nur den Beteiligten.
12. Wie der eigenständige, vom Battle-Pfad getrennte
    Adult-VN-/Belohnungspfad konkret funktioniert.
13. Wie funktionieren lokale, regionale, nationale und internationale
    Wettbewerbsebenen, und was erhält der höchste Champion konkret statt oder
    zusätzlich zu Preisgeld?
14. Wie finanziert sich die Plattform, ohne dass käufliche Karten oder
    Pay-to-win den persönlichen Moment- und Bewertungsloop entwerten?
15. Welche kleinen Effect Budgets, Knowledge Gates, Cooldowns und authored
    Milestones die bereits begrenzten Relationship Outcomes aus Post-Reactions
    und Kartenverwendung konkret kalibrieren.
16. Welche Plattformtätigkeiten überhaupt als Beruf, bezahlte Nebenrolle,
    institutionelle Funktion oder reine Fankultur existieren und ob der
    Wettbewerb berufliche Perspektiven eröffnen soll.
17. Welche Impuls-Minispielgrammatik in welchen VN-Beats eingesetzt wird, wie
    sie Handlungsabsicht, emotionale Färbung und Intensität ausdrückt und wie
    häufig sie auftreten darf, ohne Gespräch und Storyfluss zu zerlegen.
18. Wie viele permanente `PlaceNode`s und Unterräume jeder Save besitzt, welche
    Battler-Fähigkeiten und `PlaceActivityContract`s fest beziehungsweise
    optional verteilt werden, welche zusätzlichen Wohnbindungen erlaubt sind
    und welche konkrete Identität der wiederkehrende lokale
    Kobe-Battler-Hub erhält.
19. Wie viele Event-Tickets eine abgeschlossene Stream-Teilnahme vergibt,
    welche öffentlichen Events und Eventbooster sie kosten und welche
    Frequenz- beziehungsweise Anti-Grind-Grenzen den Network-/VN-Rhythmus
    schützen. Die diegetische Stream-Pack-Opening-Form, ihre Trennung vom
    NPC-Draft und das begrenzte Wissen des Protagonisten sind bereits gesetzt.
20. Welche anfängliche Zahl an Remote-NPCs, öffentlichen Editionen und
    persönlichen NPC-Karten den ersten Matchmaking-Ring freigibt und wie
    Prewarm, Nachproduktion und Backpressure über den frühen Run verteilt sind.
21. Welche festen oder besitzerspezifischen Rarity-, Entwicklungs- und
    Verteilungsregeln für PublicCardEditions gelten, ohne persönliche
    Momentkarten oder den Visual Circuit zu entwerten.
22. Ob `Monsters & Heroes` der finale In-World-Name des Battlers, der Name einer
    Variante oder lediglich der Arbeitsbegriff bleibt und wie `Hero | Monster`
    spielerseitig lokalisiert wird.
23. Nach welcher Kollationspolicy gemischte Packs persönliche und öffentliche
    Heroes, Monsters und Entwicklungsanlässe verbinden, ob alle vier Slots
    erworben werden und wie Seltenheit, Wiederholung und alternative Kunst
    verteilt sind.
24. Welche explizite Autorität `pack_owner`, `pack_opener`,
    `invited_evaluator`, `viewer_or_community`, `card_owner` und
    `development_recipient` besitzen und welche Consent-, Disclosure- und
    Receipt-Kette eine gemeinsame Freundesbewertung absichert.
25. Wie wiederholte Monstereditionen behandelt werden, ob Monsters überhaupt
    individuell entwickelt werden und wie dabei die bestehende
    No-Duplicate-Deckregel sowie die besondere Entwicklungsfantasie persönlicher
    Heroes erhalten bleiben.

Diese Punkte sind bewusst offen. Sie dürfen bei der aktuellen
Frontend-Korrektur nicht still durch Copy, Layout oder technische Bezeichner als
bereits entschiedene Lore festgeschrieben werden.
