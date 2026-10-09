# Kartenentstehung, Playground-Kombinationen und temporäre Spielbarkeit

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `MIXED_GAME_DESIGN_AND_LEGACY_ASSUMPTIONS`  
**Worum es geht:** Bildkarten, Crafting, Sammlungen, Booster und Playground-Herkunft – fachliche Ideen mit alten Datenannahmen.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../vision/card-battler.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für Card Crafting, Playground-
Kombinationsbindung und die Spielbarkeit daraus erzeugter Karten; Spielfeld,
Angriffslinien und Sichtbarkeit stehen im getrennten Card-Battler-Vertrag

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen**

Stand: 14. September 2026

## Zweck und Abgrenzung

Dieses Dokument definiert den Übergang vom bewerteten Bild zur persönlichen
Spielkarte. Es legt fest,

- wie die vollständige Playground-Herkunft von charactergebundenen 1er-, 2er-
  und 3er-Championkontexten getrennt wird,
- welche Generierungs- und Promptvarianz innerhalb dieses Kontexts zulässig
  bleibt,
- wann Keep, Favorite und Champion eine Karte erzeugen oder verbessern,
- wie Bildbeschreibung, Zufall, lokales LLM und deterministischer Validator
  zusammenarbeiten,
- wie ein neuer Save mit einem schwachen bildlosen Base Deck beginnt,
- und wann eine Karte durch den bestehenden Eliminations- und
  Delete-or-Live-Lifecycle nur vorläufig beziehungsweise nicht mehr spielbar
  ist.

Das universelle Fünf-Slot-Feld, seine drei Angriffslinien sowie offene und
verdeckte Karten sind bereits in
[`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md)
entschieden. Das exakte 40-Karten-Deck, die Ziehphase und zwei Hauptphasen mit
je zwei normalen Ausspielhandlungen stehen in
[`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md).
Der Battler verwendet keine allgemeine Mana-/Energieressource; Ausspielen folgt
Feldpräsenz und Opfer, Fähigkeiten ihren registrierten Einzelkosten. v0.1
besitzt weder Affinitäten noch Side-/Reserve-Deck. Eine endgültig gelöschte
Bildbindung setzt dieselbe CardIdentity auf ihr ursprüngliches bildloses
Standardprofil zurück. Seltene Timing- und Synergieerweiterungen benötigen eine
spätere Rules-Version. Präsenz-/Opferkurve, eindeutige Kartenidentitäten und der
initiale Effektkatalog sind verbindlich. Card-Battler-Matches sind keine
Bildreviews und erzeugen keine Keep-/Favorite-Verlustserie, keinen
Championwechsel und keine Delete-or-Live-Wirkung.

Der Kartenvertrag endet an der ausgewählten Quellkarte. Ein aus ihr durch
Freistellung, Matting, Normalisierung oder spätere Expression-Verarbeitung neu
erzeugtes `DerivedAssetImage` ist keine Bildkarte, erhält keine `CardIdentity`
und übernimmt weder Branding, Rarity, Level, Traits noch Championstatus. Sein
Asset-Lifecycle und seine VN-Verwendungen bleiben von späterer Kartenpromotion,
Niederlage oder Löschung unabhängig.

Die strukturellen Effektformen, ihre gestufte Zufallsmaterialisierung und die
rein beschreibende LLM-Kontextualisierung
stehen in
[`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md).
Kartenzonen, Statuszustände, Targets und ausführbare Opcodes stehen in
[`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md).
Command-, Matchsnapshot-, Persistenz- und Renderergrenzen stehen in der
[`Card-Battler-Runtime-Architektur`](card-battler-runtime-architecture.md).
Die getrennte manuelle Einpassung eines gebrandeten Bildes in ein
Kartengesicht, ihre Frame-Manifeste und Render-Receipts stehen im
[`Kartenkunst-Kompositionsvertrag`](card-art-composition-and-rendering.md).

## Playground-Herkunft und Character-Champion-Kombination

Die vollständige versionierte Playground-Kombination hält zunächst fest, aus
welchen Komponenten ein Bild erzeugt wurde:

```text
PlaygroundCombinationSignature
├─ character_component_version_id
├─ scene_component_version_id
├─ outfit_component_version_id
├─ weitere gebundene ComponentVersionen[]
└─ binding_rules_version
```

Der bestehende technische Schlüssel besitzt bereits die Form
`components:{character}:{scene}:{outfit}`. Im Zielvertrag referenzieren seine
Teile stabile ComponentVersion-Identitäten und nicht lediglich Anzeigenamen,
freien Prompttext oder eine nachträglich erkannte Bildähnlichkeit. Diese
vollständige Signatur ist Herkunft und Provenienz. Sie ist nicht automatisch
der einzige Championkontext des Bildes.

Jeder Kombinationschampion ist zwingend an genau einen Character und zusätzlich
an eine, zwei oder drei semantische Aspektbindungen gekoppelt:

```text
CharacterChampionSignature
├─ character_component_version_id          # immer erforderlich
├─ aspect_bindings[1..3]                  # kanonisch sortiert, ohne Dublette
│  ├─ component_kind
│  └─ component_version_id oder BindingRevision
└─ champion_combination_policy_revision
```

Damit existieren genau drei Granularitäten:

- **1er-Kombination:** Character plus genau ein Aspekt, beispielsweise Outfit,
  Scene oder Pose.
- **2er-Kombination:** Character plus genau zwei Aspekte, beispielsweise
  Outfit und Scene.
- **3er-Kombination:** Character plus genau drei Aspekte, beispielsweise
  Outfit, Scene und Pose.

Eine reine Aspektkombination ohne Character ist unzulässig. Auch ein
Character ohne mindestens einen zusätzlichen Aspekt bildet in diesem Vertrag
keinen Kombinationschampion. Zulässige Aspektarten stammen aus der
versionierten Slot-/Coverage-Policy; insbesondere Outfit, Scene, Pose/Action,
Expression, Lighting, Framing/View und Presentation-/Modifier-Bindings können
verwendet werden. Der Vertrag materialisiert nur fachlich benötigte
Kombinationen und kein vollständiges kartesisches Produkt.

Ein Bild behält seine vollständige PlaygroundCombinationSignature und kann
zugleich für mehrere kompatible CharacterChampionSignatures qualifiziert
werden. Jede Signatur besitzt einen eigenen ChampionSlot, Challenger-Pool,
16er-Cup und Titel. Gewinnt dasselbe Bild mehrere dieser Titel, bleiben Bild,
ImageBranding und CardIdentity unverändert; jeder erstmalige Titelgewinn ist
ein eigener budgetierter Entwicklungsschritt derselben Karte.

