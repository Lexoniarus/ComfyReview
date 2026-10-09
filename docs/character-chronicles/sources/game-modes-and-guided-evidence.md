# Spielmodi, Questvorrat und geführte Bild-Evidenz

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `MIXED_GAME_DESIGN_AND_M6_HISTORY`  
**Worum es geht:** Bildspielmodi, Qualifier, Arena, Cup, Aufgaben und damalige M6-Evidence-Gates.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../vision/README.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 10. September 2026

## Zweck

Dieses Dokument ist der autoritative Vertrag für Trial-Bindung, Bild-Evidenz
und den gemeinsamen Lernloop. Es konkretisiert, wie viele bereits gerenderte
Spiele pro bekannter Figur bereitstehen, wie ihre Foki rotieren, wann ein
16er-K.-o.-Spiel entsteht und wie aus jeder Viererbewertung strukturierte
Evidenz für den nächsten Generierungsbatch wird.

Die vorgelagerten Modi Vierer-Qualifier, Vierer-Ranking, Arena und
`ten_point_calibration` sind fachlich entschieden. 16er-Cup/Title Match und
Delete or Live bleiben nachgelagerte Modi. Der Beschreibungstest ist ein davon
getrenntes Auswahlspiel auf bereits behaltenen Bildkarten. Frühere Namen wie
Weakest Link sowie Legacy-/Technikrouten sind keine zusätzlichen Spielmodi.

Die Modi sind keine lose Sammlung technischer Bestandsrouten. Jede Quest besitzt einen
serverseitigen `QuestContract`, eine konkrete offene Frage und einen eng
begrenzten Evidenz-Scope. Weder UI noch LLM wählen nachträglich aus, wofür ein
Ergebnis Credit erhält.

Die vollständige Backendbindung bleibt auch dann erhalten, wenn die normale UI
nur Kartenauftrag, sichtbare Bewertungsfrage und Spielerhandlung zeigt. Die
Spielvariante erklärt die Interaktion, der ChampionSlot den Vergleichs- und
Titelkontext und der Generation-/Evaluation Focus die intern erhobene
Information. Keiner dieser Verträge ist die Bildkarte selbst. Die verbindliche
Ebenentrennung steht in
[`player-facing-terminology-and-voice.md`](player-facing-terminology-and-voice.md).

### Grenze des M6-Spielkerns

Die M6-Modi bewerten ausschließlich generierte Quellbilder und führen die
daraus gelernte Prompt-/Recipe-Änderung wieder in eine neue Bildgeneration.
Ein Keep, Favorite oder Champion wird innerhalb von M6 weder freigestellt noch
normalisiert und erhält dort keine `AssetSourceSelection` oder `AssetVersion`.
Asset-Auswahl, Sprite-/Alpha-QA, Expression- und Place-Abläufe sind
nachgelagerte Anwendungen derselben Runtimefamilien ab Chronicle Slice 3. Ihre
Erwähnung in diesem Zielkatalog reserviert den späteren Interaktionsvertrag,
erweitert aber nicht den M6-Abnahmeumfang.

## Bereiter Questvorrat pro bekannter Figur

### Ten-Point Calibration

`ten_point_calibration` ist der vierte vorgelagerte Modus und darf höchstens
einen der sechs normalen Supply-Slots einer Campaign belegen. Jedes Bild wird
einmal disponiert. Favorite schreibt deterministisch den absoluten
Bildqualitätsscore 10, Keep den Score 7. Nur Reject fragt zusätzlich einen frei
wählbaren Score von 1 bis 10 sowie einen negativen Primary Reason ab; Secondary
Reasons bleiben optional. Ein hoher Reject-Score ist zulässig, weil der Score
allgemeine Bildqualität und der Reason die kontextuelle Untauglichkeit misst.

Nur Favorite und Keep überspringen in diesem Modus die Reason-Runde. Qualifier,
Vierer-Ranking und Arena behalten ihre vollständige Reason-Pflicht. Score,
Disposition, relative Präferenz und Reasons werden getrennt gespeichert und
dürfen sich nicht gegenseitig vervielfachen.

Für **jede bekannte Figur** hält der Supply Scheduler höchstens sechs normale,
vollständig gerenderte Vierer-Games bereit. Zusätzlich existiert für **jede
aktive sensible beziehungsweise NSFW-Inhaltseinstellung** genau ein eigener
bereiter Viererbatch dieser Figur.

Der Registryumfang ist entschieden: Neben `standard` existieren exakt vier
getrennte sensible Spielvarianten `sexy`, `lewd`, `nude` und `explicit`. Sind
alle vier freigeschaltet, kann eine Figur damit höchstens sechs normale plus
vier sensible Ready-Games besitzen. Die Stufen bleiben getrennte Scopes und
werden nicht zu einem gemeinsamen „NSFW“-Pool zusammengezogen.

```text
ReadyCharacterSupply
├─ normal_games: 0..6 mit jeweils 4/4 lokal verfügbaren Bildern
├─ content_setting_games[active_setting_id]: 0..1 mit jeweils 4/4 Bildern
└─ ready_tournaments[]: nur aus bereits qualifizierten Kandidaten
```

Ein Game ist erst `READY`, wenn Quest Contract, Recipe Snapshots und alle vier
Bilddateien vollständig validiert und lokal vorhanden sind. Ein 16er-K.-o.-Cup
verwendet dagegen bereits vorhandene Kandidaten und erzeugt keinen weiteren
Viererbatch. Er darf daher zusätzlich zum gerenderten Vorrat als Pflicht- oder
Challenge-Quest erscheinen, ohne das Renderbudget zu vervielfachen.

Bei sechzehn bekannten Figuren entspricht ein vollständig vorgewärmter normaler
Vorrat bis zu `16 × 6 × 4 = 384` Bildern. Jede aktive sensible Inhaltsstufe
ergänzt bis zu `16 × 1 × 4 = 64` Bilder. Diese Menge ist eine bewusste Folge des
figurenbezogenen Systems und kein globaler Pool, den nur die aktuelle Fokusfigur
besitzt.

Sensible Inhaltsstufen besitzen getrennte Candidate Pools, Ratings, Champions,
Fehlercluster und Recipe Confidence. Wegen des Schulsettings sind sie nur unter
einem harten Erwachsenen-, Policy- und Save-Gate aktivierbar. Eine Freigabe
wirkt nie rückwirkend auf bereits anders klassifizierte Evidenz.

## Game Mode und Generation Focus sind getrennte Achsen

Der `GameMode` beschreibt die Interaktion des Spielers. Der
`GenerationFocus` beschreibt dagegen die kontrollierte Frage an die
Bildgenerierung. Beide werden erst durch eine konkrete Questinstanz verbunden.

Beispiele:

- `Vierer-Qualifier + outfit_binding`,
- `Stability Trial + identity_canon`,
- `Arena + sampler_scheduler`,
- `Error Hunt + anatomy_recovery`,
- `Sprite / Alpha QA + matting_quality`,
- `Efficiency Run + generation_time`,
- `16er-K.-o.-Cup + slot_title_selection` ohne neue Generation,
- Asset-Auswahlspiel + `asset_source_selection` ohne Championwirkung,
- Beschreibungstest + `description_match_validation` ohne Kartenwertung.

Jede **generierende** Quest besitzt genau einen primären Generation Focus. Sie
darf viele allgemeine Fehler sichtbar machen, aber nur die deklarierte
Variationsachse erhält kausalen Credit. Auswahlspiele wie 16er-Cup, Dataset
Draft, Clone Hunt, Beschreibungstest oder Delete or Live verwenden vorhandene Bilder und besitzen
deshalb keinen neuen Generation Focus; sie deklarieren stattdessen genau einen
`EvaluationFocus`.

Der implementierte Bezeichner `asset_champion_selection` ist ab diesem Vertrag
ein Legacy-/Migrationsname. Für einen Slottitel lautet die Zielsemantik
`slot_title_selection`; für die Auswahl einer Produktionsquelle
`asset_source_selection`. Der Legacyname darf weder beide Ergebnisse zugleich
autorisieren noch im normalen Frontend erscheinen.

```text
QuestExperimentContract
├─ game_mode_id
├─ generation_focus_id oder null
├─ evaluation_focus_id
├─ primary_question
├─ expected_composition_manifest
├─ locked_axes[]
├─ varied_axes[]
├─ applicable_review_layers[]
├─ evidence_scope
├─ recovery_routes[]
├─ candidate_pool_id
├─ content_setting_id oder null
└─ recipe_snapshot_ids[]
```

Der `expected_composition_manifest` hält, was erzeugt werden sollte. Erst dieser
Sollzustand erlaubt die saubere Unterscheidung zwischen einem verfehlten Auftrag
und einem technisch kaputten Versuch, den richtigen Auftrag umzusetzen.

Für jede spielbare Quest gilt zusätzlich ein harter Kompositionsvertrag:

- Eine generierende Quest bindet genau einen `generation_focus_id`, keinen
  `evaluation_focus_id`, mindestens einen neuen Challenger und höchstens drei
  übernommene Bilder.
- Ein reines Auswahl-, Requalifikations-, Kalibrierungs- oder
  Reproduzierbarkeitsspiel bindet keinen `generation_focus_id`, sondern genau
  einen `evaluation_focus_id`. Nur dieser Vertrag darf vier bereits vorhandene
  Bilder ohne neue Generierung materialisieren.
- Eine Mode-Änderung oder ein Rebind ändert den persistierten Versuchszweck
  nicht nachträglich. Soll sich der Zweck ändern, entsteht ein neuer expliziter
  Experimentvertrag mit eigener Lineage.
- Die identische Viererbesetzung darf in einer normalen Folgequest nicht erneut
  antreten. Eine ausdrücklich markierte Kalibrierungs- oder Reproduktionsprobe
  ist die einzige Ausnahme.

## Rotation der sechs normalen Generation Foci

Sechs Slots bedeuten weder sechs dauerhaft fest verdrahtete Modusnamen noch
sechs Varianten derselben Hypothese. Der deterministische Scheduler rotiert pro
Figur den aktuell nützlichsten Generation beziehungsweise Evaluation Focus aus
folgenden Funktionsgruppen:

