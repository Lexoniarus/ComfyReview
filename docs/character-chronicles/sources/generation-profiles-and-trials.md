# Generation Profiles und Character Trials

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `HISTORICAL_GENERATION_TECH_PROPOSAL`  
**Worum es geht:** Vierer-Trials, Profile, Versionierung und damalige Schema-47-/Generationsverträge.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../../ACTIVE_WORK.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 10. September 2026

## Rollierender Vertrag ab Schema 47

Der am 3. September 2026 freigegebene [rollierende M6-Lernloop](rolling-m6-learning-loop.md)
präzisiert die früheren Ein-Achsen-/Recovery-Aussagen dieses Dokuments:
Neue Human Evidence geht in die gemeinsame Kandidatenplanung ein, nicht in einen
automatischen Reparatur-Child. Nur bereits materialisierte, autorisierte
Providerarbeit darf Retrieval/Prompt Machine beim technischen Resume überspringen.

Seit `question-driven-m6-v2` bestimmt die Frage den technischen Vergleichsvertrag.
Seed-Stabilität verwendet dasselbe vollständige Recipe mit vier unabhängigen
Seeds. Sampler, Scheduler, Steps, CFG und Denoise verwenden denselben Prompt und
einen gepaarten Seed; nur die ausdrücklich benannte Renderachse variiert.
Prompt-Gewichtung hält Atome und Renderwerte fest und erzeugt die Gewichte
deterministisch innerhalb `0.7–1.8`. Prompt Machine und Judge laufen nur für
`prompt_composition` und `semantic_exploration`. Daher ist eine wiederholte
Tennis-/Schuldach-Komposition in einem Seed- oder Techniktrial kein Fehler,
wohl aber eine unzulässige Dublette in einem Prompt-Composition-Trial.
Unbegonnene Planung wird zusammengeführt; ab dem ersten KI-WorkIntent bleibt das
vollständige Eingangsmanifest unverändert. Andere Karten bleiben erhalten.
Schema 47 und sein separater Abnahmenachweis sind nicht durch ältere
`AUTOMATED_VERIFIED`-Statuszeilen bereits praktisch abgenommen.

## Zweck und Abgrenzung

Dieser Vertrag beschreibt, wie das Spiel Checkpoints, LoRAs, strukturell
unterschiedliche ComfyUI-Workflows und Renderparameter kontrolliert erprobt,
bewertet und promotet. Der normale Spieler verändert diese Technik nicht als
Standard-Setting. Er spielt bildzentrierte Trials und bewertet Ergebnisse; das
System speichert die vollständige Provenienz und entscheidet deterministisch,
welches bereits qualifizierte Profil verwendet werden darf.

Die technische Tiefe dieses Dokuments ist Backendvertrag und keine Vorgabe für
die primäre Spieler-Copy. Der Trial projiziert daraus Figur, sichtbaren
Kartenauftrag, Bewertungsfrage, relevante Konstanten und erkennbare Unterschiede.
GenerationFocus, Expected Composition, Locked/Varied Axes, Recipe, Modell,
Workflow, Seed, Roh-Evidence, Confidence und Unsicherheit werden trotzdem
vollständig und revisioniert gespeichert. Die verbindliche Trennung steht in
[`player-facing-terminology-and-voice.md`](player-facing-terminology-and-voice.md).

Die persönlichen Prompt-, Combo- und Workflow-Erfahrungen folgen zusätzlich dem
allgemeinen Evidenz- und Datenbankvertrag in
[Foundation-Vertrag zum adaptiven Generationslernen](../foundation/adaptive-generation-learning.md).

## Heutiger Ausgangspunkt

Der gegenwärtige Default im Repository verwendet
`NetaYumev35_pretrained_all_in_one.safetensors`. Die fünf gespeicherten
Character-Workflows sind derzeit identisch und enthalten unter anderem:

- `emo_hairstyle.safetensors` mit Model-Stärke `0.61` und CLIP-Stärke `0.58`,
- `41` Steps,
- CFG `5.6`,
- Sampler `sa_solver_pece`,
- Scheduler `simple`,
- Denoise `1`.

Der Code kann Checkpoint und KSampler-Werte patchen und persistiert bereits
unveränderliche Workflow-, Recipe-, Modell- und Render-Snapshots. Er besitzt
noch keine Modellfamilien-Kompatibilitätsprüfung, keinen fachlichen
`LoRAStack`, keine per-Character-Confidence und keine automatische
Experiment-/Promotion-Logik. Ein Checkpoint-Patch ist daher noch kein sicherer
Workflowfamilien-Wechsel.

Die heutige Generator-/Config-Oberfläche kann Komponenten, Batch- und Seedmodus,
Max Tries, Checkpoint, Sampler, Scheduler, Steps, CFG, Denoise und einzelne
Prompt-Drafts verändern. Der zugrunde liegende ComfyUI-Graph enthält zusätzlich
LoRA-Loader einschließlich Model-/CLIP-Stärken, Latent-Auflösung, VAE, Upscaler
und Postprocessing. Diese nicht vollständig in der heutigen UI sichtbaren
Faktoren bleiben dennoch Teil der Ergebnisursache und müssen im Zielvertrag
versioniert, vergleichbar und in Advanced-Diagnosen sichtbar sein.

Die lokal installierte Modell- oder LoRA-Menge ist nur ein auffindbares
Inventar. Ein Artefakt wird erst nach Kompatibilitäts-, Lade-, Ressourcen- und
Qualifikationsprüfung zu einem zulässigen Trial-Kandidaten.

## Vier Ebenen eines Generationsprofils

```text
WorkflowFamily
→ struktureller ComfyUI-Graph und Modellarchitektur

ModelProfile
→ Checkpoint, VAE und modellbezogener Prompt Compiler

LoRAStack
→ versionierte Character-, Style-, Utility- und Concept-LoRAs mit Stärken

RenderProfile
→ Sampler, Scheduler, Steps, CFG, Denoise und Auflösung
```

Ein `GenerationRecipe` friert alle vier Ebenen für einen Attempt unveränderlich
ein. Jedes erzeugte Bild referenziert mindestens:

- Workflow-Familie, Workflow-Version und Graph-Signatur,
- Checkpoint, Modellfamilie und VAE,
- vollständigen LoRA-Stack mit Artefaktversion, Rolle, Model- und CLIP-Stärke,
- Prompt-Compiler-, Prompt-Core- und konkrete Prompt-Version,
- Sampler, Scheduler, Steps, CFG, Denoise, Auflösung und Seed,
- Character-, Assetrollen-, Save- und Questkontext,
- sowie Parent-Try, Hypothese und kontrolliert veränderte Achsen.

## Vierer-Batch-Diversitätsvertrag

Ein Viererbatch ist weder viermal dasselbe Recipe mit nur zufälligem Dateinamen
noch ein unkontrollierter Mix aus vier verschiedenen Bildideen. Vor jeder
generierenden Vierergruppe materialisiert der Generation Planner einen
versionierten `BatchDiversityPlan` aus `QuestExperimentContract`, Generation
Focus, Expected Composition und Locked/Varied Axes. Die Prompt Machine darf
schemaförmige Slotvorschläge liefern; ausschließlich deterministischer Code darf
sie validieren. Jeder der vier Anzeigeslots bindet entweder ein unverändertes
übernommenes Bild oder genau ein neu abzuleitendes immutable
`GenerationRecipe`; nur eine vollständig neue Kohorte besitzt vier neue Recipes.

