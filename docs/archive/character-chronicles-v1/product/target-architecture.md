> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/target-architecture.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Zielarchitektur und Modulgrenzen

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 14. September 2026

## Architekturprinzip

Die bestehende Bildpipeline wird nicht ersetzt. Der vollständige MVP legt eine
serialisierbare Story- und Mehrfiguren-Simulation darüber. Die Simulation ist
Source of Truth; Browseroberfläche, Bildrenderer, LLMs und Retrieval sind
Adapter beziehungsweise Projektionen.

Für den persönlichen Playground gilt dabei ein schema-first Empty Bootstrap:
Ein neuer Save kennt das versionierte Datenbankschema, enthält aber noch keine
persönlichen Komponenten-, Combo-, Rating- oder Embedding-Zeilen. Die Prompt
Machine lässt die LLM nur strukturierte Kandidaten erzeugen. Deterministischer
Anwendungscode validiert und normalisiert sie, vergibt IDs und numerische
Gewichte und materialisiert erst dann revisionierte Runtime-Daten. Bereits
vorhandene Playground-Bestände gelangen ausschließlich über einen expliziten
Import mit demselben Validator und Provenienzvertrag in den Save; sie werden
weder automatisch geladen noch vektorisiert. Retrieval und Kosinusähnlichkeit
sind rebuildbare Kandidatenprojektionen und keine Schreib- oder
Entscheidungsautorität.

Der produktive Save besitzt genau eine autoritative Runtime-Datenbank. Alle
fachlichen Beziehungen werden dort über stabile Primär- und Fremdschlüssel
beziehungsweise unveränderliche Events und Revisionszeilen hergestellt. Die
heute noch getrennten Ratings-, Playground-, Images-, Prompt- und Combo-SQLites
sind ausschließlich signierte read-only Quellen des Development-Imports; nach
Cutover existieren weder direkte Runtime-Lesewege noch Dual-Write oder eine
zweite Wahrheit. PNG-/JSON-Dateien bleiben externe Artefakte. Die Runtime-DB
bewahrt zu ihnen Identität, Hash-/Pfadhistorie, Verfügbarkeit und
Löschprovenienz, auch wenn der Dateikörper physisch entfernt wurde.

### Laufzeittopologie

```text
Browser → API-/Game-Prozess → Domainmutation + transaktionale Outbox
                              ↓
                       Coordinator-Lane
             ↓             ↓             ↓             ↓
        LM-Studio       ComfyUI     Image-Analyse   Maintenance
                              ↓
                    persistierte Projektionen → API → Browser
```

Der Card Battler folgt derselben Topologie. Sein serverseitiger deterministischer
Reducer bleibt die einzige Regel- und Save-Autorität. Das spätere Vite-Frontend
verwendet Phaser ausschließlich für Spielfeld, Kartenbewegung und Effekte;
Deckwahl, Regeltext, Entscheidungen, Accessibility und Recovery bleiben im DOM.
Der vollständige Vertrag steht in der
[`Card-Battler-Runtime-Architektur`](card-battler-runtime-architecture.md).

`main.py` beaufsichtigt API und Worker als getrennte Prozesse. Diese Rollen sind
operative Adapter, keine neuen fachlichen Ebenen: Simulation, Quest-,
Spiel-/Wettbewerbs-, Bildkarten- und Evidence-Verträge bleiben die Autorität.
Eine offene Campaign-Session sperrt nur einen zweiten Start derselben Campaign;
Ready-Quests anderer Campaigns sowie Navigation und Reviews bleiben unabhängig
von Hintergrundarbeit nutzbar.

Schema 57 zieht dieselbe Grenze innerhalb der gemeinsamen SQLite-Persistenz.
Ein Spielercommand bestätigt ausschließlich einen kurzen Domaincommit mit
Sessionrevision, gegebenenfalls Credit, erweitertem Idempotenzbeleg und genau
einem Outboxauftrag. Evidence-, Knowledge-, Monitoring-, Rack-, Director- und
Supply-Projektionen folgen im Coordinator. Die mehrstufige M6-Materialisierung
berechnet Diffs und Hashes außerhalb einer Schreibtransaktion, checkpointet
vorbereitete Artefakte einzeln und veröffentlicht Plan, vier Slots und
ComfyUI-Handoff erst im kurzen finalen Commit. Vorbereitete Artefakte sind weder
spielbar noch evidence-fähig.

