# Story, Cast und Simulation

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 10. September 2026

## Verbindlicher Rahmen

- Ein `ChronicleRun` umfasst beide Academy-Jahre: April 2032 bis März 2033 und
  April 2033 bis März 2034.
- Gespielt werden 14 Tage pro Monat, insgesamt 336 Day Instances über
  24 Monate.
- 48 authored Special Slots tragen die großen Anime-/Academy-Ereignisse,
  davon 24 pro Jahr.
- Alle regulär eintretenden Studierenden und damit sämtliche Fokus- und
  Romancefiguren sind am ersten spielbaren Academy-Tag mindestens 18 Jahre alt.
- Der Übergang zwischen den Academy-Jahren erhält den vollständigen Story-,
  Relationship-, Knowledge-, Karten- und Visualzustand; er ist kein Ending
  und öffnet weder Abschlussaudit noch New Game Plus.
- Auch Routine-Schultage enthalten mindestens eine kleine VN- oder
  Chatinteraktion und können Bildspiele enthalten.
- Freigeschaltete VN-Szenen, Beziehungen, Character-Entwicklung und Endings
  bilden die langfristige Hauptbelohnung des Runs; Bildspiele und Card Battler
  rhythmisieren diesen Weg mit kürzeren Feedback- und Motivationsschleifen.
- Der hardcodierte Director bestimmt Wahrheit, Anwesenheit, erreichbare
  Szenenrahmen, erlaubte Spielerintents und den Korridor möglicher Statefolgen.

Routine-Schultage verwenden wiederholbare authored Event-Templates. Personality,
Relationship, Knowledge, Ort, Tageszeit und frühere Choices bestimmen deren
zulässige Varianten und Wirkungskorridore. Wiederverwendung bedeutet deshalb
denselben dramaturgischen Rahmen, nicht identischen Dialog, dieselbe konkrete
Situation oder identische Statefolgen. Ein lokales LLM realisiert innerhalb des
gewählten Vertrags die konkrete Szenenvariante einschließlich Dialog,
Nachrichten, Posts, kleiner Handlungen und emotionaler Reaktionen. Es besitzt
keine Autorität über Canon, Verfügbarkeit oder persistente Statefolgen.

### Generative Szenenrealisation und Spielerimpuls

`authored` bezeichnet im Storysystem den entworfenen Möglichkeitsraum und nicht
eine vollständig vorgeschriebene Textfassung. Ein Scene- oder Conversation-
Vertrag friert mindestens Anlass, Zeit, Ort, Participant Set, erlaubte Fakten,
Knowledge-Grenzen, mögliche Spielerintents, zulässige Variantenfamilien,
Content Scope, Effect Budget und mögliche Outcome Contracts ein. Innerhalb
dieser Grenzen darf das LLM eine neue konkrete Fassung der Situation erzeugen.

Bei ausgewählten sozialen und emotionalen Beats kann vor der Realisation eine
kurze spielerische Impulsphase liegen. Sie lässt den Spieler nicht den fertigen
Dialog schreiben, sondern erfasst beispielsweise Handlungsabsicht, emotionale
Färbung oder Intensität. Der genaue Minispielablauf ist noch zu authoren. Sein
Output ist immer ein validierter `PlayerReactionIntent` und niemals freier
Canon- oder Prompttext.

```text
Day-, Scene-, Character-, Relationship- und Knowledge-State
→ Director wählt einen erlaubten Szenen- und Wirkungskorridor
→ authored Choice, begrenzter Freitext oder Impuls-Minispiel
→ deterministisch validierter Spielerintent
→ LLM erzeugt konkrete Szenen-, Dialog-, Nachrichten- oder Postvariante
→ Validator prüft Fakten, Wissen, Teilnehmer, Ton- und Outcome-Grenzen
→ Director wendet höchstens den erlaubten persistenten Outcome an
```

Das LLM darf dabei vergängliche lokale Details, Formulierungen, Gesten,
Gesprächsübergänge und unterschiedliche emotionale Ausprägungen erfinden. Es
darf keine neue dauerhafte Beziehung, Erinnerung, Verabredung, Enthüllung,
Anwesenheit oder Welt-Wahrheit ohne einen dafür vorgesehenen Vertrag erzeugen.

## Storyzeit und Interaktionsverfügbarkeit

Storyzeit ist ein eventgetriebener Simulationszustand und keine Echtzeituhr.
Ein `DayInstance` besitzt authored Time Slots und einen aktuellen Ort. Nur ein
validierter Director-Übergang bewegt die Storyzeit weiter. Queue-, Render-,
LLM- oder reale Wartezeit verändert weder Tag noch Time Slot.

```text
DayInstance
├─ academy_year: 1 | 2
├─ calendar_day
├─ active_time_slot
├─ current_place_id
├─ reachable_place_ids[]
├─ available_activity_contract_ids[]
├─ available_scene_contract_ids[]
├─ interaction_availability[]
└─ advance_requirements[]
```

`current_place_id` und `reachable_place_ids` referenzieren ausschließlich
versionierte `PlaceNode`s des Save-`PlaceGraph`. Der Director projiziert pro
Ziel einen `PlaceAccessState` aus Wissen, Storyfreigabe, Zeit, Reiseaufwand,
aktiver Wohnbindung, Access Contract und gegebenenfalls noch fehlendem Visual
Bundle. Die Ortsauswahl darf unbekannte Character Homes, geheime Treffpunkte
oder nicht eingetretene Events nicht vorab offenlegen.

`available_activity_contract_ids` und `available_scene_contract_ids` sind
unabhängig. Ein erreichbarer Ort kann null VN-Szenen und dennoch mehrere
gültige Aktivitäten besitzen. Umgekehrt darf eine authored Szene einen
direkten plausiblen Ortswechsel binden, ohne dass der Spieler zuvor eine lokale
Routine auswählt.

```text
PlaceActivityContract
├─ activity_contract_id und place_id
├─ activity_kind: routine | study | work | rest | explore | shopping |
│  club_practice | battle_practice
├─ character_contexts[1..n]
│  ├─ character_id
│  └─ involvement_mode: co_present | remote | asynchronous | referenced
├─ presentation_mode: system | montage | minigame | short_visual
├─ visual_requirements[]
├─ time_cost und repeat_policy
├─ allowed_outcome_budget
├─ may_prepare_scene_contract_ids[]
├─ post_opportunity_contract_ids[1..n]
└─ blocker beziehungsweise unlock_hint
```

Ein `PlaceActivityContract` ist keine verkürzte freie LLM-Szene und ohne
mindestens einen validen Character-Kontext nicht zulässig. Er darf nur seine
registrierten Outcomes schreiben. `referenced` oder `asynchronous` erzeugt
allein weder Relationship-Effekt noch gemeinsame Memory oder Character
Knowledge; auch bei `co_present` oder `remote` benötigt jeder solche Write eine
explizite Outcome-Freigabe. Fehlende Character Assets blockieren nur
Aktivitäten und Szenen, die diese Figur sichtbar benötigen; sie sperren nicht
den gesamten bereits freigegebenen Orts-Hub.

Feed, Nachrichten, Booster, Bildspiele, Sammlung, Deckbau und Kalender sind
Systemhandlungen außerhalb dieses Vertrags. Reisen ist ein validierter
`PlaceGraph`-Übergang. Beides darf ohne CharacterActivityBinding verfügbar
sein, ist aber keine zeitverbrauchende Weltaktivität.

