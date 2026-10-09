# Orchestration Guardian und Systemüberwachung

Dokumentrolle: fachlicher MVP-Produkt- und Betriebsvertrag

Autorität: autoritativer Zielvertrag für maschinelle Arbeitsfreigabe,
KI-Orchestrierung, Monitoring, Reconciliation und Recovery

Stand: 10. September 2026

## Rollierender Vertrag ab Schema 47

Der am 3. September 2026 freigegebene [rollierende M6-Lernloop](rolling-m6-learning-loop.md)
präzisiert die früheren Ein-Achsen-/Recovery-Aussagen dieses Dokuments:
Neue Human Evidence geht in die gemeinsame Kandidatenplanung ein, nicht in einen
automatischen Reparatur-Child. Nur bereits materialisierte, autorisierte
Providerarbeit darf Retrieval/Prompt Machine beim technischen Resume überspringen.
Unbegonnene Planung wird zusammengeführt; ab dem ersten KI-WorkIntent bleibt das
vollständige Eingangsmanifest unverändert. Andere Karten bleiben erhalten.
Schema 47 und sein separater Abnahmenachweis sind nicht durch ältere
`AUTOMATED_VERIFIED`-Statuszeilen bereits praktisch abgenommen.

## Zweck

Character Chronicle verwendet mehrere lokale KI- und Ausführungssysteme:
Prompt Proposer und Judge, LM Studio, ComfyUI, Image Analysis, Asset Processing
und später LoRA-Training. Kein Adapter und kein Modell darf selbst entscheiden,
welcher fachliche Auftrag als Nächstes notwendig, erlaubt oder wirksam ist.

Der `OrchestrationGuardian` ist die deterministische Schutz- und
Koordinationsinstanz über den bestehenden Domain-Plannern, dem Local AI
Orchestrator und dem Submission Scheduler. Er prüft ereignisgetrieben und durch
regelmäßige Reconciliation, ob ein weiterer Auftrag benötigt wird, ob seine
Voraussetzungen noch gelten und ob er sicher eingereiht werden darf.

Er ist kein LLM-Agent und erzeugt keine freie Produktwahrheit.

## Prozess-, Lane-, Claim- und Transaktionsgrenze unter Schema 58

FastAPI führt keine Sweeps und keine Providerarbeit aus. Schema 49 trennte dafür
API und einen Orchestrierungsworker. Schema 50 präzisiert diesen Vertrag durch
fünf getrennte Runtime-Lanes. Beide Versionsangaben bezeichnen eingeführte
Grundlagen; die aktuelle operative Schemaautorität ist Schema 58. Neben API und
den fünf Maschinenlanes beaufsichtigt `main.py --role all` einen priorisierten
`player-writer`. Er claimt keine `worker_jobs`, sondern verarbeitet ausschließlich
typisierte Spielercommands über authentifiziertes Loopback-IPC und schreibt die
vorhandenen Schema-57-Idempotenzbelege:

| Lane | Autorisierte Verantwortung |
|---|---|
| `coordinator` | Director, Supply, Kandidatenplanung, Retrieval/Context, Compiler und Readiness-Barrieren |
| `lm_studio` | Text-Embeddings, Prompt Machine und Judge |
| `comfyui` | Submission, Queue-/History-Polling und Output-Ingest |
| `image_analysis` | Docker-VLM und SigLIP |
| `maintenance` | Sweeps, historische Arbeit und Index-Rebuilds ohne fremde Providerautorität |

Jede Lane besitzt eine eigene Runtime-Lease mit monotoner Fencing-Epoch. Jeder
Job ist immutable einer Lane zugeordnet; sein Claim bindet Job-ID, zufälliges
Claim-Token, Worker-ID, Lane-Runtime-Key und Runtime-Epoch. Verliert ein Worker
die Lane-Lease, darf er weder seinen Jobclaim verlängern noch einen Adapter
aufrufen oder ein Resultat abschließen. Jede Provider-, WorkIntent-, Recipe- und
Bildmutation prüft diese Bindung erneut in derselben kurzen Transaktion.
Unbekannte Jobtypen blockieren sichtbar und erhalten keine implizite
Coordinator-Autorität.

Provider-I/O findet ausschließlich zwischen kurzen Persistenzphasen statt:
Requestvertrag und Providerjob werden commitet, danach folgt der externe Call,
anschließend wird das gefencte Ergebnis commitet. Eine Ressourcenmessung darf
keine fremde Domaintransaktion committen. Temporäre Ressourcen-, Pilot- oder
Providerwartebedingungen bleiben wartend und verbrauchen kein Fehlerbudget;
eine valide Providerantwort wird nicht durch eine spätere Warnung entwertet.
Ein Transportfehler nach einem Submit gilt als unbekanntes Ergebnis, bis Queue
oder History die Korrelations-ID eindeutig auflöst. Ein physisches
Provider-`success` wird zunächst nur `succeeded`; erst der vollständig
persistierte Domain-Ingest darf den Job `ingested` setzen und die Lease
freigeben. Bei einer Übernahme nach Ablauf oder Verlust der alten Lease werden
Providerjob, neue Decision und neue Lease gemeinsam mit genau einem Reattach-
Ereignis gebunden. Ein normaler Heartbeat erzeugt keine neue Decision.
Bleibt die persistierte Korrelation auch nach 30 vollständigen Queue-/History-
Prüfungen unauflösbar, wechselt der Providerjob in eine sichtbare Quarantäne.
Das bewahrt den unbekannten Ausgang als Integritätsblocker, beendet aber die
globale Ressourcen-Backpressure.

Die M6-Materialisierung folgt derselben kurzen Transaktionsgrenze. Diffs, Hashes
und Panelberechnung laufen außerhalb eines Writes. Vor jedem gefencten
Checkpoint wird eine neue kurze `BEGIN IMMEDIATE`-Transaktion eröffnet; Claim,
Lane und Runtime-Epoch werden darin erneut geprüft. Erst der finale atomare
Publish macht Plan, vier Slots und Comfy-Outbox gemeinsam sichtbar.