Spieler-GETs lesen einen gemeinsamen `query_only`-Snapshot unter WAL. Der
Browser hält unbestätigte Spielercommands mit ihrem stabilen Idempotency-Key
lokal vor und sendet nach Reload denselben Command erneut; er speichert dabei
keine Bilder, Header, Providerdaten oder Secrets. Eine sichtbare Supply-
Revision ersetzt nur die betroffene Campaign-Gruppe. Sie darf weder den
Scroll-/Fokuszustand anderer Gruppen noch eine laufende Reason-Auswahl
zurücksetzen.

Der persönliche Produktionskatalog darf leer beginnen. Die sieben Content-
Rollen `character`, `outfit`, `scene`, `pose`, `expression`, `lighting` und
`modifier` entstehen über den persistierten Authoring-DAG oder werden als
Child-ComponentVersion innerhalb eines akzeptierten `TypedMutationCorridor`
weiterentwickelt. `style_core` bleibt eine getrennte Revisionsdomäne. Der
Development-Playground ist Vokabular und Cohort, keine Produktvoraussetzung.

```text
Authoring Content + Rules Snapshots
                 │
                 ▼
        Chronicle Simulation
  ┌──────────────┼──────────────┐
  ▼              ▼              ▼
Story/Calendar  Visual Needs   Character State
  │              │              │
  └──────────────┼──────────────┘
                 ▼
       Quest and Asset Planning
                 ▼
 vorhandene Generation/Review/Evidence-Pipeline
                 ▼
     geprüfte Assets und LoRA-Datensätze
```

## Fachliche Module

