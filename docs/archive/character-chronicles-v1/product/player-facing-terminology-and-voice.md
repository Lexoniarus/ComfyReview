> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/player-facing-terminology-and-voice.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Spielerbegriffe, Textstimmen und sprachliche Zuständigkeiten

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 14. September 2026

Dieses Dokument ist der verbindliche Vertrag für alle spielerseitigen Texte.
Technische Typ-, API- und Tabellennamen dürfen aus Kompatibilitätsgründen
abweichen. Sie dürfen jedoch nicht ungefiltert als Überschrift, Erklärung,
Status oder Handlungsaufforderung im normalen Frontend erscheinen.

## Das mentale Modell

Die Visual Novel mit ihren Beziehungen, Figurenentwicklungen, Szenen und
Endings ist das langfristige Motivations- und Belohnungssystem des Spiels.
Trials, Booster, Kartenentwicklung und Card-Battler-Matches geben auf dem Weg
dorthin kürzere Ziele, unmittelbares Feedback und Abwechslung. Spielertexte
dürfen deshalb nie den Eindruck erwecken, die VN sei bloß Lore für Bildspiele
oder der Card Battler der eigentliche Endzweck des Runs.

Der grundlegende Spielfluss lautet:

```text
Storyschritt
  → visuelle Voraussetzung
  → verpflichtende Entwicklungsaufgabe
  → Trial mit einer konkreten Bewertungsfrage
  → Bildrunde und Bewertung
  → visuelle Voraussetzung erfüllt
  → neue oder reichere VN-Szene als langfristige Belohnung
  → Story und Beziehungen können fortgesetzt werden
```

Die visuelle Entwicklung ist bewusst vor den Storyfortschritt geschaltet. Sie
ist keine freiwillige Nebenaktivität und keine Story-Quest. Der Trial ist der
spielbare Bewertungsschritt innerhalb einer Entwicklungsaufgabe.

## Drei getrennte Verträge

Jede visuelle Entwicklungsaufgabe besitzt drei gleichzeitig gültige, aber
sprachlich und fachlich getrennte Ebenen:

| Ebene | Verantwortung | Typische Inhalte |
|---|---|---|
| **Spielerprojektion** | Erklärt, welches Bild gerade beurteilt wird, was der sichtbare Auftrag ist und welche Handlung als Nächstes möglich ist. | Figur, Szene, Outfit, Tätigkeit, Bildbeschreibung, Bewertungsfrage, Keep/Favorite/Reject, Bildkarte, Challenger, Titel |
| **Spiel- und Wettbewerbslogik** | Bindet Session, Spielvariante, Fortschritt, Kartenkarriere und Turnierkontext deterministisch. | QuestContract, GameMode, ChampionSlot, Eligibility, Cup, Title Match, Story-/Playgate-Bindung |
| **Generierungs- und Evidenzbackend** | Plant kontrollierte Versuche und speichert die vollständige, rebuildbare Lerngrundlage. | GenerationFocus, Expected Composition, Locked/Varied Axes, Prompt-/Recipe-/Modell-/Seed-Provenienz, Reasons, Evidence Scope, Confidence, Unsicherheit, Bias- und Quellenmerkmale |

Die Spielerprojektion ist keine verkürzte Datenbankansicht. Sie übersetzt den
serverseitig gebundenen Auftrag in eine sichtbare Spielsituation. Sie darf weder
Evidence Scope noch Credit, Vergleichbarkeit, Championstatus, Stabilität oder
Assetfreigabe selbst bestimmen. Umgekehrt darf das Backend aus einer
spielerfreundlichen Überschrift oder freien Beschreibung keinen technischen
Vertrag erraten. Beide Seiten referenzieren dieselbe versionierte Aufgabe und
dasselbe unveränderliche Bild.

Der normale Trial zeigt nur die Informationen, die der Spieler für die aktuelle
Entscheidung benötigt. Vollständige technische Details bleiben erhalten und
sind in Advanced beziehungsweise Diagnose einsehbar. Das Verbergen aus der
Hauptinteraktion bedeutet niemals, dass eine Information nicht erhoben oder
nicht persistiert wird.

