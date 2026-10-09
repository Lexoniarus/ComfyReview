> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/card-battler-runtime-architecture.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Card Battler – Runtime-Architektur v0.1

Dokumentrolle: autoritativer technischer Zielvertrag für den ersten
Card-Battler-Vertical-Slice

Autorität: verbindliche Architektur für serverseitige Simulation,
Card-/Deck-Projektionen, PvE-Gegner, HTTP-API, Persistenz sowie die Trennung von
Phaser-Spielfeld und DOM-Oberflächen

Rules-Version: `card_battler_rules_v0.1`

Status: **Baseline abgeschlossen; implementierbarer Dokumentvertrag**

Stand: 14. September 2026

## Zweck und verbindliche Referenzen

Dieses Dokument übersetzt die abgeschlossenen Card-Battler-Regeln v0.1 in eine
implementierbare Laufzeitarchitektur. Es erfindet keine zweite Regelquelle. Die
fachlichen Regeln stehen weiterhin in:

- [`card-battler-board-and-combat-foundation.md`](card-battler-board-and-combat-foundation.md),
- [`card-battler-decks-turns-and-actions.md`](card-battler-decks-turns-and-actions.md),
- [`card-battler-effect-grammar-and-llm-authoring.md`](card-battler-effect-grammar-and-llm-authoring.md),
- [`card-battler-zones-statuses-and-opcode-registry.md`](card-battler-zones-statuses-and-opcode-registry.md),
- sowie
  [`card-crafting-and-playground-combination-lifecycle.md`](card-crafting-and-playground-combination-lifecycle.md),
- und dem presentation-only
  [`Kartenkunst-Kompositionsvertrag`](card-art-composition-and-rendering.md).

Die Runtime setzt diese Verträge deterministisch um. Browser, Phaser, DOM,
lokales LLM und PvE-Policy sind Adapter oder Projektionen und besitzen keine
Regelautorität.

Nicht Teil dieses Architekturstands sind Code, Datenbankmigrationen,
Dependency-Installation, Assets und konkrete Balanceänderungen. Menschliches
PvP, reales Matchmaking sowie WebSocket-/SSE-Echtzeittransport gehören nicht
zum Singleplayer-Produktpfad; ein Side-/Reserve-Deck ist nicht Teil von v0.1.

## Architekturprinzipien

1. **Serverautoritative Simulation:** Nur `card_battler` validiert Commands,
   verändert Matchzustand und entscheidet über legale Aktionen, Ziele,
   Auflösung und Matchende.
2. **Deterministischer Reducer:** Gleiche Rules-, Deck-, Karten-, Gegnerprofil-,
   Seed- und Commandfolge erzeugt denselben Eventstrom und Zustandshash.
3. **Eingefrorenes Match:** Ein Match referenziert unveränderliche Snapshots.
   Kartenentwicklung, Championwechsel und Bildlöschung außerhalb des Matchs
   verändern es nicht rückwirkend.
4. **Serialisierbarer Save:** Persistiert werden Domainzustand, Events,
   Snapshots und Receipts, niemals Phaser-Objekte, Tweens, DOM-State oder
   Dateipfade als fachliche Identität.
5. **Eine Inputgrenze:** Pointer, Touch und Tastatur werden im Browser auf
   semantische Aktionen abgebildet. Nur der API-Controller sendet Commands.
6. **Phaser plus DOM:** Phaser visualisiert Board und Bewegung. Das DOM besitzt
   textreiche, modale und barrierefreiheitssensitive Oberflächen.
7. **Keine Live-LLM-Regeln:** Die LLM benennt und erklärt bereits
   materialisierte Karteneffekte. Sie entscheidet weder Matchzüge noch
   Mechaniken oder Zahlen.

## Laufzeittopologie und Datenfluss

```text
Story Director / Network
  │  EncounterContract + Gegnerprofilrevision
  ▼
Deck-Readiness ──► Matchstart ──► eingefrorener MatchSnapshot
                                      │
Browser Input ──► HTTP Command ──► card_battler Reducer
                                      │
                     ┌────────────────┼────────────────┐
                     ▼                ▼                ▼
                 Domain Events   Match Head      Outbox Events
                     │                │                │
                     └────────────────┼────────────────┘
                                      ▼
                           Viewergefilterte Projektion
                              │                    │
                              ▼                    ▼
                       Phaser-Spielfeld       DOM-Overlay
```

Der Browser lädt immer eine vollständige, viewergefilterte Projektion einer
bestätigten `match_revision`. Animation Cues helfen beim Übergang von der zuvor
bestätigten zur neuen Projektion, sind aber weder Replay- noch Save-Autorität.

