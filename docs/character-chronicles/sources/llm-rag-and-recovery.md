# LLM, RAG und Recovery

> **DOKUMENTSTATUS: SOURCE_MATERIAL – NICHT VERBINDLICH.** Vollständige importierte Quellenfassung vom 2026-10-09. **Nicht** der aktuelle Code-Ist-Zustand, **kein** genehmigter Implementierungsplan und **keine** verbindliche Character-Chronicles-Architektur. Frühere Angaben wie „Autorität“, „DECIDED“, „Baseline abgeschlossen“ und „implementiert“ sind **historischer Originalwortlaut**.

**Quellkategorie:** `HISTORICAL_AI_ARCHITECTURE`  
**Worum es geht:** Frühere KI-Rollen, RAG-/Retrieval-Kontext, Provider/Recovery und Schema-47/57-Entwürfe.  
**Aktueller Referenzpunkt:** [bereinigter Überblick](../HISTORICAL_CODE_AUDIT.md) · [Quellenindex](README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

## Übernommene Quellenfassung (historischer Entwurf, keine aktuellen Beschlüsse)

**Ab hier folgt der damalige Text einschließlich seiner früheren Status- und Architekturbehauptungen.** Diese dürfen nicht ohne neue Codeprüfung/ausdrückliche Entscheidung in aktive Arbeitsaufträge umgedeutet werden.

---

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 12. September 2026

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

## Zwei logische Rollen

### Scene Realizer und Character Speaker

Diese gemeinsame lokale Sprachrolle realisiert die konkrete Variante eines
bereits autorisierten VN-, Gesprächs-, Nachrichten- oder Postrahmens. Input sind
Scene- und Behavior Contract, ein validierter Spielerintent, erlaubte
Variantenfamilien, relevante Memories, Relationship State und Scene Context.
Das Modell darf Dialog, Erzählertext, kleine Handlungen, Übergänge und
emotionale Ausprägung neu erzeugen; es entscheidet weder Wahrheit noch
Progression.

Jede Session referenziert vor dem ersten LLM-Aufruf ein authored
`ConversationBlueprint`:

```text
ConversationBlueprint
├─ topic_id und Gesprächsanlass
├─ conversation_purpose
├─ allowed_beats[]
├─ allowed_variant_families[]
├─ allowed_user_intents[]
├─ allowed_player_input_modes[]
├─ allowed_facts_and_reveals[]
├─ allowed_ephemeral_details[]
├─ forbidden_or_unknown_topics[]
├─ possible_outcome_contract_ids[]
├─ session_class und Turn-/Effect-Budget
├─ channel_variants: in_person | phone
└─ deterministic_fallback_lines[]
```

Der Director wählt das Blueprint aus Day-, Scene-, Character-, Relationship-,
Knowledge- und Availability-State. Retrieval darf anschließend ausschließlich
bereits authorisierte Fakten und Memories für dieses Blueprint bereitstellen.
Weder Retrieval noch Character Speaker wählen Thema, Gesprächsziel oder
Outcome.

Der sichtbare Ablauf lautet:

```text
Director öffnet authored Szenen- und Wirkungskorridor
→ User antwortet über Choice, begrenzten Freitext oder Impuls-Minispiel
→ Input wird einem erlaubten Intent zugeordnet und validiert
→ Code friert Fakten-, Wissens-, Varianten- und Outcome-Grenzen ein
→ Scene Realizer erzeugt die konkrete personalitygerechte Szenenvariante
→ strukturierter Validator akzeptiert sie oder fordert eine gebundene Revision
→ Director schließt Session und wendet den authored Outcome einmal an
```

Das Impuls-Minispiel ist eine mögliche Eingabeprojektion und keine eigene
Storyautorität. Es erzeugt einen strukturierten `PlayerReactionIntent`; seine
konkrete Spielmechanik wird separat authoriert und getestet.

Unpassender oder nicht eindeutig zuordenbarer Userinput führt zu einem
authorisierten Clarify-, Redirect-, Refuse- oder `no_evidence`-Pfad. Er darf
keine improvisierte Nebenstory eröffnen.

Der Scene Realizer darf Wortwahl, Satzlänge, Ton, aktuelle Stimmung, vergängliche
Gesten, kleine situative Details und direkte, telefonische beziehungsweise
plattformgebundene Darstellungsformen variieren. Diese Details werden nur dann
persistenter Canon, wenn der Vertrag sie ausdrücklich als validierbares Outcome
vorsieht. Das Modell darf keine neuen dauerhaften Fakten, Memories,
Beziehungen, Versprechen, Treffen, Storyereignisse, Reveals, Intents oder
Auswirkungen erfinden. Bei Provider- oder Validierungsfehlern wird eine authored
Fallbackvariante verwendet; die Session bleibt deterministisch fortsetzbar.

### Harte Social-/Visual-Firewall

Character Chat, Direktnachrichten, Gruppenchat, Posts und Post-Reactions sind
ausschließlich soziale und narrative Eingabekanäle. Sie dürfen Character-
Erfahrung, Knowledge, Beliefs, Relationship, Tension, Social Edges,
Conversation Availability und authored Scene-Varianten beeinflussen. Sie
erzeugen weder `VisualPreferenceEvidence` noch Prompt-/Recipe-Credit,
`VisualEvolutionProposal`s, Character-Canon-Mutationen oder automatische
Generierungsdeltas. Ein `appearance_suggestion`-Intent gehört nicht zum
Character-Speaker-Vertrag.

Ein sozialer Outcome darf einen authored Storykontext erreichbar machen und
dadurch einen neuen `VisualRequirement` auslösen, beispielsweise für einen
Besuch des Sommerfests. Er bestimmt damit, **was** für die Story darstellbar
werden muss, aber weder die konkrete Optik noch den bevorzugten Kandidaten.
Diese Autorität besitzt ausschließlich der nachgelagerte Booster-/Bildspiel-
Loop mit vollständiger Human Evidence.

Der Prolog ist eine eng begrenzte Bootstrap-Ausnahme: Seine ausdrücklich
visuellen, authored Eingaben dürfen vor dem ersten Bild eine initiale
`VisualSpec` erzeugen. Er ist keine freie Character-Chat-Session und darf
spätere bestehende Figuren nicht über soziale Antworten visuell verändern.

### Prompt Author

Formuliert aus `VisualSpec`, kanonischen Content-Snapshots, User-Locks,
bewährten persönlichen Recipes und Recovery-Evidenz einen strukturierten
semantischen Promptvorschlag. Er verwendet ein versioniertes,
contentneutrales `PromptDialectPack`, das offline aus den Strukturkonventionen
des Entwicklungskorpus destilliert und fachlich freigegeben wurde. Die
Playground-, Prompt-, Rating- und Combo-Datenbanken des Entwicklungskorpus sind
weder Runtime-RAG noch ausgelieferter Spielinhalt. Ein neuer Save besitzt nur
das versionierte Playground-Schema; sein persönlicher Komponentenbestand und
sein Textindex sind zunächst leer.

Der erzwungene Structured Output des LLM ist:

```text
PromptAuthorProposal
├─ target_kind
├─ semantic_slots[]
├─ token_atoms[]
│  ├─ phrase
│  ├─ polarity: positive | negative
│  ├─ semantic_slot
│  └─ emphasis_class
├─ tags[]
└─ unresolved_or_uncertain[]
```

Das `PromptAuthorProposal` ist noch kein Datenbankeintrag. Die LLM darf keine
IDs, numerischen Gewichte, Revisionen oder Promotionen festlegen und schreibt
nie direkt in den Runtime-Store. Erst der deterministische Playground-Validator
prüft Zielschema, Rolle, Positiv-/Negativtokens, erlaubte Grenzen, Konflikte und
Unbekanntes. Der anschließende Materializer normalisiert, vergibt IDs und
Gewichte und persistiert eine revisionierte Komponente.

Vorhandene Playground-Zeilen können denselben Prozess ausschließlich als
explizite `ImportCandidate`s mit Source Receipt durchlaufen. Sie werden nicht
beim normalen Start automatisch geladen oder vektorisiert. Der vollständige
Empty-to-Runtime-, Import- und Reindex-Kreislauf ist in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md)
verbindlich beschrieben.

