> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/deck-building-embeddings-and-llm-context.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Bildkarten, Embeddings und LLM-Kontext

Dokumentrolle: fachlicher MVP-Produkt- und KI-Integrationsvertrag

Autorität: autoritativer Zielvertrag für den Human-first-Image-Lernloop,
Embedding-/Retrieval-Semantik und rollenreine LLM-Context-Packs

Stand: 12. September 2026

Status: **DECIDED** für den Human-first-Grundvertrag und die initialen
Modellkandidaten; gepinnte Revisionen, Schwellen und eine mögliche spätere
Pre-Review-Image-Embedding-Prüfung bleiben **CALIBRATE** beziehungsweise
**DEFERRED**.

Der getrennte Vertrag für bereits bewerteten Entwicklungsbestand steht in
[`historical-reference-bootstrap-and-evaluation.md`](historical-reference-bootstrap-and-evaluation.md).
Ein vorhandenes Bild oder Review erzeugt allein keine Analysearbeit: VLM-,
Text- und Image-Arbeit entsteht ausschließlich aus einem expliziten
`image_analysis_enrollment`. Der 30-Sekunden-Sweep reconciliiert offene
Enrollments und entdeckt keinen Altbestand.

Dieses Dokument verbindet den visuellen Bildkarten- und Lernloop aus
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md),
die KI-Provider aus
[`llm-rag-and-recovery.md`](llm-rag-and-recovery.md) und den Arbeitsvertrag aus
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md).
Es ersetzt keine dieser Fachdomänen. Es legt fest, wann aus Human-Evidence
Bildvektoren entstehen, wie sie Karten-, Titel- und Entwicklungsplanung
unterstützen und welcher
begrenzte Kontext ein LLM erreichen darf.

## Schema-48-Atom- und Component-Retrieval

Zusätzlich zu den bestehenden Räumen werden ausschließlich semantische
`component_text`-Dokumente mit stabiler `component_version_id` und
`prompt_atom_text`-Dokumente mit Konzept, Rolle und Polarität vektorisiert.
Numerische Gewichte, Ratings, Confidence, einzelne Legacy-Vorkommen und
kartesische Combozeilen werden nicht eingebettet.

Ein explizit akzeptierter Development-Import erhält pro Campaign eine eigene
`proof_eligible=false`-Cohort. Runtime-fresh und Development-Vektoren werden in
getrennten Indexrevisionen gesucht und erst über Receipt-Ränge zusammengeführt.
Der verwendete Import-Run, die Cohort und die Binding-Signatur werden mit dem
Lerninput eingefroren. `fresh_proof` löst diese Bindung unabhängig von der
Campaign-Einstellung niemals auf.

Bestätigte oder korrigierte Bildbeschreibungen können passende Komponenten und
Atome auffinden. `full_frame_semantic` und `style_view` liefern nur
Same-Space-Nachbarn. Diese maschinellen Signale bleiben Retrievalhilfe; sie
erzeugen weder Score noch Disposition, Reason oder Atom-Credit.

### Schema-53-Quellen-, Index- und Rackvertrag

Schema 53 typisiert die bestehende `embedding_vectors`-Domäne in-place. Jede
aktive Dokumentvektorzeile verweist über `embedding_sources` auf genau einen
relationalen Ursprung: ComponentVersion, Atomkonzept, Recipe, bestätigte
Bildbeschreibung, Image, ChampionSlot, ComparisonContext oder einen ausdrücklich
nicht proof-fähigen HistoricalSnapshot. Space, Modell, Dimension,
Normalisierung und Preprocessing sind durch eine immutable
`embedding_space_revision` gebunden. Derselbe semantische Inhalt wird pro
Source, Space, Modell, Preprocessing und Content-Hash nur einmal eingebettet;
Campaign-, Character-, Scope- und Cohort-Verfügbarkeit wird durch
Indexmitgliedschaft und Context-Bindung ausgedrückt, nicht durch duplizierte
Vektoren.

Retrievalqueries und Queryvektoren sind eigene persistierte Entitäten. Sie sind
nie Mitglieder eines Dokumentindex. Die relationale Belegkette lautet:

```text
Entity
→ EmbeddingSource
→ Dokumentvektor
→ IndexMember
→ RetrievalCandidate
→ Selection
→ ContextPackReceipt und ContextPackSource
```

Ein aktiver Index darf keine synthetische Component-ID, kein fehlendes
Contextziel und keinen Queryvektor enthalten. Nicht eindeutig auflösbare
Altquellen bleiben HistoricalSnapshots und werden nicht in aktive Indizes
aufgenommen. Ein leerer `unavailable:image-model`-Index wird als typisierte
Abstention statt als aktiver Suchraum projiziert. World Canon, Memories und
Character Knowledge bleiben `not_materialized`, bis eine veröffentlichte
relationale Source-Revision existiert.

Die bestehenden `image_reference_set_revisions` und
`image_reference_set_members` sind die einzige Bild-Rack-Projektion. Ihre
Lineage bindet Image, AttemptImage, Review beziehungsweise Evidence, Recipe,
CompositionUse und optional den passenden Image-Vektor. Positive, negative,
Champion- und diagnostische Rollen bleiben getrennt. Ein
HistoricalReferenceRun belegt nur die Veröffentlichung; er ist nicht selbst der
Rack-Inhalt. Racks und Indizes sind vollständig rebuildbar, während Reviews,
Recipes, Components und Evidence Primärdaten bleiben.