Ändert sich der Character oder einer der in der konkreten
CharacterChampionSignature gebundenen Aspekte semantisch, entsteht ein anderer
Championkontext. Ein bloßer Wechsel von Formulierung, Seed oder technischem
Recipe erzeugt dagegen keinen neuen ChampionSlot.

Die Kombinationszugehörigkeit stammt ausschließlich aus der vor der
Generierung eingefrorenen Component-Bindung. VLM-Beschreibung, Image
Embeddings, Promptstring-Ähnlichkeit und sichtbare Bildähnlichkeit dürfen sie
weder erzeugen noch überschreiben.

## Zulässige Varianz innerhalb derselben Kombination

Innerhalb einer PlaygroundCombinationSignature dürfen insbesondere variieren:

- Seed und daraus folgende Bildkomposition,
- Pose, Ausdruck und kleinere sichtbare Details innerhalb des gebundenen
  Korridors,
- Promptlexikalisierung und äquivalente Formulierungen,
- zulässige Gewichte und kontrollierte Promptrevisionen,
- Sampler, Scheduler, Steps, CFG und andere deklarierte Renderparameter,
- Workflow- und GenerationRecipe-Revisionen,
- sowie Qualität, technische Fehler und sichtbares Ergebnis des einzelnen
  Outputs.

Diese Varianz erzeugt unterschiedliche persistente Images und kann zu
unterschiedlichen gecrafteten Karten führen. Sie ändert aber weder die
Playground-Herkunft noch eine daraus materialisierte, semantisch unveränderte
CharacterChampionSignature.

Verlässt ein Prompt- oder Komponentenversuch den semantischen Character-,
Outfit- oder Scene-Vertrag, ist er nicht bloß eine Variante derselben
Kombination. Er benötigt eine neue ComponentVersion beziehungsweise eine neue
PlaygroundCombinationSignature.

## Bildloses Base Deck und Kartenentwicklung

Ein neuer Save besitzt ein vollständiges Base Deck aus bildlosen,
ungebrandeten Standardkarten. Jede davon ist bereits eine universelle
Figurenkarte mit schwachen Angriffs- und Verteidigungswerten, aber ohne Trait
und ohne ausführbaren Karteneffekt. Damit ist der Card Battler von Beginn an regelgültig
spielbar, ohne die persönliche Bildsammlung zu entwerten. `Standard` steht
außerhalb der bildgebundenen Seltenheitsleiter.

Eine bildlose Standardkarte zeigt nur ihre ATK-/DEF-Werte, ihr gegebenenfalls
benanntes Kampfprofil und den Hinweis, dass sie noch keinen Trait besitzt. Sie
besitzt weder Figuren-, Situations- noch Bild-Lore und behauptet keinen
narrativen Ursprung. Erst ihr erster Entwicklungsschritt erzeugt einen Trait;
das Bild-Branding erlaubt danach dessen kontextuelle Benennung und Erklärung.

Jede aktuell spielbare Kartenrevision besitzt zusätzlich eine Quellenklasse:

```text
CardProvenance = blank_standard | public_event | personal_post
```

`blank_standard` ist für alle zulässigen Battler-Accounts verfügbar.
`public_event` bindet eine von der Plattform offiziell rechte- und
contentfreigegebene `PublicCardEdition`, nicht den privaten Post einer Person,
und nimmt nicht am persönlichen Booster-/Playground-/CharacterChampion-Loop
teil. `personal_post` bindet dagegen den hier beschriebenen persönlichen
Bildkartenpfad und ist nur zulässig, wenn Kartenbesitzer und alle erkennbar
dargestellten Personen zum Quell- und Generierungszeitpunkt verifiziert
volljährig und wirksam eingewilligt sind.

Die `CardIdentity` bleibt bei einem erlaubten Branding dieselbe: Eine freie
`blank_standard`-Revision kann durch einen persönlichen Booster zu einer
`personal_post`-Revision werden. Eine `public_event`-Bindung folgt dagegen nur
der offiziellen Edition und darf nicht als persönlicher Post umgedeutet oder
in dessen Visual Circuit verschoben werden. Historie und jeweilige
Eligibility-Receipts bleiben unveränderlich nachvollziehbar.

Minderjährige dürfen den Card Battler mit `blank_standard`- und
`public_event`-Karten spielen. Für ihre Accounts dürfen weder
`personal_post`-Branding noch Besitz, Deckbindung oder Matchverwendung
materialisiert werden. Spätere Volljährigkeit legalisiert keine persönliche
Karte rückwirkend aus einem Post oder Bild, das während der Minderjährigkeit
entstand. Bei gemischten, unverifizierten oder nicht vollständig
einwilligenden Personengruppen blockiert der ganze persönliche Kartenversuch;
ein automatisches Zuschneiden ist kein zulässiger Ersatz.

Sobald persönliche Bilder qualifiziert werden, beginnt die Entwicklung:

```text
bildlose Standardkarte
→ Common
→ Uncommon
→ Rare
→ Super
→ Ultra
→ Legendary
```

Die bildgebundenen Seltenheiten `Common` bis `Ultra` besitzen jeweils die
Entwicklungsstufen `Level 1`, `Level 2` und `Level 3`. Nach Level 3 folgt bei
einem weiteren gültigen Entwicklungsschritt Level 1 der nächsten Seltenheit.
`Legendary` ist die vorläufige Höchststufe.

Jeder Entwicklungsschritt ist ein Level Up. Neben dem vorgesehenen Wertebudget
führt er genau eine Trait-Aktion aus: den ersten Trait hinzufügen, einen
vorhandenen Trait steigern oder innerhalb des Rarity-Caps einen neuen
harmonischen Trait ergänzen. Die Karte bleibt dabei in einer persistenten
`TraitLineage`.

- Ein `Reject` verwirft das Bild-Branding; der zugehörige Kartenkörper bleibt
  eine schwache bildlose Standardkarte.
- Ein erstmaliges `Keep` brandet den Kartenkörper mindestens als
  `Common Level 1`.
- Ein erstmaliges `Favorite` materialisiert sie mindestens als
  `Rare Level 1`.
- Wird eine bereits entwickelte Common- oder Uncommon-Karte später Favorite,
  steigt sie mindestens auf `Rare Level 1`, verliert aber keinen bereits
  höheren Fortschritt.
- Ein qualifizierter Sieg der Karte in einem bildbezogenen Booster- oder
  Cup-Spiel erzeugt einen Entwicklungsschritt.