1. nächste Scene-Assetproduktion,
2. Identity und Stabilität,
3. Outfit, Pose, Expression oder Scene Discovery,
4. technisches Generationsprofil, Sampler, Workflow oder Laufzeit,
5. Fehlerdiagnose und Recovery des wichtigsten aktuellen Fehlerclusters,
6. Coverage, Kontinuität, Exploration oder Champion Challenge.

Die Auswahl berücksichtigt Storybedarf, offene Dataset-Lücken, Candidate- und
Championstatus, wiederkehrende Fehler, Confidence, letzte Nutzung,
Generierungszeit und erwarteten Informationsgewinn. Zwei normale Ready-Slots
dürfen nicht dieselbe Kombination aus Focus Family und Hypothese testen. Eine
authored Ausnahme ist nur für parallele, unterschiedlich gebundene Requirements
eines blockierenden SceneAssetGate zulässig und bleibt im Contract sichtbar.

Die Rotation priorisiert zuerst blockierende Scene Requirements, dann frische
Recovery aus bestätigter Evidence, niedrige oder veraltete Confidence,
Dataset-/Continuity-Lücken, fällige Champion- beziehungsweise Qualifier-Pfade
und schließlich Exploration oder Effizienz. Fairness, Cooldowns und ein
Mindestanteil nicht blockierender Foki verhindern dauerhaftes Verhungern einer
Kategorie. Die Auswahl bleibt reproduzierbare Codeentscheidung. Ein LLM darf
eine schema-valide Challenger-Hypothese
formulieren, aber weder Questpriorität noch Credit, Rating oder Promotion
bestimmen.

Der Vorrat ist vom `FocusCharacterPlayGate` zu unterscheiden. Bis zu sechs
Games dürfen gleichzeitig spielbereit sein; pro `VNProgressWindow` werden
trotzdem nur die authored regulären `1..3` Character-Trials angerechnet. Nur
der Bootstrap ohne challengefähige Grundlage besitzt `0`; Assetgate-Runden
bleiben unbegrenzt und verbrauchen dieses Budget nicht.

## Gemeinsamer Viererloop

Jeder normale Generierungsmodus verwendet denselben fachlichen Ablauf. Die
konkrete Spielerinteraktion darf ihn je nach Mode Definition unterschiedlich
inszenieren:

```text
Questziel und sichtbarer Prüffokus
→ vier Bilder erzeugen oder aus gültigem Bestand zusammenstellen
→ modusspezifische Einzel-, Set- oder Pairwise-Interaktion
→ pro Bild neue oder übernommene Disposition Favorite | Keep | Reject
→ bildweise Gründe für jede neue Disposition
→ modusspezifisches Ranking, Pairwise- oder Batchsignal
→ Evidence-Projektion
→ Keep-/Favorite-Bild als persistente Bildkarte projizieren
→ nächster QuestContract mit Control-Arm und deklarierten Mutationen
```

Die Reihenfolge innerhalb der mittleren Schritte ist modeabhängig: Der
Vierer-Qualifier verbindet Disposition und Gründe pro Einzelbild, das
Vierer-Ranking beginnt mit dem sichtbaren Set, Arena mit dem Paar. Der
Completion Contract verlangt am Ende dieselben fachlichen Bestandteile, nicht
dieselbe Bildschirmreihenfolge.

- `Favorite` bedeutet `target_hit`.
- `Keep` bedeutet `acceptable_only` und nicht bloß den schwächeren Favorite.
- `Reject` erzeugt negative Evidenz und genau eine deduplizierte Cleanup-
  Referral `awaiting_guided_evidence`, löscht aber keine Datei. Erst die
  bildweise Begründung setzt sie auf `ready` für Delete or Live.

`Skip` ist im Zielspiel keine Spielerentscheidung mehr. Ein fehlendes,
beschädigtes oder wegen fehlendem Vertrag nicht bewertbares Bild ist ein
technischer Blocker mit Recovery und keine vierte Qualitätsdisposition.

Jeder normale Bildmodus erzeugt oder übernimmt pro gezeigtem Bild eine
autoritative Disposition. Neue Favorite-, Keep- und Reject-Dispositionen
benötigen genau einen Primary Reason und dürfen mehrere Secondary Reasons tragen.
Ranking, Paarvergleich, Region und Batchkonsistenz ergänzen diese Evidence,
ersetzen sie aber nicht. Ein Bracket darf die unveränderliche Keep-/Favorite-
Qualifikation seiner Teilnehmer übernehmen.

Der Spieler wählt den Modus nicht. Der Scheduler bestimmt zuerst den Focus,
filtert kompatible `GameModeDefinition`-Revisionen und rotiert sie über Coverage-
und Gegenbalancierungsregeln. Es gibt keine feste Focus-/Mode-Zuordnung. Exakte
Control-/Challenger-Vergleiche verwenden für beide Seiten denselben Modus,
Blindzustand und symmetrische Darstellungsregeln; spätere Revalidierungszyklen
dürfen einen anderen kompatiblen Modus verwenden.

Ein `ranking` erzeugt relative Evidence und eliminiert einen niedriger
platzierten Keep nicht automatisch. Ein bindend entschiedener `elimination`-
Vergleich erzeugt Gewinner und Verlierer und wendet mode-unabhängig die gemeinsame
Lifecycle-Projektion an. Der unterlegene Keep geht sofort in DOA; jede
Favorite-Niederlage zählt in dieselbe Dreierverlustserie. Gleichstand, Abbruch
und `nicht vergleichbar` zählen nicht. Ein normaler Versus-Modus darf den
Verlierer nicht nur negativ werten und ohne Lifecycle-Folge aktiv lassen.

Vierergruppen werden rollierend weiterentwickelt: Weiterhin aktive Favorite-/
Keep-Bilder dürfen in die nächste Revision übergehen, Rejects und bindend
unterlegene Keeps werden DOA-pending, bindend unterlegene Favorites verlassen
die aktive Gruppe für ihren Cooldown, und neue Evidence-getriebene Challenger
füllen die freien Plätze.
Parent-Gruppe, Übernahmen, ausgeschiedene Bilder, neue Challenger, Focus, Kontext
und Mode Revision bilden die persistierte Lineage. Eine identische Vierergruppe
darf nur als markierte Reproduzierbarkeits- oder Kalibrierungsprobe wiederholt
werden.

Die Eignung einer Mode Revision wird nicht nur über Tempo bewertet. Completion,
Entscheidungszeit, Undo, Abbruch, technische Blocker, Reason-Vollständigkeit, Retest-
Widersprüche, spätere Pairwise-Vorhersagegüte und Focus-/Mode-Abdeckung werden
gemeinsam ausgewertet. Reihenfolge, Position, Blindzustand und Eingabeklasse
bleiben als Biasmerkmale erhalten. Ein schneller Modus mit schlechter oder
systematisch verzerrter Evidence wird nicht promoviert.

Jedes transportgültige, kontextkompatible Keep und Favorite füllt automatisch
den 16er-Pool. Es gibt keine zweite Spielerentscheidung „echter
Turnierkandidat“ gegenüber „nur brauchbar/nett“; `Keep` und `Favorite` sind selbst
die autoritativen Eintrittsentscheidungen. `Reject` füllt keinen Pool-Slot.

Keep und Favorite erscheinen zugleich als Bildkarten in der zugehörigen
Sammlung. Der spätere Cup erzeugt keinen neuen Kartenkörper, sondern verleiht
der bereits existierenden Siegerkarte einen kontextgebundenen Championtitel.
AssetSourceSelection, AssetAttempt und Asset-QA bleiben davon getrennt.
Das daraus neu erzeugte freigestellte oder normalisierte `DerivedAssetImage`
kehrt weder als Boosterkarte noch als Challenger zurück und ist auch kein
LoRA-Dataset-Candidate.

<a id="zweite-bildweise-begründungsrunde"></a>

## Bildweise Gründe im selben Spielschritt

`PM-093`/`DEC-060` und `PM-094`/`DEC-061` ersetzen den früheren globalen
Zweipass-Ablauf aus `PM-054`/`DEC-037`. Im Vierer-Qualifier folgt die Begründung
unmittelbar auf die Disposition desselben weiterhin sichtbaren Bildes. Im
Vierer-Ranking ist das Set ausschließlich während der Sortierung sichtbar; in
Arena das Paar ausschließlich während der Siegerwahl. Danach folgt pro Bild ein
zusammenhängender Dispositions-/Reason-Schritt mit genau diesem einen Fokusbild.

Die Reason-Stufe zeigt alle für das vollständige Bild und seine Assetrolle
anwendbaren Reasons genau einmal. Der Experiment Focus verändert nur Sortierung
und Hervorhebung. Die Oberfläche trennt zwei klickbare Bubble-Flächen räumlich
und semantisch:

- links: **Was hat gut funktioniert?**
- rechts: **Was hat nicht funktioniert?**

Beide Bubble-Flächen besitzen eine feste Höhe und scrollen unabhängig
voneinander. Nur ihr Inhalt scrollt; Bewertungsgegenstand, Disposition,
Fortschritt, Primary-Zusammenfassung und Abschlussaktion bleiben stehen. Die
Oberfläche verwendet keine Checkboxen und keine lange Dokumentliste. Der erste
zur Disposition passende gewählte Reason wird Primary Reason und sichtbar
markiert. Weitere gewählte Bubbles werden Secondary Reasons; ein weiterer Tap
entfernt sie. Wird der Primary Reason entfernt, rückt der nächste bereits
gewählte dispositionskonforme Reason nach. Der Bildknoten bleibt unverändert.

Freitext ist im normalen Spiel weder nötig noch vorgesehen. Eine
Nullbegründung `Nicht sicher / kein klarer Grund` ist ebenfalls nicht zulässig:
Favorite und Keep verlangen einen positiven, Reject einen negativen Primary
Reason. Gegenläufige Secondary Reasons dürfen
zusätzliche Aspekte ausdrücken, ohne den Primary Reason zu ersetzen.