## Verbindlicher Runtime-Katalog-Kreislauf

Der Katalog besitzt zwei ausdrücklich getrennte Betriebsarten, aber nur einen
Komponentenvertrag:

| Betrieb | Inhalt am Start | Herkunft neuer `ComponentVersion`en |
|---|---|---|
| M6-Entwicklung | vorhandener Playground als explorativer Testkorpus | ausgewählte Zeilen werden lazy als `development_import` gebunden; akzeptierte Promptvariationen werden als `ai_authored` Child-Versionen zurückgeführt |
| finales Produkt | inhaltlich leerer persönlicher Playground | lokale KI-Rollen erzeugen Character-, Outfit-, Scene-, Pose-, Expression-, Lighting- und Modifier-Kandidaten aus Coverage- und Character-Intents |

Import und KI-Vorschlag durchlaufen denselben Validator und deterministischen
Materializer. Beide besitzen SemanticSpec, positive und negative ungewichtete
Atome, deterministisch vergebene Gewichte, Herkunft, Character-/Scope-/Canon-
Bindung sowie bei Änderungen Parent und exakten Diff. Die LLM darf weder IDs
noch Gewichte vergeben und schreibt niemals direkt in Playground oder DB.

Für neue Vorbereitungen ab Schema 47 gilt ergänzend der
[rollierende Lernloop](rolling-m6-learning-loop.md): gemeinsame Kandidatenplanung,
eingefrorene Eingangsmanifeste, tatsächlich übertragene Human-Evidence und
source-/hashgebundenes Resume. Alte Ein-Achsen-Verträge gelten für isolierte
Diagnose, nicht pauschal für jeden Folgeversuch.

Ein neuer Save besitzt von Beginn an das versionierte Playground-Schema, aber
noch keine persönlichen Komponenten-, Combo-, Rating- oder Embedding-Zeilen.
„Leerer Store“ bedeutet deshalb **Schema vorhanden, Inhalte nicht vorhanden**.
Die Prompt Machine baut diesen Bestand im Spielverlauf auf; die LLM selbst
besitzt dabei keinen direkten Schreibzugriff auf die Datenbank.

```text
PersonalContentCoveragePlan beziehungsweise Entwicklungs-CoveragePlan
→ ComponentIntent
→ SemanticSpec
→ Component Designer erzeugt SemanticSpec
→ Prompt Lexicalizer erzeugt ungewichteten PromptAuthorProposal
→ Judge akzeptiert, revidiert oder enthält sich
→ deterministischer Validator prüft Schema, Rollen, Tokens, Grenzen und Konflikte
→ deterministischer Materializer normalisiert, vergibt IDs und numerische Gewichte
→ revisionierte Playground-Komponente im aktuellen Save
→ Generation mit vollständiger Recipe-Provenienz
→ Human Review und unveränderliche Evidence
→ deterministische Credit-, Confidence- und Recovery-Projektionen
→ rebuildbarer Textindex der akzeptierten Runtime-Inhalte
→ Retrieval-Kandidaten für den nächsten rollenreinen ContextPack
→ nächster kontrollierter Vorschlag
```

Die heute vorhandene Playground-Datenbank ist Entwicklungskorpus, nicht die
erste Produktdatenbank. Die vier ausdrücklich als Entwicklungskampagnen
betriebenen M6-Campaigns dürfen sie als Suchraum lesen. Materialisiert werden
jedoch nur tatsächlich ausgewählte Zeilen lazy und mit Source Receipt. Bei einem
normalen neuen Produkt-Save wird der Korpus weder automatisch gesichtet noch
vektorisiert. Wenn vorhandene Daten dort ausnahmsweise verwendet werden sollen,
geschieht das durch einen ausdrücklich gestarteten Import:

```text
ausgewählte Bestandszeile
→ ImportCandidate mit Source Receipt
→ derselbe Validator und Materializer wie bei einem LLM-Kandidaten
→ revisionierte Runtime-Zeile im aktuellen Save
→ rebuildbarer Textindex
```

Ein Import darf den leeren Start beschleunigen, verleiht einer Zeile aber keine
automatische Qualitäts-, Canon-, Credit- oder Promotion-Autorität. Historische
Ratings bleiben Legacy-Priors und sind nur zulässig, wenn der Importvertrag sie
ausdrücklich übernimmt. Fehlerhafte oder nicht zum Zielschema passende Zeilen
werden abgelehnt oder in eine sichtbare Import-Quarantäne gelegt; das
Runtime-Schema wird nicht an den Altbestand angepasst.

Im Entwicklungsbetrieb muss jede zulässige Komponente zunächst mindestens einen
Figurentest erhalten. Solange ungetestete Katalogbereiche existieren, plant der
Scheduler mindestens jede dritte normale Folgequest als semantische Coverage-
Frage. Der persistente Campaign-/Scope-Cursor rotiert Scene-/Outfit-
Kombinationen und den gemeinsamen Pose-/Expression-/Lighting-Stützkontext, ohne
ein kartesisches Vollprodukt zu erzeugen. Gute Aiko-Evidence macht eine Uniform
oder einen Ort nicht global gut: Cross-Character-Evidence bleibt getrennt und
erzeugt höchstens einen Blueprint-Kandidaten. Blueprint, Canon und Promotion
benötigen weiterhin eine ausdrückliche Human-/Canon-Entscheidung.