- Eine versioniert erreichte Kampferfahrungsschwelle darf ebenfalls einen
  Entwicklungsschritt erzeugen. Der Matchsieg allein ist keine Schwelle;
  entscheidend ist die regelgültige, nicht farmbare Verwendung der konkreten
  Karte.
- Das erstmalige Erreichen des Kombinationschampionstatus erzeugt einen
  zusätzlichen Entwicklungsschritt.
- Weitere regelgültige Booster-/Cup-Erfolge dürfen die Karte durch die
  regulären Stufen weiterentwickeln und liefern den visuellen Teil des
  Legendary-Nachweises. Der letzte Schritt selbst verlangt zusätzlich die
  festgelegte Battle Lineage.
- Eine Niederlage und der spätere Verlust eines Championplatzes nehmen keinen
  bereits verdienten Kartenfortschritt zurück. Der getrennte DOA- und
  Löschvertrag gilt weiterhin.
- Eine entwickelte Karte darf im Deck oder Match nicht auf eine frühere
  Rarity-/Levelrevision zurückgestuft werden. Ihre aktuelle höchste
  Entwicklungsstufe ist ihre verbindliche Spielform.
- Mit der Entwicklung steigen Fähigkeitsbudget und Ausspielvoraussetzungen.
  Super-, Ultra- und Legendary-Karten müssen ihren höheren Aufbauaufwand durch
  entsprechend starke Effekte rechtfertigen.
- Deshalb benötigt ein tragfähiges Deck bewusst eine Entwicklungskurve aus
  leicht ausspielbaren Standard-/niedrigen Karten und wenigen hochentwickelten
  Spitzenkarten. Ein reines Legendary-Deck soll praktisch nicht funktionieren.

### MemoryOrigin und CardBattleEvolution

Das beim ersten Keep oder Favorite gebundene Bild ist die unveränderliche
`MemoryOriginRevision` der persönlichen Karte. Sie bindet Quellpost,
Story-/Momentkontext, ImageIdentity, CardSubjectIdentity, Disclosure Context und
die erste materialisierte Spielform. Ein Favorite darf bei dieser erstmaligen
Materialisierung unmittelbar auf Rare Level 1 starten; die übersprungenen
Zwischenstufen sind keine nachträglich behauptete Kampfhistorie.

Jede spätere angenommene Entwicklung derselben CardIdentity besitzt zwei
getrennte Seiten:

1. Der Server materialisiert aus einem zulässigen Development Event die neue
   mechanische Rules Revision.
2. Ein gesonderter Vierer-`CardEvolutionTrial` bestimmt, wie die bereits
   verdiente Entwicklung im Bildkontext sichtbar wird.

```text
MemoryOriginRevision (immutable)
→ CardBattleExperienceEvent*
→ CardBattleExperienceDigest
→ development_ready
→ vier CardEvolutionImageCandidate
→ Keep/Favorite einer Evolutionsdarstellung
→ CardEvolutionRevision wird aktive Spielform
```

Der Experience Digest darf nur datensparsame, reproduzierbare Spielfakten
enthalten: regelgültiges Ausspielen, tatsächlich aufgelöste Traits,
Verteidigungs- und Angriffsbeiträge, entscheidende Matchereignisse sowie den
klassifizierten Kontext von Training, Ranked, Liga, Cup oder Rivalenmatch. Er
enthält weder freien Matchchat noch verdeckte Gegnerdaten oder vollständige
private Storywahrheit. Wiederholte No-op-Nutzung, sofortige Aufgabe,
abgesprochene Gegnerfolgen und andere Farmmuster werden nicht angerechnet oder
policygebunden gedeckelt.

Die aktive Evolutionsdarstellung darf den Ursprung mit wachsender Entwicklung
zunehmend als spielerische Legende interpretieren: von kleinen visuellen
Motiven über dynamischere Pose, Rahmung und Symbolik bis zur ikonischen
Legendary-Fassung. Sie muss Figur und Herkunft erkennbar halten und ist reine
Kartenmythologie. Sie erzeugt keine neue VN-AssetVersion, keinen
CharacterVisualCanon, keine LoRA-Evidence und keine Behauptung, der
dargestellte Moment habe wirklich so stattgefunden.

Lehnt der Spieler alle vier Evolutionskandidaten ab, bleibt die vorherige
aktive Revision spielbar und der verdiente Schritt `evolution_pending`; ein
späterer Retry darf neue Kandidaten erzeugen. Nimmt er eine Darstellung an,
wird sie zur einzigen aktiven höchsten Revision. Ursprung und Zwischenformen
bleiben historisch sichtbar, sind aber nicht frei wieder auswählbar oder
spielbar. Alternativ kann der Besitzer die bisherige Form bewahren oder aus dem
Wettkampf zurückziehen und damit auf die stärkere Revision verzichten. Ein
exaktes aktives Duplikat derselben Ursprungsdarstellung ist unzulässig;
unterschiedliche Karten desselben Motivs bleiben nur dann erlaubt, wenn sie aus
eigenständigen Bildkandidaten und CardIdentities hervorgegangen sind.

`Legendary` benötigt kumulativ zwei unabhängige Nachweise: eine ausreichend
lange, anti-farm-geprüfte Battle Lineage und die bereits definierte visuelle
Bewährung gegen zahlreiche unabhängige Challenger. Kampferfahrung allein darf
Legendary ebenso wenig erzeugen wie reine Matchwiederholung den Visual Circuit
ersetzen darf. Visual Champion, Legendary-Rarity und aktive Evolutionsform
bleiben getrennte Projektionen.

Das `Branding` bindet genau einen traitlosen Standard-Figurenkörper samt
Kampfprofil an ein als Keep oder Favorite behaltenes Bild, seine dargestellte Figur, Situation,
PlaygroundCombinationSignature, Bildbeschreibung und Rarity-/Levelprojektion.
Es ergänzt keine neue strukturelle Kartenart, sondern bildbezogene
Fähigkeitsmodule. Diese können fallenartig, verteidigungsartig,
supportartig oder zauberartig wirken und dürfen mit höheren Entwicklungsstufen
stärker, vielseitiger oder anspruchsvoller ausspielbar werden.

Jeder Entwicklungsschritt revisioniert dieselbe CardIdentity. Er zieht aus
einem serverseitig begrenzten und reproduzierbaren Entwicklungsbudget eine
zulässige Trait-Aktion und Werteverbesserung. Sobald eine Karte ein Bild besitzt, formuliert das LLM
nur, wie der bereits vollständig feststehende Effekt durch Figur, Situation
und Bildhandlung verständlich ausgedrückt wird. Es darf weder Mechanik,
Trigger, Ziele, Zahlen noch Regelbedeutung ergänzen oder verändern.