## Fachliche Module

| Modul | Autoritative Verantwortung | Darf nicht |
|---|---|---|
| `card_crafting` | Standardkörper, Craft Seed, CardRulesRevision, Branding, TraitLineage, Level Ups, CardBattleExperience, EvolutionRevisionen, CardArtCompositionRevisionen, CardFace-Render-Receipts und LLM-Copy-Receipt materialisieren | Matches auflösen oder Natursprachentext ausführbar machen |
| `card_collection` | CardIdentity, MemoryOrigin, aktive/historische Rules-, Branding-, Evolution-, Composition- und Face-Asset-Revisionen, Entwicklung, Availability und Reset auf Standard projizieren | laufende Matchsnapshots ändern |
| `deck` | benannte Decks revisionieren, exakt 40 einzigartige CardIdentities und Readiness prüfen | Karten kopieren oder eine ungültige Liste still starten |
| `card_battler` | MatchSnapshot, legal actions, Reducer, Ketten, Zonen, RNG, PvE-Policy, Ergebnis, Replay und post-match Usage Facts | Bildreview-, Champion-, Evolution- oder Delete-or-Live-State direkt schreiben |
| `story_director` | EncounterContract, Gegnerrolle, Storyeinsatz und erlaubte Resultfolgen binden | Matchregeln oder Kartenwerte überschreiben |
| `web_ui` | API-Controller, viewergefilterte Projektion, Input Mapping, DOM-Surfaces und Phaser-Adapter | fachlichen Zustand eigenständig fortschreiben |

`card_crafting → card_collection → deck → card_battler` ist die fachliche
Abhängigkeitsrichtung. `story_director` darf einen Encounter anbieten, startet
ihn aber erst nach positiver Deck-Readiness. Ein Battler-Ergebnis darf ein
versioniertes Story-/Reward-Event auslösen und deduplizierte Usage Facts für
eine nachgelagerte Kampferfahrungsprojektion liefern; es erzeugt niemals
Keep/Favorite, Championwechsel, EvolutionRevision, Challenger-Eignung oder
Delete-or-Live-Verlust.

## MatchAggregate und eingefrorener Snapshot

Der autoritative `CardBattlerMatch` führt mindestens:

```text
match_id
chronicle_run_id
encounter_contract_id
rules_version
match_revision
status = setup | active | completed | blocked_recovery
participants[]
first_player_id
active_player_id
priority_player_id
round_number
turn_number
phase
life_points_by_player
zones_by_player
field_slots_by_player
chain_state
pending_interaction
effect_instances
status_instances
usage_ledgers
turn_counters
rng_seed
rng_cursor
step_budget_cursor
result
state_hash
```

Der beim Start unveränderlich erzeugte `MatchSnapshot` bindet:

- genau zwei Participant Snapshots,
- die gewählte Player-Deckrevision und die Gegner-Deckrevision,
- alle 80 verwendeten CardIdentity-/CardRulesRevision-Bindungen,
- aktive CardBrandingRevisionen nur für Darstellung und erklärenden Text,
- aktive CardArtComposition-/CardFaceAssetRevisionen ausschließlich für die
  eingefrorene Darstellung; ein ausstehender Draft wird nie eingefroren,
- `card_battler_rules_v0.1`, Registry- und Balance-Policyrevisionen,
- die PvE-Gegnerprofilrevision,
- den Match Seed und die initiale RNG-Position,
- sowie den Story-/Encounter-Kontext ohne freie Regelparameter.

Jede Feldkarte erhält beim Eintritt eine eigene `field_card_instance_id`.
Zone Change beendet diese Instanz und ihre gebundenen EffectInstances. Die
CardIdentity und die matchweit eingefrorene CardRulesRevision bleiben erhalten.

## Matchzustände und Serverfortschritt

Der normale Zustandsfluss lautet:

```text
setup
→ initiative_choice
→ opening_hands
→ mulligan_commit
→ active turn loop
→ completed
```

`pending_interaction` ist kein paralleler Matchzustand, sondern beschreibt die
genau nächste menschliche Entscheidung innerhalb von `setup` oder `active`.
Sie enthält `interaction_id`, Typ, Actor, erlaubte Optionen und die Revision,
auf der sie beantwortet werden darf.

Nach jedem akzeptierten Spielercommand führt der Server eine begrenzte
`advance_until_player_input`-Schleife aus. Sie verarbeitet:

1. erzwungene Zustands- und Phasenübergänge,
2. Pflichttrigger und ihre deterministische Fallbackreihenfolge,
3. PvE-Aktionen über dieselbe Legal-Action- und Reducergrenze,
4. automatische Pässe, wenn der Mensch keine legale Reaktion besitzt,
5. sowie Matchende und die nächste echte Spielerentscheidung.

Die Schleife endet ausschließlich bei menschlicher Wahl, Matchende oder einem
technischen Step-Budget-Blocker. Ein technischer Blocker setzt
`blocked_recovery`, bewahrt die letzte bestätigte Revision und ist niemals eine
Spielniederlage.

## Command-Vertrag

Alle Spieleraktionen verwenden einen einheitlichen typisierten Envelope:

```text
command_id
match_id
expected_revision
actor_participant_id
command_type
payload
input_method? = pointer | touch | keyboard
client_elapsed_ms?
```

`command_id` ist für genau einen logischen Versuch stabil und idempotent.
`expected_revision` muss der aktuellen Matchrevision entsprechen. Ein Retry
derselben `command_id` liefert das zuvor gespeicherte Resultat. Eine fremde oder
veraltete Revision verändert nichts und liefert HTTP 409 samt aktueller
Spielerprojektion.

| Command | Verbindlicher Payload |
|---|---|
| `choose_first_player` | gewählter `participant_id`; nur durch den Initiativgewinner |
| `submit_mulligan` | Menge von null bis fünf eigenen `card_instance_id`s |
| `play_card` | Handinstanz, Zielslot, `face_up|face_down`, `attack|defense`, vollständige Opferauswahl |
| `change_battle_mode` | eigene Feldinstanz und Zielmodus |
| `move_card` | eigene Feldinstanz und gültiger freier Zielslot |
| `activate_trait` | Feldinstanz, AbilityRevision, gebundene Ziele und vollständige Kostenwahl |
| `declare_attack` | angreifende Feldinstanz, gewählte Angriffslinie und soweit erforderlich Ziel |
| `submit_choice` | aktuelle `interaction_id` plus Triggerreihenfolge, Ziele, Discard- oder andere registrierte Auswahl |
| `pass_priority` | aktuelle `interaction_id`; nur wenn ein optionales Reaktionsfenster offen ist |
| `advance_phase` | erwartete nächste Phase; nur ohne unerledigte Pflichtaktion oder Wahl |
| `concede` | keine fachlichen Zusatzdaten |

Physische Inputs sind kein Commandtyp. Drag-and-drop auf einen Slot und eine
Tastaturauswahl erzeugen denselben `play_card`-Command. Der Browser darf nur
Actions anbieten, die in `legal_actions` der aktuellen Projektion enthalten
sind; der Server validiert sie dennoch vollständig neu.

## Event- und Reducergrenze

Ein Command wird zunächst validiert und anschließend in null oder mehr
versionierte Domain Events übersetzt. Die initialen Eventfamilien sind:

- Match/Setup: `match_created`, `match_snapshot_frozen`,
  `initiative_determined`, `first_player_chosen`, `opening_hand_drawn`,
  `mulligan_committed`, `mulligan_resolved`;
- Turn/Phase: `turn_started`, `card_drawn`, `phase_advanced`,
  `hand_limit_discarded`, `turn_completed`;
- Karte/Feld: `card_played`, `card_revealed`, `battle_mode_changed`,
  `card_moved`, `card_destroyed`, `card_sacrificed`, `card_discarded`,
  `card_returned`, `card_banished`, `card_revived`;
- Fähigkeit/Kette: `ability_activated`, `trigger_collected`,
  `trigger_order_committed`, `chain_link_added`, `priority_passed`,
  `chain_link_resolved`, `effect_instance_created`,
  `effect_instance_removed`, `activation_negated`;
- Kampf/Ergebnis: `attack_declared`, `attack_redirected`,
  `attack_resolved`, `life_points_changed`, `mandatory_draw_failed`,
  `participant_conceded`, `match_completed`;
- Recovery: `match_step_budget_exhausted`, `match_recovery_resumed`.

Jedes Event besitzt mindestens `event_id`, `match_id`, `sequence`,
`causation_command_id`, `event_type`, `payload`, `rules_version` und
`created_at`. Zufallsresultate werden mit ihrem RNG-Cursor im Eventpayload
festgehalten; Replay ruft keinen neuen Zufall und keine LLM auf.

Ein Kettenglied löst atomar vollständig auf. Direkt danach prüft der Reducer
vor einem weiteren Kettenglied die Niederlagebedingungen. Werden beide
Teilnehmer durch dasselbe atomare Kettenglied niederlagenpflichtig, entsteht
ein Unentschieden. Sobald das Match terminal ist, werden verbleibende
Kettenglieder nicht mehr aufgelöst. Neue Trigger werden sonst erst nach der
bestehenden Kette gesammelt, wie im Effektvertrag definiert.