```text
BatchDiversityPlan
├─ batch_diversity_plan_id und revision
├─ quest_experiment_contract_id
├─ generation_focus_id und content_scope
├─ locked_axes[]
├─ varied_axes[]
├─ intended_comparison_axis
├─ seed_policy: independent | paired_control | reproduce_calibration
├─ slots[4]
│  ├─ stable slot_id
│  ├─ source_kind: carried_image | new_recipe
│  ├─ carried_image_id oder null
│  ├─ seed oder null
│  ├─ seed_group_id oder null
│  ├─ planned_semantic_delta
│  ├─ expected_visible_difference
│  └─ generation_recipe_id und recipe_hash oder null
├─ calibration_exception oder null
└─ status: proposed | validated | blocked | materialized | observed
```

Für normale Batches bleiben Character Identity, Artstyle, Content Scope und der
konkrete Vergleichsauftrag gebunden. Mindestens eine für den Focus zulässige,
sichtbare Achse wird pro neu erzeugtem Slot kontrolliert variiert, beispielsweise
Pose, Ausdruck, Kamera, Crop, Komposition oder Hintergrund. Die vier Slots
besitzen entweder ein unverändertes Carried Image oder ein nachvollziehbares
neues Prompt-/Recipe-Delta. Bei `independent` besitzen alle im selben Plan neu
erzeugten Slots unterschiedliche Seeds und Recipe Hashes. Ein deklarierter
`paired_control` darf denselben Seed bewusst für Control und Challenger binden,
wenn Recipe Hash und isoliertes Delta verschieden sind. Nur
`reproduce_calibration` darf Seed und Recipe identisch wiederholen. Die
Kalibrierungsausnahme benennt dafür Quellslot, Wiederholungsslot und Begründung;
jeder weitere gleiche Seed oder Recipe Hash bleibt ein Integritätsfehler. Bei
null bis drei Carried Images reduziert der Planner die Zahl der neuen
Proposal-Slots entsprechend, sodass der materialisierte Batch immer exakt vier
Anzeigeslots und niemals vier neue Slots zusätzlich zu den Carried Images
besitzt. Die
erwarteten sichtbaren Deltas werden auch gegen übernommene Bilder geprüft. Ein
anderer Seed allein ist noch kein Diversitätsnachweis, wenn die sichtbaren
Ergebnisse dennoch kollabieren. Gleichzeitig dürfen nicht beliebig viele Achsen
wechseln, weil der Batch sonst keinen kausalen Vergleich mehr erlaubt.

Undeklarierter Seed-Reuse, identischer Recipe Hash außerhalb von
`reproduce_calibration` oder fehlendes Slotdelta blockiert die Submission als
Integritätsfehler. Nach Output-Ingest erzeugen die
vier Einzelbeobachtungen zusätzlich eine rebuildbare
`BatchDiversityObservation`. Sie trennt mindestens:

- `undeclared_recipe_or_seed_reuse`: technischer Planungs-, Persistenz- oder
  Recoveryfehler,
- `model_or_prompt_convergence`: unterschiedliche gültige Recipes, aber visuell
  zu ähnliche Ergebnisse,
- `controlled_diversity_met`: Locks stabil und geplante sichtbare Deltas
  vorhanden,
- `confounded_multi_axis_change`: Vergleich durch zu viele gleichzeitige
  Änderungen nicht kausal auswertbar,
- `uncertain`: maschinell nicht belastbar entscheidbar.

VLM-Beschreibungen dürfen bereits vor dem Human Review einen verständlichen
`batch_collapse_suspected`-Hinweis mit betroffenen Achsen vorschlagen. Nach
scopegebundenem Human-first-Bootstrap dürfen SigLIP2-/CCIP-Befunde diese
Diagnose quantifizieren. Weder Hinweis noch Score versteckt, ersetzt, sortiert
oder bewertet ein transportgültiges Bild. Erst die Spielerbewertung und ihre
Reasons werden Evidence.

Der nächste kontrollierte Try konsumiert die persistierte Observation: Bei
Recipe-/Seed-Reuse folgt technische Recovery; bei echter Prompt-/
Modellkonvergenz plant er stärkere, weiterhin focusgebundene Slotdeltas; bei
Multi-Axis-Confounding reduziert er die Variation. Ein Providerresultat startet
diesen Folgeauftrag niemals selbst. Planner, Guardian und Submission Scheduler
führen ihn als neue, separat autorisierte Revision aus.

Bewertungen stammen autoritativ aus den strukturierten vNext-Reviewereignissen.
Alte skalare Ratings, daraus aggregierte Prompt Ratings und Materialized Combos
dürfen ausschließlich in einem später bewusst gestarteten Import als
`LegacyPrior` aufgenommen werden. Der erste Vier-Figuren-Learning-Proof und
normale neue Runs verwenden `evidence_policy=fresh_only`; dort sind sämtliche
Legacy-Priors deaktiviert. Neue Token-, Component-, Combo-, Workflow- und
Renderprofile werden ausschließlich als rebuildbare Projektionen aus Review-,
Vergleichs-, Batch-, Delete-, Calibration-, Recipe- und Laufzeitevidenz
berechnet. Eine unkontrollierte Gesamtbildbewertung oder ein vorhandenes Bild
ohne vollständige Recipe-Provenienz vergibt keinen kausalen Credit an jeden
enthaltenen Token oder technischen Parameter.

Der initiale Lernpfad verwendet diese Recipe-Provenienz für kontrollierte Trys,
prüft die neu gerenderten Bilder aber nicht vor dem Spielerreview per Image
Embedding. Erst ein kompatibles Favorite, eine scopekompatible `APPROVED
ChampionRevision` oder ausdrücklich kompatibles Legacy-Referenzmaterial eröffnet
die scopegebundene post-review Image-Embedding-Beobachtung; ein Keep allein
nicht. Der Vier-Schritt-Vertrag und die spätere
Kosinusdiagnostik stehen in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md).

Die vorhandenen **technischen Werte** sind davon nicht ausgeschlossen. Belegte
Promptgewichte, Komponenten-/Combo-Zusammensetzungen und vollständige Recipe-,
Sampler-, Scheduler-, Steps-, CFG-, Checkpoint-, Workflow- und LoRA-Werte bilden
eine versionierte `DevelopmentGenerationBaseline`. Sie initialisiert den ersten
Control-Arm, ist aber keine Spieler-Evidence. Neue Reviews erzeugen daraus
aufeinanderfolgende Knowledge-Revisionen; mindestens zwei vollständige
Änderungs-/Wiederbewertungszyklen werden vor dem VN-Gate gegen die Baseline und
ihre Parent-Revision verglichen.

## Workflowfamilien und Kompatibilität

Ein Wechsel von Steps oder CFG ist ein Render-Try innerhalb eines kompatiblen
Profils. Ein Wechsel zwischen Modellarchitekturen ist dagegen ein vollständiger
`WorkflowFamilyTry`. Er kann Loader, Text Encoder, Latentformat, VAE,
Promptgrammatik, Auflösung, Control-Schritte und kompatible LoRAs verändern.