Der erste Reason-Tap persistiert noch nichts. `Bewertung speichern` wird erst
mit dispositionskonformem Primary Reason aktiv und übermittelt Primary und
optionale Secondary Reasons in genau einer idempotenten Mutation. Diese enthält
gemeinsam
`attempt_image_id`, Disposition, optionalen Scalar Score, Primary Reason und
Secondary Reasons; keine dieser Angaben wird vorher separat als Review
persistiert. Beide Aktionen besitzen dasselbe Tastatur-, Fokus-
und Touch-Feedback wie die übrigen Spielaktionen.

### Fünf unabhängige Bewertungsebenen

Die Standardaction beschreibt die Disposition des Bildes, nicht die Ursache.
Die anschließenden Reasons werden deshalb fünf unabhängigen Ebenen zugeordnet:

| Ebene | Kernfrage | Typische Befunde | Erlaubte Folgerichtung |
|---|---|---|---|
| `generation_intent` | Wurde die verlangte Zusammensetzung erzeugt? | falsches Outfit, gewünschte Pose fehlt, falsche Haarfarbe, falsche Scene, unerlaubtes Zusatzelement | Prompt-, Component-, Binding- oder Composition-Recovery |
| `visual_defect` | Ist bei der Erzeugung sichtbar etwas kaputtgegangen? | deformierte Hände, Anatomiefehler, Artefakte, kaputtes Gesicht oder fehlerhaft gerenderter Hintergrund | Anatomy-, Quality-, Workflow-, Inpaint- oder Render-Recovery |
| `character_canon` | Ist es noch dieselbe Figur? | Character Drift, falsches Gesicht, veränderte Körperform, verlorenes Signaturmerkmal | Identity-/Reference-/Canon-Stability-Recovery ohne stille Canon-Änderung |
| `asset_usability` | Ist das Bild für seine konkrete Assetrolle verwendbar? | falscher Crop, abgeschnittene Figur, fehlende Safe Area, unbrauchbare Freistellung oder falscher Anchor | Assetrollen-, Crop-, Matting- oder Normalisierungs-Recovery |
| `aesthetic_preference` | Gefällt die ansonsten mögliche Lösung dem Spieler? | Farbwirkung, Ausdruck, Stimmung oder Komposition gefällt beziehungsweise gefällt nicht | persönliche Priors erst nach wiederholter vergleichbarer Evidence |

Mehrere Ebenen dürfen für dasselbe Bild gleichzeitig positive und negative
Evidence tragen. Beispiel: Outfit und Identity sind korrekt, das Gesicht gefällt,
aber Hände und Hintergrund sind technisch kaputt. Dann erhalten Outfit,
Identity und Taste positive Evidence; Anatomy und Background erhalten negative
Defect Evidence. Der nächste Try darf deshalb nicht Outfit oder Character Canon
verändern.

Diese achsenspezifische Human-Evidence ist zugleich die einzige Grundlage für
spätere positive Image-Referenzsets und negative Fehlercluster. Ein globales
Keep, Favorite oder Reject wird nicht pauschal auf alle Embedding-Räume kopiert;
ungesehene beziehungsweise technisch blockierte Bilder werden im initialen Pfad
nicht eingebettet.
Der vollständige Vertrag steht in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md).

Besonders ähnliche sichtbare Befunde benötigen unterschiedliche Codes:

- `scene_contract_mismatch`: Der falsche Hintergrund wurde erzeugt;
  `generation_intent` ist negativ.
- `background_render_defect`: Der richtige Hintergrund wurde versucht, ist aber
  sichtbar kaputt; `visual_defect` ist negativ.
- `scene_not_preferred`: Der Hintergrund ist vertragskonform und sauber, gefällt
  dem Spieler aber nicht; `aesthetic_preference` ist negativ.

Dasselbe Prinzip gilt etwa für `artstyle_contract_mismatch` gegenüber
`artstyle_not_preferred` und für `pose_missing` gegenüber
`anatomy_broken_in_pose`.

### Kontextuelle Vorauswahl

Der Server erzeugt die zulässige und priorisierte Chip-Liste aus:

- `QuestContract` und sichtbarem Prüffokus,
- `VisualSpec`, Assetrolle und authored Locks,
- vollständigem `GenerationRecipe` und deklarierter Variationsachse,
- aktiver Inhaltseinstellung,
- den aktuellen Favorite-/Keep-/Reject-Dispositionen der vier Bilder,
- sowie optionalen maschinellen Diagnosevorschlägen.

Die Registry der Reason Codes ist versioniert und authored. Ein Vision-Modell
darf später passende vorhandene Chips höher sortieren oder Bildziele
vorschlagen. Es darf keine Gründe erfinden, keine Auswahl absenden und keine
Spielerevidenz überschreiben.

Der Generation Focus priorisiert die für die Hypothese wichtigsten Chips, darf
aber keine für die Assetrolle tatsächlich anwendbare allgemeine Fehlerquelle
verbergen. Eine Outfit-Challenge zeigt also vorrangig Outfit-/Intent-Gründe,
lässt aber weiterhin Anatomy-, Identity-, Background- und technische Defects
erfassen.

Eine Place-Quest zeigt deshalb keine Haar- oder Outfitgründe. Ein Sprite-/Alpha-
Trial priorisiert Halo, Haarverlust, Löcher, Hintergrundinseln und harte Kanten.
Ein Sampler- oder Parametervergleich priorisiert Qualität, Style, Identity,
Nebenwirkungen und Laufzeit. Inhaltsspezifische Gründe erscheinen ausschließlich
im freigegebenen Scope der betreffenden Einstellung.

### Reason-Familien

| Familie | Positive Beispiele | Negative Beispiele |
|---|---|---|
| Identity | Figur klar getroffen, Gesicht stabil, Merkmale konsistent | andere Figur, Face Drift, falsche Augen oder Körperform |
| Hair und Details | Haarfarbe, Schnitt und Detail passen | falsche Farbe, falsche Frisur, Detail verloren |
| Outfit | Outfit und Character Binding getroffen | falsches Outfit, fehlendes Teil, falsche Farbgebung |
| Pose und Expression | Pose lesbar, Ausdruck passend, Hände sauber | falsche Pose, unpassender Ausdruck, Hände/Anatomie fehlerhaft |
| Artstyle und Qualität | Anime Style Core stabil, saubere Linien und Shading | Wrong Artstyle, Artefakte, unsaubere Linien oder Shading |
| Scene und Komposition | Ort, Hintergrund, Licht, Crop und Safe Area passen | komischer/falscher Hintergrund, Zusatzperson, schlechter Crop |
| Prompttreue | Zieländerung sichtbar und übrige Locks erhalten | Ziel fehlt, unrelated drift, verbotene Nebenänderung |
| Extraction und Alpha | saubere Kante, Haare erhalten, keine Inseln | Halo, Haarverlust, Löcher, Hintergrundinsel, harte Kante |
| Effizienz | verwendbares Ergebnis bei guter Laufzeit | langsam ohne Qualitätsgewinn, hohe Ausfallquote |
| Inhaltseinstellung | beabsichtigte Stufe kohärent getroffen | Stufe verfehlt, unzulässiger oder scope-fremder Inhalt |

Jeder Reason-Code deklariert zusätzlich `evaluation_layer`, fachlichen
`target_scope`, zulässige Actions, Polarität, gegenseitige Ausschlüsse und
erlaubte `recovery_routes`. Die Reason-Familie beschreibt die sichtbare Domäne;
die Bewertungsebene beschreibt, **warum** der Befund für dieses Bild relevant
ist. `background` ist daher eine Familie, aber Intent, Defect, Usability und
Taste sind verschiedene Ebenen innerhalb dieser Familie.

### Bildzuordnung und Pflichtumfang

Jeder Reason gehört genau zum aktuell fokussierten `image_id`. Die
Reason-Auswahl eines anderen Bildes ist in diesem Schritt weder sichtbar
veränderbar noch über eine Sammelaktion übertragbar. Batchbefunde wie „alle vier
driften“ werden erst anschließend deterministisch aus vier gleichartigen
Einzelbefunden abgeleitet; sie werden nicht als pauschaler Spielerchip erfasst.

- Jedes `Favorite` oder `Keep` erhält mindestens einen positiven Reason. Die
  einzige ausdrücklich versionierte Ausnahme ist `ten_point_calibration`:
  dort schreiben Favorite und Keep den deterministischen Qualitätsscore und
  gehen ohne Reason-Runde zum nächsten Bild.
- Jedes `Reject` erhält mindestens einen negativen Reason.
- Gemischte Befunde sind zulässig: Ein schönes Gesicht kann gleichzeitig mit
  falschem Outfit markiert werden.
- Der erste gewählte dispositionskonforme Reason wird Primary Reason und bleibt
  sichtbar markiert. Wird er entfernt, rückt der nächste bereits gewählte
  kompatible Reason nach; gegenläufige Secondary Reasons ersetzen ihn nicht.

Eine Nullbegründung und eine playerseitige Skip-Disposition existieren im
Zielablauf nicht.

Delete or Live fragt diese Gründe nicht erneut ab. Es konsumiert die bereits
gespeicherte negative Evidenz und bleibt anschließend eine einzige binäre
Entscheidung `Live | Delete` ohne zweite Bestätigung.

### Persistenz

```text
GuidedImageEvidence
├─ batch_id
├─ quest_instance_id
├─ image_id
├─ polarity: positive | negative | uncertain
├─ reason_code
├─ evaluation_layer
├─ reason_scope
├─ target_component_id?
├─ prompt_aspect_group_id?
├─ variation_axis?
├─ source: player
├─ is_primary
├─ generation_focus_id oder null
├─ evaluation_focus_id
├─ recipe_snapshot_id
└─ created_at
```

Die unveränderte Auswahl des Spielers ist Source of Truth. Confidence, Ratings
und nächste Maßnahmen sind rebuildbare Codeprojektionen. Maschinenbefunde
bleiben getrennt als Diagnoseevidenz.

Diese Projektionen sind Verhältnisgeschichten pro Bild, Context Hash,
Evaluation Layer und Bewertungsachse. Sie speichern positive und negative
Evidenzmasse, Beobachtungszahl, unabhängige Quellen, Verhältnis, Unsicherheit und
Confidence getrennt. Ein neues Bild darf nach einer positiven Bewertung ein
hohes Verhältnis besitzen, bleibt jedoch wegen geringer Evidenzmenge unsicher;
ein mehrfach bewertetes Bild reagiert weniger sprunghaft. Die UI darf deshalb
nie nur eine nackte Prozentzahl zeigen, sondern muss Verhältnis und
Belastbarkeit gemeinsam erklären.