Eine LM-Studio-Instanz ist nur durch ihre exakte, im Prozess bekannte oder im
Model-Lifecycle persistierte Runtime-ID Chronicle-eigen. Nur diese konkrete ID
darf auch profilübergreifend entladen werden. Ein bloß passendes Namenspräfix
reicht nicht aus; nicht belegte fremde Instanzen bleiben geschützt und erzeugen
einen sichtbaren Blocker.

Für kontrollierte Bestandsreferenz-Läufe ist ein Enrollment die zwingende
Arbeitsgrenze. Ein periodischer Sweep darf nur offene Enrollments fortsetzen;
er darf niemals aus dem Vorhandensein alter Bilder, Reviews oder Soll-/Ist-
Differenzen neue KI-Arbeit ableiten. `approve` verlangt bestandene Capability-
Reports, `start` verlangt Guardian-Enforce für `TextEmbedding`,
`ImageObservation` und `ImageEmbedding`. Generation bleibt unberührt und ein
Bestandslauf erzeugt keine ComfyUI-Aufträge. Details stehen im
[`Bestandsreferenzvertrag`](historical-reference-bootstrap-and-evaluation.md).

## Keine konkurrierende Autorität

Die bestehenden Rollen bleiben getrennt:

```text
Chronicle Simulation / Rules Snapshots
→ bestimmt fachliche Wahrheit, Gates und erlaubte Übergänge

Campaign Director
→ projiziert die nächste spielerseitige Hauptaktion

Domain Planner
→ materialisiert begründete WorkIntents aus Story-, Slot-, Stability-,
  Recovery-, Asset- und Datasetbedarf

Orchestration Guardian
→ validiert Bedarf, Abhängigkeiten, Policies, Fähigkeiten, Staleness,
  Fairness und Ressourcen; autorisiert höchstens den nächsten zulässigen Schritt

LocalAiOrchestrator
→ projiziert konkrete Provider- und Funktionsfähigkeit

Submission Scheduler
→ ordnet autorisierte GPU-/CPU-Aufträge unter Backpressure

Provider Adapter / Worker
→ führt exakt den freigegebenen Auftrag aus

Reconciler
→ übernimmt Resultate, repariert Projektionen und stößt die nächste Prüfung an
```

Der Guardian ersetzt weder Campaign Director noch Domain Planner oder
Submission Scheduler. Er verbindet ihre Entscheidungen durch einen gemeinsamen
Work-Lifecycle und verhindert, dass ein Teilsystem an den anderen vorbei
Aufträge erzeugt.

## Autoritative Eingaben

Jede Guardian-Entscheidung verwendet nur versionierte, persistierte oder
rebuildbare Eingaben:

- aktuelle Run-, Campaign-, Character- und Canon-Revision,
- SchoolYearVisualPlan-, Portfolio-, Relationship- und Participant-Projektionen,
- Story-, Scene-, Play- und Assetgate-Projektionen,
- ChampionSlot-, ComparisonContext-, Pool-, Champion- und Mastery-Zustand,
- Evaluation-, Recovery- und Generation-Knowledge-Projektionen,
- Content Policy und Rules Snapshot,
- Provider-Capability- und Modell-Lineage-Reports,
- Workflow-, Recipe-, Asset- und Referenzverfügbarkeit,
- Queue-, Lease-, Storage-, VRAM- und Backpressure-Projektionen,
- Retry-, Timeout-, Quarantäne- und Stalenesszustände,
- sowie Fairness- und Starvation-Historie über Characters und Scopes.

LLM-Text, Provider-Selbstauskunft oder UI-Zustand allein ist keine
Arbeitsautorität.

## Work Intent und Next Work Decision

Ein fachlicher Planner erzeugt einen deklarativen `WorkIntent`, keinen direkten
Providercall. Er enthält mindestens:

- stabile `work_intent_id` und Idempotency Key,
- Intent-Klasse und Zielentität,
- fachliche Begründung und Prioritätsklasse,
- erwartete Inputs und Outputs,
- gebundene Rules-, Contract- und Policy-Revisionen,
- Capability- und Ressourcenanforderungen,
- Abhängigkeiten und Blocker,
- bei einer Vierergeneration die gebundene `BatchDiversityPlanRevision`, den
  stabilen Slot, Source Kind, Seed Policy, Seed/Seed Group, Recipe Hash und
  erlaubte Batch-Geschwister,
- Staleness-/Supersession-Bedingungen,
- Retry-Budget und Recovery Route,
- sowie die erlaubte schreibende Abschlussfunktion.

Der Guardian erzeugt daraus eine persistierte `NextWorkDecision`:

```text
authorized
├─ genau gebundener WorkIntent
├─ Decision- und Policy-Revision
├─ Capability Snapshot
├─ Prioritäts- und Fairnessbegründung
├─ Idempotency-/Lease-Key
└─ erlaubter nächster Zustandsübergang

blocked
├─ maschinenlesbare Blocker
├─ verständliche Diagnose
└─ Wake-up-Bedingung

superseded
└─ Revision oder Bedarf ist nicht mehr aktuell
```

Eine Entscheidung autorisiert genau einen begrenzten nächsten Schritt. Sie ist
kein Blankoscheck für eine autonome Kette weiterer Modellaufrufe.

### Viererbatch, Slotautorität und Collapse-Reaktion

Eine generierende Vierergruppe besitzt einen übergeordneten Batch-Intent, vier
stabile Anzeigeslots und null bis vier einzeln idempotente Recipe-Intents; übrige
Slots referenzieren unveränderte Carried Images. Vor der ersten Submission prüft
der Guardian, dass alle vier auf dieselbe validierte `BatchDiversityPlanRevision`
zeigen, ihre Character-/Style-/Scope-/Focus-Locks kompatibel sind und Seed,
Recipe Hash sowie erwartetes sichtbares Slotdelta jedes neu erzeugten Slots
eindeutig bleiben. Bei `independent` müssen Seeds verschieden sein;
`paired_control` darf denselben Seed nur bei verschiedenen Recipes und isoliertem
Delta teilen. Identisches Recipe oder vollständige Wiederholung ist nur unter
`reproduce_calibration` zulässig. Undeklarierter Reuse oder ein leeres Delta
blockiert normale Arbeit.