Beim Öffnen bindet der Booster ein `target_deck_revision_id`, standardmäßig die
aktuell gewählte Deckentwicklung. Nach der Bildbewertung werden Keep- und
Favorite-Slots in stabiler Boosterreihenfolge bevorzugt auf unterschiedliche,
noch bildlose Standard-CardIdentities dieses Decks verteilt. Die konkrete
Auswahl aus mehreren freien Körpern erfolgt reproduzierbar über den gebundenen
Craft Seed und wird vor dem Branding persistiert. Fehlen freie Körper, erzeugt
der Server für die restlichen positiven Slots je eine neue Standard-
CardIdentity und brandet sie unmittelbar. Das Branding revisioniert die
gewählte Identität; es erzeugt keine zweite CardIdentity für dasselbe Bild.

## Vom Booster-Kartenkörper zur Spielkarte

Jeder reguläre Vierer-Booster besitzt genau vier Kartenresultat-Slots. Nach vier
gültigen Bewertungen liefert er immer genau vier Ergebnisreferenzen auf
unterschiedliche CardIdentities. Diese Identitäten müssen nicht alle neu sein:
Keep und Favorite entwickeln bevorzugt vorhandene freie Standardkörper des
Zieldecks. Reject materialisiert eine neue bildlose Standardkarte. Nur wenn für
einen positiven Slot kein freier Körper mehr vorhanden ist, entsteht auch für
ihn eine neue Standard-CardIdentity, die sofort gebrandet wird.

```text
Reject   → Bild wird nicht als Kartenmotiv übernommen
           → neue bildlose Standardkarte wird materialisiert

Keep     → Bild wird als Branding gebunden
           → bevorzugt vorhandener freier Standardkörper, sonst neuer Körper
           → persönliche Bildkarte ab Common Level 1

Favorite → Bild wird als Branding gebunden
           → bevorzugt vorhandener freier Standardkörper, sonst neuer Körper
           → persönliche Bildkarte ab Rare Level 1
```

Ein Reject ist negative visuelle Evidence und kein Verlust des Kartenkörpers.
Das abgelehnte Bild wird aber nicht zur Bildkarte. Ein technisch unbewertbares
oder fehlendes Bild blockiert den Booster mit Recovery; erst ein vollständig
bewerteter Booster materialisiert seine vier Kartenresultate. Ein späterer
Championtitel verbessert dieselbe gebrandete Kartenidentität und erzeugt keine
zweite Karte.

„Frei“ bedeutet dabei: bildlos, ungebrandet, verfügbar und im Zieldeck als
Standard-CardIdentity referenziert. Ein Körper wird innerhalb desselben
Boosters höchstens einem positiven Resultat zugeordnet. Referenzieren weitere
gespeicherte Decks dieselbe CardIdentity, sehen sie ab der nächsten
Deckrevision ebenfalls deren Entwicklung. Die UI weist darauf hin und lässt
alle betroffenen Decks erneut durch die Deck-Readiness prüfen. Ein bereits
laufendes Match verwendet unverändert seinen eingefrorenen Snapshot.

Vier Rejects erzeugen weiterhin vier neue bildlose Standardkarten. Vier
positive Resultate können dagegen vier vorhandene freie Karten entwickeln und
die Sammlung daher qualitativ verändern, ohne ihre Identitätsanzahl zu erhöhen.

Dieser Vier-Karten-Vertrag gilt ausschließlich für reguläre Battle-Booster.
Ein späterer Adult-Content-Bereich darf dieselbe diegetische Booster-Metapher
und eigene Bildspiele verwenden, erzeugt aber weder CardIdentity noch
ImageBranding für den Card Battler, Deckverfügbarkeit oder
CharacterChampion-Eligibility. Seine visuelle Sammlung und VN-Wirkung werden
in einem eigenen Vertrag definiert.

```text
BoosterCardBody
└─ CardIdentity
   ├─ bei Reject: bildlose StandardCardRevision
   └─ bei Keep oder Favorite: ImageBrandingRevision
      ├─ genau eine ImageIdentity
      ├─ immutable MemoryOriginRevision
      ├─ CardArtCompositionDraft
      ├─ aktive und historische CardArtCompositionRevisionen
      ├─ aktive und historische CardFaceAssetRevisionen
      ├─ BaseCardRevision
      ├─ optionaler FavoriteAugment
      ├─ optionaler ChampionAugment
      ├─ Rarity und DevelopmentLevel
      ├─ reproduzierbare DevelopmentAugments
      ├─ CardBattleExperienceProjection
      ├─ aktive und historische CardEvolutionRevisionen
      ├─ aktuelle CardRulesRevision
      └─ CardAvailabilityProjection
```

- `Reject` bleibt ein traitloser bildloser Standard-Figurenkörper mit schwachen
  ATK-/DEF-Werten, aber ohne ImageBrandingRevision, Challenger-Eignung oder
  bildbezogene LLM-Lore.
- `Keep` erzeugt eine vollständige, grundsätzlich spielbare Basiskarte auf
  mindestens `Common Level 1`.
- `Favorite` erzeugt dieselbe Basiskarte und zusätzlich eine begrenzte,
  randomisierte Favorite-Verbesserung sowie mindestens Rare Level 1.
- Ein späterer Kombinationschampion erhält zusätzlich eine begrenzte,
  randomisierte Champion-Verbesserung und einen Entwicklungsschritt innerhalb
  derselben TraitLineage.
- Ist ein Favorite zugleich Champion, wirken beide vorgesehenen
  Verbesserungsstufen innerhalb eines versionierten Gesamtbudgets.
- Eine Promotion steigert vorhandene Traits oder ergänzt einen kompatiblen
  neuen Trait. Sie würfelt Kampfprofil, Branding und TraitLineage nicht neu und
  erzeugt eine neue Revision derselben CardIdentity.
- Die manuelle Wahl von Ausschnitt, Zoom und Frame verändert keine dieser
  Regeln. Sie bestätigt ausschließlich eine presentation-only
  CardArtCompositionRevision. Bis dahin bleibt die Karte regelgültig und wird
  mit einer neutralen ausstehenden Kartenprojektion dargestellt.
- Weitere Titel dürfen keine unbegrenzte vertikale Stärke stapeln. Ihre genaue
  Wirkung gehört zum späteren Card-Battler-Vertrag.

Die bildlose Standardkarte hebt weder die negative Reject-Evidence des
abgelehnten Bildes noch einen daraus folgenden DOA-/Lösch-Lifecycle auf.
Kartenkörper, ImageBranding, Challenger-Qualifikation, Deckverfügbarkeit und
physische Bildverfügbarkeit bleiben getrennte Projektionen. Wird die
abgelehnte Bilddatei später gelöscht, bleibt der bildlose Kartenkörper
erhalten.