Das Spiel patcht deshalb keine beliebigen Checkpoints in beliebige Graphen. Jede
Workflowfamilie deklariert:

```text
family_id
model_architecture
workflow_template_version
compatible_checkpoint_ids[]
compatible_lora_families[]
prompt_compiler_id
allowed_sampler_scheduler_pairs[]
resolution_profiles[]
required_nodes[]
resource_profile
qualification_status
```

Nur `qualified` Workflowfamilien dürfen in spielerrelevanten Trials erscheinen.
Fehlende Nodes, inkompatible LoRAs oder nicht ladbare Modelle führen zu einem
technischen Ausschluss und nicht zu negativer Geschmacks-Evidenz.

## LoRA-Rollen und Ablation

Ein LoRA wird nicht wegen seines Dateinamens als hilfreich oder schädlich
eingestuft. Sein Vertrag enthält mindestens:

```text
lora_artifact_id
base_model_family
role: character | style | utility | concept
trigger_contract
allowed_asset_roles[]
model_strength_range
clip_strength_range
conflicts[]
qualification_status
```

Unklare beziehungsweise vorhandene Default-LoRAs werden durch kontrollierte
Ablation geprüft:

```text
A: bewährter Stack einschließlich LoRA
B: identischer Stack ohne LoRA oder mit genau einer anderen Stärke
→ identische semantische Aufgabe
→ gepaarte Seeds innerhalb derselben Modellfamilie
→ technische, Canon-, Style- und Taste-Evidenz getrennt auswerten
```

Ohne reproduzierbaren Vorteil wird das LoRA nicht in ein breiteres Profil
promotet. Wirkt es nur für einzelne Assetrollen oder Figuren, bleibt sein Scope
entsprechend eng. Character-LoRAs gehören zur jeweiligen Figur; Style-LoRAs
benötigen save-weite Evidenz; Utility-LoRAs dürfen auf authorisierte Aufgaben
wie Pose, View oder Sprite-Produktion begrenzt werden.

## Scope und Confidence

Profile werden hierarchisch vererbt:

```text
qualified WorkflowFamily
→ SaveGenerationProfile und AnimeStyleProfile
→ CharacterGenerationProfile
→ AssetRoleProfile für Portrait, Sprite, Place oder CG
→ lokaler Try beziehungsweise Recovery-Attempt
```

Das `AnimeStyleProfile` ist die save-weite Stilprojektion. Es verweist mit
`active_style_core_revision_id` auf genau eine aktive
`AnimeStyleCoreRevision`, hält die dafür qualifizierte persönliche
Style-Evidence und darf schmalere Character-/Assetrollen-Overrides begrenzen.
Die Core Revision ist damit der versionierte aktive Stilinhalt; das Profile ist
sein Scope-, Confidence- und Vererbungsvertrag. Beide Begriffe sind nicht
austauschbar.

Ein global erfolgreiches Profil liefert einer Figur nur einen Prior. Es markiert
diese Figur nicht automatisch als validiert. Pro Character und Assetrolle werden
mindestens Evidenzzahl, unabhängige Seeds, Usable Rate, Identity-, Style- und
Quality-Werte, Unsicherheit, letzte Profilrevision und Status gespeichert:

```text
inherited → provisional → character_proven → challenged
```

Ein Character-Override entsteht nur bei wiederholter Evidenz gegen das geerbte
Profil. Save-weite Promotion benötigt vergleichbare Evidenz über mehrere
Figuren und relevante Assetrollen. Eine neue globale Profilrevision setzt
bestehende Character-Confidence nicht still auf `proven`; betroffene Figuren
werden gezielt revalidiert.

## Challenge-Arten und Änderungsautorität

Nicht jeder Champion-Sieg bedeutet dieselbe fachliche Änderung. Jeder
`ChallengeContract` deklariert deshalb vor dem ersten Render genau einen Typ und
seinen Zielscope:

| Typ | Erlaubte Änderung | Ergebnis eines Siegs |
|---|---|---|
| `stability_challenge` | Seed, Promptrealisierung oder technische Recipe-Achse bei gleicher semantischer Figur | Recipe-, Prompt- oder Profilwissen; keine Canon Revision |
| `recovery_challenge` | kontrollierte Reparatur eines benannten Fehlers bei gleichem Requirement | neue verwendbare Asset-/Recipe-Version; keine semantische Canon-Änderung |
| `binding_challenge` | konkrete Umsetzung eines gemeinsamen Outfit-/Scene-Blueprints für eine Figur | neue Character-Binding-Revision oder enger Binding-Credit |
| `evolution_challenge` | genau eine vorab autorisierte `PromptAspectGroup` mit allen zugehörigen positiven und negativen Promptatomen | experimentelle Child-ComponentVersion; nur ein getrennter qualifizierter Character-Canon-Pfad kann sie später als Canon-Kandidat verwenden |

```text
ChallengeTargetContract
├─ challenge_type
├─ target_character_id und asset_role
├─ fixed_semantic_signature
├─ target_prompt_aspect_group_id
├─ baseline_prompt_atoms[] und challenger_prompt_atoms[]
├─ allowed_weight_bands und weight_diffs[]
├─ accepted_prompt_aspect_proposal_revision_id
├─ prompt_aspect_judgement_revision_id
├─ variable_axes[]
├─ optional_parent_canon_revision_id
├─ optional_appearance_change_proposal_id
├─ optional_change_resistance_snapshot
└─ allowed_promotion_scope
```

Bei Stability, Recovery und Binding bleibt der nicht ausdrücklich veränderte
Character Canon unverändert. Ein hübscher unbeabsichtigter Drift wird als
`ObservedVisualDelta` gespeichert, aber nicht still zum neuen Canon.

Ab Schema 55 ist die Änderungsautorisierung nicht auf Character beschränkt.
Ein `TypedMutationCorridor` kann für `character`, `outfit`, `scene`, `pose`,
`expression`, `lighting` oder `modifier` genau eine Operation `add`, `remove`,
`replace`, `reweight` oder `replace_group` autorisieren. Er bindet Parent,
konkreten Arm und Recipe, Character-/Campaign-/Scope-Kontext, auslösende
Evidence, Preserve-Gruppen und erwarteten Diff. Außerhalb des Corridors bleibt
die Component gesperrt. Style verwendet stattdessen einen eigenen
`style_core`-Corridor und erzeugt eine Child-`AnimeStyleCoreRevision`.

Ein isolierter Atomversuch verändert pro Challenger genau ein Atom. Ein
isolierter Weight-Versuch verändert ausschließlich das Gewicht eines bereits
gebundenen Atoms. Eine Evolution Challenge darf genau eine vollständige Aspect
Group ersetzen. Ein neuer Begriff und dessen Gewicht werden nicht im selben
isolierten Trial gleichzeitig bewertet; ein späterer Weight-Trial kann die
Stärke eines zuvor bewerteten Add-/Replace-Atoms untersuchen.

Vor dem ersten Evolution Render müssen Prompt Aspect Proposer, deterministischer
Hard Validator und unabhängiger Prompt Aspect Judge dieselbe konkrete Proposal
Revision akzeptiert haben. Judge-Befunde mit `revise` gehen als strukturierte
Eingabe an eine neue Proposer-Revision zurück. Weder ein Zwischenstand noch ein
Judge-Abstain darf Kandidaten erzeugen oder in das Player Review gelangen.