| Modul | Verantwortung | Grobe Funktionen | Herkunft |
|---|---|---|---|
| `chronicle_run` | zweijähriger Academy-Save, Jahresübergang, Revisionen und Abschlusszustände | `create_chronicle_run`, `transition_academy_year`, `reduce_chronicle_event`, `project_run_state` | neu |
| `story_director` | authored Story Graph, erlaubte nächste Szenen, keine freie Wahrheitserfindung | `compile_scene_contract`, `list_reachable_scenes`, `commit_scene_outcome` | neu |
| `calendar` | 336 verdichtete Tage, 48 Specials über zwei Academy-Jahre, Time Windows | `compile_day_instance`, `advance_calendar`, `close_day` | neu |
| `world_place` | versionierter PlaceGraph, permanente/charactergebundene/temporäre PlaceNodes, unabhängige Funktionsfähigkeiten, Reise- und Access Contracts sowie Character-Wohnbindungen | `materialize_place_graph`, `project_reachable_places`, `bind_character_residence`, `revise_primary_residence`, `validate_place_capability`, `resolve_match_visibility_context` | neu |
| `place_activity` | stets figurenbezogene Nicht-VN-Aktivitäten an erreichbaren Orten, Beteiligungsmodus, getrennte Availability, Zeitkosten, begrenzte Outcomes, mindestens eine mögliche Post-Perspektive und optionale Vorbereitung späterer Scenes | `compile_place_activity_contract`, `validate_character_activity_binding`, `project_available_activities`, `commit_activity_outcome`, `materialize_post_opportunities`, `explain_activity_blocker` | neu |
| `social_network` | Profile, Social Graph, Feed, Post Opportunities, subjektive Veröffentlichung, Sichtbarkeit, Reactions, gefolgte Live-/Replay-Streams, Community-Pack-Openings und getrennte BoosterIntents | `compile_post_opportunity`, `materialize_post`, `project_feed`, `schedule_pack_opening_stream`, `record_community_pack_reaction`, `issue_booster_intent` | neu |
| `cast` | 16 aktive Figuren aus 32 Blueprints, Namen und Brand Seeds | `assemble_cast`, `instantiate_character`, `lock_character_canon` | neu |
| `personality` | Base Axes, Developed Axes, Current Type und Behavior Contract | `resolve_personality_input`, `apply_axis_shift`, `derive_current_type` | neu |
| `relationship` | Bond, Trust, Affection, Tension, Route und Milestones | `evaluate_relationship_gate`, `apply_relationship_event` | neu |
| `knowledge` | World Facts, Character Knowledge, Beliefs und Teilnahme | `propagate_scene_knowledge`, `resolve_visible_context` | neu |
| `scene_gate` | Calendar-, Asset-, Play- und Ensemble-Gates | `evaluate_scene_unlock`, `explain_scene_blockers` | neu |
| `visual_asset` | Requirements, Assets, Compatibility und Scene Visual Plans | `resolve_visual_plan`, `evaluate_asset_readiness`, `bind_scene_assets` | neu |
| `asset_processing` | versionierte Masken-, Matting-, Alpha-, Normalisierungs- und QA-Ableitungen aus unveränderten Quellbildern | `create_extraction_attempt`, `normalize_sprite`, `render_asset_qa_previews` | neu |
| `quest` | QuestExperimentContracts, GameMode-/Focus-Bindung, Asset-Build-, Playgate-, Challenger-, Recovery- und Supply-Planung | `compile_quest_experiment_contract`, `plan_character_challenges`, `rotate_character_ready_supply`, `issue_playgate_credit` | erweitert vorhandene Campaign/Supply-Domäne |
| `trial_runtime` | persistente mode-neutrale QuestSession, Eingabereihenfolge und Resume-State für Einzelbild-, Set-, Pairwise-, Bracket-, Curation- und Asset-QA-Runtimes | `start_quest_session`, `project_next_interaction`, `commit_game_action`, `complete_quest_session` | aus Campaign-, Arcade- und UI-Sessionlogik herauslösen |
| `generation` | Workflowfamilien, Modell-/LoRA-/Renderprofile, versionierte BatchDiversityPlans, immutable Recipes, Trials, Submission, Polling und Ingest | vorhandene vNext-Funktionen plus `compile_batch_diversity_plan`, `project_batch_diversity_observation`, `qualify_generation_profile`, `run_profile_trial`, `promote_profile` | erweitern |
| `review_evidence` | unveränderliche Standarddecisions, bildweise Guided Evidence, Vergleiche, Kandidaten- und Dataset-Ereignisse | `record_standard_decision`, `record_guided_image_evidence`, `qualify_contender` | aus vorhandenen Reviews erweitern |
| `generation_knowledge` | rebuildbare mehrdimensionale Ratings, Confidence, Fehlercluster und Credit-Projektionen aus Raw Evidence | `rebuild_generation_projections`, `project_scoped_credit`, `explain_confidence` | aus CampaignEvidenceProjection und Rating-Aggregaten herauslösen |
| `visual_competition` | charactergebundene 1er-, 2er- und 3er-ChampionSlots als Vergleichs-/Titelkontexte, Comparison Contexts, bildübergreifende Qualifikationen, getrennte Pools, Cups, Champion-Lineage, Slot-Mastery und Character Championship; keine aspect-only oder Adult-Content-Slots | `materialize_champion_slot`, `qualify_image_for_slot`, `freeze_slot_roster`, `project_slot_title`, `project_title_overview` | aus opaken Context-Hashes und Tournament-Projektionen fachlich erweitern |
| `visual_portfolio` | persistente Bildkarten, SchoolYearVisualPlan, ClassRoster sowie eindeutiger Besitz und gemeinsame Projektion von Character-, Relationship-, Ensemble- und Scene-Bildern/-Slots | `project_image_card_collection`, `rebuild_school_year_visual_plan`, `project_class_roster`, `bind_portfolio_participants`, `project_shared_visual_context` | Chronicle-, Cast-, Relationship-, Scene- und Championprojektionen zeitlich verbinden |
| `cleanup` | Reject-Referral-Lifecycle, Delete-or-Live-Queue und journalisierte Dateidisposition | `create_pending_referral`, `activate_referral`, `void_referral`, `resolve_delete_or_live` | vorhandenen Trash-/Delete-Service fachlich abgrenzen |
| `lora` | Dataset Lock, Training, Validation und Artefakt-Lineage | `evaluate_lora_readiness`, `start_training`, `validate_artifact` | MVP-Ziel erweitern |
| `llm_gateway` | local-only LM-Studio-Adapter, OpenAI-kompatible Model Discovery, funktionsbezogene Capability-Tests und über `response_format` erzwungener JSON-Schema-Output | `discover_lm_studio_models`, `verify_model_capability`, `invoke_scene_realizer`, `invoke_character_speaker`, `invoke_prompt_author` | neu |
| `retrieval_index` | rebuildbare, strikt getrennte Text-, Bild- und optionale multimodale Indizes samt Referenzset-, Kosinus-, Reranking- und Abstention-Receipts; keine Fachautorität | `rebuild_embedding_index`, `query_compatible_space`, `project_reference_sets`, `record_retrieval_receipt` | neu |
| `description_match` | eigenständige Zwei-Bild-Prüfung versionierter Image-Worker-Beschreibungen mit character-/scopegebundenem Pool, Difficulty-/Pairing-Policy und rebuildbarer Eindeutigkeitsprojektion; keine Karten- oder Prompt-Autorität | `plan_description_pair`, `record_description_match`, `rebuild_description_quality` | neu |
| `context` | kleine rollenreine Context Packs aus direkt geladenen Facts und autorisierten Retrieval-Treffern | `assemble_speaker_context`, `assemble_prompt_context`, `persist_context_pack_manifest` | neu |
| `recovery` | aus Rating-Evidenz eine zulässige Folgeaktion ableiten | `build_recovery_case`, `select_recovery_path` | neu |
| `card_crafting` | reproduzierbare Standardkörper, CardRulesRevisionen, Bildbranding, TraitLineages, Entwicklungsevents, CardBattleExperience, irreversible EvolutionRevisionen, presentation-only Kartenkunst-Kompositionen und rein erklärende LLM-Copy | `materialize_card_result`, `record_card_battle_experience`, `advance_card_development`, `activate_card_evolution_revision`, `create_card_art_draft`, `confirm_card_art_composition`, `render_card_face`, `retire_card_branding`, `materialize_card_copy` | neu |
| `card_collection` | CardIdentities, `blank_standard | public_event | personal_post`-Provenienz, Alters-/Einwilligungs-/Stream-Disclosure-Availability, immutable MemoryOrigins, aktive und historische Rules-/Branding-/Evolution-/Composition-/Face-Asset-Revisionen sowie Rückfall gelöschter Bildbindungen auf Standard | `project_card_collection`, `evaluate_card_source_eligibility`, `evaluate_stream_disclosure`, `reset_card_to_standard`, `project_card_history` | neu |
| `deck` | benannte revisionierte Decks aus exakt 40 einzigartigen CardIdentities und serverseitige Readiness | `create_card_deck`, `revise_card_deck`, `evaluate_deck_readiness` | neu |
| `card_battler` | deterministischer Rules-Reducer, Matchsnapshots, Commands, Events, Zonen, Ketten, PvE-Gegnerprofile, Replay, Resultprojektion und post-match Usage Facts | `start_card_battler_match`, `commit_card_battler_command`, `advance_until_player_input`, `project_card_battler_match`, `materialize_card_usage_facts` | neu |
| `battle_league` | gemeinsame Ranked-/Liga-/Cup-Pyramide, Saisonstände, Qualifikation, Team-/Einzelmeldung und reproduzierbare Reward-Receipts ohne getrennte Kartenquellenformate | `project_battle_ladder`, `record_league_result`, `evaluate_league_qualification`, `materialize_battle_reward` | neu |
| `event_reward` | idempotente Event-Ticket-Vergabe aus qualifizierten Community-Pack-Openings sowie Einlösung ausschließlich für öffentliche Events und Eventbooster | `materialize_event_ticket_reward`, `project_event_ticket_balance`, `redeem_event_ticket` | neu |
| `global_settings` | figurenübergreifende Content-, Generation-, Spiel- und Accessibility-Vorgaben | `get_global_settings`, `update_content_policy`, `snapshot_effective_generation_settings` | vorhandene Content Settings erweitern |
| `orchestration` | deterministische WorkIntents, Arbeitsfreigabe, Leases, Providerkoordination, Monitoring, Reconciliation und Deadlock-Schutz | `materialize_work_intents`, `decide_next_work`, `lease_authorized_work`, `reconcile_provider_jobs`, `project_orchestration_health` | vorhandenen globalen Guardian, Local-AI-Orchestrator und Submission Scheduler unter einem gemeinsamen Vertrag koordinieren |
| `web_ui` | DOM-basierte VN-, Network-, Stream-Pack-Opening-, Kartenkunst-, Quest-, Review-, Chronicle- und Debugprojektion sowie Phaser-basierte Battler-Präsentation hinter einem gemeinsamen API-Controller | keine fachliche Schreibautorität; Phaser und Canvas-Preview bleiben verwerfbarer View-State | vorhandenes Vite-Frontend erweitern |