Gegenläufige Bewertungen derselben Achse verändern deren Verhältnis. Befunde
unterschiedlicher Achsen kompensieren einander nicht. A/B-Ergebnisse schreiben
nur auf die sichtbare Vergleichsachse. Rohereignisse verfallen nicht; eine neue
fachliche Revision erhält über ihren Context Hash eine eigene Projektion.

<a id="spielmodi"></a>

## Bestätigter geplanter Kern der Spielmodi

Status: **vier vorgelagerte und zwei nachgelagerte Modi sind bestätigt.** Der
früher deferred vierte Modus ist mit `ten_point_calibration` durch `PM-098` und
`DEC-065` entschieden.

Dieser Abschnitt ist der produktseitige Zielvertrag für die nächste
Frontend-Korrektur. Er hat für Spielerablauf, Benennung und Screenbudget Vorrang
vor den heute implementierten Phasen in
[`initial-game-mode-state-machines.md`](../README.md#fehlende-vorgängerquellen).
Der Foundation-Vertrag bleibt bis zur Korrektur die Wahrheit darüber, was der
Server heute tatsächlich ausführt; er definiert nicht mehr das gewünschte
Spielerlebnis.

### Zwei Stufen statt eines flachen Moduskatalogs

| Stufe | Bestätigte Modi | Aufgabe |
|---|---|---|
| **Vorgelagert: Bilder erstmals einschätzen** | Vierer-Qualifier, Vierer-Ranking, Arena, Ten-Point Calibration | Erhebt Disposition und bildbezogene Gründe für neue oder ausdrücklich neu zu qualifizierende Bilder; Calibration ergänzt einen davon getrennten absoluten Qualitätsscore. |
| **Nachgelagert: mit bereits bewerteten Bildern spielen** | 16er-Cup einschließlich Title Match, Delete or Live | Verwendet bereits vorhandene Qualifikation und Gründe für Championwahl beziehungsweise Cleanup; erhebt nicht dieselbe absolute Bewertung noch einmal. |

`Trials` ist weiterhin nur der gemeinsame Rahmen. Generation Focus,
Evaluation Focus, sichtbare Bewertungsfrage, Characterbindung und Creditquelle
sind orthogonale Verträge. Derselbe Spielmodus kann daher andere Inhalte oder
Evidenzfragen tragen, ohne dadurch zu einem neuen Modus zu werden.

### Gemeinsamer Grundvertrag der vorgelagerten Modi

- Disposition und zugehörige Gründe bilden pro Bild einen zusammenhängenden
  Fokusschritt: Das Bild wird zwischen diesen beiden Interaktionen nicht ersetzt.
  Eine vorausgehende Sortierung oder Paarentscheidung ist eine eigene relative
  Spielstufe; deren übrige Bilder bleiben in den nachfolgenden Einzelbildschritten
  nicht als Motiv oder Thumbnail sichtbar.
- Im Qualifier ist die Impulsentscheidung bereits die Disposition. Im
  Vierer-Ranking folgt die einmalige Disposition jedes Bildes auf die Sortierung,
  in Arena auf das Paarergebnis. Diese relative Vorentscheidung ist keine erste
  Dispositionsrunde; jedes Bild erhält insgesamt genau einmal Favorite, Keep
  oder Reject samt Reasons.
- Die einzigen playerseitigen Qualitätsdispositionen sind `Favorite`, `Keep`
  und `Reject`. `Favorite` und `Keep` benötigen mindestens einen positiven
  Primary Reason; `Reject` mindestens einen negativen Primary Reason. `Skip`
  existiert im Zielspiel nicht. Technisch unbewertbares Material blockiert und
  läuft in Recovery, statt als Qualitätsurteil gespeichert zu werden.
- Positive Reasons stehen visuell links, negative Reasons rechts. Sie dürfen
  nicht in einer gemeinsamen unsortierten Liste vermischt werden.
- Gegenläufige Secondary Reasons bleiben möglich: Ein Keep kann zusätzlich
  einen negativen Aspekt und ein Reject zusätzlich einen positiven Aspekt
  tragen. Sie ersetzen niemals den dispositionskonformen Primary Reason.
- Es gibt keine Nullbegründung wie `kein klarer Grund`. `Nichts ist gut` ist
  keine fehlende Begründung, sondern eine gültige negative Entscheidung und
  benötigt die passenden negativen Reasons.
- Die Reason-Auswahl besteht aus klickbaren Bubbles statt Checkboxen. Positive
  und negative Bubble-Fläche scrollen jeweils intern und unabhängig; nur diese
  Flächen scrollen. Die gewählten Reasons und der Primary Reason stehen darüber
  dauerhaft sichtbar.
- Weil mehrere Reasons gewählt werden dürfen, beendet der erste Bubble-Tap den
  Schritt nicht. Eine fest sichtbare Aktion `Weiter` wird aktiv, sobald der
  dispositionskonforme Primary Reason vorhanden ist. Es gibt keinen zusätzlichen
  Bestätigungs-, Übernahme- oder Disposition-Screen.

### 1. Vierer-Qualifier

**Zweck:** Vier neue Bilder einzeln absolut als `Favorite`, `Keep` oder
`Reject` qualifizieren.

**Spielerablauf pro Bild:**

1. Bild 1 steht groß und eindeutig als aktueller Bewertungsgegenstand in der
   Mitte.
2. Der Spieler wählt `Favorite`, `Keep` oder `Reject`.
3. Exakt dasselbe Bild bleibt in derselben Stage sichtbar. Links erscheinen
   positive, rechts negative Reason-Bubbles in zwei unabhängig scrollbaren
   Flächen. Auswahlleiste, Bild und `Weiter` bleiben fest sichtbar.
4. Der dispositionskonforme Primary Reason wird gewählt; optionale Secondary
   Reasons können im selben Bildschritt ergänzt werden.
5. `Weiter` wird nach vollständigem Pflichtgrund aktiv und führt zu Bild 2;
   derselbe Mikroloop läuft bis Bild 4.
6. Nach Bild 4 folgt nur eine Ergebnisprojektion beziehungsweise die nächste
   fachliche Aktion. Es gibt keinen zweiten globalen Pass über dieselben vier
   Bilder und keine erneute Dispositionsabfrage.

Für den technischen Batchabschluss wird ohne neue Spieleraktion das erste
bereits vergebene Favorite, ersatzweise das erste Keep, zum lokalen
`batch_pick`. Diese Transportwahl ist kein Cup-Champion. Sind alle vier Bilder
Reject, bleibt der Pick ehrlich `null` und alle Rejects folgen dem dokumentierten
Delete-or-Live-Lifecycle.

Ein Batch ohne Keep oder Favorite ist ein vollständig gültiges Ergebnis: Alle
vier Bilder dürfen mit negativen Gründen Reject sein. Im diegetischen
Booster-Rahmen entstehen daraus trotzdem vier Spielkarten: Die vier
Kartenkörper bleiben bildlose Standardkarten und werden weder positive
Evidence noch Challenger.
Ein technisch unbewertbares Bild ist kein Reject, sondern blockiert den
Boosterabschluss bis zur Recovery beziehungsweise Ersetzung.

### 2. Vierer-Ranking

**Zweck:** Vier neue, miteinander vergleichbare Bilder gleichzeitig von links
nach rechts als bestes bis schwächstes Bild ordnen. Dieser Modus ersetzt den
heutigen spielerseitigen Namen und Ablauf `Weakest Link`; es gibt daneben
keinen zusätzlichen Vierer-Draft oder zweiten Sortiermodus.

**Bestätigter Spielerablauf:**

1. Alle vier Bilder bleiben gleichzeitig sichtbar.
2. Der Spieler sortiert sie von links nach rechts: bestes Bild bis schwächstes
   Bild.
3. Danach erhält jedes der vier Bilder genau einmal `Favorite`, `Keep` oder
   `Reject`. Es gibt keine feste `2 Keep / 2 Reject`-Quote: `1/3`, `2/2`, `3/1`,
   vier Keeps/Favorites und vier Rejects sind ehrliche mögliche Ergebnisse.
4. Nach Abschluss der Sortierung wird Bild 1 allein und bilddominant fokussiert.
   Die übrigen drei Bilder erscheinen weder als Motiv noch als Thumbnail.
   Disposition und Reasons verwenden links und rechts getrennt scrollbare
   Bubble-Flächen, die Auswahlleiste und das feste `Weiter`: mindestens ein
   positiver Primary Reason je Favorite/Keep und mindestens ein negativer
   Primary Reason je Reject.
5. Nach `Weiter` wird das nächste Bild allein fokussiert. Es gibt keine
   zweite Sortierung, keine spätere Wiedervorlage und keine feste Quote, die
   künstlich gute oder schlechte Bilder erzeugt.

Das Ranking liefert zusätzlich relative Evidence. Ihre Stärke wird
deterministisch aus den danach gesetzten Dispositionen projiziert: Eine Ordnung
innerhalb derselben Disposition ist schwächere Präferenzevidenz; Favorite vor
Reject ist stärker als Favorite vor Keep oder Keep vor Reject. Exakte numerische
Faktoren sind versionierte Kalibrierung und keine UI-Entscheidung.

Dispositionen müssen die Sortierung als harte Invariante respektieren. In der
Reihenfolge bestes bis schwächstes Bild ist ausschließlich eine monotone Folge
`Favorite* → Keep* → Reject*` zulässig; jede der drei Gruppen darf leer sein.
Damit bleiben alle ehrlichen Mengenverteilungen einschließlich vier Favorites,
vier Keeps oder vier Rejects möglich, aber ein niedriger geranktes Bild darf
niemals eine stärkere Disposition als ein höher geranktes Bild erhalten. Die UI
verhindert eine solche Auswahl unmittelbar und bietet die direkte Korrektur der
Sortierung oder einer bereits gesetzten Disposition an. Sie sortiert und
überschreibt niemals still.

### 3. Arena

**Zweck:** Zwei neue oder für diese Frage qualifizierte Bilder blind direkt
gegeneinander stellen und relative Sieger-/Verlierer-Evidenz gewinnen.

**Bestätigter Spielerablauf:**

1. Beide Bilder stehen für die blinde Paarentscheidung gleichwertig nebeneinander.
2. Der Spieler wählt links oder rechts als Gewinner. Wenn beide Bilder
   unbrauchbar sind, muss er ausdrücklich `kein Gewinner` wählen können.
3. Danach erhält jedes Bild genau einmal `Favorite`, `Keep` oder `Reject` und
   die dazu erforderlichen Reasons. Der Paargewinner wird dadurch nicht
   automatisch Favorite/Keep und der Verlierer nicht automatisch Reject.
4. Nach der Paarentscheidung folgt immer Bild A und danach Bild B, unabhängig
   davon, welches Bild gewonnen hat. Im jeweiligen Fokusschritt ist ausschließlich
   dieses Bild sichtbar; sein Gegenstück erscheint auch nicht als Thumbnail.
   Disposition und Reasons bleiben am identischen Bildknoten und verwenden die
   getrennt scrollbaren Bubble-Flächen, Auswahlleiste und festes `Weiter`.
5. Das Paarergebnis liefert relative Evidence, deren Stärke wie beim Ranking
   von den nachfolgenden Dispositionen abhängt. Gewinner Favorite gegen
   Verlierer Reject ist stärker als ein Sieg innerhalb derselben Disposition.
   Exakte numerische Faktoren bleiben versionierte Kalibrierung.
6. Ein Gewinner muss Keep oder Favorite sein. `kein Gewinner` ist der Fall für
   zwei Rejects. Der Verlierer darf Reject, Keep oder Favorite sein; seine
   Disposition bestimmt den bereits dokumentierten Lifecycle. Dabei darf die
   Gewinnerdisposition niemals schwächer als die Verliererdisposition sein:
   Favorite darf gegen Favorite, Keep oder Reject gewinnen, Keep nur gegen Keep
   oder Reject. Ein Keep-Sieger gegen ein Favorite ist ungültig und muss in der
   Stage korrigiert werden.
7. Sobald beide Dispositionen und Pflichtgründe vollständig sind, wird das Paar
   ohne `Bewertung starten`, `Ergebnis übernehmen` oder nachgelagerte
   Disposition-Formulare abgeschlossen.

Der bestehende bindende Lifecycle bleibt unverändert: Ein unterlegener Reject
geht über seine begründete Reject-Referral zu Delete or Live, ein unterlegener
Keep über die bindende Niederlage und ein unterlegenes Favorite über die
dokumentierte Verlustserie, Cooldowns und bei Verlust drei zu Delete or Live.
Ein Arena-Sieg eines Favorites setzt dessen aktuellen Verlustzähler zurück.
Disposition und Paarergebnis werden gemeinsam persistiert; keines darf das
andere still überschreiben.

### 4. Ten-Point Calibration

Status: **DECIDED.** Der vierte vorgelagerte Modus bewertet jedes Bild als
allgemeine Qualitätskalibrierung. Favorite schreibt 10, Keep 7; Reject verlangt
einen frei wählbaren Score von 1 bis 10 und einen negativen Primary Reason. Ein
hoher Reject-Score ist kein Widerspruch: Das Bild kann technisch hochwertig und
für Outfit, Stil, Figur oder Quest dennoch ungeeignet sein. Beim Reject wird der
Score zusammen mit Primary und optionalen Secondary Reasons im gemeinsamen
Reason-Screen gewählt. `Bewertung speichern` übermittelt
Score, Disposition und alle Reasons gemeinsam in einer idempotenten
Reviewmutation. Sie bleiben fachlich getrennte Messgrößen und werden nicht als
getrennte Spielercommits vervielfacht.

### 5. 16er-Cup und Title Match

**Zweck:** Sechzehn bereits positiv qualifizierte Bilder über das Bracket
`16 → 8 → 4 → 2 → 1` bis zum Challenger- beziehungsweise Championtitel führen.

- Pro Match wird ein Sieger aus zwei weiterhin sichtbaren Bildern gewählt.
- Es gibt keine erneute absolute Auswahl `Favorite / Keep / Reject` und
  keine Wiederholung der vorgelagerten Bildqualifikation.
- Ein bereits ausgeschiedenes Bild wird nicht erneut im selben Bracket
  bewertet. Die dokumentierten Keep-, Favorite-, Cooldown-, Former-Champion-
  und Delete-or-Live-Folgen bleiben erhalten.
- Ein Cup-Match verlangt weder neue Reasons noch Favorite/Keep/Reject. Die
  Spieleraktion ist ausschließlich die Siegerwahl; vorhandene Dispositionen und
  Reasons bleiben gebunden und die Pairwise-Evidence entsteht aus dem Match.
- Ein vorhandener Champion wird erst nach dem Challenger-Cup im Title Match
  geprüft; das Title Match ist die Abschlussstufe desselben
  Wettbewerbsablaufs und kein weiterer vorgelagerter Modus.

### 6. Delete or Live

**Zweck:** Einen bereits begründet abgelehnten oder regelkonform
ausgeschiedenen Kandidaten endgültig behalten oder löschen.

1. Genau ein Bild erscheint mit Herkunft, Schutzstatus und bereits gespeicherten
   Gründen.
2. Der Spieler wählt einmal `Live` oder `Delete`.
3. Es gibt weder neue Reasons noch eine zweite Bestätigung.
4. Danach folgt unmittelbar der nächste Kandidat oder der Abschluss.

Delete or Live erzeugt keine neue Qualitätsbewertung und verändert die
historische Review-Evidence nicht.

## Eigenständiger Beschreibungstest

**Zweck:** Prüfen, ob eine Image-Worker-Beschreibung ihr Quellbild gegenüber
einem kontrolliert gewählten Gegenbild verständlich und eindeutig bezeichnet.

1. Der Server bindet genau eine versionierte Beschreibung an ihr Quellbild.
2. Er wählt genau ein anderes verfügbares Bild derselben Figur aus dem
   behaltenen Keep-/Favorite-/Champion-Pool. Dasselbe persistente Bild erscheint
   auch mit mehreren Titeln höchstens einmal im Pool.
3. Beschreibung und beide Bilder bleiben gemeinsam sichtbar. Links/rechts wird
   pro Interaktion randomisiert.
4. Der Spieler beantwortet ausschließlich: „Zu welchem Bild passt diese
   Beschreibung?“
5. Die Antwort erzeugt `DescriptionMatchEvidence`, aber keine Disposition,
   keinen Reason, keinen Challenger-, Champion-, Stability-, Asset- oder
   Delete-or-Live-Effekt.

Das Gegenbild wird zufällig innerhalb eines serverseitig gebundenen
Schwierigkeitskorridors gewählt, nicht ungefiltert aus allen Bildern. Harte
Filter binden mindestens Character, Content Scope, Dateiverfügbarkeit und
zulässige Kartenrolle. Danach dürfen Beschreibung-/Promptähnlichkeit,
`full_frame_semantic`, `style_view`, Character-Scope-Prüfung, strukturierte
Merkmalsüberlappung und Near-Duplicate-Befund den Korridor bestimmen. Scores aus
verschiedenen Embedding-Räumen werden rankbasiert zusammengeführt und niemals
roh addiert.

Eine einzelne Wahl misst nur relative Unterscheidbarkeit in genau diesem Paar.
Sie beweist weder absolute Richtigkeit noch Falschheit der Beschreibung. Erst
mehrere Paarungen über verschiedene Schwierigkeitsstufen dürfen eine
rebuildbare Projektion wie `unbewiesen`, `eindeutig`, `nur gegen leichte
Gegenbilder tragfähig`, `generisch` oder `irreführend` erzeugen. Ob die
Spieleroberfläche zusätzlich „nicht eindeutig“ anbietet und wie viele Paarungen
für eine Einstufung nötig sind, bleibt eine versionierte Kalibrierung.

Die heute in normale bildweise Reasons eingebettete Auswahl `confirm | correct |
dismiss` ist kein Zielablauf dieses Spiels. Historische und administrative
Bestandsprüfung darf diese Aktionen weiterhin revisionsgebunden verwenden; die
normale Spielerführung erhält dafür keinen zusätzlichen Pflichtblock unter der
eigentlichen Bildbewertung.

## Modusbestand vor der gemeinsamen Neufestlegung

Status: **OPEN für spielerseitige Modusliste und Abläufe.**

Die folgende Bestandsaufnahme ist kein freigegebener Game-Mode-Katalog. Vor der
Frontend-Umsetzung wird jeder Eintrag danach geprüft,

1. welche eigenständige Spielerinteraktion er tatsächlich besitzt,
2. ob er nur eine Evidenzfrage oder einen Quest-/Credit-Kontext bezeichnet,
3. ob er lediglich ein technischer Parametervergleich ist,
4. ob er mit einer anderen Variante zusammengelegt werden muss,
5. und wie viele aufeinanderfolgende Screens dasselbe Bild beanspruchen darf.

Arcade-/Rating-Seiten, `Rankings`, `Render Lab`, `Trials`, `Freier Trial` und
Routennamen sind in dieser Prüfung ausdrücklich keine Game Modes. `Trials` ist
der Rahmen; `frei` ist eine Bindung; Rankings sind eine Projektion; die übrigen
Begriffe sind Legacy-/Technikbezeichnungen, deren benötigte Funktionen in den
kanonischen Trial-Flow oder nach Advanced migriert werden.

Die heute implementierten Sessionphasen, semantischen Actions, Completion
Contracts und Lifecycle-Folgen von Vierer-Qualifier, Weakest Link und Arena stehen in
[Foundation-Zustandsvertrag](../README.md#fehlende-vorgängerquellen).
Diese Bestandsaufnahme beschreibt nur ihre bisherige Produktrolle. Der
verlinkte Foundation-Vertrag ist für den aktuell implementierten technischen
Stand autoritativ, weicht aber in den unter `GAP-026` festgehaltenen Punkten vom
oben bestätigten Zielablauf ab.

### Character Creation und visuelle Entwicklung

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Character Forge** | Vier klar unterscheidbare Start- oder Detailrichtungen vergleichen. | Gewählte Richtung, Locks und offene Achsen erzeugen den nächsten kontrollierten Try. |
| **Character Evolution Tournament** | Eine authorisierte `PromptAspectGroup` innerhalb des Character Arcs verändern. | Qualifiziert einen Evolution Challenger; Canon ändert sich erst nach separatem Title Match und Gates. |
| **Vierer-Qualifier / Seed Run** | Vier Seeds desselben gültigen Recipes als Kandidat, brauchbar/nett, Reject oder Skip einordnen. | Füllt Candidate Pool, Stability Evidence und Recovery-Bedarf. |

### Stabilität, Auswahl und Champion

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Stability Trial** | Eine feste Character-/Recipe-Signatur über neue Seeds prüfen. | Misst Trefferquote, Drift und wiederkehrende Fehler. |
| **Weakest Link** *(historischer Implementierungsname; Zielname Vierer-Ranking)* | Der heutige Automat sucht Ausreißer; dieser Spielerablauf wird nicht fortgeführt. | Ziel ist die oben definierte vollständige Sortierung aller vier Bilder mit Top-2-/Bottom-2-Projektion und All-Reject-Pfad. |
| **Arena** | Zwei kompatible Bilder auf genau einer sichtbaren Achse vergleichen. | Im normalen Bildloop bindende Elimination: Keep-DOA beziehungsweise Favorite-Verlustserie; Draw und nicht vergleichbar bleiben ungelöst. |
| **16er-K.-o.-Cup** | Sechzehn kompatible Challenger über `16 → 8 → 4 → 2 → 1` reduzieren. | Erzeugt ersten Champion oder einen Challenger für den Amtsinhaber. |
| **Champion Defense / Title Match** | Cup-Sieger direkt gegen aktuellen Champion prüfen. | Champion bleibt oder wird nach Validation versioniert ersetzt. |
| **Asset-Auswahl** | Bereits bewertete Bildkarten als Quelle für einen konkreten Produktionsvertrag vergleichen. | Wählt eine Assetquelle; erzeugt oder entfernt keinen Championtitel. |
| **Beschreibungstest** | Eine Beschreibung genau einem von zwei behaltenen Bildern derselben Figur zuordnen. | Misst relative Eindeutigkeit der Beschreibung; verändert keine Karte und keinen Bildlebenszyklus. |

Offene, noch unbewertete Bestandskarten mit dem historischen
`weakest_link`-Contract dürfen ohne Neugenerierung auf den effektiven
`four_image_ranking`-Modus gebunden werden. Der ursprüngliche immutable
QuestExperiment-, Gruppen- und Mode-Selection-Beleg bleibt unverändert; ein
append-only `QuestModeRebound` hält Original- und Effektivmodus fest. Session,
Commands, Credit, API und Frontend verwenden danach ausschließlich den
effektiven Modus. Bereits abgeschlossene historische Weakest-Link-Sessions
werden nicht umgedeutet.

Ein 16er-Cup ist eine `QuestSession` mit fünfzehn Paarentscheidungen und nicht
fünfzehn Playgate-Runden. Sein Roster ist auf genau eine versionierte,
spielerisch benannte ChampionSlot-Revision samt Inhaltseinstellung und
Compatibility Signature eingefroren. Welche Character-, Assetrollen-, Canon-,
Outfit-, Scene-, Pose-, Expression-, Framing- und View-Dimensionen den Slot
definieren, bestimmt dessen rollenspezifische Compatibility Policy. Existiert
bereits ein Champion, spielt zunächst der Challenger Cup; erst sein Sieger tritt
gegen den Champion an.

Dasselbe unveränderte Bild darf über getrennte Qualifikationen in mehreren
Slots antreten und mehrere Titel tragen. Pro Pool und Bracket zählt es höchstens
einmal; eine kontextuelle Entscheidung wird nicht als Antwort auf eine andere
Bewertungsfrage wiederverwendet. Der vollständige Vertrag steht in
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md).

Ein Asset-Auswahlbracket darf dieselbe A/B-Interaktion und bereits erhobene
Keep-/Favorite-Evidence verwenden, bleibt aber ein anderer Evaluation Focus.
Sein Sieger ist `AssetSourceSelection`, nicht automatisch Champion. Scheitert
die nachfolgende Ableitung oder QA, bleibt die Bildkarte mitsamt Bewertung und
etwaigen Titeln erhalten.

Eine Niederlage in der Asset-Auswahl ist ebenfalls keine normale
Arena-Elimination. Sie erzeugt insbesondere weder Reject/DOA noch
Favorite-Verlust, Cooldown oder Championfolge. Sie sagt nur aus, dass das andere
Bild für den gebundenen Produktionsvertrag geeigneter gewählt wurde.

Das Eligibility-Ereignis des sechzehnten rosterfähigen Challengers friert
atomar die ersten sechzehn noch keinem Cup zugewiesenen Einträge in stabiler
Ereignisfolge ein. Die Folge bestimmt ihre Bracketplätze. Spätere Challenger
warten auf den nächsten Cup; Score, frühere Gegner und Spielerwahl verändern
das fertige Feld nicht.

Jeder bindend entschiedene Eliminationsvergleich persistiert zugleich
kontextgebundene Pairwise-Evidence: Gewinner und Verlierer, Mode Revision,
optionale Runde, Bewertungsachse, Gegner und Compatibility Hash.
Der Gewinner erhält positive, der Verlierer negative Qualitätsevidenz im
gebundenen Scope. Bei einem Favorite setzt jeder bindende Eliminationssieg den
aktuellen `consecutive_loss_count` auf null, ohne frühere Matchereignisse zu
löschen. Jede bindende Favorite-Niederlage zählt unabhängig vom Modus in dieselbe
Serie. Nach Niederlage eins und zwei gilt jeweils genau ein
`ChampionCycleCooldown`: ein vollständiger Challenger-Cup bis zum nächsten
Title Match, genauso wie beim amtierenden Champion. Verlust drei verweist an
Delete or Live. `Live` erhält `favorite`, setzt Verlustserie und Cooldown auf
null und erzeugt ein neues Eligibility-Ereignis für einen späteren Cup.

Ein unterlegener Title-Match-Challenger folgt seiner unveränderten
Keep-/Favorite-Verlustregel. Ein abgelöster Amtsinhaber bleibt als geschützter
`former_champion` im Challenger-Pool und geht nicht unmittelbar in DOA.
Gleichstand oder Abbruch erhalten den Amtsinhaber und lassen das Title Match
offen.

### Fehler, Recovery und Effizienz

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Error Hunt** | Sichtbare Fehler über die kontextuelle Reason Registry markieren. | Bild- und aspektgenaue Fehlercluster. |
| **Repair Run** | Kontrollierte Reparaturen eines bestätigten Fehlers vergleichen. | Bestimmt, welche begrenzte Änderung den Fehler ohne Regression behebt. |
| **Spot the Change** | Eine isoliert veränderte Achse zwischen Control und Challengern erkennen und bewerten. | Kausaler Credit nur für die deklarierte Achse. |
| **Efficiency Run** | Zuerst Qualitätsschwelle, dann verwendbare Bilder pro Zeit vergleichen. | Laufzeit zählt erst nach bestandener Qualität und darf Qualität nicht ersetzen. |

### Identity, Prompttreue und Komponenten

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Identity Lineup** | Unter variierenden Outfits, Posen oder Scenes die Identity-stabilen Bilder auswählen. | Positive/negative Character-Similarity-Paare und Drift Evidence. |
| **Same Character?** | Bildpaare als gleiche Figur, unsicher oder andere Figur klassifizieren. | Kalibriert Identity-Grenzen ohne automatische Canon-Autorität. |
| **Combo Detective** | Sichtbare Character-, Outfit-, Pose-, Expression-, Scene-, Lighting- und Modifier-Komponenten zuordnen. | Komponentenbezogene Prompt-Adherence statt eines einzigen Gesamtscores. |
| **Component League** | Eine Komponente über mehrere passende Figuren, Seeds und Bindings bewerten. | Cross-Character-Prior; globale Promotion benötigt weiterhin ausreichende Breite. |

### Places, Sprites und Kontinuität

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Place Trial** | Personenfreie Orte auf Style, Landmarken, Safe Area, Licht und Wiederverwendbarkeit prüfen. | Scene-Blueprint- und Place-QA-Evidence, getrennt von Character Ratings. |
| **Sprite / Alpha QA** | Sprite auf Checkerboard, Schwarz, Weiß, Kontrollfarbe und VN-Hintergrund prüfen. | Routet Source-, Matting- oder Normalisierungsfehler zum richtigen Processing-Schritt. |
| **Continuity Check** | Eine konsistente Bildfolge aus Scene, Outfit, Licht, Pose und Figurenstand zusammensetzen. | Sequence-Evidence und gezielte Folgequests für Kontinuitätsbrüche. |

`Place Trial` ist hier weiterhin ein Arbeitsname und noch kein vollständig
freigegebener Spielerablauf. Reine Background-Bilder besitzen keinen Character-
Kartenkörper; ihr konkreter Bewertungs-, Vergleichs- und Resultatflow wird nach
dem M6-Lernbeweis separat gegen Place- und Scene-Asset-Anforderungen getestet.

### Cleanup und Dataset

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **Delete or Live** | Genau einen bereits abgelehnten oder ausgeschiedenen Kandidaten binär behalten oder endgültig löschen. | Bereinigt Dateien, verändert aber die zuvor gespeicherte Review-Evidence nicht. |
| **Coverage Quest** | Eine konkrete LoRA-Lücke wie Profil, Ganzkörper, Ausdruck, Hände oder Scene schließen. | Neue Coverage nur bei verwendbarem und ausreichend neuem Bild. |
| **Dataset Draft** | Aus mehr guten Bildern ein diverses, nicht redundantes Trainingsset wählen. | Dataset-Mitgliedschaft bleibt getrennt von Favorite und Championstatus. |
| **Clone Hunt** | Exakte Duplikate, Near Duplicates und schwächere Kopien erkennen. | Redundanz-Evidence und gezielte Materialbereinigung. |

### LoRA-Evaluation

| Bestands-/Arbeitsname, nicht freigegeben | Fachliche Aufgabe | Evidenz und Folge |
|---|---|---|
| **LoRA Blind Test** | Base, alte und neue LoRA-Varianten ohne sichtbare Herkunft vergleichen. | Misst echte Verbesserung, Flexibilität und Overfitting. |
| **LoRA Boss Fight** | Bekannte Kontrollen und neue Transfer-/Stressaufgaben kombinieren. | Bestätigt LoRA-Readiness oder erzeugt neue Coverage-, Repair- und Stability-Quests. |

### Technische Trial-Varianten

Sampler Duel, Parameter Trial, Workflow Trial, Checkpoint Trial, LoRA Ablation
und Style Trial sind kontrollierte technische Ausprägungen der obigen Modi.
Sie verwenden dieselbe Vierer- und Guided-Evidence-UI, verändern aber genau die
im `TrialContract` deklarierte technische Achse. Im normalen Spiel werden sie
als sichtbare Wirkung beschrieben; technische Namen und vollständige Diffs
bleiben im Advanced Workshop einsehbar.

## Inhaltseinstellungen als getrennter Scope

Inhaltseinstellungen sind keine bloßen Filter über denselben Pool. Für jede
aktive Einstellung wird pro bekannter Figur ein eigenes bereitstehendes Game
geplant. Der Scheduler wählt abhängig von dessen Zustand einen geeigneten Modus:

- Vierer-Qualifier, wenn Kandidaten fehlen,
- Stability oder Repair bei geringer Confidence beziehungsweise Fehlerclustern,
- 16er-K.-o.-Cup, sobald der getrennte Pool vollständig ist,
- Champion Defense bei vorhandenem Amtsinhaber.

Ein Ergebnis darf nie automatisch zwischen Inhaltseinstellungen Credit,
Championstatus oder Negativwissen übertragen.

## Vom Klick zum nächsten Batch

```text
GameResult
→ scoped GuidedImageEvidence
→ deterministische Rating-, Confidence- und Fehlerprojektion
→ offene Frage und ChampionSlot-Bedarf mit höchstem Informationswert
→ neuer QuestContract
→ aktueller Control-Arm plus deklarierte Mutation(en)
→ Orchestration-Guardian-Freigabe
→ nächster Viererbatch
```

Dieser Rückweg ist für jede spielbare Focus-Variante Pflicht und nicht nur eine
spätere Optimierungsoption. Ein abgeschlossenes Spiel aktualisiert zuerst die
gebundene Evidence-Projektion. Der Scheduler muss daraus anschließend explizit
eine der folgenden Wirkungen ableiten: vorhandene Kandidaten erneut vergleichen,
eine isolierte Challenger-Hypothese gegen einen neu gerenderten Control-Arm
testen, einen bestätigten Fehler reparieren, eine Coverage-Lücke schließen oder
eine begründete Exploration starten. Der daraus entstandene Batch wird wieder im
passenden Spiel bewertet. Auch A/B-, 16er- und Title-Match-Ergebnisse sind damit
Qualitätsevidenz und können spätere Challenge-Generierungen beeinflussen; sie
sind keine reinen Galerie- oder Ranglistenentscheidungen.

Der Scheduler erzeugt dabei nur einen deklarativen WorkIntent. Contract-,
Revisions-, Capability-, Ressourcen-, Backpressure- und Stalenessprüfung sowie
die begrenzte Freigabe des nächsten maschinellen Schritts folgen dem Vertrag in
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md).