Diese Freigabe validiert ausschließlich den kontrollierten **Versuch**, nicht
das generierte **Ergebnis**. Nach dem Render passieren Outputs nur ein enges
`RenderTransportGate` für Dekodierbarkeit, erwartete Datei-/Canvas-Grundform,
exakte technische Duplikate und zwingende Safety. Jeder danach darstellbare
Output wird dem Spieler gezeigt. Prompt Aspect Judge, Vision, Embeddings oder
automatische Identity-/Quality-Scores dürfen ihn wegen sichtbarer Abweichungen
nicht vorselektieren.

Das Player Review besitzt zwei aufeinanderfolgende Durchgänge innerhalb
derselben QuestSession. Im ersten Durchgang erfasst es pro Bild ausschließlich
`reject | keep | favorite | skip`. Nach allen vier Entscheidungen zeigt die
zweite `GuidedEvidenceRound` jedes nicht übersprungene Bild erneut einzeln groß
und erfasst dafür eine klickbare Mehrfachauswahl versionierter positiver und
negativer Reason Codes, genau einen vom Spieler innerhalb derselben Chipauswahl
bestätigten Primary Reason und betroffene Aspect Groups. Der zuerst gewählte
passende Chip ist lediglich der umstellbare UI-Default. Der normale Flow
enthält keinen Freitext. Fehler wie
fehlende Zieländerung, unrelated drift, Identity-, Artstyle-, Anatomy-, Outfit-,
Scene- oder Backgroundabweichung sind Spielinhalt und werden erst durch diese
Bewertung zu autoritativer Evidence. Maschinelle Befunde dürfen anschließend
Diagnose und Asset-Readiness ergänzen, aber weder Spielerauswahl noch
Mehrfachgründe ersetzen.

Reject, Keep und Favorite benötigen jeweils mindestens einen Reason Code. Der
Primary Reason muss Mitglied der Auswahl und zur Action passend negativ
beziehungsweise positiv sein. Weitere kompatible Secondary Reasons dürfen auch
Teilbefunde der Gegenrichtung ausdrücken. `skip` speichert keine Gründe und
erzeugt keine Ratingevidenz. Favorite zählt stärker positiv als Keep; Primary
zählt innerhalb derselben Entscheidung stärker als jeder einzelne Secondary
Reason. Die exakten Faktoren bleiben versionierte Balancewerte und ändern die
unveränderten Primärereignisse nicht.

Ein Reject legt im ersten Pass genau eine deduplizierte Cleanup-Referral
`awaiting_guided_evidence` an. Sie ist noch nicht als Delete-or-Live-Game
spielbar. Erst die vollständige Begründung dieses Bildes setzt sie auf `ready`;
Undo davor setzt sie append-only auf `void`. Die spätere binäre Entscheidung
fragt die bereits gespeicherten Gründe nicht erneut ab.