Die Funktionsnamen sind Roadmap-Arbeitsnamen, keine bereits festgelegte
Python-API.

## Verbindliche M6-Autoritätskette

```text
quest
→ friert GameMode, GenerationFocus/EvaluationFocus und Experiment Contract ein

generation planner
→ kompiliert daraus einen BatchDiversityPlan mit vier kontrolliert verschiedenen
  Slots; Prompt-Machine-Vorschläge werden deterministisch validiert

trial_runtime
→ führt ausschließlich die persistente Spielerinteraktion aus

review_evidence
→ speichert unveränderte Decisions, Reasons und Vergleiche

generation_knowledge
→ berechnet rebuildbare Ratings, Confidence und scoped Credit

visual_competition
→ projiziert aus der Playground-Herkunft charactergebundene 1er-, 2er- und
  3er-Signaturen, Bildqualifikationen, Pools, Titel und Arenen;
  Adult-Content bleibt außerhalb dieses Battlerpfads

visual_portfolio
→ projiziert persistente Keep-/Favorite-Bilder als Bildkartensammlung, hält
  Reject-Evidence ohne Bildkarten-Branding getrennt und ordnet eigene und
  gemeinsame Bildkarten in Class, Beziehung, Ensemble und SchoolYearVisualPlan
  ein, ohne ihre Fachzustände umzuschreiben

recovery
→ wählt nur innerhalb authorisierter Recovery Routes eine Folgehypothese

orchestration
→ prüft WorkIntent, Revisionen, Fähigkeiten, Ressourcen und Policies und
  autorisiert genau den nächsten begrenzten maschinellen Schritt

generation
→ kompiliert und rendert ausschließlich die freigegebenen neuen Recipe-Slots;
  Carried Images bleiben unverändert
```