## Verbindliche Begriffe

| Spielebene | Verbindliche Spielerbegriffe | Nicht als Synonym verwenden |
|---|---|---|
| Visual Novel | Story, Kapitel, Szene, Story-Quest, Gespräch, Tätigkeit, Entscheidung | Bildaufgabe, Trial |
| Chronicle | nächster Storyschritt, visuelle Voraussetzung, Entwicklungsaufgabe, Entwicklungsetappe, Story fortsetzen | Story-Quest für Bildbewertung, Kapitel für visuelle Stufen |
| Bildbewertung | Trial, Bildrunde, Bildziel, Bewertungsfrage, Referenzbild | Mission, Attempt, Review-Vertrag, Quest |
| Trial-Zugang | erforderlicher Trial, freier Trial, Trial fortsetzen | Arcade, Rating-Seite, Render-Lab-Seite oder Route als vermeintlicher Game Mode |
| Persistenter visueller Fortschritt | visuelle Grundlage, bestätigte Bilder, Darstellung, Wiedererkennbarkeit, Vielfalt | LoRA-Readiness, Campaign-Credit, Evidence |
| Visueller Wettbewerb | Bildkartensammlung, Bildkarte, Challenger, Champion, Titelverteidigung, Signature Champion | Context Hash, ChampionRevision, Contender Eligibility |
| Klasse und gemeinsame Entwicklung | Klasse, bekannte Figuren, gemeinsame Karte, gemeinsamer Moment, Academy-Verlauf | Participant Set, Portfolio Owner, RelationshipVisualContextRevision |
| Historische Bilder ohne Storyursprung | Archiv, Archivbild, Archiv-Trial, Archivbewertung | Memory, Ursprungsmemory |
| Persönlicher Kartenursprung | Memory, Ursprungsmemory, Erinnerungskarte | bloßes Archivbild, objektive Wahrheit |
| Laufender Spieldurchgang | Run | Campaign im normalen Frontend |
| Technische Vertiefung | Advanced, Trainingsdetails, technische Vorbereitung, Diagnose | technische Einzelheiten im primären Spielfluss |

`Character Chronicle: Memory Trials` bleibt der Produkttitel. Das Wort
`Memory` bezeichnet keinen allgemeinen Bildspeicher. Es darf für echte
Figuren-Erinnerungen und für den unveränderlichen Ursprung einer persönlichen
Bildkarte verwendet werden: Quellpost, erlebter Moment und die damals
angenommene Darstellung. Andere historische Bilder heißen im Frontend
`Archivbilder`. Ein Ursprungsmemory ist subjektiv und nie die Behauptung einer
objektiv vollständigen Aufzeichnung.

### Trial, Spielvariante und Evidenzfrage

Diese drei Begriffe dürfen weder in Dokumentation noch UI vermischt werden:

- `Trials` bezeichnet den gemeinsamen Bereich und die gemeinsame Runtime.
- Die **Spielvariante** beschreibt ausschließlich, was der Spieler sieht und
  tut, beispielsweise Einzelentscheidung, Setentscheidung, Paarvergleich oder
  Turnierfortschritt. Die endgültige spielerseitige Modusliste wird im
  Frontend-/Spielbarkeits-Schnitt nach AIAM gemeinsam festgelegt.
- Die **Bewertungsfrage** beziehungsweise der Focus beschreibt, welche
  Information gewonnen werden soll. Mehrere Spielvarianten dürfen dieselbe
  Evidenzart erzeugen; dieselbe Spielvariante darf verschiedene Foki tragen.
- `erforderlich`, `empfohlen` und `frei` beschreiben nur die Quest- und
  Creditbindung. Sie erzeugen keinen neuen Modus.

