> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/rolling-m6-learning-loop.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Rollierender M6-Lernloop

Stand: 15. September 2026

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: freigegebener rollierender Lernvertrag; präzisiert PM-090, DEC-057 und die früheren Recovery-Verträge gemäß DEC-064

Schema-48-Präzisierung: Jede neue Planung darf neben vollständigen
Promptzusammensetzungen einen isolierten `prompt_atom`- oder
`prompt_atom_weight`-Versuch wählen. Atom-Trials ändern pro Challenger exakt ein
Atom durch Add, Remove oder Replace; Weight-Trials binden exakt ein vorhandenes
Recipe-Atom und verändern nur dessen Gewicht. Der Compiler erzeugt Klammerform,
Gewicht, Recipe und Seed. Eine akzeptierte Mutation materialisiert eine
immutable Child-ComponentVersion mit Parent, exaktem Diff, Hypothese und
`influence_refs`.

Die versionierte WeightPolicy verwendet bei Legacy-only beziehungsweise
niedriger frischer Confidence Schritte von 0,20, bei mittlerer 0,10 und bei
hoher 0,05 innerhalb 0,7 bis 1,8. Vier eindeutige Werte werden an Grenzen
deterministisch verschoben. Die frühere Skalierung aller positiven Atome ist
für neue Versuche unzulässig.

Schema 55 und `m6-slotwise-v10` verallgemeinern diesen Vertrag ohne zweiten
Promptgraphen. Eine neue Component-Version darf nur innerhalb eines zuvor
persistierten und akzeptierten `TypedMutationCorridor` entstehen. Der Corridor
bindet Parent, Rolle, Character-/Campaign-/Scope-Kontext, CompositionUse,
Recipe, konkrete Human-Evidence, Preserve-Gruppen, Operation und erwarteten
Diff. Er erlaubt genau `add`, `remove`, `replace`, `reweight` oder
`replace_group` für genau eine Mutationseinheit. Außerhalb dieses Korridors
bleiben Component, Canon-, Safety-, Scope- und sonstige Locks unverändert.

## Ein Loop, unterschiedliche Versuchsziele

`Human Review → Knowledge-Revision → Lernentscheidung → Kandidaten/Retrieval → ContextPack → Prompt Machine/Judge → Compiler/DiversityPlan → Guardian → Generierung → 4/4 Ready → Human Review`

Diese Kette ist vollständig, sobald die bewertungsgetriebene Prompt-/Recipe-
Änderung sichtbar geworden, neu gerendert und erneut bewertet worden ist. Sie
enthält keine VN-Asset-Produktion: `AssetSourceSelection`, Freistellung,
Matting, Normalisierung, Asset-QA, `DerivedAssetImage` und `AssetVersion`
beginnen erst nach `M6_LEARNING_LOOP_PROVEN` in Chronicle Slice 3. Keep,
Favorite und Champion bezeichnen hier ausschließlich Zustände des Quellbilds.

Der Reviewabschluss schreibt die Folgeplanung zusammen mit der Domainmutation
in die persistente Outbox. Der Browser muss dafür weder geöffnet bleiben noch
pollend Fortschritt erzeugen. Ready-Quests bleiben während Retrieval, Prompting,
Generierung und Analyse spielbar. Ein API-Neustart unterbricht den Worker nicht;
ein Worker-Neustart verändert keine offene QuestSession und übernimmt Arbeit nur
über Claim/Fencing und Provider-Reconciliation. Optionale VLM-Beschreibung und
Image-Embeddings folgen nach Output-Ingest in einer eigenen Analyse-Lane. Sie
dürfen die nach vier validierten Bildern spielbereite Karte nicht zurückstufen;
nur ein ausdrücklich analysegebundener Modus besitzt ein eigenes Required-
Analysis-Gate.

Schema 50 führte die persistierte Stage-Kette über fünf voneinander unabhängig
claimende Lanes ein. Die aktuelle Runtime-Autorität ist Schema 58; sie erhält
diese Lane-Aufteilung und ergänzt die kurze Spielercommit-, Projektions- und
Materialisierungsgrenze:

```text
coordinator:    Freeze → Retrieval/Context → Compiler → 4/4-Publish
lm_studio:      Embeddingseiten → Slotvorschläge → Batch-Judge
comfyui:        Submit[4] → Poll/History → Output-Ingest[4]
image_analysis: optionale Observation[4] → optionale Embeddings[4]
maintenance:    Sweeps und Rebuilds ohne kreative oder Providerautorität
```

Der Viererbatch bleibt als eingefrorener ComparisonContext und atomare
Veröffentlichungsgrenze zusammengehörig. Er ist keine monolithische
Ausführungseinheit: Ein langer VLM-Call darf weder Coordinator-Arbeit noch
ComfyUI-Polling blockieren. Jede Stage besitzt einen aus Eingangsmanifest,
Ausführungsrevision, Stage und Slot beziehungsweise Seite gebildeten
Dedupe-Key. Stage-Resultat und nächste Outboxarbeit werden atomar geschrieben.
Abgeschlossene Slotcalls und ingestierte Outputs werden nach Restart nicht
erneut ausgeführt.

Dieser technische Kreislauf ist nicht identisch mit dem sichtbaren
Spielerablauf. Beide Projektionen laufen über dieselbe Quest- und Bildidentität:

```text
Spieler: Kartenauftrag → Bilder ansehen → bewerten und begründen
         → Keep-/Favorite-Bildkarte → Challenger/Titel → nächste Aufgabe

Backend: Frage/Scope → ExperimentContract → Recipe/Seed/Modell → Roh-Evidence
         → achsenspezifische Knowledge-Revision → nächste kontrollierte Planung
```

Die Spielerprojektion darf technische Schritte zusammenfassen oder in Advanced
verschieben. Sie darf dabei keine Prompt-, Recipe-, Seed-, Modell-, Focus-,
Achsen-, Quellen-, Confidence-, Unsicherheits-, Bias- oder Revisionsinformation
verwerfen. Umgekehrt darf der Planner aus Kartentitel oder lokalisierter Copy
keinen technischen Vertrag ableiten.

### Was gesammelt wird und wodurch es Autorität erhält

| Zeitpunkt | Zu speichernde Information | Erhebungsweg und Autorität |
|---|---|---|
| Vor der Generation | Character/Portfolio, semantischer Auftrag, Focus, Primary Question, Expected Composition, Locked/Varied Axes, Evidence Scope, Content Scope, GameMode und Recovery Routes | Director und deterministischer Planner frieren den versionierten QuestExperimentContract ein. Die UI bestätigt ihn nicht nachträglich. |
| Beim Kompilieren und Rendern | Component-/Prompt-/Weight-Versionen, vollständiges Recipe, Workflow, Checkpoint, LoRA-Stack, Sampler, Scheduler, Steps, CFG, Denoise, Seed, Provider- und Dateihashes | Compiler, Submission und Output-Ingest schreiben automatische Provenienz. Sie ist keine Spielerpräferenz. |
| Nach Output-Ingest | sichtbare VLM-Fakten, Unsicherheit, Reason-Vorschläge und Batch-Diversitätsbefund | Image Worker und deterministische Validatoren schreiben ausschließlich Maschinenbeobachtungen mit Modell-/Schema-Provenienz. |
| Im Beschreibungstest | DescriptionRevision, Quell- und Gegenbild, Eligibility-Snapshot, Schwierigkeitskorridor, Auswahlpolicy/Seed, Similarity-Ränge und -Abstände, Links-/Rechtsbelegung, Spielerwahl, Dauer, Inputklasse, Abbruch und Revision | Die explizite Zuordnung erzeugt ausschließlich DescriptionMatchEvidence. Eine einzelne Paarung ist keine absolute Textbestätigung und keine Bildpräferenz. |
| Im Trial | Favorite/Keep/Reject, Primary/Secondary Reasons sowie modeabhängiges Ranking, Paar- oder Setsignal | Nur die explizite Spielerhandlung erzeugt Human Evidence. Position, Reihenfolge, Eingabeklasse, Dauer, Undo und Abbruch bleiben als Bias-/Qualitätsmerkmale erhalten. |
| Nach Abschluss | positive/negative Masse, Beobachtungs- und unabhängige Quellenzahl, Verhältnis, Confidence, Unsicherheit, scoped Credit, Fehlercluster und nächste offene Frage | Deterministische rebuildbare Projektionen aus unveränderten Rohereignissen; keine LLM-Autorität und kein kompensierender globaler Qualitätsscore. |
| Über Folgerunden | Wiederholbarkeit, Drift, Transfer, Coverage und kausale Wirkung einzelner Achsen | Nur kompatible Kontexte und der jeweils erforderliche Independent-Seed-, gepaarte Control-/Challenger- oder isolierte Variationsvertrag dürfen zusammengeführt werden. |
| Bei späterer Assetverwendung, außerhalb M6 | Quellwahl, Crop/Mask/Alpha/Normalisierung, Processing-Revision, QA-Befund und Freigabe | Erst Chronicle Slice 3 erzeugt getrennte AssetSourceSelection, AssetAttempts und AssetVersionen; keine Mutation von Bildkarte, Disposition oder Championtitel. |

Die ebenfalls post-M6 mögliche
[`Kartenkunst-Komposition`](card-art-composition-and-rendering.md) ist von dieser
VN-Assetverwendung getrennt. Sie verschiebt und skaliert ein bereits
berechtigtes Bild ausschließlich hinter einem Spielkartenframe, erzeugt keine
AssetSourceSelection und schreibt keine M6-Evidence. Historische Kandidaten
dürfen dafür nur über den expliziten, nicht proof-fähigen
`development_import` bereitgestellt werden.

Für aktuelle M6-Quests ist `primary_subject=character` ein vom Experiment Focus
getrennter Lock. Deshalb bleiben auch Scene-, Outfit-, Pose- und Lichtfragen im
Character-Portraitformat. Das horizontale Scene-/CG-Profil gehört ausschließlich
zu einem späteren expliziten Non-Character-Scene-Vertrag. Im Review bezeichnet
der Focus die besonders untersuchte Achse, nicht den Umfang des Qualitätsurteils:
Favorite, Keep oder Reject gelten für das Gesamtbild; ausgewählte positive und
negative Reasons lokalisieren die Teilbefunde.

Raw Events bleiben append-only. Neue Character-, Canon-, Scope-, Prompt-,
Recipe-, Modell-, Workflow-, Asset- oder Policyrevisionen erhalten neue
Projektionen statt stiller Überschreibung. Dasselbe Bild darf in verschiedenen
kompatiblen Fragen unterschiedliche Evidence liefern; eine Beobachtung wird
nicht allein durch die mehrfache Anzeige der Karte vervielfacht.

Seit `question-driven-m6-v2` bindet jede Frage vor Kandidatenauswahl und
Generierung zusätzlich einen typisierten `experiment_kind`. `focus_kind`
beschreibt weiterhin das fachliche Erkenntnisziel, darf aber die tatsächlich
getestete Achse nicht ersetzen oder über Hilfszuordnungen verfälschen. Es gelten
folgende Versuchsverträge:

| `experiment_kind` | konstant | variiert | Prompt Machine |
|---|---|---|---|
| `seed_stability` | vollständiges Recipe und Renderprofil | vier unabhängige Seeds | nein |
| `sampler` | Prompt, Scheduler, Parameter und gepaarter Seed | Control plus drei Sampler | nein |
| `scheduler` | Prompt, Sampler, Parameter und gepaarter Seed | Control plus drei Scheduler | nein |
| `parameter_steps` | Prompt, sonstiges Renderprofil und gepaarter Seed | deterministisches Steps-Fenster | nein |
| `parameter_cfg` | Prompt, sonstiges Renderprofil und gepaarter Seed | deterministisches CFG-Fenster | nein |
| `parameter_denoise` | Prompt, sonstiges Renderprofil und gepaarter Seed | deterministisches Denoise-Fenster | nein |
| `prompt_atom` | Control-Recipe, Renderprofil und gepaarter Seed | pro Challenger exakt ein Add/Remove/Replace-Atom | drei Einzelvorschläge plus Judge |
| `prompt_composition` | Renderprofil und gepaarter Seed | vier Komponenten-/Blockzusammensetzungen | kein Modellcall für eingefrorene, vollständig validierte Candidates; Prompt Machine/Judge nur bei autorisierter semantischer Mutation |
| `prompt_atom_weight` | identisches Zielatom, alle übrigen Atome, Renderprofil und gepaarter Seed | vier deterministische Gewichte innerhalb `0.7–1.8` | nein |
| `prompt_weight` | nur eingefrorene ältere Verträge | historische Ganzprompt-Gewichtsvariation | nein; keine neue Planung |
| `semantic_exploration` | Canon-, Scope-, Rollen- und Kompatibilitätslocks | bis zu drei deklarierte semantische Achsen; unabhängige Seeds zulässig | kein Modellcall für eingefrorene, vollständig validierte Candidates; Prompt Machine/Judge nur bei autorisierter semantischer Mutation |

Der achsenspezifische Dublettenvertrag ist Teil derselben Revision. Gleiche
sichtbare Komposition ist in Seed-, Sampler-, Scheduler-, Parameter- und
Weight-Fragen ausdrücklich vergleichbar und daher erlaubt; dort müssen die
technischen beziehungsweise Seed-Ausführungen verschieden sein. In Prompt- und
Semantic-Fragen sind dagegen gleiche sichtbare Endkompositionen unzulässig.
Prompt Machine und Judge werden nur geladen, wenn eine echte sprachliche
Mutation oder neues Authoring erforderlich ist. Die bloße Auswahl verschiedener,
bereits vollständig eingefrorener Composition-/Semantic-Candidates ist kein
sprachlicher Arbeitsschritt.

Erkundung, Verbesserung, Diagnose und Bestätigung sind Zwecke derselben Planung.
Ein Reject ist ein Befund, kein Befehl, dieselbe Zusammensetzung erneut zu rendern.
Favorite, Keep und begründeter Reject sind positive beziehungsweise negative
Impulse derselben Lernpipeline. Für neue Bewertungen werden weder RecoveryCase,
Recovery-Karte noch Child-Attempt erzeugt. Die alten Tabellen bleiben nach dem
kontrollierten Purge ausschließlich leer aus Schema-Kompatibilitätsgründen.
Technisches Recovery setzt nur bereits autorisierte, materialisierte Recipes und
Seeds auf derselben normalen Karte fort und trifft keine kreative Entscheidung.

Seit Schema 57 werden Review, Sessionrevision, gegebenenfalls Credit,
Evidence-Watermark, Idempotenzresultat und genau ein Projektionsauftrag kurz und
atomar persistiert. Knowledge-/Evidence-Projektion und deduplizierter
Director-Auftrag folgen hinter der Outbox. Während des Spielercommits gibt es
keinen Provideraufruf. Andere spielbereite Karten und aktive Sessions bleiben
erhalten.
Nur der abgeschlossene Slot wird neu beurteilt. Passende aktive Favorite-/Keep-
Bilder können im selben Vergleichskontext übernommen werden; insgesamt bleiben
es vier Bilder. Vier positive Bilder schließen nur die aktuelle Frage ab. Solange
Campaign und Entwicklungsstufe aktiv sind, füllt der Director den verbrauchten
Slot mit einer anderen offenen Frage nach. `campaign_complete` ist ausschließlich
ein terminaler Campaign-/Stagevertrag und kein Synonym für vier positive Bilder.

`accepted` bezeichnet dabei ausschließlich die Annahme einer Quest und ist kein
terminaler Qualitäts-, Review- oder Supplyzustand. Eine angenommene Karte bleibt
fachlich Slot-Owner, solange ihre Session offen oder ihre persistierte Review-,
Credit- und Director-Folge noch nicht vollständig entschieden ist. Abgeschlossene
historische `accepted`-Karten bleiben Evidence und Kandidatenquelle, sind aber
weder laufende Campaign-Aktion noch fortzusetzender FIFO-Backlog.

Das frühe Setzen von `accepted` beim Annehmen der Karte ist damit beabsichtigt;
fehlerhaft wäre, daraus eine vollständige Bewertung oder einen freien Slot
abzuleiten. Erst nach Sessionabschluss, Review, Credit und Director-Entscheidung
darf der nächste Fragevertrag geplant werden. Dieser darf qualifizierte einzelne
Keep-/Favorite-Bilder übernehmen und füllt die übrigen Plätze mit neuen
Challengern. Er darf weder während der offenen Session noch allein wegen des
Annahmestatus parallel entstehen.

Vier positive Bilder dürfen nicht als identische normale Vierergruppe in den
unmittelbaren Nachfolgeslot übernommen werden. Ihre gemeinsame Frage ist
beantwortet; die Bilder bleiben einzeln für ihren kompatiblen Kandidaten- und
Champion-Cup-Pool qualifiziert. Eine spätere normale Wiederbewertung benötigt
eine tatsächlich andere, explizit persistierte Versuchsfrage. Eine Wiederholung
derselben Viererbesetzung ist ausschließlich mit einem eigenen markierten
Evaluation-, Kalibrierungs- oder Reproduzierbarkeitsvertrag zulässig.
Ohne einen solchen neuen Einzelvertrag dürfen dieselben vier Bilder als
gemeinsames Feld regulär erst in einem passenden eingefrorenen 16er-Cup wieder
aufeinandertreffen;
einzelne Bilder dürfen unabhängig davon in anders zusammengesetzten, kompatiblen
normalen Gruppen erscheinen.

Der rollierende Vorrat umfasst sechs dynamisch unterschiedliche normale Fragen
plus genau eine Quest für jeden aktivierten sensitiven Content Scope. Mit
`sexy`, `lewd`, `nude` und `explicit` sind dies zehn Karten. Keine identische
Question Signature darf im aktuellen Ready-Fenster doppelt vorkommen.

Der Supply-Loop ist für jede Campaign und jeden Character identisch. Character,
Scope, Promptbausteine und Evidence sind Eingaben desselben Ablaufs, niemals ein
Grund für eigene Scheduler- oder Recoverypfade. Jeder Zielslot besitzt genau
einen gemeinsamen Lifecyclezustand: `in_review`, `ready`, `preparing`,
`awaiting_followup`, `parked_resume`, `parked_backlog`, `blocked` oder
`missing`. Eine gutgeschriebene Bewertung
ohne Entscheidung der aktuellen `rolling-m6-v2`-Revision bleibt sichtbar
`awaiting_followup`; der Reconciler stellt ihren deduplizierten Director-Outbox-
Job auch nach einem Neustart oder Policy-Cutover wieder her. Erst das
Director-Ergebnis verbraucht die alte Karte fachlich und öffnet den Slot für die
nächste Frage. API, Scheduler und Diagnose müssen dieselbe Slotprojektion lesen.
Der globale schlanke Trial-Katalog überträgt deshalb je Campaign dieselben
Zähler und den Slot-Lifecycle; eine noch nicht spielbare Karte darf dort nicht
einfach verschwinden. Ein terminaler Prompt-/Validatorfehler wird aus dem
immutable Ausführungszustand als `blocked` in diese Projektion gefaltet und darf
nicht weiter als laufende Vorbereitung erscheinen.

Availability und Slot-Lifecycle werden gemeinsam projiziert: Das Parken entfernt
eine Karte aus dem sichtbaren aktiven Supply, erteilt aber keine Autorisierung
zur Ersatzgenerierung für ihren gemerkten logischen Slot. Eine fortsetzbare
`accepted + parked`-Session, eine geparkte vollständige Gruppe, bereits
eingereichte Providerarbeit und ein ungesendeter vorbereiteter Attempt beanspruchen
den Scope in dieser Prioritätsreihenfolge. Erst wenn der gemeinsame Resolver
keinen solchen Owner und keinen ausstehenden Director-Follow-up findet, ist der
Slot `missing`. Auswahl, Wiederanbindung und finale Slotprüfung erfolgen unter
derselben serialisierten Campaign-Transaktion. Vor dem Persistieren werden nicht
nur Stage, Settings, Generation und Owner, sondern auch Parent-Finalisierung,
Carry-Verfügbarkeit und der vollständige Lineage-Snapshot erneut geprüft.
Challenge, Attempt, AttemptImages, Karte, Mode-Selection, Gruppe und QEC werden
erst danach atomar angelegt; ein verlorenes Race hinterlässt keine dieser
Runtimeentitäten.

Ein technisches Provider-Resume ist nur zulässig, wenn ein read-only Audit den
vollständigen eingefrorenen Card-/Challenge-/Attempt-/QEC-/Gruppenvertrag, vier
Slots, Recipe-Hashes, Seed-Policy, Experimentachse, Locks, AttemptImages und
Providerbindungen als konsistent bestätigt. Plan- oder Submission-Existenz
allein ist keine Resume-Autorisierung.

Pro Campaign und Scope darf höchstens eine neue Vorbereitung gleichzeitig
beginnen. Diese fachliche Breite ändert die Ressourcenregel nicht: Zwischen
Campaigns und Scopes wird fair rotiert, schwere Providerarbeit bleibt global
sequenziell. Bereits sichtbare Provider-Reconciliation besitzt Queue-Vorrang;
sie setzt aber eine extern angenommene, gestartete oder ergebnisunklare Arbeit
mit persistierter Provider-, Run-, Stage-, Intent-, Decision- und Lease-
Korrelation voraus. `prepared` ohne externen Startbeleg ist neue Startarbeit;
WorkIntent, Guardian-Decision oder Lease allein machen daraus keine
Reconciliation. Ein nachrangiger Supply-/Rollingjob wird nach zwei Minuten
wieder in die
altersbasierte FIFO-Spur gehoben, damit kontinuierliche Recovery-Arbeit ihn
nicht unbegrenzt verhungern lässt. Ein bereinigter Altbestand darf einen später deterministisch erneut
entstandenen Attempt nicht über einen alten Modellcall-Schlüssel kontaminieren;
Embedding- und Promptjournale binden ihren Schlüssel deshalb zusätzlich an die
immutable Lern-Eingangsrevision.