`trial_runtime` vergibt keinen Progress-Credit. `review_evidence` verändert
keine Prompts. `generation_knowledge` schreibt keine Raw Evidence um.
`recovery` promotet weder Profile noch Champions. `generation` entscheidet
nicht, ob ein Bild fachlich gut ist. `web_ui` projiziert ausschließlich den
serverseitigen Session- und Questzustand.

Jede generierende Vierergruppe besitzt genau eine
`BatchDiversityPlanRevision`. Character Identity, Artstyle, Content Scope und
Vergleichsauftrag bleiben als Locks erhalten. Jeder der vier Slots bindet ein
unverändertes Carried Image oder ein neues immutable Recipe; neu erzeugte Slots
binden eine explizite Seed Policy und sichtbare, focuskompatible Prompt-/Recipe-
Deltas auch gegenüber den übernommenen Bildern. `independent` verlangt
verschiedene Seeds; `paired_control` darf bei verschiedenen Recipes denselben
Seed isoliert teilen; nur `reproduce_calibration` darf Seed und Recipe identisch
wiederholen. Seedvariation allein gilt nicht als sichtbare Diversität.
Undeklarierter Seed-/Recipe-Reuse blockiert die Submission. Eine
nach Ingest projizierte `BatchDiversityObservation` trennt technischen Reuse,
Prompt-/Modellkonvergenz, gültige kontrollierte Diversität und confounded
Multi-Achsen-Änderung. Sie ist Diagnose und nächste Planner-Eingabe, niemals
Player-Evidence oder autonome Retry-Autorität.

`visual_competition` und `orchestration` sind in
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md)
beziehungsweise
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md)
vollständig abgegrenzt. Der Orchestration Guardian ist keine neue
Progressionsautorität: Er darf nur bereits durch Simulation, Rules und
Domain-Planner erlaubte Arbeit freigeben.

Die gemeinsame Kette von Human Review über Image-/Text-Embeddings, Retrieval
und rollenreine LLM-Context-Packs bis zum nächsten Deck- oder Generation Try ist
in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md)
verbindlich beschrieben. `retrieval_index` ist dabei jederzeit rebuildbar und
schreibt keinen Review-, Slot-, Champion-, Canon- oder Readiness-State.