Jeder Reason gehört exakt zum aktuell fokussierten Bild. Es gibt keine
Sammelauswahl für den Viererbatch. Wiederkehrende Batcheffekte werden erst aus
den vier Einzelereignissen projiziert. Die zulässigen Chips stammen
deterministisch aus Quest Contract, VisualSpec, Assetrolle, Recipe,
Variationsachse und Inhaltseinstellung. Ein Vision-Modell darf vorhandene Codes
nur priorisieren; es darf sie weder erfinden noch auswählen oder persistieren.
Der vollständige UI-, Schema- und Modusvertrag steht in
[`11-game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md).

Reason-Familie und Bewertungsursache sind getrennt. Jeder Code gehört genau
einer der Ebenen `generation_intent`, `visual_defect`, `character_canon`,
`asset_usability` oder `aesthetic_preference`. Ein falscher Scene-Inhalt, ein
kaputt gerenderter richtiger Background und ein technisch korrekter, aber nicht
bevorzugter Background sind deshalb drei verschiedene Events mit verschiedenen
Recovery-Autoritäten. Mehrere Ebenen dürfen am selben Bild gleichzeitig wirken;
keine negative Ebene löscht positive Evidence einer anderen.

Die rebuildbare Wissensprojektion führt pro Bild, Context Hash, Evaluation Layer
und Bewertungsachse getrennte `positive_mass`, `negative_mass`,
`observation_count`, `independent_source_count`, `evidence_ratio`, `uncertainty`
und `confidence`. Das Verhältnis beschreibt die bisherige Richtung; Confidence
beschreibt unabhängig davon, wie belastbar sie ist. Ein neues Bild mit einer
positiven Beobachtung kann daher ein höheres Verhältnis, aber geringere
Confidence als ein älteres Bild mit sechs positiven und zwei negativen
Beobachtungen besitzen. Niedrige Confidence autorisiert weitere kontrollierte
Vergleiche und ist weder automatischer Verlust noch automatische Promotion.

Favorite/Keep und ihre Primary-/Secondary-Reasons erzeugen die Ausgangsmassen.
A/B-Matches ergänzen Gewinner- und Verlierermasse nur auf der sichtbaren Achse.
Verschiedene Achsen werden niemals zu einem kompensierenden Gesamtscore
verrechnet. Rohereignisse bleiben append-only; ein neuer Prompt-, Recipe-,
Renderprofil-, Character-, Asset- oder Canon-Kontext erhält eine neue Projektion
statt eines stillen Resets oder Decays der alten Historie.

Die fachliche Qualifikation ist fest:

- Reject ist `rejected` und liefert negative Evidenz.
- Keep ist `acceptable_only`: Das Bild ist verwendbar beziehungsweise als
  Arbeitsmaterial erhaltenswert, hat den Auftrag aber nicht vollständig
  getroffen. Es ist dennoch für den Challenger-Pool und das 16er-Spiel
  qualifiziert.
- Favorite ist `target_hit`: Der Spieler bestätigt, dass der konkrete Auftrag
  wirklich getroffen wurde. Es ist ebenfalls Challenger und besitzt nach einer
  bindenden Eliminationsniederlage begrenzten, verlustabhängigen Poolschutz.
- Skip ist `no_evidence`.

Keep und Favorite befüllen gemeinsam den Pool. Das sechzehnte rosterfähige
Eligibility-Ereignis friert atomar die ersten sechzehn noch nicht zugewiesenen
Einträge in stabiler Reihenfolge und damit ihre Bracketplätze ein. Spätere
Bilder warten ohne Score-, Rematch- oder Spielerkuration auf den nächsten Cup.
Das Spiel stellt den 16er-A/B-K.-o.-Bracket als Pflichtquest `READY`
bereit. Der aktuelle Review wird nicht zwangsweise verlassen; das zugehörige
blockierende Gate bleibt bis zum Questabschluss geschlossen. Ohne Amtsinhaber
wird der letzte Teilnehmer unabhängig von seiner ursprünglichen Action erster
Champion. Existiert bereits
ein Champion, wird der 16er-Sieger Challenger und tritt in einem zusätzlichen
direkten Title Match gegen ihn an. Ein blockierendes Asset kann deshalb auch
aus einem siegreichen Keep entstehen, aber weiterhin niemals ohne validierten
Champion abgeschlossen werden.

Eine Evolution Challenge ist zweistufig. In der Qualifikation teilen alle
Kandidaten dieselbe authorisierte semantische Änderung und werden zunächst als
stabile Realisierung dieser neuen Richtung geprüft. Erst der daraus bestätigte
Evolution Challenger tritt in einem separaten Canon Title Match gegen einen neu
gerenderten Control-Arm der aktuellen Canon Revision an. Zwischen Control und
Challenger wird nur die authorisierte `PromptAspectGroup` verändert. Alle ihr
zugeordneten positiven und negativen Atome dürfen gemeinsam wechseln; ihre
Gewichte dürfen innerhalb versionierter Bänder leicht variieren. Technisches
Profil, Assetrolle, alle übrigen Promptgruppen und gepaarte Seeds bleiben
konstant. Anschließend belegen weitere Seeds, dass der neue Stand nicht nur für
einen Zufallstreffer funktioniert.

Die Gruppengrenze ist semantisch und nicht textuell. Ein Hair Try kann daher
mehrere Bracket-Prompts zu Farbe, Schnitt, Länge, Textur und widersprechenden
Negatives umfassen und bleibt dennoch genau ein zusammenhängender Try. Haare und
Brille oder Haare und Outfit sind dagegen zwei unabhängige Gruppen und dürfen
nicht in demselben Evolution Try geändert werden.

Diese Grenze wird nicht als vollständige manuelle Token-Registry authored. Die
Playground-Kinds bilden die Root-Ordnung; pro konkreter Component Revision
gruppiert ein Prompt Aspect Proposer sämtliche vorhandenen gewichteten positiven
und negativen Atome, ein unabhängiger Judge akzeptiert oder fordert eine neue
Proposal Revision und Code validiert danach vollständige genau-einmalige
Mitgliedschaft, Overlap/Orphans und Locks. Erst der akzeptierte Snapshot wird
registriert und von Challenges wiederverwendet.

Wenn Semantik, Formulierung und Gewichte innerhalb derselben Gruppe gemeinsam
variieren, erhält der Gewinner ausschließlich `PromptAspectGroup`-, Recipe- und
Combo-Credit. Kausaler Credit für ein einzelnes Token oder Gewicht entsteht nur
in einem gesonderten Weight- oder Token-only-Trial mit ansonsten identischer
Gruppensemantik.

Erst ein bestätigter Title-Match-Sieg, bestandene
Identity-/Diversity-/Compatibility-Gates, qualifizierte Booster-/Bildspiel-
Evidence und ein weiterhin gültiger authored Mutability-Korridor erzeugen eine
neue Canon Revision. Ohne
belegten Sieger bleibt die aktuelle Revision aktiv; der qualifizierte
Evolution Challenger darf als verworfene oder vertagte Evidence erhalten
bleiben.

Die Zulassung zur Evolution Challenge hängt von Slotwiderstand,
`CharacterCanonStability`, Änderungsgröße, qualifizierter Booster-/Bildspiel-
Evidence und dem authored Mutability-Korridor ab. Geringe Stabilität erleichtert
frühen visuellen Einfluss. Freundschaft, Love-Interest-Status, Chat und andere
soziale Zustände öffnen dagegen keinen charactereigenen visuellen Slot und
senken seinen Widerstand nicht. `system_locked` Constraints bleiben grundsätzlich
außerhalb der visuellen Änderungsautorität des Spielers.

Credit bleibt so eng wie die Evidenz:

- `CharacterVisualEvolutionEvidence` gilt nur für Figur, Prompt Aspect Group,
  Canon Parent und authorisierten Entwicklungskorridor.
- `CharacterOutfitBindingEvidence` und
  `CharacterScenePresentationBindingEvidence` gelten zunächst nur für die
  konkrete Figur und Blueprint-Revision.
- `AssetRoleRecipeEvidence` gilt für Character und Assetrolle.
- `OutfitBlueprintEvidence`, `SceneBlueprintEvidence` oder save-weite
  Profilpromotion benötigen vergleichbare Erfolge über mehrere Figuren und
  passende Assetrollen.

Ein Character-spezifischer Prompt-Erfolg darf daher weder die Schuluniform für
alle Figuren umschreiben noch ein technisches Profil global promoten. Umgekehrt
bleibt ein gemeinsamer Blueprint ein Prior, bis seine konkrete Bindung für die
jeweilige Figur belegt ist.

## Spielmodi als kontrollierte Experimente

Die technische Trial-Struktur wird innerhalb eines langlebigen, semantisch
benannten Champion-Slots angewandt. Slot, Comparison Context, Bildqualifikation
und Recipe-Lineage sind im ergänzenden Vertrag
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md)
definiert. Der Slot legt den visuellen Auftrag fest; der Comparison Context legt
fest, welche technische oder semantische Achse in dieser Runde tatsächlich
variiert wird.

Diese technischen Trials sind Varianten des vollständigen figurenbezogenen
Moduskatalogs in
[`11-game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md).
Pro bekannter Figur dürfen höchstens sechs normale gerenderte Vierer-Games und
pro aktiver sensibler Inhaltseinstellung ein zusätzlicher eigener Viererbatch
`READY` sein. Das Ready-Angebot ist nicht mit dem Playgate-Dreierbudget
gleichzusetzen.

Der Game Mode legt nur die Spielerinteraktion fest. Jede generierende
Questinstanz bindet ihn an genau einen `generation_focus_id`, eine Primary
Question, ein Expected Composition Manifest, Locked/Varied Axes, Evidence Scope
und zulässige Recovery Routes. Ein allgemeiner Fehler darf unabhängig vom Fokus
erfasst werden, erhält aber keinen kausalen Credit für die getestete Achse.
Auswahlspiele auf bereits existierenden Bildern besitzen keinen Generation
Focus und verwenden stattdessen einen `evaluation_focus_id`.

| Spielmodus | Kontrollierte Frage |
|---|---|
| Seed Run | Ist das aktuelle Recipe über mehrere Seeds stabil? |
| Sampler Duel | Welches zulässige Sampler-/Scheduler-Paar funktioniert besser? |
| Parameter Trial | Welche Steps-, CFG- oder Denoise-Variante ist besser? |
| Workflow Trial | Welche qualifizierte Workflowfamilie erfüllt denselben Visual Contract? |
| Checkpoint Trial | Welcher kompatible Checkpoint trifft Qualität und Stil? |
| LoRA Ablation | Hilft ein LoRA beziehungsweise eine einzelne Stärke reproduzierbar? |
| Style Trial | Welche valide Richtung innerhalb des Anime Style Core bevorzugt der Spieler? |
| Recovery Run | Welche kontrollierte Änderung behebt einen konkreten Fehler? |

Der Trial Contract benennt genau eine Hypothese. Innerhalb eines diagnostischen
Vergleichs wird möglichst nur eine Achse verändert. Sampler und Scheduler dürfen
als gekoppeltes Paar gelten, wenn ihre Kompatibilität das erfordert. Der Spieler
sieht Bilder, verständliche Ziele und Auswirkungen; technische Namen bleiben in
der normalen Oberfläche verborgen und in Expertendiagnosen vollständig sichtbar.