Fachliche Recovery besitzt keinen alternativen Generationseingang. Jeder neue
kreative Batch benötigt die normale Lernentscheidung und eine vollständige
`BatchDiversityPlanRevision`. Technische Wiederaufnahme ist ausschließlich dann
zulässig, wenn dieselbe normale Karte ihre vier Recipes und Seeds bereits
materialisiert und autorisiert hatte. Sie überspringt keine kreative Arbeit,
sondern setzt nur offene Providerarbeit fort; WorkIntent, Decision, aktive
Ressourcenlease, ProviderJob, ComfyUI-Backpressure und Output-Reconciliation
bleiben verpflichtend.

Restart und Recovery rekonstruieren jeden Slot aus seiner immutable Provenienz.
Ein fehlender Slot wird mit genau seinem autorisierten Recipe fortgesetzt; ein
bereits fertiger Slot wird weder ersetzt noch als vermeintliche Diversitäts-
Korrektur neu generiert. Output-Ingest projiziert erst nach eindeutiger
Slotzuordnung eine `BatchDiversityObservation`.

`undeclared_recipe_or_seed_reuse` ist technische Recovery. Ein
`model_or_prompt_convergence`-Befund trotz gültiger unterschiedlicher Recipes
beziehungsweise zu hoher Ähnlichkeit mit Carried Images ist dagegen
fachliche Eingabe für einen neuen Generation-Plan. Weder VLM noch Embedding-
Worker darf daraufhin direkt weitere ComfyUI-Arbeit starten. Der Planner erzeugt
einen neuen Try mit stärkeren weiterhin focusgebundenen Deltas; der Guardian
prüft ihn wie jeden anderen WorkIntent erneut auf Revision, Content Policy,
Ressourcen und Staleness. Damit erzeugt ein Collapse weder eine autonome
Renderloop noch parallele Ersatzbatches.

## Auslöser und regelmäßige Überwachung

Der Guardian läuft primär ereignisgetrieben nach:

- Spielerentscheidung oder Sessionabschluss,
- neuer beziehungsweise revidierter Evidence-Projektion,
- Slotqualifikation, sechzehntem Challenger oder Turnierende,
- Story-, Gate-, Canon-, Content- oder Rules-Revision,
- Jobabschluss, Fehler, Timeout oder Providerstatusänderung,
- neuem Asset-, Workflow-, Modell- oder Referenzmaterial,
- sowie Änderung von Queue-, Storage- oder Ressourcenstatus.

Zusätzlich läuft ein begrenzter periodischer Reconciliation Sweep. Er dient
ausschließlich dazu, verlorene Wake-ups, abgelaufene Leases, verwaiste Jobs,
stale Recipes, unvollständige Ingests und inkonsistente Projektionen zu finden.
Er erzeugt keine ungebremste Polling- oder Renderloop.

Jeder Sweep besitzt High-Watermark, Seitenlimit, Zeitbudget und Fairnesscursor.
Eine unveränderte Blockade erzeugt keine Folge von identischen Aufträgen oder
Events.

## Entscheidungszyklus

```text
1. Facts und Projektionen bis zum High-Watermark lesen
2. offene fachliche Bedarfe materialisieren oder aktualisieren
3. erledigte, doppelte oder superseded WorkIntents schließen
4. harte Safety-, Content-, Provenienz- und Authority-Gates prüfen
5. Contract-, Context- und Revisionskompatibilität prüfen
6. Provider- und Funktionsfähigkeit prüfen
7. Queue-, Storage-, VRAM- und Backpressure prüfen
8. Priorität, Fairness, Starvation und Retrybudget auswerten
9. genau den nächsten begrenzten Schritt autorisieren oder Blocker persistieren
10. Lease atomar erwerben und an den zuständigen Adapter übergeben
11. Heartbeat, Resultat oder Timeout überwachen
12. Resultat idempotent ingestieren und Projektionen rebuilden
13. nächste Guardian-Prüfung auslösen
```

Zwischen Schritt 9 und Submission werden Zielrevision und Voraussetzungen
erneut atomar validiert. Ein veralteter WorkIntent darf trotz früherer
Autorisierung nicht mehr eingereiht werden.

## Prioritätsklassen

Die konkrete Gewichtung ist versionierte Policy. Die fachliche Ordnung lautet:

1. bereits gestartete persistente Jobs sicher abschließen oder reconciliieren,
2. fortsetzbare unvollständige Spielerabläufe sichtbar halten sowie
   Datenintegrität, abgelaufene Leases und blockierende technische Recovery,
3. unmittelbar blockierende Story-/Scene-Asset-Bedarfe,
4. bereite Pflichtquests und vollständige Challenger-Cups ohne Renderbedarf,
5. fehlende Challenger für blockierende ChampionSlots,
6. bestätigte Repair- und Stability-Aufträge,
7. regulärer Character- und Content-Supply,
8. Coverage-, Exploration-, Effizienz- und optionale Prestigeaufträge,
9. Dataset-, Image-Analysis- und LoRA-Hintergrundarbeit ohne aktuelles Gate.

Die Priorität darf keine Figur oder Content-Stufe verhungern lassen. Ein
versionierter Fairnesscursor und maximale Burstgrößen begrenzen die Dominanz
einer Campaign, eines Characters, eines Scopes oder eines Providers.

Für den heutigen Worker wird diese Ordnung in fünf ausführbare Klassen
abgebildet: laufende Providerarbeit und Reconciliation; spielrelevante
Follow-up-, Prompt- und Generierungsvorbereitung; zwingend benötigte Analyse;
allgemeine Runtime-Bildanalyse; historische Analyse und Index-Rebuild. Der
30-Sekunden-Analysesweep darf offene Enrollments entdecken und deduplizierte
Jobs anlegen, aber dabei noch keinen `WorkIntent`, keine Decision und keine
schwere Lease reservieren. Diese Bindung entsteht erst, nachdem der Job die
Worker-Auswahl gewonnen hat. Läuft ein VLM-Kindprozess bereits, wird er bis zum
Unload gepollt; danach gewinnt wartende spielrelevante Arbeit vor dem nächsten
allgemeinen Analysebild. Eine aktive Spieler-Session sperrt ausschließlich den
Start einer zweiten Session derselben Campaign und niemals diese
Hintergrundvorbereitung.