Text-Embeddings sind eine rebuildbare Projektion der bereits validierten und
materialisierten Runtime-Zeilen. Kosinusähnlichkeit darf nach harten Save-,
Character-, Rollen-, Scope- und Compatibility-Filtern semantisch ähnliche
Komponenten als Retrieval- oder Dubletten-Kandidaten finden. Sie darf Zeilen
nicht automatisch zusammenführen, Gewichte ändern oder fachliche Gleichheit
behaupten.

VLM-Beschreibungen verwenden einen eigenen Textpfad. Rohtext wird als
diagnostische `ImageDescriptionRevision` gespeichert und bleibt zunächst vom
Referenz-Retrieval ausgeschlossen. Die derzeitige Bestands-/Adminpipeline kann
eine Revision weiterhin explizit mit `confirm`, `correct` oder `dismiss`
abschließen. Im Ziel-Spielerablauf geschieht diese Prüfung jedoch nicht als
Zusatzformular im normalen Bildreview, sondern über mehrere Zuordnungen im
eigenständigen Zwei-Bild-Beschreibungstest. Erst die daraus rebuildbar als
tragfähig eingestufte oder ausdrücklich administrativ bestätigte Revision darf
mit Qwen3-Embedding-0.6B einen 1024-dimensionalen, L2-normalisierten Vektor im
Raum `machine_image_description_text` erhalten. Diese Vektoren setzen niemals
Bildbewertung, Prompt-Credit, Champion- oder Canonstatus.

Für die Bildkartenprojektion bleiben drei Texte ausdrücklich getrennt:

1. VLM-Rohbeschreibung mit Modell-, Prompt-, Schema- und Sprachprovenienz,
2. vom Spieler bestätigte oder korrigierte semantische Bildbeschreibung,
3. daraus erzeugte lokalisierte und gekürzte Karten-Copy.

Nur die zweite Ebene darf eine aus administrativer Bestätigung oder mehreren
Beschreibungsmatches abgeleitete Human-Validierung tragen; die dritte ist eine
austauschbare Frontendprojektion. Keine Ebene ersetzt den ursprünglichen
Generierungsprompt oder den versionierten Expected-Composition-Vertrag. Eine
englische Rohbeschreibung darf nicht ungeprüft als deutscher Kartenname oder
als kanonische Aussage erscheinen. Das Match- und Herkunftsschema ist in diesem
Vertrag festgelegt; konkrete VLM-Unterfelder, Mindestzahl/Schwellen der
Paarungen, eine mögliche „nicht eindeutig“-Aktion und der Lokalisierungsworkflow
bleiben versionierte Kalibrierung.

### Relationale Herkunft einer Beschreibung

Beschreibung, Bild, Generierung und Datei-Lebenszyklus sind keine getrennten
Informationsinseln. In der autoritativen Runtime-Datenbank muss jede
DescriptionRevision über stabile Schlüssel vollständig auflösbar sein:

```text
image_description_revision_id
→ machine_image_observation_id
→ attempt_image_id + image_id
→ attempt_id → challenge_id → campaign_id/Character/Content Scope
→ generation_recipe_id → Prompt-, Component-, Workflow-, Modell- und Renderrevision
→ image_id → Pfad-/Hashhistorie, available, deleted_at und Löschentscheidung
```

Normalisierung bedeutet dabei, dass nicht jede Tabelle `character_name`, Prompt
und Dateipfad erneut kopiert. Sie trägt den fachlich nächsten Primär-/Fremdschlüssel
und friert nur die für Replay nötigen Snapshots und Signaturen ein. Auch ein
physisch gelöschtes PNG/JSON-Paar behält seine `image_id`, seine Herkunft und
seine strukturierte Evidence. `available=0` verhindert lediglich eine erneute
Anzeige oder Auswahl.

Der Beschreibungstest benötigt darauf aufbauend einen expliziten relationalen
Vertrag statt loser IDs in JSON: DescriptionRevision, Quellbild, Gegenbild,
Character-/Scopebindung, Pool-Snapshot, Difficulty-/Pairing-Policy und die
Spielerinteraktion werden über Foreign Keys und immutable Events verbunden.
Rebuildbare Similaritywerte referenzieren zusätzlich Modell-, Embedding-Space-,
Index- und Preprocessingrevision. Polymorphe `source_kind/source_id`-Verweise
dürfen als technische Projektion bestehen, ersetzen für diesen Kernpfad aber
keine geprüfte Fremdschlüsselbeziehung.

Diese Verknüpfung ersetzt nicht das VLM-Beobachtungsschema. Bereits bekannte
Provenienz wie `image_id`, Character, Content Scope, Prompt, Seed, Recipe,
Workflow, Modellbindung, Pfad und Dateistatus wird von der Pipeline gebunden und
darf vom Worker weder erneut abgeleitet noch als Wahrheit zurückgeschrieben
werden. Der Worker liefert ausschließlich sichtbare Befunde, die nicht aus dem
Generierungsvertrag folgen. Das Zielschema trennt mindestens:

- sichtbare Figuren und Anzahl,
- beobachtbare Character-Merkmale ohne Altersinferenz,
- Outfit und Accessoires,
- Szene beziehungsweise Ort,
- Tätigkeit, Pose und Interaktion,
- Ausdruck und Blickrichtung,
- relevante Gegenstände,
- Bildausschnitt, Kamera/View und Komposition,
- Licht und sichtbaren Stil,
- technische beziehungsweise anatomische Auffälligkeiten,
- feldbezogene Unsicherheiten,
- sowie eine daraus gebildete englische Kurzbeschreibung.

Jeder Befund bleibt Bestandteil der versionierten `observation_json`; das
Schema, die Worker-/Modellrevision und der zugrunde liegende Providerjob stehen
bereits in eigenen referenzierten Zeilen. Der heute implementierte Minimalstand
aus `description`, globalen `uncertainties`, `reason_code_suggestions` und
`confidence` ist deshalb relational angebunden, aber inhaltlich noch nicht
feingranular genug für kontrollierte Gegenbildwahl und Fehleranalyse.

Jeder Vektor und jeder logische Index trägt eine `analysis_cohort_id`.
`runtime_fresh` und `historical_reference` werden weder gemeinsam gerankt noch
in derselben Indexrevision materialisiert. Historische Indizes sind nur nach
akzeptiertem Bestandsreferenz-Bericht opt-in-fähig und bleiben aus M6-Proof-
Receipts ausgeschlossen.

## Verbindlicher Human-first-Lernloop

Image Embeddings beurteilen keine ungesehenen Rohbilder im initialen
Produktpfad. Der erste Erkenntniszyklus besitzt vier fachliche Schritte:

```text
1. Contract und Try
   → ChampionSlot, VisualSpec, Locked/Varied Axes und Bewertungsfrage einfrieren
   → genau deklarierte Prompt-, Prompt-Weight-, Seed-, Sampler-, Scheduler-,
     Steps-, CFG-, Workflow- oder andere zulässige Variation erzeugen

2. Generation
   → vergleichbaren Viererbatch mit vollständiger Recipe-Provenienz rendern
   → keine Image-Embedding-Prüfung vor dem Human Review

3. Human Review
   → Pass 1: Favorite | Keep | Reject | Skip pro Bild
   → Pass 2: positive und negative Reason-Evidence pro Bild und Achse
   → vorgesehene Set-, Pairwise- oder Rankingentscheidung abschließen

4. Projektion und Beobachtung
   → Raw Evidence unverändert persistieren
   → Ratings, Credit, Stability- und Recovery-Projektionen deterministisch bauen
   → erst jetzt scopegebundene Image-Embedding-Jobs autorisieren
   → daraus den nächsten kontrollierten Try planen
```

Ein sauberer Save beginnt ohne Bilder, Bildvektoren, Referenzprototypen oder
Anchor Sets. Ein transportgültiges, kontextkompatibles `Favorite`, eine
scopekompatible `APPROVED ChampionRevision` oder ausdrücklich kompatibles
Legacy-Referenzmaterial darf die erste `ImageAnalysisBootstrapRevision` dieses
Scopes erzeugen. Favorite und Champion sind für diese Referenzfreigabe
gleichwertig. `Keep` ist positive Human-Evidence, aber allein kein
Bootstrap-Schlüssel; nach erfolgter Freigabe darf es als vorläufig positive
Beobachtung in den passenden Raum eingehen.

Eine vorhandene scopekompatible `APPROVED ChampionRevision` kann bei Rebuild,
Migration oder späterer Erweiterung ebenfalls Referenzmaterial liefern. Sie ist
kein Ersatz für den Human-first-Start, sondern selbst Ergebnis des
Human-in-the-loop-Wettbewerbs. Kompatibles Legacy-Material bleibt auf
ausdrücklich Legacy-fähige Entwicklungs- oder Importkontexte begrenzt.

## Reviewzustand und Embedding-Berechtigung

Disposition, achsenspezifische Beobachtung und Referenzrolle sind getrennt:

| Human-Zustand | Image-Embedding-Berechtigung | mögliche Rolle |
|---|---|---|
| noch nicht gezeigt oder laufender Review | nein | keine |
| `Skip` ohne sichere Beobachtung | nein | keine |
| abgeschlossenes `Keep` | ja, nach Bootstrap | vorläufig positive, scopegebundene Beobachtung und Kandidatenreferenz |
| abgeschlossenes `Favorite` | ja, nach Bootstrap | starke positive, scopegebundene Beobachtung und Kandidatenreferenz |
| begründetes `Reject` | nur nach Bootstrap und nur mit vollständiger achsenspezifischer Evidence | negative Diagnose, Fehler- oder Wrong-Style-Cluster; niemals positive Gesamtreferenz |
| `APPROVED ChampionRevision` | ja | validierte Wettbewerbsreferenz für ihren Slot und kompatible Scopes |
| `Delete` | nicht mehr als positive Referenz | während Quarantäne höchstens negative Evidence; bei physischer Löschung werden Bildvektoren entfernt |