Der Advanced Workshop ist ohne Unlock erreichbar und zeigt zusätzlich den
vollständigen Promptblock- und Weight-Diff, Workflowfamilie, Checkpoint,
LoRA-Stack mit Stärken, Renderprofil, Auflösungs-/Upscale-Profil,
Fixed Signature, Variable Axes, Evidenz und Generierungszeiten. Sein Warnhinweis
ist keine Berechtigungsbarriere. Guided Workshop und Story-Trials verwenden
dieselben Contracts, projizieren aber nur Hypothese, Bilder, spielerrelevante
Wirkung und Recovery.

## Seed- und Vergleichsvertrag

Gepaarte Seeds sind für Parameter-, Sampler- und LoRA-Trys innerhalb derselben
Modellfamilie ein wichtiges Kontrollmittel. Ein einzelner fixer Seed reicht nie
für Promotion. Nach dem ersten gepaarten Vergleich folgen neue Seeds zur
Generalisierung.

Bei Checkpoints derselben Architektur reduziert ein identischer Seed Varianz,
garantiert aber keine gleiche Komposition. Zwischen unterschiedlichen
Modellarchitekturen ist derselbe Zahlenwert kein gleichwertiger Bildanker. Ein
Workflowfamilien-Vergleich verwendet deshalb ein festes Panel aus mehreren
semantischen Aufgaben und mehreren Seeds.

Ein für NetaYume optimierter Prompt darf ein anderes Modell nicht unfair
bewerten. Jede Workflowfamilie kompiliert denselben semantischen Visual Contract
mit ihrem eigenen versionierten Prompt Compiler. Verglichen wird die Erfüllung
des Contracts, nicht die wortgleiche Promptzeichenfolge.

Ein bereits akzeptiertes Referenzbild und sein Recipe bilden den visuellen und
technischen Control-Anker. In einem Vierer-Challenge-Panel wird das bewährte
Recipe mit dem aktuellen gepaarten Seed erneut als Control gerendert und gegen
drei kleine Challenger-Diffs geprüft. Die folgenden Panels verwenden neue
Seeds. So bleibt die sichtbare Änderung klein, ohne einen historischen Output
mit einem neuen, seedabhängigen Output zu verwechseln.

Rating, Credit, Confidence und Profilpromotion werden aus strukturierter Evidence
deterministisch berechnet und niemals an ein LLM delegiert. Der Prompt Author
darf technische Challenger-Hypothesen liefern; er bewertet weder das Ergebnis
noch ersetzt er das aktive Control-Profil. Multi-Axis-Challenges erhalten nur
Recipe-/Combo-Credit. Ein Profilkandidat ersetzt das Control-Profil erst nach
ausreichender Evidenz über mehrere Seeds, bestandenem Visual Contract und
Regressionstest. `Control` und `Profilkandidat` sind keine Championtitel einer
Bildkarte.

## VN-Integration und Dreierbudget

Jedes `VNProgressWindow` besitzt für seine Fokusfigur ein gemeinsames Budget von
maximal drei Character-/Calibration-Trials:

```text
FocusCharacterPlayGate
├─ required_trials: bootstrap 0 | regular 1..3
├─ completed_required_trials: 0..3
├─ optional_trials_used: 0..3
├─ total_trials_used: bootstrap 0 | regular 1..3 bei Abschluss
├─ focus_character_id
└─ calibration_questions[]
```

- Nur der Bootstrap ohne challengefähige Grundlage verlangt keinen Trial.
- Jeder reguläre Contract verlangt abhängig von Story, Character-Confidence
  und neuer Assetrolle ein bis drei konkrete Trials.
- Freiwillige Trials dürfen das gemeinsame Dreierlimit auffüllen, ersetzen aber
  nicht die mindestens eine reguläre Pflicht-Runde.
- Pflicht- und freiwillige Trials teilen dasselbe Limit.
- Jeder angerechnete Trial ist an Fokusfigur, Quest, State Revision und eine
  konkrete offene Confidence- oder Qualitätsfrage gebunden.
- Supporting Characters vervielfachen das aktuelle Budget nicht automatisch.
  Fehlende eigene Evidenz führt zu ihrem erreichbaren Character-Pfad.

Routine-Szenen mit bewährten Profilen benötigen regulär eine Runde. Neue
Outfits, erste Ganzkörper- oder Sprite-Rollen, eine neue Profilrevision oder
eine wichtige Szene mit geringer Confidence können die Anforderung auf zwei
oder drei Trials erhöhen.

Nach drei erfolglosen Calibration-Trials wird nicht endlos dieselbe Hypothese
gespielt. Das System behält beziehungsweise reaktiviert das letzte bewährte
Profil, verwirft oder vertagt die experimentelle Variante und speichert die
negative Evidenz. Dieses Limit betrifft ausschließlich das
FocusCharacterPlayGate.

## Unbegrenztes Scene Asset Gate

Das Dreierbudget begrenzt niemals die Produktion blockierender Assets für die
konkret nächste VN-Sequenz:

```text
SceneAssetGate
→ Viererbatch erzeugen und bewerten
→ mit Keep oder Favorite bewertete, transportgültige Kandidaten sammeln
→ geeignete Bildquelle direkt oder über ein getrenntes Asset-Auswahlspiel wählen
→ AssetSourceSelection an genau einen AssetProductionContract binden
→ Ableitung wie Crop, Freistellung oder Normalisierung erzeugen
→ technische und fachliche Asset-QA ausführen
→ AssetVersion APPROVED
```

Existiert keine akzeptierte Bildquelle oder scheitert ihre Ableitung an
Identity-, Style-, Outfit-, Place-, Alpha- oder sonstiger Asset-QA, bleibt das
Gate offen. Das System speichert Quellbindung, Versuch, Befund und Evidenz,
probiert eine andere zulässige Quelle oder verändert kontrolliert Prompt,
Gewichtung, Workflow, Checkpoint, LoRA-Stack oder Renderprofil. Es erzeugt so
viele weitere Produktions-, Qualifier-, Auswahl- und Recovery-Runden wie nötig.

Asset-Build-Runden zählen nicht gegen das Dreierbudget. Ein vorhandenes Bild
reicht nicht; jedes `blocking` Requirement benötigt eine vom Spieler akzeptierte
`AssetSourceSelection` und eine technisch sowie fachlich freigegebene
`AssetVersion` mit Status `APPROVED`. Die Quellkarte darf Keep, Favorite oder
Champion sein. Die Auswahl verleiht keinen Championtitel. Ein fehlgeschlagener
AssetAttempt verändert weder Kartenbewertung noch vorhandene Championtitel.
Optionale Requirements blockieren die VN nicht.

## Promotion, Fallback und Standardgenerierung

Die normale Generation verwendet ausschließlich das aktive, unveränderliche und
für ihren Scope freigegebene Profil. Trials mutieren dieses Profil nicht still:

```text
proposed → testing → candidate → promoted | rejected | deferred
```

Promotion benötigt:

- technisch vergleichbare und vollständige Provenienz,
- mehrere unabhängige Seeds,
- passende Character- und Assetrollen-Evidenz,
- getrennte Taste-, Canon-, Quality- und Reliability-Signale,
- Regression gegen bereits bewährte Aufgaben,
- und eine versionierte Promotion Decision.