### Post-match Usage und Kampferfahrung

Der Reducer verändert während eines Matches niemals die Karte, mit der es
gestartet wurde. Erst das bestätigte `match_completed` materialisiert aus dem
append-only Eventstrom je eingesetzter CardIdentity einen deduplizierten
`CardBattleUsageFact`. Er darf beispielsweise regelgültiges Ausspielen,
aufgelöste Trait-Nutzung, Angriffs-/Verteidigungsbeitrag, entscheidende
Ereignisse und den klassifizierten Encountertyp enthalten.

Ein nachgelagerter, idempotenter Consumer im `card_crafting` reduziert diese
Facts unter einer versionierten Experience- und Anti-Farm-Policy zu
`CardBattleExperienceEvent`s. Replay, HTTP-Retry und erneute Outbox-Zustellung
dürfen dieselbe Erfahrung nicht doppelt schreiben. No-op-Ausspielungen,
sofortige Aufgabe, kollusive Wiederholungsmuster und andere definierte
Farmfälle werden verworfen oder gedeckelt. Der Matchausgang allein verleiht
keine Erfahrung und eine Niederlage bleibt außerhalb der visuellen
Eliminationsserien.

Usage Facts dürfen für alle Kartenquellen vorliegen. Die hier beschriebene
visuelle Memory-Evolution ist jedoch ausschließlich für eine zulässige
persönliche `personal_post`-Bildkarte definiert. Bildlose Standards besitzen
kein zu mythologisierendes Ursprungsbild; öffentliche Editionen folgen ihrer
eigenen editionsgebundenen Progressionspolicy und dürfen kein privates Memory
simulieren.

Erreicht die Projektion eine Schwelle, entsteht ausschließlich
`card_evolution_ready`. Neue Werte, Traits und Kartenkunst werden erst im
getrennten Crafting-/Evolutionvertrag materialisiert und gelten nur für künftig
gestartete Matches. Ein bereits laufender oder per Replay rekonstruierter
Snapshot bleibt auf seinen eingefrorenen Revisionen.

## PvE-Gegnerprofil

Ein `OpponentPolicyRevision` besteht aus:

```text
opponent_policy_revision_id
archetype
legal_action_feature_weights
phase_preferences
line_preferences
risk_profile
trait_family_preferences
conservation_thresholds
tie_break_order
search_depth = 0
policy_version
```

Für jeden Gegnerzug erzeugt `card_battler` zuerst die vollständige Menge
legaler Aktionen. Die Policy berechnet daraus einen ganzzahligen Score. Bei
Gleichstand entscheidet zuerst die persistierte `tie_break_order`, danach eine
seedgebundene Auswahl mit protokolliertem RNG-Cursor. Die Policy darf keine
illegale Aktion ergänzen und keine Karte außerhalb des MatchSnapshots kennen.

Storyrollen können unterschiedliche Profile referenzieren, etwa aggressiv,
defensiv, kontrollierend oder formationsorientiert. Natursprachliche
Charakterisierung und Matchdialog beeinflussen die Präsentation, niemals die
Legalität oder einen unprotokollierten Zug.

### Singleplayer-Gegnerbestand und Content-Readiness

Der Battlerzugang selbst besitzt keine Volljährigkeitsgrenze. Vor Deckbindung
und erneut vor Matchstart validiert `card_collection` jedoch die Quellenklasse
jeder Karte gegen den verifizierten Accountzustand. Minderjährige Accounts
dürfen ausschließlich `blank_standard` und `public_event` verwenden;
`personal_post` setzt einen volljährigen Besitzer sowie gültige Alters- und
Einwilligungsreceipts aller erkennbar dargestellten Personen voraus. Eine
öffentliche Edition besitzt eine eigene offizielle Rechtefreigabe und erzeugt
keine persönliche Post-, Relationship- oder Preference-Evidence.

Ein sichtbares `Online-Match` bleibt technisch immer PvE innerhalb desselben
Singleplayer-Saves. `opponent_source` unterscheidet mindestens
`core_cast_character` und `remote_platform_npc`. Nur der erste Typ darf einen
persistenten, vom `story_director` verwalteten Rivalry State des festen
16er-Casts referenzieren. Ein zufälliger Remote-NPC erhält keine freie
Aufwertung zur zusätzlichen Storyfigur.