Arcade-/Rating-Seiten, `Rankings` und `Render Lab` sind keine erlaubten
Sammelbegriffe für aktuelle Game Modes. Noch vorhandene gleichnamige Routen,
API-Namen oder technische Projektionen sind Legacy-/Kompatibilitätsbestand und
dürfen nicht als aktuelle Produktstruktur in Spielertexte zurückkehren.
Interne deterministische Ratingprojektionen bleiben davon unberührt; verboten
ist ihre Darstellung als eigener Spielbereich.

## Entwicklungsetappen und Storykapitel

Die sechs visuellen Stufen heißen `Entwicklungsetappen`. Sie sind von den
Storykapiteln der VN unabhängig. Die aktuellen spielerseitigen Namen sind:

1. Wiedererkennbarkeit
2. Umgebungen
3. Outfits
4. Ausdruck und Bewegung
5. Licht und Belastung
6. Visuelle Grundlage

Eine Entwicklungsetappe kann eine Storyfreigabe vorbereiten, ist aber selbst
kein Storykapitel. Texte müssen diese Grenze auch dann wahren, wenn interne
Datenmodelle weiterhin `stage`, `chapter_gate`, `campaign` oder `quest`
verwenden.

## Bewertungen

Die kurzen Aktionsnamen bleiben stabil, erhalten aber überall dieselbe
sichtbare oder zugängliche Bedeutung:

| Aktion | Bedeutung |
|---|---|
| Favorite | Ziel voll getroffen |
| Keep | brauchbar |
| Reject | nicht brauchbar; keine automatische Löschung |
| Skip | nicht beurteilbar |

Eine nachgelagerte Entscheidung wie `Delete or Live` ist eine eigene,
ausdrückliche Löschentscheidung. `Reject` darf nie so formuliert werden, als
würde es eine Datei unmittelbar löschen.

`Favorite`, `Batch-Auswahl` und `Champion` sind keine Synonyme. Ein Favorite ist
eine starke Einzelbildbewertung. Eine optionale Batch-Auswahl hebt ein Bild nur
innerhalb dieser Runde hervor. Ein Champion hat einen konkreten, sichtbaren
Titel in genau einer Bildkarte gewonnen. Dasselbe Bild darf mehrere Titel
besitzen und wird dann als ein Bild mit mehreren Erfolgen dargestellt, nicht als
mehrere vermeintlich unterschiedliche Dateien.

### Bildkarte, Champion-Kontext und Deck

Eine `Spielkarte` ist die persistente CardIdentity für den Card Battler. Sie
kann nach einem Reject bildlos bleiben. Eine `Bildkarte` ist dagegen die
spielerische Projektion einer Spielkarte, an die durch `Keep` oder `Favorite`
genau ein persistentes Bild gebunden wurde. Reject erzeugt eine Spielkarte,
aber keine Bildkarte. Die Karte ist nicht erst dann eine Bildkarte, wenn sie
einen Cup gewinnt. `Favorite` ist eine stärkere Bewertung als `Keep`, aber
weder eine eigene Datei noch automatisch ein Championtitel.

Die Bildkarte führt zusammen:

- das unveränderte Ursprungsmemory und seine stabile CardIdentity,
- die aktuelle aktive Kartenform sowie ihre historische Kartenlaufbahn,
- eine verständliche, kontextgebundene Kartenbeschreibung,
- die aktuelle Keep-/Favorite-Bewertung,
- Challenger-Eignungen und gewonnene Championtitel,
- sowie getrennte Stabilitäts- und Verwendungsinformationen.

`Kartenursprung` oder `Ursprungsmemory` bezeichnet die unveränderte erste
Bildbindung. `Aktuelle Kartenform` bezeichnet die einzig aktiv spielbare
höchste EvolutionRevision. `Kartenlaufbahn` bezeichnet die Folge angenommener
Formen und ihrer Kampferfahrung. Eine frühere Form darf als `bewahrt`,
`zurückgezogen` oder `historisch` bezeichnet werden, aber nicht als frei
umschaltbarer Skin. `Entwickeln` bedeutet daher sichtbar: Die Erinnerung bleibt
erhalten, doch ihre aktive Spielform wird unwiderruflich weitergeschrieben.