Bei Fehler, Abbruch oder geringer Confidence bleibt das letzte bewährte Profil
aktiv. Frühere Bilder und Bewertungen bleiben an ihre exakte Profilversion
gebunden.

## Testbare Invarianten

1. Standardgenerierung bietet normalen Spielern keine freie technische
   Checkpoint-, LoRA- oder KSampler-Mutation an.
2. Ein inkompatibler Checkpoint kann keine Workflowfamilie qualifizieren.
3. Ein Trial verändert genau die deklarierten Achsen.
4. Ein einzelner Seed kann keine Profilpromotion auslösen.
5. Ein globaler Gewinner setzt keinen Character automatisch auf
   `character_proven`.
6. LoRA-Ablation speichert Stack, Stärken und gepaarte Seeds beider Arme.
7. Pro Fokusfigur und regulärem VN Progress Window werden insgesamt mindestens
   eine und höchstens drei Character-Trials angerechnet.
8. Null Pflicht-Trials ist ausschließlich im Bootstrap erlaubt, solange noch
   keine challengefähige Grundlage existiert.
9. Asset-Build-, Qualifier- und Recovery-Runden verbrauchen kein
   Character-Trial-Budget.
10. Ein blockierendes Asset ohne `APPROVED AssetVersion` hält das SceneAssetGate
    unabhängig von Kartenbewertung, Championtitel und Rundenzahl offen.
11. Nach erfolgloser Exploration bleibt das letzte bewährte Profil aktiv.
12. Jedes Bild bleibt vollständig auf Workflow, Modell, LoRA-Stack,
    Renderprofil, Prompt und Seed zurückführbar.
13. Neue Komponenten serialisieren ausschließlich in die festen
    Playground-Rollen und das exakt gewichtete `pos`-/`neg`-Kommaschema.
14. Alte skalare Ratings und ihre Token-/Combo-Aggregate können neue
    strukturierte Review Evidence nicht überschreiben.
15. Ein Run mit mehreren veränderten Achsen erhält keinen kausalen
    Einzeltoken-, Weight-, LoRA- oder Renderparameter-Credit.
16. Der Recipe Snapshot enthält auch nicht direkt in der normalen UI sichtbare
    Workflowfaktoren wie LoRA-Stärken, VAE, Latent-Auflösung und Upscaler.
17. Kein LLM berechnet Ratings, vergibt Credit oder promotet einen Challenger.
18. Ein historisches Master-Bild ersetzt im kontrollierten Panel nicht den neu
    gerenderten Champion-Control-Arm mit gepaartem Seed.
19. Stability-, Recovery- und Binding-Challenges verändern keine
    `CharacterVisualCanonRevision`.
20. Eine Evolution Challenge referenziert eine ausschließlich aus
    qualifizierter Booster-/Bildspiel-Evidence abgeleitete
    `VisualEvolutionProposal` und genau eine Parent Canon Revision.
21. Positiver unbeabsichtigter Drift erzeugt höchstens Evolutionsevidenz, aber
    keine stille Canon-Änderung.
22. Character-Binding-Evidenz kann ohne Cross-Character-Nachweis kein
    gemeinsames Blueprint oder save-weites Profil promoten.
23. Jeder Evolution Try besitzt genau eine `target_prompt_aspect_group_id`; der
    Restprompt einschließlich positiver und negativer Atome bleibt eingefroren.
24. Mehrere Atome und Bounded Weight Diffs innerhalb derselben Zielgruppe gelten
    als ein zusammenhängender Try, erhalten aber keinen kausalen Atom-Credit.
25. Zwei unabhängige Prompt Aspect Groups können nicht durch denselben Evolution
    Try oder dieselbe Canon Revision geändert werden.
26. Eine Evolution Challenge ohne akzeptierte Proposer-Revision, zugehöriges
    Judge-Accept und bestandenen Hard Validator kann keinen Renderjob erzeugen.
27. Judge-Feedback erzeugt eine neue Proposal Revision; es mutiert niemals das
    beurteilte Proposal in place.
28. Ein ausgeschöpftes Providerbudget führt zu Fallback oder Recovery und nicht
    zur Weitergabe eines ungeklärten Prompts an das Player Review.
29. Jeder transportgültige und sichere Output erreicht das Player Review; ein
    semantischer oder visueller Modellbefund darf ihn nicht vorfiltern.
30. Reject, Keep und Favorite speichern mindestens einen versionierten Reason
    Code und genau einen Primary Reason aus derselben Auswahl; kein Secondary
    Reason geht verloren.
31. Maschinelle Diagnoseevidenz bleibt von unveränderter Spieler-Evidence
    getrennt und besitzt keine Autorität, sie zu überschreiben.
32. `skip` erzeugt keine positive oder negative Ratingevidenz und benötigt
    keinen Grund.
33. Favorite liefert stärker positive Evidence als Keep, ernennt aber ohne Cup
    oder Title Match keinen Champion.
34. Der Primary Reason passt zur Action-Polarität; logisch ausgeschlossene
    Reason-Kombinationen werden abgewiesen.
35. Keep projiziert `acceptable_only`, Favorite `target_hit`; beide füllen einen
    Challenger-Pool-Slot und können durch Turniersieg Champion werden.
36. Ein blockierendes Requirement kann durch beliebig viele Keeps, Favorites
    oder Championtitel ohne akzeptierte AssetSourceSelection und validierte
    `APPROVED AssetVersion` nicht freigeschaltet werden.
37. Jede bindende Eliminationsniederlage eines Favorites zählt unabhängig von
    UI-Modus oder Turniername in dieselbe Serie. Es bleibt im Challenger-Pool,
    setzt nach Verlust eins und zwei jeweils denselben vollständigen Challenger-
    Cup wie der amtierende Champion aus; Verlust drei in Folge geht dedupliziert
    in Delete or Live. Jeder bindende Eliminationssieg setzt den aktuellen
    Verlustfolgezähler auf null, nicht die historische Match-Evidence. Gleichstand,
    Skip, Abbruch und `nicht vergleichbar` zählen nicht. Ein Keep geht bereits
    nach seiner ersten bindenden Eliminationsniederlage dorthin.
38. `Live` reaktiviert ein ausgeschiedenes Bild mit unverändertem Review. Ein
    Favorite bleibt Favorite, setzt Verlustserie und Cooldown auf null und
    erhält ein neues Eligibility-Ereignis. Es darf ebenso wie ein gerettetes
    Keep niemals im bereits eingefrorenen
    Turnier antreten. `Delete` entfernt sein Dateipaar; keine DOA-Entscheidung
    mutiert den laufenden Bracket.
39. Jeder bindend entschiedene Eliminationsvergleich erzeugt kontextgebundene
    paarweise Qualitätsevidenz: Gewinner positiv, Verlierer negativ. Ein Sieg setzt nur
    `consecutive_loss_count` zurück; Match- und Verlusthistorie bleiben
    append-only erhalten.
40. Die Schwelle von sechzehn erzeugt eine Pflichtquest und blockiert den
    zugehörigen Fortschritt, erzwingt aber keinen Redirect aus einem laufenden
    Review oder Viererbatch. Ein atomarer Eligibility-Cut friert die ersten
    sechzehn Einträge ein; alle späteren warten auf den nächsten Cup.