Jede Gegner-Deckrevision beginnt regelgültig aus 40 bildlosen Standardkarten
und kann anschließend freigegebene persönliche Bildkarten sowie accountlokale
Instanzen gemeinsamer `PublicCardEdition`s binden. Eine generierte Bildrevision
ist erst gegnerdeckfähig, wenn ein persistiertes Human-
`CardContentApprovalReceipt` ihre technische und inhaltliche Verwendbarkeit
bestätigt. Bei persönlichen NPC-Karten des sichtbaren Gegnerpools bindet dieses
Receipt ein live oder zeitversetzt angesehenes Pack Opening eines gefolgten
Streamers, einen Gast-/Kollaborationsauftritt oder ein gezielt mit dem
Protagonisten geteiltes Opening.

Die dabei gespeicherte `CommunityPackReaction` ist weder
PlayerPreferenceEvidence des persönlichen Visual Circuits noch die
Keep-/Favorite-/Reject-Entscheidung des Besitzers. Sie darf nur das im Stream
tatsächlich offengelegte, durch `CardDisclosureContext` begrenzte
Protagonistenwissen materialisieren. Der nachgelagerte, seedgebundene
`NpcCardDraftReceipt` materialisiert allein die simulierte Präferenz des
NPC-Besitzers und darf vom Community-Ergebnis abweichen. Ein getrenntes
`EventTicketRewardReceipt` darf öffentliche Events oder Eventbooster
freischalten, aber weder Matchsnapshot noch Gegnerkarte, Kartenstärke,
BattlerRating oder Relationship verändern.

`OpponentSupplyProjection` trennt mindestens:

```text
rules_ready                 = regelgültiges 40er-Deck vorhanden
content_review_ready        = alle gebundenen Bilder human-bestätigt
stream_disclosure_ready     = persönliche Karten für den Spieler sichtbar geteilt
personal_card_count         = aktuell spielbare persönliche Bildkarten
public_edition_count        = aktuell gebundene öffentliche Editionen
matchmaking_ring_eligible   = deklarierte Schwelle des Rings erfüllt
```

Ein Match darf jederzeit Standardkarten enthalten. Pending, technisch
blockierte oder noch nicht human-bestätigte Bildbindungen gelangen dagegen
nicht in einen neuen MatchSnapshot. Die Vorproduktion darf während Prolog und
frühem Networkspiel asynchron weitere Gegnerbooster, öffentliche Editionen und
Kartenbindungen vorbereiten. Konkrete Ringgrößen und Mindestmengen sind
versionierte Supply Policy statt Bestandteil der Kampfregeln.

## Viewerprojektion und Hidden Information

`CardBattlerPlayerProjection` enthält mindestens:

```text
match_id
revision
status
rules_version
viewer_participant_id
public_state
private_state
legal_actions[]
pending_interaction?
animation_cues[]
resume_href
state_hash
```

Öffentlich sind Lebenspunkte, Phasen, Feldslots, offene Karten, Friedhöfe,
Banished-Zonen, Handanzahlen, Deckanzahlen, öffentliche Status und die
auflösende Kette. Der Besitzer sieht seine Hand vollständig. Gegnerische Hand
und Deckreihenfolge bleiben verborgen. Eine gegnerische verdeckte Feldkarte
liefert nur eine opake Feldinstanz, Position, Modus soweit regelöffentlich und
öffentliche Status; Identität, Regeln und Bild werden erst bei autorisiertem
Reveal projiziert.

`legal_actions` enthält typisierte Commands mit erlaubten Ziel- und
Auswahlkorridoren. Besitzt der Spieler in einem optionalen Reaktionsfenster
keine legale Reaktion, wird kein leerer Dialog projiziert; der Server passt
automatisch. Existiert mindestens eine Wahl, bleibt das Match ohne Zeitlimit
persistiert fortsetzbar.

## HTTP-API v0.1

Collection:

- `GET /api/vnext/card-collection`
- `GET /api/vnext/card-collection/cards/{card_id}`

Decks:

- `GET /api/vnext/card-decks`
- `POST /api/vnext/card-decks`
- `POST /api/vnext/card-decks/{deck_id}/revisions`
- `GET /api/vnext/card-decks/{deck_id}/readiness`

Matches:

- `POST /api/vnext/card-battler/matches`
- `GET /api/vnext/card-battler/matches/{match_id}`
- `POST /api/vnext/card-battler/matches/{match_id}/commands`

Der Matchstart akzeptiert `encounter_contract_id`, eine positiv geprüfte
`deck_revision_id` und einen Idempotency Key. Der Server bestimmt Gegnerdeck,
Gegnerprofil, Rules-Version und Seed über den EncounterContract und liefert die
erste viewergefilterte Projektion.