### Persönliche Fremdkarten und öffentliche Editionen

Jede gebrandete Spielkarte besitzt genau eine konkrete primäre
`CardSubjectIdentity`. Für persönliche Momentkarten bindet sie eine erlaubte
Person aus dem sozialen Quellkontext des Besitzers. Öffentliche Battle-Events
dürfen stattdessen eine fiktionale Person des öffentlichen Interesses, einen
Battler, Performer, ein konkretes Tier, Maskottchen oder Event-Creature als
Subjekt einer `PublicCardEdition` verwenden. Die bildlose Standardkarte bleibt
die einzige reguläre Karte ohne konkrete dargestellte Figur.

Eine PublicCardEdition ist eine gemeinsame Ausgabequelle, keine gemeinsam
besessene CardIdentity. Jeder Account erhält bei zulässigem Erwerb eine eigene
CardIdentity und eine accountgebundene Editionsbindung. Deshalb dürfen mehrere
simulierte Nutzer dieselbe öffentliche Bildedition spielen, ohne Ownership,
Deckrevision, Entwicklung oder Matchzustand zu teilen. Ob Editionskopien feste
Regeln und Rarity behalten oder besitzerspezifisch begrenzt entwickelt werden,
bleibt ein versionierter Folgeentscheid.

Persönliche Karten von Story-Characters und Remote-NPCs verwenden denselben
serverseitigen Card Materializer wie die Karten des Protagonisten. Vor einer
fremden ImageBrandingRevision steht jedoch zwingend ein persistiertes
`CardContentApprovalReceipt` des realen Human-in-the-loop. Im normalen
Spielerflow entsteht es innerhalb eines live oder zeitversetzt angesehenen
Pack Openings eines gefolgten Streamers, eines Gast-/Kollaborationsstreams oder
eines gezielt geteilten Openings und nicht in einer sichtbaren technischen
Review-Queue.

Die sichtbare Reaktion wird getrennt als `CommunityPackReactionReceipt`
gespeichert. Sie ist Community-Feedback zur gezeigten Darstellung und erzeugt
keine PlayerPreferenceEvidence für den persönlichen Visual Circuit. Weil der
Protagonist das Opening tatsächlich gesehen hat, darf sie ausschließlich das
durch den CardDisclosureContext freigegebene Wissen über Karte und Stream
materialisieren, niemals die vollständige private Ereignis- oder
Relationship-Wahrheit. Anschließend entscheidet ein seedgebundener
`NpcCardDraftReceipt` anhand des NPC-Geschmacksprofils über dessen Keep,
Favorite oder Reject; diese Besitzerentscheidung darf von Spielerreaktion und
simuliertem Community-Ergebnis abweichen. Ein technisch blockiertes Bild wird
vor diesem Draft ersetzt und nicht als persönliche Ablehnung des NPCs
gespeichert.

Nur eine öffentlich oder gezielt für den Protagonisten geteilte persönliche
NPC-Karte kann nach diesem Ablauf in seinen sichtbaren Gegnerpool gelangen.
Vollständige Teilnahme an einem qualifizierten Opening darf ein getrenntes
`EventTicketRewardReceipt` erzeugen. Das Ticket führt ausschließlich zu
öffentlichen Events beziehungsweise deren Eventboostern und verändert weder
NPC-Draft noch CardRules, Rarity, BattlerRating oder Relationship.

Ein Remote-NPC darf eine bekannte soziale Figur nur bei materialisierter
Social-Graph-Überschneidung verwenden. Zwei Accounts dürfen dieselbe Person aus
unterschiedlichen persönlichen Ereignissen darstellen; Quellpost,
`CardDisclosureContext`, ImageIdentity, CardIdentity und Owner bleiben dabei
getrennt. Der Disclosure Context begrenzt die Karten-Copy auf tatsächlich
preisgebbare Namen, Beziehungen, Orte, Anlässe und emotionale Deutungen.

### Gemischte Zielpacks als späterer Crafting-Rahmen

Als verbindliche Core-Idea des späteren Zielsystems dürfen Pack Openings
öffentliche Monstereditionen, persönliche oder öffentliche Heroes und bereits
autorisierte Entwicklungsanlässe mischen. `Hero | Monster` bezeichnet dabei
die konkrete Subjektfantasie derselben universellen Figurenkarte und keine neue
Rules-Kartenart. Packherkunft und Subjektart bleiben getrennte Achsen.

Das Enthüllen des gemischten Packs und eine gegebenenfalls anschließende
Bildbewertung sind getrennte Phasen. Ein Pack darf mit oder für einen Freund
geöffnet werden; eine spätere eingeladene Bewertung kann konzeptionell die
Entwicklung der CardIdentity ihres Besitzers unterstützen. Daraus folgt noch
keine Bewertungs- oder Schreibautorität. Vor der Implementierung müssen
`pack_owner`, `pack_opener`, `invited_evaluator`, `viewer_or_community`,
`card_owner` und `development_recipient` sowie Consent, Disclosure und Receipts
eigenständig festgelegt werden.

Bis zu diesem Folgeentscheid gilt unverändert: Eine öffentliche
CommunityPackReaction entwickelt keine fremde Karte und entscheidet keinen
NPC-Draft. Packkollation, Vier-Slot-Wirkung, Duplikate, Monsterentwicklung,
alternative Kartenkunst und genaue Freundesrechte sind ausdrücklich deferred.
Der aktuelle Card-Crafting- und Rules-v0.1-Vertrag wird durch diese Core-Idea
nicht erweitert.

## Randomisiertes, bildbezogenes Card Crafting

Das Card Crafting verbindet kontrollierten Zufall mit einer eng begrenzten
lokalen LLM-Rolle:

```text
als Keep oder Favorite behaltenes Image und PlaygroundCombinationSignature
→ CardCraftInputManifest
→ deterministischer Zufallswurf für Trait-Aktion, Fähigkeitsfamilie und Mechanikbudget
→ Server materialisiert den vollständigen regelgültigen Effekt
→ lokales LLM erzeugt dessen schemaförmige bildbezogene Erklärung
→ Validator prüft Regeltreue, Bildbezug und Canon-Grenze
→ Materializer vergibt IDs, Zahlen und ausführbare CardRulesRevision
→ sichtbare Kartenenthüllung
```

Das `CardCraftInputManifest` bindet mindestens:

- `image_id`, Disposition und gegebenenfalls ChampionRevision,
- PlaygroundCombinationSignature und Generation-/Recipe-Provenienz,
- sichere Character-, Outfit-, Scene- und Storybindungen,
- versionierte MachineImageObservation und deren Review-/Matchstatus,
- ausdrücklich unbekannte oder widersprüchliche Felder,
- serverseitig gezogenes Kampfprofil, TraitLineage, Trait-Aktion,
  Fähigkeitsfamilien und Mechanikbudget,
- Card-Rules-, Randomizer-, LLM- und Schema-Revision,
- sowie einen reproduzierbaren Craft Seed.

Die Bildbeschreibung liefert sichtbare Motive für Name, Flavor und die
kontextuelle Erklärung des Effekts. Sie bestimmt weder Kombinationszugehörigkeit noch technische
Wahrheit. Bekannte Generation Facts, beobachtete Bildmerkmale und Human
Evidence bleiben getrennt; nur zulässige, hinreichend gebundene Fakten dürfen
die Karte prägen.

Das LLM darf Kartenname, Flavor und die bildbezogene Erklärung des bereits
materialisierten Effekts vorschlagen. Es darf keine Regelprimitive, Trigger,
Ziele, IDs, Zufallsresultate, Zahlen, Championstatus oder
Datenbankschreibvorgänge autorisieren. Die Matchsimulation führt
ausschließlich die materialisierte strukturierte CardRulesRevision aus und
parst niemals den sichtbaren Natursprachentext.

`Card Lore` ist die kontextuelle Erklärung des validierten und materialisierten
Effekts innerhalb des Plattform-Kartenspiels und keine neue VN-Wahrheit. Ein
sichtbarer Regenschirm darf beispielsweise eine Schutzwirkung motivieren, ohne
der dargestellten Figur im World Canon magische Fähigkeiten zuzuschreiben. Bei
bildlosen Standardkarten entfällt diese Ebene; dort steht ausschließlich die
verständliche wörtliche Effektbeschreibung.

Es existiert genau ein struktureller Spielkartentyp: die universelle
Figurenkarte. Jede Karte besitzt Angriffs- und Verteidigungswert und kann offen
oder verdeckt in Angriffs- oder Verteidigungsmodus gespielt werden. Falle,
Support, Zauber und besondere Verteidigung sind keine getrennten Kartentypen,
sondern registrierte Fähigkeitsfamilien ihres Brandings. Ihre Verteilung ist
randomisiert, reproduzierbar und durch Plausibilitäts- sowie
Collection-Coverage-Grenzen geschützt. Das bildlose Base Deck besitzt nur
schwache ATK-/DEF-Profile ohne Traits; persönliche Karten kontextualisieren erst
ihre materialisierten Traits über das gebundene Bild.

## Temporäre Spielbarkeit pro CharacterChampionSignature

Keep-Karten sind bewusst vorläufig. Solange die für ihre Spielbarkeit gebundene
CharacterChampionSignature keinen Kombinationschampion besitzt, dürfen ihre
verfügbaren Keep-Karten als aktive Card-Battler-Karten verwendet werden. Ein
Titel in einer anderen 1er-, 2er- oder 3er-Signatur besetzt diesen konkreten
Championplatz nicht.

Sobald ein Kombinationschampion existiert, gilt:

- Der Champion besetzt den aktiven Championplatz der Kombination.
- Reine Keeps derselben exakten CharacterChampionSignature bleiben persistente
  Bildkarten und dürfen weiter Challenger eines späteren 16er-Cups sein.
- Diese reinen Keeps dürfen jedoch nicht zusätzlich in aktiven
  Card-Battler-Decks verwendet werden.
- Ein neuer Cup-Sieger ersetzt den bisherigen Champion erst über den
  bestehenden Title-Match-Vertrag.
- Favorite-Spielbarkeit, Champion-Spielbarkeit und weitere Deckgrenzen werden
  getrennt projiziert; der besondere Keep-Ausschluss darf nicht als Löschung
  oder Verlust seiner Challenger-Eignung formuliert werden.

Damit kann Bild- und Promptvarianz innerhalb derselben Kombination weiter
erkundet werden, ohne dass viele nahezu gleich gebundene Keep-Karten dauerhaft
als parallele aktive Spielkarten bestehen.

## Eliminations-, Verfalls- und Delete-or-Live-Vertrag

Die vorhandenen visuellen Wettbewerbe bleiben Autorität für die
Kartenlebensdauer:

- Ein Keep geht nach seiner ersten bindenden Eliminationsniederlage in
  Delete or Live.
- Ein Favorite folgt seiner gemeinsamen, modeübergreifenden Verlustserie.
- Champion- und Former-Champion-Schutz folgt dem bestehenden
  Wettbewerbsvertrag.
- Eine Card-Battler-Niederlage zählt für keine dieser Serien.
- Regelgültige Kartenverwendung darf unabhängig vom Matchausgang
  CardBattleExperience schreiben; sie ist weder Eliminationsniederlage noch
  Favorite-Verlust und verändert keinen Championtitel.

Eine gefährdete ungeschützte Keep-Karte erhält entsprechend dem vorhandenen
Foundation-Vertrag ab DOA-Bereitschaft eine persistente siebentägige Frist mit
sichtbarem Warnhinweis und konkretem Löschzeitpunkt. Weitere Referrals
verlängern diese Frist nicht. Der idempotente Expiry-Sweep prüft den
Schutzstatus unmittelbar vor der physischen Löschung erneut. Favorites, aktive
Champions und geschützte Former Champions werden nicht allein wegen
Nichtspielens automatisch gelöscht und benötigen die vorgesehene bewusste
Delete-or-Live-Entscheidung.

`Delete` beziehungsweise der autorisierte Ablauf der ungeschützten Frist
entfernt das physische Bildpaar und setzt seine Verfügbarkeit auf false. Die
aktive Bildbindung, Challenger-Eignung, Bildrarität, Level und Traits enden;
Card-, Match-, Titel- und Evidence-Historie bleiben als Tombstone
nachvollziehbar. Dieselbe CardIdentity erhält atomar eine neue aktive Revision
ihres ursprünglichen bildlosen Standardtemplates mit ihrem ursprünglichen
Kampfprofil, Standard-ATK/DEF und ohne Trait oder Effekttext. Decklisten
behalten die Identität und werden neu validiert. Bereits gestartete Matches
behalten unverändert ihren eingefrorenen Snapshot. Card-Battler-UI und
Deckprojektion zeigen die reale Deadline, erfinden aber keine zweite
Verfallsuhr.

Besitzt die CharacterChampionSignature beim Delete-or-Live-Schritt bereits
einen Champion, verändert `Live` diesen Titel nicht. Die Oberfläche zeigt den
gefährdeten Keep und die Konsequenz vor der Aktion:

```text
Bild löschen
→ Bildbindung und künftige Challenger-Eignung enden
→ dieselbe CardIdentity bleibt als bildlose Standardkarte im Deck

Keep retten
→ Keep wird Favorite
→ vorhandener Champion und dessen Karten-Level bleiben unverändert
→ gerettete Karte kann erst in einem künftigen Cup und gegebenenfalls
  Title Match Champion werden
```

`Live` erzeugt damit weder einen ChampionRevision-Eintrag noch einen
ChampionAugment und ersetzt keinen Amtsinhaber. Es erhält das Bild als Favorite,
setzt die bestehende Verlustserie und den Cooldown nach dem allgemeinen
Wettbewerbsvertrag zurück und erzeugt ein neues Eligibility-Ereignis außerhalb
des bereits eingefrorenen Brackets. Favorite- und ChampionAugment bleiben
getrennte, höchstens einmal pro CardIdentity und Policyrevision
materialisierte Entwicklungsschritte.

Die normale UI verwendet in diesem Sonderfall nicht nur die abstrakte Kurzform
`Live`, sondern kommuniziert die Konsequenz, beispielsweise als `Als Favorite
retten` gegenüber `Bild löschen`. Sie darf keinen sofortigen Championtitel
versprechen.

## Base-Deck-Start und Deck-Readiness

Ein sauberer neuer Save beginnt ohne persönliche Bilder, aber mit dem
vollständigen schwachen und bildlosen Standard-Base-Deck. Dieses Deck ersetzt
keine persönliche Sammlung und besitzt keine Keep-, Favorite-, Challenger-,
Champion- oder Bildprovenienz.

Der erste Card Battler kann dadurch nach seinem Storygate bereits stattfinden.
Generation, Viererbewertungen und Cups entwickeln das schwache Base Deck
schrittweise zu einem persönlichen bildgebundenen Deck. Ein früher Lucky
Favorite oder Champion ist deshalb eine starke Entwicklung, aber keine
Voraussetzung für die technische Decklegalität.

Der Story Director darf einen verpflichtenden Card-Battler erst materialisieren,
wenn eine serverseitige `DeckReadinessProjection` das Base Deck oder ein daraus
entwickeltes Deck als legal bestätigt. Die v0.1-Readiness prüft exakt 40
einzigartige CardIdentities, deren aktuelle spielbare Revisionen und die
festgelegten Ausspielhürden. Bildlöschung ersetzt die aktive Brandingrevision
derselben Identität durch das Standardprofil und entfernt keinen Deckslot.
Story-, Plattform-, Post-, Booster- und Bildentwicklungsbeats liefern
anschließend den persönlichen Aufbau.

## Mindestmodell

Der Zielvertrag benötigt mindestens folgende Entitäten oder gleichwertige
normalisierte Verträge:

- `playground_combination_signatures`,
- `character_champion_signatures` mit ein bis drei kanonischen
  `character_champion_aspect_bindings`,
- `combination_card_slots` mit Foreign Key auf die exakt gebundene
  CharacterChampionSignature,
- `card_identities` und immutable `card_rules_revisions`,
- revisionierte `card_provenance` sowie unveränderliche
  `card_source_eligibility_receipts`,
- `public_card_editions` und accountlokale `owned_public_card_bindings`,
- `card_craft_input_manifests` und `card_author_proposals`,
- `card_craft_random_receipts`,
- `card_content_approval_receipts`, `community_pack_opening_sessions`,
  `community_pack_reaction_receipts`, `event_ticket_reward_receipts` und
  `npc_card_draft_receipts`,
- `public_card_editions` und accountgebundene
  `owned_public_card_bindings`,
- `standard_card_templates` und immutable `card_branding_revisions`,
- `card_augments` mit Source- und Budgetrevision,
- `card_development_events` sowie rebuildbare Rarity-/Level-Projektion,
- `card_memory_origin_revisions`, `card_battle_experience_events` und
  rebuildbare `card_battle_experience_projections`,
- `card_battle_experience_digests`, `card_evolution_trials`,
  `card_evolution_candidates` und immutable `card_evolution_revisions`,
- revisionierte bildlose `standard_base_deck_definitions`,
- `card_availability_events` und rebuildbare Availability-Projektion,
- `deck_readiness_projections`,
- sowie vollständige Foreign Keys zu Image, Description, GenerationRecipe,
  Disposition, ChampionRevision und Delete-or-Live-Entscheidung.

## Testbare Invarianten

1. Jede CharacterChampionSignature enthält genau einen Character und genau
   eine, zwei oder drei kanonisch sortierte, unterschiedliche Aspektbindungen.
   Character-lose oder aspektlose Kombinationschampion-Signaturen sind
   unzulässig.
2. Gleicher Character und dieselben gebundenen Aspekt-ComponentVersionen
   erzeugen trotz anderer Seeds, Recipes, weiterer ungebundener Aspekte oder
   zulässiger Promptformulierungen dieselbe CharacterChampionSignature. Ein
   anderer Character oder ein anderer gebundener Aspekt erzeugt eine andere
   Signatur.
3. VLM und Embeddings können keine Kombinationszugehörigkeit schreiben.
4. Jede gültige erste Disposition aus Reject, Keep oder Favorite erzeugt genau
   ein Kartenresultat pro Boosterplatz. Nur Keep/Favorite binden genau eine
   ImageIdentity; technische Unbewertbarkeit erzeugt bis zum Ersatz keines.
5. Favorite- und Championpromotion revisionieren dieselbe Karte und würfeln
   weder Kampfprofil, TraitLineage noch Branding neu.
6. Derselbe Input, Craft Seed und dieselben Policyrevisionen erzeugen exakt
   dieselbe Karte und dieselben Augments.
7. Ein LLM kann keine nicht registrierte Regelprimitive oder Zahl außerhalb
   des serverseitigen Budgets ausführbar machen.
8. Ohne Kombinationschampion der exakt gebundenen
   CharacterChampionSignature darf eine verfügbare Keep-Karte aktiv spielbar
   sein.
9. Mit Kombinationschampion derselben exakten CharacterChampionSignature
   bleibt ein reiner Keep Challenger, ist aber keine aktive
   Card-Battler-Karte; Titel anderer Granularität besetzen diesen Platz nicht.
10. Ein Cup- oder Title-Match-Sieg wirkt nur innerhalb derselben
    CharacterChampionSignature. Dasselbe Bild darf getrennt in mehreren
    kompatiblen 1er-, 2er- und 3er-Signaturen Titel gewinnen.