## Auswahlpolicy und Einzelprovenienz

Der Director autorisiert Frage, Content Scope, Assetrolle und zulässigen Kontext.
Der Lernplanner vergleicht kompatible Komponenten-Versionen, Recipe-Erfahrungen
und qualifizierte technische Profile. Vorhandene `combo_prompts` begrenzen den
Suchraum nicht; ihre alten Skalar-Ratings sind keine Auswahlgrundlage.

`rolling-m6-v2` kombiniert getrennte Ränge für erwartete Qualität, Unsicherheit
und neue Abdeckung mit Reciprocal Rank Fusion, `k=60`, Gewichtung `2:1:1`.
Maximal 128 kompatible Kandidaten, verworfene Alternativen, Begrenzungsgrund und
deterministische Tie-Breaks gehören in die Entscheidung. Unbekannt ist neutral
und unsicher, keine bestätigte Erfolgswahrscheinlichkeit. Aus zulässiger
Komponenten-Evidence abgeleitete Schätzungen werden ausdrücklich als solche
markiert. Kombinationserfolg gibt niemals automatisch jedem Token Credit.

Der Explorationsteil wird aus der tatsächlich verfügbaren Evidence abgeleitet:
niedrige Confidence oder große ungetestete Abdeckung reserviert zwei Plätze,
mittlere Confidence einen und hohe Confidence beziehungsweise eine reine
Bestätigungsfrage keinen Pflichtplatz. Die rankbasierte Fusion `2:1:1`, der
persistent rotierende Campaign-/Scope-Cursor und deterministische Tie-Breaks
verhindern dabei, dass neue Varianten dauerhaft verhungern. Diagnose und
Bestätigung sind von einer erzwungenen Exploration ausgenommen.
Wiederholt schwache Kombinationen verlieren Rang; eine unveränderte Wiederholung
braucht neue relevante Evidence oder einen benannten Diagnose-/Bestätigungszweck.

Erkundung darf bis zu drei freigegebene semantische Achsen kombinieren.
Character/Canon, Scope, Assetrolle und technische Kompatibilität bleiben gesperrt.
Identity/Style benötigen eine passende ausdrückliche Frage. Isolierte Diagnosen
behalten Control/Challenger und ein Ein-Achsen-Budget; das gilt nicht pauschal für
Folgegenerationen. Eine neue Frage erhält ihren eigenen Vertrag, nicht sämtliche
Beschränkungen des abgeschlossenen Quellversuchs.

Jeder neue Slot besitzt Komponenten-, Prompt- und Recipe-Provenienz. Gemeinsam
veränderte Achsen liefern Kombinations-/Recipe-Evidence; kausaler Einzelachsen-
Credit setzt einen geeigneten isolierten Vergleich voraus.
ChampionSlot und 16er-Pool binden zusätzlich den typisierten
`experiment_kind` und die `comparison_axis`. Zwei Quests mit demselben
`focus_kind` und derselben Assetrolle, aber unterschiedlicher Versuchsfrage,
dürfen deshalb keinen Champion-Pool teilen.

### Zweistufiger Playground-Anschluss

Im aktuellen M6-Entwicklungsbetrieb ist der vorhandene Playground der
explorative Suchraum. Er wird nicht vollständig in jede Campaign kopiert:
ausgewählte Zeilen werden lazy mit `development_import`-Receipt durch denselben
Validator und Materializer gebunden, den auch `ai_authored` Vorschläge benutzen.
Der Kandidatenraum enthält anschließend sowohl noch nicht importierte
Entwicklungszeilen als auch aktive KI-ComponentVersions.

Eine von Prompt Machine und Judge angenommene semantische Blockersetzung
überschreibt keine Quellkomponente. Der Compiler materialisiert je verändertem
Block eine immutable Child-ComponentVersion mit Parent, Proposal,
`influence_refs`, Hypothese und exaktem Diff. Erst der atomar akzeptierte
Viererplan setzt diese Version auf `testing`; bei der nächsten noch nicht
eingefrorenen Entscheidung steht sie wieder als Kandidat zur Verfügung.

Der persistente Cursor erschließt Scene-/Outfit-Kombinationen und rotiert den
gemeinsamen Pose-/Expression-/Lighting-Stützkontext zwischen Entscheidungen.
Innerhalb eines Panels bleiben diese Stützblöcke zunächst stabil, damit Scene
plus Outfit höchstens zwei Achsen belegen und die Prompt Machine noch genau eine
weitere Achse konkretisieren kann. Bei offenen Katalogbereichen ist mindestens
jede dritte normale Folgequest eine semantische Coverage-Frage. Es entsteht kein
kartesisches Vollprodukt; Qualität, Unsicherheit und Neuabdeckung werden weiter
`2:1:1` rankbasiert fusioniert.

Im finalen Produktbetrieb startet derselbe Runtime-Katalog inhaltlich leer.
`CoveragePlan → ComponentIntent → Component Designer → Prompt Lexicalizer →
Judge → deterministischer Validator/Materializer` erzeugt dann Character-,
Outfit-, Scene-, Pose-, Expression-, Lighting- und Modifier-Versionen. Der
Lexicalizer liefert ungewichtete Atome; die WeightPolicy setzt Zahlen. Damit
münden Entwicklungsimport und persönliches AI-Authoring ab der ersten
materialisierten Version in exakt denselben Generation-/Review-/Evidence-Loop.

Favorite, Keep und Reject bleiben an Character, Scope, Frage, Recipe und
Version gebunden. Technisch unbewertbares Material erzeugt einen Blocker statt
einer Spieler-Disposition. Cross-Character-Evidence für Uniformen oder Orte ist eine
eigene Projektion. Sie darf einen gemeinsamen Blueprint vorschlagen, ihn aber
niemals automatisch materialisieren oder zu Canon erklären.

Jeder reguläre Vierer-Booster stellt vier bildlose Kartenkörper bereit. Nach
vier abgeschlossenen Reject-/Keep-/Favorite-Dispositionen entstehen genau vier
Spielkartenresultate: Reject lässt den Körper bildlos auf Standard, Keep bindet
das Bild mindestens als Common und Favorite mindestens als Rare. Bildlose
Karten benennen ihren Effekt plain; bei Bildkarten darf eine LLM ausschließlich
den feststehenden Effekt in den sichtbaren Bildkontext einbetten. Die Karte ist
keine neue Evidencequelle; nur Keep/Favorite erzeugen eine Bildkarte und
qualifizieren zunächst für den visuellen Challenger-Pool. Championtitel,
Stability, Dataset-Mitgliedschaft und Assetverwendungen bleiben getrennte
Beziehungen. Eine maschinelle
Bildbeschreibung darf eine verständliche Kartenbeschreibung vorschlagen, wird
im normalen Trial aber nicht zusätzlich bestätigt oder korrigiert. Ihre
spielerische Prüfung läuft im eigenständigen Zwei-Bild-Beschreibungstest. Dessen
mehrere revisionsgebundene Paarentscheidungen erzeugen ausschließlich
DescriptionMatchEvidence und eine rebuildbare Eindeutigkeitsprojektion.

## Prompt Machine und sichtbare Unterschiede

Die Prompt Machine erhält ausgewählte Kandidaten, die auslösende Human Evidence,
geeignete Referenzinhalte, Locks und Variationsbudget. Strukturierte Vorschläge
ersetzen freigegebene semantische Blöcke und benennen Zielblock, sichtbares
Ergebnis, Unsicherheit und vorhandene `influence_refs`. Kleine angehängte Zusätze
oder pauschal erhöhte Gewichte sind nicht das Standardverfahren.

Code besitzt weiterhin Seed-, Weight-, Recipe- und Submission-Autorität; der
Compiler verwendet die versionierte WeightPolicy. Prompt Machine und Judge
erhalten dieselben tatsächlich übertragenen Quellen. Der neue Einzelvertrag
`m6-slotwise-v2` ersetzt für noch nicht eingefrorene Arbeit die Sammelanfrage:
vier neue Slots bedeuten vier sequenzielle Vorschläge und anschließend einen
gemeinsamen Judge. Übernommene Bilder benötigen keinen neuen Vorschlag.
Höchstens drei Versuche je neuem Slot und drei Gesamtprüfungen sind zulässig
(maximal zwölf Vorschlags- plus drei Judge-Calls). Sind drei Vorschläge für
einen Slot unbrauchbar, wird die fehlgeschlagene Vorbereitung unverändert als
`proposal_exhausted` superseded und derselbe Supply-Slot mit neuer Kandidatenwahl
geplant. Gescheiterte Kandidaten-, Kompositions- und Proposal-Signaturen werden
ausgeschlossen. Es gibt keine pauschale Grenze von zwei vollständigen
Neuplanungen mehr. Stattdessen wird der für die Lernentscheidung eingefrorene
Pool von höchstens 128 Kandidaten revisionssicher ausgeschöpft; jede Kandidaten-
beziehungsweise Kompositionssignatur darf darin höchstens einmal verwendet
werden. Erst ein tatsächlich leerer Pool wird sichtbar `blocked`. Eine neue
Quellen- oder Evidence-Revision darf einen zuvor ausgeschlossenen Kandidaten
erneut qualifizieren. Ressourcen-, Provider- und Integritätsfehler verbrauchen
den Kandidatenpool nicht.
Validatoren prüfen Dubletten, widersprüchliche Positiv-/Negativblöcke, Locks,
Variationsbudget und Unterschiede zu übernommenen Bildern. Unterschiedliche
Negativlisten allein gelten nicht als sichtbare Alternative, wenn die positiven
freigegebenen Blöcke identisch sind.

Ein anderer Recipe-Hash oder anders formulierter VLM-Text beweist keine sichtbare
Diversität. Bilddiagnostik bleibt unsicher; Human Review entscheidet. Keine
automatische Bilderentsorgung oder Ersatzgeneration.

### Gemeinsamer Slot- und Compilervertrag

Vor dem ersten KI-Auftrag bindet jeder stabile Slot seinen Kandidaten,
Komponentenstand, Basis-Recipe-Hash, Locks, erlaubte Achsen und das Gesamtbudget
im unveränderlichen Eingangsmanifest. Komponentenwechsel zählen bereits zum
Budget: Szene plus Outfit belegen zwei Achsen; eine Poseänderung belegt die
dritte, eine zusätzliche Lighting-Änderung wäre unzulässig. Konkretisierungen
derselben Achse verbrauchen keine weitere Achse.