Die globale Disposition wird nicht auf jede Achse kopiert. Ein wegen kaputter
Hände abgelehntes Bild kann eine positive Style-Beobachtung enthalten, bleibt
aber als Asset und positive Gesamtbildreferenz ungeeignet. Umgekehrt erzeugt
nur ein expliziter Human-Grund wie `wrong_artstyle` negative Style-Evidence. Ein
allgemeines Reject darf nicht automatisch einem Wrong-Style-Cluster zugeordnet
werden.

Referenzsets entstehen ausschließlich aus solchen gespeicherten Human-
Beobachtungen und bleiben revisioniert:

```text
ImageReferenceSetRevision
├─ reference_role: style_positive | style_negative | identity_positive
│                  | recovery_positive | recovery_negative | slot_candidate
├─ character-, slot-, asset-, canon-, time- und content_scope
├─ source_review_event_ids[]
├─ source_image_ids[]
├─ evidence_cutoff_event_id
├─ membership_reason je Bild und Achse
├─ strength: provisional_keep | favorite | approved_champion
└─ status: active | superseded
```

Die Stärke darf Retrieval und Diagnose beeinflussen. Sie erzeugt keine
Preference-, Champion-, Canon-, Stability-, Readiness- oder Safety-Autorität.

## Getrennte Bildräume und ihre Funktion

Ein Bild besitzt nicht „seinen einen Embedding-Score“. Jeder Vergleich bindet
Aufgabe, Raum, Crop, Referenzset und Kalibrierungsrevision.

| Raum oder Befund | initiale Aufgabe | zulässige Wirkung |
|---|---|---|
| `source_hash` | byteidentische Datei erkennen | technische Deduplizierung; kein Embedding |
| `full_frame_semantic` | globale Bildähnlichkeit, Control-/Challenger-Delta, mögliche Near-Duplicates | Kandidaten sortieren, Clone-Hunt oder Review priorisieren |
| `style_view` | Style Drift innerhalb des AnimeStyleCore und der persönlichen Style-Baseline | Style-Recovery oder Reviewhinweis |
| `character_crop` | Single-Character-Identity über Seeds, Outfits und Kontexte | Identity Drift oder passende Referenzen markieren |
| `face_crop`, `outfit_crop`, `background_crop` | spätere spezialisierte Retrieval-/Diagnoseaufgaben | erst nach eigenem Provider-, Crop- und Fixture-Nachweis aktivieren |
| `anime_attribute_findings` | ergänzende strukturierte Attribute und sichtbare Fehler | Monitor-/Recovery-Hinweis; kein Embedding-Raum und keine Wahrheit |

Der erste Bake-off prüft Google SigLIP2 für `full_frame_semantic` und
`style_view` sowie CCIP für `character_crop`. Dasselbe SigLIP-Vektorfeld darf
nicht ohne aufgabenbezogene Referenzsets als verlässlicher Einzeltest für Style,
Pose, Outfit, Komposition und Qualität ausgegeben werden. Exakte Duplikate
werden per Source Hash erkannt; Near-Duplicate-Erkennung benötigt zusätzlich
projektbezogene Fixtures und darf bei Bedarf um einen separaten perceptual-
Hash- oder Pixelvergleich ergänzt werden.

Bei Mehrfigurenbildern erhält jede deterministisch zugeordnete Figur einen
eigenen Identity-Crop. Der Full-Frame-Vektor ersetzt weder Participant-Mapping
noch die getrennte Composition-QA.

## Kosinusvertrag

Retrieval-Vektoren werden L2-normalisiert gespeichert. Innerhalb eines
kompatiblen Raums gilt daher:

```text
cosine_similarity(a, b) = dot_product(a, b)
```

Kosinusähnlichkeit ist weder Gleichheit noch Wahrscheinlichkeit oder Qualität.
Ein Wert darf nur verglichen werden, wenn mindestens Raum, Modell-ID,
Modellrevision, Dimension, Preprocessingrevision und Normalisierung identisch
sind. Ein Modellwechsel erzeugt eine neue Indexrevision und überschreibt keine
alten Vektoren still.

Ein universeller Grenzwert wie `0.80 = relevant` ist unzulässig. Pro Modell,
Raum und Aufgabe wird mit Human-gelabelten Projektfixtures eine versionierte
`SimilarityPolicyRevision` kalibriert. Je nach Frage werden unterschiedliche
Auswertungen verwendet:

- **Top-K:** passende bereits beobachtete Bilder oder Recovery Cases finden,
- **relative Margin:** positives Referenzset gegen ein Human-gelabeltes
  negatives Set abgrenzen,
- **Variationskorridor:** zu ähnliche, sinnvoll verschiedene und möglicherweise
  gedriftete Control-/Challenger-Paare unterscheiden,
- **Cluster und Diversität:** redundante oder ungewöhnliche Gruppen für eine
  menschliche Prüfung sichtbar machen.

Beispielhafte diagnostische Margins sind:

```text
Style Margin
= robuste Ähnlichkeit zu Human-bestätigten positiven Style-Beobachtungen
- höchste Ähnlichkeit zu Human-bestätigten Wrong-Style-Clustern

Identity Margin
= robuste Ähnlichkeit zu kompatiblen Referenzen derselben Figur
- höchste Ähnlichkeit zu Human-bestätigten Referenzen anderer Figuren
```