Der Command-Endpunkt antwortet synchron mit der nächsten bestätigten
`CardBattlerPlayerProjection`. HTTP 409 enthält dieselbe Projektion für die
aktuelle Serverrevision. Technische Recovery liefert einen benannten Blocker
und `resume_href`, keine fiktive Spieleraktion. v0.1 benötigt wegen des
rundenbasierten PvE-Ablaufs weder WebSocket noch SSE.

## Persistenzvertrag

Die Runtime-Datenbank benötigt mindestens folgende Tabellen oder gleichwertige
normalisierte Verträge:

- Collection/Crafting: `card_identities`, `card_rules_revisions`,
  `card_branding_revisions`, `card_development_events`,
  `card_memory_origin_revisions`, `card_battle_experience_events`,
  `card_battle_experience_projections`, `card_battle_experience_digests`,
  `card_evolution_trials`, `card_evolution_candidates`,
  `card_evolution_revisions`,
  `card_availability_events`, `card_craft_random_receipts`,
  `standard_card_templates`, `card_source_eligibility_receipts`;
- Decks: `card_decks`, `card_deck_revisions`, `card_deck_revision_items`,
  `deck_readiness_projections`;
- Match: `card_battler_matches`, `card_battler_participants`,
  `card_battler_deck_snapshots`, `card_battler_card_snapshots`,
  `card_battler_match_events`, `card_battler_match_heads`,
  `card_battler_command_receipts`;
- Gegner: `card_battler_opponent_policy_revisions`;
- Gegnerbestand und Freigabe: `card_battler_opponent_roster_revisions`,
  `card_battler_opponent_supply_projections`,
  `card_content_approval_receipts`, `npc_card_draft_receipts`,
  `public_card_editions`, `owned_public_card_bindings`;
- Integration: transaktionale Outbox, deduplizierte
  `card_battle_usage_facts` und Chronicle-/Story-Resultevents.

Jeder akzeptierte Command schreibt unter einer SQLite-Schreibtransaktion:

1. genau ein deduplizierendes Command Receipt,
2. die geordneten Domain Events,
3. den vollständigen serialisierbaren Match Head samt neuer Revision und Hash,
4. sowie deduplizierte Outbox Events für erlaubte externe Folgen.

Der Match Head ist die schnelle Resume-Quelle; der append-only Eventstrom ist
die Replay- und Auditquelle. Ein Replay muss den gespeicherten Hash jeder
Revision reproduzieren. Inkonsistenz blockiert das Match mit Recovery und wird
nicht durch eine Browserprojektion repariert.

## Bildlöschung und Reset auf Standard

Die physische Bilddatei, CardIdentity und CardRules-Historie sind getrennte
Lebenszyklen. Bei einem autorisierten `Delete` oder Fristablauf gilt:

1. ImageIdentity, Evidence, frühere Branding-/Rules-Revisionen, Titel- und
   Matchreferenzen bleiben als Tombstone erhalten.
2. Die aktive CardBrandingRevision wird beendet und kann nicht mehr angezeigt
   oder als Challenger verwendet werden.
3. Dieselbe CardIdentity erhält atomar eine neue aktive Revision ihres
   ursprünglichen bildlosen Standardtemplates: ursprüngliches Kampfprofil,
   Standard-ATK/DEF, keine Rarity, kein Level, kein Trait und kein Effekttext.
4. Decklisten behalten dieselbe CardIdentity und bleiben bei weiterhin genau 40
   einzigartigen Identitäten strukturell legal. Readiness wird neu projiziert.
5. Ein bereits gestartetes Match bleibt unverändert auf seinen eingefrorenen
   Karten- und Bildrevisionen reproduzierbar.

Es wird weder eine andere Standardkarte automatisch eingesetzt noch die
CardIdentity aus Deck oder Sammlung entfernt. Die UI unterscheidet
`Bildbindung gelöscht` von `CardIdentity aktiv als Standard`.

## Phaser-, DOM- und Inputgrenze

Das bestehende Vite-/TypeScript-Frontend erhält später eine eingebettete
Phaser-Runtime mit dünnen Scenes:

- `BootScene`: Phaser-Konfiguration und stabile Manifestregistrierung;
- `PreloadScene`: Kartenrahmen, Board, UI-nahe Texturen, FX und Audio laden;
- `BattleScene`: bestätigte Projektionen in Kartencontainer, Slots,
  Hervorhebungen, Kamera und Animationen übersetzen;
- optionale `DebugScene`: Revision, Hash, FPS und Animation Cue anzeigen.