Die übergeordnete Portfolio- und Zeitprojektion steht in
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md).
Sie ist eine read-only Sicht auf Simulation, Competition, Assets und
Relationship State und darf keine dieser Autoritäten duplizieren.

## Gemeinsame Trial-Runtimes statt Einzelimplementierungen

Die technischen Trial-Zustandsautomaten werden auf sechs wiederverwendbare
Sessionfamilien abgebildet. Diese Familien sind Implementierungsbausteine und
weder Spielerbegriffe noch ein freigegebener Game-Mode-Katalog:

| Runtimefamilie | heutige Zuordnungsbeispiele, keine finale Modusfreigabe |
|---|---|
| `single_image_two_pass` | Vierer-Qualifier, Stability, Error Hunt, Repair, Efficiency |
| `set_comparison` | Weakest Link, Identity Lineup, Combo Detective, Continuity |
| `pairwise_comparison` | Arena, Same Character, Spot the Change, Title Match, LoRA Blind Test |
| `bracket` | 16er-Cup, Evolution Tournament |
| `curation` | Coverage Quest, Dataset Draft, Clone Hunt |
| `asset_qa` | Place Trial, Sprite-/Alpha-QA |

Ein `GameModeDefinition` konfiguriert Copy, zulässige Actions, Vergleichsregeln
und Completion Contract. Fachlicher Focus, Credit und Recovery bleiben im
gebundenen QuestExperimentContract und werden nicht aus der Runtimefamilie
abgeleitet.

Die genaue spielerseitige Modusliste und ihr Ablauf sind vor dem Frontend-Schnitt
nach AIAM offen. Legacy-Routen, technische Oberflächen, Resultprojektionen und
freie Questbindung dürfen daraus nicht als zusätzliche Modi abgeleitet werden.

## Schreibautorität

Nur deterministische Servermodule dürfen folgende Zustände schreiben:

- Calendar und Scene Progress,
- Character Development und Personality Axes,
- Relationship- und Knowledge-State,
- Gate-Erfüllung und Playgate Credits,
- Asset Readiness, Champion- und LoRA-Status,
- CardIdentity-/Branding-/Evolutionentwicklung, BattleExperience,
  Deckrevisionen, Liga-/Saisonstände und Card-Battler-Matches,
- Run-Abschluss und NG+-Carry-over.

Fachlich wirksame globale Einstellungen wie Content Policy und Generation
Defaults werden ebenfalls serverseitig versioniert. Das Frontend darf lokale
Darstellungsvorlieben cachen, aber keine sicherheits- oder
generierungsrelevante Einstellung ausschließlich im Browser halten.

LLMs dürfen Text oder Promptvorschläge innerhalb eines vorgegebenen Contracts
erzeugen. Retrieval darf Evidenzkandidaten liefern. Das Frontend darf
Entscheidungen senden. Keines dieser Systeme darf selbst einen Stateübergang
freigeben.

## Save- und Eventgrenze

Gespeichert wird serialisierbarer Simulationszustand, niemals Browser- oder
Rendererzustand. Jede relevante Mutation erzeugt ein versioniertes Domain
Event und eine reproduzierbare Projektion. Große generierte Dateien werden über
stabile Asset-IDs und Manifeste referenziert, nicht über UI-Dateinamen.

Für den Card Battler schreibt jede akzeptierte Aktion Command Receipt,
geordneten Eventstrom, neuen Match Head und gegebenenfalls Outbox Events in
einer Transaktion. Rules-, Deck-, Karten- und Gegnerprofilrevision sowie RNG
werden zu Matchbeginn eingefroren. Reload und Replay rekonstruieren denselben
Zustand, ohne Phaser, Browsercache, LLM oder neuen Zufall aufzurufen.

## Adaptergrenzen

### Globale Modellherkunft