Schema 50 legt diese fachlichen Prioritäten nicht mehr in einen einzigen
universellen Ausführungsloop. Jede Lane kann unabhängig claimen, warten und
fortschreiten. Reconciliation und stabiles Output-Ingest dürfen deshalb neben
CPU-seitiger Coordinator-Arbeit laufen. Die globale Guardian-Matrix bleibt davon
getrennt: `gpu_lm_studio_llm`, `gpu_comfyui`, `gpu_docker_vlm` und
`gpu_docker_image_embedding` sind zunächst gegenseitig exklusiv. CPU-only
Textembedding darf nur dann mit ComfyUI überlappen, wenn genau diese Modell-,
Kontext-, Offload- und Hardwarekombination einen realen, immutable
Overlap-Bake-off bestanden hat. Ohne diesen Beleg bleibt sie serialisiert.

Ein aus vorhandenen Bildern gebauter Cup kann trotz hoher fachlicher Priorität
ohne GPU-Slot vorbereitet werden. Fachliche Priorität und Ressourcenklasse sind
getrennte Dimensionen.

## ChampionSlot-bezogene Planung

Für jeden aktiven Slot projiziert der Guardian getrennte Bedarfe:

- fehlender semantischer Baseline-/Comparison-Contract,
- sekundär qualifizierbare bestehende Bilder,
- fehlende rosterfähige Challenger bis 16,
- bereiter Cup oder offenes Title Match,
- benötigte gepaarte oder unabhängige Stability-Seeds,
- aktiver Repair-Cluster,
- stale Champion- oder Slotrevision,
- fehlende Assetableitung oder QA,
- sowie optionaler Character-Championship-Bedarf.

Bestehende Bilder werden vor neuer Generierung auf zulässige sekundäre
Qualifikation geprüft. Eine Maschine darf diese Qualifikation nur vorschlagen;
wo die neue Fragestellung Player-Evidence verlangt, erzeugt der Guardian eine
Reviewaufgabe statt eines positiven Ergebnisses.

SchoolYear-, Class-, Relationship- und Ensemble-Bedarfe werden nach dem Vertrag
in
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md)
als WorkIntents materialisiert. Der Guardian darf dabei weder verborgene
Storyinformationen freigeben noch einen gemeinsamen Slot künstlich einem
einzelnen Character zuschlagen.

## KI- und Provider-Schutzgrenzen

- Ein LLM darf WorkIntents, Promptstrukturen oder Recovery-Hypothesen
  vorschlagen, aber weder Auftrag, Champion, Credit, Canon, Readiness noch
  Retry selbst autorisieren.
- Ein Judge darf eine Proposal Revision akzeptieren oder Revision verlangen,
  aber keine Generation direkt starten.
- ComfyUI führt nur ein vollständig persistiertes, validiertes Recipe aus.
- Image Analysis verarbeitet nur durch die Anwendung autorisierte Bilder und
  bleibt diagnostisch.
- Asset Processing darf aus einem gültigen Quellbild versionierte Ableitungen
  erzeugen, aber kein fachlich gescheitertes Bild zum Champion erklären.
- Kein Provider darf nach Abschluss selbstständig den nächsten Provider
  aufrufen. Der Resultat-Ingest löst stattdessen eine neue Guardian-Entscheidung
  aus.
- Unbekannte Modell-Lineage, fehlende Lizenz-/Hashdaten, Content-Policy-Konflikt
  oder ungeklärte Revisionsbindung blockieren vor Submission.

### Embedding-, Retrieval- und LLM-Schritte

`ImageEmbedding`, `TextEmbedding`, `Retrieval`, `ContextAssembly`, `LlmCall`
und eine daraus folgende `Generation` sind getrennte WorkIntent-Klassen. Keine
Autorisierung umfasst die ganze Kette. Der Resultat-Ingest eines Schritts löst
eine neue Guardian-Prüfung aus.

Im initialen Human-first-Pfad blockiert der Guardian Image-Embedding-Jobs für
ungesehene oder noch nicht vollständig bewertete Bilder. Der erste
scopegebundene Bootstrap benötigt ein kompatibles Favorite, eine scopekompatible
`APPROVED ChampionRevision` oder ausdrücklich vorhandenes kompatibles Legacy-
Referenzmaterial. Favorite und Champion sind als Referenzfreigabe gleichwertig;
ein Keep allein genügt nicht. Begründete negative Beobachtungen dürfen erst
danach ausschließlich ihre expliziten Diagnose- und Fehlercluster speisen.

Vor jedem Retrieval prüft der Guardian außerdem Embedding-Raum, Modell-, Index-,
Preprocessing-, Reference-Set- und Similarity-Policy-Revision. Vor einem
LLM-Call muss ein persistiertes, rollenreines `ContextPackManifest` vorliegen.
Der vollständige Vertrag steht in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md).

## Grenze zu unvollständigen Abläufen und Recovery

Vier Recovery-Arten bleiben fachlich getrennt:

| Recovery-Art | Beispiel | Autorität |
|---|---|---|
| Interaction Resume | begonnener Bildreview im gewählten Spielmodus, offener Cup, nicht abgeschlossene Conversation Session | zuständige persistente Session-State-Machine und Campaign Director |
| Machine Work Reconciliation | submitted ComfyUI-Job, abgelaufene Lease, vorhandener aber noch nicht ingestierter Output | Orchestration Guardian und zuständiger Provideradapter |
| Projection Repair | fehlende oder stale rebuildbare Read-/Monitorprojektion | deterministischer Rebuilder beziehungsweise globaler Guardian |
| Domain Recovery | `wrong_outfit`, Identity Drift, Alpha-Halo oder andere bewertete Bildabweichung | versionierte Recovery Policy und neuer kontrollierter Trial |

