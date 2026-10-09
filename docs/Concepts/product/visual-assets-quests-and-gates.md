# Visuelle Assets, Quests und Scene Gates

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 10. September 2026

## Bildzentrierter Kern

Story- und Social-Outcomes dürfen nachvollziehbaren **Darstellungsbedarf**
erzeugen, etwa eine neue Szene, ein authored Outfit oder einen gemeinsamen
Moment. Sie bestimmen weder dessen konkrete Optik noch visuelle Präferenz,
Prompt-/Recipe-Credit oder Character Canon. Diese Autorität besitzt nach dem
eng begrenzten Prolog-Bootstrap ausschließlich der Booster-/Bildspiel-Loop.
Fortschritt wird nicht durch Text allein freigeschaltet; die bestehende
Generation-, Review-, Fehler- und Evidenzpipeline bleibt der Produktionsmotor.

## Harte Milestone-Grenze: M6 verbessert Quellbilder, produziert keine VN-Assets

Foundation M6 endet bewusst **vor** der in diesem Dokument beschriebenen
Asset-Produktionspipeline. Der M6-Lernbeweis umfasst ausschließlich:

```text
Vierer-Generierung
→ Spielerbewertung und bildweise Gründe
→ persistierte, getrennte Evidence
→ nachvollziehbare Prompt-/Recipe-Änderung
→ neue ComfyUI-Generierung
→ sichtbarer Vergleich und erneute Bewertung
```

M6 muss damit zeigen, dass Spielerbewertungen die folgenden Bilder messbar und
sichtbar verändern können. Es erzeugt dagegen weder `AssetSourceSelection` noch
Extraction-, Matting-, Normalization- oder Asset-QA-Attempts. Auch
`DerivedAssetImage`, `AssetVersion`, Expression-Familien, Place-Assets und
`SceneAssetGate`-Readiness gehören nicht zu M6.

Keep-, Favorite- und Championstatus sind in M6 nur bewertete Bildzustände mit
Provenienz und späterer Quell-Eignung. Erst Chronicle Slice 3 darf nach
`M6_LEARNING_LOOP_PROVEN` einen solchen Zustand in einen eigenständigen
Asset-Produktionsvertrag überführen. Die folgenden Abschnitte sind daher der
nachgelagerte Zielvertrag, nicht ein Bestandteil der aktuellen M6-Umsetzung.

## Assetklassen

- Visual Canon für Identität und Character Revision,
- normalisierte, freigestellte VN-Sprites,
- wiederverwendbare Environment Assets,
- Outfits, Posen und Expressions,
- Story CGs und Memory Images,
- LoRA-Dataset-Bilder,
- negative Evidenz und Recovery Pairs.

Jedes Asset besitzt eine stabile ID, Provenienz, Character-/World-Revision,
Prompt-/Workflow-/Renderprofil-Snapshot, QA-Status und zulässige Bindung.

## Produktionsverträge statt einzelner Renderaufträge

Dieser Vertrag betrifft die Produktion unmittelbar im Spiel verwendbarer
Assets. Er beschreibt weder Character-Stabilisierung noch LoRA-Training;
Dataset-Eignung wird getrennt bewertet.

Ein storyseitiges `VisualRequirement` erzeugt keinen unstrukturierten
„Bild generieren“-Auftrag. Es kompiliert einen rollenspezifischen
`AssetProductionContract`. Dieser legt mindestens fest:

- Assetrolle und Verwendungszweck,
- erwartete beziehungsweise verbotene Subjekte,
- Hintergrund-, Transparenz-, Crop-, Safe-Area- und Anchor-Regeln,
- erforderliche Quell-, Masken-, Alpha- und Preview-Artefakte,
- Generation-, Extraction-, Normalization- und QA-Versionen,
- sowie die Bedingungen für Review und Readiness.

Das unveränderte generierte Quellbild bleibt erhalten. Abgeleitete Masken,
Alpha-Master, normalisierte Sprites und Auflösungsvarianten referenzieren dieses
Quellbild und ihre jeweilige Processing-Lineage.

## Verbindliche Sprite-Produktionspipeline

Freistellung ist Teil einer eigenen, wiederholbaren Produktionspipeline:

```text
SpriteProductionJob
→ GenerationAttempt: unverändertes Quellbild
→ RenderTransportGate: Datei darstellbar, kein exaktes Duplikat, Safety erfüllt
→ PlayerGenerationReview mit Mehrfachgründen
→ bei bestätigtem Quellbild:
→ ExtractionAttempt: semantisches Vordergrund-Gate
→ MattingAttempt: weicher Alphakanal, Maskenfusion und Kantenbereinigung
→ NormalizationAttempt: Canvas, Bounds, Scale und Bodenanker
→ AssetQA: technische Checks und Kontrollkompositionen
→ PlayerAssetReview: praktische Verwendbarkeit des abgeleiteten Sprites bewerten
→ AssetVersion APPROVED
```

Jeder technisch darstellbare und sichere Generationsoutput wird vor semantischer
Vision- oder Asset-QA im eigentlichen Bildspiel gezeigt. Falsche Figur, falsches
Outfit, fehlgeschlagene Zieländerung, Artstyle-, Anatomy-, Background- oder
Kompositionsfehler sind keine Vorfiltergründe, sondern auswählbare
Spielerfeedback-Evidence. Nur fehlende oder nicht dekodierbare Dateien, echte
Transportfehler, exakte technische Duplikate und zwingende Safety-Sperren werden
vorher ersetzt.