Jede abgeschlossene Aktivität materialisiert zusätzlich einen
`ActivityOutcomeContext` und mindestens einen dazu passenden
`PostOpportunityContract`. Damit kann auch aus einer nicht als VN-Szene
ausgespielten Alltagshandlung später ein Beitrag des Protagonisten, einer
beteiligten Figur oder eines zulässigen Orts-/Gruppenaccounts entstehen.
Opportunity bedeutet nicht automatische Veröffentlichung: Autorberechtigung,
Personality, Privacy, bisheriges Wissen und Feed-Pacing entscheiden, ob und
wann ein konkreter Post materialisiert wird.

Fehlt einer geplanten Szene Bildmaterial, bleibt dieselbe Szene mit ihrem
ursprünglichen Calendar- und Storykontext bestehen. Der Spieler darf andere
authorisierte Interaktionen oder Bildspiele nutzen. Sobald der echte Blocker
erfüllt ist, wird derselbe Scene Contract ohne künstlichen zusätzlichen Tag
erneut ausgewertet.

Für jede bekannte Figur projiziert der Director pro Time Slot genau einen
nachvollziehbaren Kontaktzustand:

```text
InteractionAvailability
├─ character_id
├─ channel: in_person | phone | none
├─ status: available | asset_blocked | story_locked | unavailable
├─ place_id oder null
├─ conversation_blueprint_id oder null
├─ session_class oder null
├─ consumes_time
└─ blocker beziehungsweise unlock_hint
```

Ein direkter Kontakt benötigt authored Anwesenheit am selben Ort und die
passenden Visual Requirements. Ein Handy-Chat benötigt mindestens einen
freigeschalteten Kontakt, ein bestätigtes Identitätsportrait und ein erlaubtes
Zeitfenster. Räumliche Trennung allein sperrt den Handykanal nicht.

## Begrenzte Interaction Sessions

Jede direkte oder telefonische Unterhaltung ist eine begrenzte
`InteractionSession`:

```text
InteractionSession
├─ interaction_session_id
├─ conversation_blueprint_id
├─ character_id und channel
├─ session_class
├─ player_input_mode: authored_choice | bounded_text | impulse_game
├─ max_player_turns
├─ allowed_intents[]
├─ scene_realization_contract_id
├─ effect_budget
├─ consumes_time
├─ cooldown_policy
└─ closing_behavior
```

Der Spieler darf eine Session vorzeitig beenden. Andernfalls schließt sie nach
ihrem authored Ziel oder Turn-Limit mit einer passenden Abschlussreaktion. Die
Session sammelt validierte Turn Evidence; der Director wendet ihren
deterministischen Outcome beim Abschluss einmal an. Wiederholte Formulierungen
desselben Intents erzeugen deshalb keinen unbegrenzten Relationship- oder
Personality-Fortschritt.

Mögliche Outcomes sind authored Änderungen an Relationship, Tension, Knowledge,
Memory, Topic- oder späterer Scene-Verfügbarkeit. Eine Personality-Wirkung
benötigt zusätzlich einen gültigen `PersonalityInputContract`, betrifft
höchstens eine primäre Achse und bleibt durch das Effect Budget begrenzt. Exakte
Turnzahlen, Cooldowns und Gewichte sind Balancewerte für spätere Playtests.

## Prolog

Der Chronicle-Run beginnt in seinem vorgesehenen MVP-Slice mit einem authored,
persönlichen Asset-unabhängigen Network-/Messenger-Opening. Dieser
`bootstrap_opening`-Zustand ist keine `vn_scene` und kein freigegebener
`location_hub`. Er darf feste ausgelieferte UI-, Typografie- und
Silhouettenmittel verwenden, benötigt aber keine save-spezifisch generierten
Character-Sprites, Hintergründe, Outfits oder Expressions. Erst nach den
jeweiligen Visual-Bundle- und Scene-Asset-Gates darf das Spiel in die erste echte
VN-Szene wechseln.

Das Opening fragt spielerisch und überwiegend indirekt ab:

- Geschlecht und Name des Spielercharakters,
- Reaktions-, Kommunikations- und soziale Präferenzsignale, aus denen eine
  gewichtete Nähe zu den 16 Personality Profiles abgeleitet wird,
- visuelle und narrative Präferenzen,
- Farb-, Character-, Uniform- und Settingtendenzen,
- sowie Signale für die erste Begegnungstrias.

Der sichtbare Rahmen ist in jedem neuen Run dieselbe standardisierte
Mutter-/Umzugskonversation in mehreren Chat Turns. Fragen, zulässige
Antwortformen, semantische Ziele und Auswertungsregeln sind authored und
versioniert. Konkrete Antworten dürfen die spätere Castinstanz verändern, aber
nicht den World Core oder die 16er-Personality-Topologie ersetzen.

Der Spieler ist dabei und im gesamten VN in First-Person-Perspektive präsent.
Name und Geschlecht wirken auf Castplanung, Anrede, Dialog- und
Simulationsverträge. Es gibt jedoch kein Player-Portrait, keinen Player-Sprite,
kein Player-Assetgate und keine Player-LoRA. Spiegel-, Gruppen- oder
Erinnerungsszenen dürfen diese Grenze nicht still aufheben.

Die Mutter erscheint innerhalb dieses Network-/Messenger-Rahmens zunächst als
authored, ausgelieferte Silhouette und nicht als generiertes VN-Sprite. Der
Prolog erzeugt
versionierte Preference Evidence und Requirements; er lässt ein LLM weder den
Cast noch die Story entscheiden.

Die sichtbare Unterhaltung darf wie ein natürlicher Chat beziehungsweise ein
VN-Gespräch wirken, ist fachlich aber keine freie `Character Chat`-Session. Jede
Prologinteraktion besitzt einen authored Vertrag. Der Director bestimmt Frage,
zulässige Antwortform, Zielslots, Wirkungskorridor und Folgeknoten. Ein LLM darf
weder die Bedeutung einer Antwort frei interpretieren noch zusätzliche Fragen,
Präferenzachsen, Storyfolgen oder Personality-Effekte erfinden.

### `PrologueInteractionContract`

```text
PrologueInteractionContract
├─ interaction_id und story_node_id
├─ speaker_id und authored_prompt_key
├─ response_mode: authored_choice | bounded_text
├─ allowed_target_slots[]
├─ allowed_effect_kinds[]
│  └─ preference | hard_lock | hard_exclusion | requirement
├─ choice_mappings[]
│  ├─ answer_id
│  ├─ target_effects[]
│  └─ next_story_node_id
├─ bounded_text_contract oder null
│  ├─ target_slot
│  ├─ accepted_value_type
│  ├─ validation_rule
│  └─ abstention_behavior
├─ per_interaction_effect_cap
└─ rules_version
```

`authored_choice` wird vollständig ohne LLM ausgewertet. `bounded_text` ist nur
für eine vorab benannte direkte Eingabe wie Name, Farbwort oder ausdrücklich
erfragtes Ausschlussmerkmal zulässig. Allgemeiner Smalltalk, mehrdeutige
Geschichten oder nicht angefragte Aussagen erzeugen keine visuellen Locks.

Der Prolog speichert für jede Antwort zunächst einen unveränderlichen Receipt:

```text
PrologueAnswerReceipt
├─ interaction_id und answer_sequence_no
├─ selected_answer_id oder raw_text
├─ response_mode
├─ rules_version
├─ accepted_at
└─ extraction_status: not_needed | pending | accepted | abstained | rejected
```

Direkt validierbare Werte werden durch Code normalisiert. Nur wenn das
`bounded_text_contract` sprachliche Normalisierung benötigt, darf ab dem dafür
autorisierten Bootstrap-Slice ein lokales LLM ein enges
`PrologueExtractionProposal` erzeugen:

```text
PrologueExtractionProposal
├─ target_slot: exakt der authored erlaubte Slot
├─ canonical_value oder null
├─ evidence_kind: direct_value | explicit_exclusion
├─ confidence
├─ supporting_text_span
└─ abstain: true | false
```