Für sämtliche KI-Funktionen gilt eine gemeinsame Ausschlusspolicy: Die
Anwendung lädt, testet, empfiehlt oder verwendet keine von Meta/Facebook
veröffentlichten Modellgewichte und keine davon abgeleiteten Weight-Lineages.
Das umfasst insbesondere LLMs, Text- und Image-Embedding-Modelle, Vision-,
Detection-, Segmentierungs-, Matting-, Diffusions- und Trainingsbasen. Damit
sind unter anderem Llama- und SAM-Familien ausgeschlossen. Jede produktive
Modellbindung benötigt Publisher, Base-Model-Lineage, Lizenz, Revision und Hash;
unbekannte oder nicht vollständig auflösbare Lineage bleibt `unavailable`.
Reine Laufzeit-, Index- oder Protokollbibliotheken ohne gelernte Gewichte werden
separat bewertet und sind nicht allein wegen ihres Herausgebers ein KI-Modell.

- `GenerationProvider`: ComfyUI heute, weitere Provider später möglich.
- `ForegroundExtractionProvider`: austauschbare Segmentierungs- und
  Matting-Pipeline; erzeugt versionierte Masken und Alpha-Ableitungen.
- `VisionAnalysisProvider`: austauschbare Recognition-, Detection-,
  schemaförmige VLM-Beschreibungs- und Embedding-Befunde; besitzt keine
  Evidence- oder Readiness-Schreibautorität. Initialer VLM-Kandidat im
  Docker-Worker ist Huihui Qwen3-VL 8B Instruct Abliterated in gepinnter
  4-Bit-Revision.
- `ComfyUiTrainingProvider`: wählt einen im ComfyUI-Kontext gepflegten,
  versionierten Trainingsworkflow, befüllt ausschließlich dessen freigegebene
  Parameter und nutzt die ComfyUI-API für Start, Queue, Progress, History,
  Abbruch und Ergebnisabfrage. Workflowdateien, Custom Nodes, Trainingslogik und
  LoRA-Ausgabeordner liegen bei ComfyUI und werden in der Anwendung nicht
  nachgebaut. Die Anwendung besitzt nur den fachlichen `LoRATrainingRun`, den
  Dataset Lock sowie Referenz, Hash und Lineage des ComfyUI-Ergebnisses. Ein
  manueller Artefaktimport gehört nicht zum primären MVP-Pfad und bleibt
  höchstens eine spätere Advanced-/Recovery-Erweiterung.
- `LmStudioProvider`: einziger generativer Sprachprovider des MVP. Verwendet
  OpenAI-kompatible Calls für Discovery und Inferenz. Strukturierte Rollen
  übergeben ein versioniertes JSON Schema als echtes `response_format` mit
  `strict = true` und verlassen sich nicht auf Promptanweisungen. Die native
  LM-Studio-v1-API darf ausschließlich Discovery-Metadaten sowie Load/Unload
  ergänzen. Jede logische Funktion besitzt eine eigene Modellbindung und
  Capability-Prüfung.
- `TextEmbeddingProvider`: primär LM Studios OpenAI-kompatibler Embeddings-
  Endpoint mit separat gewähltem und verifiziertem Embedding-Modell. Initialer
  Default ist Qwen3-Embedding-0.6B, CPU-first, mit festen 1024 Dimensionen und
  getrennten versionierten Räumen.