Character-, Outfit-/Scene-/Pose-/Expression-/Lighting-, technische,
Recovery-/Coverage- und aktivierte Inhalts-Foci bleiben eigene Vergleichsräume.
Nur ein versionierter Contract darf Evidence zwischen kompatiblen Scopes teilen.
So kann beispielsweise ein `wrong_outfit` die nächste Outfit-Generation ändern,
ohne gleichzeitig Character Canon oder Scene-Geschmack umzuschreiben.

Beispiele für begrenzte Folgewirkung:

- `identity_hit` stärkt Identity Evidence, aber kein Outfit.
- `wrong_outfit` erzeugt eine Outfit-/Binding-Recovery, ohne Character Canon
  umzuschreiben.
- `bad_hands` darf Pose, Framing oder Anatomy Negatives challengen, aber keine
  Haarfarbe.
- `wrong_artstyle` betrifft Style-/Workflow-Compliance.
- `scene_contract_mismatch` routet zu Scene-/Composition-Recovery;
  `background_render_defect` dagegen zu Quality-, Workflow- oder Inpaint-
  Recovery und `scene_not_preferred` nur zu wiederholter Taste-Evidence.
- `alpha_halo` wiederholt bei gutem Source nur Matting/Defringe.
- Eine Geschmackspräferenz verändert erst nach wiederholter, vergleichbarer
  Evidenz persönliche Priors und niemals nach einem Einzelklick globale Regeln.