Der Validator verwirft zusätzliche Slots, nicht belegte Werte und jede
Personality-, Relationship- oder Storyinterpretation. Bei Mehrdeutigkeit muss
der Extractor abstain setzen; der Director kann dann eine authored Rückfrage
anzeigen. Roher Freitext wird niemals direkt zu einem Promptatom.

### Visuelles Präferenzregister des Prologs

Prologfragen dürfen ausschließlich vorab registrierte visuelle Achsen
beeinflussen. Der erste verbindliche Registry-Scope umfasst:

- Palette: Temperatur, Sättigung und Kontrast,
- Haare: Längenkorridor, Textur-/Formtendenz und natürliche gegenüber
  ungewöhnlicher Farbrichtung,
- Character-Silhouette: kompakt, lang, weich, kantig, formell oder locker,
- Outfit: Formalität, Layering, Uniformindividualisierung und
  Accessoire-Dichte,
- Scene: traditionell/modern, urban/naturnah, indoor/outdoor,
  Detail-/Personendichte und ruhige gegenüber belebter Wirkung,
- Lighting: Temperatur, Weichheit und Dramatik,
- visuelle Expressivität,
- sowie Composition-Tendenzen, soweit eine konkrete Prologszene sie sichtbar
  und verständlich abfragt.

Eine ausdrücklich abgefragte Lieblingsfarbe wird über eine zugängliche visuelle
Farbmatrix beziehungsweise einen Color Picker mit Sättigung und Helligkeit
gewählt; benannte Presets und Tastaturbedienung bleiben als Alternative
verfügbar. Der Code leitet daraus eine Palette mit direktem Ton, gedämpfter,
heller und dunkler Variante sowie passenden analogen und komplementären Tönen
ab. Er kopiert nicht denselben RGB-Wert auf Haare, Uniform, Cast und Welt.

Die abgeleitete Palette wirkt stark auf die erste Begegnung, aber nur als
begrenzter Tilt auf den übrigen Cast sowie auf World-, Uniform- und Scene-
Akzente. Zusammen mit 32 Blueprints, weiteren Prologentscheidungen, authored
Quoten, Preference Bridges, Diversity Constraints und Save Seed entsteht die
große Castvarianz; kein einzelnes Präferenzsignal darf sie kollabieren lassen.

Diese Achsen beschreiben Optik. Sie verändern weder Base Personality noch
Protagonist Behavior, Relationship oder Route. Social- und Narrative-Signale
werden in getrennte Profile geschrieben und dürfen nicht als visuelle
Eigenschaft einer Figur zurückübersetzt werden.

### Player Personality Affinity und Erstbegegnungen

Die sozialen Antworten der Mutter-Konversation erzeugen getrennt von visueller
Evidence ein `PlayerPersonalityAffinityProfile`. Es ist keine klinische oder
endgültige Typfestlegung des realen Spielers, sondern eine reproduzierbare
gewichtete Näheprojektion über alle 16 Base Profiles. Authored Mappingregeln
dürfen Ähnlichkeit, Ergänzung und Reibung unterschiedlich gewichten und leiten
daraus eine `EarlyEncounterRanking` ab.

```text
standardisierte Prologfragen und Answer Receipts
→ registrierte soziale beziehungsweise reaktionsbezogene Evidence
→ PlayerPersonalityAffinityProfile mit Gewichten für alle 16 Profile
→ authored Compatibility-/Contrast-Mapping
→ EarlyEncounterRanking
```

Das Ranking beeinflusst, welche Fokusfiguren der Protagonist am Anfang zuerst
und mit der größten sozialen Nähe erlebt. Es entfernt keine Figur, verändert
kein Base Personality Profile und legt keine Friendship, Romance oder Route
fest. Ein nahes Profil ist eine frühe Begegnungschance, keine garantierte
Beziehung.

Der Scope jedes Signals begrenzt seine späteren Konsumenten:

| Prologachse | Erlaubte visuelle Konsumenten |
|---|---|
| Palette und Kontrast | Character, Outfit, Scene und Lighting gemäß jeweiligem Scope |
| Haarform, -länge und Farbrichtung | ausschließlich Character Visual Specs |
| Character-Silhouette | Character Visual Specs und passende Character-Outfit-Bindings |
| Outfitformalität, Layering und Accessoires | Uniform Blueprint, Outfit und Character-Outfit-Bindings |
| Architektur, Natur, Urbanität und Dichte | World Canon und Scene |
| Lichttemperatur, Weichheit und Dramatik | Lighting und kompatible Scene-Intents |
| visuelle Expressivität | Expression- und ausgewählte Pose-Intents |
| Composition-Tendenz | Modifier und Asset-Role-geeignete Framing-Intents |

Ein Signal wird nicht automatisch an alle erlaubten Konsumenten verteilt. Sein
authored `scope` muss den konkreten Konsumenten zusätzlich freigeben. So darf
eine Farbwahl für die Schuluniform nicht still Haarfarben oder das gesamte
World Lighting beeinflussen.

### Deterministische Evidence-Erzeugung

Ein authored Choice-Effekt referenziert immer einen Registry-Wert und verwendet
eine kleine diskrete Wirkungsskala `-2 | -1 | +1 | +2` sowie einen
`confidence_cap` zwischen 0 und 1:

```json
{
  "answer_id": "wait_in_old_courtyard",
  "target_effects": [
    {"target": "visual.scene.architecture.traditional", "delta": 2},
    {"target": "visual.scene.nature.integrated", "delta": 2},
    {"target": "visual.palette.saturation.muted", "delta": 1},
    {"target": "visual.lighting.soft", "delta": 1}
  ],
  "confidence_cap": 0.35,
  "scope": ["world", "future_scene", "future_character"],
  "next_story_node_id": "arrival_continue"
}
```

Jeder einzelne Target-Effekt erzeugt ein versioniertes
`PreferenceEvidenceEvent` mit Receipt-, Interaction- und Rules-Version. Eine
Antwort darf mehrere schwache Signale liefern, aber ihr gesamter Betrag wird
durch `per_interaction_effect_cap` begrenzt. Direkte Locks und Ausschlüsse sind
separate Constraint Events und werden nicht als sehr hohe weiche Präferenz
modelliert.

```text
PreferenceEvidenceEvent
├─ evidence_id
├─ receipt_id und interaction_id
├─ rules_version
├─ target_key
├─ delta und applied_confidence
├─ effect_kind: preference | hard_lock | hard_exclusion | requirement
├─ scope[]
├─ source_strength: indirect | repeated | direct
├─ reversible
└─ created_at
```

Die Projektion zu einer `VisualTasteProfileRevision` ist Codeautorität:

1. Pro Registry-Wert wird der versionierte neutrale beziehungsweise authored
   Prior mit allen gültigen `delta × confidence`-Beiträgen summiert.
2. Negative Supports werden auf null begrenzt; die verbleibenden Werte einer
   Achse werden zu einer Verteilung normalisiert.
3. Confidence wird getrennt aus Menge, Direktheit und Wiederholung der Evidence
   berechnet und darf den höchsten beitragenden `confidence_cap` nicht durch
   bloße Mehrfachwirkung derselben Interaktion umgehen.
4. Bei unzureichender oder widersprüchlicher Evidence bleibt die Achse
   `unknown`; der Content-Compiler verwendet dann Diversity und neutrale Priors
   statt eine Spielerpräferenz zu erfinden.
5. Hard Locks und Hard Exclusions werden unverändert neben der Verteilung
   geführt und können durch weiche Scores niemals überstimmt werden.

Exakte Priors, Unknown-Schwellen und Confidence-Formel werden im Prolog-Spike
kalibriert. Nicht offen ist, dass dieselbe Receipt-Folge und Rules-Version exakt
dieselbe Profile Revision erzeugen müssen.