Eine Art darf nicht als Abkürzung für eine andere verwendet werden. Insbesondere
ist ein unvollständiger Review kein negativer Bildbefund, ein Provider-Timeout
keine Erlaubnis für ein neues Recipe und ein Projection Repair keine
Spielerentscheidung.

Verbindliche Resume-Regeln:

- Eine fortsetzbare aktive Quest-, Tournament-, Conversation-, Asset-QA- oder
  andere InteractionSession wird vor einer konkurrierenden neuen Hauptaktion
  projiziert.
- Der Guardian verändert ihren Cursor, ihre Decisions oder ihren Completion
  Contract nicht. Er darf nur benötigte unabhängige Maschinenarbeit
  reconciliieren beziehungsweise zulässigen Hintergrund-Supply fortsetzen.
- Vor einem Ersatzauftrag wird geprüft, ob bereits ein Intent, eine Lease, ein
  Providerjob, Provider-History oder ein Output für denselben Idempotency Scope
  existiert.
- Ein unvollständiger, aber gültiger Ablauf wird fortgesetzt; nur ein
  versionierter Cancel-, Supersede-, Retry- oder Quarantäneübergang beendet
  beziehungsweise ersetzt ihn.
- Reload, Prozessneustart und Provider-Reconnect müssen zum selben fachlichen
  Resume-Ziel führen.
- Recovery darf keinen ChampionSlot, Relationship-Kontext, Storyzeitpunkt oder
  Rules Snapshot still neu binden.

Die Einführung des gemeinsamen Guardian-Lifecycles erfolgt deshalb zuerst im
read-only Shadow Mode: Er berechnet Decisions und vergleicht sie mit den
bestehenden Director-/Supply-/Recovery-Entscheidungen, ohne Jobs zu starten.
Erst nach Replay-, No-duplicate- und Resume-Parität übernimmt er schrittweise die
Submission-Autorisierung. Eine laufende Optimierung der bestehenden
Incomplete-Flow-Recovery wird damit nicht ersetzt, sondern als vorgelagerter
Vertrag konsumiert.

## Work-Lifecycle

```text
proposed
→ eligible
→ authorized
→ leased
→ submitted
→ running
→ succeeded
→ ingested

proposed/eligible → blocked
authorized/leased → superseded
submitted/running → retryable_failed → eligible
submitted/running → terminal_failed | quarantined
```

Verbindliche Eigenschaften:

- Jede Submission ist über WorkIntent, Decision und Providerjob idempotent
  korrelierbar.
- Lease und Heartbeat sind zeitlich begrenzt; ihr Ablauf löscht keinen
  Providerjob und erzeugt keinen ungeprüften Doppel-Submit.
- Vor einem Retry wird zuerst Provider History beziehungsweise vorhandener
  Output reconciliiert.
- Nur vollständig erreichbare Queue und History dürfen einen fehlenden
  Korrelationsbeleg gegen die Quarantänegrenze zählen. Provider-Ausfall wartet
  ohne diesen Zähler zu verbrauchen.
- Retrybudgets sind pro Fehlerklasse begrenzt und wachsen nicht durch Neustart.
- Deterministische Fehler gehen ohne Wiederholung in `terminal_failed` oder eine
  explizite Recovery Route.
- Vor Lease-Freigabe wird ein terminaler Providerstatus idempotent in den
  betroffenen Draft beziehungsweise Calibration-Eintrag und dessen Aggregat
  projiziert.
- Widersprüchliche Provenienz, unbekannte Outputs und wiederholte transiente
  Fehler gehen in Quarantäne und blockieren nur ihren Scope.
- Eine andere Campaign oder ein anderer Character darf weiterarbeiten, sofern
  keine globale Capability betroffen ist.

### Schema-46-Modell-Lifecycle und reale Providerbelegung

Für schwere lokale Modelle genügt eine Datenbanklease nicht. Vor jedem Wechsel
zu `gpu_docker_vlm` oder `gpu_docker_image_embedding` reconciliiert der Guardian
zusätzlich die tatsächliche ComfyUI-Queue, geladene LM-Studio-Instanzen, einen
laufenden Docker-Kindprozess sowie VRAM, RAM und Disk. ComfyUI wird nur bei
leerer Queue über seinen nativen `/free`-Vertrag freigegeben. Eine aktive
Recovery, fremde LM-Studio-Instanz, fehlende Providerantwort oder nicht
zurückgekehrte Ressourcengrundlinie erzeugt `resource_blocked`.

Die VRAM-Buchhaltung ist providerbezogen. Für Docker-VLM, Docker-Image-
Embeddings und LM Studio bleibt der globale `nvidia-smi`-Snapshot maßgeblich.
Für `gpu_comfyui` ist dagegen ComfyUIs `/system_stats`-Wert `vram_free` die
autoritative Allokationssicht. Unter Windows/WDDM enthält der globale
`nvidia-smi`-Verbrauch auch Desktop-, Browser- und GUI-Reservierungen und darf
deshalb nicht fälschlich als zusätzlich zum vollständigen Comfy-Arbeitsbudget
erforderlicher Speicher verrechnet werden. Der WorkIntent kennzeichnet diesen
Vertrag mit `vram_accounting=comfy_allocatable`; der Guardian verlangt dort
weiterhin das erwartete Arbeitsbudget plus 1.536 MiB Startreserve. Eine
fehlende oder zu kleine Provider-Messung blockiert fail-closed. Exklusive
Heavy-GPU-Lease, reale Queue-Backpressure, RAM-/Diskreserve und laufende
Temperatur-/Outputüberwachung werden dadurch nicht gelockert.