Phaser-Container, Sprites, Partikel, Tweens und Kamera sind verwerfbarer
View-State. `BattleScene.update()` berechnet keine Regeln. Eine einzige
`BattlePresentationController`-Grenze nimmt Projektionen entgegen, ordnet
Animation Cues an und leitet semantische Inputs an den API-Controller weiter.

Im DOM bleiben:

- Battle-Home, Gegnerdetail, Deckauswahl und Readiness,
- Starthand-/Mulligan-Auswahl,
- Kartendetail und vollständiger Traittext,
- Ziel-, Opfer-, Triggerreihenfolge- und Reaktionsdialoge,
- Phase, Lebenspunkte, Hand-/Zonenzähler und verständliche Legalitätsgründe,
- Pause, Resume, Fehler, Recovery, Ergebnis und Story-/Reward-Folgeaktion,
- Tastaturfokus, Screenreadertexte und Reduced-Motion-Einstellung.

Der getrennte Kartenkunsteditor ist ebenfalls eine DOM-/Canvas-2D-Oberfläche.
Er verschiebt und skaliert ein Quellbild hinter einem revisionierten Frame,
sendet aber nur normalisierte semantische Transformcommands. Er verwendet
keine Phaser-Scene und berechnet weder Kartenregeln noch autoritative
Renderpixel. Während er aktiv ist, besitzt er Pointer-, Touch- und
Tastaturinput vollständig.

Der dauerhafte HUD-Rahmen bleibt klein und verdeckt das Fünf-Slot-Feld nicht.
Bei Reduced Motion springt die Darstellung direkt auf die bestätigte Projektion;
kein Animation Cue darf eine fachliche Bestätigung verzögern.

Das Input Mapping besitzt mindestens `confirm`, `cancel`, `inspect_card`,
`select_previous`, `select_next`, `select_slot`, `pass_priority`,
`advance_phase` und `pause`. Pointer, Touch und Tastatur werden zentral darauf
abgebildet. Ein Modal sperrt Boardinput, nicht aber den bereits bestätigten
Serverzustand.

Assets werden ausschließlich über stabile Manifest Keys adressiert und nach
`cards`, `board`, `ui`, `fx`, `audio` und `data` gruppiert. Eine Brandingrevision
referenziert eine stabile AssetVersion; ein Dateiname ist keine CardIdentity.

## Recovery, Fehler und Nebenläufigkeit

- **Reload/Browser Back:** `GET` lädt den letzten bestätigten Match Head und die
  aktuelle Pending Interaction. Unbestätigte lokale Auswahl wird verworfen.
- **Doppelklick/Retry:** gleiche `command_id` liefert dasselbe Receipt; es
  entsteht kein zweites Event.
- **Zweiter Tab:** veraltete `expected_revision` liefert HTTP 409 mit aktueller
  Projektion.
- **Clientabbruch nach Commit:** erneutes GET oder Command-Retry findet den
  bestätigten Zustand.
- **Ungültiger Command:** HTTP 422 bei falscher Form, HTTP 409 bei gültiger Form
  auf falscher Revision, keine Mutation.
- **Step-Budget:** Match wird `blocked_recovery`; ein idempotenter Resume-Pfad
  setzt exakt nach der letzten bestätigten Revision fort.
- **Asset fehlt:** Das Match bleibt spielbar und verwendet einen neutralen
  Kartenfallback; fehlende Darstellung ändert keine Regeln.
- **LLM nicht verfügbar:** Bereits materialisierte Regeln bleiben spielbar;
  lokalisierte Copy verwendet einen klaren technischen Fallback.
- **Policyfehler:** Gegnerzug wird nicht geraten. Das Match blockiert
  recoverbar mit Policy- und State-Hash-Provenienz.

## Debug, Replay und Abnahme

Die read-only Diagnose zeigt Match-ID, Rules-Version, Revision, State Hash,
Command-/Eventsequenz, RNG Seed/Cursor, eingefrorene Deck-/Karten-/Policy-
Revisionen, Pending Interaction, Step-Budget und letzten Blocker. Verdeckte
Information bleibt außerhalb eines ausdrücklich autorisierten
Entwicklungsmodus geschützt.

Verbindliche Tests und Fixtures:

1. Gleiche Inputs erzeugen denselben Eventstrom und Zustandshash.
2. Jede v0.1-Kampf-, Zonen-, Ketten-, Stacking- und Ausspielinvariante besitzt
   mindestens ein Reducer-Fixture.
3. Reload und Resume funktionieren in jeder Phase sowie bei Mulligan,
   Zielauswahl, Triggerreihenfolge und Reaktionsfenster.