### Übergabe an die persönliche Prompt-Erzeugung

Der `PrologueOutputContract` enthält keine Promptwörter:

```text
PrologueOutputContract
├─ answer_receipt_ids[]
├─ preference_evidence_revision
├─ visual_taste_profile_revision
├─ hard_visual_locks[] und hard_visual_exclusions[]
├─ WorldCanonDraft und UniformBlueprintDraft
├─ cast_visual_planning_inputs
├─ starter_coverage_seed
└─ unresolved_required_inputs[]
```

Der nachgelagerte Coverage Allocator konsumiert nur die für eine Komponentenrolle
relevanten Ausschnitte. Er erzeugt daraus `ComponentIntent`-Objekte in den
Präferenzbändern `aligned`, `adjacent` und `exploratory`. Erst danach erzeugen
Component Designer und Prompt Lexicalizer einen `SemanticSpec` beziehungsweise
gewichtbare Promptatome. Der vollständige Vertrag steht in
[Foundation-Vertrag zum persönlichen Content Compiler](../foundation/adaptive-generation-learning.md#persönlicher-content-compiler-statt-ausgeliefertem-inhaltskatalog).

Ein vollständiger optischer Übersetzungsweg lautet damit beispielsweise:

```text
authored Antwort "im alten Innenhof warten"
→ vier schwache, gescopte PreferenceEvidenceEvents
→ höhere Supports für traditional, integrated nature, muted und soft light
→ neue VisualTasteProfileRevision mit weiterhin begrenzter Confidence
→ aligned Scene-Intent für einen ruhigen Schulort
→ SemanticSpec mit konkreter, neu entworfener Ortsstruktur
→ PromptTokenAtoms und deterministische Gewichte
```

Keiner der Zwischenschritte darf den sichtbaren Antworttext als Promptfragment
weiterreichen.

Direkte Eingaben dürfen konkrete Requirements für Schule, Uniform oder eine
Begegnungsfigur erzeugen; indirekte Choices liefern ausschließlich Evidence für
die authored Zielprofile. Slice 2 persistiert freien Usertext mit authored
Zielslot unverändert. Der nachgelagerte Bootstrap ab Slice 3 darf ihn nur über
das oben definierte enge Extraction-Schema normalisieren. Visuelle Evidence
darf die optische Ausrichtung erster Begegnungsrollen beeinflussen, aber niemals
ein Personality Base Profile auswählen oder ändern. Die Reihenfolge früher
Begegnungen folgt stattdessen dem getrennten `EarlyEncounterRanking` aus
sozialen Prologsignalen und den plausiblen Hooks des randomisierten
`CastSocialPlacementPlan`.

## Cast

- Es existieren 32 geschlechtsspezifische Blueprints: 16 Base Profiles mal zwei
  Geschlechtsvarianten.
- Ein Save instanziiert genau 16 aktive Fokusfiguren und besetzt jedes der 16
  Base Personality Profiles genau einmal mit einer zulässigen
  Geschlechtsvariante.
- Höchstens vier Fokusfiguren besitzen dasselbe Geschlecht wie der Spieler.
- Der Fokus liegt auf Figuren des anderen Geschlechts; das Spiel fragt kein
  gewünschtes Geschlecht der Gegenfiguren ab.
- Namen werden aus getrennten japanischen Vor- und Familiennamenpools
  deterministisch und kollisionsfrei vergeben.
- Blueprints sind Schablonen. Name, konkrete Optik, Character Brand,
  Beziehungen, Erinnerungen und Canon gehören zur Save-Instanz.

Die 16 Fokusfiguren sind der tief simulierte Kerncast und nicht der vollständige
Story-Cast der Welt. Wiederkehrende Familienmitglieder, Lehrkräfte,
Academy-Personal, Studierende außerhalb des Fokus-Casts, Residence-Figuren,
Clubkontakte, Rivalen, Plattformfiguren und weitere Storyrollen dürfen darüber
hinaus materialisiert werden. Sie verwenden ihrem narrativen Gewicht
entsprechend kleinere persistente Verträge und benötigen nicht automatisch eine
vollständige Friendship-/Romance-, Visual-Development- oder LoRA-Laufbahn.

Nicht alle 16 Figuren müssen in einem Run vollständig erkundet werden. Jede
Figur besitzt jedoch authored Friendship- und grundsätzlich möglichen
Love-Interest-Content. Romance wird erst nach einem Friendship Gate verfügbar.

### Randomisierte soziale Platzierung

Personality Profile, konkrete Figurenidentität und soziale Platzierung sind
getrennte Achsen. Nach Festlegung der 16 Profile lost ein reproduzierbarer,
constraint-basierter Cast-Allocator pro Save insbesondere neu aus:

- Vor- und Familienname,
- konkrete Optik und Character Brand innerhalb der Diversity-Grenzen,
- eigene Cohort beziehungsweise Klasse oder Parallelklasse,
- Wahlbereich und gemeinsame beziehungsweise getrennte Wahlkurse,
- Clubs und weitere Academy-Aktivitäten,
- mögliche Residence-, Stadt-, Plattform- und Battler-Kontexte,
- sowie zulässige vorbestehende Social Edges zwischen Figuren.

```text
16 feste Base Personality Profiles
+ Prolog-Evidence und EarlyEncounterRanking
+ Academy-Funktionsslots und Social-Graph-Regeln
+ Cast-, Gender-, Diversity- und Plausibilitätsconstraints
+ neuer Save Seed
= CastSocialPlacementPlan
```

Die akademische und soziale Platzierung bleibt innerhalb des Schemas
randomisiert und wird nicht aus einem Personality-Stereotyp abgeleitet. Ein
bestimmter Typ gehört deshalb nicht regelmäßig in dieselbe Klasse, denselben
Wahlkurs oder denselben Club. Das EarlyEncounterRanking wird erst gegen den
fertigen Platzierungsplan auf plausible Begegnungshooks projiziert; es darf die
randomisierte Weltverteilung nicht nachträglich in einen festen Castaufbau
zurückverwandeln.

Ein neuer Run mit neuem Save Seed darf bei denselben Prologantworten andere
Namen, Erscheinungsbilder, Klassen-, Kurs-, Club- und Beziehungskontexte
erzeugen. Innerhalb eines begonnenen Runs bleiben alle materialisierten
Identitäten, Platzierungen und Social Edges stabil und replaybar.

### Character Genesis Recipe und Lebensgeschichte

Das Base Personality Profile ist kein vollständiger Charakter und keine feste
Anime-Rolle. Es beschreibt den psychologischen Ausgangsraum, in dem eine pro
Save neu erzeugte Lebensgeschichte, Werte, erlernte Verhaltensweisen,
Interessen, soziale Rollen und gegenwärtige Konflikte zusammenwirken. Typische
Anime-Motive sind ausdrücklich als kombinierbare Fragmente erlaubt; kein
einzelnes Motiv darf allein die Figur definieren.

```text
CharacterGenesisRecipe
├─ base_personality_profile_id
├─ birth_date und age_at_academy_entry >= 18
├─ core_values[2..3]
├─ temperament_modifiers[1..3]
├─ anime_role_fragments[2..4]
├─ origin_and_living_context
├─ residence_binding_intent
├─ family_context
├─ formative_life_events[2..4]
├─ learned_behavior_traits[2..4]
├─ interests_and_skills[]
├─ weakness_or_insecurity
├─ academy_year_pressure_seeds[1..2]
├─ future_orientation
├─ relationship_history und personal_boundaries[]
├─ platform_stance, battler_stance und platform_reform_memory
├─ public_private_contrast
├─ academic_and_social_placement
├─ preexisting_social_edges[]
├─ hidden_facts[] mit Knowledge-/Reveal-Policy
└─ coherence_explanations[]
```

Fragmentfamilien umfassen mindestens soziale Anime-Rollen, Familien- und
Wohnformen, Bildungs- und Arbeitserfahrungen, Freundschafts- und
Beziehungsgeschichte, Erfolge und Niederlagen, Interessen und Talente,
öffentliche und private Selbstdarstellung, Plattform- und Battler-Erfahrung,
Zukunftsziele sowie aktuelle Verantwortungen und Belastungen. Der Registry ist
erweiterbar. Schwere Themen wie Missbrauch, Tod, gravierende Krankheit oder
Trauma sind keine allgemeinen Zufallsfragmente; sie benötigen eigene authored
Sensitivitäts-, Content- und Verarbeitungsverträge.

`platform_reform_memory` hält fest, wie die Figur den allgemein bekannten
Vorreform-Championship-Vorfall von 2027 wahrnahm und heute deutet. Zulässige
Quellen sind etwa Nachrichten, Schule, Familie, Fan-Community oder die spätere
offizielle Aufarbeitung. Die Haltung darf von Schutzbefürwortung über
Frühkultur-Nostalgie und Unternehmensskepsis bis zu persönlicher Betroffenheit
reichen, wird aber weder aus Personality noch aus Battlerstärke automatisch
abgeleitet.

Jedes prägende Lebensereignis ist als Ursache-Wirkungs-Kette modelliert:

```text
FormativeLifeEvent
├─ Zeitpunkt oder Altersphase
├─ beteiligte Personen und damaliger Kontext
├─ objektives Ereignis
├─ subjektive Interpretation der Figur
├─ entstandener Wert, Wunsch oder Schutzmechanismus
├─ heutige sichtbare Verhaltensfolge
├─ Knowledge Set
└─ Reveal Conditions
```

Ein Merkmal steht gegenüber dem Base Profile in genau einer erklärten
Beziehung: `aligned`, `adapted`, `counterpoint` oder `masked`. `aligned` folgt
naheliegend aus dem Profil; `adapted` ist eine erlernte Strategie;
`counterpoint` ist eine plausible überraschende Ausprägung; `masked` beschreibt
eine öffentliche Rolle, die vom privaten Verhalten abweicht. Personality setzt
damit Gewichte und Plausibilitätskorridore, aber keine stereotype Biografie.

Der Generator beziehungsweise ein strukturiertes LLM-Proposal darf eine Recipe
komponieren. Vor Materialisierung prüft deterministischer Code mindestens:

1. Personality-, Werte- und Verhaltenskohärenz,
2. biografische Erklärung von Counterpoints und Masken,
3. zeitliche, Alters-, Academy- und Wohnplausibilität einschließlich
   Volljährigkeit spätestens am ersten Academy-Tag,
4. realistische Vereinbarkeit von Stundenplan, Club, Arbeit und Verantwortung,
5. gegenseitige Konsistenz aller Social Edges und Knowledge Sets,
6. Cast-weite Rollen-, Motiv- und Lebensgeschichtsdiversität,
7. mindestens einen wiederkehrenden Begegnungskontext,
8. klare Reveal-Grenzen für verborgene Fakten,
9. Storypotenzial ohne vorab festgelegte Route,
10. eine zum Alter passende, nicht stereotype Erinnerung oder Nichtbeteiligung
    am Plattformvorfall von 2027,
11. und das Verbot unbegründeter Personality-, Gender- oder Optikstereotype.

Nach der Validierung wird aus der Recipe ein versioniertes
`CharacterCanonDossier`. Es ist für diesen Save persistenter World- und
Character Canon. Director, Scene Realizer, Character Speaker und RAG erhalten
nur den für Szene, Wissen und Reveal Policy zulässigen Ausschnitt. Eine spätere
LLM-Szene darf keine neue Familie, frühere Beziehung, Tragödie oder andere
biografische Tatsache improvisieren. Neue Lebensgeschichte entsteht nur durch
tatsächlich gespielte Ereignisse und daraus autorisierte Memories.

Das Dossier materialisiert aus dem `residence_binding_intent` eine
`CharacterResidenceBinding` mit genau einem für den aktuellen Storyzeitpunkt
primären `PlaceNode` sowie optionalen zusätzlichen und historischen
Wohnankern. Ein Umzug oder Wechsel des primären Haushalts ist ein versioniertes
Storyereignis und keine LLM-Improvisation. Wohnortwissen und tatsächlicher
Zugang bleiben getrennte Zustände.

### Visuelle Cast-Allokation und Varianz

Der Prolog erzeugt keine Character-Merkmale und keinen visuellen Default für den
gesamten Cast. Seine visuelle Evidence besitzt zwei getrennte Projektionen:

```text
VisualTasteProfileRevision
├─ GlobalCastVisualPreference
└─ FirstEncounterVisualPreference
```

`GlobalCastVisualPreference` darf die Verteilung des gesamten Casts nur begrenzt
verschieben. `FirstEncounterVisualPreference` darf stärker beeinflussen, welche
bereits geplanten Figuren zuerst sichtbar werden. Eine Antwort wie die Wahl
einer kurzhaarigen Silhouette darf daher die erste Begegnungsreihenfolge deutlich
und die globale Haarlängenverteilung nur schwach beeinflussen.

Vor dem ersten vollständigen Character-Design entsteht für alle 16 Figuren ein
gemeinsames Diversity-Skelett:

```text
CastCoverageSkeleton
├─ axis_quotas{}
│  ├─ required_value_families[]
│  ├─ minimum_counts{}
│  └─ maximum_counts{}
├─ pairwise_distance_policy
├─ primary_signature_policy
├─ cross_axis_association_caps
├─ preference_influence_caps{}
└─ rules_version
```

Erst danach wird die persönliche Evidence angewendet:

```text
authored CastCoverageSkeleton
+ begrenzte GlobalCastVisualPreference
+ World-, Uniform- und User-Constraints
+ kontrollierter Save-Seed
= CastVisualAllocationPlan für 16 Figuren
```

Eine Präferenz verändert also höchstens die erlaubte Quote, die konkrete
Verteilung von Taste Bridges und die spätere Encounter-Reihenfolge. Sie darf
keine Wertfamilie vollständig verdrängen. Exakte Quoten sind versionierte
Balancewerte. Für jede primäre Achse muss der Vertrag mindestens eine neutrale
Verteilung, Mindestabdeckung, Höchstanteil und maximalen Player-Shift benennen.

```text
CastVisualAllocationPlan
├─ cast_plan_id und rules_version
├─ source_visual_taste_profile_revision
├─ applied_preference_deltas{}
├─ axis_distributions{}
├─ character_allocations[16]
│  ├─ character_slot_id
│  ├─ allocated_axis_families{}
│  ├─ primary_preference_bridge
│  ├─ optional_secondary_preference_bridge
│  ├─ deliberately_varied_axes[]
│  ├─ counterpoint_axes[]
│  ├─ diversity_reservations[]
│  └─ forbidden_collision_signatures[]
└─ diversity_report
```

Eine `Preference Bridge` bedeutet, dass genau eine sichtbare Achse einer Figur
eine Spielerpräferenz erkennbar aufgreift. Eine optionale zweite Bridge ist nur
zulässig, wenn die übrigen Identitätsachsen ausreichend variieren. Dadurch kann
jede Figur persönlich relevant wirken, ohne das gesamte `VisualTasteProfile` zu
kopieren. Starke Präferenzen werden auf verschiedene Slots und Figuren verteilt:
eine kühle Farbpräferenz kann beispielsweise einmal Haar-/Akzentfarbe, einmal
Outfitpalette und einmal Signature Detail beeinflussen, statt viele identische
blaue Frisuren zu erzeugen.

Die primäre Identitätssignatur einer Figur besteht mindestens aus:

```text
hair silhouette family
+ dominant palette family
+ overall body/shape silhouette family
+ signature motif/accessory role
+ outfit presentation family
= PrimaryIdentitySignature
```

Keine zwei Figuren dürfen dieselbe `PrimaryIdentitySignature` besitzen. Gleiche
Einzelwerte bleiben erlaubt: Zwei Figuren dürfen beide kurze Haare haben, wenn
Struktur, Palette, Gesamtsilhouette, Signaturmotiv und Präsentation ausreichend
verschieden sind.

Visuelle Achsen werden zunächst orthogonal allokiert. Der Cast Allocator darf
keine Stereotype wie `short hair → energetic`, `glasses → analytical`,
`long hair → elegant`, `small silhouette → shy` oder `dark palette → serious`
als implizite Regel verwenden. Personality- und Storybindungen werden separat
angewendet und müssen als authored Constraint sichtbar sein.

### Deterministischer Cast-Allocator

Der Cast Allocator ist Codeautorität und arbeitet vor dem LLM:

1. Er erzeugt mehrere reproduzierbare neutrale 16er-Coverage-Kandidaten aus den
   authored Quoten.
2. Er wendet pro Achse nur den erlaubten `preference_influence_cap` an.
3. Er verteilt primäre und optionale sekundäre Preference Bridges balanciert
   über die 16 Slots.
4. Er permutiert die übrigen Achsen so, dass Cross-Axis-Korrelationen und
   stereotype Kopplungen begrenzt bleiben.
5. Er verwirft Pläne mit Quotenverletzung, Signaturduplikat oder zu geringer
   semantischer Distanz.
6. Unter den gültigen Kandidaten wählt er anhand einer versionierten
   Zielfunktion deterministisch den besten Plan.
7. Erst dieser Plan wird dem Component Designer übergeben. Das LLM darf Quoten,
   Taste Bridges oder reservierte Diversity-Achsen nicht ändern.

Kollidieren später zwei LLM-erzeugte `SemanticSpec`-Ergebnisse, wird nur der
schlechter passende beziehungsweise noch nicht stabilisierte Slot mit einem
präzisierten `ComponentIntent` neu entworfen. Der restliche Cast bleibt stabil.

### Messbare Diversity-Gates

„Deutlich unterschiedlich“ ist ein Servergate und keine freie LLM-Anweisung.
Jede `CastVisualAllocationPlan`-Revision erzeugt einen persistierten
`CastDiversityReport`:

```text
CastDiversityReport
├─ duplicate_primary_signature_count
├─ axis_coverage{}
├─ normalized_axis_entropy{}
├─ quota_deviation{}
├─ maximum_value_share{}
├─ pairwise_semantic_distance_matrix
├─ minimum_nearest_neighbor_distance
├─ cross_axis_associations{}
├─ preference_bridge_distribution{}
├─ preference_influence_cap_violations[]
├─ unresolved_or_collision_cases[]
└─ gate_status: pass | fail
```

Die semantische Distanz zweier Figuren wird als gewichtete Distanz über die
primären und sekundären Cast-Achsen berechnet. Ein identischer kanonischer Wert
liefert Distanz `0`, unterschiedliche Attribute innerhalb derselben Familie eine
partielle Distanz und unterschiedliche Hauptfamilien Distanz `1`. Die
rollenbezogenen Achsgewichte stammen aus der `CastDiversityPolicy`; freie
Promptwörter und reine Synonyme verändern die Distanz nicht.

```text
semantic_distance(A, B)
= Σ(axis_weight × canonical_axis_distance) / Σ(axis_weight)
```

Der Gate-Report bewertet sowohl mittlere paarweise Distanz als auch die
`minimum_nearest_neighbor_distance`. Ein hoher Durchschnitt darf somit kein
einzelnes beinahe identisches Figurenpaar verdecken. `normalized_axis_entropy`
ist eine Diagnose für ungewollte Konzentration; die verbindliche Sollverteilung
bleibt die authored Quote. Cross-Axis-Assoziationen messen, ob eigentlich
unabhängige Merkmale wiederholt gemeinsam auftreten. Die konkrete statistische
Methode und Schwelle sind Teil der versionierten Policy.

Ein Plan besteht das semantische Gate nur, wenn:

- alle 16 Slots vollständig und alle vorgeschriebenen Wertfamilien vertreten
  sind,
- keine primäre Identitätssignatur doppelt vorkommt,
- Minimum-, Maximum- und Player-Shift-Quoten jeder Hauptachse eingehalten sind,
- der jeweils ähnlichste Nachbar jeder Figur den kalibrierten semantischen
  Mindestabstand erreicht,
- keine unzulässig starke Kopplung zweier unabhängiger Achsen entsteht,
- Preference Bridges nicht auf wenige Figuren oder immer denselben sichtbaren
  Slot konzentriert sind,
- und keine Hard Locks, Exclusions oder authored Castregeln verletzt werden.

Die exakten Distanzgewichte, Quoten, Assoziations- und Mindestabstandsschwellen
werden innerhalb des bereits produktseitig entschiedenen `DEC-025` kalibriert.
Verbindlich sind bereits Einflussrichtung, Metriken, Fail-Closed-Gate und der
reproduzierbare Report.

Semantische Varianz allein garantiert noch keine sichtbare Varianz. Der initiale
Character-Render wird vollständig ohne Image-Embedding-Befund bewertet; eine
vorherige strukturierte VLM-Beschreibung darf ausschließlich als bestätigbare,
korrigierbare oder verwerfbare Maschinenbeobachtung sichtbar sein. Erst ein
transportgültiges, kontextkompatibles Favorite, eine scopekompatible `APPROVED
ChampionRevision` oder ausdrücklich kompatibles Legacy-Referenzmaterial erzeugt
die scopegebundene `ImageAnalysisBootstrapRevision`; ein Keep allein nicht.
Danach vergleicht ein
`RealizedCastDiversityReport` die geplanten Hauptachsen mit versionierten
Vision-Befunden und diagnostischen Bild-Embeddings. Vision und Embeddings dürfen
eine sichtbare Kollision melden, aber keine neue Character-Identität
autorisieren. Bei zu ähnlicher Realisierung wird ein kontrollierter Character-
oder Workflow-Challenger erzeugt. Der Spieler bestätigt weiterhin Canon und
Attraktivität.

Innerhalb derselben Figur gilt die umgekehrte Zielrichtung: hohe Cast-weite
Varianz, aber geringe Varianz der aktuell stabilisierten Identity Anchors über Outfits,
Posen, Expressions und Scenes hinweg.

## Academy-Run-Portfolio und gemeinsame visuelle Kontexte

Die visuelle Entwicklung wird auf Simulationsebene nicht ausschließlich als
Liste einzelner Character-Zustände projiziert. Der vollständige Run besitzt ein
`SchoolYearVisualPortfolio` mit Class-/Cast-Roster, Character-Portfolios,
Relationship-Portfolios, Ensemble-Portfolios, Scene Assets und einer
versionierten zeitlichen Visual-Plan-Projektion.

Single-Character-Karten gehören dem jeweiligen CharacterPortfolio. Gemeinsame
Friendship-, Romance-, Club-, Class- oder Storykarten gehören einem
Relationship- beziehungsweise EnsemblePortfolio mit kanonischem Participant
Set und werden lediglich in die beteiligten Character-Ansichten projiziert.
Relationship State darf authored gemeinsame Storymomente und daraus folgende
VisualRequirements oder Slots öffnen und priorisieren, aber weder eine
Evolution Challenge noch konkrete Optik bestimmen und auch keinen
Bildqualifikations-, Champion-, Stability-, Canon- oder Assetstatus vergeben.

Der vollständige Besitz-, Zeit-, Visibility-, Frontend- und
Orchestrierungsvertrag steht in
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md).