Nach einem abgeschlossenen logischen Comfy-Batch dürfen Torch-Gewichte noch im
Provider resident sein. Unterschreitet diese Idle-Residency das Startbudget des
nächsten Batches, prüft der Guardian zuerst die reale Queue. Nur bei exakt
null laufenden und null wartenden Prompts ruft er einmal ComfyUIs `/free` mit
`unload_models=true` und `free_memory=true` auf, misst `/system_stats` erneut
und entscheidet danach. Eine belegte Queue wird niemals für einen neuen Batch
entladen; fehlende Freigabe oder weiterhin zu kleine Reserve bleibt
`resource_blocked`.

Genauso wird ein ausschließlich durch residente Comfy-Gewichte
blockierter LM-/Docker-Vordergrundjob nicht dauerhaft zurückgestellt: Der
Guardian persistiert einen deduplizierten Handoff-Auftrag, ausschließlich die
Comfy-Lane prüft die Queue und führt `/free` aus, danach wird der unveränderte
Vordergrundjob erneut zugelassen. Die anfordernde Lane greift nie direkt auf
den fremden Provider zu.

Jeder Dockerjob erhält einen exklusiven Ein-Job-Kindprozess. Load und Inferenz
finden nicht im FastAPI-Elternprozess statt; das Ende des Kindprozesses ist die
Unload-Grenze. Ein atomar reservierter Prozesslock verhindert zwei gleichzeitig
akzeptierte schwere Jobs. Die HMAC-signierte Worker-Autorisierung bindet
WorkIntent, Decision, Lease, Provider-Key, Modellartefakt, Execution Profile und
Source-Hash. Direkte lokale REST-Aufrufe ohne diese Bindung sind ungültig.

Beim VLM startet dieser Kindprozess zusätzlich genau einen lokalen
`llama-server`, wartet begrenzt auf `/health`, sendet eine Bildanfrage und
beendet den nativen Prozess in jedem Erfolgs- und Fehlerpfad. Der Lifecycle
bindet Containerdigest, Binary-, Modell- und mmproj-Hash, native PID, Health,
aufgelöste sichere Startparameter, getrennte Inferenzzeit, Exit und
Post-Unload-Baseline. Repository, Revision, Lineage, Lizenz, Baumhash,
Dateigrößen, lokale Datei- und Xet-Hashes werden zusätzlich im Adapter
fail-closed gegen den gepinnten Vertrag geprüft. Ein HTTP-Fehler speichert weder
Providerbody noch Prompt oder Bild; er persistiert eine allowlistbasierte
Fehlerklasse, den Response-SHA-256 und harmlose Provider-Typ-/Codefelder.
Ressourcen-Peaks werden auch bei fehlgeschlagener Inferenz übernommen.

LM Studio verwendet reproduzierbare `lms load`-Profile. Text Embeddings laufen
CPU-only mit 8192 Kontexttokens und Providerparallelität 4. Der Guardian
autorisiert weiterhin nur einen Text-Embedding-WorkIntent; innerhalb dieses
Intents werden tokenbudgetierte, typisierte Seiten und die einzelnen Raumqueries
kontrolliert verarbeitet. Slot-/Aspect-Aufrufe laufen mit 50 Prozent GPU-Offload,
4096 Kontexttokens und Parallelität 1; der gemeinsame kompakte v10-Batch-Judge
verwendet das qualifizierte 8192-Profil mit höchstens 7200 Input- und 512
Outputtokens. Der Load-Receipt wird auf eine konkrete `instance_id` aufgelöst;
nur diese im Prozess bekannte oder im Chronicle-Lifecycle exakt persistierte ID
darf entladen werden. Modellname, Repository-ID oder eine fremde Instanz sind
kein zulässiges Unload-Ziel.

`model_lifecycle_runs`, immutable `model_lifecycle_events` und
`model_resource_samples` protokollieren Preflight, aufgelöste Konfiguration,
Load, Inferenz, Latenz, Peakwerte, Temperatur, Kindprozess-Exit beziehungsweise
Instanz-Unload und Post-Unload-Reserve. Die Worker-JSONL-Spur wird über den
Shared Spool, SHA-256 und lückenlose Sequenz übernommen. Technische Fehler
enthalten zusätzlich Exception-Typ und einen begrenzten Stacktrace, aber keine
Rohbilder, Rohprompts oder Modellantworten. Fehlende oder
abweichende Spuren, ungültige Modellresultate und Unloadfehler blockieren die
betroffene Stage fail-closed.

## Monitoring-Projektion

Die Systemüberwachung liefert mindestens:

- aktuellen High-Watermark und letzten erfolgreichen Sweep,
- jede Lane-Runtime mit Lane, Build-ID, PID, Epoch, Heartbeat und Ablaufzeit,
- Lane-Backlogs mit queued/running/waiting, ältestem Job und Wake-up-Grund,
- offene WorkIntents nach Klasse, Scope, Alter und Priorität,
- autorisierte, geleaste, laufende, stale und quarantinierte Jobs,
- Providerfähigkeit pro konkreter Funktion statt nur Online/Offline,
- Queue-, VRAM-, Storage- und Backpressure-Zustand,
- Retrybudget und letzte Fehlerklasse,
- Slotfortschritt, Pooldefizit, Stability- und Assetblocker,
- BatchDiversityPlan-Revision, vier Slot-/Recipe-Zustände, erwartete sichtbare
  Deltas und den letzten `BatchDiversityObservation`-Status,
- Human-Review-Cutoff, Image-Analysis-Bootstrap, Index- und
  Referenzset-Freshness sowie Similarity-Policy und Abstention,
- Fairness-/Starvation-Alter pro Character und Scope,
- verwaiste Outputs, fehlende Ingests und divergierende Projektionen,
- sowie für jede Blockade die nächste erwartete Wake-up-Bedingung.

Die normale UI zeigt nur verständliche Zustände wie „wird vorbereitet“,
„wartet auf vier weitere Challenger“, „Dienst nicht bereit“ oder „erneuter
Versuch nötig“. Vollständige Work-, Policy-, Provider- und Revisionsdetails
liegen in einer read-only Advanced-Diagnose.

Monitoring besitzt keine Mutationsautorität. Manuelle Advanced-Aktionen dürfen
höchstens einen autorisierten Reconcile-, Retry-, Cancel- oder Quarantänepfad
anfordern und durchlaufen dieselben Serverprüfungen.