### Verbindlicher OpenAI-kompatibler Call-Vertrag

LM Studio wird für die Inferenz über einen normalen OpenAI-Client mit lokaler
`base_url` angesprochen. Der erste verbindliche Pfad ist
`POST /v1/chat/completions`. Struktur wird nicht nur im System Prompt verlangt,
sondern als echter Requestparameter übergeben:

```json
{
  "model": "<discovered-model-id>",
  "messages": [
    {
      "role": "system",
      "content": "<role-specific contract>"
    },
    {
      "role": "user",
      "content": "<bounded task input>"
    }
  ],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "<schema-name>",
      "strict": true,
      "schema": "<versioned JSON Schema>"
    }
  }
}
```

Der Prompt erklärt Aufgabe, Semantik und erlaubte Inhalte. Er ist nicht dafür
verantwortlich, mit Formulierungen wie „Antworte nur als JSON“ die Syntax zu
erzwingen. Das übernimmt `response_format`. Der Inhalt aus
`choices[0].message.content` wird anschließend als JSON geparst und zusätzlich
durch das versionierte Anwendungsschema sowie alle Domainvalidatoren geprüft.
Grammar-konformes JSON allein erteilt keine fachliche Schreib- oder
Freigabeautorität.

Jeder Contract speichert `schema_id`, `schema_version`, Schema-Hash,
aufgelöste Modell-ID, Inferenzparameter und Call-ID. Ein Modell gilt für eine
Rolle erst als capability-geprüft, wenn es deren reales `strict`-Schema über
mehrere Positiv-, Grenz- und Abstention-Fixtures zuverlässig erfüllt. Ein
Modell, das nur durch Promptdisziplin ungefähr JSON erzeugt, ist nicht geeignet.

Auch Scene-Realizer-/Character-Speaker-Ausgaben verwenden ein schmales
strukturiertes Envelope, beispielsweise aus freigegebener Text- und
Handlungsvariante, Mood-/Delivery-Key, referenzierten Beat- und Outcome-IDs und
`abstain`; sichtbarer Dialog-, Nachrichten-, Post- oder Erzählertext bleibt
darin als klar zugeordnetes Stringfeld erhalten. So kann der Validator die
Realisation prüfen, ohne dem LLM Story- oder Stateautorität zu geben.

### Prompt Aspect Proposer und Judge

Bei offenen oder zu migrierenden Promptstrukturen arbeitet der Prompt Author in
zwei logisch und kontextuell getrennten Rollen. Der `PromptAspectProposer`
interpretiert die flachen gewichteten Atome und schlägt eine vollständige,
breite semantische Partition vor. Seit `component-aspect-alias-v2` erhält er
nur lokale Aliasse, Blockrolle, Polarität, Phrase und vorhandenes Gewicht;
UUIDs, Concept-/Variant-IDs und Ordinaldetails verbleiben in einem immutable
Aliasmanifest. Seine Ausgabe enthält ausschließlich `semantic_scope` und die
zugehörigen `atom_aliases`. Labels, IDs und Gewichte erzeugt Code.

Der `PromptAspectJudge` prüft anschließend unabhängig, ob alle positiven und
negativen Atome genau einmal, widerspruchsfrei und in fachlich breiten Gruppen
enthalten sind. Sein flaches Schema bindet `approved`, `abstain`,
`issue_codes`, `affected_atom_aliases` und `affected_group_scopes`. Erst Code
löst die Aliasse auf kanonische Bindungen zurück und prüft Vollständigkeit,
Orphans, Overlap, Polarität, Locks und den unveränderten Manifesthash.

```text
PromptAspectNegotiationSession
├─ immutable_source_prompt_snapshot
├─ root_taxonomy_revision
├─ proposal_revisions[]
├─ deterministic_validation_reports[]
├─ judgement_revisions[]
├─ accepted_proposal_revision_id oder null
└─ status: negotiating | accepted | recovery_required
```

Der Judge editiert das Proposal nicht selbst. Bei einem Befund erzeugt der
Proposer aus Source Snapshot, letzter Proposal Revision und den strukturierten
Issue-Codes eine neue Revision; danach wird erneut deterministisch validiert
und unabhängig gejudgt. Nur ein exakt referenziertes Proposal, das der Proposer
als vollständig vorgelegt, der Judge akzeptiert und der Hard Validator bestanden
hat, wird eingefroren und kompiliert. Technische Providerablehnungen erhöhen
keine semantische Revisionszahl.

```text
Source Prompt und VisualEvolutionProposal aus Booster-/Bildspiel-Evidence
→ PromptAspectProposer
→ deterministischer Schema-/ID-/Weight-/Diff-Check
→ PromptAspectJudge
→ revise: neue Proposal Revision und erneuter Check
→ accept: AcceptedPromptAspectProposal
→ Prompt Compiler und erst danach Generation
```

Ein einzelner Provider- oder Modellzyklus darf ein konfiguriertes Betriebsbudget
besitzen. Wird es ausgeschöpft, wechselt die Session in Provider-/Modell-Fallback
oder `recovery_required`; sie lockert niemals die Akzeptanzkriterien und reicht
kein ungeklärtes Proposal an Generation oder Spielerreview weiter.

Die Autorität dieser Verhandlung endet mit der Promptfreigabe. Der Prompt Aspect
Judge beurteilt weder das anschließend generierte Bild noch dessen Attraktivität,
Identity-Treue, Artstyle, Anatomie oder Backgroundqualität und darf keinen
darstellbaren Output vor dem Spieler verbergen. Diese sichtbaren Ergebnisse und
Fehler sind Gegenstand des Bildspiels und der strukturierten Spielerbewertung.

Ein deterministischer Compiler mappt die Emphasis-Klassen anhand der
versionierten Weight Policy, ergänzt codeeigene IDs und Metadaten und erzeugt
erst daraus die bestehende Playground-Grammatik:

```text
PlaygroundItemDraft
├─ kind: character | scene | outfit | pose | expression | lighting | modifier
├─ name
├─ key
├─ tags
├─ pos: exakt komma-separierte gewichtete Tokens
├─ neg: exakt komma-separierte gewichtete Tokens
└─ notes
```

Ein Target-Token behält Phrase, Klammern und Gewicht exakt, beispielsweise
`(deep wine red hair:1.35)`. Proposal- und Compiler-Validierung prüfen Syntax,
Weight Bounds, Scope, Story Locks, Excludes, Requires,
Workflow-/Modellkompatibilität und Blockbudget. Der Prompt Author schreibt nicht
direkt in die Runtime-Datenbank, bestimmt keine IDs oder numerischen Gewichte,
wählt keine Promotion und darf weder unbekannte Komponentenrollen noch
unautorisierte Storyinhalte erfinden. Bei einem Weight Trial liefert der Code
die exakte Diff-Hypothese.

Der Code ergänzt `ComponentVersion`, Parent, Hypothese, Diff, Evidence-Quellen
und Status. Eine vorgeschlagene Formulierung oder Gewichtung bleibt zunächst ein
Try und wird erst über vollständige Generation Recipes, Bildspiele und
strukturierte Review Evidence bewährt. Der vollständige Daten-, Rating- und
ComfyUI-Vertrag steht in
[Foundation-Vertrag zum adaptiven Generationslernen](../foundation/adaptive-generation-learning.md).