Median, Top-K-Mittel, negative Vergleichsgruppe, Grenzwerte und
Abstentionskorridor sind Teile der Policy-Revision und keine versteckten
Konstanten. Ein einzelnes Durchschnittsbild ist weder Style Canon noch
Character Canon.

Text- und Bildscores sowie Scores unterschiedlicher Bildräume werden nicht roh
addiert. Nach harten Filtern darf die erste Implementierung rankbasierte Fusion,
beispielsweise Reciprocal Rank Fusion, verwenden. Jede Fusion speichert ihre
Signalränge und Policy-Revision.

## Beitrag zu Karten-, Titel- und Entwicklungsbedarf

Der Bedarf entsteht deterministisch aus ChampionSlots, Kartenbestand,
Stability-Lücken und AssetProductionContracts, nicht aus Embeddings. Ein
fehlender Titelkontext, `n/16`, eine offene Stability-Frage oder ein Assetbedarf
löst einen begründeten Try aus. Im initialen Human-first-Pfad gilt:

```text
Entwicklungsdefizit
→ kontrollierten Try mit Prompt-, Weight-, Seed- oder Renderparameter-Variation planen
→ BatchDiversityPlanRevision mit vier focusgebundenen Anzeigeslots validieren
→ Carried Images unverändert binden und null bis vier neue Recipe-Slots ohne
  Image-Embedding-Vorprüfung rendern
→ VLM-Einzelbeschreibungen und vorläufige BatchDiversityObservation anzeigen
→ Human Review und achsenspezifische Evidence
→ Keep/Favorite für den gebundenen Slot qualifizieren
→ reviewed Images nach Bootstrap einbetten
→ technischen Recipe-/Seed-Reuse von Prompt-/Modellkonvergenz trennen
→ post-review mögliche Mehrfachverwendung für andere kompatible Slots vorschlagen
→ neue Fragestellung erneut vom Menschen bestätigen lassen
→ bestätigte Eligibility zählt Richtung 16er-Roster
```

Embeddings dürfen nach dem Review:

- ein bereits bewertetes Bild als Kandidat eines weiteren kompatiblen Slots
  vorschlagen,
- zu geringe oder unkontrollierte Variation für den nächsten Try markieren,
- ähnliche positive Referenzen und verschiedene Seeds für Recovery oder
  Generation abrufen,
- Clone-Hunt, Dataset Draft und Deck-/LoRA-Diversität unterstützen,
- sowie Style- und Identity-Drift über neue Human-Runs beobachten.

Die VLM-Vorabbeobachtung darf denselben Batch bereits vor dem Review als
`batch_collapse_suspected` erklären, aber nicht quantifizierte Image-Embedding-
Autorität vortäuschen. Ein Batch-Collapse ist zunächst eine Diagnose der
sichtbaren Slotvariation. Erst raum- und revisionskompatible post-review
Image-Embeddings ergänzen Distanz, Cluster und Variationskorridor. Beide Signale
fließen nur in den nächsten versionierten Planner-Try; kein Provider startet
selbst eine Ersatzgeneration.

Sie dürfen keine kontextgebundene Qualification oder Observation erfinden. Das
16er-Roster friert weiterhin die ersten sechzehn bestätigten, unterschiedlichen
Images in stabiler Eligibility-Reihenfolge ein. Ein Embedding-Ranking darf es
nicht nachträglich umsortieren oder vermeintlich bessere Bilder einschleusen.

## Text Embeddings und multimodale Grenzen

Die LM-Studio-Text-Embeddings besitzen getrennte Räume:

- `memory_text`,
- `component_text`,
- `visual_spec_text`,
- `recipe_text`,
- und eine lesbare, typisierte Repräsentation von ChampionSlot- und
  ComparisonContext-Verträgen.

`recovery_case_text` ist seit `rolling-m6-v2` kein aktiver Raum. Begründete
Rejects werden als normale negative Human Evidence im passenden fachlichen Raum
geführt; sie eröffnen keine eigene Recovery-Domäne.

Sie finden nach harten Save-, Character-, Canon-, Zeit-, Relationship-,
Visibility-, Content-, Slot- und Compatibility-Filtern relevante Textquellen.
Locked Canon und Current State werden direkt geladen und nie durch Retrieval
ersetzt.

Initialer Text-Embedding-Default ist Qwen3-Embedding-0.6B mit festen 1024
Dimensionen, L2-Norm, CPU-first-Betrieb und raumspezifisch versionierten
englischen Retrieval-Instructions. Das operative Execution Profile verwendet
8192 Kontexttokens und Parallelität 4. Dokumente werden je Raum in stabilen,
mit dem tatsächlich geladenen Provider-Tokenizer gemessenen Seiten von
höchstens 32 Einträgen und 8192 Tokens verarbeitet. Queries laufen je Raum als
eigener `input_kind=query`-Call; Dokumente und Queries werden nicht gemischt.
Eine überlange Einzelquelle wird nicht gekürzt und löst keinen automatischen
32k-Profilwechsel aus. Nach Output-Ingest darf der getrennte
Docker-VLM-Pfad mit Huihui Qwen3-VL 8B Instruct Abliterated in gepinnter
4-Bit-Revision bereits vor dem Human Review eine schemaförmige
`MachineImageObservation` erzeugen. Deren Beschreibung darf im passenden
Text-Raum nach der erforderlichen Match-/Adminvalidierung indexiert und im
eigenständigen Beschreibungstest gezeigt werden. Das ist keine Image-Embedding-
Vorprüfung: Der VLM-Text darf weder Ranking noch Reihenfolge, Eligibility,
Keep/Favorite, Champion, Canon oder Readiness setzen. Mehrere Zuordnungen
erzeugen ausschließlich DescriptionMatchEvidence; die normale Bildbewertung
bleibt davon unberührt.