Breite Multi-Axis-Spiele liefern Recipe-/Combo-Evidence. Kausaler Token-,
Weight-, Komponenten- oder Parameter-Credit entsteht nur bei einem
kontrollierten Einzelachsenvergleich.

## Modulautorität und Implementierungsstufen

Der Spielkatalog beschreibt viele Modi, aber keine Sammlung unabhängiger
Screen-Implementierungen. Alle Zustandsübergänge liegen serverseitig und folgen
derselben Autoritätskette:

```text
quest: fachliche Frage, Focus, Scope und Credit-Vertrag
→ trial_runtime: Phase, Cursor, zulässige Action und Completion
→ review_evidence: unveränderliche Spielerentscheidungen
→ generation_knowledge: rebuildbare Ratings, Confidence und Credit
→ recovery: ausschließlich erlaubte Folgerichtung
→ generation: versionierter neuer Versuch
```

`cleanup` verwaltet davon getrennt Referral und Dateidisposition. `web_ui`
projiziert nur Serverzustand und darf weder Rating, Sessionphase, Recovery,
Champion noch Progress-Credit berechnen.

| Foundation-Schritt | Liefert einmalig | Spätere Bindung |
|---|---|---|
| M6.1 plus `GAP-026` | `QuestExperimentContract`, persistente Review-Session, Guided Evidence und Reject-Pending-Lifecycle; Spielerführung gemäß `PM-093`/`DEC-060` und `PM-094`/`DEC-061` korrigiert | Slices 3/5 zeigen dieselbe Session im Asset-/Gate-Kontext |
| M6.2 | fünf Layer, Projektionen und deterministische Recovery | Chronicle ergänzt nur Character-, Scene- und Requirement-IDs |
| M6.3 | gemeinsame Runtimes `single_image_two_pass`, `set_comparison`, `pairwise_comparison`, `bracket`, `curation`; `asset_qa` bleibt nur als späterer Runtimeport reserviert | Characters, Trials und Chronicle teilen dieselbe QuestSession; echte Asset-QA beginnt erst in Slice 3 |
| M6.4/M6.5 | Focus-/Mode-Rotation, rollierende Gruppenlineage und Dreierbeweis, danach Sechser- und Inhalts-Supply | Slice 5 bindet vorhandene Foki und Modes an Scene-/Playgates |
| M6.6 | Candidate Pool, Frozen Roster, Bracket, Champion und Title Match | Slice 6 projiziert Chronicle-Blocker und Rückweg |
| M6.7 | persönliche Content- und Generation-Knowledge | Slice 3 konsumiert den Compiler beim Character-Bootstrap |