`PlayerGenerationReview` bewertet den sichtbaren Source Output;
`PlayerAssetReview` bewertet später das daraus abgeleitete Alpha-/Sprite-Asset.
Beide Evidenzarten bleiben getrennt, damit etwa ein guter Character mit
schlechtem Matting weder den Hair Prompt belastet noch als fertiges Sprite gilt.

Ein gültiges Quellbild wird bei einem reinen Masken-, Alpha- oder
Normalisierungsfehler nicht neu generiert. Nur der betroffene Processing-Schritt
wird mit einer neuen Attempt-Version wiederholt. Umgekehrt kann eine saubere
Maske keine falsche Figur, falsches Outfit oder unvollständige Pose freigeben.

### Isolationshintergrund

Sprite-Quellbilder werden gezielt für Freistellung produziert und nicht aus
beliebigen Storybildern ausgeschnitten. Der Generation Contract fordert deshalb
eine einfarbige, strukturlose und schattenlose Isolationsfläche ohne Szenerie,
Requisiten oder weitere Figuren.

Weiß ist die bevorzugte Ausgangsvariante, sofern ein vorgeschalteter
Kontrastcheck keine Kollision mit Haaren, Kleidung, Highlights oder
halbtransparenten Details erwartet. Andernfalls wählt der Contract eine
kontrastierende Matte-Farbe. Verwendete Farbe und Hintergrund-Policy gehören
zum Recipe-Snapshot. Ein optisch weiß wirkender Hintergrund ersetzt weder eine
Maske noch einen echten Alphakanal.

### Image Recognition, Segmentierung und Matting

Diese Aufgaben besitzen getrennte Autorität:

- Image Recognition beziehungsweise Vision Analysis prüft unter anderem
  Subjektzahl, Figurenpräsenz, Vollständigkeit, grobe Pose, Identity-, Outfit-
  und Rollenkompatibilität und routet nach dem Player Generation Review Fehler
  und Recovery. Der Befund versteckt keinen darstellbaren Generationsoutput.
- Segmentierung erzeugt die räumliche Vordergrundmaske.
- Matting erzeugt den weichen Alphakanal für Haare, Kanten und
  halbtransparente Bereiche.
- deterministische Asset-QA prüft Dateien, Alpha-Geometrie, Bounds, Anchor und
  Kontrollkompositionen.
- der Spieler bewertet die sichtbare Figur und ihre praktische Verwendbarkeit.

Embeddings oder ein allgemeiner Full-Frame-Score dürfen keine pixelgenaue
Maske behaupten und keinen Alpha-Gate allein freigeben. Vision-Modelle liefern
versionierte Befunde mit Confidence; der `AssetReadinessService` bleibt die
deterministische Entscheidungsinstanz.

### Verbindliches Hybridziel für Figurenfreistellung

Der erste lokale Provider-Spike mit den offiziellen ComfyUI-Workflows hat
gezeigt, dass weder reine Hintergrundentfernung noch reine semantische
Segmentierung allein die benötigte Sprite-Qualität zuverlässig erreicht:

- BiRefNet erzeugt schnell einen weichen Alphakanal und erhält viele feine
  Haarbereiche, kann aber semantisch fremde, an die Figur angrenzende Objekte
  behalten und helle beziehungsweise farbige Säume erzeugen.
- Ein identischer zweiter BiRefNet-Lauf auf seinem eigenen Ergebnis gilt nicht
  als Recovery. Im Spike blieben Alpha-Verteilung und Bounds unverändert; ein
  unveränderter Wiederholungslauf darf deshalb dedupliziert werden.
- Der historische SAM3-Spike zeigte, dass ein semantisches Personen-Gate fremde
  Objekte ausschließen kann, lieferte im getesteten Workflow jedoch eine harte
  binäre Maske und verlor feine Haare beziehungsweise erzeugte Löcher. SAM3 ist
  als Meta-Modell nach `DEC-048` kein zulässiger Produktprovider; das Ergebnis
  bleibt ausschließlich ein technischer Richtungsbeleg.

Für Figuren gilt deshalb folgende technische Zielrichtung:

```text
lineage-verifizierte Non-Meta-Maske als semantisches Personen-Gate
→ Löcher schließen und kleine Maskenlücken bereinigen
→ Gate kontrolliert erweitern
→ nur den Gate-Rand weichzeichnen
→ mit dem weichen, ebenfalls policykonformen Alpha-Kandidaten multiplizieren
→ RGB-Defringe beziehungsweise Color Decontamination im Randband
→ premultiplied-alpha-sichere Normalisierung
→ AssetQA und PlayerReview
```

Die logische Referenzformel lautet:

```text
semantic_gate = feather(dilate(close(fill_holes(semantic_mask))))
final_alpha = soft_alpha * semantic_gate
```

Der noch zu qualifizierende semantische Non-Meta-Provider entscheidet damit,
**welche Region semantisch zur Figur gehören darf**; der weiche Alpha-Provider
liefert innerhalb dieses erweiterten Gates die feinere Haar- und
Kanteninformation. BiRefNet bleibt nur dann Kandidat, wenn auch seine vollständige
Weight-Lineage die globale Modellpolicy erfüllt. Feathering darf nicht das
gesamte Sprite weichzeichnen. Defringe ist ein eigener deterministischer
Teilschritt des `MattingAttempt`, da Alpha-Blur allein bereits eingelagerte helle
oder farbige Hintergrundpixel nicht entfernt.

Jeder Versuch speichert Quellbild-ID, Publisher, Base-Model-Lineage, Lizenz,
Revision und Hash beider Provider, ComfyUI-Graphhash, Objektziel, Schwelle,
Refinement Iterations, Maskenoperationen, auflösungsnormalisierte Radien,
Laufzeit und sämtliche Zwischenartefakte. Semantische Maske, weiches Alpha,
fusioniertes Alpha und Kontrollkompositionen bleiben getrennt prüfbar.