Ein interner `ChampionSlot` ist dagegen der versionierte Vergleichs- und
Titelkontext, in dem Bilder kompatibel sein und gegeneinander antreten können.
Er ist **keine Bildkarte**. Im Frontend darf er als Auftrag, Arena oder offener
Titel erscheinen, aber nicht als vermeintlich leere Karte, die später ein Bild
„besitzt“.

Jeder Kombinationschampion ist immer charactergebunden. Seine sichtbare
Titelsignatur besitzt genau eine der folgenden Formen:

- `Character + 1 Aspekt`,
- `Character + 2 Aspekte`,
- `Character + 3 Aspekte`.

`Shopping Mall + Sonntagsoutfit` ohne Character ist daher kein zulässiger
Kombinationstitel. Dasselbe Bild darf in mehreren kompatiblen 1er-, 2er- und
3er-Kontexten Titel gewinnen. Es bleibt eine Bildkarte; jeder erstmalige
Titelgewinn ist ein Level Up derselben Spielkarte.

Die Character-Ansicht zeigt zunächst den vollständigen Bildkartenbestand aus
Keep-, Favorite- und Championkarten. Das VN-/Card-Battler-Deck ist keine zweite
unabhängige Sammlung, sondern die aktuell spielbare Teilmenge dieses Bestands.
Ein Keep erzeugt eine vollständige, aber vorläufige Basiskarte. Solange seine
exakt gebundene CharacterChampionSignature keinen Champion besitzt, darf er
aktiv gespielt werden. Sobald dieser konkrete ChampionSlot besetzt ist, bleiben
reine Keeps derselben Signatur sichtbar und challengerfähig, sind aber nicht
mehr zusätzlich aktive Spielkarten. Ein Titel in einer anderen Granularität
besetzt diesen Platz nicht. Favorite und Champion verbessern dieselbe
CardIdentity über getrennte, randomisierte Level Ups innerhalb eines
serverseitigen Budgets.

Alle Karten erscheinen als Figurenkarten mit Angriffs- und Verteidigungswert.
`Falle`, `Support`, `Zauber` und besondere `Verteidigung` beschreiben
Fähigkeitsrichtungen des Brandings und keine getrennten Kartenarten oder
Feldzonen. Eine Karte darf unabhängig voneinander offen oder verdeckt sowie im
Angriffs- oder Verteidigungsmodus liegen.

Ein aktives Matchdeck enthält exakt 40 Karten; die größere Sammlung darf
mehrere gespeicherte Decklisten speisen. v0.1 besitzt keine allgemeine Mana-
oder Energieressource, keine Kartenkopien innerhalb eines Decks und kein Side-
oder Reserve-Deck. `Character-Deck` darf nicht unkommentiert Gesamtbestand, aktuell
spielbare Karten und aktive Auswahl zugleich bezeichnen. Ein neuer Save beginnt
mit einem schwachen bildlosen
Standard-Base-Deck, aber ohne persönliche Bildkarten. Jeder vollständig
bewertete Vierer-Booster ergänzt genau vier Spielkarten: Reject lässt den
Kartenkörper bildlos auf Standard, Keep brandet ihn mindestens als Common
Level 1 und Favorite mindestens als Rare Level 1. Booster-/Cup- und
Championerfolge sowie bestätigte Kampferfahrung entwickeln gebrandete Karten
über Uncommon, Super und Ultra bis Legendary. Keine dieser Achsen kann allein
das Legendary-Gate erfüllen. Bildlose Standardkarten besitzen keinen Trait und keinen
Effekttext; bei Bildkarten darf die LLM ausschließlich die bereits
materialisierten Traits über
Figur, Situation und Bildhandlung kontextuell erklären. Der erste Battler
bleibt an eine serverseitige Deck-Readiness gebunden, darf aber bereits mit dem
regelgültigen Base Deck öffnen.