Das Modell liefert ausschließlich Slot-ID, `block_replacements`, erwarteten
sichtbaren Unterschied, Unsicherheiten und zulässige `influence_refs`.
`affected_axes` wird im Code abgeleitet. Eine unveränderte Übernahme des
ausgewählten Kandidaten ist erlaubt, wenn dieser bereits die Alternative bildet;
der Compiler darf dabei nicht auf die frühere Basiszusammensetzung zurückfallen.

Die schreibfreie Compilerprüfung und die spätere atomare Materialisierung nutzen
denselben Vertrag. Dublettenprüfung betrifft sowohl vollständige resultierende
Positiv-/Negativkompositionen als auch eine Sichtbarkeitssignatur der positiven,
freigegebenen Blöcke einschließlich übernommener Bilder. Gleiches Pose-Delta bei
unterschiedlichen Szenen ist nicht automatisch eine Dublette.
Der Judge erhält die vorkompilierten Varianten sowie die Vereinigung der
tatsächlich übermittelten Slot-Kontexte; keine nachträglich entdeckten Quellen.

Spätere Slots sehen vorherige Varianten ausdrücklich als ungeprüfte Vorschläge.
`revise` benennt Slot, Fehlercode und Feldpfad; nur betroffene neue Slots werden
mit vorherigem Vorschlag und Beanstandung erneut angefragt. `accept` mit Fehlern
ist keine Annahme. Ein formal ungültiger Structured-Output-Call darf
ausschließlich in Prompt-Author-, Lexicalizer-, Proposal- und Judge-Profilen
genau einen deterministischen Strukturheilversuch erhalten: ein eindeutig
fehlendes JSON-Komma oder genau eine fehlende Abschlussklammer außerhalb von
Strings und Zahlen. Nur wenn genau eine reparierte Variante Duplicate-Key-,
Finite-Number- und Strict-Schema-Prüfung besteht, zählt sie als derselbe
ausgeführte Call. Originalantwort und -hash, Editposition, reparierter Hash und
Validierung bleiben append-only erhalten. Refusal, Trunkierung, mehrere
Deutungen oder eine Inhaltsänderung bleiben Fehler. Ein fachlich ungültiges
einzelnes Promptatom erzeugt nur für sein Feld beziehungsweise seinen Slot eine
gezielte Korrekturanfrage; bereits gültige Felder bleiben gebunden. Erst nach
Ausschöpfung des begrenzten Modellbudgets greift die oben definierte
Kandidaten-Neuplanung. Unbekannte externe Ergebnisse, Integritätsfehler und
tatsächliche Provider-/Ressourcenfehler bleiben Reconciliation- beziehungsweise
Stop-Gates.

Development-Importe durchlaufen denselben atomweisen Parser vor Ranking,
Input-Freeze und Modellcall. Er darf ausschließlich fehlende Trenner zwischen
zwei vollständigen gewichteten Atomen, genau eine fehlende äußere runde Klammer
sowie Rand-Whitespace korrigieren. Texte, Zahlen und Gewichtungen werden nie
geraten oder geklemmt. Ein Atom wie `(boy:13)` wird verworfen, nicht in `1.3`
umgedeutet; andere gültige Atome derselben Playground-Komponente bleiben
verwendbar. Das mutable Playground-SQLite wird dabei nicht verändert.

## Schema 47 und eingefrorene Ausführung

Schema 47 ergänzt, ohne historische Reviews/Recipes/Events zu überschreiben:

- `learning_policy_revisions`: immutable Auswahlpolicy.
- `learning_decision_revisions`: immutable Kandidatenranking, Zweck, Übernahmen,
  Achsen, Knowledge-Bindung und Alternativen.
- `learning_preparations`: separater veränderbarer Zeiger auf die aktuelle
  unbegonnene oder eingefrorene Entscheidungsrevision.
- `learning_input_revisions` und `learning_input_items`: vollständige Quellenliste,
  Verträge, Modell-/Policyrevisionen und Hashes, vor dem ersten KI-WorkIntent.
- `learning_input_artifacts`: exakte Zuordnung persistierter Vektoren zu Quellen.
- `learning_model_call_requests/results`: persistierte tatsächliche Modellinputs
  und Resultate; abgeschlossene Calls werden wiederverwendet.
- `campaign_learning_cursors`: vorgemerkte/verbrauchte Evidence und Erkundungsrotation.
- additive Manifest-/Entscheidungsbindungen an WorkIntents, Receipts,
  ContextPacks und DiversityPlans.

Unbegonnene Entscheidungen können durch neuere Revisionen ersetzt werden.
Ab dem ersten KI-WorkIntent ist das Manifest fest, auch beim Ressourcenwarten.
Neue Bewertungen gehören zur nächsten Entscheidung; sie verändern keinen
laufenden Request. Gelöschte Referenzen, widerrufene Autorisierung und ungültige
Provenienz sind gesonderte Sicherheitsblocker.

Resume verwendet die exakte Liste und deren Artefakte, niemals den inzwischen
gewachsenen Gesamtbestand oder einfach den neuesten Vektor. Textbatch 32 bedeutet
höchstens 32 gleichartige Dokumente innerhalb einer zusätzlich auf 8192 reale
Tokenizer-Tokens begrenzten Seite, keine Begrenzung auf die ersten 32 Quellen.
Queries laufen je Raum getrennt mit einer revisionsgebundenen Instruction;
Dokument- und Querytexte werden nicht in einem Providerrequest vermischt.
Semantische Embeddingtexte sind getrennt vom vollständigen technischen Manifest;
Seeds, Recipe-IDs und numerische Promptgewichte werden nicht eingebettet.
Überlange Texte werden ausdrücklich blockiert, nicht vom Provider still gekürzt.

## Retrieval, Analyse und Autorität

Fünf aktive typisierte Texträume sowie `machine_image_description_text`,
`full_frame_semantic` und `style_view` verwenden denselben Retrievaldienst.
Quellen behalten Character, Scope, Context, Cohort und Modellrevision. Keine
Umkennzeichnung historischer oder fremder Quellen als Quelle des Zielkontexts.
Bildabfragen verwenden ausschließlich passende reviewed Same-Space-Anker.
Fehlender Bootstrap/Anker erzeugt einen Receipt mit Abstention. Fusion geschieht
rankbasiert, nicht durch Addition inkompatibler Text-/Bildscores.

Die auslösende Human Evidence gehört zwingend in den ContextPack; Retrieval
ergänzt sie und darf sie nicht verdrängen. Frische Analyse darf Textlernen nicht
pauschal blockieren. Nur ausdrücklich erforderliche, laufende Analyse erzeugt
`waiting_for_analysis`; technische Fehler werden sichtbar und sind kein
stillschweigendes Weglassen. Abschlüsse markieren neue Erkenntnisse für die
nächste unbegonnene Entscheidung.

Veröffentlichte historische Cohorts gelten nur für ihre Campaign und bleiben
`proof_eligible=false`. Fresh-Proof schließt historische Quellen über Manifest,
Vektoren, Receipts, ContextPack und Plan hinweg aus. VLM beschreibt, Human Review
bewertet; weder Embeddings noch LLM setzen Champion-, Canon-, Safety- oder
Evidence-Autorität.

Beschreibungsmatches verändern auch keine Prompt- oder Kartenqualität. Der
Generierungsprompt ist die ursprüngliche Absicht und darf als
Ähnlichkeitssignal beziehungsweise Provenienz dienen, aber nicht als Ground
Truth der sichtbaren Beschreibung. Qwen-Textvektoren und SigLIP-Bildvektoren
liegen in getrennten Räumen und sind nicht direkt per Kosinus vergleichbar. Ein
echter Text-zu-Bild-Score ist nur innerhalb einer gesondert qualifizierten
gemeinsamen multimodalen Modellrevision zulässig.

## Restart, Job 446 und Ressourcen

### Modellrequest und belegte Beispiele

Die Prompt Machine erhält explizite Playground-Vokabularbeispiele mit Zuordnung
zum stabilen Slot sowie tatsächlich selektierte RAG-Beispiele. Referenzbeispiele
enthalten vorhandene semantische Promptfakten, freigegebene Bildbeschreibung und
Human-Feedback; ein unbewerteter Playground-Eintrag erhält niemals ein erfundenes
positives Rating. Fehlende Beispiele werden als Abstention ausgewiesen.
Prompt Machine und Judge sehen dieselben Beispiele. Nur tatsächlich übertragene
Aliase sind als `influence_refs` zulässig. Ein Budgetproblem darf nicht alle
vorhandenen Beispiele still entfernen und anschließend erfolgreiche RAG-Nutzung
behaupten. Advanced zeigt den tatsächlichen Request, nicht nur den ursprünglichen
ContextPack.

Der Transport bleibt lokal `POST /v1/chat/completions` mit
`response_format.type=json_schema`, `strict=true`, `stream=false`. Zusätzlich
prüft der Client vollständiges JSON Schema, Abschlussgrund, Refusal, doppelte
JSON-Schlüssel und endliche Zahlen. Trunkierung und ungültige Antworten werden
nicht repariert. Semantische Achsen-/Lock-/Diversity-Prüfung bleibt separat.

Neue Slot-Manifeste binden `m6-slotwise-qwen3-v1`: Vorschlag Temperature `0.7`,
Top-P `0.8`, Top-K `20`, maximal `1024` Ausgabetokens; Judge Temperature `0.2`,
Top-P `1.0`, Top-K `20`, maximal `768` Tokens. Penalties bleiben neutral.
Kontext bleibt zunächst `4096`; ältere eingefrorene Batchverträge behalten
`m6-structured-qwen3-v2` beziehungsweise ihr früheres Profil.
Das sind **noch zu qualifizierende Samplingprofile**, keine Behauptung einer
damit bereits behobenen Modellschwäche. `/no_think` ist der modellseitige
Soft-Switch, keine garantierte Backend-Abschaltung. Kein nicht dokumentiertes
`enable_thinking`-Feld wird an den OpenAI-kompatiblen Endpoint gesendet.
Bestehende eingefrorene Manifeste behalten ihre bisherigen Einstellungen.
Sampling ist nicht mit ComfyUI-Seeds verbunden; reproduzierbares Resume verwendet
persistierte Resultate statt einer behaupteten deterministischen Neuberechnung.

Die vollständige Anfrage inklusive Korrekturtext, Chat-Template, konservativer
Schemareserve und Ausgabetokens wird über die bereits Guardian-geladene Instanz
gezählt (`lmstudio==1.5.0`, `list_loaded`, `apply_prompt_template`, `tokenize`,
`get_context_length`). Die Tokenprüfung lädt selbst kein Modell. Überlauf wird
mit tatsächlichen Budgetwerten als bekannter, nicht gesendeter Fehler gespeichert;
weder Kontextvergrößerung noch stilles Abschneiden sind erlaubt.