41. Die vier Standardbewertungen werden ohne Reason-Unterbrechung abgeschlossen;
    danach begründet eine zweite Runde jedes nicht übersprungene Bild erneut
    einzeln innerhalb derselben QuestSession.
42. Ein Reason gehört genau zu einem Bild. Eine Batchevidenz darf nur als
    deterministische Projektion der vier Einzelereignisse entstehen.
43. Die normale Begründungsrunde besitzt keinen Freitext; `Nicht sicher` bleibt
    als versionierter Escape-Code zulässig.
44. Pro bekannter Figur sind höchstens sechs normale Vierer-Games und je aktiver
    sensibler Inhaltseinstellung ein zusätzliches Vierer-Game vollständig
    gerendert `READY`; ein vorhandener 16er-Cup darf ohne neue Bilder zusätzlich
    bereitstehen.
45. Jede generierende Quest besitzt genau einen primären Generation Focus;
    Game Mode und Generation Focus sind getrennte Felder.
46. Ein Auswahlspiel ohne neue Bilder besitzt keinen künstlichen Generation
    Focus und deklariert stattdessen einen Evaluation Focus.
47. Intent Mismatch, Visual Defect, Character Drift, Asset-Unverwendbarkeit und
    ästhetische Präferenz werden getrennt gespeichert und projiziert.
48. Negative Evidence einer Ebene darf positive Evidence einer anderen Ebene
    desselben Bildes nicht überschreiben.
49. Recovery verändert ausschließlich die durch Focus Contract, Reason Code und
    Evaluation Layer autorisierten Achsen.
50. Verhältnis und Confidence werden pro Bild, Context Hash, Layer und Achse
    getrennt projiziert. Ein neues Bild ist bei wenig Historie unsicherer, nicht
    automatisch schlechter; Cross-Axis-Canceling und stiller Raw-Evidence-Decay
    sind ausgeschlossen.
51. Jede normale generierende Vierergruppe besitzt vor Submission genau eine
    validierte `BatchDiversityPlanRevision` mit vier stabilen Anzeigeslots. Jeder
    Slot bindet entweder ein unverändertes Carried Image oder ein neues immutable
    Recipe mit erwartetem sichtbarem focusgebundenem Delta.
52. Neu generierte Slots mit `seed_policy=independent` besitzen unterschiedliche
    Seeds und Recipe Hashes. `paired_control` darf einen Seed nur bei
    verschiedenen Recipes und isoliertem Delta teilen. Identisches Recipe oder
    identische vollständige Wiederholung verlangt `reproduce_calibration`;
    undeklarierter Reuse oder leeres Delta blockiert die Submission.
53. Ein anderer Seed allein beweist keine sichtbare Diversität. Die
    Batchbeobachtung trennt technischen Reuse, Prompt-/Modellkonvergenz,
    kontrollierte Diversität, Multi-Axis-Confounding und Unsicherheit.
54. VLM- und Embedding-Diagnosen verändern weder Kartenreihenfolge noch
    Reviewpflicht und starten keine Ersatzgeneration. Nur Human Review erzeugt
    Evidence; nur ein neuer Planner-/Guardian-Zyklus autorisiert den Folge-Try.
55. Restart und Recovery erhalten Planrevision, Slot, Seed und Recipe Hash und
    ergänzen ausschließlich fehlende autorisierte Slots ohne Doppel-Submit.
56. `ExperimentSpec` ist ab Schema 56 die einzige Achsenautorität. CFG wird in
    Integer-Tenths auf dem 0,1-Raster und Steps als positive Ganzzahl auf dem
    Einer-Raster gespeichert. Sampler, Render-Scheduler, CFG, Steps und Denoise
    verändern in einem Einzelachsentrial jeweils genau ein Feld.
57. `render_parameter_interaction` ist ausschließlich ein gepaartes CFG×Steps-
    2×2-Panel und verlangt vorher isolierte Evidence beider Einzelachsen. Es
    erzeugt Interaction-, aber keinen isolierten CFG- oder Steps-Credit.
58. `aspect_weight` verändert mehrere Gewichte ausschließlich innerhalb einer
    akzeptierten Aspect Group. `prompt_atom_weight` bleibt der eindeutige Name
    für ein isoliertes Einzelatomgewicht; historisches `prompt_weight` ist nur
    ein Read-Alias.
59. Im Sechserfenster werden Technik, atomare/Aspect-, Composition-/Authoring-,
    Coverage- und zwei evidence-gesteuerte Fragen reserviert; im Zwölferfenster
    wird zusätzlich `(experiment_kind, target_role, operation)` ausgeglichen.
    Nur tatsächlich Ready gewordene Karten zählen als Exposition.

Die Reason Registry ist absichtlich erweiterbar. Konkrete Frage, sichtbare
Chipreihenfolge und erlaubte Gründe werden pro Bild aus Quest Contract,
Generation/Evaluation Focus, Assetrolle, Expected Composition, Locked/Varied
Axes und Änderungsauftrag kompiliert. Neue Kontexte ergänzen eine neue
Registry-Version; sie verlangen keinen vorab vollständig aufzuzählenden globalen
Fragenkatalog.

## Spätere adaptive Revisionen und technische Qualifizierung

Diese Liste bezeichnet keine leeren Startwerte für den aktuellen
Bildspiel-/Bewertungsumbau. Technische Generierungswerte beginnen in der
`DevelopmentGenerationBaseline`, adaptive Policies mit einer versionierten
Initialversion und UX mit barrierearmen Defaults. Danach werden die folgenden
Werte entweder aus neuer Spieler-Evidence revidiert oder in ihrem späteren Slice
mit Messungen und Bake-offs qualifiziert:

- qualifizierte Workflowfamilien und kompatible Checkpoint-Pools,
- LoRA-Rollen, Stärkeintervalle und Konfliktregeln,
- genaue Seed-Panel-Größe pro Trialklasse,
- Confidence- und Promotion-Schwellen,
- Zuordnung regulärer Scene-Klassen zu ein bis drei Pflicht-Trials,
- Schwellen, Wiederholungszahl und Cooldowns, ab denen beobachteter Drift eine
  Evolution Challenge anbieten darf,
- Panelzahl, Kandidatenumfang und Promotion-Schwellen der zweistufigen
  Evolution-Qualifikation und des Canon Title Match,
- Compatibility-Gates zwischen Canon-, Outfit-, Scene- und Assetrevisionen,
- technische Weight-Bänder und Deltas der aus konkreten Playground-Prompts
  durch Proposer/Judge abgeleiteten Aspect Groups; ihre Atommitgliedschaft ist
  keine offene manuelle Authoringfrage,
- Proposer-/Judge-Confidence-Schwellen, Rundenzahl pro Providerzyklus,
  Judge-Modelltrennung und Fallbackreihenfolge,
- numerische Attribution kombinierter Primary- und Secondary-Reasons innerhalb
  der bereits entschiedenen kontextuellen Guided-Evidence-Runde,
- Revalidierungsumfang nach einer Profilpromotion,
- Hardware-, VRAM-, Laufzeit- und Backpressure-Budgets,
- sowie UI-Namen und diegetische Inszenierung der technischen Spielmodi.
