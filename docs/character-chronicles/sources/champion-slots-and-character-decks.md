# Champion-Slots, Bildkarten und Bildmehrfachverwendung

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `MIXED_GAME_IDEAS`  
**Worum es geht:** Champion-Slots, Bildkarten, Vergleichs-/Deckkonzepte und deren Beziehung zu Spielprogression.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../vision/academy-and-world.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für Champion-Kontexte, Wettbewerbe,
Bildkartensammlungen und die Mehrfachverwendung von Bildern

Stand: 10. September 2026

## Zweck

Dieses Dokument definiert die bisher fehlende fachliche Zwischenebene zwischen
Generierungsauftrag, Bildbewertung, Challenger-Pool, Champion, Stabilität und
VN-Asset. Es präzisiert die allgemeineren Verträge aus
[`visual-assets-quests-and-gates.md`](visual-assets-quests-and-gates.md),
[`generation-profiles-and-trials.md`](generation-profiles-and-trials.md) und
[`game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md).

Ein Character besitzt nicht genau einen Champion. Sein Portfolio enthält
persistente Bildkarten und fachlich benannte `ChampionSlot`s. Jeder Slot steht
für einen dauerhaft adressierbaren Vergleichs- und Titelkontext und besitzt
unabhängig von anderen Slots einen Challenger-Pool, eine Champion-Lineage und
Stabilitätsevidenz. Die Bildkarte bleibt dagegen dasselbe sammelbare Bild, auch
wenn es für mehrere Slots qualifiziert wird oder für mehrere Assets als Quelle
dient.

Dieser Vertrag beschreibt primär Single-Character-Slots. Gemeinsame
Relationship-, Ensemble-, Class- und Scene-Slots besitzen nach
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md)
einen eigenen Portfolio-Owner und werden in die beteiligten
Bildkartensammlungen und Titelübersichten projiziert. Sie werden nicht
künstlich einer Hauptfigur zugeschlagen.

## Verbindliches mentales Modell

```text
Character
└─ CharacterPortfolio
   ├─ Image[] → spielerseitige Bildkarte[]
   └─ ChampionSlot[]
      ├─ ComparisonContext[]
      ├─ ImageContextQualification[]
      ├─ ContenderEligibility[]
      ├─ ChampionRevision[]
      └─ SlotMasteryProjection

Image
├─ EvaluationObservation[]
├─ ImageContextQualification[] für mehrere Slots
├─ AlbumMembership[]
├─ ChampionTitle[]
└─ AssetBinding[] und AssetAttempt[]
```

Das Bild ist ein unveränderliches sammelbares Artefakt. Ein Slot, eine
Fragestellung, ein Titel oder ein VN-Asset besitzt das Bild nicht exklusiv,
sondern referenziert es in einem bestimmten Kontext.

Für die Ebenentrennung gilt zusätzlich der Vertrag in
[`player-facing-terminology-and-voice.md`](player-facing-terminology-and-voice.md):
Die Bildkarte ist die Spielerprojektion des Bildes, der ChampionSlot ist interne
Spiel- und Wettbewerbslogik, und ComparisonContext, Recipe-Provenienz sowie
Evidence bleiben Backenddaten. Keine dieser Ebenen ersetzt die andere.

Jeder ChampionSlot besitzt genau einen `VisualPortfolio`-Owner. Für die hier
beschriebenen Character-Karten ist dies normalerweise ein
`CharacterPortfolio`; ein gemeinsamer Slot verwendet stattdessen ein
Relationship-, Ensemble- oder Scene-Portfolio mit kanonischem Participant Set.

## Verbindliche Begriffe und Abgrenzungen

| Begriff | Verbindliche Bedeutung |
|---|---|
| `Favorite` | Absolute Spielerentscheidung „Ziel voll getroffen“ für ein einzelnes Bild. Sie kann Referenz- oder Wildcard-Eignung auslösen, ist aber kein Championtitel. |
| `Keep` | Brauchbares und vom Spieler behaltenes Bild. Es erscheint als Bildkarte und kann bei Kontextkompatibilität Challenger werden, ist aber weder Favorite noch Champion. |
| `Reject` | Negative visuelle Bewertung eines bewertbaren Bildes. Der Booster-Kartenkörper bleibt als bildlose Standardkarte erhalten; das abgelehnte Bild wird weder Bildkarte noch positive Evidence oder Challenger. |
| `ImageCard` / Bildkarte | Spielerprojektion genau eines persistenten, als Keep oder Favorite behaltenen Bildes. Bewertung, Titel, Stability und Verwendungen sind Beziehungen beziehungsweise Zustände dieses Brandings und keine zweite Kartenidentität. |
| `BatchPick` | Optionaler lokaler Favorit eines Viererbatches ohne Championwirkung. Historische Felder mit „champion“ im Namen dürfen diese Bedeutung nicht in die Ziel-UI übertragen. |
| `ChampionSlot` | Dauerhafter, benannter Vergleichs- und Titelkontext. Er definiert, was verglichen werden darf, ist aber selbst keine Bildkarte. |
| `Challenger` | Ein für genau einen Slot und dessen aktuelle Vertragsrevision qualifiziertes Bild. |
| `SlotChampion` | Aktueller Titelträger genau eines Champion-Slots. |
| `FormerChampion` | Frühere ChampionRevision desselben Slots; bleibt historisch und nach den gemeinsamen Schutzregeln geschützt. |
| `StableChampion` | Zusammengesetzte technische Projektion für einen SlotChampion, dessen Kontext zusätzlich die Stability-/Mastery-Regeln erfüllt. In der normalen UI werden Titel und Stabilität getrennt erklärt. |
| `VnReadyChampion` | Historischer beziehungsweise zusammengesetzter Technikbegriff. Die Ziel-UI zeigt stattdessen getrennt den Championtitel der Karte und eine konkrete freigegebene Assetverwendung. |
| `SignatureChampion` | Sieger einer übergeordneten Character Championship. Er repräsentiert den Character, ersetzt aber keinen SlotChampion und erzeugt keine Stability- oder Assetautorität. |
| `AssetSourceSelection` | Auswahl eines Bildes als Quelle für genau einen AssetProductionContract. Sie kann dieselbe Karte wie ein Champion referenzieren, erzeugt aber keinen Championtitel und verändert keinen vorhandenen Titel. |

Ein Bild darf gleichzeitig Favorite, Champion mehrerer Slots, Album-Mitglied,
Referenzquelle und Quelle mehrerer Asset-Ableitungen sein. Diese Rollen bleiben
als getrennte, nachvollziehbare Beziehungen gespeichert.

## Der Champion-Slot existiert vor dem Champion

Ein Slot wird nicht rückwirkend aus dem Prompt seines ersten Champions
abgeleitet. Der Slot besitzt vor der ersten Generierung einen versionierten
semantischen Vertrag. Dieser bestimmt mindestens:

- stabile `champion_slot_id` und fachlichen Anzeigenamen,
- genau eine `portfolio_id` und bei gemeinsamen Slots ein kanonisches
  Participant Set,
- Character und gebundene `CharacterVisualCanonRevision`,
- Assetrolle beziehungsweise rein visuelle Sammlungsrolle,
- Outfit-, Pose-/Action-, Expression-, Scene-, Lighting-, Framing- und
  View-Anforderungen, soweit sie für diesen Slot fachlich bindend sind,
- Content Scope,
- Expected Composition,
- Locked Axes und erlaubte Varied Axes,
- Compatibility Policy und relevante Revisionsgrenzen,
- primäre Bewertungsfrage,
- zulässige Generation-, Evaluation- und Recovery-Foci,
- sowie optionale Bindung an ein `VisualRequirement` oder einen
  `AssetProductionContract`.

Ein Slot ist kein ungefiltertes kartesisches Produkt aller Metadaten. Nur
authored Storybedarf, wiederverwendbare Assetverträge, Character Canon und ein
versionierter Coverage-Plan materialisieren relevante Slots. Etwa 40 Slots pro
Character sind plausibel; Millionen theoretischer Kombinationen sind kein
Produktziel.

### Character ist der feste Anker jeder Kombinationsmeisterschaft

Kombinationschampions werden nicht aus beliebigen Aspektpaaren gebildet. Jeder
entsprechende ChampionSlot bindet immer genau einen Character und zusätzlich
genau eine, zwei oder drei unterschiedliche semantische Aspektbindungen:

```text
CharacterChampionSignature
├─ character_component_version_id          # immer vorhanden
├─ aspect_bindings[1..3]                  # kanonisch sortiert
│  ├─ component_kind
│  └─ component_version_id oder BindingRevision
└─ champion_combination_policy_revision
```

| Granularität | Bedeutung | Beispiel |
|---|---|---|
| 1er-Kombination | Character plus ein Aspekt | Aiko + Sonntagsoutfit |
| 2er-Kombination | Character plus zwei Aspekte | Aiko + Sonntagsoutfit + Shopping Mall |
| 3er-Kombination | Character plus drei Aspekte | Aiko + Sonntagsoutfit + Shopping Mall + winkende Pose |

Ein Slot ohne Character, etwa nur `Shopping Mall + Sonntagsoutfit`, ist für
diesen Championvertrag ungültig. Ebenso entsteht hier kein aspektloser
Character-Champion. Welche Aspektarten zulässig sind, bestimmt die
versionierte Slot-/Coverage-Policy; möglich sind insbesondere Outfit, Scene,
Pose/Action, Expression, Lighting, Framing/View und
Presentation-/Modifier-Bindings.

Die vollständige `PlaygroundCombinationSignature` bleibt die Provenienz des
erzeugten Bildes. Aus ihr dürfen mehrere kompatible 1er-, 2er- und
3er-`CharacterChampionSignature`s projiziert werden. Jede besitzt einen eigenen
Pool, einen eigenen 16er-Cup und einen eigenen Titel. Ein einziges Bild kann in
mehreren dieser Slots Champion werden, bleibt dabei aber dieselbe Bildkarte und
dieselbe CardIdentity. Jeder erstmalige Slot-Titel erzeugt ausschließlich den
dafür budgetierten Champion-Level-Up dieser Karte.

Für einen wiederverwendbaren Sprite kann die Scene bewusst außerhalb des
Slotvertrags liegen. Bei einem integrierten Story-CG gehören Scene und
Presentation Binding dagegen zum Slot. Die Compatibility Policy entscheidet
dies pro Assetrolle und nicht über eine globale Liste harter Dimensionen.

## Semantischer Kontext statt wortgleichem Prompt

Der konkrete Prompttext definiert nicht die Vergleichbarkeit. Er ist zusammen
mit Recipe, Workflow, Modell, Gewichten und Renderparametern vollständige
Provenienz eines Generationsergebnisses.

Die Slotkompatibilität wird aus einer normalisierten semantischen Signatur
bestimmt:

```text
Character Canon
+ relevante Outfit-/Scene-/Presentation-Bindings
+ Assetrolle oder Sammlungsrolle
+ Pose-/Expression-/Framing-/View-Korridor
+ Content Scope
+ Locked/Varied Axes
+ Compatibility Policy Revision
→ ChampionSlotContextSignature
```

Promptformulierungen, Tokengewichte, CFG, Steps, Sampler, Scheduler, Seeds und
andere technische Werte dürfen innerhalb des erlaubten Korridors variieren.
Ändert eine Variation den semantischen Auftrag, benötigt sie einen anderen Slot
oder eine neue Slotrevision. Eine neue Recipe allein erzeugt keinen neuen Slot.

Der aktuelle Champion und sein Recipe dürfen nach dem ersten Cup eine Baseline
oder Referenzquelle für neue Versuche bilden. Sie definieren den Slot jedoch
nicht und können seine fachlichen Grenzen nicht verschieben.

## Comparison Context und kontrollierte Variation

Jede Generierungs- oder Auswahlrunde bindet einen `ComparisonContext` an genau
einen primären Generation- beziehungsweise Evaluation Focus. Er speichert:

- Slot- und Vertragsrevision,
- Primary Question und Expected Composition,
- Fixed Signature,
- Locked und Varied Axes,
- Control-/Challenger-Arme,
- Seed-Panel und Paarungsstrategie,
- GameMode-/Runtime-Revision,
- Evidence Scope,
- Recovery-Autorität,
- sowie alle Recipe- und Providerrevisionen.

Es gibt zwei fachlich verschiedene Variationsarten:

1. **Exploration:** Mehrere deklarierte Faktoren dürfen gemeinsam variieren.
   Das Ergebnis darf Bilder als Challenger qualifizieren und Recipe-/Combo-
   Evidenz erzeugen, aber keine kausale Einzelachsenbehauptung.
2. **Kontrollierter Trial:** Möglichst genau eine Achse variiert. Gepaarte Seeds
   reduzieren zunächst Zufallsvarianz; anschließend prüfen neue unabhängige Seeds
   die Generalisierung. Nur dieser Pfad darf kausalen Einzelachsen-Credit liefern.

Der Spieler bewertet weiterhin Bilder und eine verständliche Frage. Technische
Arme und vollständige Diffs bleiben im Advanced- beziehungsweise Diagnosepfad.

## Bildmehrfachverwendung ist Kernvertrag

Ein `Image` kann für beliebig viele fachlich kompatible Fragestellungen erneut
verwendet werden. Dafür entsteht pro Frage und Kontext eine eigene
`ImageContextQualification` beziehungsweise `EvaluationObservation`; die Datei
und ihre ursprüngliche Generation Provenance werden nicht dupliziert.

Beispiel:

```text
Image 142
├─ Favorite: allgemeines Ziel voll getroffen
├─ Identity Observation: positiv
├─ Outfit Observation: teilweise / nicht qualifiziert
├─ Sprite Usability Observation: positiv
├─ Challenger in „Schuluniform-Sprite“
├─ Champion in „neutrale Frontansicht“
└─ Quelle einer normalisierten Sprite-Version
```

Verbindliche Regeln:

- Eine vorhandene Disposition darf eine weitere Prüfung priorisieren oder eine
  grundsätzlich erlaubte Eligibility eröffnen, beantwortet aber keine andere
  Fragestellung automatisch.
- Eine Observation ist nur bei identischer Frage, Scope-, Contract- und
  Revisionsbindung wiederverwendbar.
- Ein Bild darf in mehreren Slots jeweils Challenger oder Champion sein.
- Innerhalb desselben Pools zählt dasselbe Bild höchstens einmal.
- Ein eingefrorener 16er-Cup benötigt sechzehn unterschiedliche Bilder.
- Eine sekundäre Slotqualifikation darf nach der ursprünglichen Generierung
  entdeckt werden. Sie benötigt denselben Compatibility Check und gegebenenfalls
  eine neue kontextuelle Spielerbewertung wie ein primär erzeugtes Bild.
- Roll-up-Projektionen deduplizieren nach zugrunde liegendem Bild, Seed, Attempt,
  Observation und Zielmetrik. Drei Titel desselben Bildes werden nicht zu drei
  unabhängigen Identity-Seeds.
- Evidenz wird nie über inkompatible Canon-, Assetrollen-, Content-, Prompt-
  oder Recipe-Revisionsgrenzen hinweg vermischt.

Die Mehrfachverwendung spart Renderbudget und erzeugt sichtbare Bildkarrieren.
Sie ist kein Weg, Mindeststichproben oder Stabilität künstlich zu erhöhen.

## Challenger-Pool, Cup und Titelverteidigung

Jedes transportgültige, verfügbare und für die aktuelle Slotrevision
kontextkompatible Keep oder Favorite darf ein
`ContenderEligibilityEvent` für diesen Slot erzeugen. Ein Bild kann über
getrennte Ereignisse mehreren Slots zugeordnet werden.

Dies gilt ausschließlich für reguläre, Card-Battler-fähige Content Scopes.
Adult-Content-Pools dürfen später eigene Bildspiele und einen eigenen
Booster-Rahmen besitzen, erzeugen jedoch keinen CharacterChampionSlot, keinen
16er-Cup und keine Deckverfügbarkeit.

Für jeden Slot und Content Scope gilt:

1. Die ersten sechzehn aktuell rosterfähigen, noch keinem Cup dieses Slots
   zugewiesenen unterschiedlichen Bilder werden atomar eingefroren.
2. Die stabile Eligibility-Reihenfolge bestimmt die Bracketplätze.
3. Ohne Amtsinhaber wird der Cup-Sieger erster SlotChampion.
4. Mit Amtsinhaber wird der Cup-Sieger Challenger eines getrennten Title Match.
5. Ein Title Match verändert ausschließlich die ChampionRevision desselben
   Slots.
6. Spätere Bilder warten auf den nächsten Cup; kein laufendes Bracket wird
   nachträglich kuratiert oder aufgefüllt.
7. Keep-/Favorite-Verlustserien, Cooldowns, Former-Champion-Schutz und Delete or
   Live folgen dem gemeinsamen Wettbewerbsvertrag.

Tournament-Evidence beantwortet relative Qualität im Slot. Sie ist weder
Stability-Nachweis noch kausale Parameter-Evidenz.

## Champion, Stabilität und Assetverwendung sind orthogonal

Ein Slot besitzt drei getrennte Projektionen:

```text
Title
  kein Champion | aktiver Champion | Former-Champion-Lineage

Mastery
  ungetestet | developing | repair | stable/mastered

Production je AssetProductionContract
  ungebunden | Quelle gewählt | Ableitung läuft | QA offen | approved | failed
```

Ein Champion beweist den besten bisher entschiedenen Einzeloutput eines Slots.
Stability beweist Wiederholbarkeit über unabhängige Seeds und Batches. Ein
bestandener AssetProductionContract beweist ausschließlich die Verwendbarkeit
einer Bildquelle oder ihrer Ableitung für eine konkrete VN-Rolle samt Crop-,
Alpha-, Safe-Area-, Anchor-, Artefakt- und QA-Regeln.

Deshalb sind folgende Zustände ausdrücklich zulässig:

- Champion, aber noch instabil,
- stabile Kohorte, aber noch kein ausgespielter Champion,
- stabiler Champion ohne gebundene Assetverwendung,
- Championkarte mit fehlgeschlagenem Assetversuch und unverändertem Titel,
- sowie ein freigegebenes VN-Asset, dessen Quellkarte weder Favorite noch
  Champion sein muss, sofern der Asset- und Human-Acceptance-Vertrag erfüllt ist.

Character-weite Confidence entsteht hierarchisch aus kompatiblen
Slotprojektionen. Identity-Evidenz kann über mehrere geeignete Slots wirken;
Outfit-, Pose-, Scene- und Assetrollen-Evidenz bleibt enger gebunden. Eine
stabile Portraitkohorte beweist keinen stabilen Full-Body-Sprite.

## Bildkartenbestand, Titelübersicht und spielbares Deck

Die normale visuelle Character-Ansicht projiziert zuerst die
`Bildkartensammlung`, nicht die ChampionSlots als vermeintliche Karten. Jede
Bildkarte referenziert genau ein persistentes Keep-/Favorite-Bild und zeigt
mindestens:

- verständliche Bildbeschreibung und gebundenen sichtbaren Kontext,
- Keep oder Favorite und die daraus folgende Startseltenheit,
- Challenger-Eignungen und gewonnene Titel,
- Stability als getrennte Information,
- konkrete freigegebene, offene oder fehlgeschlagene Assetverwendungen,
- sowie die Bildkarriere und einen kontextuellen Trial-Einstieg.

Eine davon getrennte Titel- beziehungsweise Arenaübersicht projiziert die
materialisierten ChampionSlots. Sie zeigt offene Titel, kompatiblen
Challenger-Fortschritt, aktuellen Champion, Former-Champion-Lineage,
Slot-Mastery und das nächste sinnvolle Bildziel. Ein offener Slot ist damit ein
offener Auftrag oder Titel, keine leere Bildkarte.

Das spätere VN-/Card-Battler-Deck ist keine zweite, von diesen Karten losgelöste
Sammlung. Es ist die aktuell spielbare Teilmenge desselben Character-Bestands
plus zulässiger bildloser Standardkarten und offiziell freigegebener
`PublicCardEdition`s. Öffentliche Editionen gehören nicht zu einem persönlichen
CharacterPortfolio, nicht zum persönlichen Booster-/Visual-Circuit und nicht
zu dessen ChampionSlots. Minderjährige Accounts dürfen ausschließlich diese
beiden nicht-persönlichen Quellen verwenden; personenbezogene Karten aus
privaten Posts setzen verifizierte Volljährigkeit und vollständige
Einwilligungs-Eligibility voraus. Jeder vollständig bewertete persönliche
Vierer-Booster liefert vier Kartenkörper: Reject lässt seinen Körper bildlos
auf Standard, Keep brandet ihn mindestens als Common Level 1 und Favorite
mindestens als Rare Level 1. Nur Keep und Favorite erzeugen eine Bildbindung an
der bereits vorhandenen CardIdentity. Favorite und Champion revisionieren
dieselbe gebrandete Karte mit
randomisierten, serverseitig budgetierten Verbesserungen. Bildlose Karten
besitzen keinen Trait und keinen Effekttext; eine Bildkarte erklärt ihre bereits
materialisierten Traits über Figur, Situation und sichtbare Bildhandlung.

Die Spielbarkeit eines Keeps ist bewusst vorläufig und an die dafür gebundene
exakte CharacterChampionSignature gekoppelt. Solange dieser konkrete 1er-,
2er- oder 3er-Slot keinen Kombinationschampion besitzt, darf der verfügbare Keep
aktiv verwendet werden. Sobald er besetzt ist, bleiben reine Keeps derselben
Signatur Bildkarten und Challenger, dürfen aber nicht zusätzlich als aktive
Card-Battler-Karten verwendet werden. Ein Championtitel in einer anderen
Granularität besetzt diesen Slot nicht. Ein späterer, durch Cup und Title Match
verdienter Championwechsel revisioniert die Titelbindung, nicht die
Bildidentität. Delete or Live kann keinen Championwechsel erzeugen.

Das aktive Matchdeck enthält verbindlich 40 Karten; Ziehphase und die beiden
Hauptphasen sind festgelegt. v0.1 verwendet keine allgemeine Mana- oder
Energieressource, genau eine Instanz jeder CardIdentity, kein Side-/Reserve-Deck
und die in den spezialisierten Regeln festgelegten Siegbedingungen. Der
gesellschaftliche Normalfall ist ein gemischtes Deck mit vielen bildlosen
Standards, einzelnen öffentlichen Editionen und wenigen persönlichen
Bildkarten. Ein Full Deck aus vierzig Bildkarten ist selten und prestigeträchtig,
aber weder Ligaformat noch notwendigerweise strategisch optimal. Alle drei
Quellen spielen im selben Wettbewerbssystem; Quellen- und Altersregeln schaffen
keine getrennte Public- oder Personal-Liga.

Jede persönliche Bildkarte bewahrt ihr unveränderliches Ursprungsmemory.
Regelgültige Matchverwendung kann post-match Kampferfahrung erzeugen und eine
neue, visuell stärker mythologisierte aktive Revision derselben CardIdentity
vorbereiten. Wird diese Evolution angenommen, bleiben Ursprungsbild und frühere
Formen historisch sichtbar, sind aber nicht frei wieder aktiv spielbar. Diese
Kartenlaufbahn verändert keinen ChampionSlot und ersetzt keinen visuellen
Challenger-Nachweis; Legendary benötigt beide getrennten Bewährungsachsen. Der
vollständige Entstehungs-, Kombinations- und Verfallsvertrag steht in
[`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md).
Deck- und Zugstruktur stehen in
[`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md).

Die Character-Oberfläche muss deshalb drei Zustände verständlich unterscheiden,
ohne drei getrennte Datenwelten zu erfinden:

- vollständiger Kartenbestand aus bildlosen Standardkarten, öffentlichen
  Eventeditionen und den persönlichen Keep-/Favorite-/Champion-Bildkarten,
- aktuell spielbare Teilmenge aus vorläufig zulässigen Keeps, Favorites und
  Kombinationschampions gemäß Playground-Kombinations- und Availability-Vertrag,
- aktives, serverseitig validiertes 40er-Spieldeck aus einzigartigen
  CardIdentities.

`CharacterDeck` darf als technischer Legacyname nicht unkommentiert alle drei
Bedeutungen zugleich tragen.

Beispiel:

```text
32 Bildkarten gesammelt
24 Titel besetzt
19 einzigartige Titelträger
15 stabile Kontexte
9 freigegebene Assetverwendungen
```

Ein Bild erscheint nur einmal als Bildkarte, darf auf dieser Karte aber mehrere
Titel tragen. Titel- und Arenaansichten dürfen dasselbe Bild als jeweiligen
Titelträger referenzieren. Die Bilddetailansicht führt Bewertungen, Titel,
Assetbindungen und VN-Verwendungen zusammen, statt die Datei als mehrere
vermeintlich unabhängige Karten darzustellen.

## Character Championship und Signature Champion

Eine übergeordnete Character Championship darf aktuelle SlotChampions und nach
Rules Snapshot zugelassene Favorites als Wildcards verwenden. Sie stellt eine
andere Frage als ein Slot-Cup, beispielsweise: „Welches Bild repräsentiert
diesen Character am stärksten?“

Verbindliche Grenzen:

- Jedes einzigartige Bild erhält höchstens einen Platz im selben Wettbewerb,
  auch wenn es mehrere Slottitel besitzt.
- Der SignatureChampion ersetzt keinen SlotChampion.
- Sein Sieg erzeugt keine Slot-Stability, keine Assetfreigabe und keinen
  kausalen Generation Credit.
- SlotChampions und Favorites behalten ihre ursprünglichen Rollen unabhängig
  vom Ausgang.
- Teilnehmerzahl, Wildcardquote, Seeding und Wiederholungsrhythmus liegen im
  versionierten Rules Snapshot und dürfen später kalibriert werden.

Der SignatureChampion ist Prestige-, Cover- und Repräsentationsstatus. Eine
spätere figurenübergreifende Championship benötigt einen eigenen Vertrag und
wird aus diesem Character-Wettbewerb nicht automatisch abgeleitet.

## Verbindung zur Generierung

Der Scheduler plant nicht nur abstrakte Character-, Scene- und Outfit-Combos.
Er projiziert pro Slot einen Bedarf, beispielsweise:

```text
Slot ohne Baseline
Slot mit zu wenigen qualifizierten Bildern
15/16 rosterfähige Challenger
Champion benötigt Titelverteidigungszyklus
Stability benötigt neue unabhängige Seeds
Repair-Cluster benötigt kontrollierten Challenger
Assetvertrag benötigt fehlende Source- oder QA-Variante
```

Aus diesem Bedarf erzeugt der Orchestration Guardian aus
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md)
den nächsten autorisierten Auftrag. Ein Slot darf Bilder aus bestehenden,
sekundär kompatiblen Beständen erhalten; neue Generierung ist nur eine mögliche
Quelle.

Der erste Produktpfad prüft neu gerenderte Bilder nicht vorab per Image
Embedding. Er erzeugt zunächst einen kontrollierten Try, lässt ihn vollständig
durch den Human-in-the-loop-Review laufen und autorisiert erst danach
scopegebundene Bildbeobachtungen. Post-review dürfen Embeddings bereits
bewertete Bilder als Kandidaten weiterer Slots vorschlagen; die neue
Fragestellung benötigt dennoch eine eigene Human-Observation. Der vollständige
Deck-/Embedding-/Context-Vertrag steht in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md).

## Persistenz- und API-Mindestmodell

Der Zielvertrag benötigt mindestens folgende stabilen Entitäten oder
gleichwertige normalisierte Verträge:

- `champion_slots` und immutable `champion_slot_revisions`,
- `character_champion_signatures` mit verpflichtendem Character sowie ein bis
  drei normalisierten, kanonisch sortierten Aspektbindungen,
- `portfolio_id` sowie normalisierte Participant-Bindungen für jeden Slot,
- `comparison_contexts`,
- `image_context_qualifications`,
- `evaluation_observations`,
- slotgebundene `contender_eligibility_events`,
- `champion_revisions` mit expliziter `champion_slot_id`,
- `slot_mastery_projections`,
- `asset_bindings`,
- optionale `character_championships` und `signature_champion_revisions`.

Ein opaker `context_hash` darf als Integritäts- und Lookup-Schlüssel bestehen,
ersetzt aber weder die typisierten Felder noch eine lesbare Context-Projektion.
Hashes werden aus kanonisch serialisierten, revisionierten Verträgen berechnet
und niemals als alleinige Produktsemantik behandelt.

## Abgrenzung zum implementierten Foundation-Stand

Der Foundation-Stand besitzt bereits Context Hashes, Challenger-Pools,
eingefrorene Rosters, Brackets und ChampionRevisionen. Er materialisiert jedoch
noch keinen langlebigen, benannten ChampionSlot mit vollständiger
Assetrollen-/Pose-/Expression-/Framing-/View-Bindung und keiner allgemeinen
Many-to-many-Qualifikation eines Bildes für mehrere Slots. Diese Spezifikation
ist Zielvertrag; die Abweichung wird im Traceability-Register geführt.

## Testbare Invarianten

1. Ein Character kann gleichzeitig mehrere aktive SlotChampions besitzen.
2. Eine ChampionRevision referenziert genau einen Slot und dessen Revision.
3. Eine Recipe-Änderung erzeugt ohne semantische Vertragsänderung keinen neuen
   Slot.
4. Ein Slotwechsel wird nicht allein aus Promptstring-Ähnlichkeit entschieden.
5. Dasselbe Bild darf in zwei kompatiblen Slots unterschiedliche Rollen und
   Ergebnisse besitzen.
6. Eine Bewertung zu Frage A beantwortet Frage B nicht automatisch.
7. Ein Bild belegt innerhalb desselben Pools und Brackets höchstens einen Platz.
8. Ein 16er-Cup enthält sechzehn unterschiedliche verfügbare Bilder.
9. Mehrfachqualifikation erhöht keine metrische Stichprobe durch Doppelzählung.
10. Tournament-Sieg allein setzt weder `mastered` noch `VN-ready`.
11. Stability allein erzeugt keinen Championtitel.
12. Asset-QA wirkt ausschließlich auf den gebundenen Produktionsvertrag.
13. Ein SignatureChampion verändert keinen Slottitel und keine Assetfreigabe.
14. Bildkartensammlung, Titelübersicht und Bilddetailansicht werden vollständig aus Serverzustand
    projiziert.
15. Reload und deterministischer Rebuild rekonstruieren Slots, Qualifikationen,
    Titel, Mastery, Assetbindungen und Mehrfachverwendungen identisch.
16. Jedes als Keep oder Favorite behaltene Bild erscheint als genau eine
    Bildkarte, unabhängig von der Zahl seiner Slotqualifikationen und
    Championtitel. Reject erzeugt nur eine bildlose Spielkarte und keine
    Bildkarte oder Challenger-Eignung.
17. Ein fehlgeschlagener AssetAttempt verändert weder Keep/Favorite noch einen
    Champion- oder Signature-Titel.
18. Eine AssetSourceSelection erzeugt ohne getrennten Cup- beziehungsweise
    Title-Match-Sieg keinen Championtitel.
19. Jede CharacterChampionSignature bindet genau einen Character plus eine,
    zwei oder drei unterschiedliche Aspektbindungen; Character-lose und
    aspektlose Signaturen sind unzulässig.
20. Unterschiedliche Seeds, Recipes oder zulässige Promptvarianten verändern
    eine semantisch unveränderte CharacterChampionSignature nicht. Dasselbe
    Bild darf getrennt für mehrere kompatible 1er-, 2er- und 3er-Signaturen
    qualifiziert sein und mehrere Titel tragen.
21. Existiert ein Kombinationschampion, bleibt ein reiner Keep derselben
    exakten Signatur challengerfähig, ist aber nicht zusätzlich als aktive
    Card-Battler-Karte zulässig.
22. Card-Battler-Matches verändern keine Keep-/Favorite-Verlustserie und lösen
    weder Championwechsel noch Delete or Live aus.