Als reine Startwerte für den nächsten 4096-Pixel-Spike gelten 24–48 Pixel
Gate-Erweiterung und 4–8 Pixel Feathering. Das sind keine Produktdefaults;
gespeichert und kalibriert werden relative Werte zur Quellauflösung. Exakte
Schwellen, Radien, Fallbacks und rollenspezifische Provider bleiben Teil von
`DEC-022`.

Der lokale historische Drei-Bild-Spike ist nur Richtungsbeleg, kein
Qualitätsbenchmark und wegen des darin verwendeten SAM3 kein Produktkandidat.
Seine Beobachtung – weiches Alpha erhält Feindetails, ein semantisches Gate
entfernt Fremdobjekte – definiert lediglich die Vergleichsaufgabe. Erst ein
vollständig Non-Meta-konformer Provider- und Fusionstest kann die Hybridrichtung
als produktionsfähig qualifizieren.

### Alpha-QA

Vor Freigabe wird das Sprite mindestens auf transparentem Checkerboard, Schwarz,
Weiß, einer gesättigten Kontrollfarbe und einem echten kompatiblen VN-Background
komponiert. Geprüft werden:

- abgeschnittene Haare, Hände, Kleidung oder Körperteile,
- Hintergrundinseln und zusätzliche verbundene Komponenten,
- transparente Löcher im Vordergrund,
- helle oder farbige Halos,
- ungewollte Schatten und Farbübersprechen der Matte,
- ausreichender Canvas-Abstand, plausible Bounds und korrekter Bodenanker,
- sowie konsistente Scale innerhalb der Sprite-Familie.

Quellbildqualität, Extraction-Qualität und normalisierte Assetqualität erhalten
getrennte Fehlercodes und Review-Evidenz. Dadurch verändern Alpha-Fehler weder
ungezielt Character-Prompts noch deren Ratings.

| Fehlerebene | Beispiele | Erlaubter nächster Schritt |
|---|---|---|
| Source | falsche Figur, falsches Outfit, unvollständiger Körper, echte Szenerie | Generation-/Prompt-Recovery |
| Extraction/Matting | Halo, fehlende Haarspitzen, Löcher, Hintergrundinseln, mitgenommene Möbel oder Requisiten, harte Maskenkante | neuer parameter- oder providerverändernder Extraction-/Matting-Attempt auf demselben Quellbild; identische Wiederholung wird dedupliziert |
| Normalisierung | falscher Scale, Bounds, Canvas oder Anchor | neuer Normalization-Attempt |
| Place-QA | verbotene Person oder Fokusfigur | maskierter Repair oder Neugenerierung laut Befund |

## Gemeinsame Blueprints und Character-spezifische Bindings

Figurenübergreifende Inhalte werden nicht sechzehnmal unabhängig erfunden. Ein
gemeinsames Blueprint hält die World- und Designregeln; eine versionierte
Character-Bindung übersetzt sie in die konkrete Figur. Dadurch bleibt etwa die
Schuluniform erkennbar dieselbe Uniform, obwohl Schnittwirkung, Layering,
Accessoires und Promptformulierung pro Figur unterschiedlich ausfallen dürfen.

```text
UniformBlueprintRevision
+ CharacterVisualCanonRevision
+ CharacterOutfitBindingRevision
→ OutfitSemanticSpec
→ character-spezifischer Prompt und GenerationRecipe
```

Der `UniformBlueprintRevision` gehören harte gemeinsame Anker wie Palette,
Wappen, Materialfamilie, erlaubte Grundvarianten, Saison- und Formalitätsregeln
sowie verbotene Abweichungen. Die `CharacterOutfitBindingRevision` hält dagegen
unter anderem Silhouette und Fit, erlaubte Blueprint-Variante, Layering,
Ärmel-/Kragenentscheidung, charaktereigene Akzente, Signaturaccessoires,
körperbezogene Formulierungen und Character-spezifische Negatives. Eine
Figurenbindung darf keinen harten Uniformanker aufheben.

Für Orte gilt dieselbe Trennung:

```text
SceneBlueprintRevision
+ optionale CharacterScenePresentationBindingRevision
→ Place Asset oder integrierter CG Contract
```

Das Scene Blueprint bindet Geometrie, Landmarken, Materialien, zulässige
Tageszeit-/Wetterkorridore, Character Safe Areas und die Personen-Policy. Eine
Character Scene Presentation Binding darf Position, Framing, Pose-Interaktion,
Lichtharmonie, Kontrast, Stimmung und zugehörige Promptgewichte für die konkrete
Figur spezifizieren, ohne den Ort selbst umzudefinieren.

Es bleiben zwei fachlich verschiedene Produktionspfade:

- Ein wiederverwendbares `PlaceAsset` wird ohne Fokusfigur und standardmäßig
  ohne Personen produziert und anschließend mit normalisierten Sprites
  komponiert.
- Ein integriertes Story-CG kompiliert Character Canon, Outfit Binding, Scene
  Blueprint und Scene Presentation Binding in ein flaches Gesamtbild. Es darf
  nicht nachträglich als universelles Place- oder Sprite-Asset gelten.

Jedes Requirement referenziert die exakten Blueprint-, Character-Canon- und
Binding-Revisionsstände. Eine neue Character Canon Revision invalidiert nicht
pauschal alle alten Assets; der Compatibility Check entscheidet pro Assetrolle,
ob ein bestehendes Asset historisch gültig bleibt, weiterverwendbar ist oder neu
produziert werden muss.