Vor der Intro-/Cast-Umsetzung beweist `M6_LEARNING_LOOP_PROVEN` diesen gesamten
Kern mit Aiko, Kaori, Mizuki und Hina als Entwicklungs-Startmaterial. Der Proof
beginnt mit `evidence_policy=fresh_only`: Vorhandene Bilder werden in neuen
QuestSessions erneut bewertet und qualifiziert; ihre historischen Ratings
beeinflussen weder Pool noch Bracket, Recovery, Promotion oder Folgegeneration.
Kausaler Parameter-Credit verlangt vollständige Generation-Recipe-Provenienz.

Die praktische Spielerabnahme ist bewusst an diesen vollständigen Proof
gebunden und nicht an M6.1 oder einen anderen isolierten Teilslice. M6.1–M6.7
werden jeweils automatisiert und mit technischen Browser-Smoke-Tests geprüft.
Erst wenn Bewertung, Guided Evidence, Spielvariation, Candidate-/16er-Lifecycle,
neue Challenger-Generierung und Folgebewertung zusammenlaufen, beurteilt der
Spieler den Loop als Ganzes.

`fresh_only` bezieht sich auf Spielerurteile. Die im vorhandenen Material
belegten Promptgewichte, Komponenten-/Combo-Zusammensetzungen sowie Recipe-,
Sampler-, Scheduler-, Steps-, CFG-, Checkpoint-, Workflow- und LoRA-Werte bilden
als `DevelopmentGenerationBaseline` ausdrücklich die Startwerte. Neue Evidence
erzeugt darauf aufbauende Revisionen; sie startet nicht bei willkürlichen
technischen Nullwerten.

Die dazu verwendete Entwicklungs-/Testmatrix wird nicht separat authored. Ein
deterministischer Offline-Extractor projiziert die vorhandenen Playground-,
Combo-, Bild-, Rating-, Recipe- und Workflowdaten samt Bilddateien in ein
versioniertes Fixture-Manifest. Dieses beschreibt reale Komponenten- und
Bildabdeckung, gewichtete Promptstrukturen, beobachtete Parameterbereiche,
Vergleichsgruppen und Provenienzlücken. Historische Ratings dürfen daraus
Testfälle und Kalibrierungsverteilungen liefern, aber keine frische
Spielentscheidung oder Folgegeneration autorisieren.

Historische Reasons laufen auch im späteren optionalen Import nicht durch ein
LLM und werden nicht anhand ihrer Formulierung geraten. Nur eine eindeutige,
versionierte Codeabbildung verleiht ihnen dort einen neuen Layer. Unklare Werte
bleiben `legacy_unclassified`; weder sie noch gemappte Altgründe wirken im
ersten Learning-Proof. Ein späterer schwacher Prior darf keinen kausalen Token-,
Weight-, Component-, Focus- oder Recovery-Credit erzeugen.