## Persistenz-Mindestmodell

Der Zielvertrag benötigt mindestens folgende Entitäten oder gleichwertige
persistente Verträge:

- `work_intents`,
- `work_intent_dependencies`,
- `orchestration_policy_revisions` und Policy Head,
- `next_work_decisions`,
- `work_leases` und Heartbeats,
- `worker_jobs` mit immutable Execution-Lane, Claim-Token,
  Lane-Runtime-Key/-Epoch und Claim-Heartbeat,
- lanegebundene `worker_runtime_leases`,
- `provider_job_bindings`,
- `batch_diversity_plans`, `batch_diversity_slots` und rebuildbare
  `batch_diversity_observations`,
- `work_attempts`,
- `work_blockers`,
- `reconciliation_runs` mit High-Watermark,
- `quarantine_entries`,
- sowie rebuildbare `orchestration_monitor_projections`.

Raw Providerstatus darf Projektionen speisen, ersetzt aber keine persistierte
fachliche Zustandsmaschine.

## Phasengerechter Ressourcenschutz

Die Ressourcenpolicy `phase-aware-memory-pressure-v1` behandelt 4096 MiB RAM
und 1536 MiB VRAM als Planungsreserven, nicht als nachträgliche Gültigkeitsprüfung
einer Modellantwort. Vor Laden/Profilwechsel werden freie Ressourcen, reale
Providerbelegung und zusätzlicher Profilbedarf geprüft. Die Planungsreserve ist
dabei kein zweiter Working Set: Passt die profilgebundene Startschätzung selbst
und liegt kein OS-Speicherdruck vor, wird eine unterschrittene Restreserve als
Warnung protokolliert. Ein geladenes Modell
wird zwischen Einzelcalls nicht erneut als zusätzlicher Gewichtsbedarf berechnet.

Nach dem Laden und während Inferenz erzeugt eine bloße Reserveunterschreitung
eine protokollierte Warnung. Eine valide Antwort und ihr Receipt bleiben gültig.
Das zusätzliche Windows-Low-Memory-Signal pausiert Folgearbeit; der aktuelle
Call wird kontrolliert abgeschlossen und die eigene Instanz entladen. Fehlende
Messbarkeit blockiert neue schwere Arbeit, entwertet aber kein erhaltenes
Resultat. Tatsächliches Provider-OOM, unbekannte Ergebnisse und nicht bestätigtes
Unload bleiben getrennte harte Fehler beziehungsweise Reconciliation-Blocker.

Messungen enthalten Phase, Zeitpunkt, Policy-/Profilbindung, RAM, VRAM und
OS-Signal. Sekündliche Stichprobenmaxima werden nicht als lückenloser Peak
bezeichnet. Nach bestätigtem Unload ist eine kleine Baseline-Abweichung kein
Fehler; die nächste Ladung erhält ihre eigene aktuelle Startprüfung.
Es werden weder fremde Prozesse beendet noch pauschale neue Toleranzgrenzen
eingeführt. Ein Ressourcen-Wake-up setzt dieselbe autorisierte Ausführung fort.
Beim Wechsel von idle ComfyUI zu LM Studio darf der Guardian nach bestätigter
leerer Queue den residenten Comfy-Modellcache kontrolliert freigeben. Bei
laufenden oder wartenden Prompts bleibt `/free` gesperrt.

Der rollierende Live-Test kann als persistenter `campaign_scope`-Pilot begrenzt
werden: dieselbe Campaign und derselbe Content Scope, einschließlich zukünftiger
Review-/Director-Folgeattempts. Eine feste Start-Attempt-ID ist dabei Provenienz,
keine Beschränkung auf eine Runde. Jobs außerhalb des Bereichs warten ohne
Retryverbrauch; der gemeinsame Supply-Planner erzeugt dort keine neuen Karten.
Auch innerhalb des Bereichs gelten Human-first, Bedarfsermittlung, Guardian und
exklusive schwere GPU-Arbeit unverändert. Ein qualifiziertes Execution Profile
wird für neue Eingangsmanifeste gebunden; laufende Manifeste bleiben unverändert.

Für den Test über alle spielbaren Quests erweitert `active_content_policy` diesen
Vertrag auf alle aktiven Campaigns und alle aktuell freigeschalteten Content-
Scopes. Der zum Cutover gültige Settings-/Campaign-Snapshot wird unveränderlich
protokolliert; jede neue Autorisierung prüft zusätzlich den aktuellen Zustand.
Die Erweiterung verändert nicht die Ressourcenparallelität: Der Guardian lässt
weiterhin genau eine schwere GPU-Klasse zu und rotiert fair zwischen Campaigns
und Scopes. `pilot_scope_status` zeigt Freigabe-Snapshot, aktuellen Scope und
Settings-Drift getrennt an.

## Recovery und Deadlock-Schutz

Der Guardian muss zwischen vier Fällen unterscheiden:

1. **wartend:** Eine externe oder Spieleraktion ist erwartbar; kein Retry.
2. **temporär blockiert:** Capability oder Ressource fehlt; Wake-up bei Änderung.
3. **recoverable:** Eine versionierte Retry- oder Recovery Route ist zulässig.
4. **fachlich unmöglich:** Contract, Content, Provenienz oder Dependency kann
   nicht erfüllt werden; sichtbarer Blocker statt Endlosschleife.

Für M6-Attempts wird daraus eine verbindliche zustandsabhängige Ausführung:

- `waiting` mit weiterhin erreichbarer laufender Arbeit setzt denselben Attempt
  fort;
- vom Provider bereits angenommene Arbeit wird ausschließlich über ihre
  persistierte Provider-ID reattached und nie neu abgesendet;
- ein terminaler unmaterialisierter Pre-Provider-Attempt ohne Session, Review,
  Credit oder Providerbilder wird append-only superseded und erhält genau einen
  deduplizierten Nachfolger;