## Place-Produktion ohne Figuren

Ein `PlaceProductionContract` setzt sichtbare Hauptfiguren und standardmäßig
auch Personen auf `forbidden`. Negative Prompts sind nur eine Generierungshilfe
und kein Nachweis. Das darstellbare Bild bleibt trotzdem Teil des
Spielerreviews; `scene_or_background_wrong`, `extra_or_missing_person` und
weitere Gründe erfassen den Fehlschlag. Vision Analysis prüft anschließend
Personen, Gesichter und dominante figurähnliche Silhouetten; ein Befund kann die
finale Place-Readiness blockieren und abhängig vom Fehler zu maskiertem Repair
oder Neugenerierung führen, aber nicht rückwirkend das Spielerurteil ersetzen.
Kleine Statisten sind nur mit einer expliziten authored Policy zulässig.

Places benötigen keinen Alphakanal, aber eine charaktergeeignete Safe Area.
Story-CGs bleiben flache Gesamtbilder und dürfen weder als sauberer Place noch
als universeller Sprite umgedeutet werden.

Die reine Background-Bewertung benötigt eine eigene, noch zu konkretisierende
Spielerlinie. Fest steht bereits: Ein personenfreier Place-Output erzeugt keine
`CardIdentity` und keine Character-Champion-Eignung. Seine Bewertung muss
Scene-Intent, tatsächlichen Ort, Style-Konsistenz, Personenfreiheit, Safe Areas,
Auflösung, Anschlussfähigkeit und technische Backgroundfehler getrennt
erfassen. Ob dafür der Arbeitsmodus `Place Trial` bestehen bleibt und welche
Dispositionen beziehungsweise Vergleichsstufen er sichtbar verwendet, wird
erst nach dem M6-Lernbeweis in einem eigenen Background-Spike entschieden.

## Vier unabhängige Scene Gates

```text
SceneUnlockContract
├─ focus_character_id
├─ CalendarGate
├─ SceneAssetGate
├─ FocusCharacterPlayGate
├─ RelationshipKnowledgeGates[]
└─ EnsembleDevelopmentGate mit ParticipantRequirements[]
```

- `CalendarGate` prüft authored Zeit und Vorgängerszenen.
- `SceneAssetGate` produziert ausschließlich Material der unmittelbar
  kommenden Szene und läuft ohne feste Rundengrenze bis zur Vollständigkeit.
- `FocusCharacterPlayGate` ist nur im Bootstrap ohne challengefähige Grundlage
  `0`. Jedes reguläre Focus-Character-VN-Fenster verlangt abhängig von Scene
  Contract und Character-Confidence mindestens eine und höchstens drei aktuelle
  characterbezogene Challenge-Runden. Pflicht- und freiwillige Trials teilen
  ein hartes Maximum von drei. Asset-Build-Runden zählen nicht.
- `EnsembleDevelopmentGate` prüft konkrete authored Milestones benötigter
  Supporting Characters.

Die Bootstrap-Ausnahme endet, sobald eine challengefähige Grundlage existiert.
Danach verlangt auch ein Routine-Schritt mindestens eine Runde; neue
Assetrollen, geringe Confidence oder eine neue Profilrevision dürfen die
Anforderung bis auf drei konkrete Trials erhöhen. Der vollständige Profil-,
Confidence- und Trial-Vertrag steht in
[`10-generation-profiles-and-trials.md`](generation-profiles-and-trials.md).

## Questpool

Der seit Foundation M6.5 implementierte Sechser-Vorrat ist ein rollierendes
Ready-Fenster und keine Gesamtbildgrenze. Der Scheduler hält pro **bekannter
Figur** sechs normale, vollständig gerenderte Vierer-Games sowie für
jede aktive sensible Inhaltseinstellung ein zusätzliches eigenes Vierer-Game
bereit. Ihre Foki rotieren zwischen Scene Asset, Identity/Stability,
Outfit/Pose/Expression/Scene, Auswahl/Champion, Recovery/Cleanup und
Experiment/Coverage/Continuity. Ein aus bereits vorhandenen Kandidaten gebauter
16er-Cup darf zusätzlich `READY` sein, weil er keine vier neuen Bilder rendert.