`Online-Match` bezeichnet ausschließlich ein innerhalb der fiktionalen
Plattform vermitteltes Singleplayer-Duell gegen einen simulierten Nutzeraccount.
Spielertexte dürfen weder einen realen menschlichen Gegner noch echtes
Multiplayer-Matchmaking behaupten. `PvP` bleibt deshalb außerhalb technischer
Diagnose ungeeignet; intern ist der Modus PvE. Ein `Rivale` ist ausschließlich
eine dafür plausibilisierte Figur des festen 16er-Story-Casts. Zufällige
Online-Gegner bleiben Plattform-NPCs und werden nicht zu zusätzlichen Rivalen.

Eine öffentliche Bildkarte zeigt weiterhin genau eine konkrete Figur, etwa
eine bekannte öffentliche Person, einen Battler, ein Tier, Maskottchen oder
Event-Creature. Viele Accounts dürfen eigene CardIdentities derselben
öffentlichen Edition besitzen. Eine persönliche Bildkarte bleibt dagegen an
den zulässigen sozialen Quellkontext ihres Besitzers gebunden.

`Hero` und `Monster` sind vorgesehene, aber noch nicht final lokalisierte
Subjektbegriffe innerhalb desselben Figurenkarten-Rulesets. Ein Hero zeigt eine
konkrete Person oder charakterhafte Figur; ein Monster eine konkrete benannte
Kreatur, ein Tier, Maskottchen oder anderes world-authored Creature. Die
Begriffe beschreiben keine getrennten Feldzonen oder mechanischen Kartentypen.
`Monsters & Heroes` ist vorerst nur der Arbeitstitel für den In-World-Battler
oder eine Battler-Variante und darf noch nicht als finaler Markenname in
produktiver Copy behauptet werden.

Ein `Pack Opening` bezeichnet zunächst das gemeinsame Enthüllen eines Packs.
Eine eventuell folgende `Bildbewertung`, ein `Card Crafting` oder ein
`Evolution Trial` ist eine getrennte Phase und darf sprachlich nicht mit dem
Opening gleichgesetzt werden. Im späteren Zielsystem können gemischte Packs
Heroes und Monsters enthalten und mit beziehungsweise für Freunde geöffnet
werden. Solange Rollen- und Receipt-Vertrag noch fehlen, darf die UI daraus
weder Bewertungsautorität noch Eigentums- oder Entwicklungswirkung versprechen.

Die Human-in-the-loop-Freigabe einer fremden persönlichen Karte erscheint im
normalen Spielertext als live oder zeitversetzt angesehenes Pack Opening eines
gefolgten Streamers, als Gast-/Kollaborationsstream oder als gezielt geteiltes
Opening. Der Protagonist `reagiert`, `stimmt ab`, `schaut das Opening` oder
`meldet` einen Kandidaten; er `zertifiziert`, `moderiert` oder `prüft Content`
nicht. Seine Reaktion ist keine Keep-/Favorite-/Reject-Entscheidung des
Besitzers und keine Präferenz seines eigenen Visual Circuits. Sie darf jedoch
begrenztes Wissen über die tatsächlich gezeigte Kartenfassung erzeugen. Der
private Quellmoment und nicht offengelegte Relationship-Kontext bleiben
unbekannt.

`Event-Ticket` bezeichnet die Belohnung für eine vollständig abgeschlossene
Community-Teilnahme an einem qualifizierten Pack Opening. Spielertexte verbinden
Tickets ausschließlich mit öffentlichen Events und Eventboostern. Sie dürfen
weder eine persönliche Streamerkarte noch Kartenstärke, Rarity, BattlerRating
oder Relationship als unmittelbare Gegenleistung versprechen.

`Live` beziehungsweise die spielerseitige Aktion `Als Favorite retten` macht
eine Karte nicht zum Champion. Sie erhält das Bild als Favorite und erlaubt
eine spätere erneute Cup-Qualifikation. Ein Championtitel und sein Level Up
entstehen ausschließlich durch den gebundenen 16er-Cup und, bei vorhandenem
Amtsinhaber, das Title Match.