- Focus-/Diff-Fehler und semantische Erschöpfung schließen Route und
  Proposal-Signatur für denselben Evidence-Head aus; rein technische Fehler
  dürfen einen weiterhin gültigen eingefrorenen Vertrag wiederverwenden.

Ein terminaler Child-Job ist niemals eine aktive Vorbereitung. Die öffentliche
Slotprojektion wird aus dem wirksamen Stage-Zustand und nicht aus einem älteren
erfolgreichen Parentjob abgeleitet.

Ein Image-Providerjob mit abgelaufenem Lease wird vor jeder Fortsetzung gegen
StageAttempt, WorkIntent und den exakten Provider-Key reconciliiert. Nur diese
identische Arbeit erhält eine neue Decision und Lease. Bereits laufende oder
fertige Kindprozesse werden reattached und gepollt; vorbereitete, nie gestartete
Jobs bleiben versuchsfrei. `ImageProviderLeaseReattached` hält alte und neue
Bindung nachvollziehbar fest. Die neue Bindung wird zugleich im offenen
Workerjob persistiert; alle weiteren Polls erneuern diese Lease per Heartbeat und
erzeugen nicht periodisch weitere Reattach-Revisionen für denselben Kindprozess.

Ein Deadlock-Check sucht unter anderem nach zyklischen Dependencies,
unerreichbaren ChampionSlot-Voraussetzungen, dauerhaft leerem Candidate Source,
gegenseitig wartenden Providerjobs und Gates ohne zulässigen Progressionspfad.
Er darf keine Requirements abschwächen. Er liefert Diagnose und den nächstmöglichen
autorisierten Reparaturpfad.

## Abgrenzung zum implementierten Foundation-Stand

Der Foundation-Stand besitzt Campaign Director, globalen Guardian, persistierte
Stage-Handoffs, fünf getrennte Worker-Lanes, Providerjobs, Backpressure und
Monitorprojektionen. Schema 50, Lane-Registry, Seiteneffekt-Fencing und der
Fünf-Prozess-Fullstack sind automatisiert verifiziert. Noch offen sind reale
Lane-Restarts, die profilgebundene Overlap-Qualifikation und die Live-Abnahme.
Der aktuelle Status bleibt unter `CR-MVP-048` und `GAP-033` sichtbar.

## Testbare Invarianten

1. Kein LLM, Worker, Adapter oder Frontend autorisiert seinen Folgeauftrag.
2. Jede maschinelle Arbeit referenziert einen persistierten WorkIntent und eine
   gültige NextWorkDecision.
3. Dieselbe Decision erzeugt auch nach Restart höchstens einen wirksamen
   Providerjob.
4. Vor Submission werden Zielrevision und harte Gates erneut geprüft.
5. Ein superseded Intent kann keinen fachlichen Resultatübergang schreiben.
6. Provider-Timeout erzeugt keinen Doppel-Submit ohne History-Reconciliation.
7. Retrybudget und Quarantäne überleben Prozessneustarts.
8. Ein Fehler in einem Character-Scope blockiert keine unabhängigen Scopes.
9. Backpressure verändert keine fachliche Priorität oder Evidence.
10. Ein Sweep ohne neue Facts erzeugt keine identischen Folgejobs oder Events.
11. Sekundäre Bildqualifikation erzeugt bei neuer Frage eine Reviewaufgabe und
    keine erfundene positive Observation.
12. Ein fehlender Challenger darf gezielte Generierung, bestehende
    Requalifikation oder eine sichtbare Blockade auslösen, aber keinen leeren
    Cup.
13. Monitoring ist vollständig read-only.
14. Deterministischer Replay bis zum selben High-Watermark erzeugt dieselben
    offenen Bedarfe, Blocker und Prioritäten.
15. Jeder blockierte Zustand nennt eine Wake-up-Bedingung oder einen terminalen
    fachlichen Grund.
16. Eine fortsetzbare InteractionSession bleibt nach Guardian-Sweep und Restart
    dieselbe primäre Hauptaktion.
17. Shadow- und aktive Guardian-Decision stimmen vor dem Cutover für dieselben
    Facts und Policy-Revisionen überein.
18. Jede Lane claimt nur registrierte eigene Jobs; ein unbekannter Typ erhält
    keine implizite Coordinator-Autorität.
19. Ein stale Lane-Worker kann nach externem I/O weder Providerstatus noch
    Recipe, Lease oder Bildbindung schreiben.
20. Vier eindeutig ingestierte Outputs öffnen die Quest; optionale Analyse
    darf die Ready-Karte nicht wieder sperren.
21. Zwei technische Lernzyklen sind ein Runtimebeleg und setzen
    `M6_LEARNING_LOOP_PROVEN` nicht automatisch.

## Edge-getriggerte Recovery und Vektorreuse ab Schema 55

Supply-Reconcile, Catalog-Recovery und Projection-Rebuild reagieren auf eine
neue persistierte Zustandsrevision oder auf einen einmaligen Startup-
High-Watermark. Ein Watchdog prüft ausschließlich read-only. Er darf einen
terminalen Heavy-Job nicht wiederbeleben und ohne neue Facts weder einen
identischen Successor noch ein identisches Chronicle Event erzeugen.

Vor einem Text-Embedding-Auftrag prüft der Coordinator die bestehende
Dokumentbindung aus Source, Space, Modell, Preprocessing und Content-Hash.
Vorhandene gültige Vektoren werden wiederverwendet; Reconcile und Campaign-
Wechsel erzeugen keinen erneuten Providercall. Queryvektoren bleiben davon
getrennt und werden niemals Dokumentindexmitglieder.

Der aktive `m6-slotwise-v10`-Judge erhält die gemeinsame Baseline einmal und je
Arm nur Alias und autorisierten Diff. Token-Preflight, Providercall und
persistiertes Resultat bleiben lane- und epochgefencet. Eine definitive
Providerablehnung ist ein bekanntes Ergebnis; nur ein Transportabbruch ohne
Providerbeleg wird reconciliert. Die Live-Verifikation des vollständigen
Refills ist weiterhin ausstehend.