- `ImageEmbeddingProvider`: getrennte lokale Capability in einem asynchronen
  Docker-Worker, nicht in LM Studio. Der Provider besitzt mehrere
  modellgebundene Räume:
  allgemeine Bild-/Style-Ähnlichkeit, Anime-Character-Identity sowie
  strukturierte Anime-/Content-Tags. Die initialen Referenzkandidaten sind
  [SigLIP2 So400m/14 384](https://huggingface.co/google/siglip2-so400m-patch14-384),
  [CCIP `ccip-caformer_b36-24`](https://huggingface.co/deepghs/ccip_onnx) und ergänzend der
  [WD EVA02 Large Tagger v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3).
  Aktiviert wird eine Bindung erst nach Fixture-, Dimensions-, Preprocessing-,
  Revisions- und Lizenzprüfung. Ein VLM wird nicht allein aufgrund seiner
  Bildannahme als Image-Embedding-Modell zugelassen.
- `ContentRepository`: versionierte authored Daten; keine Laufzeitautorität der
  alten Playground-SQLite.

Jeder Adapter erhält einen deterministischen Fake für Contract- und
End-to-End-Tests.

Der `LocalAiOrchestrator` projiziert nicht nur, ob LM Studio, ComfyUI und der
Image-Embedding-Worker online sind, sondern ob die konkrete Spielfunktion
ausführbar ist. Er verbindet entdeckte/geladene LM-Studio-Modelle, deren
Settings-Zuordnung, Capability-Reports, ComfyUI-Workflow-Readiness, persistierte
VLM-/Image-Embedding-Jobs und den gemeinsamen Submission-/Backpressure-Zustand. Der
Worker erhält nur bereits durch die Anwendung autorisierte Bilder und
verarbeitet `standard`, `sexy`, `lewd`, `nude` und `explicit` ohne eigene
providerseitige Inhaltszensur oder Scope-Ablehnung. Die Safety- und
Content-Autorität bleibt vor der Submission in der Anwendung; der Worker ist
kein Bypass. Nach Output-Ingest darf bereits eine rein diagnostische
`MachineImageObservation` samt getrenntem Textvektor erzeugt werden, damit der
eigenständige Beschreibungstest später auf eine revisionsgebundene Beobachtung
zugreifen kann. Sie erzeugt keinen Zusatzschritt im normalen Bildreview. Bis im
angefragten Scope ein transportgültiges,
kontextkompatibles Favorite, eine scopekompatible `APPROVED ChampionRevision`
oder ausdrücklich vorhandenes kompatibles Legacy-Referenzmaterial existiert,
bleibt jedoch die Image-Embedding-Capability `waiting_for_human_evidence`: Es
werden keine Bildvektoren berechnet und kein persönlicher Bildindex befüllt.
Favorite und Champion sind für diese Referenzfreigabe gleichwertig; ein Keep ist
positive Evidence, aber allein kein Bootstrap-Schlüssel. Danach dürfen
Keeps/Favorites positive
Beobachtungen und begründete
Rejects ausschließlich ihre expliziten negativen beziehungsweise
achsenspezifischen Befunde speisen; Skip erzeugt nichts. Simulation und Save
referenzieren Ergebnisse und Provenienz, niemals einen Prozess- oder
GPU-Zustand.

Training, Bildgeneration, lokales LLM, VLM und Image Embeddings teilen sich
standardmäßig dieselbe lokale GPU. Deshalb entscheidet der
`OrchestrationGuardian`, welcher begrenzte Auftrag autorisiert wird; der
Submission Scheduler reiht nur bereits autorisierte Arbeit ein. Im initialen
RTX-3060-Profil sind ComfyUI, LM-Studio-LLM, Docker-VLM und
Docker-Image-Embedding-Batch gegenseitig exklusive schwere GPU-Klassen;
Qwen3-Embedding-0.6B läuft CPU-first. ComfyUI behält seine eigene
Workflowausführung, LM Studio seine Modelllaufzeit und der Docker-Worker seine
Inferenz. Für Image Embeddings gilt:
Favorite, scopekompatible `APPROVED ChampionRevision` oder ausdrücklich
kompatibles Legacy-Referenzmaterial →
`ImageAnalysisBootstrapRevision` → Review-/Reason-gebundene Referenzrollen →
deterministische Crops → persistierter Job → Worker-Inferenz → persistiertes
Resultat mit Source Hash, Modellrevision, Raum, Preprocessingrevision und
Dimension. Erst nach dieser Bootstrap-Revision dürfen abgeschlossene spätere
Reviews reguläre Bildjobs erzeugen. `APPROVED ChampionRevisionen` können
Referenzsets und Rebuilds speisen; Legacy-Material bleibt auf ausdrücklich
Legacy-fähige Kontexte begrenzt. Der Worker schreibt nie direkt in die
Spieldatenbank. Weder Anwendung noch Frontend dürfen parallele Kapazität
voraussetzen oder Storyzeit aus realer Laufzeit ableiten.

## Debug- und Nachvollziehbarkeitsoberfläche

Jeder Vertical Slice ergänzt eine einschaltbare Debugprojektion mit:

- Run-, Day-, Scene- und Character-Revision,
- angewandter Rules- und Content-Version,
- Gate Checks und Blockern,
- geplanten Visual Needs und gewählten Assets,
- Quest- und Credit-Provenienz,
- LLM-Contract, validiertem Ergebnis und Fallback,
- sowie Event-IDs vor und nach einer Entscheidung.

Die Debugprojektion ist read-only und darf nicht zum zweiten Admin-Backend
werden.