## Character State

```text
CharacterState
├─ CharacterIdentity und BrandCanon
├─ CharacterVisualArc und aktuelle CharacterVisualCanonRevision
├─ CharacterDevelopmentState
├─ BasePersonalityProfile und BaseAxisVector
├─ DevelopedAxisVector und CurrentPersonalityProfile
├─ PersonalityExpressionState
├─ RelationshipState zum Spieler
├─ SocialEdges zu anderen Figuren
├─ KnowledgeRecords und Beliefs
├─ VisualDevelopmentState
└─ Story- und Eventteilnahme
```

## Zeitliche visuelle Figurenentwicklung

Der Prolog legt für jede der 16 Figuren eine klare, Cast-kompatible
Ausgangsrichtung fest. Er friert die Figur jedoch nicht für den gesamten Run
ein. Jede Figur besitzt zusätzlich einen authored `CharacterVisualArc`, der
festlegt, welche Merkmale Identitätsanker sind, welche sich durch Story und
Beziehung entwickeln dürfen und welche lediglich zur aktuellen Darstellung
gehören. Diese authored Identity Anchors sind semantische Constraints und keine
ausgelieferten Referenzbilder, Bildvektoren oder persönlichen Anchor Sets; die
visuelle Referenzlineage entsteht erst aus frischer Player-Evidence.

