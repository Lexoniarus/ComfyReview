# Academy-Abschluss, LoRA-Audit und New Game Plus

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 10. September 2026

## Zentrale Entscheidung

Der Abschluss des zweiten Academy-Jahres und die technische LoRA-Validierung
sind zwei getrennte Zustände. Der Übergang nach dem ersten Jahr ist nur ein
persistenter Zwischenstand: Er beendet weder den Run noch eröffnet er Audit,
Auffüllen, Ending oder New Game Plus. Das finale Ending darf durch ein
fehlgeschlagenes Training nicht rückwirkend blockiert werden.

Wie viele Character-LoRAs ein Run hervorbringt, wird nicht vorab festgelegt.
Der Code bewertet am Ende des vollständigen zweijährigen Academy-Runs den tatsächlich erreichten Story- und
Visual-Stand aller sechzehn Figuren. Bereits vollständig LoRA-ready Figuren
sind direkt wählbar. Bei noch nicht fertigen Figuren entscheidet der erreichte
Storyprogress zusammen mit der Größe der Restlücke, ob eine begrenzte
Auffüllphase angeboten wird. Der Spieler entscheidet anschließend selbst,
welche Figuren aufgefüllt, trainiert und in New Game Plus übernommen werden.

Freigestellte, normalisierte oder aus einem Basissprite zusammengesetzte
`DerivedAssetImage`-Artefakte sind reine Runtime-/VN-Assets. Sie sind weder
LoRA-Dataset-Candidates noch Coverage-Nachweise und werden nicht in Training,
Holdout oder Validation exportiert. Das ursprüngliche Quellbild behält seine
eigene, davon unabhängige Dataset-Eignung.

## Laufende interne Auswertung, einmaliges Spielerangebot

Der Director darf `LoRAReadiness` während beider Academy-Jahre intern fortlaufend
berechnen, damit Questplanung und Dataset Coverage nicht blind arbeiten. Das
erste verbindliche, spielerseitige Übernahmeangebot erfolgt jedoch beim
Abschluss des zweiten Academy-Jahres.

## Zwei getrennte Auswertungen mit unterschiedlicher Wirkung

```text
NarrativeQualification
├─ introduction und Character Development
├─ authored Character Milestones
├─ ausreichende gemeinsame Story-Evidenz
└─ gültiger Abschlussstand der betreffenden Route oder Teilroute

VisualLoRAReadiness
├─ gesperrter Character Canon
├─ gültige Dataset-Version
├─ Identity- und Artstyle-Stabilität
├─ Coverage und Diversität
├─ behobene kritische Fehlercluster
├─ Prompt-/Workflow-/Modell-Lineage
└─ unabhängiger Validation-/Holdout-Vertrag
```

Friendship oder Romance erzeugt nicht automatisch technische Readiness. Die
narrative Auswertung wird insbesondere dann zum Zulässigkeitskriterium, wenn
eine technisch noch nicht fertige Figur nach dem Ending aufgefüllt werden soll.
Ein bereits vollständig LoRA-ready Candidate bleibt dagegen direkt wählbar.

## Ergebnisgruppen

### `ready`

Visual LoRA Readiness ist vollständig erfüllt. Die Figur kann sofort für
Training und anschließende Validierung ausgewählt werden. Ihr Storyprogress
wird im Outcome und Carry-over festgehalten, bildet aber kein zusätzliches
Auffüllgate, weil keine Restlücke mehr geschlossen werden muss.

### `fillable`

Die Figur ist noch nicht LoRA-ready, wurde aber narrativ ausreichend entwickelt
und es fehlen nur wenige, klar begrenzte visuelle Nachweise. Der Audit nennt
fehlende Requirements, erwartete Runden und einen maximalen Auffüllumfang.

Die Auffüllphase darf nur technische beziehungsweise visuelle Lücken schließen.
Sie darf nach dem Ending keine verpasste Friendship-/Romance-Route, unbekannte
Outfits, neue Character Milestones oder nicht erlebte Storykontexte erfinden.

### `not_qualified`

Die Figur ist nicht LoRA-ready und entweder reicht die narrative Entwicklung
nicht für ein Auffüllangebot oder der visuelle Abstand überschreitet den
erlaubten Auffüllrahmen. Sie kann in diesem Run nicht nachträglich durch
unbegrenzten Grind zu einer NG+-Figur gemacht werden.

## Deterministischer Audit

```text
CharacterAcademyRunEndAudit
├─ character_id
├─ story_progress_revision
├─ narrative_qualification_checks[]
├─ dataset_version_id
├─ visual_readiness_checks[]
├─ unresolved_failure_clusters[]
├─ status: ready | fillable | not_qualified
├─ fill_up_plan_id oder null
├─ estimated_rounds
├─ estimated_generation_time
└─ rules_version
```