Identische Human-Befunde dürfen verlustfrei gruppiert werden: vollständige
Quellalias-Mitgliedschaft bleibt im ContextPack, der Modellkontext enthält einen
Gruppenalias, Anzahl und einen gemeinsamen Reason-Katalog. Dies ist keine neue
Evidence und kein kausaler Credit. Semantisch unterschiedliche Befunde bleiben
getrennt. Bis zu drei passende, nicht identische RAG-Beispiele ergänzen den
Pflichtkontext; fehlende negative/positive Kategorien werden ausgewiesen.
Recipe-Fakten bleiben blockweise, nicht auf den globalen Promptanfang reduziert.

Grundlagen: [LM Studio Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output),
[Chat-Completions-Parameter](https://lmstudio.ai/docs/developer/openai-compat/chat-completions)
und [Qwen3-Modellvertrag](https://huggingface.co/Qwen/Qwen3-14B).
Die Tokenprüfung folgt der [offiziellen Tokenisierungs- und Chat-Template-Schnittstelle](https://lmstudio.ai/docs/python/tokenization).
Die Qwen-Empfehlung für nicht-denkendes Sampling ist der Ausgangspunkt des
Vorschlagsprofils; das niedrigere Judge-Temperature ist eine eigene Testhypothese.

### Wiederaufnahme und Ressourcen

Ressourcen-/Providerwarten verbraucht kein Fehlerbudget. Transiente Fehler werden
höchstens dreimal je Stufe nach Provider-/Output-Reconciliation wiederholt.
Deterministische Integritäts-/Schema-/Provenienzfehler blockieren sofort; Sweeps
dürfen blockierte M6-Jobs nicht wiederbeleben. Ein Modellrequest mit unbekanntem
externem Ergebnis wird nicht blind doppelt gesendet, sondern zur Reconciliation
blockiert. Bereits persistierte Resultate sind replaybar.

`not_before` ist dabei ausschließlich der früheste Zeitpunkt des nächsten
Claims beziehungsweise Ressourcenchecks. Ein ansonsten ausführbarer
spielrelevanter M6-Job in Coordinator-, LM- oder Comfy-Lane, der selbst oder
als unmittelbarer Handoff auf die gemeinsame Heavy-Ressource wartet,
behält bis dahin seine Foreground-Reservierung; sobald er fällig ist, trägt die
gewöhnliche Runnable-Projektion den Vorrang ohne Lücke weiter. Fachlich noch
nicht fällige Timer, Provider-Unverfügbarkeit, Pilot-Warten und Maintenance
reservieren die Heavy-Ressource nicht.

Die Reservierung gilt nur für weiterhin ausführbare Jobs. Ein Job mit
ausgeschöpftem Versuchslimit oder ein durch den aktuellen Pilot-/Scopevertrag
ausgeschlossener Job kann optionale Analyse nicht dauerhaft zurückhalten.

Einzelrequests werden anhand WorkIntent, Eingangsmanifest, Slot, Stufe und
Revision gebunden. Request-/Resultathashes, konkrete Samplingparameter,
Schemahash, Tokenverbrauch und Abschlussgrund bleiben nachvollziehbar.
Crash nach Slot zwei wiederholt diese beiden Calls nicht. Bekannte ungültige
Antworten bleiben als Fehlerartefakte erhalten; unbekannte externe Ergebnisse
bleiben ein gesonderter Reconciliation-Fall. Die sequenzielle Promptphase
erneuert Lease und Providerheartbeat. Ein Modell darf zwischen Einzelcalls
geladen bleiben; vor ComfyUI sind kontrolliertes Unload und Ressourcenprüfung
weiterhin Pflicht.

Job 446 wird nicht gelöscht oder manuell neu generiert. Vollständig
rekonstruierbare Inputs werden übernommen. Fehlt der ursprüngliche vollständige
Snapshot, darf ausschließlich die unmaterialisierte Vorbereitung nachvollziehbar
superseded werden; genau ein Auftrag für ihren freien Slot folgt. Existierende
Arme, Providerarbeit, aktive Sessions und historische Receipts bleiben erhalten.
`scripts/m6_learning_reconcile.py` ist standardmäßig read-only; `--apply` benötigt
die unveränderte Inventarsignatur und erstellt zwingend ein SQLite-Backup.

Modelle/Plattformen bleiben unverändert. Guardian entscheidet exklusiv über die
schweren GPU-Klassen; Text Embeddings bleiben ein einzelner CPU-WorkIntent und
nutzen innerhalb des geladenen 8k-Profils Parallelität 4. Kein Cloud- oder
Modellfallback, kein Umgehen des Guardian und kein Prozessabschuss als
Speicherfreigabe. Die [Orchestrierungsregeln](orchestration-guardian-and-monitoring.md)
gelten auch für technische Wiederaufnahme.

## Abnahmegrenze

### Ausführungsrevision und Kontextbudget

Der fachliche Schema-47-Eingang (Evidence, Kandidaten, Slots, Locks und Hashes)
bleibt unverändert. Ein explizites Resume legt einen immutable
`M6ExecutionResumeAuthorized`-Event mit Elternrevision, Inventarsignatur,
Execution-Profile und Budgetpolicy an. Es entsteht ein neuer Prompt-WorkIntent,
nicht ein Reset des alten Jobs oder seiner Request-/Resultathistorie.

Erfolgreiche Calls werden nur bei identischen Eingängen wiederverwendet und mit
`M6ModelCallReused` auf den ursprünglichen Call gebunden. Bekannte Fehler bleiben
sichtbar. `not_submitted=true` verbraucht keinen Modellversuch; tatsächlich
ausgeführte Versuche zählen revisionsübergreifend (drei je Slot, drei Judge-Calls).
Unbekannte externe Ergebnisse, widerrufene Referenzen und ungeklärte Providerarbeit
blockieren. Materialisierte Recipes werden ausschließlich technisch fortgesetzt.

Die Budgetrevision `templated-input-grammar-separate-v3` zählt die vollständige
templatisierte Anfrage und die unveränderte Ausgabereserve (1024/768). Der
Schemaumfang wird separat protokolliert; beim qualifizierten GGUF-Grammatikpfad
wird er nicht zusätzlich als Prompttext gezählt. Der gemeldete Providerverbrauch
muss die SDK-Eingangszählung bestätigen. Unterschiedliche Evidence wird niemals
zusammengefasst; exakt gleiche Judge-Blöcke dürfen verlustfrei über `shared_ref`
und `shared_values` referenziert werden.

Reicht 4096 tatsächlich nicht, erfolgt keine Submission. Ein explizit freigegebener
8192-Kontext benötigt zuerst eine eigene Load-/Ressourcen-/Unload-Qualifikation
und einen `M6ContextProfileQualified`-Nachweis. GPU-Offload 50 Prozent, Parallelität
eins, Modell, Temperature und Ausgabelimits bleiben gleich. Es gibt keine stille
Kontexterhöhung. Der nächste Resume bindet das qualifizierte Profil revisionssicher.

### Ressourcenmessung statt behaupteter Hardwaregrenze

Die anfänglichen 5500 MiB für Prompt/Judge sind eine konservative Startschätzung,
kein gemessener Spitzenbedarf. Guardian weist Schätzung, 1536 MiB VRAM-Reserve,
tatsächlich freien VRAM und RAM getrennt aus. Während echter Inferenz werden
sekündliche Stichproben sowie Messungen nach dem Laden, zwischen Calls und nach
Unload an Lifecycle und Execution Profile gebunden. Stichprobenmaxima sind kein
lückenloser Peak-Nachweis und ändern die Policy nicht automatisch. Ein anderes
Kontextprofil benötigt seine eigene Qualifikation. Kleine Baseline-Abweichungen
allein blockieren bei bestätigtem Unload nicht.

Die immutable Ressourcenpolicy `phase-aware-memory-pressure-v1` trennt
Modellergebnis und nächste Ressourcenfreigabe. Vor dem Laden gelten die
profilgebundene Startschätzung und die reale Providerbelegung. Passt der
geschätzte zusätzliche Working Set in den freien Speicher und meldet das
Betriebssystem keinen Speicherdruck, ist ein nicht vollständig verbleibender
Planungspuffer eine Warnung und kein Startverbot. Nach dem Laden werden
Modellgewichte nicht erneut als zusätzlicher Bedarf berechnet. Während und nach
Inferenz ist eine Unterschreitung von 4096 MiB RAM oder 1536 MiB VRAM allein eine
Warnung, kein Modellfehler. Eine valide Antwort samt Receipt wird dauerhaft
gespeichert, bevor über Folgearbeit entschieden wird.

Das Windows-Signal `LowMemoryResourceNotification` wird zusätzlich gemessen.
Tatsächlicher Speicherdruck oder fehlende Messbarkeit pausiert neue Calls;
laufende Arbeit wird kontrolliert abgewickelt und die eigene Instanz entladen.
Provider-OOM, unbekannte Ergebnisse, konkurrierende Arbeit und fehlgeschlagenes
Unload bleiben eigenständige Fehler beziehungsweise Reconciliation-Blocker.
Sekündliche Messungen sind Stichproben, keine garantierten Hardware-Peaks.

Eine historische Antwort, die ausschließlich wegen der alten RAM-Reserveprüfung
als fehlgeschlagen gespeichert wurde, darf nur durch explizite gebundene
Neubewertung wiederverwendet werden: Request-/Resultathashes, Manifest,
Strict JSON, Abschlussgrund und Slot-Compilervertrag müssen bestehen.
`M6ResourceResultRevalidated` und ein abgeleiteter Validierungsreceipt verweisen
auf den unveränderten alten Fehler und die neue Policy. Ein früher nicht
erfasstes Betriebssystemsignal wird ausdrücklich als unbekannt dokumentiert.
Der tatsächlich ausgeführte ursprüngliche Call zählt weiterhin zum Versuchslimit.

Ressourcenwarten setzt dieselbe autorisierte Ausführung fort und verbraucht keine
Modellversuche. Ein nachgewiesener Fehler vor Modellladung bleibt dagegen als
fehlgeschlagener Lifecycle erhalten; nach Codefix und Regression darf eine neue,
explizit autorisierte Ausführungsrevision ihn referenzieren. Ein Docker-Leerlaufobjekt
mit ausschließlich leeren PID-/Provider-Key-/Startfeldern ist keine aktive Arbeit.
Vor dem Wechsel von einer leeren ComfyUI-Queue zu LM Studio wird der von ComfyUI
resident gehaltene Modellcache kontrolliert über `/free` entladen und danach neu
gemessen. Laufende oder wartende Comfy-Prompts verhindern diesen Wechsel.

Die getrennten Worker-Lanes heben diese Ressourcenregel nicht auf.
`gpu_lm_studio_llm`, `gpu_comfyui`, `gpu_docker_vlm` und
`gpu_docker_image_embedding` bleiben zunächst eine gegenseitig exklusive
Guardian-Gruppe. CPU-only Textembedding darf nur nach zwei reproduzierbaren
Overlap-Läufen mit derselben Modell-, Kontext-, Offload- und Hardwarerevision
parallel zu ComfyUI autorisiert werden. Beide Resultate müssen valide bleiben,
Unload und Betriebssystemsignale müssen sauber sein und die gemeinsame Wallclock
muss sich gegenüber der sequenziellen Baseline verbessern. Ohne vollständigen
Beleg bleibt die Kombination serialisiert; es gibt keinen stillen Policywechsel.
Unabhängige Lane-Claims sind deshalb keine unabhängige Heavy-Startautorität.
Claim, laneübergreifende Arbeitsklasse und Guardian-Lease prüfen dieselbe
persistierte Prioritätsprojektion; kollidierende Starts bleiben atomar exklusiv.

Läuft eine Image-Analyse über einen App-Neustart hinaus, wird ein abgelaufener
Lease nur für denselben WorkIntent, StageAttempt und Provider-Key neu autorisiert.
Ein bereits vorhandenes Resultat wird anschließend ingestiert; ein lediglich
vorbereiteter Providerjob wird nicht als neuer Modellversuch gezählt. Decision-,
Lease- und Reattachment-Ereignisse erhalten eine durchgehende Korrelation.
Ein `provider_reconcile_unknown` muss denselben vollständigen Request- und
Source-Hash-Vertrag erfüllen wie ein bekannter Poll. Meldet der Provider für
diesen Schlüssel eindeutig `404`, wird die Foreground-Priorität direkt vor dem
POST erneut geprüft; inzwischen wartende Questgenerierung gewinnt.
Ein definitiver Authentifizierungs-, Autorisierungs-, Schema- oder Requestfehler
terminalisiert Providerjob und Stage und gibt die Lease frei. Ausschließlich
`409 heavy_model_process_active` ist versuchsneutrales Provider-Backpressure;
andere Konflikte blockieren fail-closed. Ein `5xx` oder Transporttimeout nach
Write-ahead bleibt unbekannt und wird vor jedem weiteren POST per GET
reconciliiert.

Ein vor dem Docker-Modellstart festgestellter Ressourcenengpass setzt den
StageAttempt und sein Enrollment ausschließlich auf einen wiederaufnehmbaren
Wartezustand. Der Workerjob bleibt mit derselben Stage-, Intent- und
Provider-Key-Bindung eingeplant; nach frei gewordenen Ressourcen wird kein neuer
fachlicher Auftrag und kein zweiter Providerjob erzeugt. Ältere
`resource_blocked`-Zeilen ohne externe Provider-ID werden beim Workerstart
einmalig in genau diesen Wartepfad übernommen. Sobald die Stufe läuft oder ein
Artefakt ingestiert wurde, verschwinden Wartegrund und Wake-up-Projektion.

Der Live-Pilot wird persistent durch revisionierte `M6PilotRestricted`-Events
gesteuert. `attempt` lässt genau einen Attempt zu, `campaign_scope` eine Campaign-
Scope-Kombination. Der aktuelle Mehr-Character-Test verwendet
`active_content_policy`: Alle aktiven Campaigns sowie `standard` und die jeweils
aktuell in den Settings freigeschalteten sensitiven Scopes dürfen den normalen
rollierenden Loop einschließlich Folgeattempts und Analyse durchlaufen.

Die Freigabe selbst erzeugt keine Bilder und reaktiviert keine gelöschten,
abgebrochenen oder invalidierten Versuche. Bestehende Karten bleiben erhalten;
neue Arbeit entsteht aus Review-Folgeentscheidungen oder tatsächlich freien
Supply-Slots. Eine spätere Scope-Deaktivierung sperrt neue Arbeit sofort, eine
bewusste Reaktivierung erlaubt sie wieder. Der Freigabe-Snapshot bleibt trotzdem
für den Audit erhalten. Das gebundene, hardwarequalifizierte Promptprofil und
der Filter überleben Neustarts. Es gibt keine künstliche Rundenzahlbegrenzung,
keinen zweiten Generierungsweg und keine synthetische Spielerakzeptanz.

Der [Schema-47-Implementierungsnachweis](../acceptance/m6.7/02-rolling-loop.md)
trennt automatisierte Tests, DB-Kopie, realen Providerlauf und Spielerabnahme.
Zwei zusammenhängende abgeschlossene Lernzyklen müssen Bewertung → Auswahl →
Kontext → Vorschlag → Recipe-Diff → Folgebewertung belegen. Unabhängige gefüllte
Tabellen reichen nicht. Qualitätsgewinn pro Einzelbild wird nicht versprochen.
`M6_LEARNING_LOOP_PROVEN` bleibt eine ausdrückliche Spielerentscheidung.

## Schema-53-Datenbank-Gate vor weiterer Promptoptimierung

Der rollierende Vertrag setzt für neue Implementierungsarbeit zuerst eine
einzige relationale Graphautorität voraus. Globale ComponentVersions werden über
Katalog- und Availability-Bindungen in Campaigns verwendet; globale
CompositionVersions werden erst durch eine konkrete CompositionUse an Character,
Scope, Settings und Recipe gebunden. Evidence und Retrieval müssen von Review
und AttemptImage bis zu Recipe, CompositionUse, Component und Atom vollständig
per Foreign Key auflösbar sein. Alte Text-IDs und JSON-Snapshots bleiben nur
historische Belege.

Ebenso muss jede aktive Retrievalauswahl über typisierte EmbeddingSource,
Vektor, Indexmitglied, ReceiptCandidate und ContextPackSource nachweisbar sein.
Bild-Racks verwenden ausschließlich die bestehenden relationalen Reference-Set-
Revisionen; fehlende Image-Vektoren sind eine Abstention, kein leerer aktiver
Index und kein Grund für erfundene Evidenz.

Dieses Gate repariert bewusst noch nicht Candidate Ranking, Evidence Injection
oder Prompt-Machine-Verhalten. Es stellt nur sicher, dass der folgende
Prompt-Lernblock keine kampagnenduplizierten Komponenten, polymorphen IDs oder
parallelen Datenautoritäten mehr kompensieren muss. Der funktionale Zwei-
Zyklen-Nachweis bleibt danach separat offen.

## Historischer Schema-53-/v6-Zwischenstand der Evidence-Injection

Die damaligen Promptplanungen verwendeten den Vertrag `m6-slotwise-v6`. Pro Campaign,
Content-Scope und `focus_kind` wird genau ein immutable Evidence-Head gewählt.
Der einzige Candidate-Ranker löst vor dem Ranking ComponentVersion,
CompositionVersion/CompositionUse, Recipe, Promptatome und Atomgewichte auf
kanonische Beziehungen auf. Dieselbe Human-Bewertung zählt innerhalb einer
Evidence-Lane nur einmal. Direkte isolierte Evidence löst dabei konkurrierende
Attributionen derselben Quelle vor Reason- und Combination-Evidence auf; eine
direkte negative Bewertung wird dadurch jedoch niemals zu einem positiven
Rankingsignal. Legacy bleibt in den Entwicklungskampagnen ausschließlich Prior
beziehungsweise Tie-Breaker und erhöht keine persönliche Confidence.

Retrievalfragen sind raumspezifisch. Catalog, Campaign, Character-Bindung,
Scope, Modellbranch, Cohort, Proof-Eignung, Component-Rolle und bei Atomen auch
Polarität werden relational vor der Vektorsuche gefiltert. Ausgeschlossene
Peer-Compositions dürfen nicht in den ContextPack zurückkehren. Die auslösende
Human Evidence bleibt Pflichtquelle; unbewertete Playground-Komponenten sind
nur Vokabular oder Exploration, niemals positive Referenzen. Prompt Machine und
Judge sehen nur die tatsächlich ausgewählten Quellen unter stabilen Aliassen.

`keep_candidate` erhält die eingefrorene Composition unverändert. Für einen
bereits deterministisch ausgewählten `prompt_composition`- oder
`semantic_exploration`-Arm ohne autorisiertes Mutationsziel ist es das einzige
zulässige Slot-Ergebnis: fehlende kandidatenbezogene Evidence ist hier der
Grund für den Versuch und kein Abstention-Grund. Allgemeine Human Evidence im
ContextPack wird nicht still als Evidence dieses neuen Kandidaten ausgegeben.
Nachrückende, vertragsgültige Kandidaten behalten dabei ihre Ranking-,
Explorations- und Auswahlgrund-Metadaten.
`refine_atom` darf ausschließlich das vorab autorisierte Atom bearbeiten und
liefert nur eine ungewichtete Phrase; Gewichte, Seeds, IDs und Recipes bleiben
Codeautorität. Ein Reason eröffnet lediglich eine prüfbare Hypothese. Kausaler
Atom-Credit entsteht erst nach einem isolierten Vergleich. Angenommene
Verfeinerungen materialisieren fail-closed eine Child-ComponentVersion mit
Parent, exaktem Diff und `influence_refs`. Vollständig neue Components laufen
über den getrennten persistierten Component-Authoring-DAG und gelangen erst
danach in denselben Candidate-Pool.

Dieser Implementierungsstand macht den Zwei-Zyklen-Lauf testbar. Erst ein realer
Spielerbeleg, in dem Evidence aus Zyklus eins im Evidence-Head, Ranking,
ContextPack und Folge-Recipe von Zyklus zwei wieder erscheint, schließt dieses
Abnahmegate. Er setzt `M6_LEARNING_LOOP_PROVEN` weiterhin nicht automatisch.

### Historischer v8-Zwischenstand des gerichteten Review-Vertrags

Die damaligen Promptplanungen verwendeten `m6-slotwise-v8` und
`directed-human-evidence-v1`. Der ContextPack enthält keine losgelöste Liste
von Reason-Codes mehr, sondern reviewgebundene `evidence_observations` mit
Gesamt-Disposition, Score, Primary Reason sowie getrennten `preserve`, `change`
und `unknown`-Feldern. Positive und negative Reasons desselben Bildes bleiben
bis Prompt Machine, Judge und Recipe-Diff in derselben Observation verbunden.

Retrievaltreffer ohne positive Human Evidence dürfen nicht als Preserve- oder
positive Referenz erscheinen. Negative Evidence wird ausschließlich als
Change-Beispiel geführt; unbewertete Component- und Atomtexte sind nur
`exploration_targets`. Kosinusähnlichkeit findet semantisch verwandte Quellen,
bestimmt aber weder Polarität noch Qualität. Diese bleiben relationale
Metadaten.

Code autorisiert Candidate, Zielrolle, Zielatom und Operation. Ohne
deterministisch bindbares Ziel bleibt ein Reason auf Aspect-/Component-Ebene
und kann nicht irgendein Atom derselben Rolle freigeben. Der Judge muss alle
nicht zur Requalifikation freigegebenen Preserve-Achsen erhalten und darf nur
den vorautorisierten Change bearbeiten. Ein explorativer Try bleibt als
unbewiesen gekennzeichnet.

## Verlorene LM-Studio-Antworten

Ein persistierter Modellrequest ohne persistiertes Resultat wird niemals mit
demselben Call-Key erneut gesendet. Eine eigene LM-Worker-Stage prüft zuerst den
nativen Providerzustand. Solange die frühere Instanz noch vorhanden oder der
Provider nicht erreichbar ist, wartet die Stage versuchsneutral. Ist nach einem
Restart nachweislich keine Instanz mehr vorhanden, wird der alte Ausgang
append-only als `provider_outcome_lost_after_reconciliation` abgeschlossen und
eine neue technische Ausführungsrevision autorisiert. Erfolgreiche frühere
Slotvorschläge werden nur bei identischem Eingangsmanifest wiederverwendet; nur
der fehlende Vorschlag erhält einen neuen Call-Key. Ein verlorener, tatsächlich
abgesendeter Call zählt weiterhin zum Slotbudget und führt bei dessen
Erschöpfung in die normale Kandidaten-Neuplanung.

Providerheartbeats sind an genau einen Providerjob, WorkIntent, WorkLease und
LM-Lane-Claim gebunden. Sie dürfen keinen älteren Providerjob desselben
WorkIntents aktualisieren. Ein terminaler WorkIntent mit fehlender Run-ID und
ohne aktive Modellinstanz ist keine physisch laufende Heavy-Arbeit, sondern ein
sichtbarer Reconciliation-Zustand.

## Bereinigung der früheren semantischen Recovery-Domäne

`scripts/purge_semantic_recovery.py` entfernt nach signiertem Read-only-Audit,
frischem SQLite-/Datei-Rollbackpaket und leerer Providerbelegung ausschließlich
die erfassten fachlichen Recovery-Fälle, ihre Child-Attempts und die drei durch
`recovery_case_text` kontaminierten normalen M6-Attempts. Ursprüngliche normale
Quellattempts und lediglich übernommene Bilder bleiben erhalten. Champion-,
Turnier- oder fremdes Attempt-Eigentum blockiert fail-closed. Dateien werden
zuerst in ein validiertes Staging verschoben; DB und Dateien werden bei jedem
Fehler gemeinsam zurückgestellt. Anschließend werden Knowledge, Cursor,
Historical-Reference-Indizes, Champion-Eignung und Racks nur aus den verbleibenden
zulässigen Quellen neu aufgebaut. `recovery_case_text` ist kein aktiver
Embedding-, Retrieval- oder Prompt-Raum mehr.

## Champion-Cup

Sobald innerhalb derselben Campaign, desselben ComparisonContextes und desselben
Content Scopes 16 unterschiedliche verfügbare Keep-/Favorite-Bilder geeignet
sind, friert der bestehende 16er-Cup ein zusätzliches Ready-Roster ein. Er ersetzt
keinen der sechs normalen oder scopegebundenen Supply-Slots.

Der Cup verleiht der bereits vorhandenen Siegerkarte einen Slottitel. Er erzeugt
keine neue Karte und keine AssetSourceSelection. Ein technisch ähnlich
inszeniertes Asset-Auswahlspiel folgt erst post-M6 in Chronicle Slice 3. Es
besitzt einen getrennten Evaluation Focus und schreibt dort ausschließlich
Quell- und AssetAttempt-Beziehungen.

## Relationale Aspect-Gruppen und `m6-slotwise-v9`

`m6-slotwise-v9` erweitert den gerichteten Review-Vertrag um eine konkrete,
immutable Aspect-Partition je `ComponentVersion`. Die statische
`prompt_aspect_groups`-Taxonomie bleibt Root-Vokabular; erst ein akzeptiertes
Proposer-/Judge-Ergebnis und der deterministische Complete-partition-Validator
materialisieren Group-Set, Gruppen und N:M-Atombindungen. Jedes positive und
negative Atom gehört innerhalb dieses Sets genau einer Gruppe. Ein fehlerhaftes
Set blockiert nur die davon abhängige Atom-/Evolution-Planung, nicht andere
Supply-Slots. Eine unvollständige Partition erhält höchstens drei gezielte,
append-only Korrekturrunden mit den konkreten Orphan-/Overlap-Befunden. Bleibt
sie ungültig, bleibt die bereits validierte ComponentVersion für Composition-
und Coverage-Trials verfügbar; nur ihr Aspect-Group-Set wird verworfen.

Der Providervertrag `component-aspect-alias-v2` überträgt keine UUID- oder
Lineage-Metadaten. Er ordnet die kanonischen Atombindungen lokal als
`a001...aNNN` und sendet nur Alias, Blockrolle, Polarität, Phrase und bestehendes
Gewicht. Die vollständige Rückauflösung bleibt in einem immutable
Aliasmanifest. `component-aspect-instruction-v2` verlangt eine vollständige,
breite Partition von normalerweise vier bis zehn und höchstens zwölf Gruppen;
eine Gruppe je Atom ist unzulässig. Alle verwalteten Structured-Output-Aufrufe
durchlaufen vor dem POST den realen 4.096-Token-Preflight. Definitive
Providerablehnungen und unvollständige Antworten sind bekannte Resultate und
keine unbekannten Ausgänge.

Vor jeder neuen Planung wählt Code genau eine Experimentfamilie aus gerichteter
Evidence, Unsicherheit, Neuabdeckung und der fairen technischen Rotation.
Weight-, Atom-, Aspect-/Evolution-, Composition- und Technik-Trials besitzen
dadurch getrennte Variationsverträge. Ein Evolution-Challenger darf nur die
vorautorisierte Aspect Group ersetzen; alle anderen Gruppen, Components,
Renderwerte und Locks bleiben eingefroren. Auswahlgleichstände werden mit einem
persistierten Seed reproduzierbar aufgelöst.

Mindestens jede dritte normale Nachfüllentscheidung bleibt semantische
Coverage. Sie verwendet zuerst eine bereits authored, aber ungetestete
ComponentVersion. Nur wenn keine solche Version existiert, darf der getrennte
Worker-DAG genau einen neuen Challenger über `CoveragePlan → ComponentIntent →
Designer → Lexicalizer → Aspect Proposer/Judge → Validator/WeightPolicy`
erzeugen. Die LLM liefert Semantik und ungewichtete Atome; Zahlen, Klammern,
IDs, Reihenfolge, Availability und Providerarbeit bleiben Codeautorität.

Eine Quest wird weiterhin unmittelbar nach vier eindeutig validierten
ComfyUI-Ingests spielbar. Optionale Bildanalyse ist nachgelagert. Terminale
Vorbereitungen ohne Viererplan und ohne offene Providerarbeit werden append-only
superseded und erhalten genau einen aktuellen Successor; der ursprüngliche
Fehler und bereits gültige technische Resultate bleiben erhalten.
Dieser revisiongebundene Successor besitzt den Zielslot bis zur atomaren
Materialisierung exklusiv. Ein generischer Campaign-Reconcile darf ihm weder
zuvorkommen noch einen zweiten Attempt mit dem ausgeschlossenen Experiment
erzeugen. Jeder tatsächliche Proposer-/Judge-Call besitzt dafür einen eigenen
gefencten Providerbeleg mit exakt demselben versionierten Call-Key und
Requesthash wie das Call-Journal.

## Generischer Component- und Atomvertrag ab Schema 55 / `m6-slotwise-v10`

Die sieben Content-Rollen `character`, `outfit`, `scene`, `pose`,
`expression`, `lighting` und `modifier` verwenden denselben Corridor-,
Child-Version- und Evidence-Vertrag. Je Rolle kann Code ein vorhandenes Atom
neu gewichten, entfernen oder ersetzen, einen vorautorisierten neuen Atomslot
hinzufügen, eine vollständige Aspect Group ersetzen oder bei einer echten
Coverage-Lücke eine neue Component authoren. `style_core` bleibt davon
getrennt: Style-Trials erzeugen Child-`AnimeStyleCoreRevision`en und keine
Playground-Component.

Die Operationswahl ist deterministisch. Direkte Weight-Evidence oder eine
Weight-Frage autorisiert `reweight`; ein eindeutiges negatives Atomsignal
autorisiert `remove` oder `replace`; ein gerichteter Change ohne vorhandenes
passendes Atom autorisiert `add`; eine vollständige Change-Gruppe autorisiert
`replace_group`. Widersprüchliche oder noch unzureichende Evidence darf eine
reproduzierbar geseedete Exploration öffnen, wird aber als unbewiesener Try
gespeichert. Ein neu hinzugefügtes beziehungsweise ersetztes Atom und sein
optimales Gewicht werden nicht im selben isolierten Versuch untersucht.

Jeder Challenger materialisiert vor dem Render eine immutable experimentelle
Child-ComponentVersion mit Parent, exaktem Atom-/Weight-/Group-Diff,
`influence_refs`, Corridor-Acceptance und Recipe-/Arm-Bindung. Unveränderte
Aspect-Gruppen werden vom Parent übernommen. Die globale Component-ID und das
charakterspezifische Lernen bleiben getrennt: Eine Outfit-Version kann global
adressierbar sein, während ihre erste Availability und Evidence nur für Aiko
gelten. Character-Versionen bleiben an ihre Character-Lineage gebunden.

Slot-, Aspect-, Designer- und Lexicalizer-Calls bleiben im kompakten
4.096-Kontextprofil. Der gemeinsame v10-Batch-Judge verwendet dagegen das
gesondert qualifizierte 8.192-Profil. Sein Request überträgt die gemeinsame
Baseline genau einmal und pro Arm nur kompakte Aliasse und den Diff. Der
Preflight erlaubt höchstens 7.200 tatsächliche Inputtokens und reserviert
höchstens 512 Outputtokens; Trunkierung oder ein stiller Profilwechsel sind
verboten.

Ein Produktions-Save benötigt keinen Development-Playground. Fehlt eine
passende Component, läuft der persistierte Pfad `CoveragePlan →
ComponentIntent → Component Designer → Prompt Lexicalizer → Aspect
Proposer/Judge → Validator/WeightPolicy → ComponentVersion →
Availability`. Die LLM liefert Semantik und ungewichtete Atome; Code behält
IDs, Gewichte, Klammern, Reihenfolge, Seeds und Persistenzautorität.

Gerichtete Evidence bleibt observationsgebunden. Positive Reasons erzeugen
nur für ihre Achse `preserve`, negative Reasons nur `change`; beide Richtungen
desselben Reviews bleiben gemeinsam. Ohne positive Human Evidence entsteht
keine positive Referenz. Ein Reject mit positivem Outfit- und negativem
Background-Grund bewahrt damit das Outfit, öffnet den Background für Änderung
und gibt der Gesamtcomposition keinen positiven Credit.

Reconcile und Catalog-Recovery arbeiten edge-triggered. Ein Sweep liest den
aktuellen Zustand und erzeugt ohne neue Zustandsrevision weder einen neuen
schweren Job noch ein identisches Event. Dokumentvektoren werden vor dem
Provideraufruf über Source, Space, Modell, Preprocessing und Content-Hash
wiederverwendet. Dieser implementierte Vertrag bleibt bis zum realen
`5/6 → 6/6 → Review → Follow-up → neuer Viererbatch` unter
`LIVE_VERIFICATION_PENDING`; `M6_LEARNING_LOOP_PROVEN` bleibt unset.

### Stabiler v11-Ausführungspfad unter Schema 58

Experiment und Candidate werden vor Card-, Attempt- und QEC-Erzeugung als ein
gemeinsames Paar gewählt. Der Capability-Resolver prüft die Atome, Gewichte und
Aspect Groups genau der gewählten ComponentVersion und ihres Recipes. Zusätzlich
muss der tatsächliche Panel-Diff den Focus enthalten: eine Identity-Frage
benötigt einen Character-Diff, eine Scene-Frage einen Scene-Diff und entsprechend
für die übrigen Rollen. Ist das Paar ungeeignet, gilt die begrenzte Leiter:
vorhandenes gültiges Panel, genau eine autorisierte Mutation beziehungsweise
Authoring-Operation, danach die nächste kompatible Experimentfamilie. Ein
Candidate leiht niemals Atome oder Gruppen eines anderen Candidates.

Ein bereits eingefrorener und vollständig validierter Composition- oder
Semantic-Candidate wird als deterministisches `keep_candidate` übernommen.
Evidence-Aliasse und Auswahlgrund stammen aus dem Evidence-Head und werden von
Code in Contract und Trace gebunden; dafür gibt es weder Slot-Proposal-Call noch
Batch-Judge. LM Studio wird nur für `add`/`replace`, Aspect-/Component-Evolution,
neues Component-Authoring oder ein begründetes `abstain` verwendet. Der Judge
läuft nur, wenn mindestens ein Arm eine solche modellgenerierte semantische
Änderung enthält.

`m6-slotwise-v11` bindet pro Challenger eine geordnete Liste ausschließlich
candidate-eigener Mutationstargets. Erschöpft ein Modellcall ein Add-/Replace-
Target, bleiben Control und bereits akzeptierte Arme unverändert; nur der
betroffene Arm wechselt auf das nächste vorautorisierte Target. Erst wenn alle
Targets dieses Candidates erschöpft sind, wechselt die gemeinsame
Experiment-Candidate-Auswahl zur nächsten kompatiblen Route. Ungewöhnliche,
aber strukturell gültige Discovery wird gerendert und vom Spieler bewertet.

Eine geladene LM-Studio-Instanz gilt nur über ihre exakte Runtime-ID als
Chronicle-eigen: entweder ist sie im aktuellen Prozess bekannt oder durch den
persistierten Model-Lifecycle belegt. Ausschließlich eine so belegte konkrete
Instanz darf profilübergreifend entladen werden. Ein bloß ähnlich benannter,
nicht belegter Prozess bleibt fremd und wird nicht verändert.

Paneldiffs und Hashes werden außerhalb von SQLite-Schreibtransaktionen
berechnet. Jeder Materialisierungscheckpoint öffnet eine neue kurze
`BEGIN IMMEDIATE`-Transaktion, prüft Claim, Lane und Epoch und committet vor dem
nächsten rechenintensiven Schritt. Der finale Publish von Plan, vier Slots und
Comfy-Outbox bleibt atomar und gefenct.

Recovery ist zustandsabhängig: ein berechtigt wartender Attempt wird unter
demselben Vertrag fortgesetzt; bereits angenommene Providerarbeit wird nur über
ihre persistierte Provider-ID reattached; ein terminaler unmaterialisierter
Pre-Provider-Attempt ohne Session, Review, Credit oder Providerbilder wird
append-only superseded und erhält genau einen deduplizierten Nachfolger. Ein
terminaler Child-Job darf nicht als aktive Vorbereitung projiziert werden.
Fachliche Focus-/Diff- oder semantische Fehler schließen Route und Signatur für
denselben Evidence-Head aus; rein technische Fehler dürfen einen weiterhin
gültigen eingefrorenen Vertrag wiederverwenden.

Neue Recipes werden unter Prompt Contract v4
(`campaign-v4-canonical-atoms`) aus den kanonischen gewichteten Atomfeldern der
gewählten ComponentVersion kompiliert. Recipe-Occurrences bleiben von den
kanonischen Atom-IDs getrennte immutable Renderbelege und werden für einen
Weight- oder Atomversuch über Phrase, Polarität und eindeutige Kardinalität
zurückgebunden. Eine Abweichung sperrt nur den widersprüchlichen Versuch und
darf weder eine fremde Component-Fähigkeit ausleihen noch den allgemeinen
Supply-Slot blockieren. Die Bezeichnungen Prompt Contract v3 in älteren
Abschnitten beschreiben ausschließlich historische Recipes.

LM-Heartbeats dürfen bei kurzer SQLite-Contention begrenzt und stop-aware
warten. Erst ein belegter Fence-, Epoch-, Lane-, Lease- oder Providerbinding-
Verlust terminalisiert den Call. Runtime-Lesepfade materialisieren keine
fehlenden Promptgraph-Bindungen; solche Integritätslücken werden vor der
Providerarbeit konkret gemeldet.

## Ausgeglichene Experimentmatrix ab Schema 56, Runtime unter Schema 58

Schema 56 führte die folgenden Experiment- und Receipt-Strukturen ein. Es ist
keine aktuelle Runtimeversionsangabe; Schema 58 ist die operative Autorität und
erhält diese additiven Strukturen.

Eine zentrale `ExperimentSpec`-Registry ist die Metadatenautorität für
Experimentkind und -familie, Standardachse, Seed-Policy, Vergleichsdesign,
Evidence-Credit, UI-Erklärung, konstante Felder, Prompt-Machine-Bedarf und das
zulässige Achsenbudget. `build_experiment_route_facts()` liefert ausschließlich
Facts; `select_next_supply_question()` entscheidet die faire Reihenfolge;
`build_experiment_contract()` und `validate_panel_recipe_diffs()` schließen
den gemeinsamen Metadaten- und Diffvertrag. Die konkrete Panelmaterialisierung
bleibt im Batch-Diversity-Pfad, die Credit-Projektion im typisierten
Evidence-Projektor; sie werden nicht als nicht existente Registry-Funktionen
behauptet.

In sechs tatsächlich spielbereit gewordenen normalen Quests erscheinen
mindestens eine Technik-/Seed-, eine Atom-/Weight-/Aspect-, eine
Composition-/Authoring-, eine Coverage- und zwei evidence-gesteuerte Fragen.
Fehlgeschlagene oder supersedete Vorbereitungen zählen nicht. Ein rollierendes
Zwölferfenster gleicht zusätzlich `(experiment_kind, target_role, operation)`
aus. Eine für denselben Evidence-Head und Supply-Slot semantisch ausgeschöpfte
Route ist ausgeschlossen; der Nachfolger wählt die nächste kompatible Familie.

CFG wird als Integer-Tenths und damit auf dem 0,1-Raster persistiert, Steps als
positive Ganzzahl auf dem Einer-Raster. Adaptive `stride_units` verändern nur
den Abstand. Ein CFG×Steps-Interaction-Panel ist ein gepaartes 2×2 und wird
erst nach isolierter Evidence für beide Einzelachsen zugelassen; es erzeugt
nur Interaction-/Combination-Credit. Sampler, Render-Scheduler, Denoise, Seed,
Atom, Einzelgewicht, Aspect-Gewicht, Aspect-Evolution, Composition und
Authoring behalten jeweils eigene Diff- und Credit-Verträge.

Jeder LM-Schritt hinterlässt ein redigiertes, immutable
`ProposalValidationReceipt`: Token-Preflight, Providertransport,
Structured-Output, Entscheidungssemantik, semantische Dublette, Judge,
Recipe-Diff und ComfyUI-Handoff bleiben unterscheidbar. `abstain` ohne Grund
erhält genau eine gezielte Korrektur; äquivalente Mutationen werden anhand ihrer
normalisierten Semantik erkannt. Drei unbrauchbare semantische Antworten
schließen die Route, nicht Candidate oder Component.

Cosine Similarity bleibt für typisierte semantische Quellen aktiv. Rack-Suchen
schließen eine relational gebundene eigene Vector-, Source- oder
Image-Identität automatisch aus. Generische Component-/Atom-Suchen tun dies
nur über explizite Hard Filter wie `excluded_embedding_vector_ids` oder
`excluded_source_refs`; Rang 1 wird nie pauschal verworfen. Image-Racks tragen nur
Human-abgeleitete Rollen `axis_preserve`, `explicit_negative` und
`diagnostic_only`, dienen Nachbarschaft und Neuabdeckung und vervielfachen
keinen Human-Credit. Fehlende Image-Vektoren erzeugen eine Abstention und
blockieren weder Supply noch Quest-Readiness.

## Schema-57-Contention-Grenze

Der fachliche Viererbatch bleibt unverändert, wird aber nicht in einer langen
SQLite-Schreibtransaktion materialisiert. Inputsnapshot, Diffs und Hashes
entstehen außerhalb der Schreibsperre. Child-Components, Corridors, Recipes und
Promptgraph-Bindungen werden über stabile IDs einzeln checkpointet. Erst der
erneute Claim-, Hash- und Epoch-Check veröffentlicht Plan, vier Slots,
Attempt-Bindungen und Comfy-Outbox atomar. Ein Crash verwendet vorbereitete
Artefakte wieder; vor dem Publish besitzen sie keine Readiness- oder
Evidence-Autorität.

Der Reviewabschluss speichert nur unveränderte Spielerfacts, Sessionrevision,
gegebenenfalls Quest Credit, Evidence-Watermark, erweitertes
Idempotenzresultat und genau einen `campaign_review_project`-Auftrag. Der
Coordinator projiziert anschließend Evidence, Knowledge, Monitoring, Racks und
Follow-up. Ein Fehler dieses Projektionsjobs kann weder den abgeschlossenen
Review zurückrollen noch Ready-Quests anderer Campaigns sperren.

Hintergrund-Schreibtransaktionen besitzen ein beobachtbares Zielbudget von
250 ms. `SQLITE_BUSY` innerhalb des kurzen, begrenzten Heartbeat-Retryfensters
gilt als Contention; ein falscher Claim-Token oder eine abgelaufene Runtime-
Epoch bleibt sofort fail-closed. Catalog Recovery berechnet Dateideltas vor dem
Write und committet nur tatsächliche Änderungen in kleinen Einheiten.

Status: **IMPLEMENTED / LIVE VERIFICATION PENDING**. Automatisiert belegt sind
atomarer Review-/Outboxcommit, Idempotenzkonflikt, gestaffelte
Planmaterialisierung, transienter Busy-Retry, query-only Lean-Projektion und
reaktiver kampagnenlokaler DOM-Refresh. Offen bleiben der reale
Contention-/Restart-Beleg und zwei vollständige Review-/Follow-up-/Viererbatch-
Zyklen. `M6_LEARNING_LOOP_PROVEN` bleibt unset.