Adult-Content kann später innerhalb eines eigenen Network-Bereichs ebenfalls
als Booster inszeniert werden. Diese Booster sind keine Battle-Booster: Ihre
Ergebnisse gelangen weder ins Card-Battler-Deck noch in Champion-Cups. Die
Bezeichnung muss deshalb stets durch Bereich und Gestaltung eindeutig machen,
welcher Booster-Typ gemeint ist. Konkrete spielerseitige Eigennamen bleiben
deferred, solange der Adult-Content- und Card-Battler-Überbau noch nicht
Bestandteil der aktuellen Frontend-Umsetzung ist.

`Stabil` beschreibt Wiederholbarkeit und nicht den Wert der Karte. Eine
technische Assetfreigabe beschreibt ausschließlich eine konkrete Verwendung
oder Ableitung. Sie ist kein allgemeiner Kartenrang. Scheitert beispielsweise
die Freistellung eines Favorites oder Champions, bleiben Karte, Bewertung und
Championtitel unverändert; nur dieser Assetversuch beziehungsweise diese
Verwendung ist fehlgeschlagen. `Signature Champion` bezeichnet den
übergeordneten Repräsentationstitel eines Characters und ersetzt keinen
konkreten Slottitel.

Eine `gemeinsame Karte` beziehungsweise ein `gemeinsamer Moment` gehört nicht
verdeckt einer der beteiligten Figuren. Er erscheint bei allen Beteiligten mit
demselben Bild- und Titelzustand. Die Klassenansicht beschreibt Cast,
Academy-Jahresbezug und nächste bekannte Entwicklung; sie bewertet Characters
nicht gegeneinander und verwendet keine Ranglistenstimme.

## Textstimmen nach Oberfläche

### Visual Novel

Die VN spricht diegetisch: Figuren im eigenen Ton, ergänzt durch einen
Erzähler. Systembegriffe der Bildproduktion haben dort keinen Platz. Wenn die
Story wegen visueller Entwicklung wartet, wird der Übergang erzählerisch
motiviert; die konkrete Aufgabe erscheint anschließend in der Chronicle.

### Chronicle und Characters

Diese Flächen verwenden eine direkte, ruhige Meta-Spiel-Stimme. Jeder Text
beantwortet möglichst eine der Fragen:

- Was ist der nächste Storyschritt?
- Welche visuelle Voraussetzung fehlt noch?
- Welche Entwicklungsaufgabe erfüllt sie?
- Was wird nach dem Trial freigeschaltet oder verlässlicher?

### Trials

Ein Trial konzentriert sich auf genau eine Bewertungsfrage. Während der
Bildentscheidung sind interne Ursachen, Scheduler-Entscheidungen und
Pipeline-Status nachrangig. Die Wirkung wird in sichtbaren Begriffen erklärt,
zum Beispiel: „Deine Bewertung entscheidet, welche Darstellung künftig
zuverlässig weiterverwendet wird.“

Die sichtbare Aufgabenbeschreibung benennt vorrangig den Gegenstand, zum
Beispiel Figur, Ort, Outfit, Tätigkeit, Ausdruck und Bildausschnitt. Technische
Versuchsnamen wie `sampler_scheduler`, `prompt_composition`, `ablation` oder
`asset_champion_selection` sind keine normale Spieler-Copy. Die Oberfläche darf
stattdessen erklären, was gleich bleiben soll und worauf der Spieler bei den
Unterschieden achten soll.

### Bildbeschreibung und Image Worker

Eine maschinelle Bildbeschreibung ist ein Vorschlag des Image Workers. Sie kann
in einem eigenen Beschreibungsspiel geprüft werden. Sie ist weder der Prompt
noch eine Bildbewertung und vergibt keinen Keep-, Favorite-, Challenger-,
Champion-, Canon-, Stability- oder Assetstatus. Insbesondere gehört die Frage,
ob eine Beschreibung passt, nicht in den normalen Qualifier-, Ranking-, Arena-
oder Kalibrierungsablauf.