Falls später SigLIPs Textencoder für Text-zu-Bild-Retrieval qualifiziert wird,
bildet er einen eigenen multimodalen SigLIP-Raum. Sein Textvektor ist kein
LM-Studio-RAG-Vektor. Nur Text- und Bildrepräsentationen derselben verifizierten
multimodalen Modellrevision dürfen dort verglichen werden. Diese Capability ist
nicht automatisch Teil des ersten Image-Embedding-Workers.

## Rollenreines LLM-Context-Pack

Retrieval übergibt einem LLM keine Datenbank und keine freie Liste von
Ähnlichkeitstreffern. Ein `ContextAssembler` baut nach Guardian-Autorisierung ein
kleines, rollenreines `ContextPackManifest`:

```text
ContextPackManifest
├─ context_pack_id, role und task_contract_id
├─ WorkIntent- und NextWorkDecision-ID
├─ gebundene Save-, Slot-, Canon-, Rules- und Policy-Revisionen
├─ direkt geladene harte Facts und Locks
├─ Retrieval-Queries und harte Filter
├─ ausgewählte Source-IDs, Ränge und Retrieval-Receipt-IDs
├─ Embedding-Raum, Modell-, Index- und Similarity-Policy-Revision
├─ explizite unknown-, absent- und forbidden-Felder
├─ Tokenbudget und Context-Hash
└─ erlaubtes Output-Schema und erlaubte Folgefunktion
```

Ein Prompt Author erhält beispielsweise VisualSpec, Slotrevision, Locked/Varied
Axes, aktuelle Human-Evidence, kompatible Recipes und ausdrücklich erlaubte
Recovery Routes. Er erhält weder versteckte Storywahrheit noch die Autorität,
Gewichte, IDs, Slotzugehörigkeit oder Championstatus zu setzen. Der Character
Speaker erhält dagegen nur authored Conversation-, Knowledge-, Relationship-
und Visibility-Kontext; Bild-Retrieval gehört dort nur hinein, wenn der
Conversation Contract ausdrücklich über sichtbare Appearance sprechen darf.

Für M6-Promptarbeit wird Human Evidence als gerichtete Observation injiziert.
Ein Review bleibt die Klammer um Gesamt-Disposition sowie alle positiven und
negativen Reasons. Positive Reasons sind Preserve-Constraints, negative Reasons
Change-Constraints; eine fehlende Achsenbewertung bleibt unbekannt. Ein
positiver Teilgrund eines Rejects ist deshalb keine positive Bild- oder
Composition-Evidence.

Component- und Atomvektoren transportieren ausschließlich semantische
Ähnlichkeit. Disposition, Reason-Polarität, Character-Eignung, Confidence,
Ratings und Gewichte bleiben relationale Filter- und Rankingdaten. Ein Treffer
ohne positive Human Evidence kann nur Change-Beispiel oder unbewertetes
Explorationstarget sein, niemals positive Referenz. Die Prompt Machine erhält
die reviewgebundene Richtung; der Judge sieht dieselben Aliasse und keine
zusätzliche Retrievalquelle.

## Guardian-Kette

Jeder KI-Schritt ist ein eigener begrenzter Auftrag:

```text
fachlicher Deck-, Trial- oder Recovery-Bedarf
→ WorkIntent materialisieren
→ Guardian prüft Human-Review-, Scope-, Revisions- und Capability-Gates
→ gegebenenfalls genau einen Image-/Text-Embedding-Job autorisieren
→ Ergebnis validieren und Retrieval-Projektion rebuilden
→ neue Guardian-Entscheidung
→ genau eine Retrieval-/Context-Pack-Erstellung autorisieren
→ neue Guardian-Entscheidung
→ genau einen schema-gebundenen LLM-Call autorisieren
→ Ergebnis als Proposal validieren
→ neue Guardian-Entscheidung
→ gegebenenfalls genau eine Generation autorisieren
→ Human Review eröffnet den nächsten Lernzyklus
```

Kein Embedding-Worker, Retriever, LLM oder Provider startet den Folgeschritt
selbst. Monitoring zeigt zusätzlich Bootstrapzustand, Review-Cutoff,
Indexrevision, Referenzset-Freshness, fehlende Human-Labels,
Similarity-Policy-Revision und Abstention an.

## Spätere Pre-Review-Prüfung

Eine Vektorprüfung noch ungesehener neuer Bilder ist **nicht** Teil des
initialen Vertrags. Sie darf erst als neue, ausdrückliche Entscheidung geprüft
werden, wenn:

- der vollständige Human-first-Lernloop stabil und restartfest läuft,
- ausreichend echte Human-Referenzen über mehrere Figuren, Slots, Seeds und
  Content Scopes vorhanden sind,