Der Trial-/Evidenzvertrag, die noch zu prüfende Bestandsliste von Modusnamen,
die Ready-Mengen, Inhalts-Scope-Trennung und die zweite bildweise
Begründungsrunde stehen in
[`11-game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md).

Ein Ready-Slot bindet einen `GameMode` an einen fachlich getrennten
`GenerationFocus`. Der Modus beschreibt die Spieleraktion; der Fokus beschreibt
Expected Composition, Primary Question, Locked/Varied Axes, Evidence Scope und
Recovery-Autorität. Jede generierende Quest besitzt genau einen primären Fokus.
K.-o.-, Cleanup- und Dataset-Auswahlspiele auf vorhandenen Bildern besitzen
stattdessen nur einen Evaluation Focus.

Assetgate und Playgate sind getrennt:

- Assetgate baut das Scene Visual Manifest.
- Playgate challengt eine aktuelle Qualitätsannahme der Fokusfigur.
- Globale oder fremde Character-Challenges erfüllen das Playgate nicht.
- Pro Fokusfigur und VN Progress Window werden insgesamt höchstens drei
  Pflicht- und freiwillige Playgate-Runden angerechnet.
- Credits sind an State Revision und Window gebunden und nicht hortbar.

### Quest-Credit-Vertrag

Nicht der verwendete Game Mode entscheidet über Fortschritt. Vor dem Start
einer anrechenbaren Runde erzeugt der Server eine gebundene Quest-Instanz mit
mindestens:

```text
QuestCreditContract
├─ quest_id
├─ progress_scope: character | place | style | scene | global
├─ target_id oder null
├─ credit_type: visual_development | playgate | assetgate | research
├─ credit_value
├─ credit_cap
├─ eligible_state_revision
├─ rules_snapshot
└─ optional story_contract_id
```

Der Contract wird nach vollständigem Questabschluss höchstens einmal
angerechnet. Öffnen, Abbrechen, Resultansicht oder nachträgliches Umsortieren
erzeugen keinen Credit. Assetgate-Runden, freie technische Vergleiche,
Place-Aufgaben, Resultprojektionen, Cleanup-Entscheidungen und freie
Advanced-Workshop-Versuche erfüllen ohne passenden Character- und
Playgate-Contract kein
`FocusCharacterPlayGate`. Ein Reject innerhalb einer regulär abschließbaren
Runde verhindert den Credit nicht automatisch; maßgeblich ist der authored
Abschlussvertrag der Quest.

Zum vollständigen Questabschluss gehört bei einem normalen Viererreview nach
den vier Standardbewertungen eine zweite Runde. Jedes nicht übersprungene Bild
wird erneut einzeln groß gezeigt und über kontextuell zulässige positive und
negative Reason Chips begründet. Gründe werden nie pauschal für alle vier
Bilder erfasst. Die serverseitige Evidence-Projektion darf Batcheffekte erst aus
den vier bildbezogenen Ereignissen ableiten.

Ein Reject erzeugt bereits in Pass 1 negative Evidence und eine deduplizierte
Cleanup-Referral `awaiting_guided_evidence`, aber noch keinen spielbaren
Delete-or-Live-Eintrag. Erst die Begründung desselben Bildes aktiviert `ready`;
Undo davor setzt die Referral append-only auf `void`. Delete or Live konsumiert
die gespeicherten Gründe ohne erneute Abfrage.

Die Gründe bleiben auf fünf unabhängigen Ebenen getrennt:

- `generation_intent`: Auftrag oder verlangte Zusammensetzung getroffen,
- `visual_defect`: sichtbarer Generierungs- oder Renderfehler,
- `character_canon`: Identity beziehungsweise Character Drift,
- `asset_usability`: Verwendbarkeit für Crop, Sprite, Place oder andere Rolle,
- `aesthetic_preference`: persönlicher Geschmack bei ansonsten möglicher
  Korrektheit.

Ein Bild darf auf mehreren Ebenen gleichzeitig positive und negative Evidence
erzeugen. Ein falscher Scene-Inhalt, ein defekt gerenderter richtiger Background
und ein sauberer, aber nicht bevorzugter Background sind verschiedene Gründe
und dürfen nicht dieselbe Recovery auslösen.

## Kandidaten und Champions

### Championtitel und Assetquellen

Der vollständige fachliche Vertrag für benannte Champion-Slots,
Comparison Contexts, Bildmehrfachverwendung, getrennte Titel-/Mastery-/Asset-
Zustände, Bildkartensammlung, Titelübersicht und Signature Champion steht in
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md).
Die folgenden Cup- und Gate-Regeln gelten jeweils innerhalb genau eines solchen
Slots und seiner aktuellen Vertragsrevision. Ein opaker Challenge Context Hash
ist nur technischer Integritätsschlüssel und ersetzt diesen Vertrag nicht.

Championtitel und Assetproduktion sind getrennte Verträge. Ein Slot-Cup kürt
eine bereits existierende Bildkarte für einen sichtbaren Titel. Eine
`AssetSourceSelection` wählt dagegen ein Bild als Quelle für genau einen
`AssetProductionContract`. Sie darf dieselbe Karte referenzieren, erzeugt aber
keinen Championtitel. Umgekehrt ist ein Championtitel weder technische
Assetfreigabe noch allgemeine Pflicht für die Produktion eines blockierenden
Assets.

### Eigenständiger Lifecycle abgeleiteter VN-Assets

Keep-, Favorite- und Championstatus machen ein Bild zu einer zulässigen Quelle,
nicht zum fertigen Asset. Aus einer bestätigten `AssetSourceSelection` erzeugt
der Freistellungsworkflow ein neues abgeleitetes Bildartefakt mit eigener
`DerivedAssetImageIdentity`. Dieses Artefakt besitzt seine vollständige
Processing- und Source-Lineage, lebt fachlich aber unabhängig von der
ursprünglichen Bildkarte:

```text
ImageIdentity mit Keep | Favorite | Champion
→ AssetSourceSelection für genau einen AssetProductionContract
→ Extraction-/Matting-/NormalizationAttempts
→ DerivedAssetImageIdentity
→ PlayerAssetReview
→ AssetVersion APPROVED
→ ScenePresentationBindings[1..n]
```

Eine `DerivedAssetImageIdentity`:

- erzeugt keine `CardIdentity`, kein Image Branding und keine Battler-Traits,
- nimmt an keinem Booster, Challenger-Pool, Cup, Title Match oder Delete-or-Live-
  Lifecycle teil,
- ist kein LoRA-Dataset-Candidate und erzeugt keine Dataset-Coverage,
- übernimmt weder Disposition noch Favorite-/Championstatus des Quellbilds,
- und darf als immutable `AssetVersion` gleichzeitig in beliebig vielen
  kompatiblen Scene Presentation Manifests referenziert werden.

Der Asset-Lifecycle wirkt auch in Gegenrichtung nicht auf die Karte zurück. Ein
abgelehntes Matting oder eine ersetzte AssetVersion verändert weder Keep,
Favorite, Champion noch die LoRA-Eignung des ursprünglichen Bildes. Nach
materialisierter Ableitung bleiben AssetVersion und ihre gespeicherte
Provenienz selbst dann erhalten, wenn die ursprüngliche Kartenbindung später
verloren geht oder gelöscht wird. Eine solche Kartenlöschung darf weder eine
laufende noch eine historische VN-Szene beschädigen.

### Expression-Familien aus einem stabilen Basissprite

Ein freigestellter Sprite zeigt zunächst genau die Pose, das Outfit und den
Ausdruck seines abgeleiteten Bildartefakts. Unterschiedliche VN-Ausdrücke dürfen
nicht durch ungebundene vollständige Neugenerierungen entstehen. Der spätere
Produktionsvertrag benötigt deshalb mindestens folgende Hierarchie:

```text
CharacterVisualCanonRevision
└─ CharacterOutfitBindingRevision
   └─ SpriteBaseVersion mit Pose, Canvas, Scale und Anchors
      └─ ExpressionVariantVersion[]
         └─ zusammengesetzte und geprüfte SpritePresentationVersion
```

Jede Expression-Variante muss dieselbe Character-, Outfit-, Pose-, Canvas- und
Anchor-Bindung behalten, eine eigene Processing-Lineage besitzen und erneut
technische sowie sichtbare Asset-QA bestehen. Auch diese Varianten bleiben
reine VN-Assets ohne Karten- oder LoRA-Lifecycle.

Verbindlich ist die Nicht-Drift-Grenze; die konkrete ComfyUI-Pipeline bleibt bis
nach dem abgeschlossenen M6-Lernloop technischer Spike. Verglichen werden
mindestens Face-only-Inpainting mit unveränderten Außenpixeln, ein ausgerichteter
Kopf-/Gesichtslayer und eine referenzgebundene vollständige Regeneration als
Fallback. Der Spike bestimmt Masken, Denoise, Provider, QA-Schwellen,
Fehlerbilder und den frühesten Zustand, ab dem eine belastbare
Expression-Familie materialisiert werden darf.

Der logische Core-Game-Batch bleibt im vollständigen MVP ein fester
Vierervergleich.
Vier bezeichnet die Spiel- und Evidenzeinheit, nicht die technische
GPU-Parallelität. Renderjobs dürfen abhängig von Hardware und Scheduler einzeln
oder parallel laufen. Sonderversuche mit anderer Samplezahl sind zulässig,
erfüllen aber ohne ausdrücklichen Rules-Vertrag keinen normalen Character-,
Asset- oder Playgate-Batch.

Für einen titelgebundenen ChampionSlot laufen Viererbatches so lange, bis für
die konkrete Challenge sechzehn mit Keep
oder Favorite bewertete, transportgültige und aktuell rosterfähige Kandidaten
verfügbar sind. Das Eligibility-Ereignis des sechzehnten Kandidaten friert
atomar die ersten sechzehn noch keinem Cup zugewiesenen Einträge in stabiler
Ereignisreihenfolge ein. Diese bestimmt die Bracketplätze; spätere Kandidaten
warten auf den nächsten Cup. Das 16er-Spiel wird als Pflichtquest `READY`
bereitgestellt.
Die aktuelle Reviewinteraktion wird nicht zwangsweise verlassen. Eine
ausdrücklich titelgebundene Voraussetzung bleibt bis zum Abschluss der
Pflichtquest offen. Der 16er-Bracket besteht aus direkten A/B-Vergleichen und
reduziert das Feld `16 → 8 → 4 → 2 → 1`. Ein SceneAssetGate darf aus dem
Champion-Cup allein keine Produktionsfreigabe ableiten.
Ohne bestehenden Champion wird der letzte Teilnehmer unabhängig von seiner
ursprünglichen Reviewaction erster Champion. Mit Amtsinhaber wird er Challenger
und tritt in einem zusätzlichen direkten Title Match gegen den Champion an.

Jede bindende Eliminationsniederlage eines Favorites zählt unabhängig von
Runtimefamilie, Oberfläche oder Turniername in dieselbe Verlustserie. Nach der
ersten und zweiten Niederlage in Folge bleibt es mit Bestandsschutz im
Challenger-Pool, pausiert aber jeweils für genau
einen `ChampionCycleCooldown`: einen vollständigen Challenger-Cup bis zum
nächsten Title Match, identisch zur Wartephase des amtierenden Champions. Die
Sperre wächst nicht. Die dritte Niederlage in Folge verweist auch das Favorite
an Delete or Live. Jeder bindende Eliminationssieg setzt den aktuellen
Verlustfolgezähler auf null, ohne die historischen Matchereignisse zu entfernen.
Gleichstand, Skip, Abbruch und `nicht vergleichbar` zählen nicht. Ein Keep wird
bereits nach seiner ersten bindenden Eliminationsniederlage dorthin verwiesen.
Verliert ein Bild dort,
wird sein Dateipaar gelöscht; gewinnt es, kehrt es mit unveränderter
Reviewaction erst für ein späteres 16er-Turnier in den Pool zurück. Bei einem
Favorite setzt `Live` die aktuelle Verlustserie und den Cooldown auf null,
erhält `favorite` und erzeugt ein neues Eligibility-Ereignis.
Der laufende Bracket wird niemals nachträglich aufgefüllt oder verändert.

Ein im Title Match unterlegener Challenger folgt seiner Keep-/Favorite-Regel.
Ein abgelöster Amtsinhaber bleibt als geschützter `former_champion` im Pool und
geht nicht unmittelbar in DOA. Gleichstand oder Abbruch erhalten den
Amtsinhaber und lassen die Pflichtquest offen.

Jeder bindend entschiedene Eliminationsvergleich liefert neben einem möglichen
Turnierfortschritt kontextgebundene Pairwise-Quality-Evidence: Gewinner,
Verlierer, Mode Revision, optionale Runde,
Bewertungsachse und Challenge-Kontext werden persistiert und getrennt auf beide
Bilder projiziert.

Ein unverändertes Bild darf über getrennte
`ImageContextQualification`s mehreren kompatiblen Slots und Bewertungsfragen
zugeordnet werden. Innerhalb eines Pools und Brackets zählt es höchstens einmal;
eine Observation für Frage A beantwortet Frage B nicht automatisch. Ein
16er-Roster besteht immer aus sechzehn unterschiedlichen Bildern.

Ein AssetProductionContract darf aus kontextkompatiblen Keep-, Favorite- oder
Championkarten eine Quelle wählen. Das kann direkt erfolgen, wenn der
Requirement-Vertrag eine eindeutige bereits akzeptierte Quelle besitzt, oder
über ein eigenes A/B-Auswahlspiel mit `evaluation_focus_id =
asset_source_selection`. Ein solches Bracket darf dieselbe Interaktionsform und
bereits vorhandene Human Evidence nutzen, schreibt aber
`AssetSourceSelection` statt `ChampionRevision`. Quellbindung, jede technische
Ableitung und jede QA-Prüfung werden als getrennte Revisionen persistiert.

Für ein `blocking` Scene Requirement gibt es kein Produktionsrundenlimit. Fehlt
eine akzeptierte Assetquelle oder scheitert deren Ableitung beziehungsweise
abschließende technische oder fachliche Validierung, bleibt das SceneAssetGate
offen. Weitere Viererbatches, Recovery, neue Quellenauswahl und technische
Ableitungen laufen so oft wie nötig, bis eine `APPROVED` AssetVersion vorliegt.
Diese Runden verbrauchen kein FocusCharacterPlayGate-Budget.

Eine fehlgeschlagene Ableitung verändert weder die unveränderliche Bildkarte
noch ihre Keep-/Favorite-Bewertung, Challenger-Eignung oder vorhandenen
Championtitel. Sie belegt ausschließlich, dass dieser AssetAttempt für den
gebundenen Produktionsvertrag nicht erfolgreich war.

Kein Kandidat in einem Viererbatch ist kein Fehler des Spielers. Die Runde
liefert negative Evidenz und wird mit einer zulässigen Recovery- oder
Variationsentscheidung fortgesetzt. Werden in den ersten sechzehn Bildern null
Kandidaten bestätigt, beginnt ein neuer vollständiger Zyklus mit weiteren
sechzehn Bildern. Die Evidence des gescheiterten Zyklus bleibt erhalten und
autorisiert ausschließlich die im Contract vorgesehenen deterministischen
Recovery-Mutationen des neuen Zyklus.

## Readiness- und Blockerprojektion

Der Server liefert jeden Gate Check einzeln. Ein Blocker nennt:

- das fehlende Asset oder die fehlende Figur,
- den konkreten Requirement- beziehungsweise Milestone-Identifier,
- eine verständliche diegetische Erklärung,
- und einen direkten Link zum erreichbaren Progressionspfad.

Der Story-Abhängigkeitsgraph wird vor Auslieferung auf Zyklen und zeitlich
unerreichbare Requirements validiert.

## Mehrfigurenbilder

Mehrfigurenbilder und ihre gemeinsamen ChampionSlots gehören einem
Relationship-, Ensemble- oder Scene-Portfolio mit kanonischem Participant Set.
Sie werden in Character-Ansichten nur projiziert und nicht pro Figur dupliziert.
Der übergeordnete Vertrag steht in
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md).

Normale VN-Szenen bevorzugen getrennte freigestellte Sprites vor einem
wiederverwendbaren Hintergrund. Für echte Ensemble- und Story-CGs benötigt ein
späterer Slice einen expliziten `MultiCharacterCompositionContract`. Er muss
Identity Bleeding verhindern und mindestens festlegen:

- sichtbare Character Slots und räumliche Bindungen,
- zulässige LoRA-/Referenzkombinationen,
- regionale beziehungsweise maskierte Conditioning-Schritte,
- Reihenfolge für Inpainting oder Harmonisierung,
- Character-spezifische QA pro Slot,
- sowie Fallback auf komponierte Einzelassets.

Ein flaches Gruppenbild darf nicht als gültig gelten, wenn nur die globale
Bildqualität stimmt, aber eine beteiligte Figur ihre Identität verliert.

## Testbare Invarianten

1. Fertige Assets bei noch offenen authored Pflicht-Trials lassen die
   Fokus-Szene gesperrt; `required_trials = 0` ist ausschließlich im Bootstrap
   ohne challengefähige Grundlage zulässig.
2. Playgate ohne fertige Pflichtassets lässt dieselbe Szene gesperrt.
3. Eine Supporting Figure mit fehlendem Milestone blockiert trotz fertiger
   Assets und erfülltem Fokus-Playgate.
4. Nach Erfüllung des letzten echten Blockers wird dieselbe Szene ohne
   künstliche Zusatzrunde freigeschaltet.
5. Asset-Build-Runden verbrauchen kein Playgate-Budget.
6. Ein globaler Render Trial erfüllt kein Character-Playgate.
7. Reload rekonstruiert Kandidatenpool, Bracket, Credits und Scene Bindings.
8. Ein Extraction-Fehler bei gültigem Quellbild startet keine neue Generation.
9. Ein Sprite ohne echten, geprüften Alphakanal erfüllt kein Sprite-Requirement.
10. Ein Place mit verbotener Figurenpräsenz erfüllt trotz positivem
    Spielerurteil kein Place-Requirement.
11. Ein Vision- oder Embedding-Score allein setzt keinen Readiness-Status.
12. Pflicht- und freiwillige Character-Trials überschreiten zusammen nie drei
    Runden pro Fokusfigur und VN Progress Window.
13. Ein blockierendes Requirement ohne akzeptierte AssetSourceSelection und
    validierte `APPROVED AssetVersion` hält das SceneAssetGate unabhängig von
    Kartenbewertung, Championtitel und bisheriger Rundenzahl offen.
14. Jeder sichere, dekodierbare und nicht exakt duplizierte Generationsoutput
    erreicht das Player Generation Review unabhängig von semantischer Qualität.
15. Vision-, Identity-, Artstyle-, Anatomy-, Outfit-, Scene- und
    Backgroundbefunde dürfen die spätere Readiness blockieren, aber keinen
    darstellbaren Output vor dem Bildspiel verbergen.
16. Keep und Favorite sind Challenger-Pool-Kandidaten; die stärkere
    Favorite-Evidenz verleiht begrenzten Bestandsschutz nach einer bindenden
    Eliminationsniederlage, aber keinen automatischen Matchsieg.
17. Ein bindend unterlegenes Keep wird dedupliziert an Delete or Live verwiesen.
    `Live` reaktiviert es unverändert erst für ein späteres Turnier, `Delete`
    entfernt das Dateipaar; der laufende Bracket bleibt eingefroren.
18. Die Schwelle von sechzehn friert den Roster eines ChampionSlots ein und
    erzeugt eine Pflichtquest, aber keine erzwungene Navigation aus einem
    laufenden Review. Nur ein ausdrücklich titelgebundenes Gate bleibt bis zum
    Questabschluss geschlossen; ein SceneAssetGate benötigt weiterhin seine
    eigene Source Selection und Asset-QA.
    Der Cut verwendet atomar die ersten sechzehn rosterfähigen Eligibility-
    Ereignisse; spätere Einträge warten ohne Score- oder Spielerkuration auf den
    nächsten Cup.
19. Jede bindende Eliminationsniederlage eines Favorites zählt mode-unabhängig
    in dieselbe Serie. Es pausiert nach Verlust eins und zwei jeweils für denselben
    vollständigen Challenger-Cup wie der amtierende Champion; Verlust drei in
    Folge erzeugt eine deduplizierte Delete-or-Live-Referral. `Live` erhält es
    als Favorite, setzt Verlustserie und Cooldown auf null und erzeugt ein neues
    Eligibility-Ereignis. Kein gerettetes Bild darf in dasselbe Bracket
    zurückkehren. Jeder bindende Eliminationssieg setzt den Verlustfolgezähler
    auf null, nicht die historische Evidenz; Gleichstand, Skip, Abbruch und
    `nicht vergleichbar` zählen nicht.
20. Der Challenger-Verlierer eines Title Matches folgt seiner Keep-/Favorite-
    Verlustregel. Ein abgelöster Champion bleibt als `former_champion` geschützt
    im Pool; Gleichstand oder Abbruch erhalten den Amtsinhaber.
21. Jeder aufgelöste bindende Eliminationsvergleich erzeugt kontextgebundene
    positive Gewinner- und
    negative Verlierer-Evidenz; Bracketfortschritt allein ersetzt diese
    persistierte Pairwise-Evidence nicht.
22. AssetSourceSelection und ChampionRevision sind getrennte Records und dürfen
    nicht durch denselben untypisierten `asset_champion_selection`-Ausgang
    materialisiert werden.
23. Ein fehlgeschlagener AssetAttempt verändert weder Bildkartenidentität,
    Review-Disposition noch Championtitel.
24. Eine abgeleitete `DerivedAssetImageIdentity` erzeugt weder CardIdentity noch
    Challenger-, Champion-, Delete-or-Live- oder LoRA-Dataset-Eignung.
25. Kartenverlust oder Kartenlöschung entfernt keine bereits materialisierte
    AssetVersion und beschädigt keine laufende oder historische VN-Bindung.
26. Dieselbe immutable AssetVersion darf gleichzeitig von mehreren kompatiblen
    Scene Presentation Manifests verwendet werden.
27. Eine Expression-Variante darf außerhalb ihres versionierten
    Ausdruckskorridors weder Outfit, Pose, Canvas, Anchor noch Character Canon
    verändern.

## Noch zu kalibrieren

- Readiness-Schwellen pro Assetrolle,
- konkrete reguläre Pflichtzahl `1..3` nach Scene-Klasse und
  Character-Confidence,
- Quest-Prewarm- und Backpressure-Budget,
- Mutationsstärken und Eskalationsschwellen für den bereits entschiedenen neuen
  vollständigen 16er-Zyklus nach null Candidates,
- LoRA-Gate gegenüber frühem Referenzworkflow,
- konkrete Vision-, Segmentierungs- und Matting-Provider,
- rollenspezifische Alpha-, Confidence- und Kontrastschwellen,
- konkrete Background-Spieloberfläche, Dispositionen und Place-Vergleiche,
- ComfyUI-Workflow, Maskenstrategie und QA-Schwellen für Expression-Familien,
- und genaue technische Pipeline für mehrfigurige Story-CGs.