Das Beschreibungsspiel zeigt eine Beschreibung und genau zwei verfügbare
Bildkarten derselben Figur aus dem behaltenen Pool. Der Spieler beantwortet nur:
„Zu welchem Bild passt diese Beschreibung?“ Die Quelle der Beschreibung ist
serverseitig gebunden; das zweite Bild wird innerhalb eines kontrollierten
Schwierigkeitskorridors gewählt. Die Auswahl misst, wie eindeutig die
Beschreibung relativ zu diesem Gegenbild ist. Sie bewertet weder den Spieler
noch die Qualität oder den Lebenszyklus der beiden Karten.

Die technische Rohbeschreibung, die bestätigte beziehungsweise korrigierte
Beschreibung und die lokalisierte Karten-Copy bleiben getrennte Revisionen
beziehungsweise Projektionen. Rohtext darf insbesondere nicht ungeprüft als
englischer Kartentitel in ein deutschsprachiges Frontend gelangen. Eine einzelne
Paarwahl bestätigt den Text noch nicht absolut; erst mehrere revisionsgebundene
Zuordnungen dürfen ihn als eindeutig, nur in leichten Paaren tragfähig,
generisch oder irreführend projizieren. Übersetzung, Textkorrektur und
Karten-Copy bleiben davon getrennte Workflows.

### Workshop, Settings und Advanced

Der Workshop erklärt die Folgen vergangener Bewertungen und kommende
Vergleichsbilder. Settings erklären Regeln des Runs. Exakte Werte,
Prompt-Verträge, Provider, Seeds, Evidence, Confidence, Dataset-Versionen und
LoRA gehören in ausdrücklich bezeichnete `Advanced`- oder Diagnosebereiche.
`LoRA` ist eine technische Umsetzung der visuellen Grundlage, keine frühe
Spielermechanik und kein Synonym für Fortschritt.

## New Game Plus

New Game Plus übernimmt den gesamten visuellen Zustand, insbesondere Bilder,
Bewertungen, gelernte Generierungsinformationen und vorhandene technische
Modelle. Storywissen und Erinnerungen an Gespräche oder Tätigkeiten werden
nicht übernommen. Texte dürfen deshalb visuelle Übernahme nie als Erinnerung
der Figur formulieren.

## Copy-Prüfung für neue Features

Vor der Abnahme eines neuen Frontend-Texts ist zu prüfen:

1. Ist die Spielebene eindeutig: VN, Chronicle, Trial, Archiv oder Advanced?
2. Verwendet der Text ausschließlich die Begriffe dieser Ebene?
3. Nennt er eine sichtbare Wirkung statt einer technischen Ursache?
4. Ist eine Bildbewertung als Trial und nicht als Story-Quest bezeichnet?
5. Ist eine visuelle Stufe als Entwicklungsetappe und nicht als Kapitel bezeichnet?
6. Sind `Campaign`, `Attempt`, `Evidence`, `Credit`, `Seed`, `ComfyUI` und `LoRA` außerhalb von Advanced verborgen?
7. Wird `Memory` nur für echte Figuren-Erinnerungen oder das klar gebundene
   Ursprungsmemory einer persönlichen Karte verwendet, niemals für einen
   allgemeinen Bildspeicher?
8. Bleiben Storywissen und visueller Carry-over im New Game Plus getrennt?
9. Ist eine Bildkarte eindeutig das persistente Bild und nicht ein ChampionSlot?
10. Bleiben Championtitel, Stabilität und konkrete Assetverwendung getrennt?
11. Bleiben technische Rohbeschreibung, bestätigte Bildbeschreibung und
    lokalisierte Karten-Copy unterscheidbar?

Bei einem Konflikt zwischen bestehender Copy und diesem Vertrag hat dieses
Dokument für spielerseitige Texte Vorrang. Interne Bezeichner werden getrennt
migriert und sind kein Grund, die veraltete Sprache im Frontend fortzuführen.