Vor dem VN-Gate wird nicht nur ein einzelnes Ergebnis abgenommen. Mindestens
zwei aufeinanderfolgende Änderungs-/Wiederbewertungszyklen müssen Baseline oder
Parent-Revision, Hypothese, kontrolliertes Parameterdelta, neue Recipes, neue
Spieler-Evidence und Folgeentscheidung lückenlos verbinden. Eine read-only,
rebuildbare `LearningCycleMonitorProjection` zeigt pro Figur, Focus und
Inhaltsstufe Action-/Reason-Verhältnisse, Control-/Challenger-Ergebnisse,
Confidence, `4/4`-Ausbeute, Laufzeiten, Parameterdeltas, Provenienzlücken,
Scope-Leaks und Regressionen. Der Monitor beobachtet; er bewertet oder promotet
nicht selbst.

## Testbare Invarianten

1. Pro bekannter Figur sind höchstens sechs normale Vierer-Games `READY`.
2. Jede aktive sensible Inhaltseinstellung besitzt pro bekannter Figur höchstens
   ein zusätzliches `READY`-Game und einen getrennten Evidenzscope.
3. Ein Game ist erst bei validierten `4/4` Bildern spielbereit.
4. Ein zusätzlich sichtbarer 16er-Cup erzeugt keine neuen vier Bilder.
5. Der Vierer-Qualifier verbindet pro Bild Favorite/Keep/Reject und Reason;
   nach Bild vier folgt keine zweite Wiedervorlage. Ein playerseitiger Skip
   existiert nicht.
6. Der normale Reason Flow enthält weder Freitext noch Checkboxliste. Nur die
   positive und negative Bubble-Fläche scrollen unabhängig; Bild,
   Auswahlleiste, Primary-Markierung und `Weiter` bleiben sichtbar.
7. Vierer-Ranking und Arena erheben zuerst relative Evidence und danach pro
   weiterhin sichtbarem Bild genau einmal Favorite/Keep/Reject samt Reasons.
   Das Ranking erzwingt keine Dispositionsquote, aber die harte monotone Folge
   `Favorite* → Keep* → Reject*`; eine niedrigere Rangposition darf keine
   stärkere Disposition als eine höhere besitzen. In Arena darf der Gewinner
   ebenfalls keine schwächere Disposition als der Verlierer erhalten.
8. Relative Ranking-/Arena-Evidence wird abhängig von der anschließenden
   Dispositionskombination versioniert gewichtet und überschreibt diese nicht.
9. Der 16er-Cup erhebt pro Match ausschließlich den Sieger und weder neue
   Dispositionen noch Reasons.
10. Die auswählbaren und priorisierten Reason Codes sind mit Generierungsauftrag,
   Quest, Focus, Variationsachse, Assetrolle, Recipe und
   Inhaltseinstellung kompatibel.
11. Kein Modell darf einen Reason Code erfinden, auswählen oder als
   Spielerevidenz persistieren.
12. Positive und negative Reasons gehören immer zu genau einem Bild;
   Batchevidenz wird ausschließlich daraus projiziert.
13. Reject erzeugt keinen direkten Delete. Seine Referral bleibt bis zum
    Abschluss der bildweisen Begründung `awaiting_guided_evidence`; erst `ready`
    ist in Delete or Live sichtbar. Undo davor setzt sie append-only auf `void`.
    Delete or Live fragt den Grund nicht ein zweites Mal ab.
14. Ein Einzelbatch kann keinen globalen Component-, Weight-, Workflow- oder
    Style-Standard promoten.
15. Eine Quest schreibt nur in den vorab gebundenen Evidence- und Credit-Scope.
16. Die nächste Generation enthält einen gültigen Control-Arm und nur
    deklarierte Mutationen.
17. Ein 16er-Cup bleibt eine QuestSession und kann kein Playgatebudget über
    seine fünfzehn Matches vervielfachen.
18. Jede generierende Quest besitzt genau einen primären Generation Focus;
    Auswahlspiele ohne neue Bilder besitzen keinen erfundenen Generation Focus.
19. Game Mode allein bestimmt weder Generation Focus noch Evidence Scope.
20. `generation_intent`, `visual_defect`, `character_canon`, `asset_usability`
    und `aesthetic_preference` bleiben getrennte Evidence-Dimensionen.
21. Jede abgeschlossene generierende oder auswählende Focus-Quest besitzt einen
    nachvollziehbaren Folgezustand; bei offenem Lern-, Recovery- oder
    Coverage-Bedarf entsteht ein versionierter neuer Try und dessen erneute
    Spielerprüfung.
19. Die Vier-Figuren-Fixtures sind aus dem vorhandenen Korpus rebuildbar; eine
    manuell gepflegte Parallelmatrix darf nicht zur zweiten Wahrheit werden.
20. Ein visuell ähnlicher Befund wie „Hintergrund falsch“ muss zwischen
    Contract Mismatch, Render Defect und Taste unterscheiden.
21. Eine Recovery darf nur die durch Ebene, Focus Contract und Reason Code
    autorisierten Achsen verändern.
22. Zwei normale Ready-Slots derselben Figur testen nicht dieselbe Focus-
    Hypothese, sofern kein explizites blockierendes Multi-Requirement dies
    begründet.
23. Legacy-Gründe ohne eindeutiges versioniertes Mapping bleiben
    `legacy_unclassified` und erzeugen keinen kausalen Credit.
24. Character-, Trials- und Chronicle-Einstiege besitzen keine eigenen
    Sessionkerne für denselben Modus.
25. Jedes transportgültige, kontextkompatible Keep oder Favorite wird ohne
    zusätzliche Contender-Abstimmung challengerberechtigt.
26. Jedes aufgelöste A/B-Match erzeugt positive Gewinner- und negative
    Verlierer-Evidenz im gebundenen Vergleichskontext; ein Sieg setzt nur den
    aktuellen Favorite-Verlustfolgezähler zurück.
27. Ein abgelöster Amtsinhaber bleibt als `former_champion` geschützt im Pool.
28. Das sechzehnte rosterfähige Eligibility-Ereignis friert atomar die ersten
    sechzehn Einträge und ihre Bracketplätze ein; spätere Einträge warten auf
    den nächsten Cup.
29. Favorite-Niederlage eins und zwei pausieren jeweils für genau einen
    Championzyklus. Nach Verlust drei setzt DOA-`Live` das Favorite mit
    Verlustserie null und neuem Eligibility-Ereignis zurück in den Pool.
30. Evidence Ratio und Confidence bleiben pro Bild, Context Hash, Layer und
    Achse getrennt. Wenig Historie bedeutet hohe Unsicherheit, nicht automatisch
    geringe Qualität; verschiedene Achsen kompensieren einander nicht.
31. `fresh_only` leert die Spieler-Evidence, nicht die versionierte
    `DevelopmentGenerationBaseline` aus belegten technischen Startwerten.
32. Vor `M6_LEARNING_LOOP_PROVEN` sind mindestens zwei aufeinanderfolgende
    Änderungs-/Wiederbewertungszyklen monitorbar; jede Revision ist auf neue
    Spieler-Evidence und exakt deklarierte Änderungen zurückführbar.
33. `standard`, `sexy`, `lewd`, `nude` und `explicit` sind fünf getrennte
    Inhaltsstufen. Die letzten vier sind die vollständige NSFW-Variantenmenge.
34. Jedes Bild startet in einem kompatiblen Evidence-Kontext mit demselben
    neutralen Prior. Ein A/B-Match schreibt ohne Status- oder Corpusbonus genau
    eine Gewinner- und eine Verliererbeobachtung.
35. Prompt Aspect Groups werden aus den konkreten gewichteten Playground-Atomen
    durch Proposer/Judge abgeleitet und erst nach deterministischer vollständiger
    genau-einmaliger Atomzuordnung materialisiert; es gibt keine parallele
    handgeschriebene Token-Registry.

Frage, Chippriorität und zulässige Gründe werden für jedes Bild aus dem
gebundenen Quest-/Bildkontext kompiliert. Die versionierte Registry darf mit
neuen Modi wachsen; ihre vollständige globale Aufzählung ist keine offene
Produktentscheidung.

## Startwerte, adaptive Schärfung und technische Messwerte

Für den Beginn von M6.3/M6.4 fehlt kein manuell festzulegender Startwert. Die
Werteklassen werden wie folgt behandelt:

- Generierungsparameter starten aus der versionierten
  `DevelopmentGenerationBaseline` des existierenden Vier-Figuren-Materials.
  Der neutrale Evidence-Prior bleibt davon getrennt.
- Mode-/Focus-Rotation, Fairness, Wiederholungsabstand, Pairing- und
  Reason-Prioritäten sowie Confidence-/Promotionprojektionen starten mit einer
  konkreten versionierten Policy. Neue Generierungen und ihre frischen
  Bewertungen schreiben diese Policy nachvollziehbar fort. Sie sind deshalb
  adaptive Laufzeitwerte und keine vor der Umsetzung offene Kalibrierungsfrage.
- Copy, Animation, Belohnungsinszenierung und physische Eingabeabbildung sind
  barrierearme UX-Defaults. Sie werden im Browserplaytest verbessert, aber nicht
  aus Bildbewertungen gelernt.
- Prefetch-, VRAM-, Speicher- und Generierungszeitbudgets für 16 Figuren werden
  auf der Zielhardware gemessen. Readiness-, Safety- und Provider-Schwellen der
  feststehenden Inhaltsstufen werden in ihren vorgesehenen Safety-/Provider-
  Slices validiert. Diese technischen Messwerte ändern weder die bereits
  feststehenden fünf IDs `standard | sexy | lewd | nude | explicit` noch den
  hier definierten Spielzustandsablauf.

Jede adaptive Revision speichert mindestens Ausgangspolicy, Evidence-Cutoff,
veränderten Wert, Grund und beobachtete Folge. Ein stilles Ersetzen der
Startwerte oder ein Rückschluss aus ungeklärter historischer Evidence ist
unzulässig.