4. Idempotency und Revision Conflict erzeugen keine doppelten Events.
5. Nach jedem Kettenglied wird Matchende geprüft; simultane Niederlage durch
   dasselbe Glied ergibt Unentschieden.
6. Gegnerprofile wählen ausschließlich legale und reproduzierbare Aktionen.
7. Gegnerhand, Deckreihenfolge und verdeckte Karten leaken keine Identität,
   Regeln oder Assets.
8. Bildlöschung setzt dieselbe CardIdentity auf Standard zurück, hält ein
   strukturell legales Deck stabil und verändert keinen laufenden Snapshot.
9. Phaser und DOM zeigen dieselbe Revision; übersprungene Animationen und
   Reduced Motion verändern kein Ergebnis.
10. Ein technischer Step-, Asset-, Policy- oder LLM-Fehler erzeugt keine
    Spielniederlage und bleibt fortsetzbar beziehungsweise erklärbar.
11. Ein sichtbares Online-Match benötigt keine menschliche Gegenstelle und
    reproduziert denselben PvE-Eventstrom vollständig save-lokal.
12. Keine unbestätigte fremde Bildbindung erreicht einen neuen MatchSnapshot;
    eine persönliche NPC-Karte im sichtbaren Gegnerpool benötigt zusätzlich ein
    öffentliches oder gezielt geteiltes Pack Opening.
13. Community-Reaktion und NPC-Draft bleiben getrennt reproduzierbar. Die
    Reaktion erzeugt keine PlayerPreferenceEvidence und höchstens das im Stream
    freigegebene Protagonistenwissen; der NPC-Draft bleibt alleinige Autorität
    für Keep, Favorite und Reject des Besitzers.
14. Remote-NPCs verwenden bekannte soziale Figuren nur bei materialisierter
    Social-Graph-Überschneidung; ein zufälliger Gegner wird kein neuer Rivale.
15. Mehrere Accounts können getrennte CardIdentities derselben öffentlichen
    Edition besitzen, ohne Deck- oder Matchzustand zu teilen.
16. Minderjährige Accounts können regelgültig mit Standard- und öffentlichen
    Eventkarten spielen, aber keine persönliche Postkarte besitzen, ins Deck
    binden oder in einen neuen MatchSnapshot übernehmen.
17. Öffentliche Eventkarten gelangen nur über eine offizielle Rechte- und
    Contentfreigabe ins Spiel und schreiben keine persönliche Bildpräferenz,
    Beziehung oder CharacterChampion-Qualifikation.
18. Nur ein bestätigtes `match_completed` kann Usage Facts schreiben; Retry,
    Replay und doppelte Outbox-Zustellung erzeugen keine doppelte
    CardBattleExperience.
19. Ein Match verändert keine seiner eingefrorenen Kartenrevisionen. Eine
    dadurch erreichte Evolutionsschwelle gilt frühestens für einen künftig
    gestarteten Matchsnapshot.
20. No-op-, Concede-, Kollusions- und Wiederholungsmuster werden durch die
    versionierte Anti-Farm-Policy verworfen oder gedeckelt.
21. `card_battler` darf `card_evolution_ready` vorbereiten, aber weder eine
    Evolutionsdarstellung auswählen noch CardRules- oder EvolutionRevisionen
    aktivieren.
22. Event-Tickets aus Stream-Pack-Openings verändern kein Matchresultat, keine
    Kartenwerte und keine Gegnerentscheidung; ihre Vergabe und Einlösung sind
    getrennte idempotente Reward-Receipts.

## Bewusst nach v0.1 verschoben

- Side-/Reserve-Decks und Best-of-Serien,
- Affinitäten oder weitere Deck-Synergieachsen,
- alternative oder seltene zusätzliche Siegbedingungen,
- zusätzliche Opcodes, Trigger und nicht additive Zahlenlayer,
- konkrete Balancekalibrierung von Profilverteilung, Budgets und Häufigkeiten,
- sowie finale visuelle Marke, FX-, Audio- und Animationstuning.

Diese Erweiterungen benötigen eine neue Rules-, Registry- oder
Presentation-Revision. Sie sind keine offenen Architekturblocker der Baseline
`card_battler_rules_v0.1`.

Menschliches PvP, reales Online-Matchmaking und fremder Live-Datentransport
sind nicht in diese Liste verschoben. Sie sind durch den verbindlichen
Singleplayer-Vertrag ausgeschlossen. Eine spätere Änderung wäre eine neue
Produktentscheidung und keine normale Rules-Erweiterung.