LLMs dürfen die verständliche Präsentation formulieren, aber weder Status noch
fehlende Requirements oder Schätzwerte verbindlich bestimmen.

## Ablauf

```text
zweites Academy-Jahr und Endings abschließen
→ alle 16 CharacterAcademyRunEndAudits erzeugen
→ ready, fillable und not_qualified erklären
→ Spieler wählt beliebig viele fillable Figuren zum Auffüllen
→ Spieler wählt beliebig viele qualifizierte Figuren zum Training
→ jedes Artefakt separat validieren
→ Spieler wählt beliebig viele validierte Figuren für NG+
→ unveränderliches NewGamePlusManifest erzeugen
```

Der Spieler darf eine, mehrere oder keine Figur übernehmen. Eine Figur wird erst
nach erfolgreicher Artefaktvalidierung tatsächlich NG+-fähig.

## Zustände

```text
ChronicleRun
├─ academy_year: 1 | 2
├─ narrative_status: active | inter_year_transition | academy_completed
├─ production_status: active | auditing | filling | training | resolved
├─ character_outcomes[16]
├─ narrative_endings[]
└─ validated_lora_artifact_ids[]

CharacterProductionOutcome
├─ character_id
├─ narrative_qualification
├─ visual_readiness
├─ audit_status
├─ selected_for_fill_up
├─ selected_for_training
├─ training_run_ids[]
├─ validated_artifact_ids[]
└─ selected_for_new_game_plus
```

## Fehlgeschlagene Validierung

Ein fehlgeschlagenes Training oder Validation Report ändert das Ending nicht.
Es erzeugt nachvollziehbare Repair-, Coverage- oder Stability-Quests. Der
Spieler darf:

- die Figur reparieren und erneut trainieren,
- ein anderes Candidate-Artefakt validieren,
- oder die Figur aus der NG+-Auswahl entfernen.

## Training und Validierung über ComfyUI

Für das vollständige MVP existiert genau ein primärer Produktionsweg:

```text
locked DatasetVersion
→ versionierten Trainingsworkflow im ComfyUI-Kontext auswählen
→ freigegebene Parameter setzen und fachlichen LoRATrainingRun anlegen
→ über ComfyUI API einreihen und Queue, Progress, History und Fehler spiegeln
→ .safetensors im ComfyUI-LoRA-Ordner referenzieren und Hash/Lineage registrieren
→ vorhandene Control-, Transfer- und Stressworkflows über ComfyUI starten
→ LoRA Blind Test/Boss Fight und deterministischen Validation Report auswerten
```

ComfyUI besitzt Trainingscode, Custom Nodes, Workflowdateien, Queue,
GPU-Ausführung und LoRA-Ordner; diese Funktionen werden in der Anwendung nicht
nachgebaut. Die Anwendung besitzt nur die fachliche Reihenfolge, spiegelt
Jobzustände und behält die Freigabeautorität. Training und normale Bildgeneration
teilen einen Submission-/Backpressure-Scheduler vor der ComfyUI-Einreihung;
reale Laufzeit bewegt keine Storyzeit. Ein manueller externer Import gehört
nicht zum primären MVP-Pfad.

## New Game Plus

```text
NewGamePlusManifest
├─ parent_chronicle_run_id
├─ selected_character_artifacts[]
│  ├─ character_id und Character-Canon-Snapshot
│  ├─ validated_lora_artifact_id
│  ├─ Base-Model- und Workflow-Kompatibilität
│  └─ Dataset-/Training-/Validation-Lineage
├─ new_run_rules_snapshot
├─ new_run_content_snapshot
├─ carry_over_policy
└─ created_at
```

Nur explizit ausgewählte, validierte und kompatible Artefakte werden geladen.
Ein später verbessertes Artefakt ersetzt nicht still die Basis eines bereits
gestarteten NG+-Runs.

Im initialen NG+-Schnitt besteht `carry_over_policy` ausschließlich aus den
ausgewählten validierten Character-LoRAs und ihrer technischen Lineage. Bilder
bleiben Provenienz. Personality, Relationships, Memories, Story-State und
freigespielte Content-Snapshots werden nicht übernommen.

## Noch offen beziehungsweise zu kalibrieren

- Mindest-Milestones für Narrative Qualification,
- maximal erlaubte Restlücke für `fillable`,
- Berechnung der erwarteten Runden und Generierungszeit,
- konkrete GPU-Prioritäten, Pausen-/Resume-Regeln und maximale Parallelität von
  Training, Validation und normaler Generation,
- Behandlung einer nicht mehr verfügbaren Base-Model-Version,
- und Verhalten des neuen Cast Assemblers bei mehreren übernommenen Figuren.

Diese Werte müssen vor dem Academy-Abschluss-Slice entschieden oder dort durch
versionierte Playtests kalibriert werden.