Der kurze Child-Pfad ab Schema 55 verwendet für alle sieben Component-Rollen
einen akzeptierten `TypedMutationCorridor`. Code autorisiert darin Rolle,
Operation, Zielatom beziehungsweise Aspect Group, Preserve-Gruppen und
Weight-Band. Die LLM darf nur die benötigte ungewichtete Phrase oder die
semantische Gruppierung liefern. `add`, `remove`, `replace`, `reweight` und
`replace_group` werden vor dem Render gegen Parent, Corridor, Arm, Recipe und
den exakten Child-Diff validiert. Der vollständige Authoring-Pfad bleibt für
eine echte Coverage-Lücke zuständig und benötigt keinen vorbefüllten
Development-Playground.

Character Speaker, Prompt Author, Prompt Aspect Proposer und Prompt Aspect Judge
können zunächst dasselbe physische LM-Studio-Modell verwenden. Die logischen
Contracts, Kontexte, Call- und Output-IDs, Schemas, Token Budgets,
Temperaturwerte und Schreibrechte bleiben getrennt. Der Judge erhält nicht die
freie Begründung des Proposers, sondern Source Snapshot und strukturiertes
Proposal, damit er dessen Fehler nicht nur sprachlich fortschreibt.

## Provider

Der MVP ist **local-only**. Prompt Machine und Character Speaker verwenden
ausschließlich LM Studio; Gemini, ein automatischer Cloud-Fallback und ein
zweiter generativer Provider gehören nicht zum aktuellen Zielvertrag.

Unabhängig vom Provider sind sämtliche Meta-/Facebook-Modellgewichte und davon
abgeleitete Weight-Lineages ausgeschlossen. Das gilt für jede KI-Rolle,
einschließlich Prompt Machine, Character Speaker, Judge, Text Embeddings, Image
Analysis, Segmentierung, Matting, Generation und Training; Llama- und
SAM-Familien sind damit keine zulässigen Kandidaten. Discovery allein genügt
nicht: Publisher, Base-Model-Lineage, Lizenz, Revision und Hash müssen
verifizierbar sein, andernfalls bleibt die Bindung `unavailable`.

### Modell-Discovery und Verwaltung

Die Anwendung fragt zuerst den OpenAI-kompatiblen Modellkatalog von LM Studio
über `GET /v1/models` ab. Er ist die kanonische Quelle für Modell-IDs, die über
den bestehenden OpenAI-Client tatsächlich ansprechbar sind. Bei aktiviertem
Just-in-time Loading darf dieser Katalog auch lokal heruntergeladene, noch nicht
geladene Modelle enthalten.

Für zusätzliche Managementinformationen darf der Adapter ergänzend die native
LM-Studio-v1-API verwenden: Modelltyp, geladen beziehungsweise nur lokal
vorhanden, Instance-ID sowie kontrolliertes Load/Unload. Die Anwendung scannt
keine Modellordner und führt keine eigene Modellverwaltung neben LM Studio.