```text
CharacterVisualArc
├─ initial_visual_direction
├─ system_locked_constraints[]
├─ deeply_stabilized_identity_anchors[]
├─ mutable_slots[] mit MutabilityClass und erlaubtem Korridor
├─ authored_visual_mutability_policy
├─ authored_milestone_hooks[]
├─ exclusions[] und cooldowns[]
└─ current_character_visual_canon_revision_id
```

Die Mutability Class ist Bestandteil jedes visuellen Slots:

| Klasse | Bedeutung | Beispiele |
|---|---|---|
| `system_locked` | gehört nicht zur visuellen Änderungsautorität des Spielers | Character-ID, historische Revisionen, Safety sowie fremde World-/Uniform-Hard-Constraints |
| `deeply_stabilized` | zentraler Identitätsanker mit hohem, durch Evidenz wachsendem Widerstand; nur innerhalb des authored Korridors und mit besonders starker Booster-Evidence challengebar | Gesichtsstruktur, grundlegende Silhouette, zentrale Signatur |
| `milestone_mutable` | wird erst an einem passenden Story- oder Character-Milestone für Bild-Challenges relevant; die visuelle Richtung stammt trotzdem nur aus Booster-Evidence | dauerhafte Stilphase, prägendes Accessoire |
| `evidence_mutable` | darf ausschließlich durch qualifizierte Booster-/Bildspiel-Evidence als kontrolliertes Experiment geöffnet werden | Haarfarbe, Haarschnitt, Brille, bevorzugte Palette |
| `presentation_mutable` | variiert kontextabhängig, ohne den Character Canon zu ändern | Outfitvariante, Pose, Expression, Scene-Framing |
| `ephemeral` | gilt ausschließlich für die konkrete Szene oder das konkrete Bild | temporäre Frisur, Lichtreflex, nasses Haar |