11. Eine Card-Battler-Niederlage verändert weder Disposition noch
    Favorite-Verlustserie, Champion oder Delete-or-Live-Status.
12. `Live` erzeugt niemals einen Championtitel oder Championwechsel. Es rettet
    das Bild als Favorite und kann nur ein neues Eligibility-Ereignis für einen
    späteren Cup erzeugen.
13. Physische Bildlöschung beendet Bildanzeige, Branding, Traits, Entwicklung
    und Challenger-Eignung, erhält aber dieselbe CardIdentity als bildlose
    Standardkarte sowie relationale Herkunft, Evidence und Matchhistorie.
14. Ein neuer Save besitzt null persönliche Bildkarten, aber ein vollständiges
    schwaches bildloses Standard-Base-Deck.
15. Reject lässt den zugehörigen Kartenkörper bildlos auf Standard; Keep
    brandet ihn mindestens als Common Level 1 und Favorite mindestens als Rare
    Level 1. Keine Promotion darf bestehenden höheren Fortschritt senken.
16. Gültige Entwicklungsschritte folgen reproduzierbar der Leiter Common,
    Uncommon, Rare, Super, Ultra und Legendary.
17. Card-Battler-Decklegalität wird auch für das reine Base Deck serverseitig
    projiziert; Bildkarten bleiben persönliche Entwicklung und keine
    technische Voraussetzung für das erste Match.
18. Ein minderjähriger Account kann ein legales Deck ausschließlich aus
    `blank_standard` und `public_event` bilden; `personal_post`-Karten werden
    bereits vor Besitz-, Deck- und Matchmaterialisierung abgelehnt.
19. Eine `public_event`-Karte erzeugt keine persönliche Review-, Relationship-,
    CharacterChampion- oder VisualPreferenceEvidence.
20. Eine `personal_post`-Karte benötigt ein gültiges Alters- und
    Einwilligungsreceipt für Besitzer und jede erkennbare Person; fehlende
    Eligibility darf weder durch Crop noch durch spätere Volljährigkeit geheilt
    werden.
21. Jede reguläre Spielkarte ist strukturell eine Figurenkarte mit Angriffs-
    und Verteidigungswert; Falle, Support, Zauber und Verteidigung sind
    Fähigkeitsfamilien und keine getrennten Kartenarten.
22. Eine entwickelte Karte kann im Match nicht als frühere schwächere Revision
    ausgespielt werden; aktuelle Stärke, Ausspielhürde und Deckbaukosten bilden
    einen gemeinsamen Vertrag.
23. Ein vollständig bewerteter regulärer Vierer-Booster erzeugt genau vier
    Ergebnisreferenzen auf unterschiedliche CardIdentities. Positive Resultate
    entwickeln bevorzugt freie Standardkörper des Zieldecks und erzeugen nur
    bei Mangel neue Identitäten; Rejects erzeugen neue bildlose Standardkarten.
    Vier Rejects ergeben daher vier neue Standardkarten, aber keine Bildkarten
    und keine neuen visuellen Challenger.
24. Bildlose Standardkarten besitzen keinen Trait und keinen Effekttext. Bei
    Bildkarten darf das LLM ausschließlich die bereits feststehenden Traits in Figur,
    Situation und Bildhandlung einbetten; es verändert keine Spielregel.
25. Die Zuteilung freier Standardkörper ist craft-seed-gebunden,
    reproduzierbar, innerhalb eines Boosters eindeutig und verändert keinen
    bereits laufenden Match-Snapshot.
26. Jeder Entwicklungsschritt steigert einen vorhandenen Trait oder ergänzt
    innerhalb des Rarity-Caps einen kompatiblen neuen; Kampfprofil und
    TraitLineage werden nicht neu gewürfelt.
27. Jede Bildkarte bindet genau eine konkrete primäre CardSubjectIdentity;
    allein die bildlose Standardkarte besitzt noch kein dargestelltes Subjekt.
28. Dieselbe PublicCardEdition darf mehreren Accounts gehören, erzeugt aber je
    Account eine getrennte CardIdentity und keinen geteilten Matchzustand.
29. Keine persönliche Fremd- oder öffentliche Bildbindung wird ohne
    CardContentApprovalReceipt in ein neues Deck oder einen MatchSnapshot
    aufgenommen. Für eine persönliche NPC-Karte im sichtbaren Gegnerpool bindet
    das Receipt ein öffentliches oder gezielt geteiltes Stream-Pack-Opening.
30. CommunityPackReaction und NPC-Draft bleiben getrennt. Die Reaktion erzeugt
    keine PlayerPreferenceEvidence, darf aber das im Opening tatsächlich
    sichtbare, durch CardDisclosureContext begrenzte Protagonistenwissen
    schreiben; Keep/Favorite/Reject des NPCs stammen ausschließlich aus seinem
    reproduzierbaren NpcCardDraftReceipt.
31. Ein Remote-NPC darf eine bekannte soziale Figur nur über eine
    materialisierte Social-Graph-Überschneidung und einen gültigen
    CardDisclosureContext darstellen.
32. Die MemoryOriginRevision einer persönlichen Bildkarte bleibt unverändert;
    eine angenommene Evolution erzeugt eine neue aktive Revision derselben
    CardIdentity und macht keine frühere Revision wieder aktiv spielbar.
33. Derselbe abgeschlossene Matchsnapshot erzeugt durch Retry oder Replay
    höchstens einmal CardBattleExperience. Laufende Matches verändern keine
    CardRules-, Branding- oder EvolutionRevision.
34. No-op-, Concede-, Kollusions- und Wiederholungsmuster erzeugen keine oder
    nur die ausdrücklich policygedeckelte Kampferfahrung.
35. Vier abgelehnte Evolutionskandidaten verändern weder aktive Bild- noch
    Rules Revision; der verdiente Entwicklungsschritt bleibt retryfähig
    `evolution_pending`.
36. Eine CardEvolutionRevision darf Kartenkunst und erklärende Copy verändern,
    aber keine VN-Asset-, CharacterVisualCanon-, LoRA-, Relationship- oder
    Storywahrheit schreiben.
37. Legendary benötigt sowohl den versionierten visuellen Bewährungsnachweis
    als auch die geforderte Battle Lineage; normale Matchwiederholung allein
    kann die Stufe nicht materialisieren.
38. Ein EventTicketRewardReceipt aus einem Stream-Pack-Opening kann nur
    öffentliche Eventteilnahme beziehungsweise Eventbooster freischalten und
    verändert keine persönliche Fremdkarte, Kartenstärke, Rarity, BattlerRating
    oder Relationship.