API-Grundlage sind LM Studios offizielle Dokumente für
[OpenAI-kompatibles Model Listing](https://lmstudio.ai/docs/developer/openai-compat/models),
[OpenAI-kompatiblen Structured Output](https://lmstudio.ai/docs/developer/openai-compat/structured-output),
[native REST-Modellverwaltung](https://lmstudio.ai/docs/developer/rest) und
[OpenAI-kompatible Text Embeddings](https://lmstudio.ai/docs/developer/openai-compat/embeddings).

```text
LmStudioModelDiscovery
├─ discovered_at und endpoint_revision
├─ model_id
├─ model_type: llm | embedding | vision | unknown
├─ availability: loaded | loadable | unavailable
├─ instance_id oder null
├─ context_length beziehungsweise dimension, soweit gemeldet
├─ capability_test_revision
└─ verified_capabilities[]
```

Discovery ist noch keine Eignung. Ein Modell erscheint nur in einem
funktionsbezogenen Settings-Dropdown, wenn sein Typ passt und der zugehörige
Capability-Test bestanden wurde und seine Lineage die globale No-Meta-Policy
erfüllt. Ein LLM für die Prompt Machine muss mindestens
das über `response_format.type = json_schema` mit `strict = true` übergebene
Structured-Output-Schema stabil erfüllen; der Character Speaker benötigt seinen
separaten strukturierten Conversation-Envelope-Test.

### Getrennte Funktionszuordnung in Settings

Die globale Konfiguration besitzt voneinander unabhängige Modellbindungen:

```text
LocalAiModelAssignments
├─ prompt_machine_model_id
├─ character_speaker_model_id
├─ prompt_judge_model_id oder inherit_prompt_machine
├─ text_embedding_model_id oder null
└─ image_analysis_bindings[]
```

Die LM-Studio-Dropdowns enthalten nur aktuell entdeckte und für die
jeweilige Funktion verifizierte Modelle. Geladene und nur ladbare Modelle sind
sichtbar unterscheidbar; verschwundene gespeicherte IDs bleiben als klarer
Blocker erhalten und werden nicht still ersetzt. Dieselbe physische Modell-ID
darf mehrere Rollen belegen, wird aber nie vorausgesetzt.

### Referenzbelegung auf der vorhandenen Hardware

Für den Entwicklungsrechner mit RTX 3060 12 GB VRAM und 32 GB RAM gilt
folgende initiale Belegung. Sie ist der Default des Capability-Bake-offs, aber
noch keine Freigabe ohne bestandene Fixtures:

| Funktion | Runtime und Referenzmodell | Betriebsprofil |
|---|---|---|
| Prompt Machine und Prompt Judge | LM Studio mit [Huihui Qwen3 14B Abliterated v2](https://huggingface.co/huihui-ai/Huihui-Qwen3-14B-abliterated-v2), Apache-2.0, als gepinnte `Q4_K_M`-GGUF-Quantisierung | Slot-/Aspect-Aufrufe verwenden 4096 Kontexttokens; der gemeinsame kompakte v10-Batch-Judge verwendet das qualifizierte 8192-Profil mit maximal 7200 Input- und 512 Outputtokens; striktes JSON-Schema, 50 Prozent GPU-Offload und Parallelität 1; die installierte normale `qwen3-14b`-Variante ist wegen der Uncensored-Pflicht kein zulässiger Produktdefault |
| Character Speaker | initial dieselbe Qwen3-14B-Bindung mit eigenem Rollen- und Capability-Test | logische Trennung trotz gleicher Gewichte; ein späteres separates Roleplay-Modell benötigt eine eigene No-Meta-/Uncensored-/Conversation-Eval |
| Text Embeddings | LM Studio mit dem bereits vorhandenen [Qwen3-Embedding-0.6B](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B), Apache-2.0 | CPU-only, Kontext 8192, Parallelität 4, feste 1024 Dimensionen, L2-Norm und Last-Token-Pooling; raumspezifische Retrieval-Instructions werden versioniert und für mehrsprachige Inhalte auf Englisch formuliert; das qualifizierte GGUF-Profil besitzt genau einen providerverwalteten EOS-Abschluss |

Die konkrete Quantisierung erhält wie jedes andere produktive Gewicht eine
geprüfte Base-Model-Lineage, Repository-Revision und einen Dateihash. Die
Bezeichnung `abliterated` ersetzt weder den Five-Scope-Refusal-Test noch die
fachliche Structured-Output- und Rollenqualifikation.

Für neue `m6-slotwise-v10`-Planungen verwenden Slot- und Aspect-Aufrufe das
4096-Profil. Der Batch-Judge erhält die gemeinsame Baseline genau einmal und pro
Arm nur kompakte Aliasse sowie den autorisierten Diff. Er verwendet das
qualifizierte 8192-Profil; sein Preflight begrenzt den tatsächlichen Input auf
7200 Tokens und reserviert höchstens 512 Outputtokens. Es gibt weder Trunkierung
noch einen automatischen Profilwechsel. Frühere Aussagen, auch den gemeinsamen
Judge auf 4096 beziehungsweise 3000 Inputtokens zu begrenzen, beschreiben einen
historischen Zwischenstand und sind für neue v10-Arbeit nicht autoritativ.

Text-Embeddings können über das OpenAI-kompatible `POST /v1/embeddings` von LM
Studio erzeugt werden. Image Embeddings laufen dagegen in einem eigenen lokalen
Docker-Worker. Ein beliebiges Vision Language Model gilt nicht automatisch als
Image-Embedding-Modell. Jede Bildbindung bleibt `unavailable`, solange
Capability-Test, stabiler Vektor-/Dimensionsvertrag, deterministisches
Preprocessing, feste Modellrevision und Lizenzprüfung nicht bestanden sind.
Text- und Bildvektoren sowie verschiedene Bildräume werden niemals vermischt.

Der Requestvertrag `qwen3-embedding-cpu-8k-token-pages-v5` verwendet für GGUF
und Last-Token-Pooling genau einen providerverwalteten EOS-Abschluss. Character
Chronicle entfernt versehentlich vorhandene explizite `<|endoftext|>`-Suffixe,
hängt selbst aber keinen zweiten Separator an. Die Tokenbudgetierung reserviert
den wirksamen Abschluss dennoch. Request-, Provider- und Tokenizerbeleg müssen
die Invariante nachweisen; ältere Eingangsrevisionen bleiben indexseitig
getrennt.
Das operative Modellprofil verwendet bewusst 8192 Kontexttokens. `Textbatch 32`
ist nur die maximale Stückzahl einer Seite und keine Zusage, dass 32 beliebig
lange Quellen gemeinsam in einen Kontext passen. Nach kontrolliertem Load zählt
der tatsächlich geladene LM-Studio-Tokenizer jeden vollständig vorbereiteten
Text einschließlich Instruction und End-Token. Der Page Planner gruppiert nur
Dokumente desselben logischen Raums, in stabiler Quellenreihenfolge, mit
höchstens 32 Einträgen und höchstens 8192 realen Tokens. Eine einzelne größere
Quelle wird ohne Trunkierung oder automatischen Profilwechsel blockiert.

Dokumente und Retrievalfragen werden nie im selben Providerrequest verarbeitet.
Jeder aktive Raum erhält genau eine kompakte Query mit eigener versionierter
englischer Instruction. Eine gemeinsame fachliche Ausgangsfrage darf damit in
mehreren Räumen gesucht werden, wird aber nicht als sechsfacher Text in einen
gemischten Großbatch kopiert. Ein WorkIntent hält das Modell über seine
sequenziellen Dokumentseiten und Querycalls geladen und entlädt es erst danach
kontrolliert. Call-Keys binden Manifest, Profilrevision, Inputart, Raum und
Seitennummer; ein Neustart wiederholt nur einen noch nicht abgeschlossenen Call.
Die 32k-Fähigkeit des Modells bleibt eine Fähigkeit, aber kein operativer
Standard oder automatischer Fallback.

Die Modellzuordnung ist globale Betriebskonfiguration und kein Teil des Save
States. Jeder persistierte LLM- oder Embedding-Output speichert jedoch die
tatsächlich aufgelöste Modell-ID, Capability-Test-Revision und relevante
Load-/Schema-Konfiguration als Provenienz.

Der Orchestrator projiziert daraus pro Funktion einen eigenen Zustand:

```text
LocalAiFunctionAvailability
├─ function: prompt_machine | character_speaker | prompt_judge
│            | text_embedding | image_caption | image_embedding_general
│            | image_identity | image_attribute_tagger
├─ selected_model_id oder null
├─ resolved_instance_id oder null
├─ model_availability: loaded | loadable | unavailable
├─ capability_status: untested | passed | failed | stale
├─ resource_status: free | waiting | busy | blocked
├─ effective_status: ready | loading | waiting | waiting_for_human_evidence
│                   | unavailable | invalid
└─ blocker_code und remediation_action oder null
```

Eine gespeicherte Auswahl darf bei erneutem Discovery nicht still auf ein
anderes Modell zeigen. Für LM-Studio-Rollen ist Auto-Load nur für die explizit
ausgewählte Modell-ID zulässig und erfolgt über LM Studio. Reicht der
Ressourcenvertrag nicht, wartet der Job oder fordert ein kontrolliertes Unload
an; die Anwendung beendet keine fremden Prozesse. Der Docker-Worker lädt nur
die in seinem geprüften Image beziehungsweise Manifest fest gebundenen
Modellrevisionen und lädt zur Laufzeit nichts still nach.

### Image-Embedding-Worker für den M6-Lernbeweis

Der Providerpfad ist entschieden: ein separater, asynchroner Docker-Worker mit
NVIDIA-GPU-Zugriff. LM Studio bleibt für Sprache und Text Embeddings zuständig.
Meta-/Facebook-Gewichte sind für den Image-Embedding-Provider ausgeschlossen.
Die konkreten Modellgewichte werden erst nach einem Bake-off auf den
Projektfixtures aktiviert; folgende Bindungen sind die initialen
Referenzkandidaten:

Der Installationsstand vom 1. September 2026 ist davon getrennt: Die drei
obligatorischen Docker-Artefakte sind mit festem Repository-Commit und
portablem Tree-Hash heruntergeladen, im lokalen Modellregister als `candidate`
eingetragen und über das Manifest des Workers erreichbar. Text Embeddings sowie
beide SigLIP2-Räume sind unter aktuellen Execution Profiles qualifiziert.
Qwen3-VL bleibt nach dem fail-fast Hardware-Bake-off blockiert: Der lokale
Transformers-/Accelerate-/BitsAndBytes-Stack kann das 8B-Modell unter der
verbindlichen GPU-/CPU-Mischplatzierung nicht ohne verbleibenden `meta`-
Attention-Parameter und ohne Verletzung der VRAM-Reserve ausführen. Der danach
implementierte GGUF-/`llama.cpp`-Pfad behält den Kandidaten bei und lädt sein
Q4_K_M-GGUF samt F16-mmproj erfolgreich; sein erster Bildrequest endete jedoch
fail-closed mit HTTP 400. Profilrevision 6 verwendet nun den dokumentierten
`json_object`-plus-`schema`-Vertrag und erzwingt den vollständigen
Artefakt-/Lineage-Pin, wurde aber noch nicht erneut auf der GPU
ausgeführt. CCIP bleibt
bewusst vor dem Laden am Crop-/Preprocessing-Gate blockiert. Installation oder
ein Einzel-Smoke aktivieren keine produktive Planung; ein fehlgeschlagener
Kandidat wird nicht still durch ein anderes Modell ersetzt.

| Logische Capability | Referenzkandidat | Aufgabe | Aktivierungsbedingung |
|---|---|---|---|
| `structured_image_observation` | [Huihui Qwen3-VL 8B Instruct Abliterated](https://huggingface.co/huihui-ai/Huihui-Qwen3-VL-8B-Instruct-abliterated), über die gepinnte [noctrex-Q4_K_M-GGUF-Quantisierung](https://huggingface.co/noctrex/Huihui-Qwen3-VL-8B-Instruct-abliterated-GGUF) | schemaförmige sichtbare Bildbeschreibung mit Charactermerkmalen, Outfit, Scene, Pose, Ausdruck, Style, technischen/anatomischen Auffälligkeiten und Unsicherheit | `llama.cpp`-Kindprozess mit Modell-/mmproj-Hash besteht JSON-/Domainvalidierung, Restart, Four-character-/Five-scope-Refusal-Fixtures, Halluzinations- und reale VRAM-/Latenz-/Unloadmessung; kein stiller Fallback |
| `full_frame_semantic`, `style_view` | [Google SigLIP2 So400m/14 384](https://huggingface.co/google/siglip2-so400m-patch14-384), Apache-2.0 | globale visuelle/semantische Ähnlichkeit, Style Drift, Control-/Challenger-Delta, Near-Duplicates | 384×384 Direct Resize, `AutoModel`/`AutoProcessor`/`get_image_features()`, 1152 Dimensionen, L2-Norm und feste Revision verifiziert |
| `character_crop` | [DeepGHS CCIP `ccip-caformer_b36-24`](https://huggingface.co/deepghs/ccip_onnx), OpenRAIL | Identity-Konsistenz einer einzelnen Anime-Figur über Seeds und Batches sowie Cross-Character-Separation | Single-Character-Crop, Fixture-Eval und Lizenz-/Distributionsprüfung bestanden |
| `anime_attribute_findings` | optional nach dem ersten Worker: [SmilingWolf WD EVA02 Large Tagger v3](https://huggingface.co/SmilingWolf/wd-eva02-large-tagger-v3), Apache-2.0 | ergänzende Ratings-, Character- und General-Tag-Befunde für Attribute und Fehlerdiagnose | kein Blocker der essenziellen SigLIP2-/CCIP-Aktivierung; Schwellen und Tag-Mapping separat kalibriert; kein Vektorraum und keine kanonische Wahrheit |

SigLIP2 allein ersetzt keinen Character-Identity-Test. CCIP wird umgekehrt nur
auf einem deterministischen Crop mit genau einer Anime-Figur verwendet und
nicht für Mehrfigurenkomposition oder globalen Style. Der WD-Tagger ergänzt
strukturierte Befunde; er ersetzt weder einen Embedding-Raum noch
Spieler-Evidence.

Das VLM erzeugt keinen Image-Embedding-Vektor. Es schreibt eine getrennte
`MachineImageObservation` mit sichtbaren Facts, Unsicherheiten, vorgeschlagenen
vorhandenen Reason Codes und Konfidenzen. Modell-, Schema-, Prompt-, Attempt-,
Image- und Dateiprovenienz bindet die Pipeline über referenzierte Runtimezeilen;
der Worker errät oder dupliziert sie nicht. Nach erfolgreicher Validierung darf
die lesbare Beobachtung einen separaten Text-Embedding-Job im Raum
`machine_image_description_text` auslösen, sobald die DescriptionRevision durch
den eigenständigen Beschreibungstest oder einen administrativen Bestandslauf
dafür freigegeben wurde. Der
frühere `recovery_case_text`-Raum ist aus aktiven Index-, Retrieval- und
Promptverträgen entfernt. VLM-Text, Textvektor, Bildvektor und
Playerentscheidung bleiben getrennte Records. Mehrere playerseitige Zwei-Bild-
Zuordnungen erzeugen eine rebuildbare DescriptionMatch-Projektion; kein
Maschinenbefund oder einzelnes Match setzt
Keep, Favorite, Champion, Canon, Readiness oder Safety.

Die VLM-Rohbeschreibung ist auch dann keine Spieler-Copy, wenn sie lesbar ist.
Eine Bildkarte darf daraus eine gekürzte lokalisierte Beschreibung vorschlagen,
bindet diese aber an Roh-, Match-/Validierungs- und Lokalisierungsrevision.
Der ursprüngliche Generierungsprompt, Expected Composition und die bestätigte
Beschreibung bleiben getrennte Quellen. Im normalen Bildreview werden keine
VLM-Felder bestätigt. VLM-Unterfelder, Matchschwellen, eine mögliche
„nicht eindeutig“-Aktion und der Lokalisierungsworkflow bleiben versionierte
Kalibrierung des eigenen Beschreibungsspiels.

Im Gegensatz zum Image-Embedding darf diese rein diagnostische
VLM-Vorabbeobachtung nach Output-Ingest und Content-Autorisierung bereits vor
dem ersten Human Review laufen, damit der Spieler eine Beschreibung und
bestätigbare beziehungsweise verwerfbare Vorschläge erhält. Sie verändert weder
Bildreihenfolge noch Auswahlmöglichkeiten und startet keine weitere
Providerarbeit selbst:

```text
Output-Ingest
→ MachineImageObservationJob
→ schemaförmige VLM-Beschreibung
→ optionaler Text-Embedding-Job der validierten Beschreibung
→ UI zeigt Beschreibung, Unsicherheit und vorhandene Reason-Code-Vorschläge
→ Spieler bestätigt, verwirft oder korrigiert
→ erst die Spieleraktion erzeugt Human Evidence
```

### Batch-Diversität als geschlossener Prompt-/Bildloop

Die Prompt Machine verlässt sich nicht darauf, dass vier Seeds automatisch vier
sichtbar verschiedene Bilder ergeben. Sie liefert für jeden gebundenen neuen
Slot sequenziell einen schemaförmigen Vorschlag. Der gemeinsame Judge sieht
anschließend die vier vorkompilierten Endzusammensetzungen. Der deterministische
Planner materialisiert daraus eine `BatchDiversityPlanRevision` mit gemeinsamem
ComparisonContext, Locks und vier stabilen Anzeigeslots. Ein neuer Kandidat darf
eine bis drei deklarierte Achsen verändern; gemeinsam veränderte Achsen erzeugen
nur Kombinationsevidence. Ein-Achsen-Credit ist ausdrücklich isolierten
Diagnosefragen vorbehalten. Jeder Slot bindet ein unverändertes kompatibles
Carried Image oder ein neues immutable Recipe mit Seed und erwartetem sichtbaren
Delta.

Jeder normale Folge-Try beginnt erst nach dem finalisierten Human Review. Die
angenommene Questkarte hält ihren Supply-Slot bis zum `QuestCreditAward`; danach
reiht die Review-Transaktion ausschließlich eine idempotente
`CampaignFollowupEvaluated`-Entscheidung ein. Provider- oder LLM-Aufrufe finden
nie innerhalb dieser Transaktion statt. Der Campaign Director entscheidet mit
der neuesten Evidence über `continue_learning`, `waiting_for_analysis`,
`stage_advanced`, `campaign_complete` oder `blocked`. Vier positive Bilder
schließen nur die aktuelle Frage. Andere bereits spielbereite Karten bleiben
unverändert; der verbrauchte Slot erhält bei aktiver Campaign eine andere Frage.

Eine normale neu geplante Vierergruppe durchläuft vor ComfyUI zwingend
`TextEmbedding → Retrieval → ContextAssembly → LlmCall/Judge →
BatchDiversityPlan`. Erst `ready_for_generation` darf `quest_batch_submit`
einreihen. Derselbe Vertrag gilt beim Restart-Reconcile; ein vorbereiteter
Attempt ohne vollständigen vierteiligen DiversityPlan wird erneut an
`m6_prepare_batch` und niemals direkt an ComfyUI gegeben. Nur bereits vollständig
materialisierte und früher autorisierte Providerarbeit darf mit identischen
Recipes und Seeds technisch fortgesetzt werden. Fachliche RecoveryCases und
RecoveryArms sind kein alternativer Prompt- oder Generationseingang mehr.

Veröffentlichte `historical_reference`-Cohorts sind das ausdrückliche Opt-in
für dieselbe Campaign. Der Server löst sie selbst auf; der Browser übergibt
keine Cohort-IDs. Pro veröffentlichter Cohort entstehen drei getrennte
RetrievalReceipts: Beschreibungstext, `full_frame_semantic` und `style_view`.
Bildräume verlangen einen gerade bewerteten Anchor desselben Modell- und
Vektorraums; ohne ihn wird `no_reviewed_anchor` quittiert. Text- und Bildscores
werden nicht addiert, sondern nur revisioniert rankbasiert fusioniert. Ein
gebundener `fresh_proof` schließt historische IDs technisch aus.

Der ContextPack enthält die tatsächlich ausgewählten, bereinigten
Evidence-Inhalte als stabile Aliase mit Receipt, Rang, bestätigter oder
korrigierter Beschreibung, Human-Disposition, achsenspezifischen Reasons,
Scope, Referenzstärke und Cohort-Provenienz. Prompt Machine und Judge erhalten
dieselbe Zusammenfassung. `influence_refs` dürfen ausschließlich auf diese
Aliase zeigen und bleiben deklarative Nachvollziehbarkeit; Seed, Recipe-ID,
Gewichte, Champion- und Evidence-Autorität bleiben beim deterministischen Code.
`GET /api/vnext/attempts/{attempt_id}/m6/trace` projiziert Directorentscheidung,
Receipts, ContextPack, Proposal-/Judge-Runden, Influence-Referenzen,
DiversityPlan, Guardian-/Provider-/Lifecycle-Bindungen und nachgelagerte
Bildanalyse ohne Rohvektoren.

Die Seed Policy gehört dem deterministischen Plan: `independent` verwendet
verschiedene Seeds, `paired_control` darf bei verschiedenen Recipes denselben
Seed für einen isolierten Control-/Challenger-Vergleich teilen und
`reproduce_calibration` darf eine vollständige Wiederholung ausdrücklich
markieren. Undeklarierter Reuse ist ein Integritätsfehler; Seedvariation allein
ist kein sichtbarer Diversitätsnachweis.

```text
QuestExperimentContract
→ Prompt Machine schlägt focusgebundene Deltas für neue Slots vor
→ Code bindet Carried Images unverändert und validiert neue Seeds/Recipes
→ BatchDiversityPlanRevision
→ Guardian autorisiert null bis vier neue Recipe-Submissions unter einem Batch
→ ComfyUI rendert und Output-Ingest ordnet jedes Resultat exakt seinem Slot zu
→ VLM erzeugt Einzelbeschreibungen und BatchDiversityObservation
→ UI zeigt einen möglichen Batch-Collapse als Diagnose, aber alle gültigen Karten
→ Human Review erzeugt alleinige Evidence
→ post-review Image Embeddings ergänzen nach Bootstrap Near-Duplicate-, Style-
  und Identity-Distanzen
→ Generation Planner erstellt bei Bedarf einen neuen kontrollierten Try
```

Die Batchdiagnose unterscheidet einen technischen Recipe-/Seed-Reuse von echter
Prompt-/Modellkonvergenz trotz unterschiedlicher Recipes. Außerdem erkennt sie
erreichte kontrollierte Diversität, unzulässig breite Multi-Achsen-Variation und
Unsicherheit. VLM und Image Embeddings dürfen keinen Output verbergen,
umsortieren, automatisch ablehnen oder unmittelbar eine Ersatzgeneration
starten. Ihr Mehrwert ist, die vom Spieler beobachtete Gleichförmigkeit
achsenbezogen und über nachfolgende Batches messbar zu machen. Erst ein neuer
Planner-/Guardian-Zyklus darf daraus technische Recovery, stärkere zulässige
Slotdeltas oder einen engeren Vergleich ableiten.

„Unzensiert“ bedeutet in diesem Providervertrag konkret: Nach erfolgreicher
Content-Autorisierung durch die Anwendung verarbeitet der Worker die fünf
Produkt-Scopes `standard`, `sexy`, `lewd`, `nude` und `explicit` identisch und
ohne eigene providerseitige Inhaltszensur, Refusal- oder Scope-Filter. Das hebt
keine Safety-, Alters-, Save- oder Freigaberegel auf; unautorisierte Inputs
erreichen den Worker nicht.

Der ausgelieferte Runtime-Store enthält weder Legacy-Bilder noch vorbefüllte
Bildvektoren, Referenzprototypen oder persönliche Anchor Sets. Im initialen
Human-first-Pfad bleiben Image Embeddings für ungesehene Rohbilder vollständig
inaktiv: Renderabschluss und `VisualSpec` allein erzeugen keinen Job. Ein
transportgültiges, kontextkompatibles Favorite, eine scopekompatible `APPROVED
ChampionRevision` oder ausdrücklich vorhandenes kompatibles Legacy-
Referenzmaterial darf die erste scopegebundene `ImageAnalysisBootstrapRevision`
erzeugen. Favorite und Champion sind für diese Referenzfreigabe gleichwertig.
Keep ist positive Human-Evidence, aber allein kein Bootstrap-Schlüssel; nach der
Freigabe darf es als vorläufig positive Beobachtung eingebettet werden.

```text
kontrollierten Try ohne Image-Embedding-Vorprüfung generieren
→ vollständigen Human-Run gemäß gewähltem Spielmodus persistieren
→ mindestens ein kompatibles Favorite bestätigen oder vorhandene Champion-/
  Legacy-Referenz für diesen Scope nachweisen
→ ImageAnalysisBootstrapRevision erzeugen
→ positive Rollen aus Keep/Favorite und achsenspezifischen Gründen ableiten
→ explizit begründete negative Beobachtungen getrennt ableiten
→ deterministische Full-Frame-, Style- und Character-Crops materialisieren
→ ImageEmbeddingJob persistent einreihen
→ Docker-Worker berechnet modellgebundene Vektoren/Tags
→ Anwendung validiert und persistiert Output samt Provenienz
→ LearningCycleMonitorProjection aktualisieren
→ Spieler-Evidence bleibt alleinige Präferenz- und Promotionsautorität
```

```text
ImageAnalysisBootstrapRevision
├─ source_type: completed_human_run | approved_champion_rebuild | legacy_reference
├─ source_quest_session_id oder null
├─ source_keep_evidence_event_ids[]
├─ source_favorite_evidence_event_ids[]
├─ source_champion_revision_id oder null
├─ source_legacy_reference_ids[]
├─ reference_scope und reference_role
├─ evidence_cutoff_event_id
├─ reference_asset_ids[]
├─ created_at
└─ status: active | superseded
```

Erst nach dieser Bootstrap-Revision dürfen vollständig abgeschlossene Reviews
reguläre Image-Analysis-Jobs auslösen. Positive Gesamtbildreferenzen stammen aus
kompatiblen Keeps, Favorites oder `APPROVED ChampionRevisionen`; ihre Stärke
bleibt unterscheidbar. Ein begründetes Reject darf nur seine explizite negative
oder achsenspezifische Evidence speisen. So kann ein wegen kaputter Hände
abgelehntes Bild positive Style-Evidence tragen, ohne positive Assetreferenz zu
werden. `wrong_artstyle` entsteht nur aus einem entsprechenden Human-Grund.
Skip und unvollständiger Review erzeugen keinen Bildjob.

Eine `APPROVED ChampionRevision` kann eine verlorene oder migrierte
Referenzprojektion rebuilden, ist in einem sauberen Save aber selbst Ergebnis
des Human-in-the-loop-Pfads. Vorhandenes kompatibles Legacy-Referenzmaterial ist
der ausdrücklich begrenzte dritte Herkunftspfad eines Legacy-fähigen
Entwicklungs- oder Importkontexts.

Die Aktivierung ist scopegebunden. Eine Human-Beobachtung schaltet nur ihre
deklarierte Character-/Referenzrolle und ihren Content-/Style-Kontext frei.
Andere Scopes bleiben `waiting_for_human_evidence`; eine Übertragung
benötigt eine ausdrücklich versionierte Compatibility-Regel und geschieht nie
still.

Ein Job ist durch Source Hash, Asset-/Crop-ID, Scope, logischen Raum,
Modell-ID/-Revision, Preprocessingrevision und erwartete Dimension idempotent.
Lease, Retry, Timeout und Fehlercode sind persistent. Der Worker besitzt keinen
direkten Schreibzugriff auf die Spieldatenbank. Alle Bilder vor dem ersten
gültigen Human-Bootstrap laufen ohne Image-Embedding-Diagnostik; die
schemaförmige VLM-Beschreibung und ihr getrennter Textvektor bleiben nach
Output-Ingest erlaubt. Nach der Bootstrap-Revision darf ein Review bei
nachlaufender Image-Embedding-Diagnostik sichtbar sein; der vollständige
M6-Diagnosereport und das Gate warten jedoch auf alle für den Vergleich
verlangten Jobs.

Der Mehrwert bleibt diagnostisch und retrievalbezogen:

- sichtbare Größe des Control-/Challenger-Deltas messen,
- Identity-Konsistenz über Seeds/Batches und Trennung zwischen Figuren prüfen,
- Style Drift gegen positive und bewusst falsche Referenzprototypen markieren,
- Near-Duplicates beziehungsweise zu geringe Variation finden,
- auffällige Attribute und Content-Mismatches als Befund für Monitor und
  Recovery bereitstellen.

Kein Embedding, Tag oder Ähnlichkeitsscore bewertet Geschmack, setzt Canon,
promotet einen Challenger, erfüllt Readiness oder trifft eine Safety-Entscheidung.

## Retrieval-Domänen

- World Canon,
- Character Knowledge und Beliefs,
- Character Memories,
- Prompt- und Recipe-Evidenz,
- Bildähnlichkeit und Style-Evidenz,
- negative Fehler- und Recovery-Evidenz.

Prompt- und Recipe-Retrieval verwendet zur Runtime ausschließlich validierte,
materialisierte Inhalte des aktuellen Saves beziehungsweise ausdrücklich
übernommene persönliche NG+-Evidence. Sein Textindex startet leer und wird erst
nach erfolgreicher Materialisierung oder explizitem Import rebuildbar erzeugt.
Beim leeren Save erhält der Prompt Author nur `VisualSpec`, authored Locks, Task
Contract und `PromptDialectPack`. Das alte Entwicklungskorpus, seine Embeddings
und konkreten Kombinationen bleiben unerreichbar, solange sie nicht bewusst als
ImportCandidates durch denselben Validator übernommen wurden.

Text- und Bildembeddings besitzen getrennte Räume und Modellversionen.
Kosinusähnlichkeit erzeugt Kandidaten, aber niemals Wahrheit oder einen
Stateübergang; insbesondere werden semantisch ähnliche Playground-Komponenten
nicht automatisch gleichgesetzt oder zusammengeführt. Harte Character-, Canon-, Zeit-, Scope- und
Compatibility-Filter laufen vor dem Ranking. L2-Normalisierung, kompatible
Modell-/Preprocessingrevisionen, taskgebundene Schwellen, relative Margins,
rankbasierte Fusion, Human-Referenzsets und Abstention stehen vollständig in
[`deck-building-embeddings-and-llm-context.md`](deck-building-embeddings-and-llm-context.md).

Ab Schema 53 ist diese Grenze relational erzwungen. Dokumente besitzen genau
eine typisierte `EmbeddingSource`; Retrievalqueries und ihre Vektoren werden
getrennt persistiert und dürfen nie als Dokumentindexmitglieder erscheinen.
Campaign-, Character-, Scope- und Cohort-Gültigkeit gehört zur
Indexmitgliedschaft beziehungsweise Context-Bindung und nicht zur
Vektoridentität. Auswahlbelege und ContextPacks referenzieren ihre tatsächlich
übertragenen Quellen über Foreign Keys. Nicht eindeutig kanonisierbare
Altquellen bleiben nicht proof-fähige HistoricalSnapshots; nicht
materialisierte World-, Memory- oder Knowledge-Quellen erzeugen eine
Abstention. Die LLM erhält dadurch ausschließlich veröffentlichte relationale
Quellen und niemals eine JSON-ID, die der Runtimegraph nicht auflösen kann.

## Recovery

### Technische Wiederaufnahme, keine fachliche Recovery-Domäne

Rejects und technische Bildfehler eröffnen keinen RecoveryCase und keine eigene
Karte. Sie werden als Human Evidence beziehungsweise technischer Befund durch
dieselbe rollierende Kandidatenplanung ausgewertet. Prompt-, Weight-, Sampler-
und Render-Fragen sind versionierte normale Questfragen. Ein LLM darf
semantische Blockänderungen vorschlagen, aber keine Seeds, numerischen Gewichte,
Recipes, Kompatibilitätsregeln oder Freigaben bestimmen.

Recovery bezeichnet im aktiven Vertrag ausschließlich die Wiederaufnahme
bereits materialisierter und autorisierter Providerarbeit: dieselben Recipes,
Seeds und Slotbindungen werden nach Queue-/History-/Output-Reconciliation über
Guardian fortgesetzt. Es entsteht keine kreative Entscheidung und keine zweite
Generierungspipeline. Profil-, Trial- und Promotion-Semantik stehen in
[`10-generation-profiles-and-trials.md`](generation-profiles-and-trials.md).

## Scheduler

Bildgenerierung, lokales LLM, Image Embeddings und LoRA-Training teilen
gegebenenfalls dieselbe GPU. Domain Planner erzeugen nur deklarative
`WorkIntent`s. Der deterministische `OrchestrationGuardian` autorisiert nach
Contract-, Revisions-, Capability-, Policy-, Ressourcen- und Stalenessprüfung
den nächsten begrenzten Schritt; der Submission Scheduler ordnet ausschließlich
bereits autorisierte Arbeit. Der `LocalAiOrchestrator` projiziert die konkrete
Funktionsfähigkeit. LM Studio besitzt Modelllaufzeit und Load/Unload,
ComfyUI besitzt Workflows und Ausführungsqueue, der Docker-Worker besitzt seine
Bildinferenz. Der Orchestrator benötigt:

- Prioritätsklassen für sichtbaren Spielerfortschritt,
- Queue- und Backpressure-Limits,
- Abbruch und Wiederaufnahme,
- persistente Lease-/Retry-/Timeout-Semantik für Image-Embedding-Jobs,
- lokalen Modell- beziehungsweise authored Fallback ohne Cloudroute,
- messbare Warte- und Laufzeiten,
- und reproduzierbare Jobprovenienz.

Das initiale Ressourcenprofil erlaubt auf der RTX 3060 genau eine schwere
GPU-Klasse gleichzeitig: ComfyUI-Generation **oder** LM-Studio-LLM **oder**
Docker-VLM **oder** Docker-Image-Embedding-Batch. Qwen3-Embedding-0.6B läuft
CPU-first und darf deshalb verfügbar bleiben. Der Guardian hält eine
konfigurierte VRAM-Reserve, priorisiert sichtbaren Spielerfortschritt, fordert
kontrolliertes Load/Unload mit Idle-TTL an und startet niemals aufgrund einer
bloßen Soll-/Ist-Differenz parallele GPU-Arbeit. Erst reale Messungen dürfen eine
weniger konservative Parallelität freigeben.

Bei ComfyUI wird die Reserve gegen den vom Provider über `/system_stats`
gemeldeten allokierbaren CUDA-Speicher geprüft. Der globale Windows-/WDDM-
Desktopverbrauch ist weiterhin Diagnosewert, aber kein zweites, zusätzliches
8-GiB-Arbeitsbudget. Damit blockiert ein normaler Browser-/Desktop-Grundzustand
keine ansonsten zulässige Generation. Für LM Studio und Docker gelten weiterhin
ihre eigenen global gemessenen Load-/Unload-Budgets; eine schwere Klasse bleibt
zu jedem Zeitpunkt exklusiv.

Von ComfyUI nach einem fertigen Viererbatch absichtlich resident gehaltene
Torch-Gewichte gelten ebenfalls nicht als Fremdmodell. Vor dem nächsten
logischen Batch darf der Guardian sie ausschließlich bei leerer Providerqueue
über `/free` entladen und danach neu messen. Laufende oder wartende Prompts
werden nie unterbrochen.

Ein fertig materialisierter Prompt darf auch bei später nicht verfügbarem LM
Studio an ComfyUI gehen. Neue Prompt-Machine- oder Character-Speaker-Aufträge
bleiben dagegen funktionsbezogen blockiert. Ein ComfyUI-Job darf nicht deshalb
abgebrochen werden, weil ein anderes LM-Studio-Modell ausgewählt wurde.

Der vollständige Work-, Monitoring- und Recovery-Lifecycle steht in
[`orchestration-guardian-and-monitoring.md`](orchestration-guardian-and-monitoring.md).

## Sicherheits- und Leak-Tests

1. Scene Realizer und Character Speaker können kein Gate erfüllen oder
   Relationship State setzen.
2. Prompt Author kann keine unbekannte Content-ID einschleusen.
3. Eine Figur erhält keine Memory, an der sie nicht beteiligt war.
4. World Secrets werden erst nach authored Freigabe in Context Packs geliefert.
5. Ungültiger Structured Output löst Reparatur oder deterministischen Fallback
   aus, aber keine stille Freitextübernahme.
6. Embedding-Neubau verändert keine Source-of-Truth-Events.
7. Kein Call verlässt im local-only MVP den konfigurierten LM-Studio-Endpunkt.
8. Scene Realizer und Character Speaker können Thema, erlaubte Beatfamilie,
   Reveal, Outcome und Sessionlimit nicht erweitern.
9. Ein nicht erlaubter Userintent erzeugt Redirect, Refuse oder
   `no_evidence`, aber keine neue Story.
10. Derselbe Intent mehrfach innerhalb einer Session überschreitet weder
    Effect Budget noch einmalige Outcome-Anwendung.
11. Ein Release-Paket enthält keine Zeile, kein Embedding und keine konkrete
    Character-/Outfit-/Scene-Combo des Prompt-Entwicklungskorpus.
12. Corpus-Leak-Tests erkennen exakte Prompttreffer, seltene N-Gramme und
    charakteristische Combo-Signaturen im `PromptDialectPack` und in
    synthetischen Beispielen.
13. Ein leerer Save kann einen Character-Prompt aus `VisualSpec` und
    `PromptDialectPack` erzeugen, ohne eine Seed-Datenbank zu öffnen.
14. Der LLM-Output kann weder numerische Weight Policy noch persistierte IDs
    oder Compilerreihenfolge überschreiben.
15. Kein produktiver Structured-Output-Call verlässt sich ausschließlich auf
    eine JSON-Anweisung im Prompt; Schema-ID, Hash und `response_format` sind im
    Request- und Ergebnisreceipt nachweisbar.

## Noch zu kalibrieren

- Capability-Fixtures und Mindestwerte pro logischer LLM-Rolle,
- Capability-Mindestwerte und finale gepinnte Quantisierungsrevisionen der
  festgelegten Qwen3-14B-, Qwen3-VL-8B- und Qwen3-Embedding-Bindungen,
- konkrete Destillationsmetriken, synthetische Beispiele und Leak-Schwellen des
  `PromptDialectPack`,
- konkrete Vector-Store-Implementierung und Rebuild-/Migrationsprofil,
- finale Modellrevisionen, Preprocessingrevisionen und Schwellen des
  SigLIP2-/CCIP-/WD-Bake-offs sowie Freigabe der CCIP-Lizenz für den
  Distributionspfad,
- Token Budgets und Latenzgrenzen,
- Confidence-/Abstention-Schwellen,
- sowie Aufbewahrung und Datenschutz für Cloud-Requests.

## In Schema 56 eingeführte Validierung, unter Schema 57 ausgeführt

Schema 56 bezeichnet hier die Einführung der Receipt- und
Route-Exhaustion-Strukturen. Die aktuelle Runtime- und Persistenzautorität ist
Schema 57.

Jeder verwaltete M6-Modellcall schreibt je durchlaufener Grenze ein
`ProposalValidationReceipt`. Token-Preflight, Providerantwort, Structured
Output, Entscheidungssemantik, semantische Dublette, Batch-Judge, Recipe-Diff
und ComfyUI-Handoff bleiben getrennt. Das Receipt enthält ausschließlich IDs,
Hashes, Regelcodes, Tokenzahlen und Laufzeiten; Rohprompt und Rohantwort bleiben
im geschützten Call-Journal.

`abstain` ist nur mit nicht leerer Begründung gültig. Ein unbegründetes
`abstain` erhält genau eine gezielte Korrektur. Normalisierte semantische
Signaturen erkennen gleichwertige No-op-, Peer- oder Aspect-Mutationen auch bei
abweichender Formulierung. Nach drei tatsächlich empfangenen unbrauchbaren
Antworten wird die Route als `proposal_exhausted` abgeschlossen und für
Evidence-Head plus Supply-Slot ausgeschlossen. Der Nachfolger wählt eine andere
kompatible Experimentfamilie; Candidate und Component werden nicht abgewertet.

Slot- und Aspect-Aufrufe verwenden das 4.096-Profil. Der gemeinsame kompakte
Batch-Judge verwendet ausschließlich das qualifizierte 8.192-Profil mit
maximal 7.200 Input- und 512 Outputtokens. Ein technischer Preflight-Abbruch ist
`not_submitted`; eine belegte Providerantwort ist kein unbekannter Ausgang.

Ein eingefrorener, vollständig validierter `prompt_composition`- oder
`semantic_exploration`-Candidate wird deterministisch übernommen. Dafür werden
weder Prompt Machine noch Batch-Judge aufgerufen; Evidence-Aliasse und
Auswahlbegründung stammen aus dem persistierten Evidence-Head. LM Studio wird
nur für echte sprachliche Mutation, Aspect-/Component-Evolution, Authoring oder
ein begründetes `abstain` verwendet. Der Judge ist nur erforderlich, wenn
mindestens ein Arm eine modellgenerierte semantische Änderung enthält.

Die LM-Lifecycle-Autorität ist die exakte Runtime-ID. Eine Instanz darf nur dann
als Chronicle-eigen profilübergreifend entladen werden, wenn diese konkrete ID
im aktuellen Prozess bekannt oder in einem Chronicle-Lifecycle persistiert ist.
Ein Namenspräfix allein verleiht keine Ownership und eine fremde Instanz bleibt
unangetastet. Wartende Providerarbeit setzt denselben Attempt fort; angenommene
Providerarbeit wird über ihre persistierte ID reattached. Ein terminaler
Pre-Provider-Attempt ohne materialisierten Plan, Session, Review, Credit oder
Providerbilder erhält append-only genau einen deduplizierten Nachfolger.