Damit ist beispielsweise „grüne statt blaue Haare“ weder grundsätzlich
verboten noch eine unmittelbare Chat- oder Storyanweisung. Es ist nur dann eine
mögliche Figurenentwicklung, wenn der Haarfarbslot den authored Korridor
besitzt und wiederholte qualifizierte Booster-/Bildspiel-Evidence einen
kontrollierten Versuch rechtfertigt. Gespräch, Relationship und Personality
dürfen weder diesen Korridor erweitern noch die visuelle Hypothese auswählen.

Der Änderungswiderstand ist dynamisch und nicht nur eine feste Slotfreigabe. Zu
Beginn besitzt eine Figur wenig bestätigte visuelle Evidenz; der Spieler kann
ihre Richtung deshalb vergleichsweise stark beeinflussen. Mit bestätigten
Portraits, Sprites, Outfits, mehreren unabhängigen Seeds und bewährten Recipes
steigt die `CharacterCanonStability` des betroffenen Slots. Eine spätere
Abweichung benötigt entsprechend stärkere und unabhängig wiederholte
Booster-/Bildspiel-Evidence innerhalb des authored Mutability-Korridors.

```text
ChangeResistanceSnapshot
├─ prompt_aspect_group_id und current_semantic_signature
├─ base_slot_resistance
├─ canon_stability und independent_evidence_count
├─ asset_role_coverage
├─ proposed_change_magnitude
├─ recency_and_cooldown
├─ independent_booster_evidence
├─ visual_hypothesis_confidence
└─ authored_mutability_limit
```

Friendship, Love Interest, Tension, Chatverlauf und Character Knowledge senken
diesen Widerstand nicht. Sie dürfen andere Scene- und Relationship-Varianten
öffnen, aber keine visuelle Gruppe challengebar machen. `system_locked`
Constraints, historische Revisionen sowie World- und Uniform-Canons bleiben
erhalten; jede tatsächliche visuelle Entwicklung muss aus Booster-/Bildspiel-
Evidence hervorgehen und den vollständigen Qualifier-, Title-Match- und
Compatibility-Prozess bestehen.

Jeder einzelne Evolution Try bindet genau eine versionierte
`PromptAspectGroup`. Sie ist die fachliche Einheit eines zusammenhängenden
Details und kann mehrere positive und negative Promptatome enthalten. So darf
die Gruppe `hair` alle auf Haare zielenden Farb-, Form-, Längen-, Textur- und
Konfliktatome gemeinsam ändern, während Gesicht, Körper, Outfit, Scene und
Artstyle eingefroren bleiben. Eine Challenge darf nicht gleichzeitig eine
zweite, unabhängige Gruppe wie `glasses` oder `outfit_style` verändern.

Numerische Gewichte innerhalb der Zielgruppe dürfen sich in authored Bändern
leicht mitverändern. Dadurch bleibt es ein einzelner Haar- beziehungsweise
Stil-Try, auch wenn mehrere Bracket-Prompts gemeinsam angepasst werden. Der
Versuch erhält dann Gruppen-/Recipe-Evidenz und keinen unbelegten kausalen Credit
für jedes einzelne Token oder Gewicht.

Auch Booster-Evidence verändert keinen Canon direkt:

```text
qualifizierte wiederholte Booster-/Bildspiel-Evidence
→ validierte VisualEvolutionProposal innerhalb authored Mutability
→ kontrollierte Evolution Challenge
→ bestätigter und validierter Champion
→ neue CharacterVisualCanonRevision
```

Chat, Post, Post-Reaction und soziale VN-Choices fehlen bewusst in dieser
Kette. Sie können einen authored Storykontext und damit einen darzustellenden
Assetbedarf eröffnen, liefern aber keine visuelle Hypothese und keinen
Prompt-, Recipe-, Champion- oder Canon-Credit.

Eine `CharacterVisualCanonRevision` speichert mindestens Parent Revision,
genau eine geänderte Prompt Aspect Group, beibehaltene Identity Anchors, Quelle
der Änderung,
Visual-Evidence- und Mutability-Snapshot, Championbild als Canon-Quelle und den
Story-Zeitpunkt, ab
dem sie wirksam ist. Frühere Bilder bleiben für frühere Storyzeitpunkte gültig;
zukünftige Requirements binden die dann aktive Revision. Outfit-, Scene- und
Recipe-Bindings werden gezielt auf Kompatibilität geprüft und nicht still
umgeschrieben.