- False-Positive-, False-Negative-, Scope-Leak- und Starvation-Raten gemessen
  wurden,
- taskgebundene Similarity Policies und Abstention praktisch kalibriert sind,
- und ein Shadow Mode zeigt, was eine Vorprüfung verändert hätte.

Selbst dann beginnt die Einführung read-only. Eine Pre-Review-Projektion darf
weder Bilder löschen noch Reviews überspringen, Keeps/Favorites erzeugen,
Challenger qualifizieren oder Championentscheidungen treffen. Weitergehende
Automatisierung benötigt einen eigenen Requirements-, Decision- und
Abnahmevertrag.

## Testbare Invarianten

1. Kein ungesehenes Bild erhält im initialen Pfad einen Image-Embedding-Job.
2. Der erste saubere Bootstrap benötigt ein kompatibles Favorite; eine
   scopekompatible `APPROVED ChampionRevision` ist gleichwertig. Legacy-
   Referenzmaterial gilt nur in ausdrücklich Legacy-fähigen Kontexten, ein Keep
   allein genügt nicht.
3. Skip erzeugt keine visuelle Beobachtung; Reject erzeugt nur explizit
   begründete negative beziehungsweise achsenspezifische Evidence.
4. Wrong-Style-Cluster enthalten ausschließlich Human-gelabelte
   Wrong-Artstyle-Beobachtungen.
5. Embedding-, Referenz- und Retrieval-Indizes sind vollständig rebuildbar und
   keine Source of Truth.
6. Kosinuswerte werden nur innerhalb identischer Modell-, Raum- und
   Preprocessingrevisionen verglichen.
7. Es existiert kein universeller Similarity-Grenzwert über mehrere Aufgaben.
8. Ein Image- oder Textscore erzeugt keinen fachlichen Stateübergang.
9. Mehrfachverwendung eines Bildes benötigt für jede neue Bewertungsfrage eine
   eigene Human-Observation.
10. Kein Embedding-Ranking verändert die stabile Reihenfolge eines eingefrorenen
    16er-Rosters.
11. LM-Studio-Textvektoren werden niemals mit Image-Embedding-Vektoren
    verglichen.
12. Jeder Retrieval- und LLM-Call ist über WorkIntent, Decision, Context Pack,
    Modell-/Schema-Receipt und Ergebnisrevision nachvollziehbar.

## Rollen- und operationsgebundenes Retrieval ab Schema 55

Schema 55 erzeugt keinen weiteren Vektorraum. Der bestehende Component- und
Atomindex wird durch relationale Query-Manifeste vorgefiltert. Ein Manifest
bindet Component-Rolle, Character-Kontext, Scope, Availability, Modellbranch,
Proof-Eignung, Polarität und genau eine autorisierte Operation. Beispiele sind
`Character/Hair + Replace`, `Outfit/Main Garment + Add`,
`Scene/Background + Reweight` und `Modifier/Framing + Remove`. Kosinusähnlichkeit
ordnet erst die nach diesen Filtern zulässigen Quellen.

Preserve, Change, Confidence, Bewertungen und Gewichtungen bleiben relationale
Metadaten und werden nicht eingebettet. Positive Retrievalquellen benötigen
positive Human Evidence; negative Quellen dienen ausschließlich als
Change-Beispiele. Unbewertete Komponenten und Atome sind Vokabular oder
Exploration und dürfen nicht als positive Referenz erscheinen.

Ein neuer persönlicher Save benötigt keinen vorbefüllten Development-
Playground. Fehlender Content entsteht über `CoveragePlan → ComponentIntent →
Component Designer → Prompt Lexicalizer → Aspect Proposer → Aspect Judge →
deterministischer Validator/WeightPolicy → ComponentVersion → Availability`.
Änderungen einer vorhandenen Version verwenden den kürzeren, relationalen Pfad
`Evidence/Coverage → TypedMutationCorridor → optionaler Lexicalizer → Judge →
Compiler → Child-ComponentVersion`. Beide Pfade münden anschließend in denselben
Candidate Pool.

Dokumentvektoren werden vor jedem Provideraufruf anhand Source, Space, Modell,
Preprocessing und Content-Hash wiederverwendet. Ein identischer Inhalt erzeugt
weder durch einen Reconcile noch durch eine neue Campaign ein zweites
Embedding. Der aktive Schema-55-/v10-Stand bleibt bis zum realen Refill- und
Zwei-Zyklen-Nachweis `LIVE_VERIFICATION_PENDING`.

Ab Schema 56 entfernen Image-Rack-Suchen vor der Rangbildung automatisch ein
relational gebundenes Self-Match: dieselbe Vector-ID, dieselbe typisierte Source
oder dasselbe Bild. Generische Component-/Atom-Suchen schließen die eigene
Quelle ausschließlich über explizite Hard Filter wie
`excluded_embedding_vector_ids` oder `excluded_source_refs` aus. Der erste
verbleibende Treffer ist der beste echte Nachbar und wird nicht pauschal
übersprungen.
Image-Racks werden nur aus Human Evidence als `axis_preserve`,
`explicit_negative` oder `diagnostic_only` materialisiert. Sie unterstützen
Drift, Near-Duplicate-Abstand und visuelle Neuabdeckung, erzeugen aber keinen
zweiten Qualitätscredit.