Bildbewertungen können ebenfalls Entwicklungsevidenz liefern. Eine Variante
innerhalb der erlaubten visuellen Toleranz verbessert nur Stabilitäts- oder
Recipe-Wissen. Ein unbeabsichtigter Drift darf selbst bei positivem Rating den
Canon nicht still ersetzen. Erst wiederholte, kontextgebundene
`AppearanceEvolutionEvidence` kann eine passende Evolution Challenge anbieten.

Nach jeder Canon Revision wird die Cast-weite Diversity erneut gegen die
betroffenen Hauptachsen geprüft. Eine Überschneidung wie dieselbe Haarfarbe ist
zulässig, solange die gesamte `PrimaryIdentitySignature` unterscheidbar bleibt.
Bei einer echten Kollision wird nur die betroffene Revision beziehungsweise ihr
Challenger repariert; der übrige Cast wird nicht neu ausgewürfelt.

## Personality

Die vier kontinuierlichen Achsen `I/E`, `S/N`, `T/F` und `J/P` bilden eine
geschlossene Topologie aus genau 16 Typen. Base Profile und Base Axis Vector
bleiben unverändert. Authored VN-Choices und validierte Chatintents dürfen pro
Turn genau eine primäre Achse begrenzt bewegen. Aus dem Developed Axis Vector
wird der Current Type deterministisch abgeleitet.

Bildratings, Navigation und visuelle Präferenzsignale verändern Personality
nicht. LLMs und Embeddings besitzen keine Schreibautorität.

## Beziehung und Route

`RelationshipState` trennt langfristige Werte wie Familiarity, Trust,
Affection und Bond Level von kurzfristiger Tension. Friendship und Romance
teilen zunächst dieselbe Vertrauensbasis und verzweigen erst an authored Intent
Gates. Mehrere parallele Love-Interest-Versuche haben nur dann Konsequenzen,
wenn die beteiligten Figuren davon wissen und ihre Character-Regeln darauf
reagieren.

Für visuelle gemeinsame Momente erzeugt eine authored Relationship- oder
Routeänderung eine `RelationshipVisualContextRevision`. Sie friert Participant
Set, Knowledge-, Canon-, Storyzeit-, Content- und Composition-Kontext ein. Das
Relationship Gate darf daraus neue gemeinsame VisualRequirements oder Slots
materialisieren; jede Bildqualifikation, jeder Cup und jede technische
Freigabe folgt weiterhin den allgemeinen Bild- und Championverträgen.

## Wissen

World Canon, tatsächliche Ereignisse, Character Knowledge, Beliefs und
Spielerpräferenzen bleiben getrennte Domänen. Teilnahme an einer Szene erzeugt
deterministische Knowledge Events. Offscreen-Konversation ist nur über
authorisierte Story Events und vorhandene Social Edges zulässig.

## Minimale testbare Simulation

Vor einer Skalierung auf das ganze Jahr muss ein Slice beweisen:

1. Prologchoice erzeugt reproduzierbare Preference Evidence.
2. Begrenzter Prolog-Freitext kann nur den authored Zielslot befüllen oder
   abstain setzen; zusätzliche visuelle oder Personality-Slots werden verworfen.
3. Dieselben Answer Receipts und dieselbe Rules-Version erzeugen dieselbe
   `VisualTasteProfileRevision` und denselben Starter-Coverage-Input.
4. Der Cast Allocator erzeugt 16 vollständige Slots ohne doppelte primäre
   Identitätssignatur und verwirft einen Fixture-Plan mit Preference Collapse.
5. Eine einzelne Haar- oder Farbpräferenz kann die erlaubte Castquote nur bis
   zum versionierten Influence Cap verschieben.
6. Eine Figur wird aus einem Blueprint mit stabiler Save-Identität instanziiert.
7. Eine VN-Choice verändert genau die erlaubten Character- und
   Relationshipfelder.
8. Save/Load reproduziert denselben State.
9. Ein zweiter Charakter erhält Wissen nur durch Teilnahme oder authored
   Propagation.
10. Der Director liefert nach Reload dieselbe erlaubte nächste Szene.
11. Ein Chat- oder Social Event kann weder visuellen Canon noch visuelle
    Evidence verändern; ein Ratingevent kann Evidence liefern, aber keinen Canon
    direkt verändern.
12. Nur eine bestandene Evolution Challenge erzeugt eine neue, zeitlich
    gebundene `CharacterVisualCanonRevision`; alte Storybilder bleiben gültig.
13. Eine Canon Revision verletzt keine `system_locked` Constraints und erhält
    die Cast-weite Mindestunterscheidbarkeit.
14. Niedrige Canon Stability benötigt bei gleicher Änderungsgröße weniger
    unabhängige Booster-/Bildspiel-Evidence als eine über viele Assetrollen
    stabilisierte Figur.
15. Maximale Freundschaft und maximaler Love-Interest-Status öffnen keinen
    charactereigenen visuellen Slot und senken keinen Änderungswiderstand.
16. Ein Evolution Try verändert genau eine `PromptAspectGroup`; alle nicht
    zugehörigen positiven und negativen Promptatome sowie ihre Gewichte bleiben
    Teil der Fixed Signature.
17. Variieren Semantik und Gewichte innerhalb derselben Zielgruppe gemeinsam,
    entsteht nur Gruppen-/Recipe-Credit und kein kausaler Atom-Credit.
18. Ein neuer Run beginnt reproduzierbar in `bootstrap_opening`/
    `network_fullscreen`; ohne persönliche Visual Bundles kann weder ein
    `location_hub` noch eine `vn_scene` freigeschaltet werden.

## Noch zu authoren beziehungsweise kalibrieren

- konkrete 32 Blueprint-Packs und Influence Bounds,
- vollständige Prolog-Fragebank mit `PrologueInteractionContract` pro Frage,
  vollständigem Evidence Mapping, Effect Caps, authored Rückfragen und
  Bounded-Text-/Abstention-Fällen,
- konkrete Registry-Werte, neutrale Priors, Unknown-Schwellen und
  Confidence-Projektion des `VisualTasteProfile`,
- numerische Ausprägung des entschiedenen visuellen Cast-
  Instanziierungsvertrags, der Blueprint, Prolog-Evidenz, abgeleitete Palette,
  Save Seed und Cast-weite Diversity Constraints reproduzierbar in konkrete
  Gesichter, Haare, Farbwelten, Körper-/Mode-Silhouetten und Character Brand
  Seeds der 16 Figuren übersetzt,
- exakte authored Quoten, Player-Influence-Caps, semantische Distanzgewichte,
  Cross-Axis-Assoziationsgrenzen und Schwellen des semantischen sowie realisierten
  Cast-Diversity-Gates,
- konkrete Registry-Zuordnung und numerische Caps für die bereits entschiedene
  Trennung aus indirekt beeinflussten, authored gebundenen und kontrolliert
  variierten Merkmalen,
- zunächst konservative Basiswiderstände, Stability-Projektion, authored
  Mutability-Korridore, benötigte unabhängige Booster-Evidence, Cooldowns und
  Evolutionskorridore pro Blueprint; ihre finale Balance ist ausdrücklich bis
  nach einem spielbaren VN-Kern vertagt,
- Calendar- und Scene-Daten für 336 Tage und 48 Specials mit eigenem
  Übergangsvertrag zwischen Academy-Jahr 1 und 2,
- Umfang geteilter gegenüber geschlechtsspezifischer Storymodule und die erst in
  Slice 13 kalibrierte Dichte einzigartiger gegenüber wiederholbarer authored
  Event-Templates,
- Relationship-Schwellen und konkrete Route-Milestones,
- sowie Interaction Budget pro Day Instance.
