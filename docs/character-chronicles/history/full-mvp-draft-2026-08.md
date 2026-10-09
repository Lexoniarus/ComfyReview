# ComfyReview – vollständiger MVP-Zielentwurf: Chronicle, Chat und Prompt Recovery

**Dokumentklasse:** `HISTORICAL_EVIDENCE` · **Rolle:** historischer Gesamtentwurf, kein aktueller MVP-Vertrag.

> **Historische Konzeptquelle (neu eingeordnet 2026-10-09):** Dieses August-2026-Langdokument enthält Ideen und technische Annahmen aus früheren ComfyReview-/Chronicle-Überlegungen, einschließlich einer **inzwischen verworfenen Character-Chronicles-Entwicklungsrichtung**. **ComfyReview wird aktuell weiterentwickelt und soll langfristig zu Character Chronicles werden**, aber nicht durch verpflichtende Übernahme dieses alten MVP-Plans. Der damalige „autoritative“ Wortlaut ist historische Quelle, **kein** bestätigter heutiger Ablauf, keine bindende Schema-/UI-/Workerarchitektur und kein implementierter aktueller Produktstand. [Projektentwicklung](../../PROJECT_EVOLUTION.md) · [Ideensammlung](../README.md) · [Entscheidungsregeln](../../DECISION_POLICY.md).

Status: Konzeptentwurf  
Stand: 28. August 2026

Teils veraltet und überholt

> **Verbindliche Terminologiekorrektur:** Der Dateiname und ältere
> `Post-MVP`-Formulierungen sind historisch. Der hier beschriebene
> Chronicle-/VN-/Schuljahres-Ansatz einschließlich der begrenzten LLM-Rollen ist
> der aktuelle vollständige MVP-Zielscope. Der bereits funktionierende
> bildzentrierte Einzel-Character-Loop ist seine technische Baseline, kein
> konkurrierender finaler MVP-Scope.

Modulare Zielarchitektur, Roadmap und Traceability:
[`../README.md`](../README.md). Dieses Langdokument bleibt
als Herleitung und Detailreferenz erhalten; neue implementierungsrelevante
Entscheidungen werden primär im zuständigen Modulvertrag gepflegt.

Arbeitstitel des Gesamtspiels: **Character Chronicle: Memory Trials**  
Der Arbeitstitel ist vorerst final festgelegt.

**Autoritative Zielkorrektur vom 26. August 2026:** Historische Bilder sind im
zukünftigen System nur ein optionaler Importpfad und keine Standardprogression.
Die heutigen Prompt-, Combo-Prompt- und Playground-Datenbanken definieren die
fachlichen Ausgangsschemata, werden aber weder als vorbefüllte Datenbankdateien
noch mit kuratierten Beispielinhalten ausgeliefert. Das Spiel erzeugt und
entwickelt persönliche Datenbanken aus Spielerbewertungen sowie aus
versionierten Prompt-, Weighting- und Workflow-/KSampler-Trys. Das
Outcome eines vollständigen einzelnen Character-Foundation-Runs ist eine
versionierte, validierte Character-LoRA. Im Chronicle-Schuljahres-Run werden dagegen alle
sechzehn Character-Outcomes am Jahresende getrennt ausgewertet; dadurch können
null, eine oder mehrere validierte Character-LoRAs als wählbare
New-Game-Plus-Basen entstehen. Der Spieler entscheidet selbst, welche
qualifizierten Figuren übernommen werden.
Bei widersprüchlichen älteren Aussagen in diesem Dokument gilt
[`../sources/year-end-lora-and-new-game-plus.md`](../sources/year-end-lora-and-new-game-plus.md).
Der verbindliche Lern- und Tuningloop ist in
[`../sources/rolling-m6-learning-loop.md`](../sources/rolling-m6-learning-loop.md)
beschrieben.

Terminologiehinweis: Die im MVP sichtbaren historischen **Memory Trials** werden intern als `campaign_archive_*` beziehungsweise Archive Validation gespeichert. Die in diesem Dokument beschriebenen späteren Memory Trials betreffen Persönlichkeitsachsen und Relationship-/Story-State. Beide Systeme dürfen dieselbe verständliche UI-Sprache verwenden, besitzen aber getrennte Domänenobjekte und Evidenzräume.

## 1. Einordnung

Dieses Dokument beschreibt den vollständigen MVP auf Basis des bereits
erreichten Bildloops. Die Chronicle-Stufe ergänzt:

- eine geführte, chatbasierte Character Creation,
- genau 16 feste Persönlichkeitsprofile im Anime-Kontext,
- einen kontrollierten Übergang vom Character Creator zum Gespräch mit der Figur,
- zwei eng begrenzte LLM-Rollen mit austauschbaren lokalen oder Cloud-Providern,
- hardcodierte Story- und Progressionslogik,
- sowie Rating-basierte Prompt-Recovery.

Die internen Prompt-, Combo-Prompt- und Playground-Datenbanken werden nicht als
fertig befüllte Produktdaten an den User ausgeliefert. Sie werden im lokalen
Backend für den jeweiligen Spieler beziehungsweise Spielstand aufgebaut und
fortgeschrieben. Der User interagiert mit Figuren, Bildern, verständlichen
Entscheidungen und Ratings, aber nicht mit Diffusion-Prompts oder internen
Komponenten-IDs.

## 2. Leitprinzipien

1. **Bilder bleiben der zentrale Spielgegenstand.** Dialog und Story führen zu visuellen Trys, Bewertungen, stabileren Figurenbildern und schließlich besseren LoRA-Datensätzen.
2. **Der Ablauf ist geführt.** Ein hardcodierter Game Director bestimmt Szenen, Fortschritt, zulässige Entscheidungen und Konsequenzen.
3. **LLMs besitzen keine Spielhoheit.** Sie formulieren Character-Dialog oder kompilieren einen Bildprompt innerhalb enger Vorgaben.
4. **Es gibt genau einen festen Prompt-Style.** Wrong Artstyle bleibt ein klarer Fehler und kein alternatives Spielergebnis.
5. **Es gibt genau 16 zulässige Personality-Profile.** Jeder Character-Slot besitzt eines davon als Base-Ausgangspunkt. Entwicklung darf den aktuellen Typ ausschließlich durch kontinuierliche Bewegung auf den vier bestehenden Achsen in einen anderen dieser 16 Typen überführen; ein siebzehntes Profil oder eine Achse außerhalb des Systems entsteht nie.
6. **Rating-Daten erzeugen Aktionen.** Ein Fehlergrund führt zu einem passenden Recovery-Pfad und bleibt als negative Evidenz erhalten.
7. **Generierungszeit ist messbar.** Sie beeinflusst die Wahl zwischen qualitativ vergleichbaren Recovery- und Generierungswegen.

## 3. Geführte Character Creation

### 3.1 Erste Entscheidung: Geschlecht des Spielercharakters

Jeder neue Save beginnt mit einer direkten Wahl für den Spielercharakter:

- männlich,
- oder weiblich.

Diese Entscheidung betrifft nicht das gewünschte Geschlecht einer einzelnen Gegenfigur. Sie steuert den Cast Assembler: Der aktive Cast besteht primär aus Figuren des jeweils anderen Geschlechts und zusätzlich aus einigen Figuren desselben Geschlechts. Sämtliche 16 Personality-Profile bleiben unabhängig von der Wahl als unterschiedliche Base-Ausgangsprofile vertreten. Die daraus entwickelten Current Profiles dürfen sich im weiteren Spielverlauf doppeln oder zeitweise fehlen.

Die Geschlechtswahl des Spielercharakters wird im Prolog vor der Cast-Zusammenstellung bestätigt und danach als Save Canon behandelt. Das Spiel stellt keine zusätzliche Frage nach dem bevorzugten Geschlecht der Gegenfiguren.

### 3.2 Die 16 Persönlichkeitsprofile

Das Spiel verwendet als festes Raster:

#### Analysten

- Architekt – INTJ
- Logiker – INTP
- Kommandeur – ENTJ
- Debattierer – ENTP

#### Diplomaten

- Advokat – INFJ
- Mediator – INFP
- Protagonist – ENFJ
- Aktivist – ENFP

#### Wächter

- Logistiker – ISTJ
- Verteidiger – ISFJ
- Exekutive – ESTJ
- Konsul – ESFJ

#### Forscher

- Virtuose – ISTP
- Abenteurer – ISFP
- Unternehmer – ESTP
- Entertainer – ESFP

Die Profile werden für das Spiel eigenständig beschrieben und in einen Anime-Kontext übersetzt. Namen, Texte, Illustrationen und Testfragen externer Angebote werden nicht kopiert. Jedes Profil erhält einen internen, versionierten Profile Pack mit:

- Verhaltensregeln,
- Dialogtendenzen,
- Beziehungsmustern,
- typischen Konflikten,
- Grenzen und Reaktionen,
- Story-Ereignissen,
- möglichen Entwicklungsbögen,
- sowie visuellen Inszenierungstendenzen.

Eine Anime-Inszenierung ist ein dramaturgischer Ausgangspunkt und kein starrer Beruf oder Stereotyp. Derselbe Typ kann viele unterschiedliche Figuren hervorbringen.

Ein optionaler Assertive-/Turbulent-Wert ist nur ein versteckter Intensitäts- oder Entwicklungsmodifikator. Er erzeugt keine zusätzlichen Basisprofile.

### 3.3 Kontrollierter Zufall

Zufall darf Vielfalt erzeugen, aber keine Regeln überschreiben. Randomisiert werden können:

- konkrete Biografieelemente aus erlaubten Pools,
- Hobbys und Gewohnheiten,
- anfängliche Beziehungssituation,
- visuelle Kandidaten innerhalb des jeweils ausgewählten Gendered Character Blueprints,
- Reihenfolge geeigneter Story-Ereignisse,
- sowie Varianten von Outfit, Pose, Expression und Szene.

Nicht zufällig veränderbar sind:

- der feste Prompt-Style,
- bereits bestätigter Locked Canon,
- die Zahl und Definition der 16 Profile,
- technische Sicherheits- und Validierungsregeln,
- sowie die Voraussetzungen für Progression und LoRA-Freigabe.

## 4. Hardcodierter Game Director

Der Game Director ist deterministische Anwendungslogik und kein LLM. Er besitzt die alleinige Kontrolle über:

- Kapitel und Szenen,
- angebotene Userentscheidungen,
- feste Profilzuordnung, Entwicklungs-Evidenz und Profil-Reveal,
- Character State und Relationship State,
- Freischaltungen,
- visuelle Trys,
- Canon-Änderungen,
- Rating-Auswertung,
- Recovery-Strategien,
- Dataset-Zulassung,
- sowie Progression und Belohnungen.

### 4.1 Gemeinsames Story-Skelett

Die 16 Profile werden nicht als 16 vollständig getrennte Programme implementiert. Ein gemeinsames Story-Skelett lädt profilabhängige Profile Packs und Ereignisse:

```text
Prolog: Spielergeschlecht, Name, Präferenz-Choices und Cast Assembly
→ Kapitel 1: erste Begegnungen und soziales Verhalten
→ Kapitel 2: Wahrnehmung und Interessen
→ Kapitel 3: Entscheidungen und Konflikte
→ Kapitel 4: Alltag und Planung
→ Enthüllung: verborgenes Grundprofil wird für den Spieler zunehmend lesbar
→ profilabhängiger Entwicklungsbogen
→ dauerhafter Character- und Relationship-Loop
```

Frühe Szenen können universell oder gruppenspezifisch sein. Der Director kennt Base Profile, aktuelle Achsenlage und daraus abgeleitetes Current Profile von Beginn an. Er verwendet das zum Current Profile gehörende Behavior Pack, ohne Base-Herkunft, Character Brand oder bisherige Entwicklung zu verlieren. Mit wachsender gemeinsamer Erfahrung darf er deutlichere profilspezifische Ereignisse priorisieren und Base-Herkunft sowie aktuelle Entwicklung für den Spieler schrittweise erkennbar machen.

### 4.2 Hardcodierter Welterzähler

Der Welterzähler benötigt kein eigenes LLM. Szenenbeschreibung, Übergänge, Aufgaben und Konsequenzen stammen aus authorisierten Templates und Story-Daten.

Varianten entstehen aus geprüften Slots wie:

```text
[Ort] + [Tageszeit] + [aktueller Zustand] + [Story-Ereignis]
```

Nur vorhandene, kompatible Einträge dürfen eingesetzt werden. Dadurch bleibt die Geschichte reproduzierbar, testbar und profilecht.

## 5. Zwei begrenzte LLM-Rollen

### 5.1 Character Speaker

Der Character Speaker formuliert ausschließlich die sichtbare Antwort der Figur. Er erhält:

- bestätigten Character Core,
- festes Persönlichkeitsprofil,
- aktuelle Szene und erlaubte Fakten,
- Current State,
- Relationship State,
- ausgewählte Erinnerungen,
- die vom Director vorgegebene Aussageabsicht,
- Sprachstil und Grenzen.

Er darf keine neuen Canon-Fakten, Story-Ereignisse, Outfits oder Orte festlegen. Eine mögliche strukturierte Ausgabe ist:

```json
{
  "dialogue": "Ich habe nicht vergessen, was gestern passiert ist ... Warum ist dir das plötzlich so wichtig?",
  "expression": "guarded",
  "relationship_signal": "seeks_explanation"
}
```

Alle Tags werden gegen erlaubte Werte validiert. Der Director entscheidet anschließend über Zustandsänderungen.

### 5.2 Playground Author und Prompt Generator

Die zweite LLM-Rolle ist kein freier Story- oder Einzelbildgenerator. Sie ist ein strukturierter Playground Author, der Userantworten aus dem geführten Chat in neue persönliche Content-Drafts übersetzt.

Diese Rolle erzeugt:

- Character Drafts,
- Scene Drafts,
- Outfit Drafts,
- Pose Drafts,
- Expression Drafts,
- Lighting Drafts,
- Modifier Drafts,
- sowie Vorschläge für storybezogene Kombinationen vorhandener Komponenten.

Ihre Eingaben enthalten nur:

- den vom Director festgelegten Ziel-Slot,
- ausdrückliche Userangaben und bestehende Locks,
- das Schema des jeweiligen Playground-Kinds,
- Tag-, Konflikt- und Promptregeln,
- passende bereits freigegebene persönliche Komponenten,
- den aktuellen Storybedarf,
- und die feste Style-Version.

Eine mögliche strukturierte Ausgabe ist:

```json
{
  "kind": "outfit",
  "name": "Dark Blue Gold-Trim Jacket",
  "spec": {
    "primary_color": "dark_navy_blue",
    "accent_color": "muted_gold",
    "style": "understated_elegant",
    "avoid": ["military"]
  },
  "tags": ["jacket", "dark_blue", "gold_trim", "elegant"],
  "positive_fragment": "fitted dark navy blue jacket with subtle muted gold stitching",
  "negative_fragment": "military uniform, medals, epaulettes",
  "missing_fields": []
}
```

Das Modell schreibt nie direkt in SQLite. Seine Ausgabe wird als Draft gespeichert, gegen Schema und Regeln geprüft, mit Bildern getestet und erst nach Review als persönlicher Playground-Inhalt freigeschaltet.

Für eine konkrete Bildgenerierung darf dieselbe LLM-Rolle aus einer validierten Visual Specification die benötigten Komponentenfragmente formulieren. Der finale Prompt entsteht weiterhin deterministisch aus festem Style Core, Character Core und freigegebenen Playground-Items.

### 5.3 Logische Rollen statt zwingend zwei geladener Modelle

Character Speaker und Playground Author sind zwei getrennte Kontexte und Verträge. Sie müssen anfangs nicht zwingend zwei verschiedene Modelle sein. Auf lokaler Hardware kann dasselbe geladene Modell mit getrennten Systemprompts verwendet werden, um Modellwechsel, VRAM-Verbrauch und Latenz zu reduzieren.

Später kann der Playground Author auf ein kleineres, schnelleres lokales oder containerisiertes Modell wechseln, wenn dessen strukturierte Draft- und Prompt-Ausgaben ausreichend stabil sind.

<a id="6-post-mvp-kernloop"></a>

## 6. Chronicle-Kernloop des vollständigen MVP

```text
Director wählt das nächste authorisierte Story-Ereignis
→ Erzähler fragt eine storyrelevante Entscheidung oder fehlende Definition spielerisch ab
→ User antwortet frei oder wählt eine sichtbare Option
→ Director aktualisiert Story-, Profil- und Input-State deterministisch
→ Playground Author erzeugt bei Bedarf einen Component- oder Combo-Draft
→ Server validiert den Draft und plant einen visuellen Try
→ Character Speaker formuliert bei ausreichender Character-Reife eine kontrollierte Reaktion
→ persönliche Playground- und Combo-Daten liefern erlaubte Komponenten und Evidenz
→ Promptfragmente werden validiert und deterministisch kompiliert
→ ComfyUI erzeugt das Bild
→ User bewertet das Bild innerhalb derselben Chat-Timeline
→ Director wählt Commit-, Progress- oder Recovery-Pfad
```

Jeder visuelle Try soll mindestens einem fachlichen Zweck dienen:

- Character Canon definieren oder prüfen,
- eine Story-Szene visualisieren,
- Outfit, Pose oder Expression freischalten,
- Character-Stabilität testen,
- eine Dataset-Lücke schließen,
- oder einen bekannten Fehler gezielt reparieren.

## 7. Generation Recipe als Recovery-Grundlage

Recovery versucht nicht, einen Prompt nachträglich aus einem Bild zu erraten. Jede Generierung speichert serverseitig ein vollständiges, versioniertes Generation Recipe:

```text
Generation Recipe
├── Character- und Canon-Version
├── Profile Pack und Story Event
├── Scene, Outfit, Pose, Expression und Lighting
├── Style- und Prompt-Compiler-Version
├── positiver und negativer Prompt
├── verwendete Text- und Bildreferenzen
├── Modell, Workflow und Renderparameter
├── Seed
├── Queue-, Render- und Gesamtzeit
└── spätere Ratings und Fehlergründe
```

Der vollständige Prompt und interne Datenbankinhalte werden nicht an den Client ausgeliefert.

## 8. Rating-basierte Prompt-Recovery

### 8.1 Ziel

Ein Rating ist nicht nur Statistik. Es liefert ein strukturiertes Signal dafür:

- welche Teile eines Bildes erhalten werden sollen,
- welcher Fehler behoben werden muss,
- ob ein vollständiger Retry oder eine lokale Reparatur sinnvoll ist,
- welche früheren Rezepte künftig bevorzugt werden,
- und welche Kombinationen als Risiko gelten.

### 8.2 Bewertungsdaten

Jedes bewertete Bild speichert mindestens:

- Entscheidung: Favorite, Keep, Reject, Delete oder Skip,
- primären Fehlergrund,
- optionale sekundäre Fehlergründe,
- bestätigte gute Aspekte,
- Rating-Zeitpunkt,
- Generation Recipe ID,
- Recovery-Wunsch,
- sowie die resultierende Recovery-ID.

Gute Aspekte können separat bestätigt werden:

- Character Identity,
- Gesicht und Haare,
- Artstyle,
- Outfit,
- Pose,
- Expression,
- Hintergrund,
- Lighting,
- Komposition.

So kann ein Bild beispielsweise gute Character Identity, aber fehlerhafte Hände besitzen. Recovery soll dann nicht unnötig den gesamten Character Core verändern.

### 8.3 Recovery-Matrix

| Fehler oder Rating | Primärer Recovery-Pfad | Zu bewahrende Elemente |
|---|---|---|
| Wrong Artstyle | Style Core hart neu einsetzen, widersprechende Tokens entfernen, vollständig regenerieren | Character Canon und gewünschte Komponenten |
| Mixed Artstyle / 3D Drift | Style-Konflikte entfernen und Negative Core verstärken | Character Canon, Szene und Outfit |
| Bad Hands | Hände inpainten; alternativ kompatible Pose oder Crop wählen | Gesicht, Character Identity, Outfit und möglichst Komposition |
| Bad Face / Eyes | Gesicht gezielt inpainten oder mit stärkeren Canon-Referenzen regenerieren | Körper, Outfit, Szene und Lighting |
| Weird Background | Hintergrund inpainten oder Scene Block neu kompilieren | Figur, Pose, Ausdruck und Outfit |
| Wrong Scene | Scene Block ersetzen und vollständig neu generieren | Character Canon, Outfit und gewünschte Story-Absicht |
| Character Drift | Canon-Referenzen und Identity Block priorisieren | gewünschte Szene, Outfit und Ausdruck, sofern konfliktfrei |
| Wrong Character Features | betroffene Canon-Merkmale explizit neu kompilieren | alle bereits korrekten Merkmale |
| Wrong Outfit | Outfit Block ersetzen oder verstärken | Character Identity, Pose, Szene und Ausdruck |
| Wrong Pose | nur eine kompatible Pose aus dem erlaubten Pool einsetzen | Character Identity, Outfit, Szene und Ausdruck |
| Additional Person | Solo-Komposition erzwingen und zusätzliche Personen negativ ausschließen | Hauptfigur und Story-Szene |
| Bad Composition / Crop | Kompositionspreset wechseln und vollständig regenerieren | Character Canon und inhaltliche Komponenten |
| technischer Defekt | identisches Recipe technisch erneut ausführen | alle fachlichen Vorgaben |
| insgesamt schlecht | neues Recipe mit neuem Seed und geprüftem Basispreset | nur Locked Canon und Challenge-Ziel |
| gut mit kleinem lokalen Fehler | Inpainting oder regionale Reparatur | alle bestätigten guten Bereiche |
| gut, aber zu langsam | günstigeren kompatiblen Workflow testen | visuelles Ziel und Qualitätsuntergrenze |

### 8.4 Recovery-Ablauf

```text
Rating oder Delete mit Fehlergrund
→ ursprüngliches Generation Recipe laden
→ positive und negative Aspekte trennen
→ hardcodierte Recovery Policy auswählen
→ passende frühere Erfolgs- und Fehlerrezepte abrufen
→ Recovery Specification erzeugen
→ Specification validieren
→ Prompt Generator kompiliert nur erlaubte Änderungen
→ Full Retry, Variation oder Inpainting ausführen
→ Original und Recovery als zusammengehöriges Paar auswerten
```

Der Prompt Generator wählt die Recovery-Methode nicht selbst. Er erhält bereits eine geprüfte Recovery Specification vom Director.

## 9. Prompt- und Image-RAG für Recovery

RAG dient als Retrieval-Schicht, nicht als Source of Truth.

Für eine Recovery können abgerufen werden:

- erfolgreiche Recipes derselben Figur,
- stabile Recipes mit vergleichbarer Szene oder Pose,
- Canon-Bilder für Character Identity,
- akzeptierte Bilder für Outfit oder Ausdruck,
- frühere Fehler derselben Komponenten,
- sowie Recovery-Paare, bei denen derselbe Fehlertyp bereits behoben wurde.

Positive und negative Bildquellen bleiben getrennt:

- **Visual Canon:** beste bestätigte Identity-Referenzen,
- **Visual Episodes:** akzeptierte Story- und Komponentenbilder,
- **Negative Visual Evidence:** abgelehnte oder gelöschte Bilder mit Fehlergrund,
- **Recovery Pairs:** fehlerhaftes Ausgangsbild plus bewertetes Reparaturergebnis.

Negative Visual Evidence darf nie versehentlich als positive visuelle Referenz für die Figur verwendet werden.

## 10. Umgang mit Delete

`Delete` bedeutet zunächst fachliche Entfernung, nicht sofortige physische Vernichtung.

Ein gelöschtes Bild wird:

- aus Galerie, aktiver Auswahl und LoRA-Album entfernt,
- für das Training gesperrt,
- mit verpflichtendem Fehlergrund versehen,
- zusammen mit seinem Generation Recipe als negative Evidenz erhalten,
- und in einen wiederherstellbaren Quarantäne- oder Trash-Bereich verschoben.

Eine separate Bereinigung darf die Bilddatei später endgültig entfernen. Recipe, Rating, Fehlergrund, Laufzeit und statistische Signale bleiben auch danach erhalten.

## 11. Positive Ratings und bewährte Recipes

Positive Ratings verstärken nicht pauschal den gesamten Prompt. Sie erhöhen gezielt die Evidenz der bestätigten Bestandteile:

- gutes Gesicht stärkt die verwendeten Canon-Referenzen,
- stabiles Outfit stärkt das Outfit Recipe,
- korrekte Szene stärkt Scene Block und Workflow-Kombination,
- stabile Pose stärkt die entsprechende Character-Pose-Kombination,
- schnell und gut erhöht das Ranking des Workflows,
- wiederholt stabile Gesamtresultate werden als Proven Recipe markiert.

Das System führt zunächst keine automatische Modellnachschulung aus. Es lernt durch Retrieval, Ranking und validierte Wiederverwendung. Eine spätere trainierte Preference- oder Prompt-Optimierung ist eine eigenständige Ausbaustufe.

## 12. Generierungszeit als Recovery-Faktor

Für jedes Original- und Recovery-Bild werden gespeichert:

- Queue Time,
- Render Time,
- Total Time,
- Workflow und Hardware-Signatur,
- Auflösung und Batch-Größe,
- sowie brauchbare Bilder pro Renderminute.

Zeit darf Qualitäts- und Identity-Anforderungen nicht überstimmen. Bei vergleichbarer Qualität bevorzugt das System jedoch:

- erfolgreiche Inpainting-Reparatur statt vollständiger Regeneration,
- kleinere kompatible Workflows,
- bewährte Recipes mit geringerer Fehlerrate,
- sowie Promptvarianten mit höherer brauchbarer Ausbeute pro Minute.

## 13. Vorgeschlagene Datenobjekte

### `generation_recipes`

- Recipe ID und Parent Recipe ID,
- Character- und Canon-Version,
- Story Event und Komponenten-IDs,
- Prompt- und Style-Version,
- positiver und negativer Prompt,
- Referenz-IDs,
- Workflow und Renderparameter,
- Seed und Zeitwerte,
- Recipe-Status.

### `image_reviews`

- Image ID und Recipe ID,
- Review-Aktion,
- primärer und sekundäre Fehlergründe,
- bestätigte gute Aspekte,
- Dataset-Zulassung,
- Review-Zeitpunkt.

### `recovery_attempts`

- Ausgangsbild und Ausgangs-Recipe,
- Recovery Policy,
- zu bewahrende und zu ersetzende Felder,
- neues Recipe,
- Recovery-Methode,
- Ergebnisbewertung,
- Qualitäts- und Zeitvergleich.

### `proven_recipes`

- normalisierte Combo-Signatur,
- Character- und Style-Kompatibilität,
- Zahl unabhängiger Seeds,
- Qualitäts- und Stability-Werte,
- Fehlerverteilung,
- mittlere Renderzeit,
- Confidence und letzte Validierung.

### `personality_profile_packs`

- eine der 16 Profile IDs,
- versionierte Verhaltensregeln,
- Voice Guide,
- Beziehungsmuster,
- Story-Ereignisse und Voraussetzungen,
- Konflikt- und Entwicklungsbogen,
- erlaubte Anime-Inszenierungstendenzen.

## 14. Validierungsregeln

Vor jedem Character- oder Generation-Call gelten mindestens folgende Prüfungen:

- nur bekannte IDs und Enum-Werte,
- keine Änderung des Locked Canon ohne explizite Freigabe,
- genau ein gültiges Basisprofil,
- keine Änderung der Geschlechtswahl nach Canon Lock,
- feste und bekannte Style-Version,
- keine negative Evidenz als positive Referenz,
- keine nicht freigeschalteten Komponenten,
- keine widersprüchlichen Outfit-, Pose- oder Scene Blocks,
- begrenzte Ausgabegröße und gültiges JSON,
- Fallback auf authorisiertes Template bei ungültiger LLM-Ausgabe.

Ein fehlgeschlagener LLM-Call darf den Spielfortschritt nicht beschädigen. Der Director kann eine neutrale Template-Antwort oder ein deterministisch kompiliertes Basis-Recipe verwenden.

<a id="15-stufenweise-post-mvp-umsetzung"></a>

## 15. Stufenweise Chronicle-Umsetzung

### Stufe A: Geführter VN-Prolog

- erste Userinteraktion als authored VN-Szene mit Erzähler und Mutter-Silhouette,
- Spielergeschlecht und Name als direkte Startangaben,
- überwiegend sichtbare Auswahlkarten statt freiem Prolog-Chat,
- hardcodierte Input Requirements für die Character-Basics,
- strukturierte Explicit User Locks,
- Playground Author mit validierten Draft-Ausgaben,
- erste Character- und Identity-Bilder.

### Stufe B: Character Chat und Bild-Progression

- Character-Chat-Gate nach ausreichender Character Definition,
- 16 versionierte Personality Behavior Packs,
- Character Speaker mit validierter Ausgabe,
- persönliche Playground SQLite,
- persönliche Combo Prompt DB,
- Bild-Games für Sprites, Outfits, Posen, Expressions und Szenen,
- vollständige Generation Recipes.

### Stufe C: Chronicle-Ready-Gate und Hybrid-VN

- Visual-Readiness-Prüfung,
- VN-Starter-Pack aus freigegebenen Assets,
- Visual Asset Resolver,
- storybezogene On-Demand-Combos,
- Text- und Image-RAG für Canon und persönliche Bibliothek,
- dauerhafter Mix aus VN-Szenen, Character Chat und Bild-Games.

### Stufe D: Rating Recovery

- gute Aspekte zusätzlich zum Fehlergrund erfassen,
- hardcodierte Recovery-Matrix,
- Full Retry, Variation, Inpainting und Cutout-Recovery,
- Recovery Pairs und Proven Recipes,
- Zeit- und Qualitätsvergleich.

### Stufe E: Adaptive Priorisierung

- komponentenbezogene Fehlerwahrscheinlichkeiten,
- Ranking bewährter Recipes und Combos,
- Recovery-Vorschläge anhand ähnlicher Erfolge,
- automatische Wahl des günstigsten ausreichend sicheren Recovery-Pfads,
- spätere Auswertung für LoRA-Dataset- und Workflow-Optimierung.

## 16. Erfolgskriterien

Die Chronicle-Erweiterung innerhalb des vollständigen MVP ist erfolgreich, wenn:

- jede Figur einem von genau 16 Profilen folgt,
- das Geschlecht des Spielercharakters vor Cast Assembly und Character-Aufbau gewählt wird,
- die erste Interaktion als geführter VN-Prolog mit authored Choices beginnt,
- alle erforderlichen Userangaben spielerisch über authorisierte Input Requirements erhoben werden,
- der Director ohne generative Story-Entscheidungen funktioniert,
- Character Speaker und Playground Author nur ihre definierten Aufgaben erfüllen,
- Character Chat und vollständige VN-Darstellung getrennte Readiness-Gates besitzen,
- die Bild-Games den persönlichen VN-Asset-Pool aufbauen,
- persönliche Playground- und Combo-Daten ohne Auslieferung der Entwicklungsdatenbanken entstehen,
- der User keine Prompts schreiben oder interne Prompt-Daten sehen muss,
- jedes Delete einen verwertbaren Fehlergrund besitzt,
- ein Rating einen nachvollziehbaren Recovery-Pfad auslösen kann,
- gute Bildbereiche bei lokalen Fehlern möglichst erhalten bleiben,
- negative Bilder vom LoRA-Dataset ausgeschlossen, aber analytisch nutzbar bleiben,
- Recovery-Ergebnisse gegen ihr Ausgangsbild verglichen werden,
- und Qualität, Stabilität sowie Generierungszeit gemeinsam messbar verbessert werden.

## 17. Noch zu entscheidende Details

- Mit welchen authored Texten und Chronicle-Markern werden Base Profile, Current Profile und qualitative Achsenentwicklung nach ausreichender Bekanntheit sichtbar gemacht?
- Welche konkreten Inputs erhalten pro Blueprint die Gewichtsklassen `weak`, `standard`, `strong` oder `anchor` und welche Influence-Bound-Reaktion folgt daraus?
- Welche Story-Ereignisse sind universell, gruppenspezifisch oder profilspezifisch?
- Welche guten Bildaspekte lassen sich schnell genug einzeln bestätigen?
- Welche Fehler werden zunächst durch Prompt-Retry und welche direkt durch Inpainting behandelt?
- Wann wird ein Recipe als ausreichend bewährt markiert?
- Wie lange bleiben quarantänisierte Bilddateien physisch erhalten?
- Werden beide LLM-Rollen zunächst mit demselben lokalen Modell betrieben?

## 18. Technische Vertiefung: KI-gestützte Visual Novel

### 18.1 Produktarchitektur

Die Chronicle-Erweiterung wird technisch als deterministische Visual Novel mit zwei assistierenden LLM-Rollen umgesetzt.

```text
Eine durchgehende Chat-Timeline
              ↓
Hardcodierter Game Director und Erzähler
      ├── Story Graph und Input Requirements
      ├── Profile Scoring und 16 Behavior Packs
      ├── Character-, Relationship- und Memory-State
      ├── Character Speaker
      └── Playground Author
              ↓
Persönliche Playground SQLite
              ↓
Persönliche Combo Prompt DB
              ↓
Visual Asset Resolver, Image-RAG und Generation Planner
              ↓
Deterministischer Prompt Compiler
              ↓
ComfyUI, Review und Recovery
```

Der Game Director bleibt die einzige Instanz, die verbindliche Spielzustände verändert. LLM-Ausgaben werden als Formulierung, Vorschlag oder Promptfragment behandelt und besitzen ohne Validierung keine Autorität.

### 18.2 Memory Trials als Profil-Gameloop

Die Memory Trials sind authorisierte Anime-Situationen, die gleichzeitig:

- Persönlichkeit sichtbar machen,
- Story-Erinnerungen erzeugen,
- die Beziehung entwickeln,
- visuelle Szenen freischalten,
- und neue Bilder der Figur erzeugen.

Das `BasePersonalityProfile` jeder aktiven Figur ist bereits durch ihren ausgewählten Blueprint festgelegt und wird niemals durch ein LLM bestimmt. Es bleibt als Ausgangspunkt und historischer Rückanker erhalten. Das daraus entwickelte `CurrentPersonalityProfile` darf sich ausschließlich durch gewichtete Bewegung auf den vier bestehenden Achsen verändern. Vier Trial-Gruppen machen diese Achsen sichtbar und sammeln Entwicklungs- sowie Relationship-Evidenz:

```text
Social Trials       → I oder E
Perception Trials   → N oder S
Conflict Trials     → T oder F
Planning Trials     → J oder P
```

Jeder gültige Personality-relevante VN- oder Character-Chat-Input verschiebt genau eine primäre Achse oder stabilisiert deren bestehende Richtung. Andere Achsen dürfen im selben Turn nur stabilisiert werden. Ein einzelner Input erzeugt dadurch keinen großen Sprung, kann aber bei unmittelbarer Grenznähe den Current Type in den direkten Nachbartyp überführen. Ein inkompatibler Einfluss kann von der Figur abgelehnt werden, die bestehende Achsenrichtung stabilisieren, Vertrauen beschädigen oder den Fokus des Schedulers auf eine andere Figur verlagern. Die Trials entwickeln eine bereits vorhandene Person innerhalb des unveränderten 16er-Systems.

```text
Spielergeschlecht und Name wählen
→ authored VN-Prolog sammelt erste Präferenzsignale
→ aktiven Cast aus 32 Gendered Blueprints zusammenstellen
→ erste Character-Bilder generieren und reviewen
→ Character Chat als neue Fähigkeit innerhalb derselben Oberfläche freischalten
→ Bild-Games erzeugen nach und nach Sprites, Outfits, Posen, Expressions und Szenen
→ mehrere Memory Trials liefern Development- und Relationship-Evidenz
→ verborgenes Grundprofil wird für den Spieler zunehmend verständlich
→ Chronicle-Ready-Gate durch ausreichenden visuellen Content erreichen
→ VN-Darstellung freischalten
→ dauerhafter Mix aus VN-Szenen, Character Chat und Bild-Games
```

### 18.3 Authorisierte Story Graphs

Jede Story-Szene ist ein strukturiertes, versioniertes Content-Objekt. Die sichtbare Narration und die möglichen Konsequenzen werden authored und nicht frei generiert.

```json
{
  "scene_id": "boundary_trial_02",
  "chapter": "conflict",
  "narration_key": "boundary_trial_02_intro",
  "choices": [
    {
      "id": "intervene_directly",
      "development_impulse": {
        "social_initiative": 1,
        "conflict_directness": 2
      },
      "relationship_delta": 1,
      "next_scene": "boundary_trial_02_direct"
    },
    {
      "id": "observe_first",
      "development_impulse": {
        "reflection": 1,
        "interpretation": 1
      },
      "relationship_delta": 0,
      "next_scene": "boundary_trial_02_observe"
    }
  ]
}
```

Das Story-System verwendet:

- gemeinsame Prolog-Szenen,
- gruppenspezifische Szenen für Analysten, Diplomaten, Wächter und Forscher,
- profilspezifische Szenen mit zunehmender Reveal-Tiefe,
- wiederverwendbare Trial-Module,
- geschlechtsabhängige visuelle Varianten,
- sowie kontrollierte Random Events aus kompatiblen Pools.

Der Character Speaker darf `next_scene`, Evidenzwerte, Relationship-Werte oder Freischaltungen niemals bestimmen.

### 18.4 Vertrag des Character Speakers

Der Director legt die kommunikative Absicht fest. Der Character Speaker formuliert lediglich eine passende Äußerung in der bestätigten Figurenstimme.

```json
{
  "speech_intent": "refuse_but_show_curiosity",
  "profile": "INTJ",
  "tone": "guarded",
  "relationship_level": 2,
  "allowed_facts": ["previous_rooftop_argument"],
  "max_sentences": 3
}
```

Eine gültige Ausgabe enthält nur erlaubte Felder:

```json
{
  "dialogue": "So einfach ist das nicht. Aber wenn du wirklich einen Plan hast, höre ich ihn mir an.",
  "expression_id": "guarded_curiosity"
}
```

Validiert werden mindestens:

- maximale Länge,
- bekannte Expression ID,
- keine neuen Canon-Fakten,
- keine technischen oder internen Begriffe,
- keine Änderung des Spielzustands,
- Einhaltung von Grenzen und Voice Guide.

Bei ungültiger Ausgabe verwendet der Director eine authorisierte Template-Zeile. Ein fehlgeschlagener LLM-Call blockiert dadurch weder Szene noch Spielstand.

### 18.5 Deterministische und vorgeschlagene Erinnerungen

Story-Erinnerungen entstehen direkt aus authorisierten Events und benötigen kein LLM:

```text
Der Spieler verteidigte die Figur im Boundary Trial.
```

In späteren Character-Interaktions-Turns innerhalb derselben geführten Chat-Timeline darf der Character Speaker lediglich strukturierte Memory Candidates vorschlagen:

```json
{
  "memory_candidate": {
    "type": "user_preference",
    "fact": "Der User mag nächtliche Zugfahrten.",
    "confidence": 0.76
  }
}
```

Vor dem Speichern prüft das Backend:

- ob die Information neu ist,
- ob sie bestehendem Canon widerspricht,
- ob sie momentan, episodisch oder langfristig relevant ist,
- ob sie sensibel oder identitätsverändernd ist,
- ob Wiederholung oder ausdrückliche Bestätigung vorliegt,
- und ob eine sichtbare Userbestätigung erforderlich ist.

Das LLM schreibt nie direkt in Locked Canon oder Langzeiterinnerungen.

### 18.6 Text-Memory-Retrieval

Text-RAG arbeitet nicht ausschließlich mit semantischer Ähnlichkeit. Vor jedem Character Call wird ein begrenztes Kontextpaket aufgebaut:

```text
1. Locked Canon vollständig laden
2. Current State laden
3. Memories nach Character, Typ und Gültigkeit filtern
4. semantische Relevanz zur aktuellen Situation bestimmen
5. Recency, emotionale Bedeutung und Wiederholung gewichten
6. Widersprüche und Duplikate entfernen
7. nur die relevantesten Erinnerungen an den Speaker übergeben
```

Canon und aktuelle Zustände sind direkte Datenbankabfragen. Nur der wachsende episodische Bestand benötigt Retrieval.

### 18.7 Image-Retrieval für VN-Szenen

Für neue VN-Bilder stellt das Backend ein aufgabenspezifisches Referenzpaket zusammen. Ein möglicher Abruf enthält:

```text
2 starke Visual-Canon-Bilder für die Identität
+ 1 bestätigtes Bild des gewünschten Outfits
+ 1 stabile Referenz für Pose oder Perspektive
+ bekannte negative Evidenz für diese Szene
+ erfolgreiche Recovery Pairs desselben Fehlertyps
```

Die Auswahl folgt festen Filtern und Rankings für:

- Character- und Canon-Version,
- Identity Strength,
- Dataset- und Review-Status,
- Outfit, Pose, Expression, Szene und Lighting,
- Qualität und Stability-Evidenz,
- bekannte Fehlergründe,
- sowie technische Workflow-Kompatibilität.

Negative Visual Evidence bleibt strikt von positiven Referenzpools getrennt.

### 18.8 Visual Specification und Prompt Compilation

Der Director erstellt vor jedem visuellen Try eine typisierte Visual Specification:

```json
{
  "character_version": 4,
  "scene_id": "school_rooftop_sunset",
  "outfit_id": "winter_uniform_01",
  "pose_id": "leaning_on_railing",
  "expression_id": "guarded_curiosity",
  "style_version": 1
}
```

Der Prompt Generator darf daraus ausschließlich erlaubte Promptfragmente formulieren. Der finale Prompt entsteht anschließend in einem deterministischen Compiler:

```text
Fixed Style Core
+ Locked Character Core
+ validierte Komponentenfragmente
+ aufgabenspezifische Referenzen
+ Fixed Negative Core
+ Recovery Constraints
```

Der Prompt Generator besitzt keine Kontrolle über Style-Version, Character Canon, Komponenten-IDs, Workflow, Seed oder Recovery-Methode.

### 18.9 Lokaler Inference Scheduler

Character Speaker und Prompt Generator sind zwei logisch getrennte Rollen, aber zunächst nicht zwingend zwei gleichzeitig geladene Modelle. Ein zentraler Scheduler koordiniert LM Studio und ComfyUI, damit sie nicht unkontrolliert um GPU-Speicher und Rechenzeit konkurrieren.

Ein konservativer Ablauf ist:

```text
Character-Antwort über LM Studio erzeugen
→ Ausgabe validieren und speichern
→ visuellen Try planen
→ Promptfragmente über LM Studio erzeugen
→ Prompt deterministisch kompilieren
→ LLM-Job und gegebenenfalls Modellkontext freigeben
→ ComfyUI-Generation starten
→ Renderzeit und GPU-Signatur speichern
```

Der Scheduler benötigt mindestens:

- getrennte Queues für Text- und Bildjobs,
- Prioritäten für sichtbare Useraktionen,
- Timeouts und begrenzte Retries,
- Modell- und VRAM-Zustand,
- Abbruch und Wiederaufnahme,
- Ergebnis-Caching,
- sowie Messung von Queue-, Inference- und Renderzeit.

Später kann ein kleines Textmodell dauerhaft auf CPU oder teilweise ausgelagert laufen, wenn dies schneller ist als wiederholte Modellwechsel. Diese Entscheidung wird anhand lokaler Messwerte getroffen.

### 18.10 Eventbasierter Save State

Alle verbindlichen Änderungen werden als unveränderliche Domain Events gespeichert. Daraus lassen sich der aktuelle Zustand und frühere Versionen rekonstruieren.

Beispielhafte Events sind:

- `PlayerGenderSelected`,
- `CanonPortraitConfirmed`,
- `StorySceneEntered`,
- `StoryChoiceSelected`,
- `PersonalityInputResolved`,
- `PersonalityAxisShifted`,
- `PersonalityAxisStabilized`,
- `MemoryAxisImpulseApplied`,
- `CurrentPersonalityProfileChanged`,
- `PersonalityChronicleUpdated`,
- `BasePersonalityRevealed`,
- `CharacterDialogueGenerated`,
- `MemoryCreated`,
- `MemoryCorrected`,
- `VisualTryRequested`,
- `ImageGenerated`,
- `ImageReviewed`,
- `RecoveryRequested`,
- `RecoveryCompleted`.

Der aktuelle Save State kann regelmäßig als Snapshot gespeichert werden. Die Events seit dem letzten Snapshot werden anschließend erneut angewendet.

Dieses Modell ermöglicht:

- reproduzierbare Spielstände,
- Undo für Studio-Entscheidungen,
- Debugging fehlerhafter LLM-Ausgaben,
- Migration von Profile- und Content-Versionen,
- Vergleich von Original und Recovery,
- sowie nachvollziehbare Character- und Relationship-Entwicklung.

LLM-Rohantworten werden zu Diagnosezwecken gespeichert, gelten aber nicht selbst als Domain Events. Erst eine validierte und vom Director akzeptierte Wirkung erzeugt ein Event.

### 18.11 Technischer Turn-Ablauf

```text
Useraktion empfangen
→ erlaubte Aktion gegen aktuellen Save State prüfen
→ Domain Event erzeugen
→ deterministischen State Reducer ausführen
→ nächste authorisierte Story-Szene bestimmen
→ Text-Memory-Kontext abrufen
→ Character Speaker aufrufen
→ Antwort validieren oder Template-Fallback verwenden
→ optional Visual Specification erzeugen
→ Image-RAG ausführen
→ Prompt Generator aufrufen
→ Prompt deterministisch kompilieren
→ ComfyUI-Job über Scheduler ausführen
→ Bild und Generation Recipe speichern
→ Review oder nächste VN-Aktion anbieten
```

### 18.12 Empfohlene Reihenfolge für die technische Detailplanung

1. Domain State und Event-Katalog definieren.
2. Story-Graph-Schema und Content-Versionierung festlegen.
3. deterministisches Profile Scoring definieren.
4. Character-Speaker-Vertrag und Fallbacks spezifizieren.
5. Memory Write und Text Retrieval spezifizieren.
6. Image Retrieval und Visual Specification an das bestehende Bildsystem anbinden.
7. LM-Studio-/ComfyUI-Scheduler entwerfen.
8. Save/Load, Migration und Debugging festlegen.

Der sinnvollste nächste Deep Dive ist der erste Punkt: ein vollständiges Zustandsmodell dafür, welche Daten einer Figur unveränderlich, entwickelbar, momentan oder rein episodisch sind und welche Events diese Daten verändern dürfen.

## 19. Visuelle Verfügbarkeit als Story-Progression

### 19.1 Zentrale Konsequenz

Eine Story-Szene kann nur stabil dargestellt werden, wenn ihre benötigten visuellen Assets bereits vorhanden sind oder rechtzeitig erzeugt werden können. Character-, Outfit-, Pose-, Expression- und Szenenbilder sind deshalb keine rein dekorativen Inhalte. Sie bilden eine spielbare Produktions- und Progressionsebene.

Der Bild-MVP wird damit später zum visuellen Prolog und zur dauerhaften Werkstatt der Visual Novel:

```text
Figur visuell formen
→ Identity stabilisieren
→ erstes Character-LoRA trainieren
→ VN-Basisassets erzeugen
→ Chronicle freischalten
→ Story erzeugt neuen Bildbedarf
→ Bild-Gamemode spielen
→ Asset bewerten, reparieren und freischalten
→ Story fortsetzen
→ Dataset und LoRA weiterentwickeln
```

Die Story darf trotzdem nicht für jede Textbox ein neues Bild benötigen. Wiederverwendbare Assets tragen den normalen Dialog; neue Generierungen markieren visuelle Erweiterungen und wichtige Erinnerungen.

### 19.2 Visuelle Asset-Klassen

#### Visual Canon

Bestätigte Referenzbilder für Gesicht, Haare, Körperbau, Farbpalette und zentrale Character-Merkmale. Sie definieren die visuelle Identität und dienen als Referenzen für weitere Generierungen.

#### VN Character Sprites

Freigestellte, normalisierte Figurenvarianten für Dialogszenen. Sie besitzen einen transparenten Hintergrund, eine feste Canvas-Größe, einen gemeinsamen Maßstab und einen definierten Bodenanker.

#### VN Backgrounds

Wiederverwendbare Orte ohne fest integrierte Hauptfigur. Tageszeit, Lighting und Storyzustand werden als Varianten geführt, wenn sie visuell relevant sind.

#### Story CGs und Memory Images

Vollständig komponierte Bilder für Memory Trials, Wendepunkte, Beziehungsereignisse und besondere visuelle Belohnungen. Sie werden im Chronicle beziehungsweise Memory Album gespeichert.

#### LoRA Dataset Images

Trainingsgeeignete Bilder mit ausreichender Identity, Qualität und Abdeckung. VN-Sprites und Story CGs dürfen nur dann zusätzlich Dataset-Bilder sein, wenn sie die Dataset-Regeln erfüllen. Freisteller allein dürfen das Training nicht dominieren.

#### Negative Evidence und Recovery Pairs

Fehlerhafte Bilder mit strukturierten Gründen sowie die daraus hervorgegangenen Reparaturergebnisse. Sie steuern spätere Recovery- und Risikobewertungen.

### 19.3 Visual-Readiness-Stufen

Der Director leitet die visuelle Bereitschaft einer Figur aus tatsächlich freigegebenen Assets und Stability-Evidenz ab.

```text
Identity Ready
→ Gesicht und Körper besitzen belastbare Canon-Referenzen

LoRA Ready
→ Dataset erfüllt die Voraussetzungen für einen Trainingslauf

Chronicle Ready
→ stabiles visuelles Basismodell und VN-Starter-Pack vorhanden

Scene Ready
→ visuelle Pflichtassets einer konkreten Szene verfügbar

Chapter Ready
→ visuelle Pflichtassets des nächsten Kapitels verfügbar oder geplant
```

`Chronicle Ready` sollte normalerweise ein erstes brauchbares Character-LoRA voraussetzen. Alternativ kann für frühe Tests ein nachweislich stabiler Referenz-Workflow zugelassen werden. Die Schwelle bleibt konfigurierbar und muss durch Playtests bestätigt werden.

Ein mögliches Chronicle-Starter-Pack enthält:

- bestätigtes Gesicht und bestätigten Körper,
- ein Default-Outfit,
- einen freigegebenen neutralen VN-Seed-Sprite,
- zwei grundlegende Posen,
- fünf bis sechs häufig benötigte Expressions,
- zwei bis drei wiederverwendbare Anfangshintergründe,
- sowie ein erstes Character-LoRA oder einen vergleichbar stabilen Referenz-Workflow.

Diese Zahlen sind Startwerte für Tests und keine endgültige Content-Vorgabe. Es wird nicht automatisch das vollständige kartesische Produkt aus allen Posen, Expressions und Outfits erzeugt. Freigeschaltet werden nur tatsächlich benötigte und spielerisch wertvolle Kombinationen.

### 19.4 Visuelle Klassen von Story-Szenen

| Szenenklasse | Primärer Bildbedarf | Neue Generierung |
|---|---|---|
| Dialogue Scene | vorhandener Background plus vorhandene Sprites | normalerweise keine |
| Expression Beat | vorhandener Sprite mit anderer Expression | nur bei fehlender wichtiger Expression |
| Visual Expansion | neues Outfit, neue Pose, neuer Ort oder neue Lichtvariante | gezielt erforderlich |
| Key Memory CG | vollständig komponiertes Storybild | normalerweise erforderlich |
| Recovery Beat | Reparatur eines bereits erzeugten Storybildes | abhängig vom Fehler |

Eine Memory Trial mit mehreren Text- und Choice-Schritten soll dadurch mit wenigen neuen Assets auskommen. Neue Bilder bleiben bedeutsam, ohne dass jeder Storyknoten einen eigenen Render benötigt.

### 19.5 Visual Requirement einer Story-Szene

Story-Content referenziert keine Dateipfade. Eine Szene deklariert semantische Visual Requirements mit stabilen Manifest-IDs:

```json
{
  "scene_id": "rooftop_confession",
  "visual_requirements": [
    {
      "requirement_id": "rooftop_dialogue_base",
      "asset_role": "dialogue_composition",
      "policy": "reuse_or_generate",
      "blocking": true,
      "constraints": {
        "background_id": "school_rooftop_sunset",
        "outfit_id": "winter_uniform_01",
        "pose_ids": ["standing_relaxed"],
        "expression_ids": ["guarded", "surprised"],
        "minimum_character_version": 4,
        "minimum_style_version": 1
      }
    },
    {
      "requirement_id": "rooftop_memory_cg",
      "asset_role": "key_memory_cg",
      "policy": "generate_and_review",
      "blocking": false,
      "constraints": {
        "scene_id": "school_rooftop_sunset",
        "story_intent": "first_vulnerable_admission"
      }
    }
  ]
}
```

Ein Requirement kann zusätzlich Mindestwerte für Identity, Qualität, Stability, Alpha-Qualität, LoRA-Version und Workflow-Kompatibilität verlangen.

### 19.6 Visual Policies

- **`reuse_only`:** Die Szene darf ausschließlich bereits freigegebene Assets verwenden.
- **`reuse_or_fallback`:** Bevorzugtes Asset verwenden, andernfalls eine authorisierte Ersatzdarstellung zeigen.
- **`reuse_or_generate`:** Vorhandenes Asset verwenden oder einen neuen Try anfordern.
- **`prefetch`:** Asset im Hintergrund vorbereiten, bevor es zwingend benötigt wird.
- **`generate_and_review`:** Neues Bild erzeugen und vor Canon- oder Story-Freigabe bewerten.
- **`canon_required`:** Nur ein ausdrücklich bestätigtes und versionskompatibles Asset erfüllt das Requirement.
- **`optional_memory`:** Story darf fortgesetzt werden; das Bild erscheint nach Fertigstellung als neue Erinnerung.

Die Policy ist authored. Das LLM darf weder Blocking-Verhalten noch Qualitätsanforderungen verändern.

### 19.7 Visual Asset Resolver

Der Resolver verbindet Story Requirements mit der persönlichen Asset-Bibliothek.

```text
Story-Szene anfordern
→ Visual Requirements laden
→ Character-, Canon- und Content-Version prüfen
→ persönliche Bibliothek nach kompatiblen Assets durchsuchen
→ positive Assets nach Eignung und Evidenz ranken
→ Negative Evidence nur zur Risikoprüfung abrufen
→ Requirement auflösen:
   ├── vorhandenes Asset binden
   ├── authorisierten Fallback binden
   ├── Prefetch-Job planen
   ├── Visual Quest eröffnen
   └── blockierendes Requirement als nicht erfüllt melden
```

Der Resolver erzeugt eine `SceneVisualPlan`, die das Frontend darstellen kann und der Director für Progression verwendet. Er kompiliert selbst keine Prompts.

### 19.8 Lebenszyklus eines visuellen Assets

```text
MISSING
→ PLANNED
→ QUEUED
→ GENERATING
→ REVIEW_REQUIRED
→ APPROVED
```

Alternative Übergänge sind:

```text
REVIEW_REQUIRED → RECOVERY_REQUIRED → QUEUED
REVIEW_REQUIRED → REJECTED
REVIEW_REQUIRED → QUARANTINED
```

Nur `APPROVED` erfüllt standardmäßig ein blockierendes Story Requirement. Optionaler Content darf während `GENERATING` oder `REVIEW_REQUIRED` bereits als ausstehende Erinnerung sichtbar sein.

Der Asset-Lebenszyklus ist getrennt vom Story-State. Eine laufende Bildgenerierung setzt die gesamte VN deshalb nicht in einen globalen `GENERATING`-Zustand.

### 19.9 VN-Sprite-Pipeline

Jede Sprite-Familie beginnt mit einem freigegebenen In-Game-Seed, der Silhouette, Palette, Outfit, Proportionen und Character Identity korrekt zeigt.

```text
freigegebener Character-Seed
→ transparenter Referenz-Canvas
→ zusammenhängende Pose- oder Expression-Varianten erzeugen
→ Varianten ausschneiden
→ gemeinsame Skalierung bestimmen
→ alle Varianten am gleichen Bodenanker ausrichten
→ Preview-Komposition im VN-Layout rendern
→ einzeln und als Familie prüfen
→ Sprite-Familie freigeben
```

Varianten einer Familie werden bevorzugt in einem gemeinsamen Edit- oder Sheet-Vorgang erzeugt. Unabhängige Einzelgenerierungen erhöhen Identity-, Proportions- und Maßstabsdrift. Wenn der verwendete Workflow keinen stabilen gemeinsamen Sheet-Pass ermöglicht, werden Einzelvarianten immer vom gleichen bestätigten Seed abgeleitet und anschließend gemeinsam normalisiert.

Zu erhaltende Invarianten sind:

- dieselbe Figur und Character-Version,
- dieselbe Blick- beziehungsweise Körperausrichtung innerhalb einer Familie,
- dieselbe Silhouetten- und Proportionsfamilie,
- dieselbe Farbpalette,
- dasselbe Outfit mit identischen Details,
- transparenter Hintergrund,
- keine Szenerie, Labels oder zusätzlichen Figuren,
- gemeinsamer Maßstab und Bodenanker.

Für statische VN-Dialoge werden zunächst vollständige Character-Sprites pro Pose und Expression verwendet. Separate Augen-, Mund- oder Gesichts-Layer sind eine spätere Optimierung, da sie zusätzliche Anschluss- und Identity-Fehler erzeugen können.

### 19.10 Sprite-Normalisierung und Manifest

Ein VN-Sprite wird nicht über seinen Dateinamen referenziert. Das Manifest speichert mindestens:

```json
{
  "asset_id": "sprite_char4_uniform1_relaxed_guarded",
  "asset_role": "vn_sprite",
  "character_id": "char_001",
  "character_version": 4,
  "outfit_id": "winter_uniform_01",
  "pose_id": "standing_relaxed",
  "expression_id": "guarded",
  "canvas_width": 2048,
  "canvas_height": 2048,
  "anchor_x": 0.5,
  "anchor_y": 0.96,
  "content_bounds": [322, 114, 1726, 1978],
  "shared_scale_group": "char4_uniform1_standing",
  "alpha_review_status": "approved",
  "visual_review_status": "approved"
}
```

Alle Varianten derselben Scale Group werden anhand der vereinigten sichtbaren Grenzen und eines gemeinsamen Maßstabs normalisiert. Standardanker ist Bottom Center. Der exakte freigegebene Seed kann bei Bedarf als erste beziehungsweise neutrale Variante zurück in die ausgelieferte Familie eingesetzt werden, um einen sichtbaren Wechsel beim Start einer Animation oder Expression-Folge zu vermeiden.

### 19.11 Zusätzliche Freistellungsfehler

Für transparente VN-Assets werden zusätzliche Review- und Recovery-Gründe benötigt:

- schlechte oder ausgefranste Alpha-Kante,
- Hintergrundreste,
- transparente Löcher in Haaren, Haut oder Kleidung,
- abgeschnittene Haare oder Accessoires,
- Farbsaum beziehungsweise Halo,
- fremde Objekte im Cutout,
- falscher Figurenmaßstab,
- falscher Bodenanker,
- sichtbares Springen zwischen Varianten,
- inkonsistente Proportionen innerhalb einer Sprite-Familie.

Lokale Alpha- und Kantenprobleme führen bevorzugt zu Masken- oder Inpainting-Recovery. Identity- oder Proportionsdrift kann eine vollständige Neuableitung vom freigegebenen Seed verlangen.

### 19.12 Prefetch und Generierungsbudget

Der Director darf nicht vorsorglich alle Bilder aller Storybranches generieren. Prefetch wird auf Assets begrenzt, die:

- von mehreren möglichen nächsten Szenen gemeinsam benötigt werden,
- nach einer bereits getroffenen Entscheidung mit hoher Sicherheit folgen,
- eine bekannte lange Renderzeit besitzen,
- oder für ein unmittelbar bevorstehendes blockierendes Requirement nötig sind.

Ungewählte Branches erhalten keine vollständigen Key CGs. So werden Rechenzeit und ungenutzte Bilder begrenzt.

Ein Storyabschnitt erhält ein konfigurierbares visuelles Budget, beispielsweise:

- vorhandene Sprites und Backgrounds für normale Dialogschritte,
- höchstens eine gezielte Visual Expansion pro kurzer Trial,
- ein Key Memory CG für einen wichtigen Abschluss,
- weitere Varianten nur bei ausdrücklichem Userwunsch oder Dataset-Bedarf.

Die konkreten Werte werden anhand von Renderzeit, Fehlerrate, Nutzungsdauer der Assets und Spieltempo getestet.

### 19.13 Key Visual und Background Chronicle

Bildgenerierungen werden nach ihrer Storywirkung unterschieden:

#### Key Visual

Die Szene wartet bewusst auf ein geprüftes Bild. Die Fertigstellung wird als Memory Reveal inszeniert. Bei einem klaren Fehler öffnet sich ein Recovery Trial.

#### Background Chronicle

Das Bild wird parallel zu Dialog oder Review erzeugt. Nach Fertigstellung erscheint es als ausstehende Erinnerung. Die Story darf weiterlaufen, solange das Bild kein blockierendes Requirement erfüllt.

```text
Story Event erzeugt Erinnerung
→ Background-Generation startet
→ Dialog wird fortgesetzt
→ Memory Developed erscheint
→ User öffnet und bewertet das Bild
→ Keep: Erinnerung erhält ein freigegebenes Bild
→ Delete oder Fehler: Recovery-Pfad wird angeboten
```

### 19.14 Verbindung von Bildspiel und Story

Eine fehlende visuelle Voraussetzung wird nicht als technisches Formular präsentiert, sondern als spielbarer Auftrag:

- ein neues Outfit über Character Forge formen,
- eine benötigte Expression in einer Expression Trial stabilisieren,
- einen Ort über eine Scene Challenge freischalten,
- eine Pose über Stability Trial qualifizieren,
- ein fehlerhaftes Story CG in einem Repair Run retten,
- oder das nächste LoRA-Training durch Dataset Coverage vorbereiten.

Damit bleibt auch nach Freischaltung der VN der Bild-Loop aktiv. Story und Bildsystem treiben sich gegenseitig an:

```text
Story erzeugt visuellen Bedarf
→ Bildspiel erzeugt und qualifiziert das Asset
→ Asset erweitert die darstellbare Story
→ Story erzeugt neue Erinnerungen und Dataset-Bedarf
→ verbessertes LoRA erweitert den visuellen Möglichkeitsraum
```

### 19.15 Technische Qualitäts- und Playtest-Gates

Vor Freigabe einer Sprite-Familie oder eines Story Requirements werden mindestens geprüft:

- Identity bleibt über Varianten stabil,
- Proportionen und gemeinsamer Maßstab driften nicht,
- Bodenanker bleibt beim Wechsel ruhig,
- Transparenz ist erhalten,
- Outfitdetails bleiben konsistent,
- Ausdruck ist bei tatsächlicher VN-Größe lesbar,
- Asset funktioniert im Zielhintergrund und nicht nur isoliert,
- Storyfluss bleibt bei laufender Generation bedienbar,
- blockierende Generierung besitzt Recovery und Abbruch,
- Save/Load rekonstruiert gebundene und ausstehende Assets korrekt,
- Renderzeit und Zahl ungenutzter Prefetch-Bilder bleiben im Budget.

### 19.16 Nächster Deep Dive

Der nächste technische Schwerpunkt ist der `VisualAssetResolver`. Zu definieren sind:

1. das exakte Schema eines `VisualRequirement`,
2. die Kompatibilitätsregeln zwischen Requirement und persönlichem Asset,
3. das Ranking mehrerer geeigneter Assets,
4. die Ableitung einer `SceneVisualPlan`,
5. Blocking-, Fallback- und Prefetch-Verhalten,
6. sowie die Events für Asset-Bindung, Generation, Review und Recovery.

Dieser Resolver ist die zentrale Brücke zwischen authored VN-Content und der vom User erspielten persönlichen Bildbibliothek.

## 20. Visual Asset Resolver: verbindliche Fachspezifikation

### 20.1 Systemgrenze

Der `VisualAssetResolver` ist reine Backend-Domainlogik. Er verbindet authored Storybedarf mit freigegebenen Assets, ohne selbst Bilder zu rendern oder Prompts zu schreiben.

```text
Story Director
→ Visual Requirement
→ Visual Asset Resolver
→ Scene Visual Plan
→ DOM Renderer
```

Bei fehlenden Assets erzeugt der Resolver keine direkte ComfyUI-Anfrage. Er meldet einen fachlichen Bedarf. Der Director entscheidet anschließend, ob ein Prefetch-Job, eine Visual Quest, ein Fallback oder ein Story-Blocker entsteht.

Der Renderer erhält nur den fertigen Plan. Er darf weder die persönliche Bibliothek durchsuchen noch Assets eigenständig ersetzen.

### 20.2 Character-Version und Visual Compatibility Revision

Allgemeine Character-Entwicklung und visuelle Kompatibilität werden getrennt versioniert:

```json
{
  "character_version": 12,
  "visual_compatibility_revision": 3
}
```

`character_version` steigt bei allen bestätigten Änderungen, zum Beispiel neuen Vorlieben, Erinnerungen oder Voice-Anpassungen.

`visual_compatibility_revision` steigt nur, wenn vorhandene Bilder sichtbar inkompatibel werden, beispielsweise durch:

- andere Haarfarbe oder dauerhaft neue Frisur,
- geänderten Körperbau,
- neues dauerhaftes Character-Merkmal,
- entferntes oder hinzugefügtes charakteristisches Accessoire,
- grundlegende Änderung der visuellen Alters- oder Stilvorgabe.

Ein neues Outfit allein erzeugt keine neue visuelle Revision. Es ist eine separate Komponente.

Assets referenzieren die visuelle Revision, für die sie freigegeben wurden. Standardmäßig gilt exakte Kompatibilität. Bewusste Migrationen zwischen Revisionen werden in einer geprüften Compatibility Map gespeichert und niemals allein aus einer höheren Versionsnummer abgeleitet.

```json
{
  "character_id": "char_001",
  "from_visual_revision": 2,
  "to_visual_revision": 3,
  "compatibility": "incompatible",
  "reason": "hair_color_changed"
}
```

### 20.3 Vollständiges Visual-Requirement-Schema

Story-Content bleibt möglichst character-unabhängig. Er referenziert einen Actor Slot wie `main_character` statt einer konkreten Character-ID. Erst die laufende Chronicle bindet diesen Slot an die Userfigur.

```json
{
  "schema_version": 1,
  "requirement_id": "rooftop_guarded_sprite",
  "asset_role": "vn_sprite",
  "actor_slot": "main_character",
  "usage": "dialogue_primary",
  "policy": "reuse_or_generate",
  "blocking": true,
  "binding_scope": "scene_instance",
  "hard_constraints": {
    "visual_revision_mode": "exact",
    "style_version": 1,
    "outfit_ids": ["winter_uniform_01"],
    "pose_ids": ["standing_relaxed"],
    "requires_transparency": true,
    "minimum_identity_score": 0.9,
    "minimum_quality_score": 0.8,
    "review_status": "approved"
  },
  "preferences": {
    "expression_ids": ["guarded", "uncertain"],
    "facing": ["three_quarter_left", "front"],
    "continuity_group": "rooftop_sequence_a"
  },
  "forbidden": {
    "error_reasons": ["wrong_artstyle", "character_drift"],
    "tags": ["wet_clothes", "battle_damage"]
  },
  "fallback_chain": [
    {
      "fallback_id": "neutral_same_pose",
      "allow_expression_ids": ["neutral"],
      "requires_user_notice": false
    },
    {
      "fallback_id": "silhouette_pending_generation",
      "asset_role": "character_silhouette",
      "requires_user_notice": true
    }
  ],
  "generation_policy": {
    "generation_allowed": true,
    "prefetch_allowed": true,
    "priority": "story_visible",
    "maximum_attempts": 3,
    "recovery_allowed": true
  }
}
```

### 20.4 Pflichtfelder

Jedes `VisualRequirement` besitzt mindestens:

- `schema_version`,
- stabile `requirement_id`,
- `asset_role`,
- `actor_slot` oder einen expliziten Environment Slot,
- `usage`,
- `policy`,
- `blocking`,
- `binding_scope`,
- `hard_constraints`,
- explizite `fallback_chain`, auch wenn sie leer ist,
- und `generation_policy`.

Storytexte, Dateipfade, Prompts und konkrete Backend-URLs gehören nicht in das Requirement.

### 20.5 Asset Roles

Der erste Katalog enthält:

- `visual_canon_reference`,
- `vn_sprite`,
- `vn_portrait`,
- `vn_background`,
- `key_memory_cg`,
- `story_prop`,
- `character_silhouette`,
- `transition_visual`,
- `ui_illustration`.

Ein Asset kann mehrere fachliche Eignungen besitzen, aber genau eine primäre Rolle. Dataset-Zulassung ist ein separater Status und keine Asset Role.

### 20.6 Usage und Binding Scope

`usage` beschreibt, wofür das Asset in der Szene eingesetzt wird, beispielsweise:

- `dialogue_primary`,
- `dialogue_secondary`,
- `scene_background`,
- `expression_beat`,
- `memory_reveal`,
- `chapter_key_visual`,
- `loading_transition`.

`binding_scope` legt fest, wie lange eine erfolgreiche Auswahl stabil bleibt:

- `turn`: nur für den aktuellen Dialogturn,
- `scene_instance`: für die gesamte laufende Szeneninstanz,
- `sequence`: über mehrere zusammenhängende Szenen,
- `chapter`: innerhalb des Kapitels,
- `memory`: dauerhaft an eine konkrete Erinnerung gebunden.

Eine bestehende Bindung wird nicht automatisch durch ein später höher bewertetes Asset ersetzt. Dadurch springen Figuren, Outfits und Hintergründe innerhalb einer Szene nicht unkontrolliert.

### 20.7 Hard Constraints

Hard Constraints sind nicht verhandelbar. Ein Kandidat wird verworfen, wenn eine Bedingung nicht erfüllt ist.

Mögliche Constraints sind:

- Character- beziehungsweise Actor-Slot-Kompatibilität,
- exakte oder ausdrücklich gemappte visuelle Revision,
- Asset Role,
- Style-Version,
- Outfit-, Pose-, Expression-, Scene- und Lighting-IDs,
- Alpha- beziehungsweise Transparenzstatus,
- Canvas- und Aspect-Ratio-Anforderungen,
- gemeinsame Scale Group oder Anchor Group,
- Mindestwerte für Identity, Qualität und Stability,
- Review- und Freigabestatus,
- LoRA- oder Workflow-Kompatibilität,
- Content- und Story-Version,
- sowie maximale technische Asset-Größe.

Ein Hard Constraint darf nicht über ein Scoring kompensiert werden. Ein sehr schönes Bild im falschen Outfit bleibt inkompatibel, wenn das Outfit für die Szene zwingend ist.

### 20.8 Preferences

Preferences bestimmen die Reihenfolge kompatibler Kandidaten. Sie dürfen keine Hard Constraints lockern.

Mögliche Präferenzen sind:

- bevorzugte Expression-Reihenfolge,
- bevorzugte Pose oder Blickrichtung,
- gleiche Sprite-Familie wie im vorherigen Turn,
- gleiche Scale und Anchor Group,
- gleiche Outfit-Version innerhalb einer Sequence,
- visuelle Kontinuität zur vorherigen Szene,
- höhere Identity- und Qualitätswerte,
- höhere Stability-Evidenz,
- geringere Lade- oder Renderkosten,
- gewünschte Neuheit bei einem Reveal,
- sowie zuletzt verwendetes Asset vermeiden, wenn Wiederholung dramaturgisch unerwünscht ist.

### 20.9 Forbidden Constraints

Explizite Ausschlüsse haben Vorrang vor Preferences und Fallbacks:

- verbotene Tags,
- bekannte Fehlergründe,
- unzulässige Storyzustände,
- bereits als Negative Evidence klassifizierte Assets,
- falsche Alters- oder Präsentationskategorie,
- unpassende Wetter-, Schadens- oder Zustandsvarianten,
- sowie Assets aus inkompatiblen Character- oder Style-Versionen.

Ein Fallback muss alle Forbidden Constraints weiterhin erfüllen.

### 20.10 Visual-Asset-Schema

Der Resolver arbeitet mit normalisierten Asset-Metadaten:

```json
{
  "asset_id": "sprite_char4_uniform1_relaxed_guarded",
  "asset_role": "vn_sprite",
  "state": "approved",
  "character_id": "char_001",
  "visual_compatibility_revision": 3,
  "style_version": 1,
  "component_ids": {
    "outfit_id": "winter_uniform_01",
    "pose_id": "standing_relaxed",
    "expression_id": "guarded",
    "scene_id": null,
    "lighting_id": null
  },
  "semantic_tags": ["school", "reserved", "three_quarter_left"],
  "technical": {
    "mime_type": "image/webp",
    "width": 2048,
    "height": 2048,
    "has_alpha": true,
    "anchor_x": 0.5,
    "anchor_y": 0.96,
    "scale_group": "char4_uniform1_standing",
    "content_bounds": [322, 114, 1726, 1978]
  },
  "quality": {
    "identity": 0.94,
    "overall": 0.87,
    "stability": 0.82,
    "alpha": 0.91
  },
  "provenance": {
    "generation_recipe_id": "recipe_541",
    "source_asset_id": "canon_char4_fullbody_02",
    "workflow_version": "sprite-cutout-1.0",
    "lora_version": "char4-lora-1"
  },
  "review": {
    "status": "approved",
    "error_reasons": []
  }
}
```

Dateipfad und auslieferbare URL werden über einen separaten Asset-Storage-Service aufgelöst. Sie sind keine Identität des Assets.

### 20.11 Resolver-Phasen

Der Resolver arbeitet reproduzierbar in festen Phasen:

```text
1. Requirement-Schema und Content-Version validieren
2. Actor Slot gegen laufenden Chronicle State auflösen
3. bestehende Bindung des Binding Scope suchen
4. Kandidaten über indizierte Hard-Constraint-Felder laden
5. Hard und Forbidden Constraints anwenden
6. kompatible Kandidaten ranken
7. Fallback Chain der Reihe nach prüfen
8. bei fehlendem Asset einen fachlichen Generation Need erzeugen
9. Scene Visual Plan erstellen
10. Entscheidung und verwendete Evidenz für Debugging protokollieren
```

Eine noch gültige bestehende Bindung besitzt Vorrang vor einem neuen Ranking. Neu gerankt wird nur bei fehlender, ungültiger oder bewusst gelöster Bindung.

### 20.12 Ranking-Modell

Nach allen harten Filtern erhält jeder Kandidat einen normalisierten Score. Ein erster konfigurierbarer Ausgangspunkt ist:

```text
Story Fit          30 %
Visual Continuity  25 %
Character Identity 20 %
Quality/Stability  15 %
Technical Cost      5 %
Desired Novelty     5 %
```

`Story Fit` bewertet die weichen Komponentenwünsche. `Visual Continuity` bevorzugt bestehende Familien, Outfits, Maßstäbe und Bindungen. `Desired Novelty` wird nur für Reveals oder ausdrücklich neue visuelle Momente positiv gewichtet.

Das Ranking wird vollständig aus strukturierten Metadaten berechnet. Ein LLM ist nicht beteiligt.

Bei gleichem Score entscheidet eine stabile Reihenfolge, beispielsweise:

1. höhere Continuity,
2. höhere Identity,
3. höhere Stability,
4. jüngere gültige Freigabe,
5. lexikografische Asset-ID als letzter deterministischer Tie-Breaker.

### 20.13 Fallback-Kaskade

Fallbacks werden explizit durch die Story authorisiert und in Reihenfolge geprüft. Eine typische Kaskade ist:

```text
exakter Asset Match
→ erlaubte Expression-Alternative derselben Pose und desselben Outfits
→ authorisierter neutraler Sprite derselben Familie
→ authorisierte Silhouette oder verdeckte Darstellung
→ Background Generation beziehungsweise Visual Quest
→ blockierendes Requirement
```

Nicht erlaubt sind stille Wechsel zu falschem Outfit, falscher Character-Version, falschem Artstyle oder widersprüchlichem Storyzustand.

Für später vom Spieler erstellte Playground-Sets gilt derselbe Vertrag wie für die MVP-Combo-Quests: `Character`, `Scene` und `Outfit` müssen als versionierter Snapshot auflösbar sein, genau ein fachlicher Fokus wird deklariert und die Inhaltsstufe ist explizit klassifiziert. Ein späterer Generation Planner darf unklassifizierte oder nicht freigegebene sensible Komponenten nicht still ergänzen oder als neutralen Fallback verwenden.

Jeder Fallback kann festlegen:

- ob er für den User sichtbar gekennzeichnet wird,
- wie lange er gebunden bleibt,
- ob parallel ein Ersatzasset generiert wird,
- ob er in Key Visuals zulässig ist,
- und ob die Szene später mit dem finalen Asset erneut angesehen werden kann.

### 20.14 Scene Visual Plan

Die Resolver-Ausgabe ist vollständig darstellbar und serialisierbar:

```json
{
  "plan_id": "svp_984",
  "scene_instance_id": "scene_run_221",
  "state_version": 18,
  "status": "ready_with_pending_memory",
  "layers": [
    {
      "slot": "background",
      "asset_id": "bg_rooftop_sunset_03",
      "binding_id": "bind_701",
      "z_index": 0,
      "presentation": {
        "position": "center",
        "transition": "crossfade"
      }
    },
    {
      "slot": "character_left",
      "asset_id": "sprite_char4_uniform1_relaxed_guarded",
      "binding_id": "bind_702",
      "z_index": 10,
      "presentation": {
        "anchor": "bottom_center",
        "position": "left",
        "speaker_emphasis": true
      }
    }
  ],
  "fulfilled_requirements": [
    "rooftop_dialogue_base"
  ],
  "fallbacks": [],
  "pending_needs": [
    {
      "requirement_id": "rooftop_memory_cg",
      "need_type": "background_generation",
      "blocking": false
    }
  ],
  "blockers": []
}
```

Mögliche Planstatus sind:

- `ready`,
- `ready_with_fallback`,
- `ready_with_pending_memory`,
- `waiting_for_review`,
- `blocked_by_generation`,
- `blocked_by_missing_canon`,
- `invalid_content`.

### 20.15 Unveränderliche Asset-Bindungen

Sobald eine Szeneninstanz ein Asset bindet, wird die Bindung als Domain Event gespeichert. Ein späterer Library Rebuild, ein besseres Rating oder ein neu erzeugtes Asset verändert die bereits dargestellte Szeneninstanz nicht automatisch.

Key Memory CGs werden dauerhaft an die konkrete Erinnerung und Generation Recipe gebunden. Eine Recovery erzeugt eine neue Asset-Version und ein ausdrückliches Replacement Event. Das ursprüngliche Bild bleibt historisch nachvollziehbar.

Mögliche Bindungsereignisse sind:

- `SceneVisualPlanCreated`,
- `VisualAssetBound`,
- `VisualFallbackBound`,
- `VisualBindingReleased`,
- `MemoryVisualBound`,
- `MemoryVisualReplaced`.

### 20.16 Generation Need

Kann ein Requirement nicht aufgelöst werden, erzeugt der Resolver ein strukturiertes `GenerationNeed`:

```json
{
  "generation_need_id": "need_311",
  "requirement_id": "rooftop_memory_cg",
  "scene_instance_id": "scene_run_221",
  "asset_role": "key_memory_cg",
  "blocking": false,
  "priority": "story_visible",
  "reason": "no_compatible_asset",
  "preserve": {
    "character_id": "char_001",
    "visual_revision": 3,
    "story_intent": "first_vulnerable_admission"
  },
  "allowed_component_ids": {
    "scene_ids": ["school_rooftop_sunset"],
    "outfit_ids": ["winter_uniform_01"],
    "expression_ids": ["guarded", "vulnerable"]
  }
}
```

Erst der Director beziehungsweise ein Generation Planner übersetzt diesen Need in Visual Specification, Image-RAG-Anfrage, Prompt-Compilation und ComfyUI-Job.

### 20.17 Resolver-Events

Der vollständige fachliche Eventkatalog umfasst mindestens:

- `VisualRequirementEvaluated`,
- `VisualAssetBound`,
- `VisualFallbackBound`,
- `VisualRequirementFulfilled`,
- `VisualRequirementBlocked`,
- `VisualGenerationNeeded`,
- `VisualGenerationRequested`,
- `VisualAssetGenerated`,
- `VisualAssetReviewRequired`,
- `VisualAssetApproved`,
- `VisualAssetRejected`,
- `VisualRecoveryRequested`,
- `VisualRecoveryCompleted`,
- `VisualBindingReleased`,
- `MemoryVisualBound`,
- `MemoryVisualReplaced`.

LLM-Ausgaben erzeugen keine dieser Events direkt. Erst eine validierte Director-Entscheidung darf ein Domain Event schreiben.

### 20.18 Debug- und Testoberfläche

Für jede Resolver-Entscheidung muss eine Development View anzeigen können:

- ursprüngliches Requirement,
- aufgelösten Actor Slot,
- gefundene Kandidatenzahl,
- pro Kandidat erfüllte und verletzte Hard Constraints,
- angewandte Forbidden Filters,
- Score-Aufschlüsselung,
- verwendete Fallback-Stufe,
- bestehende Bindungen,
- erzeugte Generation Needs,
- finale Scene Visual Plan,
- sowie Laufzeit der einzelnen Resolver-Phasen.

Zentrale automatisierte Tests sind:

- falsche visuelle Revision wird ausgeschlossen,
- falsches Outfit kann nicht durch hohe Qualität gewinnen,
- Negative Evidence wird nie positiv gebunden,
- gleiche Eingaben erzeugen denselben Plan,
- bestehende Scene Binding bleibt stabil,
- authorisierter Fallback wird in korrekter Reihenfolge verwendet,
- nicht authorisierter Fallback blockiert,
- optionaler Need blockiert die Szene nicht,
- blockierender Need setzt den korrekten Planstatus,
- Save/Load rekonstruiert identische Bindungen,
- Recovery ersetzt ein Memory-Bild nur über ausdrückliches Event.

### 20.19 Nachgelagerte Vertiefung

Der `Generation Planner` bleibt eine erforderliche nachgelagerte Schicht. Er übersetzt einen fachlichen `GenerationNeed` in Visual Specification, Referenzen, Negative Evidence, Generierungs- oder Recovery-Methode, Workflow- und Zeitbudget sowie einen validierbaren Auftrag an Prompt Compiler und ComfyUI.

Vor seiner Detailplanung wird jedoch der gemeinsame `ChatTurnContract` festgelegt. Er ist die vorgelagerte Klammer, die Story, spielerische Userabfrage, Personality-Verhalten, Component Drafts, Character-Reaktion und visuellen Bedarf in einem kontrollierten Turn zusammenführt.

## 21. Konsolidierte Richtung: VN-Prolog, spätere Character Chats und eine gemeinsame Timeline

### 21.1 Gemeinsame Timeline mit unterschiedlichen Präsentationsmodi

Die erste Interaktion des Users ist eine authored VN-Szene. Erzähler, Umzugszimmer und Mutter-Silhouette führen durch direkte Startangaben und indirekte Präferenz-Choices. Der Prolog ist kein freier Chat und kein technischer Konfigurator.

Der User erlebt eine zusammenhängende Oberfläche und Historie. Innerhalb dieser Timeline wird der freie, aber kontrollierte Character Chat als eigene Fähigkeit freigeschaltet, sobald eine Figur visuell und strukturell ausreichend definiert ist. VN-Prolog, spätere Character Chats und Bild-Games bleiben fachlich getrennte Modi, verwenden aber denselben Save State und dieselbe Chronicle-Historie.

Die vollständige VN-Darstellung ist eine weitere, spätere Freischaltung. Sie setzt genügend geprüfte Character-Sprites, Expressions, Outfits, Hintergründe und Storybilder voraus. Bis dahin tragen authored Erzähler-/VN-Turns und Bild-Games den Fortschritt.

Innerhalb derselben Timeline können erscheinen:

- authorisierte Erzählernachrichten,
- sichtbare Entscheidungen,
- freie Userantworten innerhalb eines definierten Input Contracts,
- kontrollierte Antworten der Figur,
- Bildgenerierungs- und Fortschrittskarten,
- Visual Reveals,
- Review-, Delete- und Recovery-Interaktionen,
- sowie Chronicle- und Memory-Ereignisse.

Die technische Trennung der Systeme bleibt intern bestehen. Sie darf nicht zu getrennten Userflüssen führen.

### 21.2 Reife- und Freischaltstufen

```text
STUFE 1: NARRATOR VN READY
→ sofort verfügbar
→ Erzähler und Mutter-Silhouette erheben Spielergeschlecht, Name und erste Präferenzsignale über Choices

STUFE 2: FIRST IMAGE READY
→ Character Draft ist promptfähig
→ erste Portrait- und Identity-Trys können generiert werden

STUFE 3: CHARACTER CHAT READY
→ Character Core und erste bestätigte Bilder sind vorhanden
→ die Figur darf innerhalb authorisierter Storyframes selbst antworten

STUFE 4: IMAGE GAME PROGRESSION
→ Sprites, Expressions, Posen, Outfits und Szenen werden erspielt
→ persönliche Playground- und Combo-Daten wachsen

STUFE 5: CHRONICLE READY
→ ausreichende Identity Stability und visuelle Mindestabdeckung
→ benötigtes VN-Starter-Pack und geeigneter Referenz- oder LoRA-Workflow vorhanden

STUFE 6: HYBRID VN LOOP
→ VN-Szene, Erzähler, Character Chat und Bild-Games greifen dauerhaft ineinander
```

`Character Chat Ready` und `Chronicle Ready` sind ausdrücklich verschiedene Gates. Eine Figur kann bereits sprechen, obwohl noch nicht genügend visueller Content für einen vollständigen VN-Ablauf vorhanden ist.

### 21.3 Der Erzähler erhebt jeden benötigten User-Input spielerisch

Alle Informationen, die das System nicht kontrolliert zufällig festlegen darf, werden durch authorisierte Storymomente abgefragt. Der User sieht keine technische Character Specification und keinen Prompt-Editor. Im Prolog erfolgen diese Eingaben primär über Auswahlkarten oder Bildentscheidungen; freier Text ist dort zunächst auf Namensfelder und ausdrücklich dafür vorgesehene Eingaben begrenzt.

Beispiele sind:

- Geschlecht des Spielercharakters,
- Haarfarbe und Frisurenrichtung,
- Augenfarbe,
- Körper- und Silhouettenrichtung,
- Farbpalette,
- besondere visuelle Merkmale,
- Outfitart, Primär- und Akzentfarben,
- Material- und Stilwünsche,
- gewünschte oder auszuschließende Details,
- sowie Reaktionen, aus denen deterministisch Personality-Evidenz entsteht.

Die Frage wird in die aktuelle Szene eingebettet:

```text
Technischer Bedarf:
outfit.primary_color fehlt

Sichtbarer Storyturn:
Der Erzähler beschreibt, wie die Figur vor zwei Jacken stehen bleibt.
„Welche Farbe zieht deinen Blick zuerst an?“
```

Die Antwort kann abhängig von Phase und Input Contract als Choice, Bildauswahl, validiertes Textfeld oder späterer Character-Chat erfolgen. Jede Variante schreibt in ein ausdrücklich definiertes strukturiertes Input-Feld. Der Prolog verwendet keinen allgemeinen Freitextkanal zur verdeckten Character- oder Prompt-Erstellung.

### 21.4 Arten von Character-Informationen

#### Explicit User Locks

Direkte Userentscheidungen, die nicht still verändert werden dürfen:

- Geschlecht und Name des Spielercharakters,
- bestätigte Haar- und Augenfarbe,
- bestätigte zentrale Character-Merkmale,
- ausdrücklich gewählte Outfitfarben,
- visuelle Ausschlüsse,
- sowie später bewusst bestätigte Canon-Fakten.

#### Deterministic Progress Values

Werte, die aus authorisierten Entscheidungen berechnet werden:

- Evidenz für I oder E,
- Evidenz für N oder S,
- Evidenz für T oder F,
- Evidenz für J oder P,
- Relationship-Entwicklung,
- Trust und Story Flags.

#### Controlled Random Slots

Optionale Details, die innerhalb eines authorisierten Pools zufällig gewählt werden dürfen, wenn der User sie nicht selbst definieren soll. Der Zufall muss im Save State gespeichert und reproduzierbar sein.

#### LLM Suggestions

Vorschläge, die erst nach Userbestätigung und Bildreview verbindlich werden. Ein LLM-Vorschlag besitzt niemals automatisch Canon-Status.

### 21.5 Input Requirement

Jeder Story Node kann ein oder mehrere strukturierte Input Requirements besitzen:

```json
{
  "input_requirement_id": "first_outfit_primary_color",
  "target": {
    "entity": "outfit_draft",
    "field": "primary_color"
  },
  "required_before": "first_outfit_generation",
  "collection_mode": "choice_or_free_text",
  "narrator_prompt_key": "prologue.outfit.primary_color",
  "choices": [
    "dark_navy_blue",
    "deep_red",
    "forest_green"
  ],
  "allow_free_text": true,
  "normalization_schema": "canonical_color_v1",
  "lock_policy": "explicit_user_lock",
  "fallback_policy": "ask_again",
  "may_randomize": false
}
```

Der Director entscheidet anhand des Save States, welches Requirement als Nächstes sinnvoll in die Story eingebettet wird. Das Playground Author LLM darf kein Requirement erfinden, entfernen oder überspringen.

### 21.6 ChatTurnContract

Jeder sichtbare Turn wird durch einen serialisierbaren Vertrag beschrieben:

```json
{
  "turn_id": "turn_0042",
  "story_node_id": "prologue_first_outfit",
  "phase": "guided_character_definition",
  "narrator": {
    "message_key": "prologue.outfit.primary_color",
    "presentation": "story"
  },
  "input_requirement_ids": [
    "first_outfit_primary_color"
  ],
  "accepted_user_actions": [
    "select_choice",
    "submit_free_text"
  ],
  "playground_author_task": {
    "enabled": true,
    "target_kind": "outfit",
    "operation": "update_draft"
  },
  "character_speech": {
    "enabled": true,
    "speech_intent": "react_to_player_color_choice",
    "behavior_pack_id": "INTJ-v1",
    "maximum_sentences": 2
  },
  "visual_need": {
    "enabled": false
  },
  "next_transition": "after_valid_input"
}
```

Der Contract wird vom hardcodierten Director erzeugt. Das Frontend rendert ihn. Die LLMs erhalten nur die für ihren Teil benötigten Felder.

### 21.7 Zwei LLM-Rollen innerhalb desselben Turns

#### Character Dialogue LLM

Es erhält:

- Speech Intent,
- explizite Regeln des Personality Behavior Packs,
- aktuelle Szene,
- bestätigten Character Core,
- Relationship- und Current State,
- erlaubte Memories,
- aktuelle Usernachricht,
- Längen- und Inhaltsgrenzen.

Es formuliert nur die sichtbare Figurenrede und eine erlaubte Expression ID.

#### Playground Author LLM

Es erhält:

- Ziel-Kind und Zielfeld,
- aktuelle Component Specification,
- neue Userantwort,
- Locked Visual Facts,
- erlaubte Tags und Regeln,
- festen Prompt Style Contract,
- sowie vorhandene persönliche Komponenten-IDs, wenn eine Combo vorgeschlagen wird.

Es normalisiert Userinput und erzeugt Component- oder Combo-Drafts. Es darf keine SQL-Anweisungen ausführen, keine unbekannten IDs erfinden und keinen finalen Story- oder Canon-State schreiben.

Ein Turn kann nur eine, beide oder keine LLM-Rolle benötigen. Der Erzählertext selbst bleibt authored.

### 21.8 16 authorisierte Personality Behavior Packs

Für jedes der exakt 16 Profile wird ein versioniertes Behavior Pack angelegt. Das Character Dialogue LLM soll die Bedeutung eines Typencodes nicht selbst auslegen müssen.

Der Director wählt für einen Turn das Pack des `CurrentPersonalityProfile`. Kontinuierliche Achsenstärken, Base-Herkunft, Character Brand, Memories und Relationship State konkretisieren dieses Pack. Ein Current-Type-Wechsel tauscht deshalb nicht die gesamte Person aus, sondern verändert ab dem Folgeturn die typbezogene Gewichtung innerhalb ihres bestehenden Canon.

Ein Pack definiert mindestens:

- Initiative,
- Social Energy,
- Trust-Geschwindigkeit,
- Nähe- und Distanzverhalten,
- Konfliktstil,
- Entscheidungsstil,
- emotionale Offenheit,
- Reaktion unter Druck,
- Humor- und Teasing-Tendenzen,
- Frageverhalten,
- Memory-Salienz,
- bevorzugte und seltene Expressions,
- bevorzugte und seltene Posen,
- erlaubte Entwicklungsrichtungen,
- sowie verbotene Personality Shortcuts.

Der Director wählt aus Story Intent, Behavior Pack und Current State konkrete `must_do`- und `must_not_do`-Regeln. Das LLM formuliert nur innerhalb dieser Regeln.

### 21.9 Persönliche Playground SQLite

Die Entwicklungs-Playground-DB wird nicht ausgeliefert. Jeder User erhält eine leere persönliche Playground-DB mit demselben fachlichen Grundschema und zusätzlichen Draft- und Versionsdaten.

Die persönliche DB wächst über:

```text
Input Requirement erfüllt
→ Playground Author erzeugt oder ergänzt Component Draft
→ Schema-, Tag- und Konfliktvalidierung
→ Test-Combo planen
→ Bilder generieren und reviewen
→ Draft korrigieren, verwerfen oder freigeben
→ freigegebenes Playground Item committen
```

Atomare persönliche Inhalte bleiben:

- `character`,
- `scene`,
- `outfit`,
- `pose`,
- `expression`,
- `lighting`,
- `modifier`.

Explizite Userangaben werden zusätzlich strukturiert gespeichert. `pos` und `neg` sind kompilierte Promptfragmente und nicht die alleinige Source of Truth.

### 21.10 Persönliche Combo Prompt DB

Auch die Entwicklungs-Combo-Prompt-DB wird nicht vorausgefüllt ausgeliefert. Die persönliche Combo-DB entsteht aus:

- freigegebenen Playground-Items,
- tatsächlich gespielten oder getesteten Kombinationen,
- Generation Recipes,
- Bildratings,
- Stabilität,
- Fehlerverteilungen,
- Generierungszeiten,
- und besten Bildern pro Combo.

Die bestehende 2er- und 3er-Analyse für `Character + Scene` sowie `Character + Scene + Outfit` bleibt als Rankingebene nützlich. Vollständige Story-Combos mit Pose, Expression, Lighting und Modifier werden on demand materialisiert, statt das vollständige kartesische Produkt im Voraus zu erzeugen.

Der Playground Author darf einen Combo Draft nur mit existierenden persönlichen IDs erzeugen. Fehlt ein benötigtes Item, erzeugt er einen separaten Component Draft. Erst der Server erstellt die normalisierte Combo-Signatur und den Datenbankeintrag.

### 21.11 Zusammenspiel von Personality und Visuals

Personality Behavior Packs dürfen visuelle Vorschläge gewichten, aber ausdrückliche Userentscheidungen niemals überschreiben.

Beispiel:

```text
INTJ Behavior Pack bevorzugt zurückhaltende Expression
+ User hat leuchtend rote Jacke ausdrücklich gewählt
= zurückhaltende Pose in leuchtend roter Jacke
```

Nicht zulässig wäre, die rote Jacke wegen eines Personality-Stereotyps automatisch dunkelblau zu machen.

### 21.12 Vollständiger Turn-Ablauf

```text
1. Director lädt hardcodierten Story Node.
2. Fehlende Input Requirements werden gegen den Save State geprüft.
3. Erzähler bettet das nächste Requirement spielerisch in die Szene ein.
4. User antwortet per Choice, Bildauswahl oder Freitext.
5. Server validiert Aktion und Ziel des Inputs.
6. Playground Author normalisiert die Antwort und aktualisiert einen Draft.
7. Director aktualisiert Personality-Development-, Relationship- und Story State deterministisch.
8. Falls vorgesehen, erzeugt der Director einen Personality-basierten Speech Contract.
9. Character Dialogue LLM formuliert die kontrollierte Reaktion der Figur.
10. Falls ein visueller Reifegrad erreicht ist, wird eine Test- oder Story-Combo geplant.
11. Bilder werden generiert und innerhalb derselben Timeline reviewed.
12. Rating und Fehlergründe aktualisieren Draft, Combo-Evidenz und Recovery.
13. Freigegebene Inhalte werden in persönliche Playground- und Combo-Daten übernommen.
14. Der nächste authorisierte Story Node wird freigeschaltet.
```

Nicht jeder Turn führt alle Schritte aus. Ein früher Turn kann nur Erzählerfrage und Draft-Update enthalten; ein später Turn kann gleichzeitig Character-Reaktion, Storyfortschritt und visuelle Generierung auslösen.

### 21.13 Feste Produktentscheidungen dieser Richtung

- Die erste Userinteraktion ist immer ein geführter VN-Prolog mit Erzähler, Mutter-Silhouette und authored Choices.
- Character Chat wird nach ausreichender Character Definition als Fähigkeit innerhalb derselben zusammenhängenden Oberfläche freigeschaltet.
- Character Chat Ready und Chronicle Ready sind getrennte Reife-Gates.
- Nach den ersten Character-Bildern bilden die Bild-Games die zentrale Progression zum benötigten VN-Asset-Pool.
- Die VN-Darstellung wird erst bei ausreichender visueller Abdeckung freigeschaltet.
- Nach Chronicle Ready entsteht ein dauerhafter Mix aus VN, Character Chat und Bild-Games.
- Der hardcodierte Erzähler bleibt die dauerhafte Rahmeninstanz.
- Sämtlicher erforderlicher User-Input wird spielerisch durch authorisierte Storyturns erhoben.
- Der User schreibt keine Diffusion-Prompts und bearbeitet keine technischen Datenbankfelder.
- Das Character Dialogue LLM entscheidet weder Story noch Personality.
- Das Playground Author LLM erzeugt persönliche Component- und Combo-Drafts, schreibt aber nie direkt in SQLite.
- Die 16 Personality-Typen besitzen explizite versionierte Behavior Packs.
- Expliziter Userinput besitzt Vorrang vor Personality-Gewichtungen und LLM-Vorschlägen.
- Die Entwicklungs-Playground- und Combo-Prompt-Daten werden nicht ausgeliefert.
- Persönliche Playground- und Combo-Daten entstehen durch Chat, Bildgenerierung und Review.
- Die Combo Prompt DB bleibt zentrale Evidenzschicht für Qualität, Stabilität, Laufzeit und Wiederverwendung.
- Story-Progression, Profile Scoring, Commit, Recovery und Save State bleiben deterministisch.

### 21.14 Nächster Deep Dive

Als nächster Schritt wird der `ChatTurnContract` vollständig ausdefiniert:

1. zulässige Phasen und Turnarten,
2. Aufbau und Priorisierung mehrerer Input Requirements,
3. Choice-, Freitext- und Bildauswahl-Verarbeitung,
4. Regeln für Character-Reaktionen im selben Turn,
5. Draft- und Combo-Operationen,
6. visuelle Trigger und blockierende Voraussetzungen,
7. Eventfolge, Idempotenz und Save/Load,
8. sowie Fallbacks bei ungültigem Userinput oder LLM-Ausfall.

Dieses Objekt bildet die zentrale Runtime-Schnittstelle zwischen authored Story, einem einzigen sichtbaren Chat, den zwei begrenzten LLM-Rollen und der persönlichen Bilddatenbank.

## 22. Technische Referenzentscheidung für LLMs und Retrieval

### 22.1 Zwei logische Rollen, nicht zwingend zwei physische Modelle

Character Speaker und Playground Author bleiben fachlich, technisch und in ihren Datenverträgen getrennt. Für den ersten Prototyp müssen dafür jedoch nicht zwei Modelle gleichzeitig im Speicher liegen.

Die vorläufige Referenzkonfiguration lautet:

| Aufgabe | Referenzmodell oder System | Ausführung |
|---|---|---|
| Hardcoded Story und Erzähler | kein LLM | deterministischer Game Director |
| Playground Author | `qwen3-8b` | lokal über LM Studio |
| Character Speaker | zunächst ebenfalls `qwen3-8b` mit getrenntem Contract | lokal über LM Studio |
| Text Retrieval | `qwen3-embedding-0.6b` | lokal über LM Studio |
| schneller Text-Retrieval-Fallback | `text-embedding-nomic-embed-text-v1.5` | lokal über LM Studio |
| Cloud-Vergleich und möglicher Speaker während Bildgenerierung | Gemini Flash | Google Gemini API |
| visuelles Retrieval, spätere Ausbaustufe | SigLIP-2-Klasse | eigener lokaler Worker |

Die Anwendung kennt keine modellspezifische Spiellogik. Ein Provider Layer kapselt mindestens:

```text
CharacterSpeakerPort
├── LMStudioCharacterSpeaker
└── GeminiCharacterSpeaker

PlaygroundAuthorPort
├── LMStudioPlaygroundAuthor
└── GeminiPlaygroundAuthor
```

Beide Rollen verwenden eigene Systemverträge, Schemata, Temperatur- und Tokenlimits. Ein Modell darf nicht allein deshalb Zugriff auf beide Kontexte erhalten, weil beide Rollen zunächst vom selben Modell ausgeführt werden.

### 22.2 OpenAI-kompatible Calls und erzwungener Structured Output

LM Studio wird über seine OpenAI-kompatible API angesprochen. Für strukturierte Aufgaben wird das erwartete Ergebnis nicht nur im Prompt beschrieben, sondern über `response_format.type = json_schema` und ein striktes JSON-Schema beim Sampling erzwungen.

Beispielhafter Aufruf:

```json
{
  "model": "qwen3-8b",
  "messages": [],
  "response_format": {
    "type": "json_schema",
    "json_schema": {
      "name": "component_draft",
      "strict": true,
      "schema": {}
    }
  }
}
```

Schema-Erzwingung ersetzt keine fachliche Validierung. Die verbindliche Verarbeitungskette lautet:

```text
Schema-constrained Generation
→ JSON parsen
→ gegen typisiertes Anwendungsschema validieren
→ Explicit User Locks und Scope-Regeln prüfen
→ höchstens ein gezielter Repair-Call mit konkreten Fehlern
→ deterministischer Fallback oder erneute Userfrage
```

Ein formal gültiger Draft ist beispielsweise trotzdem unzulässig, wenn die Antwort `dunkelblau`, `kurz`, `goldene Nähte` oder das Verbot `nicht militärisch` verliert. Umgekehrt darf ein Outfit-Draft keine Pose, Beleuchtung, Szene oder Handlung ergänzen.

Tokenlimits werden so gewählt, dass ein begonnenes JSON-Objekt vollständig beendet werden kann. Für Qwen-3-Modelle wird der Thinking-Modus bei diesen kurzen Runtime-Aufgaben deaktiviert. Rohantworten, Validierungsfehler, Repair-Anzahl, Modell-ID, Prompt-Contract-Version und Laufzeit werden als Telemetrie gespeichert.

Offizielle Referenz: [LM Studio Structured Output](https://beta.lmstudio.ai/docs/developer/openai-compat/structured-output)

### 22.3 Lokaler Modelltest vom 26. August 2026

Die auf dem Entwicklungsrechner installierten Modelle wurden mit denselben kleinen Playground-Author- und Character-Speaker-Contracts über `/v1/chat/completions` getestet. Die Messwerte enthalten beim Cold Call auch das Laden des Modells und sind keine allgemeingültigen Benchmarks.

Testhardware:

- NVIDIA GeForce RTX 3060 mit 12 GB VRAM,
- etwa 32 GB System-RAM,
- LM Studio als OpenAI-kompatibler lokaler Server,
- geladener Kontext für `qwen3-8b`: 8192 Tokens.

Ergebnisse:

| Modell | Beobachtung | Vorläufige Einstufung |
|---|---|---|
| `qwen3-8b` | vollständiger Outfit-Draft, korrekter enger deutscher Dialog, gute Contract-Treue | lokaler Referenzkandidat |
| `llama-3.1-sauerkrautlm-8b-instruct` | brauchbares Deutsch und gültiger Dialog | Speaker-Vergleichskandidat |
| `qwen2.5-7b-instruct` | formal gültig, ließ im ersten Author-Test wichtige Promptfragmente leer | nur mit verbesserter Semantikprüfung |
| `gemma-3-12b-it` | langsamer und ergänzte unerlaubt Pose beziehungsweise Beleuchtung | kein Referenzmodell für enge Drafts |
| `qwen3-4b-rpg-roleplay-v2` | valides Schema, erfand jedoch Handlungen des Spielers | für den kontrollierten Speaker ungeeignet |
| `mistral-nemo-12b-arliai-rpmax-v1.3` | sehr langsam und am Tokenlimit unvollständig | derzeit ungeeignet |

Gemessene Referenzwerte für `qwen3-8b`:

- Cold Playground-Author-Call inklusive Laden: etwa 15,0 Sekunden,
- warmer Playground-Author-Call: etwa 2,3 Sekunden,
- warmer Character-Speaker-Call: etwa 1,6 Sekunden,
- GPU-Gesamtbelegung nach dem Laden: etwa 8,7 GB,
- verbleibender VRAM: etwa 3,3 GB.

Der geschätzte zusätzliche GPU-Verbrauch gegenüber dem vorherigen Zustand beträgt damit ungefähr 5,2 GB. Eine schwere ComfyUI-Generation und `qwen3-8b` sollen auf dieser Hardware nicht unkoordiniert gleichzeitig laufen.

### 22.4 Verbindlicher GPU-Scheduler

LM Studio, Bildmodelle und spätere visuelle Encoder teilen sich dieselbe GPU. Der Backend-State bleibt die Source of Truth; Frontend oder Renderer dürfen keine Modellbelegung steuern.

Die zunächst bevorzugte Folge lautet:

```text
User antwortet
→ Playground Author auf Qwen 3 8B
→ Draft validieren und Prompt deterministisch kompilieren
→ Qwen bei anstehender schwerer Bildgeneration entladen
→ ComfyUI-Job ausführen
→ Bilder reviewen
→ Qwen bei Bedarf erneut laden
```

Während ComfyUI die GPU belegt, darf der Character Speaker optional über Gemini laufen. Dadurch kann ein Dialog die Generierungswartezeit spielerisch überbrücken, ohne mit ComfyUI um lokalen VRAM zu konkurrieren. Diese Parallelisierung ist ein Optimierungsweg, keine Voraussetzung für korrekten Fortschritt.

Jeder LLM- und Bildjob besitzt:

- `job_id`,
- `role`,
- `provider`,
- `model_id`,
- Priorität,
- Timeout,
- geschätzten Ressourcenbedarf,
- tatsächliche Laufzeit,
- sowie Abbruch- und Fallbackgrund.

### 22.5 Gemini als austauschbarer Cloud-Provider

Gemini erhält keine Sonderrechte im Game Director. Es muss dieselben fachlichen Contracts, JSON-Schemas und semantischen Validatoren wie der lokale Provider erfüllen.

Zu evaluierende Kandidaten:

- eine Flash-Lite-Variante für hohe Call-Zahl und einfache Normalisierung,
- eine Flash-Variante für besseren Character-Dialog,
- die jeweils aktuelle stabile Flash-Generation als Qualitätsvergleich.

Gemini 3.7 Flash unterstützt Text- und Bildeingaben sowie Structured Outputs. Die konkrete Free-Tier-Verfügbarkeit und Rate Limits werden nicht als dauerhafte Produkteigenschaft vorausgesetzt, weil Google die tatsächlich verfügbaren Limits accountabhängig in AI Studio ausweist.

Vor einer Produktentscheidung wird derselbe goldene Testkorpus gegen lokal und Gemini ausgeführt. Bewertet werden:

- Schema-Passrate,
- vollständige Übernahme expliziter User Locks,
- Vermeidung unerlaubter Ergänzungen,
- Personality- und Speech-Contract-Treue,
- Qualität und Natürlichkeit deutscher Dialoge,
- Cold- und Warm-Latenz,
- Rate-Limit-Fehler,
- Kosten pro 1000 Turns,
- sowie Datenschutz- und Offline-Verhalten.

Offizielle Referenzen:

- [Gemini 3.7 Flash](https://ai.google.dev/gemini-api/docs/models/gemini-3.7-flash)
- [Gemini Structured Outputs](https://ai.google.dev/gemini-api/docs/structured-output)
- [Gemini Pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini Rate Limits](https://ai.google.dev/gemini-api/docs/rate-limits)

Im Entwicklungsprojekt ist zum Stand dieser Entscheidung noch kein Gemini API Key konfiguriert. Gemini wurde deshalb noch nicht gegen den lokalen Testkorpus gemessen.

### 22.6 Text Memory und Text Retrieval

Text-RAG ist keine frei umgeschriebene Chat-Historie. Die kanonische Wahrheit besteht aus strukturierten und versionierten Records:

- bestätigte Character Facts,
- Explicit User Locks,
- Relationship State,
- Story Events,
- freigegebene Memories,
- persönliche Playground-Items,
- und Review-Evidenz.

Embeddings dienen nur der Kandidatensuche. Der Director filtert anschließend nach Character-Version, Story-Zeitpunkt, Freigabe, Scope und Widerspruchsfreiheit.

In einem kleinen deutschen Retrieval-Test lieferten sowohl `qwen3-embedding-0.6b` als auch `text-embedding-nomic-embed-text-v1.5` die passende dunkelblaue Jacke auf Rang eins. Der Qwen-Encoder bleibt wegen der mehrsprachigen Zielsetzung der bevorzugte Kandidat; Nomic bleibt ein schneller, kleiner Vergleichs- und Fallbackpfad. Die endgültige Auswahl erfordert einen projektbezogenen Retrieval-Testkorpus.

### 22.7 Image Retrieval ist kein reines Vektor-RAG

Für VN-Bilder gelten zuerst harte fachliche Filter:

```text
Character und Character-Version
→ Asset Role und Story-Slot
→ Canon- und Freigabestatus
→ Outfit, Pose, Expression und Scene
→ Content Level und Forbidden Constraints
→ Review-, Stability- und Qualitätsgrenzen
→ erst danach visuelle Ähnlichkeit
```

Ein visuell ähnliches, aber falsches Outfit oder eine falsche Character-Version darf nie durch einen hohen Embedding-Score ausgewählt werden.

Jedes freigegebene Bild speichert mindestens:

- Prompt- und Component-Snapshot,
- Character-Version,
- bestätigte sichtbare Tags,
- Asset Role,
- Story-Bindungen,
- Review- und Fehlerdaten,
- Generierungsrecipe und Seed,
- sowie später optional einen visuellen Embedding-Vektor.

Für spätere Image-Text- und Image-Image-Suche ist ein separater lokaler SigLIP-2-Worker ein sinnvoller Kandidat. Dieser Worker ist kein drittes erzählendes LLM und besitzt keine Story- oder Prompt-Autorität.

Offizielle Modellreferenz: [SigLIP 2 Base](https://huggingface.co/google/siglip2-base-patch16-224)

### 22.8 Docker und Headless-Betrieb

Docker verändert die Modellqualität oder den verfügbaren VRAM nicht. Es kann später reproduzierbare, unabhängig aktualisierbare Services für Embeddings, SigLIP oder einen lokalen LLM-Server liefern.

Aktueller Entwicklungszustand:

- Docker-Client ist installiert,
- Docker-Desktop-Daemon läuft derzeit nicht,
- GPU-Nutzung unter Docker Desktop für Windows würde den WSL2-Backend voraussetzen.

Vorläufige Betriebsentscheidung:

- LM Studio bleibt die einfachste Entwicklungsumgebung,
- für einen späteren headless Betrieb werden `llmster` oder ein schlanker `llama.cpp`-Server geprüft,
- Docker wird zuerst für klar abgegrenzte Worker erwogen,
- vLLM ist auf einer einzelnen RTX 3060 und bei geringer Parallelität zunächst nicht die bevorzugte Lösung.

Offizielle Referenzen:

- [LM Studio Developer und Headless Deployment](https://lmstudio.ai/docs/developer)
- [Docker Desktop GPU Support unter Windows](https://docs.docker.com/desktop/features/gpu/)
- [llama.cpp Server](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md)
- [vLLM Docker Deployment](https://docs.vllm.ai/en/latest/deployment/docker/)

### 22.9 Vorläufig festgelegte technische Richtung

- Zwei LLM-Rollen bleiben getrennt, dürfen aber zunächst dasselbe physische Modell verwenden.
- `qwen3-8b` ist der lokale Referenzkandidat für Playground Author und Character Speaker.
- Alle strukturierten Calls verwenden erzwungenen Structured Output plus nachgelagerte semantische Validierung.
- Der Prompt-Compiler und nicht das LLM erzeugt den finalen Diffusion-Prompt.
- Der Game Director und nicht das LLM schreibt Story-, Relationship- oder Canon-State.
- Ein zentraler GPU-Scheduler koordiniert lokale LLMs, ComfyUI und visuelle Encoder.
- Gemini bleibt ein austauschbarer Provider und möglicher Character Speaker während lokaler Bildgenerierung.
- Text- und Image-Retrieval besitzen getrennte Pipelines.
- Strukturierte Metadaten und harte Filter haben Vorrang vor Embedding-Ähnlichkeit.
- Docker ist eine spätere Betriebs- und Packaging-Option, keine Voraussetzung für den Prototyp.

### 22.10 Nächster inhaltlicher Deep Dive

Als nächstes wird der tatsächliche Spielerablauf des Prologs spezifiziert:

1. erste verbindliche Geschlechtswahl,
2. spielerische Erhebung der visuellen Basismerkmale,
3. Instanziierung des sechzehnköpfigen Casts aus sechzehn unterschiedlichen Base-Personality-Profilen,
4. kontrollierter Random-Anteil,
5. erster Playground- und Character-Draft,
6. erste Bildgeneration,
7. Bildreview und Canon-Kandidat,
8. erstmalige Character-Reaktion,
9. Character Chat Ready,
10. sowie der Übergang in die ersten bildbasierten Memory Trials.

Dabei wird für jeden Turn entschieden, welcher Text authored ist, welche Auswahl der User trifft, ob der Playground Author benötigt wird, ob der Character Speaker bereits sprechen darf und welches konkrete Bild- oder Progressionsziel daraus entsteht.

## 23. Japanisches Schuljahr, Character Routes und Character Branding

### 23.1 Präzisierung der 32 geschlechtsspezifischen Character-Schablonen

Die 16 Personality-Profile werden jeweils als männliche und weibliche Verhaltens- und Storyschablone authored. Daraus entsteht ein Katalog mit 32 `GenderedCharacterBlueprints`:

```text
16 Personality-Grundprofile
× 2 Geschlechtsvarianten
= 32 geschlechtsspezifische Character Blueprints
```

Ein einzelner Save verwendet daraus einen aktiven Cast von sechzehn Fokusfiguren. Die 32 Blueprints sind ausdrücklich **keine 32 vorgefertigten, wiederkehrenden Personen**. Sie entsprechen eher einem Tomodachi-Life-artigen Schablonensystem: Ein Blueprint definiert erlaubte Ausgangsausprägungen, Verhaltensgrenzen und mögliche Entwicklungsrichtungen. Name, konkretes Aussehen, Character Brand, Beziehungen und erlebter Canon gehören dagegen zur Figureninstanz des jeweiligen Saves.

Männliche und weibliche Schablonen sind keine Pronomen- oder Sprite-Swaps. Sie dürfen gemeinsame abstrakte Storyfunktionen verwenden, besitzen jedoch getrennt authorbare:

1. Character Brands und visuelle Seeds,
2. soziale Rollen und Beziehungen,
3. Character-Arc-Beats,
4. Scene- und Speech Contracts,
5. Outfit-, Pose- und Expression-Anforderungen,
6. Friendship-/Romance-Ausprägungen,
7. Grenzen, Konflikte und Outcomes.

Jede aktive Figur besitzt ein festes Base-Personality-Profil als charakterliches Gravitationszentrum und historischen Ausgangspunkt. Userentscheidungen verändern ihre langfristigen Achsenwerte einzeln und gewichtet. Überschreitet eine Achse die Mitte, entsteht unmittelbar ein anderer Current Type innerhalb derselben 16er-Topologie. Ein freier, achsenloser oder durch ein LLM bestimmter Typwechsel bleibt ausgeschlossen.

### 23.2 Setting: fiktive japanische Senior Academy

Die Handlung spielt an einer fiktiven japanischen Senior Academy. Sie verwendet bewusst die erkennbare Struktur eines typischen japanischen Schuljahres, ist aber kein exaktes Abbild einer konkreten realen Schule.

Verbindliche Setting-Regeln:

- Das Schuljahr läuft von April bis März.
- Der Protagonist zieht für das letzte Schuljahr in eine neue Stadt.
- Alle sechzehn Hauptfiguren und alle möglichen Romance Characters sind zu Beginn der Handlung mindestens 18 Jahre alt.
- Die Academy besitzt Uniformen, Klassen, Wahlfächer, Clubs, Schülervertretung, Prüfungen und typische saisonale Schulereignisse.
- Der fiktive Academy-Status erlaubt typische JRPG-/VN-Schulästhetik, ohne reale Alters- oder Ausbildungsregeln erzählerisch verbiegen zu müssen.

Das gemeinsame Chronicle-Projekt begleitet das Abschlussjahr. Es gibt dem Protagonisten einen glaubwürdigen Anlass, bestehende Beziehungen und frühere Erinnerungen der Gruppe kennenzulernen und im letzten gemeinsamen Jahr neue Erinnerungen mit ihr zu schaffen.

### 23.3 Hardcodierter Jahresrahmen

Der Calendar Director besitzt eine feste Folge wiederkehrender Zeitfenster:

| Zeitraum | Feste Settings und Ereignisse | Hauptfunktion |
|---|---|---|
| Ende März und April | Umzug, Kirschblüten, Schulweg, Eröffnung, Homeroom, Orientierung | Player Core, erste Ankerfigur und erster Canon |
| Ende April und Mai | Club Recruitment, Golden Week, erste Ausflüge, Midterms | erster Sozialkreis und Alltag außerhalb des Unterrichts |
| Juni | Regenzeit, Clubs, Chronicle-Projekt, gemeinsame Aufgaben | erste persönliche Konflikte und weitere Figuren |
| Juli | Prüfungen, Tanabata, Ferienplanung | vollständiger Cast und erste klare Beziehungspräferenzen |
| August | Sommerferien, Training Camp, Meer, Sommerfestival, Feuerwerk | große Ensemble- und Fokus-Events |
| September | Rückkehr, Sportfest-Vorbereitung, Teamkonflikte | Gruppendynamik und Konkurrenz |
| Oktober | Sportfest, Kulturfestival und Vorbereitungen | zentraler gemeinsamer Jahreshöhepunkt |
| November | Schulausflug oder Herbstfahrt | vertiefte Friendship-/Romance-Szenen |
| Dezember | Prüfungen, Winter, Weihnachten | Route Intent und erste klare Beziehungsentscheidung |
| Januar | Hatsumōde, Zukunftsplanung, Abschluss- und Prüfungsdruck | Zukunftskonflikte und Character Crisis |
| Februar | Valentinstag und Abschlussvorbereitung | persönlicher Route Climax |
| März | White Day, Abschied, Graduation und Chronicle Reveal | Auflösung und Endings |

Die konkreten Daten sind authored und werden nicht von einem LLM erfunden. Varianten einzelner Ereignisse dürfen durch Character Focus, Relationship State, Personality State und Visual Readiness ausgewählt werden.

### 23.4 Character Brand Instance statt profilloser Ausgangsfigur

Eine Figur ohne bereits festgelegten sichtbaren Development State ist keine neutrale oder leere Figur. Bei der Instanziierung einer der 32 Schablonen kompiliert der Director einen save-spezifischen `CharacterBrandSeed`, der die konkrete Figur vom ersten Auftritt an klar erkennbar macht. Die zulässigen Brand-Bausteine und Widerspruchsregeln sind authored; ihre konkrete Kombination wird aus Schablone, Prolog-Evidenz, World Canon, Cast-Diversity und kontrolliertem Zufall bestimmt.

Der Brand Seed definiert mindestens:

- narrative Rolle im Sozialkreis,
- sichtbare erste Wirkung,
- persönliche Leidenschaft oder Kompetenz,
- zentrale Sehnsucht,
- inneren Widerspruch,
- individuelles Problem oder Geheimnis,
- bestehende Beziehungen zu mindestens zwei anderen Figuren,
- wiederkehrenden Ort,
- symbolisches Motiv oder Signature Prop,
- charakteristische Situationen und wiederkehrende Gesten,
- visuellen Silhouetten- und Outfit-Rahmen,
- sowie Grenzen dessen, was die Figur auch durch Userinput nicht beliebig werden kann.

Das Branding wird bewusst nicht auf ein MBTI-Stereotyp reduziert. Jeder Gendered Character Blueprint ist bereits mit genau einem Grundprofil verbunden, erhält darüber hinaus aber ein eigenes Motiv, einen Konflikt, Beziehungen und Widersprüche. Zwei Figuren mit ähnlichen sichtbaren Verhaltensweisen dürfen deshalb trotzdem aus unterschiedlichen inneren Gründen handeln.

Beispielsweise kann eine Figur des Chronicle-Projekts eine alte Kamera, ein starkes Interesse an vergänglichen Momenten und die Angst besitzen, vergessen zu werden. Ihr Base Profile beeinflusst, von welchem Punkt aus sie mit diesem Motiv umgeht. Relationship State, Memories und wiederholte Inputs können ihre Current Axes weiterentwickeln und dadurch auch das Current Profile verändern. Motiv, Brand, erlebter Canon und Base-Herkunft werden dadurch nicht ausgetauscht.

### 23.5 Brand Seed, Brand Canon und veränderbare Ebenen

Vor der ersten Bildfreigabe existiert ein `BrandSeed`. Während der Einführung darf der User Aussehen, Stil und einzelne Ausdrucksformen durch geführte Antworten beeinflussen. Nach einem akzeptierten Canon-Portrait wird daraus ein versionierter `BrandCanon`.

#### Weitgehend stabile Identität

- narrative Rolle,
- Backstory und zentrale Beziehungen,
- Leidenschaft und Kernkonflikt,
- Signature Motif und wiederkehrende Orte,
- grundlegende visuelle Erkennbarkeit,
- bereits bestätigte Canon Facts.

#### Durch den User mitformbare Entwicklung

- sichtbarer Ausdruck der vier Personality-Achsen innerhalb der Influence Bounds,
- Umgang mit dem eigenen Konflikt,
- Vertrauen, Offenheit und Nähe,
- Humor und Kommunikationsverhalten,
- Selbstbild und Zukunftsentscheidung,
- Friendship- oder Romance-Entwicklung,
- Outfits und visuelle Selbstdarstellung innerhalb des Brandings.

#### Kurzfristiger dynamischer Zustand

- Stimmung,
- aktuelle Expression,
- situative Pose,
- Konfliktintensität,
- Reaktion auf die letzte Userentscheidung,
- aktueller Gesprächs- und Szenenkontext.

Der User kann eine Figur beeinflussen, aber nicht vollständig umprogrammieren. Authorisierte Character-Entscheidungen, kontrollierter Random-Anteil, frühere Erfahrungen und bestehende Beziehungen bewahren ihre Eigenständigkeit.

### 23.6 Base-Herkunft, entwickelte Achsen und situativer Ausdruck

Jede Figur besitzt vom Zeitpunkt der Cast Assembly an ein festes, zunächst verborgenes `BasePersonalityProfile` und einen unveränderlichen `BaseAxisVector`. Zusätzlich führt sie einen langfristig veränderlichen `DevelopedAxisVector`. Aus dessen vier Vorzeichen wird das `CurrentPersonalityProfile` abgeleitet. Der `PersonalityExpressionState` bildet ausschließlich den kurzfristigen, situationsabhängigen Ausdruck ab.

Der sichtbare Ausdruck entsteht aus:

```text
Current Personality Behavior Pack
+ kontinuierlicher DevelopedAxisVector
+ Base-Herkunft, Character Brand und bisherige Erfahrungen
+ Memories, Relationship State und Userentscheidungen
+ aktueller Szenen-, Stress- und Gesprächskontext
= aktueller PersonalityExpressionState
```

Große saisonale Ereignisse dienen als Personality Trials. Sie prüfen nicht durch einen Fragebogen, sondern durch Verhalten in einer konkreten Situation:

- Frühling: Kontaktaufnahme, soziale Energie und Rückzug,
- Frühsommer: Wahrnehmung, Interessen und Interpretation,
- Herbst: Entscheidungen, Loyalität und Konflikt,
- Winter: Planung, Freiheit, Zukunft und Bindung.

Der Character Speaker erhält immer den bereits bestimmten aktuellen Behavior Contract. Das Base Profile wird nicht durch Userentscheidungen erzeugt. Der Current Type kann sich jedoch durch wiederholte gewichtete VN- und Chatinputs sowie authorisierte Memory-Impulse entlang einzelner Achsen entwickeln. Der Character Speaker formuliert nur die daraus folgende Oberfläche und darf weder Achsenwerte noch Typwechsel bestimmen.

Für jedes Profil beziehungsweise jeden Blueprint werden Influence Bounds definiert:

- `compatible`: Impuls passt zur Figur und kann Entwicklung sowie Beziehung fördern,
- `stretch`: Figur kann sich mit ausreichendem Vertrauen vorsichtig bewegen,
- `resistant`: sichtbares Verhalten ändert sich kaum; Spannung oder Distanz kann steigen,
- `core_violation`: Impuls widerspricht einem Kernwert und erzeugt ein authored negatives Relationship Outcome.

Der Spieler kann daher nicht jede Figur in jede Richtung drängen. Wiederholte Inkompatibilität darf dazu führen, dass eine Route stagniert und der Daily Scheduler eine passendere Figur stärker in den Fokus rückt.

### 23.7 Fester Rhythmus eines spielbaren Schultags

Nicht jeder Kalendertag wird vollständig ausgespielt. Routine darf durch authored Montagen übersprungen werden. Jeder tatsächlich spielbare normale Schultag verwendet jedoch einen wiedererkennbaren Ablauf:

```text
Schulweg
→ Homeroom und Tagesankündigung
→ Unterrichtsblock
→ Pausen-Event
→ weiterer Unterrichtsblock
→ Mittagspause
→ Nachmittagsunterricht
→ Club oder freie Aktivität
→ Nachmittags- beziehungsweise Abend-Event
→ Character Chat oder Bildreview
→ Tagesabschluss und Save State
```

Ein normaler Tag enthält nicht in jedem Slot eine große Szene. In der Regel gibt es:

- eine relevante Character-Interaktion,
- optional ein kurzes Pausen- oder Schulweg-Event,
- einen Fortschritt bei einem bevorstehenden Visual Need,
- und eine erkennbare Zeitbewegung im Schuljahr.

### 23.8 Kontrollierter Zufall für Unterricht und Begegnungen

Fächer, Sitz- oder Projektpartner, Gangbegegnungen und kleine Pausen-Events dürfen kontrolliert variieren. Der Scheduler berücksichtigt dabei:

- gewählte oder erkennbare Fokusfigur,
- aktuelle Character-Arc-Stufe,
- noch offene Personality-Evidenz,
- Relationship State,
- vorhandene Visual Assets,
- Figuren, die lange nicht vorkamen,
- Wiederholungsvermeidung,
- sowie fest blockierte Calendar Events.

Reiner Zufall ist nicht zulässig. Ein Romance- oder Friendship-Fokus muss die Wahrscheinlichkeit sinnvoller Begegnungen erhöhen, ohne andere Figuren vollständig aus dem sozialen Kreis zu entfernen.

Die Academy besitzt einen festen Homeroom, aber Wahlfächer, Projekte, Clubs, Sportgruppen und Chronicle-Aufgaben erlauben unterschiedliche Figurenkombinationen.

### 23.9 Fokusfigur und große Calendar Events

Große Ereignisse besitzen einen gemeinsamen authored Rahmen und einen bindbaren `focus_character_id`. Der Spieler bestimmt die Fokusfigur durch frühere Entscheidungen, direkte Einladung oder akkumulierte Beziehungspriorität.

Beispiel Sommerfestival:

```text
Festival wird im Kalender angekündigt
→ Focus Candidate Pool wird bestimmt
→ Spieler lädt eine Figur ein oder bestätigt die entstehende Priorität
→ Event-spezifischer Character-Arc-Beat wird gewählt
→ Personality Trial und Relationship Intent werden festgelegt
→ Visual Requirements werden erzeugt
→ Bilder werden generiert und reviewed
→ Visual Readiness erreicht
→ VN-Szene läuft mit der Fokusfigur
→ Story-, Personality- und Relationship-State werden aktualisiert
```

Der Eventrahmen mit Ort, Zeitpunkt, Hauptbeats und erlaubten Übergängen bleibt authored. Character Speaker und Playground Author arbeiten ausschließlich innerhalb des konkreten Event Contracts.

### 23.10 Visual Readiness vor einer VN-Szene

Die Fokusentscheidung muss früh genug erfolgen, damit die benötigten Bilder vor der eigentlichen VN-Szene erstellt werden können. Der Calendar Director kennt kommende Großereignisse mehrere In-Game-Wochen im Voraus und erzeugt rechtzeitig Visual Needs.

Ein Event kann beispielsweise benötigen:

- einen freigegebenen Hintergrund,
- ein Event-Outfit der Fokusfigur,
- erforderliche Expressions und Posen,
- ein oder mehrere Character Sprites,
- sowie ein optionales oder verpflichtendes Key Visual.

Die benötigten Inhalte werden durch Bild-Games generiert, verglichen, korrigiert und stabilisiert. Erst die freigegebenen Assets dürfen im VN Event verwendet werden.

Dadurch entsteht der verbindliche Loop:

```text
bevorstehendes Story Event
→ Fokusfigur und Character Beat
→ Event Visual Manifest
→ Prompt- und Bild-Trys
→ Review und Recovery
→ Visual Ready
→ VN-Szene
→ neue Character- und Story-Entwicklung
```

### 23.11 Zusammengesetzter Event Contract

Eine konkrete Route-Szene wird als serialisierbare Verbindung der drei Storyschichten beschrieben:

```json
{
  "event_id": "summer_festival",
  "calendar_window": "august_week_2",
  "scene_setting_id": "festival_fireworks_return_path",
  "focus_character_id": "character_04",
  "character_arc_beat_id": "first_voluntary_vulnerability",
  "personality_state_revision": 7,
  "personality_trial_axis": "social_openness",
  "relationship_mode": "undecided",
  "relationship_stage": "growing_trust",
  "narrator_beat_set_id": "summer_festival_return_v1",
  "required_visual_manifest_id": "visual_need_0184",
  "visual_ready": false
}
```

Aus diesem Contract entstehen konkrete Speech Contracts, Choices, Visual Requirements und State Events. Das LLM darf weder den Calendar Event noch den Character-Arc-Beat austauschen.

### 23.12 Festgelegte inhaltliche Richtung

- Das japanisch geprägte Schuljahr von April bis März ist das gemeinsame Storygerüst.
- Normale Schultage besitzen einen festen Rhythmus mit kontrolliert variierenden Fächern und Begegnungen.
- Ein aus 32 Schablonen zusammengestellter aktiver Cast aus sechzehn save-spezifisch instanziierten und gebrandeten Figuren bildet den Sozialkreis.
- Jedes der 16 Personality-Profile ist als unterschiedliches Base Profile genau einmal im aktiven Cast repräsentiert; Current Profiles dürfen sich durch unabhängige Achsenentwicklung doppeln oder zeitweise fehlen.
- Der Character Brand verhindert, dass eine frühe oder noch offene Personality profillos wirkt.
- Userinput beeinflusst Entwicklung und Selbstausdruck, überschreibt aber nicht beliebig Backstory, Kernkonflikt oder bestehende Beziehungen.
- Große Calendar Events besitzen eine Fokusfigur und treiben gleichzeitig Schuljahr, Character Arc, Personality und Relationship voran.
- Friendship und Romance verwenden dieselben gemeinsamen Jahresereignisse, erhalten an definierten Gates aber eigene Varianten.
- Die Bildbewertung findet vor der zugehörigen VN-Szene statt und produziert deren freigegebenen Content.
- Der hardcodierte Calendar Director setzt alle Termine, Szenenrahmen und Progressionsbedingungen.

### 23.13 Nächster inhaltlicher Deep Dive

Als Nächstes werden sechzehn Personality-Slots mit jeweils einer männlichen und einer weiblichen Schablone entworfen. Für jede der 32 Schablonen werden ohne feste Person, Namen und finales Aussehen definiert:

1. Rolle im Sozialkreis,
2. Leidenschaft oder Kompetenz,
3. Sehnsucht und Kernkonflikt,
4. innerer Widerspruch,
5. Verbindung zu mindestens zwei anderen Slots,
6. Signature Motif und wiederkehrender Ort,
7. visuelle Brand-Leitplanken,
8. Character-Arc-Beats über das Schuljahr,
9. geeignete Calendar Focus Events,
10. sowie die Frage, wie sich derselbe Brand glaubwürdig in allen 16 Personality-Entwicklungen ausdrücken kann.

## 24. Langfristiger Character Focus und Visual Champion Quests

### 24.1 Sechzehn aktive Slots aus 32 Gendered Character Templates

Der Autorenkatalog enthält für jedes der 16 Personality-Grundprofile eine männliche und eine weibliche Character-Schablone. Der Cast Assembler instanziiert pro Save sechzehn aktive Fokusfiguren aus diesem 32er-Katalog. Sämtliche Personality-Profile bleiben dadurch als unterschiedliche Base-Ausgangspunkte existent, während Geschlecht, Name, konkrete visuelle Identität und Character Brand erst im Save gebunden werden.

Für jede Figureninstanz gelten:

- genau ein aus authored Regeln kompiliertes, save-spezifisches Character Branding,
- ein verborgenes und unterschiedlich stark ausgeprägtes Grundprofil,
- ein aktueller sichtbarer Personality State,
- sowie ein durch wiederholte Interaktion veränderbarer Development State.

Jeder aktive Slot verwendet genau ein anderes `BasePersonalityProfile`. Damit sind zu Beginn jedes Saves alle 16 Typen als Base-Herkunft vertreten. Für jeden Slot wählt der Cast Assembler die männliche oder weibliche Variante anhand der globalen Cast-Gewichtung und der Diversity-Regeln. Der Base-Ausgangspunkt bleibt stabil; `DevelopedAxisVector`, `CurrentPersonalityProfile` und `PersonalityExpressionState` bewegen sich nach den authored Einfluss-, Gewichts- und Memory-Regeln. Die Current-Type-Verteilung wird nicht künstlich auf genau einen Vertreter pro Typ gezwungen.

### 24.2 Ein Monat gehört keiner einzelnen Figur

Ein monatlicher Fokus bedeutet erhöhte Aufmerksamkeit und nicht den Abschluss einer kompletten Character Story. Eine vollständige Route benötigt wiederkehrende Begegnungen über mehrere Jahreszeiten.

Ein Character-Arc kann folgende Beats besitzen:

1. Einführung,
2. wiederkehrender Alltag,
3. erste freiwillige Annäherung,
4. persönliches Vertrauen,
5. Konflikt oder Rückzug,
6. Personality Trial,
7. Reparatur oder Eskalation,
8. Friendship-/Romance-Entscheidung,
9. Zukunftskonflikt,
10. Graduation Outcome.

Eine Figur darf bei mehreren großen Ereignissen Fokusfigur sein. Beispielsweise kann dieselbe Route über Golden Week, Sommerfestival, Kulturfestival, Schulausflug, Weihnachten, Valentinstag und Graduation fortgesetzt werden.

Ein einzelner Durchlauf soll nicht alle sechzehn persönlichen Geschichten vollständig abschließen können. Der Spieler kann:

- eine oder wenige Figuren sehr tief entwickeln,
- mehrere Friendship Routes weit voranbringen,
- andere Figuren nur teilweise kennenlernen,
- und in späteren Durchläufen andere Character-/Personality-Kombinationen erleben.

Nicht fokussierte Figuren verschwinden nicht. Sie bleiben über Unterricht, Pausen, Clubs, Gruppenereignisse und ihre Verbindungen untereinander im sozialen Kreis sichtbar.

### 24.3 Base, Developed, Current und Expressed Personality

Jede Figur besitzt vier klar getrennte Personality-Sichten:

#### Base Personality

Die verborgene Ausgangstendenz der Figur. Sie wird aus einem der 16 Profile und vier individuellen, von null verschiedenen Achsenstärken instanziert. Base Profile und Base Axis Vector bleiben als Herkunft, Vergleichspunkt und möglicher Memory-Anker erhalten.

#### Developed Personality

Die langfristige Achsenlage, die über das Schuljahr aus gültigen VN- und Character-Chat-Inputs, wichtigen Character Events und authorisierten Memory-Impulsen entsteht. Jede Wirkung betrifft genau eine primäre Achse; weitere Achsen dürfen im selben Turn nur stabilisiert werden. Die Entwicklung bleibt innerhalb der vier vorhandenen Achsen und der 16 zulässigen Typkombinationen.

#### Current Personality

Der aus den Vorzeichen des `DevelopedAxisVector` abgeleitete aktuelle Typ. Überschreitet eine Achse die Mitte, wechselt das Current Profile unmittelbar zum direkten Nachbartyp. Exakt null behält den bisherigen Pol, bis die Achse tatsächlich auf die Gegenseite wechselt. Current Profiles dürfen sich innerhalb des Casts doppeln oder zeitweise fehlen; nur die Base-Verteilung bleibt vollständig.

#### Expressed Personality

Das Verhalten, das die Figur im aktuellen Story- und Relationship State zeigt. Stress, Vertrauen, Umgebung und anwesende Personen können den sichtbaren Ausdruck kurzfristig verstärken, dämpfen oder kontrastieren. Dieser Zustand ist weder Base-Herkunft noch langfristige Entwicklung.

Ein einzelner Input verursacht keinen großen oder achsenlosen Sprung. Liegt die primäre Achse bereits unmittelbar an der Mitte, kann derselbe begrenzte Input jedoch einen Wechsel in genau einen direkten Nachbartyp auslösen. Dieser Wechsel wird ab dem folgenden Turn im Behavior Contract verwendet.

### 24.4 Drei authored VN-Choices als Einfluss

Storyrelevante Interaktionen bieten grundsätzlich drei authored Auswahlmöglichkeiten. Diese werden durch Event und Director definiert und nicht frei von einer LLM erfunden.

Jede Choice besitzt:

- eine verständliche sichtbare Aussage,
- einen unsichtbaren Handlungs- oder Kommunikations-Intent,
- mögliche Personality-Impulse,
- mögliche Relationship-Effekte,
- erlaubte Scene Outcomes,
- sowie Bedingungen, unter denen einzelne Outcomes wahrscheinlicher oder ausgeschlossen sind.

Beispiel:

```json
{
  "choice_id": "trip_planning_spontaneous",
  "visible_text_key": "trip.choice.decide_there",
  "intent": "encourage_flexibility",
  "personality_influence": {
    "judging_perceiving": 8
  },
  "relationship_effects": {
    "trust": 1
  },
  "eligible_outcomes": [
    "reject_spontaneity",
    "accept_small_compromise",
    "embrace_spontaneity"
  ]
}
```

Der Outcome Resolver verwendet:

```text
Base Personality und Base Axis Vector
+ aktueller Developed Axis Vector und Current Personality
+ Character Brand und persönlicher Arc
+ Relationship State
+ authorisierte Memory-Impulse
+ aktueller Situations- und Stresskontext
+ Intent der gewählten Choice
+ kleiner kontrollierter Varianzanteil
= autorisiertes Scene Outcome
```

Der Character Speaker erhält erst das bereits bestimmte Outcome und formuliert die Reaktion. Er darf keine andere Konsequenz auswählen.

Der Outcome Resolver prüft zusätzlich die `InfluenceBounds` des Base Profiles, des Blueprints und des aktuellen Entwicklungsstands. Ein akzeptierter oder ausgehandelter Impuls darf die primäre Achse in Intent-Richtung bewegen. Ein widerständiger oder kernverletzender Impuls stabilisiert stattdessen die bestehende Achsenrichtung und darf Relationship-Werte verschlechtern, Route Gates schließen oder den künftigen Character Focus reduzieren. Der Director kann daraufhin eine andere, kompatiblere Figur häufiger anbieten. Nur eine tatsächliche Achsenüberschreitung erzeugt einen Current-Type-Wechsel.

### 24.5 Eine Choice wirkt auch ohne sichtbaren Outcome-Wechsel

Der User beeinflusst die Figur, kontrolliert sie aber nicht direkt. Wenn Base-Anker, Current Axis, Relationship State oder aktive Memories stark in eine andere Richtung drücken, kann das sichtbare Outcome trotz einer Choice unverändert bleiben.

Die Choice wird dennoch als Ereignis gespeichert und kann beeinflussen:

- eine Personality-Achse,
- Vertrauen oder Nähe,
- Konflikt und Widerstand,
- eine Character Memory,
- Ton und Nuance der aktuellen Reaktion,
- spätere Choice-Verfügbarkeit,
- oder die Wahrscheinlichkeit eines zukünftigen Outcomes.

Unsichtbare numerische Typenpunkte werden nicht unmittelbar angezeigt. Der Spieler erkennt die Wirkung an späterem Verhalten, Dialogen, Entscheidungen und visueller Selbstdarstellung der Figur.

### 24.6 Visual Requirements werden zu verpflichtenden Quest-Ketten

Jeder für die VN benötigte Asset-Slot erzeugt mindestens eine spielbare Bildquest. Das bloße Vorhandensein einer PNG-Datei erfüllt kein Visual Requirement.

Ein `VisualAssetQuest` kann beispielsweise gelten für:

- einen Background,
- ein Character Sprite,
- ein Event-Outfit,
- eine Expression,
- eine Pose,
- ein Key Visual,
- oder ein späteres Outcome CG.

Der Queststatus lautet:

```text
unstarted
→ generating
→ qualifier_review
→ repair_required oder knockout_ready
→ champion_selection
→ champion_validation
→ bound_to_story
```

Nur `bound_to_story` erfüllt einen blockierenden Slot des Event Visual Manifests.

### 24.7 Qualifier: Vierer-Spiele bis zu sechzehn bestätigten Kandidaten

Jede neue Asset Quest erzeugt fortlaufend Vierer-Batches desselben fachlichen Ziels. Ein Batch ist eine spielbare Qualifikationsrunde und niemals allein die Auswahlbasis eines blockierenden Story Assets.

Die Endbedingung ist nicht die Zahl der Runden oder Rohbilder, sondern der Füllstand des bestätigten Kandidatenpools:

```text
Qualifier Batch 1 → 4 Bilder bewerten → 0 bis 4 bestätigte Kandidaten
Qualifier Batch 2 → 4 Bilder bewerten → 0 bis 4 bestätigte Kandidaten
…
wiederholen, bis confirmed_candidate_count = 16
→ erst danach K.-o.-Turnier starten
```

Vier Batches sind lediglich das theoretische Minimum, falls jedes der ersten
sechzehn gezeigten Bilder als Favorite oder Keep bestätigt wird. Bilder mit
technischem Hard Fail, `reject`, `skip` oder ungeklärtem Reviewstatus zählen
nicht zur Sechzehnerzahl. Deshalb können fünf, acht, zwölf oder mehr
Vierer-Runden notwendig werden.

Diese Character- beziehungsweise Asset-Qualifier dürfen einem kontrollierten Variant Plan folgen und sind deshalb nicht automatisch Stability Trials. Sie beantworten, welche visuelle Ausprägung Canon werden soll. Evidenz zur technischen Stabilität entsteht nur in einem getrennten Render Trial, in dem Prompt, fachliche Specification und gepaarte Seeds konstant bleiben.

Die Qualifikation prüft in fester Reihenfolge:

1. richtige Character Identity,
2. richtiger fester Artstyle,
3. keine harten Anatomie-, Hand- oder Hintergrundfehler,
4. korrekte Umsetzung des Asset-Slots,
5. Eignung für die konkrete VN-Verwendung,
6. erst danach ästhetische Qualität.

`Reject` und harte Fehler entfernen ein Bild aus dem Turnier. Sie erzeugen
negative Evidenz und bei systematischen Fehlern einen Repair Run.

Die bereits im Review vergebene Wertung ist zugleich die fachliche
Turnierdisposition:

- `favorite`: klarer Zieltreffer und automatisch challengerberechtigt,
- `keep`: brauchbar, weiterverwendbar und automatisch challengerberechtigt,
- `reject`: für das Ziel nicht brauchbar und nach vollständiger Begründung für
  Delete or Live vorgemerkt,
- `skip`: derzeit nicht sicher beurteilbar und ohne Präferenzevidenz.

`Contender` bezeichnet in älteren Passagen dieses Dokuments nur noch einen
abgeleiteten Pool-Eintrag eines transportgültigen, kontextkompatiblen Keeps oder
Favorites. Es ist keine zusätzliche Spielerwertung und keine strengere Teilmenge
von Keep. Es gibt kein künstliches Maximum pro Batch. Ein Batch ohne Keep oder
Favorite liefert trotzdem wertvolle Fehler-, Recovery-, Style- und
Stabilitätsevidenz, erhöht den Poolfüllstand aber nicht.

Für einen finalen Champion müssen mehrere Contender tatsächlich miteinander verglichen worden sein. Ein einzelner Glückstreffer darf niemals direkt an eine VN-Szene gebunden werden.

### 24.8 K.-o.-Auswahl mit festem Sechzehnerfeld

Sobald exakt sechzehn bestätigte Kandidaten vorliegen, wird ein reguläres Sechzehner-K.-o.-Feld erzeugt:

```text
Round of 16 → 8 Gewinner
Viertelfinale → 4 Gewinner
Halbfinale → 2 Gewinner
Grand Final → 1 Visual Champion
```

Der Spieler hat damit vor jeder Storybindung sowohl jedes Bild im Vierervergleich
beurteilt als auch den späteren Champion mehrfach gegen andere echte Kandidaten
gewählt. Jedes entschiedene Match speichert Gewinner, Verlierer, Runde,
Bewertungsachse, Vergleichskontext und beteiligte Revisionen: Der Gewinner liefert
positive und der Verlierer negative paarweise Qualitätsevidenz. Ein A/B-Sieg
setzt nur den aktuellen Zähler aufeinanderfolgender Niederlagen auf null; die
historische Evidenz bleibt bestehen. Ein einzelner Glückstreffer kann nicht
unmittelbar Champion werden.

#### Stagnations- und Null-Kandidaten-Recovery

Eine oder mehrere vollständig gespielte Vierer-Runden ohne echten Kandidaten werden als negativer Evidenzabschnitt gespeichert. Der Pool wird nicht künstlich mit Live-Bench-Bildern aufgefüllt und das nächste Story-Gate bleibt geschlossen.

Aus den bewerteten Batches werden mindestens abgeleitet:

- Verteilung von Wrong Artstyle, falschen Händen, problematischen Hintergründen und weiteren Löschgründen,
- Character-Identity- und Prompt-Treue-Probleme,
- Anzahl lediglich brauchbarer Live-Bench-Bilder,
- Usable-, Contender- und Delete-Rate,
- wiederkehrende Fehler je Seed, Batch und Promptfragment,
- Modell-, Workflow- und Renderkontext,
- gesamte Generierungszeit und brauchbare Bilder pro Minute,
- sowie die wahrscheinlich zu reparierende Prompt- oder Recipe-Komponente.

Der Recovery-Ablauf lautet verbindlich:

```text
Vierer-Batch spielen
→ bestätigte Kandidaten in den Quest-Pool übernehmen
→ negative Evidenz aus allen übrigen Bildern aggregieren
→ bei unzureichender Trefferquote Prompt-/Recipe-Recovery auslösen
→ nächsten Vierer-Batch erzeugen
→ wiederholen, bis der Pool exakt 16 bestätigte Kandidaten enthält
→ erst dann K.-o.-Readiness durch den Code feststellen
```

Neue Bilder ersetzen ältere Evidenz nicht. Alle Batches und Prompt-/Recipe-Revisionen bleiben getrennt versioniert und vergleichbar. Ein bereits bestätigter Kandidat darf nach einer Revision nur im Pool bleiben, wenn sein `CandidateCompatibilityHash` weiterhin zum unveränderten Visual Requirement, Canon und Style Contract passt; andernfalls wird er archiviert und der Poolplatz neu erspielt.

Eine neue Revision gilt erst dann als Verbesserung, wenn sie gegenüber dem negativen Ausgangsabschnitt eine höhere Contender- oder Usable Rate beziehungsweise eine klar verbesserte Fehlerverteilung zeigt. Weitere Runden dürfen erneut null Kandidaten liefern; der Loop endet trotzdem erst bei sechzehn bestätigten Kandidaten.

Jeder Vergleich bietet zusätzlich zu links, rechts, Gleichstand und nicht vergleichbar die Entscheidung `no_champion_quality`. Auch ein Grand Final darf damit enden, dass keiner der beiden Finalisten die notwendige Qualität für die VN-Freischaltung erreicht. In diesem Fall folgt ein Repair- oder Refinement-Zyklus.

Die Bewertungsachse ist an den Asset-Slot gebunden. Für ein VN Sprite kann Lesbarkeit und Character Consistency wichtiger sein als dramatische Komposition; für ein Key Visual besitzen Komposition und emotionaler Ausdruck höheres Gewicht.

Unterschiedliche Bewertungsachsen werden nicht zu einer unklaren Gesamtfrage vermischt. Harte Gates werden vor ästhetischen Paarvergleichen geprüft.

### 24.9 Champion, Runner-up und qualifizierter Pool

Eine abgeschlossene Asset Quest speichert nicht nur ein Siegerbild:

- `champion`: primäres VN Asset,
- `runner_up`: freigegebene Alternative und Recovery-Fallback,
- `qualified_pool`: weitere brauchbare Varianten für LoRA, Album oder spätere Vergleiche,
- `rejected_pool`: nicht geeignete, aber diagnostisch relevante Evidenz,
- `quarantine_pool`: Bilder mit klaren Löschgründen.

Der Champion steht für die beste verfügbare Variante. Er beweist allein noch keine Prompt- oder Combo-Stabilität. Stability Trials bleiben für wiederverwendbare Outfits, Posen, Expressions und Character Recipes separat erforderlich.

#### Kein separater Live-Bench-Entscheid

Ein brauchbares Bild wird als Keep bewertet und ist damit ohne erneute
Abstimmung challengerberechtigt. Ein klarer Zieltreffer wird Favorite. Das
System darf diese Bewertungen nicht durch eine zweite Einordnung als „nur nett“
aus dem Turnier entfernen. Dataset Draft und Clone Hunt dürfen weiterhin
Dataset-Nutzen und Redundanz prüfen, verändern aber nicht rückwirkend die
ursprüngliche Reviewaction. Delete or Live erhält ausschließlich Bilder, die
durch eine festgelegte Referral-Regel dorthin gelangt sind.

### 24.10 Questtiefe nach Asset-Vertrag

Die frühere Staffelung mit vier, acht oder sechzehn Kandidaten entfällt. Stattdessen entscheidet der Scene Contract zuerst, ob ein eigener neuer Visual Champion überhaupt benötigt wird:

#### Wiederverwendbares oder nicht blockierendes Asset

Ein bereits freigegebenes Portrait, Sprite, Outfit, Place oder eine Standardexpression darf wiederverwendet werden, wenn Canon-, Style-, Framing- und Scene-Kompatibilität maschinell bestätigt sind. Ein rein optionales Album- oder Laborbild kann ohne Story-Turnier entstehen, blockiert dann aber keine Progression und darf nicht still als Story Champion gebunden werden.

#### Turnierpflichtiges Asset Requirement

Sobald für eine bevorstehende Situation ein neuer Story Champion benötigt wird, gilt unabhängig von der Assetklasse:

- wiederholte spielbare Vierervergleiche,
- genau sechzehn technisch zulässige und vom Spieler als echte Kandidaten bestätigte Bilder,
- ein vollständiges Sechzehner-K.-o.-Turnier,
- ein Champion und ein Runner-up,
- sowie eine abschließende Codevalidierung gegen den konkreten Scene Contract.

Focus Events, Key Visuals oder besonders riskante Outfits unterscheiden sich deshalb nicht durch ein kleineres oder größeres Kandidatenfeld, sondern durch zusätzliche Identity-, Stability-, Alpha-, Composition- oder LoRA-Requirements nach dem Turnier.

### 24.11 Entry Manifest und Outcome Manifest

Ein noch unbekanntes VN-Choice-Outcome kann nicht sinnvoll vorab als drei vollständige CG-Varianten generiert werden. Große Events besitzen deshalb zwei visuelle Manifeste.

#### Entry Visual Manifest

Wird vor der VN-Szene abgeschlossen und enthält:

- Background,
- Event-Outfit,
- benötigte Sprites,
- Basisposes,
- und die vor dem Choice bekannten Expressions.

#### Outcome Visual Manifest

Entsteht erst nach dem deterministisch ausgewerteten Choice-Outcome und kann enthalten:

- Outcome CG,
- neue besondere Expression,
- veränderte Pose,
- Chronicle Memory Image,
- oder ein visuelles Relationship Milestone.

Das Entry Manifest blockiert den Beginn der zugehörigen VN-Szene. Das Outcome Manifest blockiert bei storykritischen Bildern den Abschluss des Events beziehungsweise die nächste größere Progressionsstufe.

Dadurch müssen keine drei teuren Bildzweige vorsorglich generiert werden, obwohl nur einer davon tatsächlich Canon wird.

### 24.12 Visual-Ready-Gate für VN-Progression

Ein Event ist erst `visual_ready`, wenn jeder blockierende Asset-Slot:

- mindestens einen vorgeschriebenen Bild-Game-Loop durchlaufen hat,
- über so viele vollständig gespielte Vierer-Qualifier verfügt, dass sechzehn bestätigte Kandidaten vorliegen,
- keine offenen harten Fehler besitzt,
- einen in einem echten Grand Final bestätigten Champion enthält,
- und als versioniertes Asset an den Story Contract gebunden wurde.

`visual_ready` erfüllt damit ausschließlich das `SceneAssetGate`. Der Beginn der VN-Szene benötigt zusätzlich die Calendar-, Focus-Character-Play- und Ensemble-Development-Freigaben des später definierten `SceneUnlockContract`.

Beispiel:

```text
Sommerfestival · 5 blockierende Slots

Festival Background       → Champion bestätigt
Fokusfigur Yukata         → Champion bestätigt
Festival Sprite Neutral   → Champion bestätigt
Festival Sprite Guarded   → Repair erforderlich
Return Path Background    → Champion bestätigt

Visual Readiness: 4/5
VN Event bleibt in Vorbereitung
```

Der Spieler sieht daraus keine technische Assetliste, sondern eine verständliche Questvorbereitung für das bevorstehende Ereignis.

### 24.13 Verbindliche Verbindung der bestehenden Bildmodi

Für Visual Asset Quests werden die bereits im MVP definierten Modi wiederverwendet:

```text
Seed Run mit vier Bildern
→ Error Hunt / Weakest Link / Delete or Live
→ qualifizierter Kandidatenpool
→ Arena als Paarvergleich
→ festes 16er-K.-o.-Bracket
→ bei bestehendem Amtsinhaber direktes Title Match
→ bei Fehlern Repair Run
→ bei wiederverwendbaren Combos Stability Trial
→ Champion und Runner-up an Story binden
```

Damit entsteht kein separater Chronicle-Bewertungsmodus. Die VN-Progression gibt den bestehenden Bild-Games ein konkretes erzählerisches Ziel.

### 24.14 Festgelegte Richtung

- Ein Kalendermonat schließt nicht automatisch eine Character Route ab.
- Vollständige Character Routes verteilen sich über wiederkehrende Fokus-Events des gesamten Schuljahres.
- Drei authored VN-Choices beeinflussen Personality und Relationship über begrenzte, gewichtete Achsenimpulse. Sie ersetzen weder Base-Herkunft noch Character Brand, können bei Grenznähe aber genau einen direkten Current-Type-Wechsel auslösen.
- Jede Choice bleibt als wirksames State Event erhalten, auch wenn das sichtbare Outcome gleich bleibt.
- Jeder blockierende VN-Asset-Slot verlangt eine mehrstufige Bildquest.
- Ein erster Vierer-Batch dient nur als erste Qualifikationsrunde.
- Wiederholte Vierer-Batches laufen, bis sechzehn bestätigte Kandidaten für das blockierende VN Asset vorliegen; vier Batches sind nur das theoretische Minimum.
- Nach jedem Batch sind Favorite und Keep automatisch challengerberechtigt;
  Reject und Skip füllen den Pool nicht.
- Pro Batch gelangen null bis vier kompatible Keeps oder Favorites in den Kandidatenpool.
- Ein Batch darf ohne Keep oder Favorite enden; seine vier Bilder bleiben als
  Evidenz erhalten und der füllstandsbasierte Loop läuft weiter.
- Bei unzureichender Trefferquote folgen Recovery und weitere Vierer-Batches, bis der Pool vollständig ist.
- Unterschiedliche Prompt- und Recipe-Revisionen bleiben getrennt versioniert; Kandidaten dürfen nur bei weiterhin passendem Compatibility Hash gemeinsam antreten.
- Ein K.-o.-Finale darf mit `no_champion_quality` enden; die Story erzwingt keinen mittelmäßigen Gewinner.
- Ein Champion muss mindestens einen echten Vergleich gegen einen anderen qualifizierten Kandidaten gewinnen.
- Storykritische Assets verwenden mehrere Batches, einen festen 16er-Cup und
  bei bestehendem Amtsinhaber ein separates Title Match.
- Champion, Runner-up und weitere qualifizierte Bilder bleiben getrennt erhalten.
- Die VN-Szene startet erst nach abgeschlossenem Entry Visual Manifest.
- Choice-abhängige Outcome-Bilder werden erst nach der Szene erzeugt und vor der nächsten relevanten Progressionsstufe abgeschlossen.

## 25. Globale Places, Outfit-Blueprints, freigestellte Figuren und Auflösungen

Nicht jede Visual Asset Quest gehört exklusiv zu der Figur, durch deren Story sie ausgelöst wurde. Story-Auslöser, Asset-Besitzer und spätere Nutzung werden deshalb getrennt gespeichert.

### 25.1 Asset-Ebenen

```text
PlaceDefinition
└─ PlaceVariant

OutfitBlueprint
└─ CharacterOutfitBinding
   └─ CharacterSpriteFamily

StoryCG

ComposedVNShot
├─ PlaceVariant
├─ CharacterSprite(s)
└─ UI / Licht / Effekt-Overlay
```

#### PlaceDefinition und PlaceVariant

Ein `PlaceDefinition` beschreibt einen charakterunabhängigen Ort, beispielsweise:

- Klassenraum,
- Schuldach,
- Bahnhof,
- Einkaufsstraße,
- Festivalgelände,
- Park,
- oder Strand.

Ein `PlaceVariant` beschreibt eine konkret benötigte visuelle Fassung dieses Ortes:

- Kameraposition und Bildausschnitt,
- Tageszeit,
- Jahreszeit,
- Wetter,
- Beleuchtung,
- Event-Dekoration,
- Storyzustand,
- und Aspect Family.

Ein im Fokus einer Figur freigeschalteter Ort wird nicht Eigentum dieser Figur. Beispiel: Die Sommerfestival-Route von Character 04 kann `festival_main_street · night` auslösen; der bestätigte Hintergrund steht danach allen sechzehn Fokusfiguren zur Verfügung.

Fordern mehrere zukünftige Szenen dieselbe Place-Variante an, wird daraus eine gemeinsame Visual Asset Quest statt mehrerer doppelter Quests.

#### OutfitBlueprint und CharacterOutfitBinding

Ein `OutfitBlueprint` ist ein charakterübergreifendes Designkonzept, beispielsweise:

- Schuluniform,
- Sommeruniform,
- Sportkleidung,
- Yukata,
- Wintermantel,
- oder Festival-Helfer-Outfit.

Der Blueprint definiert Kleidungsgrammatik, Materialidee, erlaubte Farbwelt, notwendige Teile und verbotene Abweichungen. Das fertige Bild wird jedoch nicht charakterübergreifend geteilt.

Für jede Figur entsteht ein eigenes `CharacterOutfitBinding`. Es verbindet den gemeinsamen Blueprint mit:

- Character Canon und CharacterBrandSeed,
- Körperform und Silhouette,
- Gender und Präsentation,
- persönlicher Farbpalette,
- charaktertypischen Accessoires,
- User Locks,
- und bereits bestätigten Identitätsmerkmalen.

Damit kann das gleiche Uniform- oder Yukata-Konzept für alle Figuren gelten, während Prompt, Passform, Silhouette und Bildauswahl pro Figur unterschiedlich bleiben.

Der Prompt Compiler baut eine Outfit-Sprite-Anforderung entsprechend aus festen Komponenten:

```text
PromptStyleCore
+ CharacterCanon
+ OutfitBlueprint
+ CharacterOutfitBinding
+ Pose / Expression
+ SpriteTransparencyContract
+ Negative Constraints
```

Globale Bewertungsergebnisse können Fehler des Outfit-Blueprints sichtbar machen. Der Champion bleibt trotzdem immer figurspezifisch.

#### CharacterSpriteFamily

Eine `CharacterSpriteFamily` enthält die freigestellten Darstellungen einer Figur für ein bestimmtes Outfit und einen definierten Storyabschnitt:

- Basispose,
- benötigte Posen,
- Expressions,
- Blickrichtung,
- Alpha-Maske,
- normalisierte Skalierung,
- und einheitlichen Bottom-Center-Anchor.

Diese Sprites werden zur Laufzeit vor einen Place-Hintergrund gesetzt. Sie dürfen keine fest eingebaute Landschaft, keine Hintergrundreste und keinen gemalten Rahmen enthalten.

#### StoryCG und ComposedVNShot

Ein `StoryCG` ist ein flaches, szenenspezifisches Gesamtbild. Es darf nicht nachträglich als sauberer Background oder universeller Sprite behandelt werden.

Ein `ComposedVNShot` entsteht dagegen zur Laufzeit aus einem wiederverwendbaren Place, einem oder mehreren freigestellten Sprites und optionalen Licht- oder Effekt-Layern. Diese Trennung ist der Standard für Dialogszenen.

### 25.2 Background Game als globale Quest

Auch eine turnierpflichtige Background Quest verwendet wiederholte Vierervergleiche, bis 16 bestätigte Kandidaten vorliegen, und anschließend das vollständige K.-o.-System. Die Bewertungskriterien unterscheiden sich jedoch von Character Images.

Ein guter VN-Hintergrund benötigt:

- eine klare freie Bühne für ein bis mehrere Character Sprites,
- verständliche Vorder-, Mittel- und Hintergrundstaffelung,
- korrekte Perspektive und stabile Architektur,
- den verbindlichen Anime-Artstyle,
- geringe Ablenkung im Dialogfokus,
- passende Beleuchtung,
- und Wiederverwendbarkeit mit unterschiedlichen Figuren.

Standardmäßig werden Places ohne integrierte Hauptfiguren erzeugt. Folgende Probleme sind explizite Fehlergründe:

- `unexpected_character_in_background`,
- `unusable_character_stage`,
- `wrong_perspective`,
- `broken_architecture`,
- `wrong_artstyle`,
- `text_or_watermark`,
- `distracting_center_object`,
- `unsafe_crop`,
- und `background_not_reusable`.

Kleine atmosphärische Statisten sind nur zulässig, wenn der jeweilige Place Contract sie ausdrücklich fordert. Sie dürfen nicht wie Fokusfiguren wirken.

### 25.3 Sprite-Erzeugung und Freistellung

Freistellung ist kein nachträglicher Reparaturtrick für beliebige Szenenbilder, sondern Teil einer eigenen Sprite-Pipeline.

Der autoritative Kurzvertrag steht in
[`../sources/visual-assets-quests-and-gates.md`](../sources/visual-assets-quests-and-gates.md).
Ein Visual Requirement kompiliert dafür einen versionierten
`SpriteProductionJob`; ein einzelner ComfyUI-Renderjob ist noch kein fertiges
Spiel-Asset.

Der bevorzugte Ablauf lautet:

```text
bestätigtes Character- und Outfit-Seed
→ zusammenhängende Pose-/Expression-Familie erzeugen
→ unveränderte Quellbilder mit kontrollierter Isolationsfläche speichern
→ versionierte Segmentierung und Vordergrundmaske
→ versioniertes Matting und weicher Alphakanal
→ Scale-, Bounds- und Anchor-Normalisierung
→ technische Alpha-QA auf mehreren Kontrollhintergründen
→ Bild-Game und Champion-Auswahl
→ versioniertes Sprite Manifest
```

Die Isolationsfläche ist einfarbig, strukturlos und schattenlos. Weiß ist die
bevorzugte Ausgangsvariante, solange sie ausreichend Kontrast zu Haaren,
Kleidung, Highlights und halbtransparenten Details besitzt; andernfalls wird
eine kontrastierende Matte-Farbe als Teil des Recipe-Snapshots gewählt. Ein
weißer Bildhintergrund ist noch keine Transparenz und ersetzt keinen geprüften
Alphakanal.

Image Recognition beziehungsweise Vision Analysis kann Subjektzahl,
Figurenpräsenz, Vollständigkeit, Identity, Outfit und Assetrolle prüfen und den
Recovery-Pfad routen. Die pixelgenaue Freistellung bleibt Aufgabe von
Segmentierung und Matting. Ein Embedding- oder Full-Frame-Score darf weder eine
Maske erfinden noch allein das Alpha- oder Readiness-Gate freigeben.

Generation, Extraction, Matting, Normalisierung und QA besitzen getrennte
Attempts und Provenienz. Ist das Quellbild fachlich gültig, werden reine Masken-,
Alpha-, Scale- oder Anchor-Fehler ohne neue Figurengenerierung repariert. Das
Spiel bewahrt Quellbild, Maske, Alpha-Master, normalisiertes Sprite und
Kontrollkompositionen als getrennte, miteinander verknüpfte Artefakte auf.

Zusammengehörige Posen und Expressions sollen möglichst als Familie aus einem bestätigten Seed entstehen. Unabhängige Einzelgenerierungen erhöhen Identitäts-, Outfit- und Proportionsdrift.

Zusätzliche Sprite-Fehlergründe sind:

- Alpha-Halo oder Farbsäume,
- fehlende Haarspitzen,
- abgeschnittene Finger oder Kleidungsteile,
- transparente Löcher in Kleidung oder Körper,
- verbliebene Hintergrundinseln,
- ungewollter Bodenschatten,
- inkonsistente Skalierung,
- falscher Anchor,
- und zu enger Zuschnitt.

Die Eignung als VN-Sprite und die Eignung als LoRA-Trainingsbild sind zwei getrennte Bewertungen. Freigestellte Sprites können Trainingsmaterial ergänzen, sollen den Datensatz aber nicht dominieren.

Für Place-Produktion gilt der Gegenvertrag: Figuren und standardmäßig auch
Personen sind verboten, Places benötigen eine Character-Safe-Area und keinen
Alphakanal. Negative Prompts sind nur Generierungshilfe; ein versionierter
Vision-Befund prüft Personen, Gesichter und dominante figurähnliche Silhouetten.

### 25.4 Verbindliche Bildbühne und Zielauflösungen

Die VN-Bildbühne besitzt eine feste `16:9`-Kompositionslogik. Die logische Referenzauflösung ist `1920 × 1080`.

Unterstützte Ausgabeklassen sind:

| Klasse | Pixelauflösung | Verwendung |
|---|---:|---|
| 720p | 1280 × 720 | kleine Browserfenster und sparsame Geräte |
| 1080p | 1920 × 1080 | Referenz und Standardziel |
| 4K UHD | 3840 × 2160 | große Displays und hochauflösende Ausgabe |

`4K` meint in diesem Projekt die browserübliche UHD-Auflösung `3840 × 2160`, nicht DCI 4K.

Diese drei Klassen sind keine drei unabhängigen künstlerischen Assets. Der Spieler bestimmt im Bild-Game genau einen Champion in der kanonischen 16:9-Komposition. Daraus entstehen kontrollierte Auflösungsderivate. Es gibt daher keine neue 16-Bilder-Quest nur für 720p, 1080p oder 4K.

Für jedes visuelle Master-Asset werden mindestens folgende Metadaten gespeichert:

```text
aspect_family: vn_16_9
master_width
master_height
safe_area_normalized
fit_policy
anchor_normalized
available_derivatives: [720p, 1080p, 4k_uhd]
```

### 25.5 Responsive Browser-Verhalten

Das Browserfenster selbst muss nicht exakt 16:9 sein. Die visuelle Spielbühne bleibt jedoch 16:9 und verwendet eine explizite Darstellungsregel:

- VN-Backgrounds können innerhalb ihrer Safe Area mit `cover` skaliert werden.
- Story CGs verwenden standardmäßig `contain`, damit keine erzählerisch relevanten Bildteile verloren gehen.
- Character Sprites werden relativ zur Bühne skaliert und über normalisierte Anchors positioniert.
- Dialogbox, Choices und Navigation liegen als responsive UI-Ebene über der Bildbühne.
- Bei extremen Fensterformaten wird Letterboxing beziehungsweise Pillarboxing akzeptiert.

Kritische Figuren, Gesichter, Interaktionsobjekte und Storyhinweise müssen innerhalb einer im Asset gespeicherten Safe Area liegen. Der untere Dialogbereich wird bereits bei der Bildkomposition berücksichtigt.

### 25.6 Auflösungsabhängiges Asset Loading

Der Client lädt nicht pauschal alle 4K-Dateien. Ein Asset Resolver wählt anhand von:

- Viewport-Größe,
- Device Pixel Ratio,
- Leistungsprofil,
- Speicherbudget,
- und verfügbaren Derivaten

die kleinste ausreichend scharfe Variante. Dadurch bleibt 720p performant, während ein 4K-Display hochwertige Assets erhalten kann.

Sprites besitzen ebenfalls ein hochauflösendes transparentes Master, werden aber nicht als drei unabhängige Character Designs erzeugt. Anchor, Bounding Box und Scale werden normalisiert gespeichert und beim Rendern auf die aktuelle Bühne übertragen.

### 25.7 QA pro Auflösungsklasse

Der künstlerische Champion wird nur einmal gewählt. Seine technischen Derivate erhalten danach automatische und stichprobenartige QA für:

- Schärfe und Upscale-Artefakte,
- Alpha-Kanten,
- Safe-Area-Verletzungen,
- unbeabsichtigten Zuschnitt,
- korrekte Sprite-Positionierung,
- Lesbarkeit von Dialog und Choices,
- Ladezeit und Texturspeicher,
- sowie identische Farbwahrnehmung zwischen den Varianten.

Scheitert nur ein Auflösungsderivat, wird dieses Derivat repariert oder neu erzeugt. Die bereits bestätigte Bildauswahl wird dadurch nicht automatisch verworfen.

### 25.8 Festgelegte Richtung

- Places und Place-Varianten sind globale, charakterübergreifend nutzbare Assets.
- Eine Character Route darf eine globale Place Quest auslösen, besitzt deren Ergebnis aber nicht exklusiv.
- Doppelte Place-Anforderungen werden zu einer gemeinsamen Quest zusammengeführt.
- Outfit-Ideen werden als gemeinsame Blueprints gespeichert.
- Das sichtbare Outfit und sein Champion werden für jede Figur separat erzeugt und bewertet.
- Dialogszenen verwenden standardmäßig getrennte Backgrounds und freigestellte Character Sprites.
- Story CGs bleiben szenenspezifische, flache Gesamtbilder.
- Freistellung ist Bestandteil einer kontrollierten Sprite-Pipeline mit eigener Alpha-, Scale- und Anchor-QA.
- Die verbindliche VN-Bühne ist 16:9 mit 1920 × 1080 als logischer Referenz.
- Unterstützte Zielklassen sind 720p, 1080p und 4K UHD.
- Ein Champion wird nicht pro Auflösung neu ausgewählt; 720p, 1080p und 4K sind technische Derivate desselben Assets.
- Der Client lädt immer die kleinste für Viewport und Device Pixel Ratio geeignete Variante.

## 26. Recovery- und Embedding-Architektur

Dieser Abschnitt konkretisiert die zuvor beschriebene Rating-Recovery sowie Text- und Image-RAG. Embeddings sind ein rekonstruierbarer Suchindex. Sie sind weder Story State noch Character Canon noch alleinige Entscheidungsinstanz.

### 26.1 Drei getrennte Recovery-Domänen

Der allgemeine Begriff `Recovery` wird technisch in drei Domänen geteilt:

- **`OperationalRecovery`:** abgebrochene Jobs, abgelaufene Leases, Neustart, Queue- und Dateizustände,
- **`VisualRecovery`:** Wrong Artstyle, Bad Hands, Weird Background, Character Drift, Alpha-Fehler und andere Bildprobleme,
- **`MemoryCorrection`:** falsche, widersprüchliche oder veraltete Character-Erinnerungen.

Diese Domänen besitzen getrennte Statuswerte, Events und Erfolgsmetriken. Ein erfolgreich wiederaufgenommener Renderjob ist noch keine erfolgreiche Bild-Recovery; eine korrigierte Erinnerung verändert nicht automatisch ein bereits gebundenes Bild.

### 26.2 Source of Truth und rekonstruierbarer Retrieval-Index

Die Source of Truth bleibt in strukturierten und versionierten Datensätzen:

- Character Canon,
- Story- und Relationship-State,
- freigegebene Memories,
- Generation Recipes,
- Userentscheidungen,
- Ratings und Fehlergründe,
- Asset Bindings,
- sowie ausdrücklich freigegebene persönliche Playground-Items.

Embeddings werden aus diesen Quellen abgeleitet und dürfen jederzeit neu aufgebaut werden. Der erste Implementierungspfad verwendet dafür eine separate `retrieval.sqlite3`. Ein Verlust oder Rebuild dieser Datenbank darf keine Story-, Review- oder Canon-Daten zerstören.

### 26.3 Keine Runtime-Abhängigkeit von der Authoring-Datenbank

Die interne Playground-, Combo-Prompt- und Prompt-Rating-Datenbank wird nicht mit dem Spiel ausgeliefert. Die Runtime darf deshalb weder direkt noch über einen vollständigen vorab erzeugten Vektorindex von diesen Datenbanken abhängen.

Ausgeliefert werden nur ausdrücklich freigegebene und versionierte Laufzeit-Artefakte, beispielsweise:

- Schemas und Validierungsregeln,
- feste Prompt- und Recovery-Policies,
- der eine verbindliche Prompt Style Core,
- freigegebene Style-Prototypen,
- aggregierte nicht reversible Priors,
- sowie Runtime-Content, der tatsächlich Teil des Spiels sein soll.

Zur Laufzeit werden User-Content, bestätigte Memories, tatsächlich erzeugte Bilder, gespielte Recipes und Recovery Cases eingebettet. Theoretische kartesische Combo-Räume werden nicht vollständig eingebettet. Komponenten und tatsächlich gespielte Kombinationen sind die sinnvollen Retrieval-Einheiten.

### 26.4 Getrennte Embedding-Räume

Folgende Räume bleiben logisch und technisch getrennt:

#### Text

- `memory_text`,
- `component_text`,
- `visual_spec_text`,
- `recipe_text`,
- und `recovery_case_text`.

#### Bild

- `full_frame_semantic`,
- `character_crop`,
- `face_crop`,
- `outfit_crop`,
- `background_crop`,
- und `style_view`.

Nicht jedes Asset benötigt jeden Bildvektor. Ein Place benötigt beispielsweise kein Face Embedding; ein freigestellter Character Sprite benötigt normalerweise kein Background Embedding.

Ein einzelner Full-Frame-Vektor darf nicht gleichzeitig als verlässliche Messung für Character Identity, Artstyle, Outfit, Hände, Hintergrund und Komposition behandelt werden.

### 26.5 Embedding-Versionierung

Jeder gespeicherte Vektor besitzt mindestens:

```text
embedding_id
owner_type
owner_id
space
model_id
model_revision
dimension
preprocessing_revision
normalized
source_hash
created_at
```

Kosinuswerte werden nur innerhalb desselben Embedding-Modells, derselben Revision, desselben Preprocessings und desselben Vektorraums verglichen. Ein Modellwechsel überschreibt bestehende Vektoren nicht still. Eine neue Indexrevision wird parallel aufgebaut und nach erfolgreicher Evaluation aktiviert.

### 26.6 Kosinusähnlichkeit

Alle Retrieval-Vektoren werden L2-normalisiert gespeichert. Damit kann Kosinusähnlichkeit effizient als Skalarprodukt berechnet werden:

```text
cosine_similarity(a, b) = dot_product(a, b)
```

Kosinusähnlichkeit dient ausschließlich zur Kandidatensuche und zum Ranking innerhalb eines kompatiblen Vektorraums. Sie darf keine harten Regeln überschreiben.

Verbindliche Reihenfolge:

```text
Source of Truth und Anfrage
→ harte fachliche Filter
→ kompatibler Embedding-Raum
→ Cosine Top-K
→ fachliches Reranking
→ begrenztes Kontextpaket
→ Director- oder Recovery-Entscheidung
```

Ein universeller Schwellenwert wie `0.80 = relevant` ist nicht zulässig. Schwellenwerte werden pro Modell, Vektorraum und Aufgabe anhand eines projektbezogenen Eval-Korpus kalibriert.

### 26.7 Harte Filter vor Text-Retrieval

Vor der semantischen Suche werden unter anderem gefiltert:

- User- und Save-Scope,
- Character und Character-Version,
- Memory-Typ,
- Story-Zeitpunkt und Gültigkeitsfenster,
- Freigabestatus,
- Relationship- und Content-Scope,
- Widerspruchsstatus,
- und Sichtbarkeit für den aktuellen Character Speaker.

Locked Canon und Current State werden direkt geladen und nicht durch Vektorsuche ersetzt. Semantisches Retrieval ist hauptsächlich für den wachsenden episodischen Memory-Bestand zuständig.

Eine Memory-Repräsentation für Embeddings wird aus strukturierten Feldern deterministisch normalisiert, beispielsweise:

```text
Character + Event + User Action + Character Reaction
+ Consequence + Emotion + Story Time + Relationship Scope
```

Sie besteht nicht nur aus einer frei vom LLM formulierten Zusammenfassung.

### 26.8 Bild-Retrieval und Artstyle-Drift

Da das Projekt nur einen Prompt Style verwendet, dient Style Retrieval nicht der freien Stilwahl. Es dient vor allem:

- der Erkennung von Wrong Artstyle,
- dem Ranking geeigneter Style-Referenzen,
- der Prüfung von Mixed Artstyle,
- und dem Vergleich von Recovery-Ergebnissen mit dem Style Canon.

Dafür besitzt jede Style-Version einen kleinen freigegebenen `StyleReferencePack` mit:

- mehreren positiven Style-Prototypen,
- asset-rollenspezifischen Referenzen,
- sowie mehreren repräsentativen Wrong-Style-Prototypen.

Ein erster Style-Drift-Wert kann als relative Margin berechnet werden:

```text
Style Margin
= robuste Ähnlichkeit zu positiven Prototypen
- höchste Ähnlichkeit zu einem Wrong-Style-Prototyp
```

Die positive Seite darf beispielsweise als Median oder Top-K-Mittel mehrerer kompatibler Referenzen berechnet werden. Ein einzelnes Durchschnittsbild ist nicht der gesamte Style Canon.

Style, Character Identity, Outfit und Scene erhalten getrennte Scores und Gates. Ein hoher Style Score kompensiert keine falsche Figur und keine falsche Character-Version.

### 26.9 Kombinieren mehrerer Retrieval-Signale

Text- und Bild-Kosinuswerte stammen aus unterschiedlichen Score-Verteilungen und werden nicht roh addiert. Der erste Implementierungspfad verwendet rankbasierte Fusion, beispielsweise Reciprocal Rank Fusion:

```text
Text-Rang
+ passender Bild-Rang
+ historischer Recovery-Erfolgsrang
+ Effizienzrang
→ kombinierte Kandidatenliste
```

Harte Gates werden immer vorher angewendet. Später kann aus den gesammelten Spielerbewertungen ein kalibrierter Reranker entstehen. Bis dahin bleiben Gewichte und Grenzwerte konfigurierbar, versioniert und durch Retrieval-Evals abgesichert.

### 26.10 Verbindlicher RecoveryCase-Vertrag

Ein `RecoveryCase` speichert mindestens:

```text
Ausgangs-Recipe und Recipe Revision
Ausgangsbild und kompatible Embedding-Referenzen
Asset Role und Visual Specification
primären und sekundäre Fehlercodes
zu bewahrende Achsen
ausgewählte Recovery Policy
konkreten Recipe- und Prompt-Delta
Ergebnisbild und neue Recipe Revision
behobene und neu entstandene Fehler
Qualitäts- und Stability-Veränderung
Generierungs- und Gesamtzeit
Userentscheidung
Recovery Outcome
```

Mögliche Outcomes sind mindestens:

- `successful`,
- `target_fixed_with_regression`,
- `target_not_fixed`,
- `technically_failed`,
- `inconclusive`,
- und `awaiting_review`.

Eine Visual Recovery gilt nur als `successful`, wenn:

1. der Zielfehler behoben wurde,
2. keine geschützte Achse schlechter wurde,
3. das Ergebnis mindestens `usable` ist,
4. und die Verbesserung durch das Spielerreview bestätigt wurde.

Ein repariertes Gesicht mit neuem Character Drift ist deshalb kein erfolgreicher Recovery Case.

### 26.11 Retrieval eines Recovery-Pfads

```text
Fehler und Ausgangs-Recipe
→ harte Filter auf Error Code, Asset Role, Style-Version,
  Workflow-/Modellkompatibilität und gegebenenfalls Character-Version
→ ähnliche Visual Specifications per Text-Cosine
→ ähnliche Ausgangsbilder in passenden Bildräumen
→ erfolgreiche Recovery Cases ranken
→ wenige unterschiedliche Top-K-Fälle auswählen
→ Director bestimmt hardcodierte Recovery Policy
→ Prompt Generator formuliert nur den erlaubten Delta
```

Bevorzugt wiederverwendet wird der bewährte Recovery-Delta, nicht der komplette Prompt eines fremden Falls. Dadurch werden keine fremden Character-, Outfit- oder Storymerkmale eingeschleppt.

Bei einem Null-Contender-Zyklus werden zusätzlich ähnliche negative Zyklen und nachweislich verbesserte Folgezyklen abgerufen. Der neue Zyklus bleibt trotzdem eine eigene Recipe Revision mit 16 neuen Bildern.

### 26.12 Delete und Vektor-Lebenszyklus

Bei `Delete` verliert ein Bild sofort jede Berechtigung als positive Retrieval- oder Generierungsreferenz.

Während der wiederherstellbaren Quarantäne dürfen seine Bildvektoren ausschließlich im negativen Evidenzraum verbleiben. Bei endgültiger physischer Löschung werden Full-Frame-, Face-, Character-, Outfit- und Crop-Vektoren ebenfalls gelöscht.

Erhalten bleiben:

- Generation Recipe,
- Prompt- und Component-Snapshot,
- strukturierte Fehlercodes,
- Recovery Policy und Delta,
- nicht visuell rekonstruierbare aggregierte Statistik,
- sowie Generierungs- und Laufzeitdaten.

### 26.13 Speicher- und Indexstrategie

Für den ersten Chronicle-Slice mit Retrieval wird kein eigener Vector Server vorausgesetzt. Die bevorzugte Architektur ist:

- separate `retrieval.sqlite3`,
- normalisierte Float32-Vektoren,
- Metadaten und Modellversionen neben jedem Vektor,
- harte SQL-Vorfilterung,
- exakte Kosinusberechnung auf dem reduzierten Kandidatenpool,
- und wiederaufbaubare Indexjobs.

Ein nativer SQLite-Vektorindex wie `sqlite-vec`, ein HNSW-Index oder ein separater Vector Service wird erst eingeführt, wenn gemessene Korpusgröße und Abfragelatenz dies rechtfertigen. Chroma, Qdrant oder ein vergleichbarer Dienst ist keine Voraussetzung für den ersten lokalen Prototyp.

### 26.14 Evaluation und Abstention

Vor produktiver Aktivierung wird ein projektbezogener Retrieval-Testkorpus aufgebaut. Er enthält mindestens:

- relevante und irrelevante deutsche Memories,
- widersprüchliche und veraltete Character Facts,
- gleiche und unterschiedliche Figuren,
- korrekte und falsche Outfits,
- gleiche Szenen mit unterschiedlichem Artstyle,
- Wrong-Artstyle-Beispiele,
- erfolgreiche und erfolglose Recovery Pairs,
- sowie schwierige Near-Duplicates.

Getrennt gemessen werden unter anderem:

- Recall@K,
- Precision@K,
- korrekter Top-1-Fall,
- Canon- oder Scope-Verletzungen,
- false positive Style Matches,
- Recovery Success Rate,
- Regression Rate,
- und Retrieval-Latenz.

Ist kein Kandidat ausreichend sicher, enthält das System sich. Mögliche Folgen sind ein deterministischer Fallback, ein neues Bild-Game, eine erneute Userfrage oder ein vollständig neues Recipe. Ein schwacher Treffer wird nicht allein deshalb verwendet, weil er Rang eins besitzt.

### 26.15 Festgelegte Richtung

- Kosinusähnlichkeit ist der mathematische Kern der Kandidatensuche innerhalb eines kompatiblen Embedding-Raums.
- Embeddings sind ein rekonstruierbarer Index und keine Source of Truth.
- Locked Canon, Current State und harte fachliche Regeln werden nie durch Vektorsuche ersetzt.
- Text-, Bild-, Style-, Identity-, Outfit- und Background-Räume bleiben getrennt.
- Text- und Bildscores werden nicht roh miteinander addiert.
- Ein Bild kann je nach Asset Role mehrere Crop- und Full-Frame-Vektoren besitzen.
- Die nicht ausgelieferte Playground- und Combo-Datenbank ist keine Runtime-Abhängigkeit.
- Theoretische Combo-Räume werden nicht vollständig eingebettet.
- Recovery verwendet bevorzugt validierte Deltas und nicht komplette fremde Prompts.
- Ein Recovery-Fall ist nur erfolgreich, wenn der Zielfehler ohne Regression geschützter Achsen behoben wurde.
- Endgültig gelöschte Bilddateien hinterlassen keine visuellen Crop- oder Full-Frame-Vektoren.
- Der erste lokale Prototyp verwendet SQLite und exakte Suche nach harten Filtern.
- Schwellenwerte werden pro Aufgabe kalibriert; Retrieval darf sich bei zu geringer Sicherheit enthalten.

## 27. Verdichteter Jahreskalender, täglicher Character Loop und Relationship Levels

Dieser Abschnitt präzisiert den bisherigen Schuljahres- und Episodenrahmen. Die 24 Special-Episoden ersetzen den Alltag nicht. Sie liegen als authored Höhepunkte innerhalb eines verdichteten Kalenders aus 168 spielbaren Story-Tagen.

### 27.1 Verbindliche Kalendergröße

```text
12 In-Game-Monate
× 14 spielbare Story-Tage pro Monat
= 168 Story-Tage pro Durchlauf
```

Ein Story-Tag ist kein exaktes Abbild eines einzelnen realen Kalendertages. Er verdichtet ungefähr zwei reale Tage beziehungsweise mehrere irrelevante Routinetage zu einem spielbaren Fortschrittsschritt.

Alle 168 Story-Tage werden als serialisierbare Day Instances geführt. Eine Day Instance darf Routine per Erzählermontage zusammenfassen, enthält aber immer mindestens eine direkte Character-Interaktion.

### 27.2 24 Special-Episoden innerhalb von 168 Tagen

Pro Durchlauf existieren genau 24 authored Special Slots. Im Mittel besitzt jeder Monat:

- ein kleineres Special im mittleren Monatsabschnitt,
- und ein großes Special als Monats- oder Arc-Payoff.

Damit gilt als Richtwert:

```text
168 Story-Tage
- 24 Special-Episoden
= 144 Schul-, Wochenend-, Ferien-, Fokus-, Prüfungs-
  und Vorbereitungstage
```

Eine Special-Episode ist ein besonders stark authored Ereignis mit eigenem Event Contract, Visual Manifest und größerem Story-Payoff. Der Begriff bedeutet nicht, dass die übrigen Tage keine VN-Szenen oder relevante Story enthalten.

### 27.3 Monatlicher Standardrhythmus

Ein normaler Schulmonat verwendet ungefähr folgende Verteilung:

| Day Type | Anzahl | Funktion |
|---|---:|---|
| normale Schultage | 8 | Alltag, Unterricht, Pausen, Club, Character- und Build-Fortschritt |
| Wochenende oder freie Tage | 2 | frei wählbarer Fokus, Ausflug, Hobby, längere Interaktion |
| Fokus- oder Vorbereitungstage | 2 | Character Arc, Eventvorbereitung und Visual Gates |
| Special-Episoden | 2 | authored Höhepunkte und größere Outcomes |

Die Verteilung ist saisonal variabel. Ferienmonate ersetzen Schultage durch Ferien-, Club-, Camp- oder Ausflugstage. Prüfungsmonate können freie Slots durch Study-, Exam- oder Counseling-Tage ersetzen. Die Summe bleibt grundsätzlich bei 14 Story-Tagen.

Ein möglicher Rhythmus lautet:

```text
Tag 1–5    Alltag, Character-Aufbau und erste Vorbereitung
Tag 6      kleineres Special
Tag 7–12   Alltag, Branches und Bild-Quests
Tag 13     unmittelbare Eventvorbereitung und Visual Gate
Tag 14     großes Monatsspecial
```

### 27.4 Arbeitsstand der 24 Special Slots

| Monat | Special A | Special B |
|---|---|---|
| April | Transfer, Opening und erste Begegnung | Chronicle- und Club-Gründung |
| Mai | Golden-Week-Ausflug | erste Study-Group- und Midterm-Krise |
| Juni | Rainy-Day-Episode | Chronicle Field Assignment |
| Juli | Tanabata | Termabschluss, Pool oder Ferienauftakt |
| August | Beach, Camp oder Test of Courage | Sommerfestival und Feuerwerk |
| September | Rückkehr und neue Gruppendynamik | Sportfest |
| Oktober | Kulturfestival-Vorbereitung | Kulturfestival und Chronicle Midpoint |
| November | Schulfahrt Teil 1 | Ryokan-, Nacht- oder Enthüllungs-Event |
| Dezember | Winterprüfungen und erster Schnee | Christmas Event |
| Januar | Hatsumōde | Zukunftsberatung und Character Crisis |
| Februar | Valentine | Chronicle- oder Graduation-Crisis |
| März | White Day und Farewell | Graduation und Chronicle Reveal |

Die Tabelle ist der aktuelle verbindliche Arbeitsrahmen. Einzelne Special-Bezeichnungen und ihre genaue Character-Besetzung werden im späteren Story Authoring konkretisiert, ohne die Zahl von 24 Slots oder den Jahresverlauf still zu verändern.

### 27.5 Tägliche Character-Interaktion ist verpflichtend

Jeder Story-Tag besitzt mindestens einen `DailyCharacterBeat`. Dieser kann dargestellt werden als:

- kurze VN-Szene,
- Character Chat,
- VN-Szene mit anschließendem Chat,
- Chat mit anschließendem visuellen Reveal,
- oder längere Hybrid-Szene.

Auch ein normaler Schultag enthält damit grundsätzlich Character-Content. Ein Tag, der ausschließlich aus Menüs, Queue-Warten, Bildreview oder einer Erzählermontage besteht, ist nicht vollständig.

Der Mindest-Beat kann sehr kurz sein:

```text
Begrüßung auf dem Schulweg
→ eine kleine Reaktion oder Userantwort
→ sichtbare Character-Reaktion
→ optionaler Relationship- oder Memory-Impuls
```

Nicht jeder Daily Character Beat benötigt drei große VN-Choices. Drei authored Choices bleiben der Standard für storyrelevante Interaktionen. Kleine Standardszenen dürfen eine kurze Antwort, eine binäre Alltagsentscheidung oder einen begrenzten Chatturn verwenden.

### 27.6 Normaler Schultag mit VN, Chat und Build Game

Ein normaler Tag kann folgenden vollständigen Loop verwenden:

```text
DAY_OPEN
→ authored Morgen- und Kalender-Setup
→ Homeroom, Unterricht oder Montage
→ Pausen-/Lunch-VN-Szene
→ Nachmittagswahl oder Director-Zuweisung
→ Club-, Focus- oder Chronicle-Szene
→ Build-/Bild-Game für aktuelle oder kommende Visual Needs
→ Evening Chat oder kurzer Character-Abschluss
→ State-Auswertung
→ DAY_COMPLETE
```

Je nach Tag dürfen VN und Build-Game ihre Reihenfolge wechseln. Ein Bildreview kann beispielsweise eine neue Figurendarstellung freischalten, die unmittelbar danach in einer kurzen VN-Szene erscheint.

### 27.7 Build Games sind echte Progressionshandlungen

Build Games sind kein optionales Nebenspiel. Sie erzeugen und stabilisieren den visuellen Content, der für weitere VN-Szenen benötigt wird.

```text
Story kündigt zukünftigen Bedarf an
→ Visual Manifest wird erzeugt
→ Generation und Vierer-Batches
→ Bild-Games, Ratings und Fehlergründe
→ K.-o.-System, Recovery und Champion
→ Asset wird an Story Requirement gebunden
→ VN-Szene oder Event kann fortgesetzt werden
```

Der Fortschritt entsteht aus tatsächlich erzeugten, bewerteten und gebundenen Assets. Es gibt keine abstrakten Build-Punkte, die einen fehlenden Champion ersetzen.

Build Games können:

- ein Asset für die aktuelle Day Instance fertigstellen,
- Content für ein kommendes Special vorbereiten,
- globale Places oder Outfit-Blueprints freischalten,
- Character Sprites und Expressions erweitern,
- Recovery Debt abbauen,
- oder LoRA- und Dataset Coverage verbessern.

### 27.8 Visual Gates auf Tages- und Eventebene

Eine normale VN-Szene darf vorhandene Backgrounds, Outfits und Sprites wiederverwenden. Nicht jeder der 168 Tage fordert deshalb ein neues einzigartiges CG oder einen vollständig neuen Asset-Satz.

Benötigt eine Szene jedoch ein noch fehlendes blockierendes Asset, entsteht ein echtes Visual Gate:

```text
Daily Character Beat kann gegebenenfalls bereits stattfinden
→ Visual Need wird spielerisch erklärt
→ notwendige Build Games werden gespielt
→ Asset wird approved
→ blockierte VN-Szene wird fortgesetzt
```

Für größere Specials werden Build Milestones über mehrere vorherige Story-Tage verteilt:

1. Event ankündigen und Manifest erstellen,
2. Qualifier-Runden beginnen,
3. Contender und Recovery auswerten,
4. K.-o.-System spielen,
5. Champions an das Entry Manifest binden,
6. Visual-Ready-Gate vor dem Special bestätigen.

Das Special wird nicht übersprungen, wenn das Manifest unvollständig ist. Die Story verbleibt in einem nachvollziehbaren Vorbereitungsschritt, während Build- und Recovery-Games fortgesetzt werden.

### 27.9 Asynchrone Generierung ohne Character-Leerlauf

Bildgenerierung darf Zeit benötigen. Während ein nicht unmittelbar blockierender Job läuft, kann der Spieler:

- eine bereits visuell gedeckte Daily VN-Szene spielen,
- einen kurzen Character Chat führen,
- vorhandene Bilder bewerten,
- Chronicle Memories kuratieren,
- oder einen anderen vorbereiteten Build Task bearbeiten.

Der Calendar Director darf die Zeit mit Character-Content überbrücken, aber kein Visual-Ready-Gate umgehen. Generierungswartezeit und In-Game-Kalenderzeit sind getrennte Zustände.

### 27.10 Relationship State statt einfacher Affection-Leiste

Jede Player-Character-Beziehung besitzt einen strukturierten `RelationshipState`:

```text
bond_level
familiarity
trust
affection
romantic_tension
current_tension
route_mode
milestone_flags
interaction_history
event_cooldowns
last_meaningful_interaction_day
```

#### Langfristige Werte

- **`bond_level`:** sichtbare, langfristige Beziehungsstufe,
- **`familiarity`:** wie gut sich beide durch gemeinsame Zeit kennen,
- **`trust`:** Bereitschaft, sich verletzlich zu zeigen und Aussagen zu glauben,
- **`affection`:** positive emotionale Bindung,
- **`romantic_tension`:** romantische Signale, nur wenn fachlich und inhaltlich zulässig,
- **`route_mode`:** `undecided`, `friendship`, `romance` oder ein authored Sonderzustand.

#### Kurzfristige Werte

- **`current_tension`:** aktuelle Verstimmung, Unsicherheit oder ungelöster Konflikt,
- **`interaction_history`:** zuletzt verwendete Eventfamilien und Reaktionen,
- **`event_cooldowns`:** Schutz vor unpassender Wiederholung,
- **`last_meaningful_interaction_day`:** Scheduler-Signal gegen das Verschwinden einer Figur.

Ein hoher Bond Level bedeutet nicht automatisch geringe aktuelle Spannung. Eine enge Freundschaft kann sich nach einem Konflikt vorübergehend guarded oder strained anfühlen, ohne dass die gesamte langfristige Beziehung sofort gelöscht wird.

### 27.11 Verbindliche Bond Levels

| Level | Arbeitsname | Typisches Verhalten |
|---:|---|---|
| 0 | Unbekannt | keine persönliche Routine, formale oder zufällige Begegnung |
| 1 | Bekannt | Begrüßung, kurzer Smalltalk, einfache gemeinsame Aufgaben |
| 2 | Vertraut | freiwilliges Gespräch, wiederkehrender Lunch oder gemeinsamer Heimweg |
| 3 | Freundschaft | aktive Einladung, Hilfe, erste persönliche Informationen |
| 4 | Tiefes Vertrauen | Verletzlichkeit, Konfliktreparatur, private Erinnerungen |
| 5 | Enge Bindung | Friendship- oder Romance-Intent wird eindeutig und erhält eigene Varianten |
| 6 | Dauerhafte Bindung | Friendship- oder Romance-Ending und gemeinsamer Zukunftsbezug |

Die sichtbare Bezeichnung darf später an die finale UI-Sprache angepasst werden. Die Stufenlogik bleibt getrennt von kurzfristigen Punkten und Stimmungen.

### 27.12 Levelaufstieg benötigt Evidenz und Milestone

Ein Bond Level steigt nicht ausschließlich durch das Sammeln wiederholbarer Punkte.

```text
ausreichende Familiarity-, Trust- und Affection-Evidenz
+ erforderlicher Character-Arc-Stand
+ authored Milestone Event
+ keine blockierende ungelöste Krise
= Bond-Level-Up erlaubt
```

Der Director und nicht das Character-LLM entscheidet über das Level-up. Die Figur kann die veränderte Nähe in einem authored Milestone oder vom Speaker formulierten, eng begrenzten Reaktionssatz ausdrücken.

Normale Interaktionen können Evidenz und Beziehungston verändern. Die großen Stufengrenzen benötigen jedoch ein Event, damit Relationship Progress nicht durch endlos wiederholte Begrüßungen gefarmt wird.

### 27.13 Friendship und Romance sind keine zwei komplett getrennten Leisten

Bis zu einer engen Bindung teilen Friendship und Romance dieselben Grundlagen:

- Bekanntheit,
- Vertrauen,
- gemeinsame Erinnerungen,
- Konflikte und Reparatur,
- sowie gegenseitige Wertschätzung.

`route_mode` wird erst an authored Intent Gates eindeutig. Eine romantische Route benötigt zusätzlich passende Signale, gegenseitige Offenheit und erlaubte Route Flags. Eine Friendship Route bleibt ein vollwertiger Abschluss und ist kein gescheiterter Romance-Pfad.

Romance- und Friendship-Level besitzen deshalb denselben `bond_level`, aber unterschiedliche:

- Eventvarianten,
- Speech Intents,
- Gesten und Expressions,
- Visual Requirements,
- Memories,
- und Endings.

### 27.14 Wiederholbare Standard-Eventfamilien

Alltagsszenen dürfen strukturell wiederkehren. Wiederholung wird dann zu sichtbarer Beziehungsentwicklung statt zu identischem Content.

Mögliche Eventfamilien:

- `morning_greeting`,
- `walk_to_school`,
- `hallway_encounter`,
- `lunch_break`,
- `rooftop_lunch`,
- `library_study`,
- `club_cleanup`,
- `walk_home`,
- `train_or_bus_ride`,
- `evening_message`,
- `weekend_invitation`,
- und `check_in_after_conflict`.

Beispiel `walk_home`:

```text
Level 0: zufällig dieselbe Strecke, kaum Gespräch
Level 1: höflicher gemeinsamer Weg bis zur Kreuzung
Level 2: Figur wartet gelegentlich oder beginnt Smalltalk
Level 3: gemeinsamer Heimweg wird aktiv vorgeschlagen
Level 4: persönliches Thema oder ehrlicher Check-in
Level 5 Friendship: vertrautes Ritual und gegenseitige Unterstützung
Level 5 Romance: bewusste Nähe, Unsicherheit oder romantisches Signal
Level 6: gemeinsamer Zukunftsbezug und route-spezifische Variante
```

Die Eventfamilie bleibt erkennbar, aber Beat, Speech Intent, Expression, Choice und Outcome variieren mit:

- Bond Level,
- Route Mode,
- Personality Behavior Pack,
- Current Tension,
- Story- und Character-Arc-State,
- Tageszeit und Ort,
- anwesenden Figuren,
- sowie Wiederholung und Cooldown.

### 27.15 Scheduler für den täglichen Character Beat

Der Director bestimmt den Daily Character Beat deterministisch aus gewichteten fachlichen Signalen:

```text
verbindlicher Storybedarf
+ aktuelle oder gewählte Fokusfigur
+ Relationship- und Character-Arc-Readiness
+ authored Development-Readiness aller benötigten Supporting Characters
+ Figuren mit zu langer Abwesenheit
+ offene Personality-Evidenz
+ passender Day Type und Ort
+ verfügbare Visual Assets
- Wiederholung und Cooldown
- unpassende Konflikt- oder Routebedingungen
= zulässige Daily-Event-Auswahl
```

Kontrollierter Zufall darf nur zwischen mehreren bereits zulässigen Varianten entscheiden. Er darf keine Story Gates, Relationship Levels oder Visual Requirements umgehen.

Nicht fokussierte Figuren bleiben durch B-Story-Beats, Pausen, Unterricht, Clubs und Ensemble-Szenen sichtbar. Ein langfristiger Route-Fokus erhöht die Begegnungswahrscheinlichkeit deutlich, entfernt die anderen fünfzehn aktiven Figuren aber nicht aus dem Sozialkreis.

### 27.16 DayInstance-Vertrag

```json
{
  "day_id": "september_day_09",
  "month": "september",
  "ordinal": 9,
  "day_type": "school_focus",
  "special_slot_id": null,
  "calendar_summary_key": "sep.day09.sports_preparation",
  "daily_character_beat": {
    "event_family": "club_cleanup",
    "focus_character_id": "character_04",
    "support_character_ids": ["character_09"],
    "presentation": "vn_then_chat",
    "relationship_variant": "trusted_guarded",
    "required": true
  },
  "scene_unlock_contract": {
    "scene_unlock_contract_id": "unlock_club_cleanup_04",
    "scene_id": "scene_club_cleanup_04",
    "story_beat_id": "beat_sep_club_cleanup",
    "focus_character_id": "character_04",
    "supporting_character_ids": ["character_09"],
    "calendar_gate": {
      "required_day_id": "september_day_09",
      "status": "satisfied"
    },
    "scene_asset_gate": {
      "visual_manifest_id": "club_cleanup_entry_04",
      "status": "incomplete"
    },
    "focus_character_play_gate": {
      "required_rounds": 2,
      "completed_rounds": 1,
      "source_state_revision": 18
    },
    "ensemble_development_gate": {
      "participant_requirements": [
        {
          "character_id": "character_09",
          "required_narrative_milestone_ids": ["club_introduction"],
          "minimum_visual_development_tier": "identity_ready",
          "required_knowledge_ids": ["fact_club_cleanup_plan"]
        }
      ]
    },
    "relationship_gate_ids": [],
    "knowledge_gate_ids": []
  },
  "build_requirements": [
    {
      "visual_manifest_id": "club_cleanup_entry_04",
      "milestone": "manifest_complete",
      "blocking": true
    }
  ],
  "completion_requirements": [
    "daily_character_beat_completed",
    "scene_unlock_contract_satisfied",
    "required_build_milestones_completed",
    "state_events_committed"
  ]
}
```

Das Frontend rendert die Day Instance, besitzt aber weder Relationship- noch Progressionslogik. Der Director schreibt die resultierenden serialisierbaren State Events.

### 27.17 Tagesabschluss und Save State

Vor `DAY_COMPLETE` werden mindestens gespeichert:

- abgespielte Story- und Daily-Event-IDs,
- Userantworten und Choices,
- Character-, Personality- und Relationship-Deltas,
- neue oder korrigierte Memories,
- Build- und Visual-Manifest-Fortschritt,
- Ratings und Recovery-Ergebnisse,
- verwendete Standard-Eventvarianten und Cooldowns,
- sowie die nächsten bereits angekündigten Visual Needs.

Ein Reload rekonstruiert den Tag aus diesem Zustand. Renderer-, UI- oder laufende Animationsobjekte sind kein Save State.

### 27.18 Festgelegte Richtung

- Ein Durchlauf besitzt zwölf Monate mit jeweils vierzehn spielbaren Story-Tagen.
- Die 24 Special-Episoden liegen innerhalb dieser 168 Tage und ersetzen den Alltag nicht.
- Jeder Story-Tag enthält mindestens eine direkte Character-Interaktion als VN, Chat oder Hybrid.
- Normale Schultage dürfen und sollen VN-Szenen enthalten.
- Kleine Daily Beats benötigen nicht immer drei große Choices; storyrelevante VN-Szenen verwenden weiterhin drei authored Choices.
- Build Games sind verpflichtende Progressionshandlungen, weil sie die real verwendeten Story-Assets erzeugen und freigeben.
- Nicht jeder Tag benötigt neue Assets; vorhandene freigegebene Places, Outfits und Sprites werden wiederverwendet.
- Fehlende blockierende Assets erzeugen echte Visual Gates auf Tages- oder Eventebene.
- Asynchrone Generierung darf mit Character-Content überbrückt werden, aber kein Gate umgehen.
- Jede Player-Character-Beziehung besitzt einen langfristigen Bond Level und zusätzliche Trust-, Affection-, Tension- und Route-Zustände.
- Friendship und Romance teilen die Vertrauensbasis, erhalten ab authored Intent Gates unterschiedliche Varianten und gleichwertige Endings.
- Relationship-Level-Ups benötigen sowohl Evidenz als auch ein authored Milestone Event.
- Wiederholbare Standard-Events variieren nach Bond Level, Personality, Route, Current Tension und Story State.
- Wiederholung besitzt Cooldowns und erzeugt keinen unbegrenzten Relationship Grind.
- Der Director besitzt Kalender-, Daily-Event-, Relationship- und Gate-Autorität; LLMs formulieren nur innerhalb eines ausgewählten Contracts.

## 28. Diegetisches Prolog-Onboarding und kontinuierliche Präferenzermittlung

Das Spiel beginnt nicht mit einem technischen Character Editor und nicht mit einem freien LLM-Chat. Der Prolog ist bereits eine authored Story, in der Erzähler, Umgebung und eine als Silhouette dargestellte Mutter spielerisch strukturierte Informationen erheben.

Das Ziel ist nicht, alle späteren Figuren einzeln abzufragen. Das System ermittelt:

- visuelle Vorlieben,
- bevorzugte Farb- und Lichtwelten,
- Haar- und Silhouettentendenzen,
- Character- und Social-Style-Präferenzen,
- Setting- und Uniformrichtung,
- narrative Interessen,
- und geeignete erste Begegnungsfiguren.

Diese Signale bleiben Hypothesen. Sie bestimmen weder dauerhaft eine Route noch verhindern sie, dass der Spieler später andere Figuren fokussiert.

### 28.1 Belegter Ausgangszustand der Entwicklungsdaten

Die aktuelle Playground-Datenbank enthält vier echte Beispielcharaktere:

- Aiko,
- Kaori,
- Mizuki,
- und Hina.

Der zusätzliche Eintrag `Empty` ist ein technischer Background-Platzhalter und keine Figur. Die vier Beispielcharaktere sind bereits sehr konkrete weibliche Promptpakete. Sie sind Referenz- und Kalibrierungsmaterial, aber noch kein generatives Cast-System.

Vor der Intro- und Cast-Umsetzung bilden diese vier Figuren außerdem den
verbindlichen internen Startzustand für `M6_LEARNING_LOOP_PROVEN`. Verwendet
werden ihre Komponenten, gewichteten positiven/negativen Prompts, Outfits,
Szenen, vorhandenen Bilder und vollständigen Recipes. Nicht übernommen werden
ihre historischen Bewertungen: Der Proof startet mit
`evidence_policy=fresh_only`, und jedes vorhandene Bild benötigt eine neue
Two-Pass-Qualifikation, bevor es Keep, Favorite oder Challenger sein kann.
Fehlt einem Bild die vollständige Recipe-Provenienz, darf seine frische
Bewertung visuelle Evidence liefern, aber keinen kausalen Prompt-, Weight-,
Sampler-, Scheduler-, Checkpoint-, LoRA- oder Workflow-Credit.

Der Proof umfasst den vollständigen Weg aus neuen Viererreviews, bildweisen
Gründen, Candidate Pool, 16er-Cup, Pairwise-Evidence, kontrollierten Control-/
Challenger-Trys und Revalidierung auf neuen Seeds. Erst nach diesem Gate folgt
der Prolog-/Empty-Content-Bootstrap, der das Entwicklungs-Startmaterial durch
persönlich erzeugte Inhalte ersetzt. Legacy-Import und die mögliche spätere
Requalifikation weiterer Playground-Bilder sind ein eigener späterer Pfad und
kein Bestandteil dieses ersten Beweises.

Die vorhandenen Outfitdaten bieten viele Schuluniformvarianten, sind jedoch stark auf Bluse, Rock, Schleife und weibliche Präsentation ausgerichtet. Für die verbindliche anfängliche Auswahl zwischen männlich und weiblich sowie einen gemischten Cast muss der Uniformvertrag deshalb aus einem gemeinsamen Academy Blueprint mit getrennten Präsentationsvarianten neu aufgebaut werden.

Die vier Beispielprompts werden fachlich zerlegt:

```text
gemeinsame Qualitäts- und Artstyle-Tokens
→ Prompt Style Core und Negative Core

individuelle sichtbare Merkmale
→ CharacterVisualSpec

charakterspezifische Ausschlüsse
→ Character Constraints

allgemeine Anatomie- und Fehlervermeidung
→ globale Recovery- und Negative Policies
```

Neue Figuren werden nicht durch Kopieren oder Variieren der vier bestehenden Komplettprompts erzeugt.

### 28.2 Fixe, direkt wählbare und indirekt beeinflussbare Ebenen

#### Fixe Project- und Story-Regeln

- ein verbindlicher Anime Prompt Style,
- fiktive Senior Academy,
- April-bis-März-Schuljahr,
- 168 Story-Tage,
- 24 Special Slots,
- Chronicle-Projekt,
- authored CharacterBrandSlots,
- 16 mögliche Personality-Profile,
- Story-, Event- und Relationship-Gates,
- Mindestvielfalt des Casts,
- Prompt Compiler,
- Visual Asset Contracts,
- und Recovery-Regeln.

#### Explizite Userentscheidungen

Einige Informationen werden nicht verdeckt inferiert:

- Geschlecht beziehungsweise Präsentation des Protagonisten,
- Name und erlaubte direkte Identitätsangaben,
- Content-, Intimitäts- und Komfortgrenzen,
- Barrierefreiheit,
- und ausdrückliche visuelle Ausschlüsse.

#### Indirekt ermittelte Präferenzen

- traditionelle, moderne, urbane, küstennahe oder naturbetonte Weltwirkung,
- Schulfarben, Wappen- und Uniformrichtung,
- formelle oder individualisierte Kleidung,
- Palette, Sättigung, Kontrast und Lighting,
- realistische oder ungewöhnlichere Haarfarben,
- Haarlängen, Texturen und Silhouetten,
- Accessoire-Dichte,
- visuelle Expressivität,
- Social Energy und Character-Style-Tendenzen,
- Comedy-, Drama-, Mystery- und Slice-of-Life-Gewichtung,
- und bevorzugte erste Begegnungsdynamiken.

Der User beeinflusst Verteilungen und Tendenzen. Eine einzelne Antwort bestimmt nicht direkt, dass eine bestimmte Figur eine konkrete Haarfarbe oder Personality erhalten muss.

### 28.3 Diegetischer Prolog als authored Auswahlspiel

Der Prolog besteht aus mehreren kurzen Storyszenen. Die sichtbaren Fragen sind plausibler Bestandteil des Umzugs und des bevorstehenden Schulstarts.

#### Szene A: Ankunft in der neuen Stadt

Auswahl zwischen Eindrücken wie:

- altem Innenhof und bewachsenen Gebäuden,
- moderner Glasarchitektur,
- Bahnhof und Einkaufsstraße,
- Küste oder Hügeln.

Erhobene Signale:

- Stadtprofil,
- Academy-Architektur,
- bevorzugte Place-Arten,
- Farbtemperatur,
- und Lichtstimmung.

#### Szene B: Einzug mit der Mutter

Die Mutter erscheint zunächst nur als authored Silhouette. Dadurch benötigt der Prolog noch keinen generierten Supporting Character Canon.

Normale Gesprächsanlässe können sein:

- welche Umzugskiste zuerst geöffnet wird,
- wie das neue Zimmer wirken soll,
- welche Gegenstände sichtbar aufgestellt werden,
- oder was aus einer Erinnerungskiste behalten wird.

Erhobene Signale:

- Palette,
- Ordnung und Detaildichte,
- Hobby- und Signature-Prop-Tendenzen,
- Accessoires,
- und Character Motifs.

Die Mutter ist authored und verwendet keine freie Character-LLM-Rolle. Ihre Funktion ist Story, familiärer Anker und kontrollierte Informationsabfrage.

#### Szene C: Alte Erinnerungen

Ein Klassenfoto oder eine Erinnerung erlaubt indirekte Fragen nach sozialen Präferenzen:

- jemand zieht den Protagonisten aktiv mit,
- jemand lässt zunächst Raum,
- jemand fordert heraus,
- oder jemand bemerkt stille Probleme.

Diese Auswahl gewichtet erste Character-Dynamiken, legt aber weder Route noch Relationship fest.

#### Szene D: Schulunterlagen und Uniform

Eine conversationale Auswahl zwischen:

- formeller vollständiger Uniform,
- Cardigan- oder Vest-Variante,
- locker individualisierter Variante,
- und kleinem persönlichem Signature Detail

erzeugt den globalen `UniformBlueprint` mit saisonalen und präsentationsabhängigen Bindings.

#### Szene E: Schulbroschüre und Silhouetten

Die Broschüre zeigt keine finalen Character Designs, sondern stilisierte Silhouetten, Clubrollen, Haarformen, Körperhaltungen und Accessoire-Typen.

Eine Frage wie „Wen würdest du wahrscheinlich nach dem Weg fragen?“ liefert schwache Evidenz für:

- Haar- und Gesamtsilhouette,
- formelles oder lockeres Auftreten,
- Initiative,
- Nähe- und Distanzwirkung,
- und geeignete erste Begegnungsrollen.

#### Szene F: Erster Abend

Der Erzähler fragt nach Erwartungen und Sorgen. Die Auswahl beeinflusst:

- Prolog-Tempo,
- erste Social Situation,
- Anchor-, Connector- und Counterpoint-Gewichtung,
- und den ersten Daily Character Beat.

#### Szene G: Erster Schultag

Die bisherigen Signale bestimmen die erste Begegnungsreihenfolge und die ersten Character Build Quests. Der User erhält keine unsichtbare Route-Festlegung.

### 28.4 Struktur einer indirekten Frage

Jede Frage besitzt authored Antworten. Eine Antwort verändert mehrere kleine Gewichte:

```json
{
  "answer_id": "wait_in_old_courtyard",
  "effects": {
    "world.traditional": 2,
    "world.nature": 2,
    "palette.muted": 1,
    "lighting.soft": 1,
    "cast.formality": 1,
    "place.quiet_spaces": 2
  },
  "signal_type": "preference",
  "scope": "world_and_future_cast",
  "confidence": 0.35
}
```

Die sichtbare Antwort ist kein Promptfragment. Ein deterministischer Mapper erzeugt daraus `PreferenceEvidenceEvents`. Für diese Grundfunktion wird kein LLM benötigt.

Eine Antwort darf:

- mehrere Achsen leicht beeinflussen,
- keine Personality direkt festlegen,
- kein Relationship Level erzeugen,
- keine bestehende Character Identity überschreiben,
- und keine explizite Usergrenze inferieren.

### 28.5 Getrennte User- und Spielermodelle

Das System führt mindestens vier getrennte Zustände:

#### `VisualTasteProfile`

- Farben und Kontrast,
- Haarformen und Silhouetten,
- Kleidung und Accessoires,
- Bildstimmung,
- Character- und Place-Ästhetik.

#### `NarrativeTasteProfile`

- Comedy, Drama, Mystery und Slice of Life,
- Konfliktintensität,
- langsame oder direkte Offenheit,
- bevorzugte Eventtypen.

#### `SocialPreferenceProfile`

- Initiative,
- Nähe- und Distanzdynamik,
- ruhige, direkte, fürsorgliche oder herausfordernde Gegenüber,
- bevorzugte Gruppenkonstellationen.

#### `ProtagonistBehaviorState`

- tatsächlich gewählte Handlungen,
- Verhaltens- und Kommunikationsmuster des Protagonisten ohne Zuordnung zu einem der 16 Personality-Profile,
- Kommunikationsstil,
- moralische und soziale Entscheidungen.

Der `RelationshipState` jeder konkreten Figur bleibt eine weitere getrennte Domäne. Optisches Interesse, Protagonistenverhalten und bereits entstandene Beziehung werden nicht miteinander gleichgesetzt.

### 28.6 PreferenceEvidenceEvent

```json
{
  "evidence_id": "pref_0048",
  "source_type": "prologue_choice",
  "source_id": "school_brochure_02.answer_c",
  "signal_type": "visual_preference",
  "targets": {
    "visual.hair_shape.layered": 1,
    "visual.silhouette.relaxed": 2,
    "social.initiative.medium": 1
  },
  "scope": "future_character_generation",
  "confidence": 0.4,
  "story_day": "prologue_day_00",
  "reversible": true
}
```

Jedes Signal speichert Quelle, Scope, Gewicht, Confidence und Zeitpunkt. Dadurch bleibt nachvollziehbar, warum sich ein Taste Profile verändert hat.

### 28.7 Starke und schwache Präferenzsignale

#### Schwache Signale

- einzelne indirekte Prolog-Antwort,
- einmalige VN-Reaktion,
- zufällig ausgewählte Eventrichtung,
- oder erste Begegnungsentscheidung.

#### Mittlere Signale

- wiederholte Wahl ähnlicher Character- oder Eventtypen,
- freiwillige Fokuswahl,
- mehrfache Auswahl derselben Outfit- oder Place-Richtung,
- wiederholter Besuch einer Figur.

#### Starke visuelle Signale

- direkte Bildpaarwahl,
- Champion- und Favorite-Entscheidung,
- klarer Delete-Grund,
- wiederholte Ablehnung derselben sichtbaren Eigenschaft,
- und bestätigte Canon-Auswahl.

Nicht jede VN-Choice ist ein Geschmackssignal. Eine Choice mit der Frage „Was tust du?“ beeinflusst primär `ProtagonistBehaviorState`. Eine Choice mit der Frage „Mit wem möchtest du den Nachmittag verbringen?“ ist dagegen ein Social- und Fokus-Signal.

### 28.8 Kontinuierliche Aktualisierung

```text
Prolog-Antworten
→ PlayerTasteProfile Revision 1

erste Bild-Games und Begegnungen
→ Revision 2

Fokusentscheidungen, Ratings und Alltagsszenen
→ Revision 3 und weitere versionierte Updates
```

Das System darf später weitere diegetische Preference Probes in den Alltag einbetten, beispielsweise:

- Einkauf für ein Festival,
- Auswahl eines Chronicle-Layouts,
- Dekoration eines Clubraums,
- Entscheidung über einen Treffpunkt,
- Auswahl eines Kostüms,
- oder Sortieren von Bildern und Erinnerungen.

Diese Probes erscheinen nicht an jedem Tag und werden nicht als Persönlichkeitstest bezeichnet. Bild-Games liefern ohnehin kontinuierliche und meist stärkere visuelle Evidenz.

### 28.9 CharacterBrandSlot und Just-in-time-Visualisierung

Alle narrativ benötigten CharacterBrandSlots können von Anfang an existieren, ohne dass jede Figur bereits ein vollständiges sichtbares Design besitzt.

```text
authored CharacterBrandSlot
+ aktuelle PlayerTasteProfile Revision
+ WorldCanonVersion und UniformBlueprint
+ bereits sichtbarer Cast
+ CastDiversityRules
+ kontrollierter Character Seed
= CharacterVisualSeed
→ Character Build Quest
→ Canon Champion
→ erster vollständiger VN-Auftritt
```

Bereits enthüllte Character Canons werden durch spätere Taste-Änderungen nicht rückwirkend umgebaut. Neu gewonnene Evidenz beeinflusst:

- noch nicht enthüllte Figuren,
- zukönftige Outfits,
- optionale Frisurvarianten,
- Places,
- Eventpräsentation,
- und die Gewichtung späterer Begegnungen.

### 28.10 Erste Begegnungstrias

Die ersten Figuren werden nicht ausschließlich nach maximaler Taste-Ähnlichkeit ausgewählt:

1. **Anchor:** relativ hohe Übereinstimmung mit den ersten Präferenzsignalen,
2. **Connector:** glaubwürdige Verbindung zu Klasse, Club und Sozialkreis,
3. **Counterpoint:** attraktive, aber bewusst abweichende Richtung zur Prüfung früher Annahmen.

Der Counterpoint ist keine absichtlich unattraktive Figur. Er verhindert lediglich, dass schwache Prologsignale sofort den gesamten Cast homogenisieren.

Keine dieser drei Figuren wird automatisch zur Friendship- oder Romance Route. Beziehung entsteht ausschließlich durch spätere Interaktionen und Relationship Gates.

### 28.11 Präferenz, Exploration und Cast Diversity

Als erster konfigurierbarer Director-Richtwert gilt:

```text
60 % bestehende Präferenzrichtungen bedienen
25 % angrenzende Varianten testen
15 % kontrollierte Überraschung und Vielfalt
```

Die konkreten Werte benötigen Playtests. Unabhängig davon gelten harte Diversity Constraints gegen:

- zu ähnliche Haarfarben und Frisuren,
- gleiche Körper- und Kleidungssilhouetten,
- wiederholte Signature Accessories,
- identische Farbzuordnungen,
- stereotype Kopplung von Personality und Aussehen,
- und ungewollt einseitige Gender-/Präsentationsverteilung.

### 28.12 Verbindlicher Blueprint-Katalog, Laufzeit-Cast und begrenzte Route Coverage

Der vollständige Autorenkatalog besteht aus 32 `GenderedCharacterBlueprints`: sechzehn männlichen und sechzehn weiblichen Schablonen für die 16 Personality-Grundprofile. Sie sind keine fest benannten Personen. Ein Save instanziiert daraus sechzehn konkrete Fokusfiguren. Jede Figureninstanz besitzt einen eigenen Character Arc sowie Friendship- und Love-Interest-Potenzial. Der Jahreskalender ist jedoch absichtlich zu knapp, um in einem Lauf alle sechzehn aktiven Figuren vollständig zu erkunden.

Die frühere Zahl zwölf wird nicht mehr als Cast-Grenze verwendet. Sie beschreibt höchstens eine plausible Größenordnung dafür, wie viele Figuren ein sehr breit spielender Durchlauf gut kennenlernen könnte. Tatsächliche Route Coverage entsteht aus:

- investierten Storytagen,
- gemeinsam besuchten Events,
- Relationship Gates,
- freigeschalteten Visual Assets,
- Entscheidungen und Konsequenzen,
- sowie konkurrierenden Fokusgelegenheiten im Jahreskalender.

Das Geschlecht des Spielers bestimmt die Cast-Gewichtung: Höchstens vier der sechzehn aktiven Fokusfiguren haben dasselbe Geschlecht wie der Spieler; mindestens zwölf gehören dem jeweils anderen Geschlecht an. Die konkrete Zahl innerhalb dieses Korridors wird deterministisch aus Story- und Diversity-Anforderungen bestimmt.

### 28.13 Festgelegte Richtung

- Der Prolog ist eine authored Story und kein technischer Fragebogen.
- Erzähler und Mutter-Silhouette erheben Informationen innerhalb glaubwürdiger Szenen.
- Die Mutter benötigt im Prolog keine freie LLM-Rolle und keinen vollständigen Character Canon.
- Indirekte Antworten erzeugen mehrere schwache, strukturierte Präferenzsignale.
- Explizite Identitäts-, Content- und Komfortentscheidungen bleiben transparent.
- User Taste, Protagonist Behavior und konkrete Relationships sind getrennte State-Domänen.
- Bildentscheidungen liefern stärkere visuelle Evidenz als einzelne Storyantworten.
- Noch unbekannte Figuren werden kurz vor ihrem relevanten Auftritt aus BrandSlot, aktueller Taste Revision, World Canon und Diversity-Regeln konkretisiert.
- Bereits bestätigte Character Canons werden nicht automatisch verändert.
- Die ersten Figuren bilden Anchor, Connector und Counterpoint statt drei nahezu identischer Taste-Matches.
- Ein späterer Fokuswechsel bleibt immer möglich.

## 29. World Canon RAG und Character Knowledge Layer

Das Spiel benötigt neben charakterspezifischem Canon und Character Memory ein eigenes logisches World Canon RAG. Der wichtigste Schutzmechanismus ist jedoch eine epistemische Schicht: Ein World Fact darf nur dann in einen Character Call gelangen, wenn die konkrete Figur ihn wissen darf.

### 29.1 Getrennte Wissensdomänen

```text
World Canon
├─ objektive Weltwahrheit
├─ Academy, Stadt, Orte und Regeln
├─ Uniform, Clubs und Institutionen
├─ Kalender und öffentliche Ereignisse
└─ öffentliche Geschichte

Character Canon
├─ Brand, Backstory und Ziele
├─ Personality und Behavior Contract
├─ private Konflikte und Beziehungen
└─ Locked Character Facts

Character Knowledge
├─ bekannte World Facts
├─ selbst erlebte Events
├─ erhaltene Informationen
├─ Geheimnisse
├─ Gerüchte und Annahmen
└─ mögliche falsche Überzeugungen

Player Preference
├─ visuelle und narrative Präferenzen
└─ Director-Wissen, nicht automatisch Character-Wissen

Visual Retrieval
├─ Character-, Place- und Outfit-Referenzen
├─ Recipes und Ratings
└─ Recovery Evidence
```

Diese Domänen dürfen getrennte logische RAGs innerhalb derselben technischen Retrieval-Infrastruktur verwenden. Sie werden nicht als ein gemeinsamer ungefilterter Vektorpool behandelt.

### 29.2 World Canon als versionierte Source of Truth

Der Prolog kompiliert die feste Weltgrundlage und die erlaubten Usereinflüsse zu einer persönlichen `WorldCanonVersion`:

```text
Fixed World Core
+ Prolog Preference Evidence
+ ausdrückliche User Locks
+ kontrollierter World Seed
= WorldCanonVersion 1
```

Ein World Canon kann mindestens enthalten:

- Academy-Name und Typ,
- Stadtprofil,
- Schulfarben und Wappen,
- Architektur,
- Uniform Blueprint,
- Schulweg und Verkehrsstruktur,
- wiederverwendbare Places,
- Clubs und Räume,
- Schulregeln,
- Kalenderstruktur,
- Chronicle-Projekt,
- saisonale Weltzustände,
- und autorisierte historische Fakten.

Strukturierte Kernfakten werden direkt aus der Datenbank geladen. Nur wachsende Lore, Beschreibungen und historische Details benötigen semantisches Retrieval.

### 29.3 WorldFact-Vertrag

```json
{
  "fact_id": "festival_location_changed",
  "world_revision": 3,
  "category": "calendar_event",
  "claim": "Das Sommerfestival findet wegen des Wetters im überdachten Flusspark statt.",
  "truth_status": "canonical",
  "valid_from": "august_day_07",
  "valid_until": null,
  "visibility_scope": "school_public",
  "spoiler_gate": "festival_change_announced",
  "source_event_id": "school_announcement_aug_07"
}
```

World Facts sind versioniert. Ein neuer Zustand ersetzt einen alten nicht still, sondern besitzt Gültigkeit, Revision und Source Event.

### 29.4 CharacterKnowledgeRecord

```json
{
  "character_id": "character_04",
  "fact_id": "festival_location_changed",
  "knowledge_state": "confirmed",
  "learned_at": "august_day_07",
  "source": "school_announcement",
  "confidence": 1.0
}
```

Mögliche Knowledge States sind:

- `confirmed`,
- `observed`,
- `heard_from_other`,
- `rumor`,
- `suspected`,
- `misunderstood`,
- `forgotten_or_uncertain`,
- und `explicitly_unknown`.

Die Existenz eines World Facts bedeutet nicht automatisch, dass jede Figur einen CharacterKnowledgeRecord dafür besitzt.

### 29.5 BeliefRecord und falsches Wissen

Eine Figur darf eine falsche oder unvollständige Überzeugung besitzen. Diese ist nicht Teil der objektiven Weltwahrheit:

```json
{
  "belief_id": "kaori_archive_rumor_01",
  "character_id": "character_02",
  "claim": "Mizuki hat den Chronicle-Archivraum versehentlich beschädigt.",
  "belief_state": "rumor",
  "confidence": 0.55,
  "source_character_id": "support_07",
  "created_at_story_day": "january_day_05",
  "resolved_by_event_id": null
}
```

Der Character Speaker darf die Überzeugung als Gerücht oder Annahme ausdrücken, aber nicht als objektiv bestätigte World Truth, sofern sein Speech Contract dies nicht ausdrücklich erlaubt.

### 29.6 Sichtbarkeits- und Zugriffsscopes

Jeder Fact, Lore Chunk und Memory besitzt einen Scope, beispielsweise:

- `public`,
- `school_public`,
- `class:{id}`,
- `club:{id}`,
- `event_participants`,
- `shared_memory:{participant_ids}`,
- `character_private:{id}`,
- `narrator_only`,
- `director_only`,
- und `spoiler_after:{event_id}`.

Sichtbarkeit wird vor semantischer Ähnlichkeit geprüft:

```text
anfragende Rolle und konkrete Figur
→ Save, World- und Character-Version
→ Knowledge- und Visibility-Filter
→ zeitliche Gültigkeit
→ Spoiler Gate
→ kompatibler Embedding-Raum
→ Cosine Top-K
→ Widerspruchs- und Confidence-Prüfung
→ Context Pack
```

Ein hoher Embedding-Score darf niemals ein Geheimnis, einen zukünftigen Storybeat oder fremde private Erinnerung freischalten.

### 29.7 Wissensverteilung durch Domain Events

Wissen wird nicht nur beim LLM Call berechnet. Authorisierte Storyereignisse erzeugen Knowledge Events:

- `WorldFactCreated`,
- `WorldFactRevised`,
- `PublicAnnouncementMade`,
- `CharacterObservedFact`,
- `CharacterToldFact`,
- `RumorReceived`,
- `BeliefCorrected`,
- `SecretShared`,
- und `KnowledgeRevokedOrInvalidated`.

Ein öffentliches School Announcement kann allen berechtigten Schülern einen KnowledgeRecord geben. Ein privates Gespräch gibt Wissen nur den anwesenden Figuren. Eine Figur, die zu diesem Zeitpunkt nicht anwesend war, erhält es nicht automatisch.

### 29.8 Beispiel einer differenzierten Wissenslage

Objektive Weltwahrheit:

> Der Chronicle-Archivraum wurde durch einen Wasserschaden beschädigt.

Mögliche Character Views:

- Protagonist hat den Schaden gesehen,
- Mizuki war dabei und kennt die Ursache,
- Aiko weiß nur, dass das Treffen ausgefallen ist,
- Kaori hat ein falsches Gerücht über Mizuki gehört,
- die restliche Schule weiß noch nichts.

Alle Figuren dürfen dadurch unterschiedlich über dasselbe Ereignis sprechen, ohne dass ein LLM ihre Wissenslage frei erfindet.

### 29.9 Context Pack für den Character Speaker

```text
Locked Character Core
+ Personality Behavior Pack
+ Relationship State
+ Current State und Scene Contract
+ eigene freigegebene Memories
+ erlaubte bekannte World Facts
+ aktuelle Beliefs und Gerüchte
+ aktuelle Usernachricht
= Character Context Pack
```

Der Character Speaker erhält niemals das vollständige World RAG. Er darf keine neuen Facts oder Knowledge Grants schreiben. Seine Ausgabe bleibt Figurenrede und erlaubte Expression.

### 29.10 Context Pack für den Prompt Generator

```text
Visual World Bible
+ aktive WorldCanonVersion
+ PlaceDefinition oder PlaceVariant
+ UniformBlueprint
+ CharacterVisualCanon
+ Visual Specification
+ Prompt Style Core
+ Recovery Constraints und Evidence
= Visual Prompt Context
```

Private Character-Memories oder Gerüchte gelangen nur dann in den Promptpfad, wenn der Director daraus eine ausdrücklich erlaubte sichtbare Pose, Expression, Prop- oder Scene-Anforderung erzeugt hat.

Der Prompt Generator muss nicht den privaten Grund einer Emotion kennen. Er benötigt die bereits freigegebene sichtbare Spezifikation.

### 29.11 Narrator und Director

Der Erzähler bleibt authored. Er benötigt kein frei formulierendes World-LLM und darf auf authorisierte World- und Storywerte über Textkeys und kontrollierte Variablen zugreifen.

Der Game Director besitzt Zugriff auf:

- Story Graph,
- Calendar und Day State,
- World Canon,
- Character Knowledge und Beliefs,
- Relationship und Personality State,
- Preference Profiles,
- Visual Requirements,
- und Progression Gates.

Dieser Zugriff dient deterministischen Entscheidungen. Der Director ist kein erzählendes LLM.

### 29.12 Player Preference ist kein Character-Wissen

Ein Eintrag wie „Der Spieler bevorzugt kurze rote Haare und direkte Figuren“ ist ausschließlich Director- und Cast-Assembler-Wissen.

Er darf verwendet werden für:

- noch nicht enthüllte Character Visual Seeds,
- Begegnungsgewichtung,
- Outfit- und Place-Vorschläge,
- Preference Probes,
- und Bildkandidaten.

Eine Figur erhält diese Information nur, wenn sie innerhalb der Story tatsächlich mitgeteilt oder sichtbar demonstriert wurde.

### 29.13 Logische Retrieval-Namespaces

Dieselbe lokale Embedding-Infrastruktur und `retrieval.sqlite3` können verwendet werden. Die RAGs bleiben durch Namespaces, Owner und Policies getrennt:

```text
world_lore_text
world_visual_text
character_memory_text
character_belief_text
component_text
player_preference_text
recovery_case_text
```

Darüber sitzen getrennte Assembler:

- `WorldContextAssembler`,
- `CharacterContextAssembler`,
- `VisualContextAssembler`,
- und `PreferenceContextAssembler`.

Ein gemeinsamer Textencoder macht die Scopes nicht austauschbar. Kosinuswerte werden nur innerhalb des zugelassenen Raums ausgewertet.

### 29.14 Source of Truth, Retrieval und Schreibautorität

```text
strukturierter Canon und Domain Events
→ Source of Truth

Embeddings und Chunk-Index
→ rekonstruierbare Kandidatensuche

Context Assembler
→ autorisierte Sicht für genau eine Rolle

LLM
→ Formulierung oder Promptfragment

Director und Validator
→ erlaubtes Resultat und eventuelle State Events
```

Kein LLM schreibt direkt in World Canon, Character Knowledge, Beliefs, Preference Profiles, Relationship State oder Story Progression.

### 29.15 Festgelegte Richtung

- World Canon RAG und Character Memory RAG sind getrennte logische Wissensräume.
- Das World RAG enthält Welt-, Academy-, Place-, Uniform-, Kalender- und öffentliche Lore-Inhalte.
- Charaktere erhalten niemals automatisch das gesamte World RAG.
- CharacterKnowledgeRecords und Beliefs modellieren, was eine Figur weiß, vermutet, missversteht oder nicht weiß.
- Sichtbarkeit, Zeit und Spoiler Gates werden vor Vektorsuche geprüft.
- Falsche Beliefs bleiben von objektiver World Truth getrennt.
- Wissen verbreitet sich nur durch authorisierte Domain Events und Teilnehmerregeln.
- Character Speaker, Prompt Generator, Narrator und Director erhalten unterschiedliche Context Views.
- Player Preference bleibt Director-Wissen und wird nicht an Figuren geleakt.
- Die RAGs dürfen dieselbe lokale technische Infrastruktur verwenden, besitzen aber getrennte Namespaces und Assembler.
- Embeddings sind auch hier nur Retrieval und niemals Canon oder Schreibautorität.

## 30. Offene Integrationsfragen und empfohlene Vertiefungsreihenfolge

Die Grundrichtung ist definiert. Für die nachfolgenden Chronicle-Slices fehlen jedoch noch mehrere verbindliche Verträge. Sie werden nicht gleichzeitig gelöst, weil die späteren Systeme von den früheren Outputs abhängen.

### 30.1 Kritische Produktentscheidungen

1. **Cast-Slot-Auswahl:** nach welcher authored Priorität werden innerhalb der festen Grenze null bis maximal vier gleichgeschlechtliche Slots gewählt.
2. **Protagonistenworkflow:** wie werden die acht vorhandenen Spielerporträts im Prolog präsentiert, ausgewählt oder als Präferenzanker für eine spätere individuelle Variante verwendet.
3. **Romance-Gates:** konkrete Friendship-Schwelle, Intent Gates und Freischaltregeln bis zur Love-Interest-Route.
4. **Prolog-Termination:** welche minimale Start-Story und welche Build Requirements erzeugt sein müssen, bevor der Prolog in den ersten asset-gebundenen Progressionsschritt übergeht.
5. **Style Discovery:** welche Style-Achsen zu Beginn offen sind, wie viele unabhängige Trials einen stabilen Wert ergeben und wann eine Revision wieder geöffnet werden darf.

Diese Entscheidungen verändern Content- und Generierungsumfang. Sie müssen vor dem finalen CharacterBrandSlot-Katalog getroffen werden.

### 30.2 Fixed-vs-Variable-Matrix der Welt

Noch festzulegen ist für jedes Feld:

- projectweit unveränderlich,
- pro Save auswählbar,
- indirekt beeinflussbar,
- kontrolliert zufällig,
- später entwickelbar,
- oder nach Canon Lock unveränderlich.

Benötigte Bereiche:

- Academy-Name und Geschichte,
- Stadt- und Landschaftsprofil,
- Architektur,
- Schulfarben und Wappen,
- Uniform Blueprint,
- Club- und Raumstruktur,
- wiederverwendbare Places,
- saisonale Varianten,
- Cast-Zusammensetzung,
- CharacterVisualSeeds,
- und Narrative Tone.

Ohne diese Matrix kann der Prolog nicht sicher wissen, welche Antworten in Canon, Preference oder Random State schreiben dürfen.

### 30.3 Prolog Vertical Slice

Als nächster konkreter Storyvertrag wird ein vollständiger Day-0-Prolog benötigt:

1. authored Erzählertexte,
2. Mutter-Silhouetten-Szenen,
3. sichtbare Antwortkarten,
4. `PreferenceEvidenceEvents`,
5. direkte User Locks,
6. resultierende `WorldCanonVersion 1`,
7. resultierender `UniformBlueprint`,
8. `PlayerTasteProfile Revision 1`,
9. erste Encounter-Trias,
10. und erste Visual Build Requirements.

Erst dieser Vertical Slice zeigt, ob sich das Onboarding wie Story statt wie ein verstecktes Formular anfühlt.

### 30.4 Fragebank und Evidence Mapping

Offen sind:

- Anzahl fester und adaptiver Fragen,
- maximale Prologdauer,
- Antwortkarten pro Frage,
- Achsen und erlaubte Werte,
- Gewicht und Confidence jeder Antwort,
- widersprüchliche Antworten,
- Neutral-/Surprise-Me-Optionen,
- und sichtbare Korrekturmöglichkeiten vor dem ersten Canon Lock.

Jede Frage benötigt einen Test, der beweist, dass keine einzelne Antwort eine unzulässig direkte oder stereotype Character-Zuordnung erzeugt.

### 30.5 PlayerTasteProfile und Lernlogik

Zu spezifizieren sind:

- konkrete Visual-, Narrative- und Social-Achsen,
- Normalisierung und Confidence,
- Zusammenführung widersprüchlicher Evidenz,
- zeitliche Stabilität oder Decay,
- stärkere Gewichtung direkter Bildentscheidungen,
- Abgrenzung gegen Protagonist Behavior,
- manuelle Locks und Resets,
- und die Berechnung von Exploration, Exploitation und Diversity.

Der erste Prototyp soll deterministic scoring verwenden. Ein ML- oder LLM-basierter Präferenzklassifikator ist keine Voraussetzung.

### 30.6 CharacterBrandSlot- und Cast-Assembler-Vertrag

Für jeden Slot fehlen noch:

- narrative Rolle,
- Beziehungen zu anderen Slots,
- Kernkonflikt,
- erlaubte Personality-Entwicklungen,
- Gender-/Präsentationsregeln,
- visuelle Pflicht- und Verbotsachsen,
- erlaubte World-/Clubbindungen,
- Reveal Window,
- und geeignete Special Slots.

Der Cast Assembler benötigt außerdem eine formale Diversity Objective Function und Kollisionsregeln für Haare, Palette, Silhouette, Accessoires, Hobbys und Social Roles.

### 30.7 Bootstrap und erste Generierungsreihenfolge

Noch ungeklärt ist, welche Assets mitgeliefert, pro Save erzeugt oder erst später gebaut werden:

- Umzugszimmer und Mutter-Silhouette,
- Stadt-Establishing-Shot,
- Academy Exterior,
- Uniform Blueprint Preview,
- Protagonist,
- Anchor, Connector und Counterpoint,
- erste Classroom- und Clubroom-Places,
- und erste Daily Expressions.

Die Reihenfolge muss die reale Generierungszeit berücksichtigen und darf den Prolog nicht vor dem ersten spielbaren Character Beat minutenlang blockieren.

### 30.8 World Canon Datenmodell und Authoring

Zu trennen sind:

- kleine strukturierte Kernfakten,
- lange Lore-Chunks,
- visuelle World Specifications,
- dynamische World State Changes,
- öffentliche Ankündigungen,
- historische Fakten,
- und Story Secrets.

Offen sind Chunk-Größe, Tags, Versionierung, Validity Windows, Spoiler Gates und der Authoring-Workflow für neue World Facts.

### 30.9 Knowledge Propagation und Belief Resolution

Für jeden Story Event muss definiert werden:

- wer anwesend ist,
- wer etwas beobachtet,
- welche Fakten öffentlich werden,
- ob Weitererzählen erlaubt ist,
- wie Gerüchte entstehen,
- wann ein Belief korrigiert wird,
- und wie widersprüchliche Knowledge Records aufgelöst werden.

Ohne diese Regeln entsteht trotz getrenntem RAG schnell unbeabsichtigte Allwissenheit.

### 30.10 Context Assembler und Token Budgets

Jede LLM-Rolle benötigt einen konkreten Budgetvertrag:

- feste Pflichtdaten,
- maximale Zahl episodischer Memories,
- maximale Zahl World Lore Chunks,
- Umgang mit Beliefs und Rumors,
- Priorisierung bei zu großem Kontext,
- Query-Konstruktion,
- und deterministischen Fallback bei leerem oder widersprüchlichem Retrieval.

Character Speaker und Prompt Generator dürfen nicht denselben generischen RAG-Wrapper verwenden.

### 30.11 Build- und Story-Integration

Noch zu verbinden sind:

- Zeitpunkt des CharacterVisualSeed,
- Erzeugung eines Visual Manifests,
- Mindestanzahl der Build-Runden,
- Umgang mit Null-Contender-Zyklen vor einem Reveal,
- Character Content während Generierungswartezeit,
- und der Canon Lock nach Champion-Bestätigung.

Der Preference State darf keine bereits bestätigte Figur verändern, muss aber neue Build Quests sinnvoll beeinflussen.

### 30.12 Evaluation und Leak Tests

Benötigt werden mindestens:

- Prolog-Tests für unterschiedliche Antwortmuster,
- Cast-Diversity-Snapshots über viele Seeds,
- Tests gegen stereotype Personality-Visual-Kopplung,
- Tests für späten Fokuswechsel,
- Knowledge-Visibility- und Spoiler-Leak-Tests,
- falsche-Belief- und Korrekturtests,
- RAG Recall/Precision pro Namespace,
- Context-Budget-Tests,
- und Save-/Reload-Reproduzierbarkeit.

### 30.13 Empfohlene Reihenfolge

```text
1. Cast-Gewichtung und explizite Startentscheidungen festlegen
→ 2. Fixed-vs-Variable-Matrix erstellen
→ 3. Day-0-Prolog als Vertical Slice authoren
→ 4. PreferenceEvidence- und TasteProfile-Vertrag finalisieren
→ 5. CharacterBrandSlots und Diversity Resolver spezifizieren
→ 6. Bootstrap- und erste Build-Reihenfolge festlegen
→ 7. WorldFact-, Knowledge- und Belief-Schema finalisieren
→ 8. Context Assembler pro LLM-Rolle definieren
→ 9. Build-, Calendar- und Relationship-Integration schließen
→ 10. Retrieval-, Leak- und End-to-End-Evals bauen
```

Der nächste inhaltliche Deep Dive sollte daher nicht mit Vektordatenbankdetails beginnen. Zuerst werden Cast-Gewichtung, Fixed-vs-Variable-Matrix und der vollständige Prolog-Output festgelegt. Diese drei Entscheidungen definieren die Daten, die World RAG, Character Generation und spätere Context Assembler überhaupt verarbeiten müssen.

## 31. Sechzehn Figuren, parallele Routes, sozialer Wissensfluss und lernende Bildpräferenzen

### 31.1 Fester Cast, absichtlich unvollständiger Lauf

Ein Save enthält sechzehn vollwertige Fokusfiguren. Jede Figur kann grundsätzlich so tief erkundet werden wie jede andere. Es gibt keine zweite Klasse aus lediglich dekorativen Supporting Characters, die benötigt würde, um die 16 Personality-Profile abzubilden.

Der Spieler soll in einem Durchlauf dennoch nicht alle sechzehn persönlichen Geschichten vollständig abschließen können. Diese Begrenzung entsteht organisch aus dem Schuljahr:

- Jeder relevante Besuch, jedes Gespräch und jedes Fokus-Event verbraucht Zeit oder eine Begegnungsgelegenheit.
- Tiefe Routes benötigen wiederkehrende Begegnungen über mehrere Jahreszeiten.
- Visual Asset Quests müssen vor bestimmten VN-Szenen abgeschlossen werden.
- Manche Termine, Einladungen und Route Events konkurrieren miteinander.
- Vernachlässigte Beziehungen stagnieren oder entwickeln sich ohne direkten Spielerfokus weiter.

Es gibt daher kein hartes technisches Maximum von zwölf erkundbaren Figuren. Ein breiter Lauf kann viele Figuren kennenlernen, ein fokussierter Lauf wenige Figuren sehr tief erschließen. Die vollständige Route Coverage ist bewusst ein Langzeit- und Replay-Ziel.

### 31.2 Jede Figur besitzt Friendship und Love Interest

Für jede der sechzehn Fokusfiguren werden mindestens folgende authored Pfade vorgesehen:

1. Kennenlernen und gemeinsame Basisszenen,
2. Friendship Route,
3. erst nach ausreichender Friendship freischaltbare Love-Interest-Route,
4. Distanzierungs-, Konflikt- oder Reparaturzustände,
5. ein zum erreichten Stand passendes Graduation Outcome.

Friendship und Romance sind keine voneinander isolierten Vollskripte. Sie teilen Character Arc, Alltag und große Calendar Events. An definierten Gates unterscheiden sich:

- Intention und Ton der Auswahlmöglichkeiten,
- körperliche und emotionale Grenzen,
- Versprechen und Erwartungen,
- Reaktionen anderer Figuren,
- Konflikte,
- sowie mögliche Endzustände.

Eine Friendship Route darf tief, intim und narrativ vollständig sein, ohne automatisch als gescheiterte Romance behandelt zu werden. Love Interest ist bei jeder Figur grundsätzlich vorhanden, beginnt jedoch niemals direkt beim Kennenlernen. Ein authored Friendship Gate aus Vertrautheit, Vertrauen und mindestens einem gemeinsamen Milestone muss zuvor erfüllt sein.

### 31.3 Parallele Relationship Progression

Mehrere Beziehungen dürfen gleichzeitig wachsen. Ein globaler Single-Route-Lock wäre für den sozialen Schuljahresansatz zu früh und zu unflexibel.

Der deterministische Relationship State pro Figur wird um folgende Bereiche ergänzt:

```text
RelationshipState
├─ familiarity
├─ trust
├─ affinity
├─ tension
├─ romantic_interest_character
├─ romantic_interest_player
├─ route_mode: undecided | friendship | romance
├─ romantic_intent_stage: none | hinted | expressed | reciprocated
├─ commitment_state: none | exploring | exclusive | negotiated_nonexclusive | committed | strained | ended
├─ promises[]
├─ boundaries[]
├─ known_relationship_facts[]
└─ unlocked_route_gates[]
```

Dabei darf ein `route_mode` noch lange `undecided` bleiben. Vor dem Friendship Gate können höchstens frühe Sympathie oder schwache romantische Foreshadowing-Signale auftreten; der eigentliche Romance-Pfad bleibt gesperrt. Flirt, Neugier oder ein früher romantischer Moment sind außerdem nicht automatisch ein exklusives Versprechen.

### 31.4 Mehrere Love Interests erzeugen kontextuelle Konsequenzen

Der Versuch, mehrere Love-Interest-Routes parallel zu verfolgen, erhält keine pauschale und sofortige Negativstrafe. Die Konsequenz hängt von tatsächlich etablierten Umständen ab:

- Weiß die betroffene Figur davon?
- Wurde Exklusivität versprochen?
- Wurden Grenzen oder Absprachen verletzt?
- Welche Erwartungen besitzt die Figur aufgrund von Character Brand, Personality State und bisherigen Erfahrungen?
- Handelt der Spieler offen, unklar oder bewusst heimlich?
- Besteht zwischen den Beteiligten bereits Vertrauen, Freundschaft, Rivalität oder Spannung?
- Passt eine nicht-exklusive Konstellation zu den ausdrücklich authored Grenzen aller Beteiligten?

Mögliche Outcomes sind daher nicht nur ein Malus:

- neutrale Offenheit ohne frühe Bindung,
- Unsicherheit oder Klärungsgespräch,
- humorvolle oder kompetitive Spannung,
- Eifersucht,
- Vertrauensverlust,
- veränderte Event-Einladungen,
- Freundschaft als neue Route,
- einvernehmlich nicht-exklusive Beziehung,
- exklusive Entscheidung,
- Rückzug oder Trennung.

Eine nicht-exklusive Route ist nur möglich, wenn die Story sie ausdrücklich unterstützt und alle beteiligten Figuren informiert zustimmen. Das LLM darf weder Zustimmung noch Exklusivität erfinden. Gebrochene Versprechen und verschwiegene Beziehungen lösen deterministische Story Events aus, sobald die relevante Information eine Figur glaubwürdig erreicht.

### 31.5 Konsequenzen benötigen Wissen statt Allwissenheit

Eine Figur reagiert nur auf Informationen, die sie besitzt oder plausibel ableitet. Das System trennt daher weiterhin:

- tatsächlichen World und Relationship State,
- Wissen einzelner Figuren,
- subjektive Beliefs,
- Gerüchte,
- und dem Spieler bekannte Informationen.

Jede VN-Szene besitzt eine verbindliche Teilnehmerliste. Alle anwesenden Figuren erhalten nach Abschluss die dafür markierten Fakten:

```json
{
  "scene_id": "scene_summer_festival_07",
  "participant_character_ids": ["char_02", "char_07", "char_11"],
  "observed_fact_ids": ["fact_player_arrived_with_char_07"],
  "private_fact_grants": {
    "char_07": ["fact_player_promised_rooftop_meeting"]
  },
  "shareability": {
    "fact_player_arrived_with_char_07": "socially_shareable",
    "fact_player_promised_rooftop_meeting": "private"
  }
}
```

Teilnahme bedeutet also nicht, dass jede Figur jeden inneren Gedanken oder jedes private Detail kennt. Der Scene Contract bestimmt beobachtbare und private Fakten explizit.

### 31.6 NPC-Beziehungen und Offscreen-Konversation

Ein vollständiges freies Simulieren aller Paarbeziehungen wäre unnötig teuer und kaum kontrollierbar. Bei sechzehn Figuren existieren bereits 120 mögliche ungerichtete Paare. Deshalb wird ein sparsamer authored Social Graph verwendet.

Jede Figur besitzt zunächst drei bis fünf bedeutende Kanten, beispielsweise:

- enge Freundschaft,
- Geschwister- oder Familiennähe,
- Club- oder Klassenbindung,
- Rivalität,
- frühere Enttäuschung,
- gegenseitigen Respekt,
- oder einseitige Vertrautheit.

Nur bedeutende Kanten erhalten einen detaillierten `NpcRelationshipState`:

```text
NpcRelationshipState
├─ familiarity
├─ trust
├─ affinity
├─ tension
├─ disclosure_tendency
├─ protected_topics[]
├─ shared_fact_ids[]
└─ active_social_beats[]
```

Offscreen-Konversationen laufen nicht als autonome, unbegrenzte LLM-Chats. Der Calendar Director kann kontrollierte `SocialExchangeEvents` auslösen. Der Event Contract entscheidet deterministisch:

- welche Figuren miteinander sprechen,
- warum das Gespräch stattfindet,
- welche Fakten als Kandidaten gelten,
- welche Geheimhaltungs- oder Vertrauensregeln greifen,
- und welches Knowledge Event danach geschrieben wird.

Das Figuren-LLM darf die freigegebenen Aussagen formulieren. Ob eine Information geteilt wurde und welchen Wahrheitsstatus sie besitzt, entscheidet ausschließlich die Spiellogik.

### 31.7 Fester Prolograhmen mit wachsenden Auswirkungen

Der Prolog besitzt einen weitgehend gleichen authored Ablauf:

```text
Umzugszimmer
→ Gespräch mit der Mutter-Silhouette
→ Erinnerungs-/Entscheidungsmomente
→ Ankunft in der neuen Stadt
→ erster Blick auf Academy und Uniform
→ erste Begegnungen
```

Die konkrete Mutterfigur muss zu diesem Zeitpunkt nicht generiert werden. Silhouette, Inszenierung und Dialogfunktion bleiben wiederverwendbar. Die Szene ist absichtlich vage genug, dass unterschiedliche Saves denselben dramaturgischen Rahmen verwenden können.

Die Antworten verändern nicht rückwirkend den Prolograhmen. Sie erzeugen strukturierte Outputs für spätere Inhalte:

- `PlayerTasteProfile Revision 1`,
- `WorldCanonVersion 1`,
- `AnimeStyleProfile Revision 1`,
- `UniformBlueprint Revision 1`,
- Farb- und Formrichtungen,
- erste CharacterVisualSeeds,
- Gewichtung der ersten Encounter-Trias,
- und erste Visual Asset Requirements.

Spätere Entscheidungen und Bildbewertungen dürfen diese Profile weiter präzisieren. Bereits als Champion bestätigte und per Canon Lock fixierte Figuren werden dadurch nicht rückwirkend umgestaltet.

### 31.8 Ein Anime Style Core und ein spielerisch konvergierendes Style-Profil

Die Vorgabe eines einzigen Prompt Styles bleibt als äußerer Korridor bestehen. Der Spieler wählt keine voneinander unabhängigen Medien oder beliebigen Renderpipelines. Innerhalb dieses Anime-Korridors wird die konkrete visuelle Handschrift jedoch nicht pauschal am Anfang festgelegt, sondern entsteht schrittweise aus wiederholten Bildbewertungen.

Es gelten drei Ebenen:

1. `AnimeStyleCore`: projektweit feste Prompt-Grammatik, Medium-Grenzen und harte Verbote.
2. `StyleDiscoveryEnvelope`: erlaubter Testraum für noch unklare Style-Achsen.
3. `AnimeStyleProfile`: aus wiederholter Evidenz entstandene, versionierte Präferenz- und Generierungsrichtung eines Saves.

Das entstehende Style-Profil kann kontrolliert präzisieren:

- Palette und Farbsättigung,
- Kontrast,
- Linienweichheit innerhalb eines freigegebenen Bereichs,
- Lichtstimmung,
- Detaildichte,
- Grad der stilisierten Proportionen,
- Hintergrundatmosphäre,
- und visuelle Wärme oder Kühle.

Ein anderer gültiger Wert innerhalb der noch offenen Discovery Envelope ist eine bewusst getestete Variante und kein Artstyle-Fehler. Wiederholte Ratings können einzelne Achsen von `open` über `preferred` zu `stable` bewegen. Auch stabile Achsen bleiben versioniert und dürfen nur durch erneute explizite Style Trials verändert werden, nicht nebenbei durch ein einzelnes Character Rating.

`Wrong Artstyle` ist dagegen jederzeit ein klarer Fehler- und Löschgrund, wenn ein Bild bereits den übergeordneten AnimeStyleCore verlässt, beispielsweise durch Fotorealismus, 3D-Renderlook, unpassendes Medium oder massiv inkompatible Proportionen. Nach Stabilisierung enger Style-Achsen kann zusätzlich `style_profile_mismatch` verwendet werden: Das Bild ist technisch im AnimeStyleCore, passt aber nicht mehr zum aktuell bestätigten Save-Stil und wird deshalb nicht als Story Champion zugelassen.

### 31.9 Bildbewertungen erzeugen wiederholte Preference Evidence

Visuelle Präferenzen dürfen nicht aus einem einzelnen Vergleich abgeleitet werden. Die wiederholten Pflicht-Vierervergleiche bis zu sechzehn bestätigten Kandidaten dienen auch als kontrollierte Experimente über mehrere Batches hinweg.

Jedes Bild besitzt neben Embeddings strukturierte Merkmale, unter anderem:

- Palette,
- Kontrast,
- Haarform und -länge,
- Silhouette,
- Kleidungsform,
- Detailgrad,
- Linien- und Lichtprofil,
- Pose,
- Komposition,
- Hintergrunddichte,
- sowie technische Generierungsparameter.

Eine Auswahl erzeugt ein `VisualPreferenceObservation`, aber noch keine endgültige Regel:

```json
{
  "observation_id": "vpo_00412",
  "source": "pairwise_comparison",
  "winner_asset_id": "asset_871",
  "loser_asset_id": "asset_868",
  "differing_axes": ["palette_temperature", "line_softness"],
  "confounded_axes": ["pose_energy"],
  "confidence": 0.34,
  "scope": "character_visual",
  "session_id": "save_03_day_18"
}
```

Nur Merkmale, die zwischen zwei Kandidaten tatsächlich unterscheidbar waren, dürfen Evidenz erhalten. Sind zu viele Achsen gleichzeitig verändert, sinkt die Confidence. Wiederholt sich dasselbe Signal über unterschiedliche Seeds, Batches, Figuren und Spieltage, steigt seine Stabilität.

Jede Achse wird als Verhältnisgeschichte und nicht als globaler Punktestand
projiziert. Der Code führt dafür mindestens `positive_mass`, `negative_mass`,
`observation_count`, `independent_source_count`, `evidence_ratio`, `uncertainty`
und `confidence`. Ein Bild mit sechs positiven und zwei negativen Beobachtungen
besitzt eine andere Historie als ein neues Bild mit einer positiven Beobachtung,
auch wenn das neue Bild nominell zunächst das höhere Verhältnis hat. Die hohe
Unsicherheit des neuen Bildes autorisiert weitere Vergleiche; sie ist kein
automatischer Verlust.

Positive und negative Befunde verschiedener Achsen werden niemals zu einem
Gesamtscore gegeneinander verrechnet. Favorite und Keep liefern die
Ausgangsevidenz, Primary und Secondary Reasons verteilen sie auf die passenden
Achsen, und A/B-Matches ergänzen Gewinner- beziehungsweise Verlierermasse nur auf
der sichtbaren Vergleichsachse. Rohereignisse bleiben append-only. Eine neue
Prompt-, Character-, Asset- oder Canon-Revision erhält einen neuen Context Hash
und damit eine neue Projektion; die alte Historie bleibt Provenienz.

Eine Präferenzachse durchläuft mindestens:

```text
unknown → tentative → probable → stable
```

Der Übergang benötigt mehrere unabhängige Beobachtungen. Exakte Schwellenwerte werden durch Playtests kalibriert. Ein direkter Favorite, ein explizites „passt perfekt“ oder ein klarer Löschgrund kann stärker gewichtet werden als ein knapper Paarvergleich, ersetzt aber ebenfalls nicht jede langfristige Evidenz.

### 31.10 Geschmackslernen und Generatorqualität sind getrennte Signale

Die Bewertung eines Bildes darf drei unterschiedliche Fragen nicht vermischen:

1. **User Taste:** Gefällt dem Spieler die valide visuelle Richtung?
2. **Canon Compatibility:** Passt das Bild zu Figur, Outfit, Szene und aktuellem Style-Profil?
3. **Generation Reliability:** Hat Prompt-/Modell-/Parameterkombination technisch zuverlässig funktioniert?

Klare Fehler wie falsche Hände, anatomische Defekte, komischer Hintergrund, kaputte Freistellung oder Wrong Artstyle schreiben primär in Quality- und Recovery-Daten. Sie sollen nicht automatisch als ästhetische Abneigung des Spielers interpretiert werden.

Beispiel:

```text
Bild besitzt gewünschte kühle Palette,
aber sechs Finger
→ positive oder neutrale Taste-Evidence für Palette möglich
→ harter Quality-Fail für Anatomie
→ Asset wird gelöscht und nicht zum Champion
→ Recovery darf die funktionierenden Promptteile bewahren
```

Candidate Ranking verwendet getrennte Werte und harte Gates. Ein hoher Taste Score kann einen Fehler- oder Canon-Fail niemals überstimmen.

### 31.11 Kontrollierte Variation bis zu sechzehn bestätigten Kandidaten

Die Vierer-Batches einer Visual Asset Quest sollen nicht aus nahezu identischen Zufallsseeds bestehen. Der Prompt Generator erhält einen fortlaufenden deterministischen Variant Plan:

- mehrere Kandidaten bedienen den aktuellen stabilen Präferenzkern,
- einige testen angrenzende Werte einzelner Achsen,
- wenige liefern kontrollierte Exploration,
- und alle müssen Canon, Style Core und harte Anforderungen einhalten.

Wo sinnvoll, werden Kandidaten paarweise so geplant, dass nur wenige Achsen variieren. Dadurch kann aus Bewertungen tatsächlich gelernt werden. Gleichzeitig darf der Loop nicht wie ein sichtbares A/B-Testlabor wirken; die Varianten bleiben als Bildspiel und Character Build Quest inszeniert.

Nach jeder Viererrunde werden alle transportgültigen, kontextkompatiblen Keeps
und Favorites automatisch in den Quest-Pool übernommen. Der Vergleichsloop
läuft weiter, bis dieser Pool sechzehn bestätigte Kandidaten enthält. Eine Runde
ohne Kandidaten liefert trotzdem:

- Quality-Fehlerstatistik,
- Recovery-Vorschläge,
- schwache oder negative Preference Evidence,
- Laufzeit- und Modellmetriken,
- sowie Hinweise darauf, welche Variationsachsen nicht funktioniert haben.

### 31.12 Kleine, rollenreine LLM-Kontexte

Die genaue Kontextgröße ergibt sich aus den späteren Contracts. Verbindlich ist bereits, dass kein Modell den gesamten Save, den gesamten World Canon oder alle Figuren-Memories erhält.

Der `Character Speaker` bekommt nur:

- unveränderlichen Character Core,
- aktuellen Personality- und Relationship State,
- den authored Scene/Speech Contract,
- in dieser Szene erlaubte aktuelle Fakten,
- wenige relevante episodische Memories,
- und ein enges Structured-Output-Schema.

Der `Prompt Generator` bekommt nur:

- Visual Requirement,
- Character/Place/Outfit Canon,
- AnimeStyleCore und aktuelles AnimeStyleProfile,
- Variant Plan,
- relevante Recovery Evidence,
- technische Modellgrenzen,
- und das erzwungene Prompt-Schema.

Keines der beiden Modelle entscheidet Wahrheit, Anwesenheit, Beziehungsstatus, Einverständnis, Wissensbesitz, Route Gates, Champion-Status oder Storyfortschritt. Diese Zustände gehören zur serialisierbaren Simulation und werden vor dem LLM-Aufruf festgelegt sowie nach der Antwort validiert.

### 31.13 Noch zu vertiefende Verträge

Aus der jetzt festgelegten Richtung folgen vier nächste Designaufgaben:

1. `CastGenderSlotSelector`: deterministische Auswahl von null bis maximal vier gleichgeschlechtlichen Slots nach Story-, Social-Graph- und Diversity-Bedarf.
2. `RelationshipAgreementModel`: authored Grenzen, Exklusivitätsregeln und mögliche nicht-exklusive Konstellationen.
3. `SocialExchangeEvent`: wann Wissen außerhalb sichtbarer Szenen zwischen Figuren weitergegeben werden darf.
4. `VisualPreferenceModel`: konkrete Achsen, Mindestzahl unabhängiger Beobachtungen, Confidence-Update und Umgang mit widersprüchlicher Evidenz.

### 31.14 Verbindliche Richtung

- Es existieren 32 authorbare männliche beziehungsweise weibliche Character-Schablonen, nicht 32 persistente Personen.
- Ein Save instanziiert daraus sechzehn aktive Fokusfiguren mit allen 16 Personality-Profilen als unterschiedlichen Base-Ausgangspunkten. Die daraus entwickelten Current Profiles dürfen sich später doppeln oder zeitweise fehlen.
- Nicht alle sechzehn aktiven Figuren können in einem Lauf vollständig erkundet werden.
- Jede Figur besitzt eine Friendship- und eine Love-Interest-Route.
- Mehrere Beziehungen dürfen parallel wachsen.
- Mehrere romantische Interessen haben charakter-, wissens- und vereinbarungsabhängige Folgen statt eines pauschalen Strafwerts.
- Alle Teilnehmer einer VN-Szene erhalten explizit markiertes Wissen über beobachtbare Ereignisse.
- NPC-zu-NPC-Wissensfluss verwendet einen sparsamen Social Graph und hardcodiert ausgelöste SocialExchangeEvents.
- Der Prolog bleibt als VN-Rahmen weitgehend gleich, erzeugt aber variable World-, Style-, Uniform-, Taste- und Encounter-Outputs.
- Der AnimeStyleCore bleibt der gemeinsame technische Rahmen; wiederholt positiv bewertete Bilder formen pro Save eine versionierte persönliche Style-Baseline innerhalb dieses Rahmens.
- Bildpräferenzen werden aus wiederholter Evidenz und nicht aus einem einzelnen Vergleich gelernt.
- Taste, Canon Compatibility und technische Generatorqualität bleiben getrennte Bewertungsdomänen.
- LLMs erhalten kleine, rollenreine Kontexte und besitzen keine Wahrheits- oder State-Autorität.

## 32. Spielergeschlecht und geschlechtsspezifischer Cast-Aufbau

### 32.1 Die einzige direkte Geschlechtsfrage betrifft den Spieler

Der Prolog fragt zu Beginn transparent das Geschlecht des Spielercharakters ab:

```text
player_gender: male | female
```

Es folgt keine separate Frage wie „Soll dein Gegenüber männlich oder weiblich sein?“. Das Spiel leitet seine Begegnungsgewichtung unmittelbar aus dem Spielergeschlecht ab:

```text
Spieler männlich
→ überwiegend weibliche aktive Figuren
→ einzelne männliche Figuren im sozialen Kreis

Spieler weiblich
→ überwiegend männliche aktive Figuren
→ einzelne weibliche Figuren im sozialen Kreis
```

Diese Regel ist keine versteckte Präferenzinferenz. Sie ist eine feste Produkt- und Storyprämisse und darf nicht durch das Taste-Modell umgedeutet werden.

### 32.2 32 Schablonen, sechzehn aktive Persönlichkeits-Slots

Die Authoring-Matrix lautet:

| Personality-Slot | männlicher Blueprint | weiblicher Blueprint |
|---|---|---|
| Profile 01 | `profile_01_male` | `profile_01_female` |
| Profile 02 | `profile_02_male` | `profile_02_female` |
| … | … | … |
| Profile 16 | `profile_16_male` | `profile_16_female` |

Pro Save wird für jeden der 16 Personality-Slots genau eine Schablone instanziiert. Das garantiert gleichzeitig:

- alle 16 Personality-Grundprofile im sozialen Kreis,
- einen aktiven Cast von sechzehn Figuren,
- eine klare Mehrheit des anderen Geschlechts,
- und einzelne gleichgeschlechtliche Freundschafts-, Rivalitäts- und Gruppendynamiken.

Der nicht gewählte Gender Blueprint eines Personality-Slots wird in diesem Save nicht als zweite nahezu identische Figur instanziiert. Ein Blueprint trägt keine feste Identität über Saves hinweg; er stellt Grenzen, Ausgangsausprägungen und mögliche Verschiebungen bereit.

### 32.3 Verbindlicher Gender-Korridor

Für jeden Save gilt:

```text
same_gender_count ∈ [0, 4]
opposite_gender_count = 16 - same_gender_count
```

Damit gehören immer mindestens zwölf aktive Fokusfiguren dem anderen Geschlecht an. `12/4` ist der breiteste erlaubte gleichgeschlechtliche Sozialanteil und kein frei überschreitbarer Testwert. Weniger als vier gleichgeschlechtliche Figuren sind zulässig, wenn Story-, Rollen- und Social-Graph-Abdeckung trotzdem kohärent bleiben.

Die null bis vier gleichgeschlechtlichen Slots werden nicht ausschließlich nach Zufall gewählt. Der Cast Assembler berücksichtigt:

- Rolle im Sozialkreis,
- notwendige Freundschafts- und Rivalitätsachsen,
- Clubs und Klassen,
- Event-Abdeckung,
- visuelle Diversity,
- sowie Verbindungen zwischen den aktiven Figuren.

### 32.4 Fokus bedeutet Begegnungsgewicht, nicht sofortigen Route Lock

Figuren des anderen Geschlechts erhalten im Normalfall:

- frühere Reveals,
- mehr persönliche Encounter Slots,
- höhere Wahrscheinlichkeit für Calendar Focus Events,
- und mehr frühe Love-Interest-Signale.

Gleichgeschlechtliche Figuren bleiben dennoch vollwertige Figuren mit eigenem Character Arc, Visual Build Quests und Relationship State. Sie dürfen nicht zu rein funktionalen Sidekicks werden.

Die bestehende Regel gilt für jede aktive Figur: Friendship und Love-Interest-Content sind grundsätzlich vorhanden, unabhängig davon, ob die Figur dem gleichen oder dem anderen Geschlecht angehört. Love Interest wird jedoch erst nach dem verbindlichen Friendship Gate zugänglich. Innerhalb eines konkreten Saves steuert das Encounter Budget den Fokus deutlich zugunsten des anderen Geschlechts; gleichgeschlechtliche Figuren bleiben seltener im frühen Fokus, besitzen aber dieselbe grundsätzliche Route-Tiefe.

### 32.5 Männlich und weiblich sind getrennte Storyrealisierungen

Der gemeinsame Personality-Slot definiert nur die abstrakte charakterliche Grundlogik. Seine beiden Gender Blueprints besitzen unterschiedliche konkrete Abläufe. Nicht ausreichend sind:

- Name und Pronomen auszutauschen,
- denselben Dialog lediglich umzuschreiben,
- dasselbe Outfit anders zu schneiden,
- oder identische Beziehungen auf andere Figuren-IDs zu kopieren.

Pro Blueprint werden mindestens separat festgelegt:

```text
GenderedCharacterBlueprint
├─ personality_profile_id
├─ gender
├─ character_brand_seed
├─ social_role
├─ arc_theme
├─ seasonal_arc_beats[]
├─ relationship_edges[]
├─ friendship_gates[]
├─ romance_gates[]
├─ boundaries_and_expectations[]
├─ visual_seed_constraints
├─ outfit_families[]
├─ pose_and_expression_families[]
└─ gender_specific_scene_contracts[]
```

Gemeinsame abstrakte Eventfunktionen bleiben möglich. Beispielsweise können beide Varianten eines Profiles im Sommerfestival einen Vertrauenskonflikt besitzen, aber Anlass, Inszenierung, Reaktion, Dialog und Folgeereignis müssen nicht gleich sein.

### 32.6 Cast Assembly nach dem Prolog

Der deterministische Ablauf lautet:

```text
Spielergeschlecht wählen
→ Spielernamen erfassen und reservieren
→ `same_gender_count` zwischen null und vier bestimmen
→ `opposite_gender_count` als Rest auf sechzehn setzen
→ für jedes der 16 Personality-Profile Gender Blueprint wählen
→ Social-Role- und Diversity-Constraints prüfen
→ eindeutige Namen aus den geschlechtsspezifischen Pools verteilen
→ erste Encounter-Trias bestimmen
→ nur unmittelbar benötigte Figuren visuell konkretisieren
→ restliche aktive Blueprints als noch nicht visuell gelockte Cast-Plätze speichern
```

Das LLM entscheidet weder Geschlechterzahl noch Personality-Abdeckung. Es formuliert später lediglich strukturierte Details innerhalb des bereits ausgewählten Blueprints.

### 32.7 Auswirkungen auf Bilder und Asset Quests

Der 32er-Katalog verdoppelt nicht automatisch alle vorab zu generierenden Bilder. Da pro Save nur sechzehn Varianten aktiv sind und Figuren Just in Time konkretisiert werden, entstehen Bildquests nur für tatsächlich bevorstehende Reveals und Szenen.

Trotzdem muss jeder Gender Blueprint eigene Prompt- und Recovery-Leitplanken besitzen. Besonders betroffen sind:

- Körper- und Gesichtssilhouette,
- Uniformvariante,
- Freizeitoutfits,
- formelle Kleidung,
- Posen und Körpersprache,
- Interaktion mit Requisiten,
- sowie Composition Templates für Friendship- und Romance-Szenen.

Gemeinsame Places, Hintergründe und neutrale Props bleiben charakter- und geschlechterübergreifend wiederverwendbar.

### 32.8 Auswirkungen auf Social Graph und Wissen

Der Social Graph wird pro Save aus den sechzehn aktiven Varianten kompiliert. Es werden daher weiterhin höchstens 120 aktive Figurenpaare betrachtet, nicht sämtliche 496 möglichen Paare des 32er-Autorenkatalogs.

Blueprints dürfen vorgegebene Beziehungskanten oder Rollenanforderungen besitzen. Der Cast Assembler muss nach der Gender-Auswahl prüfen, ob der aktive Graph weiterhin kohärent ist. Fehlende Gegenkanten werden über authored Alternativen aufgelöst und niemals frei durch ein LLM erfunden.

### 32.9 Verbindliche Richtung

- Der Autorenkatalog enthält 16 männliche und 16 weibliche Character-Schablonen.
- Männliche und weibliche Varianten besitzen konstant unterschiedliche konkrete Storyabläufe.
- Ein Save verwendet sechzehn aktive Figuren und deckt alle 16 Personality-Grundprofile ab.
- Der Spieler wählt nur das eigene Geschlecht.
- Das Spiel fragt nicht nach einem gewünschten Geschlecht der Gegenfiguren.
- Der aktive Cast besteht überwiegend aus Figuren des anderen Geschlechts und aus einzelnen Figuren desselben Geschlechts.
- Höchstens vier aktive Figuren haben dasselbe Geschlecht wie der Spieler; mindestens zwölf haben das andere Geschlecht.
- Der gegengeschlechtliche Fokus wird durch Encounter- und Event-Gewichtung hergestellt.
- Gleichgeschlechtliche Figuren bleiben vollwertige Mitglieder des Sozialkreises.
- Cast Assembly und Route-Verfügbarkeit werden deterministisch gesteuert; kein LLM trifft diese Entscheidungen.

## 33. Japanischer Namenspool und deterministische Namensvergabe

### 33.1 Zweck

Die Character Blueprints besitzen keine fest eingebrannten Namen. Nachdem der Spieler zu Beginn seinen eigenen Namen angegeben hat, verteilt der Cast Assembler zufällig japanische Namen auf die sechzehn aktiven Figuren.

Die Namen werden getrennt gespeichert als:

```text
given_name
family_name
```

Japanische Familiennamen sind nicht geschlechtsspezifisch. Deshalb bestehen drei zentrale Pools:

```text
male_given_names[]
female_given_names[]
family_names[]
```

### 33.2 Der Spielername löst die Vergabe aus

Der Prolog fragt den Spielernamen transparent und vor der ersten konkreten Figurenbegegnung ab. Sinnvoll sind zwei Eingabefelder, auch wenn die Szene sie als eine natürliche Frage inszeniert:

```text
player_given_name
player_family_name
```

Beispielhafte diegetische Formulierung durch die Mutter-Silhouette:

> „Bevor wir die letzten Kartons schließen: Wie soll die Academy deinen Namen in den Unterlagen führen?“

Nach Bestätigung passiert deterministisch:

```text
Spielername normalisieren und reservieren
→ aktiven 16er-Cast fertigstellen
→ Vornamen nach Character-Geschlecht ziehen
→ Familiennamen ziehen
→ Kollisions- und Beziehungsregeln prüfen
→ NameAssignments im Save speichern
→ Character Canon sperren
```

Der Spieler wird nicht gebeten, die anderen Figuren selbst zu benennen. Ihre Namen sollen sich wie ein natürlich vorgefundener sozialer Kreis anfühlen.

### 33.3 Zufällig, aber reproduzierbar

Die Ziehung verwendet einen Save Seed und keine bei jedem Laden neue Zufallsfolge:

```text
name_rng_seed = hash(save_seed, cast_schema_version, name_pool_version)
```

Damit gelten:

- Save und Reload behalten dieselben Namen.
- Tests können denselben Cast reproduzieren.
- Ein neuer Durchlauf kann andere Namen erhalten.
- Änderungen am Namenspool sind durch `name_pool_version` nachvollziehbar.
- Das LLM erfindet oder verändert keine Character-Namen.

Der Spielername dient als Auslöser und Ausschlusswert, nicht als alleiniger Seed. Zwei neue Saves mit demselben Spielernamen sollen nicht zwangsläufig denselben Cast erhalten.

### 33.4 Kollisionsregeln

Für den aktiven Cast gelten zunächst folgende Regeln:

1. Kein NPC erhält exakt denselben vollständigen Namen wie der Spieler.
2. Kein Vorname erscheint innerhalb des aktiven 16er-Casts doppelt.
3. Kein vollständiger NPC-Name erscheint doppelt.
4. Familiennamen bleiben im Normalfall ebenfalls eindeutig.
5. Gleiche Familiennamen sind nur erlaubt, wenn eine authored Familienbeziehung existiert.
6. Unterschiedliche Schreibweisen mit derselben Aussprache werden als mögliche Kollision behandelt.
7. Namen dürfen nicht aufgrund von Personality, Haarfarbe, Körperform oder Romance-Potenzial bevorzugt werden.

Eine bewusste Geschwisterbeziehung reserviert den Familiennamen bereits vor der normalen Ziehung für beide Figuren.

### 33.5 Starter-Pool für männliche Vornamen

Der erste kuratierte Pool kann beispielsweise enthalten:

```text
Akihiro, Akio, Atsushi, Daichi, Daiki, Eiji, Haruki,
Haruto, Hayato, Hideki, Hiroki, Hiroto, Issei, Itsuki,
Jun, Kaito, Kazuki, Kenji, Kenta, Koji, Kosei, Kota,
Makoto, Masato, Minato, Naoki, Ren, Riku, Rintaro,
Ryo, Ryota, Seiji, Seiya, Shin, Shinji, Shota, Shun,
Sota, Taichi, Takumi, Tatsuya, Tomoya, Yuma, Yuto,
Yuji, Yukio, Yusuke
```

Der Produktionspool sollte mindestens 64 kuratierte männliche Vornamen enthalten, damit mehrere Runs nicht zu schnell dieselben Kombinationen erzeugen.

### 33.6 Starter-Pool für weibliche Vornamen

Der erste kuratierte Pool kann beispielsweise enthalten:

```text
Aiko, Akari, Asuka, Ayaka, Ayane, Chika, Emi, Eri,
Fumika, Hana, Haruka, Hikari, Honoka, Kana, Kanna,
Kaori, Karin, Koharu, Mai, Maki, Madoka, Mei, Miku,
Mio, Misaki, Mizuki, Momoka, Nanami, Natsumi, Nozomi,
Reina, Rena, Riko, Rina, Rin, Ruri, Saki, Sakura,
Sayaka, Shiori, Tomomi, Yui, Yuka, Yuna, Yuzuki
```

Auch dieser Produktionspool sollte mindestens 64 kuratierte Einträge besitzen. Namen, die in Japan für mehrere Geschlechter verwendet werden können, dürfen vorkommen, benötigen im Datensatz jedoch eine explizite `gender_usage`-Markierung statt einer ungeprüften Zuordnung.

### 33.7 Gemeinsamer Pool für Familiennamen

Ein gemeinsamer Starter-Pool kann enthalten:

```text
Abe, Aoki, Endo, Fujii, Fujita, Fujiwara, Fukuda, Goto,
Hara, Harada, Hasegawa, Hashimoto, Hayashi, Ikeda, Inoue,
Ishida, Ishii, Ishikawa, Ito, Kato, Kaneko, Kimura,
Kobayashi, Kudo, Maeda, Matsuda, Matsumoto, Miura,
Miyazaki, Mori, Morita, Murakami, Nakagawa, Nakajima,
Nakamura, Nakano, Nishimura, Ogawa, Okada, Okamoto,
Ono, Ota, Sakai, Sakamoto, Sasaki, Sato, Shibata,
Shimizu, Suzuki, Takagi, Takahashi, Takeuchi, Tamura,
Tanaka, Ueda, Uchida, Watanabe, Yamada, Yamaguchi,
Yamamoto, Yamashita, Yamazaki, Yoshida, Yokoyama
```

Der Pool soll größer als die Vornamen-Pools sein und mindestens 96 kuratierte Familiennamen enthalten. Häufigkeit kann optional gewichtet werden, aber eine rein realistische Verteilung darf nicht dazu führen, dass ein großer Teil des Casts denselben Nachnamen erhält.

### 33.8 Datenmodell

Ein Eintrag im Namenspool benötigt mehr als einen freien String:

```json
{
  "name_id": "given_f_001",
  "kind": "given",
  "romanized": "Aiko",
  "kana": null,
  "kanji": null,
  "gender_usage": ["female"],
  "reading_key": "aiko",
  "enabled": true,
  "weight": 1.0,
  "tags": []
}
```

Kanji und Kana bleiben optional, bis ihre konkrete Schreibweise kuratiert wurde. Das System darf nicht automatisch eine beliebige Kanji-Schreibweise aus dem romanisierten Namen ableiten, da derselbe japanische Name unterschiedliche Schreibweisen und Bedeutungen besitzen kann.

Die Zuweisung im Save ist davon getrennt:

```json
{
  "character_instance_id": "save03_character_07",
  "given_name_id": "given_f_001",
  "family_name_id": "family_023",
  "display_order": "family_given",
  "assigned_at": "prologue_name_lock",
  "canon_locked": true
}
```

### 33.9 Anredeformen gehören nicht ins freie LLM

Im japanischen Schulkontext verändert sich die Anrede mit Beziehung und Situation. Deshalb werden zusätzlich deterministische `AddressFormRules` benötigt:

- Familienname ohne oder mit `-san`,
- `-kun`,
- `-chan`,
- Vorname bei größerer Nähe,
- formelle vollständige Namen,
- individuelle Spitznamen,
- sowie bewusst unerwünschte Anreden.

Das Relationship System entscheidet, welche Anrede freigeschaltet ist. Das Figuren-LLM darf nur aus den für die aktuelle Szene erlaubten Formen wählen und keine neue Intimität durch einen erfundenen Spitznamen herstellen.

### 33.10 Reroll und Canon Lock

Vor der ersten Figurenenthüllung darf ein kompletter neuer Save Seed beziehungsweise ein ausdrücklich angebotenes Prolog-Reroll die Namen neu verteilen. Sobald eine Figur vorgestellt, bildlich generiert oder in einer Memory referenziert wurde, ist ihr Name Canon.

Ein späteres Reroll einzelner Namen würde Dialoge, RAG-Chunks, Bildmetadaten und Beziehungserinnerungen inkonsistent machen und ist daher nicht Teil des normalen Spielloops. Eine technische Migration oder explizite Debugfunktion bleibt davon getrennt.

### 33.11 Verbindliche Richtung

- Der Spieler gibt zu Beginn Vor- und Familiennamen an.
- Danach verteilt der Cast Assembler zufällig Namen auf die aktiven Figuren.
- Männliche und weibliche Vornamen kommen aus getrennten kuratierten Pools.
- Familiennamen verwenden einen gemeinsamen geschlechtsneutralen Pool.
- Die Vergabe ist save-seeded und reproduzierbar.
- Spieler- und NPC-Namen werden gegen Kollisionen geprüft.
- Namen sind unabhängig von Personality und visuellen Präferenzen.
- Nach der ersten Enthüllung wird der vollständige Character-Name Teil des Canon Locks.
- Anredeformen und Spitznamen werden durch Relationship State freigeschaltet und nicht vom LLM erfunden.

## 34. Getrennte Character-, Environment-, Style- und Render-Trials

### 34.1 Warum getrennte Modi notwendig sind

Nicht jedes Bildexperiment beantwortet dieselbe Frage. Character- und Story-Progression, ästhetische Style-Findung und technische Render-Optimierung dürfen ihre Evidenz nicht vermischen.

Verbindlich getrennt werden:

1. `CharacterCanonTrial`: Welche Character-Ausprägung oder welches Character Asset soll Canon werden?
2. `EnvironmentBuildTrial`: Welcher reine Background beziehungsweise Place soll für die VN freigeschaltet werden?
3. `StyleDiscoveryTrial`: Welche erlaubte visuelle Handschrift innerhalb des AnimeStyleCore bevorzugt der Spieler?
4. `RenderProfileTrial`: Welche technische Einstellung erzeugt bei gleichem Inhalt die beste stabile Ausbeute?

Alle Modi verwenden Bilder, Ratings und bei ausreichenden Kandidaten ein K.-o.-System. Sie schreiben jedoch in unterschiedliche State- und Evidenzräume.

### 34.2 CharacterCanonTrial

Ein Character Trial ist an genau eine aktive Figur und einen konkreten Visual Need gebunden, beispielsweise:

- Canon Portrait,
- Frisuren- oder Farbkonkretisierung,
- Outfit,
- Pose,
- Expression,
- freigestellter VN Sprite,
- oder Character-bezogenes Story CG.

Die Kandidaten dürfen sich kontrolliert in mehreren fachlichen Merkmalen unterscheiden, solange bestätigte Character Locks erhalten bleiben. Das Ziel ist Auswahl und Canon-Bildung, nicht die Messung eines unveränderten Prompts.

Ein abgeschlossener Character Trial:

- bindet Champion und gegebenenfalls Runner-up an den Character Canon,
- erfüllt ein Visual Requirement,
- kann die nächste Character-VN-Szene freischalten,
- erzeugt Character-spezifische Taste- und Recovery-Evidenz,
- und bewegt damit den Storyfortschritt zu dieser Figur.

Das ausgewählte Bild verändert Relationship-Werte nicht automatisch. Relationship-Fortschritt entsteht durch die zugehörige Storyhandlung; das Bildspiel stellt den dafür benötigten Content bereit.

### 34.3 EnvironmentBuildTrial

Ein Environment Trial verwendet ausschließlich Scenes oder Places ohne integrierte Fokusfigur. Er gilt unter anderem für:

- Umzugszimmer,
- Schulweg,
- Academy Exterior,
- Classroom,
- Clubraum,
- Dach,
- Stadtorte,
- Festivalstraße,
- Strand,
- Schulfahrt-Orte,
- und saisonale Varianten.

Das Hard Constraint `no_character_present` verhindert, dass versehentlich eine unbekannte oder unpassende Figur in einen wiederverwendbaren Background eingebrannt wird.

Ein bestätigter Environment Champion gehört grundsätzlich zum globalen Place Pool des Saves. Er kann von mehreren Figuren und Routen verwendet werden. Der Trial darf eine anstehende VN-Szene freischalten, ist aber nicht Eigentum der gerade beteiligten Figur.

### 34.4 StyleDiscoveryTrial

Ein Style Trial untersucht eine noch offene Achse innerhalb der `StyleDiscoveryEnvelope`. Er kann mit einem Character-Motiv oder einem reinen Environment-Motiv gespielt werden.

Konstant bleiben möglichst:

- dargestelltes Subjekt,
- Scene Intent,
- Canon Locks,
- Seitenverhältnis,
- technische Grundqualität,
- und alle nicht untersuchten Style-Achsen.

Variiert wird gezielt beispielsweise:

- Sättigung,
- Kontrast,
- Linienweichheit,
- Detaildichte,
- Lichtcharakter,
- Hintergrundatmosphäre,
- oder Grad stilisierter Proportionen.

Ein einzelner Style Trial setzt keine globale Wahrheit. Wiederholte Ergebnisse aus Character- und Environment-Motiven erhöhen oder senken die Confidence einer Style-Achse. Erst mehrere unabhängige Trials dürfen eine neue `AnimeStyleProfileRevision` vorschlagen.

### 34.5 RenderProfileTrial

Ein Render Trial optimiert technische Generierungseinstellungen. Dafür bleiben fachlicher Prompt, Visual Specification und Seeds gepaart. Pro Trial wird exakt eine technische Achse verändert:

- Sampler,
- Scheduler,
- Steps,
- CFG,
- Denoise,
- gegebenenfalls Modell- oder Workflow-Revision in einem ausdrücklich dafür vorgesehenen Boss Trial.

Beispiel:

```text
identischer Character Prompt
+ identische vier Seeds
+ identisches Canon- und Style-Profil
+ vier unterschiedliche Sampler
= vergleichbarer Sampler Trial
```

Die Auswertung berücksichtigt:

- Hard-Fail-Rate,
- Usable- und Contender-Rate,
- Character Identity oder Background-Treue,
- StyleProfile-Kompatibilität,
- Paarvergleichsergebnisse je Seed,
- Queue-, Render- und Gesamtzeit,
- sowie brauchbare Bilder pro Minute.

Ein schnelleres Renderprofil darf nur gewinnen, wenn seine Qualität innerhalb des festgelegten akzeptablen Korridors liegt.

### 34.6 Character- und Environment-spezifische Renderprofile

Render Trials existieren in zwei fachlichen Scopes:

```text
character_render_profile
environment_render_profile
```

Ein Character Render Trial misst zusätzlich Identity Consistency, Anatomie und Interaktion mit Outfit, Pose und Expression. Ein Environment Render Trial verwendet `no_character_present` und gewichtet Komposition, Tiefe, Architektur, Wiederverwendbarkeit und saubere Character-Abwesenheit.

Falls einzelne Character-LoRAs nachweislich andere Einstellungen benötigen, darf ein versionierter Character Override entstehen. Ohne ausreichende Evidenz gilt weiterhin das gemeinsame Character Render Profile.

### 34.7 Integration in den Tagesablauf

Style- und Render-Trials bilden einen eigenen spielbaren Laborbereich, werden aber durch den Calendar Director in den Schuljahresloop eingebettet. Sie können erscheinen:

- als Chronicle-Lab-Aufgabe an einem normalen Schultag,
- während ein anderes Story Asset generiert wird,
- als Vorbereitung auf ein kommendes Special,
- nach wiederholtem Artstyle- oder Quality-Drift,
- nach Aktivierung eines neuen Modells oder Workflows,
- oder als regelmäßig angebotene optionale Tagesaktivität.

Ein Lab Trial verbraucht keinen Character Relationship Beat. Jeder Story-Tag behält seine direkte Character-Interaktion; der Trial kann zusätzlich die Build-/Laborhandlung des Tages bilden.

### 34.8 Einheitliches Review-Vokabular

Die sichtbaren und gespeicherten Bewertungen werden vereinheitlicht:

| Aktion oder Status | Bedeutung |
|---|---|
| `skip` | keine sichere Bewertung; erzeugt keine positive oder negative Präferenz-Evidenz |
| `reject` | für das aktuelle Ziel ungeeignet; benötigt mindestens einen Grund und wird für Delete or Live vorgemerkt |
| `keep` | valide und brauchbar; automatisch für einen kompatiblen Challenger-Pool berechtigt |
| `favorite` | klarer Zieltreffer; automatisch challengerberechtigt und stärker als Keep zu gewichten |

`Contender` ist nur die interne Bezeichnung für den daraus abgeleiteten Pool-Eintrag
eines kompatiblen Keeps oder Favorites. Es gibt dafür keine zweite
Spielerentscheidung. `Live Bench` ist keine Reviewwertung.

### 34.9 K.-o.-System pro Trial

Nur transportgültige Keeps und Favorites desselben Trial-Ziels und einer
fachlich vergleichbaren Revision dürfen in ein gemeinsames K.-o.-System gelangen.

Die Standardregel lautet:

```text
0–15 berechtigte Keeps/Favorites → kein Bracket; weitere Vierervergleiche und bei Bedarf Recovery
16 berechtigte Keeps/Favorites   → Round of 16, Viertelfinale, Halbfinale und Grand Final
```

Ein Vierer-Batch kann null bis vier Kandidaten liefern. Jedes kompatible Keep oder
Favorite füllt den Pool; Reject und Skip tun es nicht. Dadurch bleibt die Anzahl
der Runden offen, während das spätere Turnier immer dieselbe verständliche
Struktur besitzt.

### 34.10 Evidenzgrenzen

| Trial | darf schreiben in | darf nicht allein beweisen |
|---|---|---|
| Character Canon | Character Canon, Character Taste, Recovery | technische Prompt-Stabilität |
| Environment Build | Place Canon, Environment Taste, Recovery | Character Preference oder Identity Stability |
| Style Discovery | Style Preference und StyleProfile Confidence | Sampler- oder Workflow-Überlegenheit |
| Render Profile | technische Qualität, Stabilität und Effizienz | allgemeine ästhetische Userpräferenz |

Ein Bild kann mehreren Prüfungen dienen, seine Evidenz muss aber weiterhin an den jeweils konstant gehaltenen Bedingungen und dem ursprünglichen Trial Contract hängen.

### 34.11 Verbindliche Richtung

- Character Progression und technische Renderoptimierung sind getrennte Spielmodi.
- Character Trials bewegen den visuellen und darauf aufbauenden Storyfortschritt einer Figur.
- Reine Environment Trials ohne Figuren erzeugen wiederverwendbare Places und Backgrounds.
- Style Trials lassen den Spieler die visuelle Handschrift innerhalb des festen AnimeStyleCore schrittweise formen.
- Render Trials vergleichen gleiche Prompts und gepaarte Seeds mit kontrolliert veränderten technischen Einstellungen.
- Character und Environment besitzen getrennte Render-Evidenzräume.
- Style- und Render-Labor bleibt ein eigener Bereich, wird aber regelmäßig in Story-Tage integriert.
- Ratings und K.-o.-System verwenden über alle Trial-Arten ein gemeinsames Grundvokabular.

## 35. Konsistenzstand vor der Milestone-Zerlegung

### 35.1 Inzwischen verbindlich geklärt

- Der Spieler wählt sein eigenes Geschlecht; das Spiel fragt kein gewünschtes Geschlecht der Gegenfiguren ab.
- Der aktive Cast besteht primär aus Figuren des anderen Geschlechts und zusätzlich aus einigen gleichgeschlechtlichen Figuren.
- Höchstens vier der sechzehn aktiven Fokusfiguren besitzen dasselbe Geschlecht wie der Spieler.
- Der Prolog ist eine authored VN-Szene mit Erzähler, Mutter-Silhouette und überwiegend festen Choices; allgemeiner freier Character Chat folgt erst später.
- Die 32 Gendered Blueprints sind Schablonen und keine über Saves hinweg fest identischen Personen.
- Die vorhandenen Spieler- und NPC-Porträts liefern einen authored visuellen Bootstrap; die Mutter kann zunächst als Silhouette inszeniert und später mit demselben Portrait vollständig gezeigt werden.
- Jeder der 16 aktiven Personality-Slots besitzt ein festes, zunächst verborgenes Base Profile und einen unveränderlichen Base Axis Vector.
- Userentscheidungen verändern Current Axes, Ausdruck und Beziehung einzeln und gewichtet; Current Types können dadurch innerhalb des geschlossenen 16er-Systems wechseln.
- Nicht kompatibler Einfluss kann Vertrauen beschädigen, eine Route stagnieren lassen und eine andere Figur stärker in den Fokus bringen.
- Jede aktive Figur besitzt Friendship- und Love-Interest-Content.
- Love Interest wird erst nach einem authored Friendship Gate zugänglich.
- Character-, Environment-, Style- und Render-Trials sind getrennte Spielmodi mit getrennten Evidenzräumen.
- Reine Scenes ohne Figuren werden als wiederverwendbare Environment Assets erspielt.
- Style- und Render-Labor ist ein eigener Bereich, wird aber in den Tagesablauf integriert.
- Das Review-Grundvokabular und die K.-o.-Reduktion sind vereinheitlicht.
- Storyzeit schreitet nicht nach einer festen Bildzahl fort. Ein Scene Unlock benötigt Calendar-, Scene-Asset-, Focus-Character-Play- und gegebenenfalls Ensemble-Development-Freigabe.
- Das Scene Asset Gate produziert ausschließlich das Material der bevorstehenden Szene; das Focus Character Play Gate entwickelt die fokussierte Figur unabhängig davon über aktuelle Challenges weiter.
- Eine Fokus-Szene darf sichtbar blockiert bleiben, bis authored Mindest-Milestones benötigter Supporting Characters erreicht sind.
- Ein Vierervergleich wird so oft wiederholt, bis sechzehn vom Spieler bestätigte, technisch zulässige Kandidaten für die konkrete Situation vorliegen; erst dann beginnt das K.-o.-Spiel.

### 35.2 Inhaltliche Entscheidungen, die vor belastbaren Milestones noch fehlen

#### A. Protagonisten-Portraitvertrag

- Wählt der Spieler eines der acht vorhandenen Porträts direkt oder dienen sie nur als verdeckte visuelle Präferenzanker?
- Wird die gewählte Darstellung sofort Canon oder später durch eine individuelle generierte Variante ersetzt?
- Welche zusätzlichen Protagonistenassets werden jenseits eines Gesprächsporträts für VN- und Gruppenszenen benötigt?

#### B. Template-Instanziierungsvertrag

- Welche Ausgangsachsen und Grenzwerte besitzt jede der 32 Schablonen?
- Welche Brand-Bausteine werden fest durch die Schablone vorgegeben und welche pro Save kombiniert?
- Welche konkreten Gewichtsklassen, Blueprint-Modifikatoren und maximalen Turn-Deltas gelten für die vier Current Axes?
- Welche globalen Schablonendaten werden klar von Name, Bild-Canon, Relationship State und Save-Erinnerungen getrennt?

#### C. Sharing-Grenze der männlichen und weiblichen Variante

- Welche Arc-Themen, Calendar Functions und Relationship Gates dürfen geteilt werden?
- Welche Szenenketten, Konflikte, Social Edges und Outcomes müssen zwingend getrennt authored werden?

#### D. Prologumfang und konkrete Outputs

- minimale Zahl authored Szenen und Preference Probes, die nötig ist, um die Start-Story loszutreten,
- welche World-, Uniform- und Style-Requirements dadurch erzeugt werden,
- welches erste Portrait beziehungsweise welche visuelle Identität zwingend vor einer Begegnung oder Chat-Interaktion vorliegen muss,
- und welcher konkrete Asset-Ready-Zustand den nächsten Progressionsschritt freigibt.

#### E. Style Discovery Contract

- vollständige Liste erlaubter Style-Achsen,
- Grenzen des unveränderlichen AnimeStyleCore,
- Mindestzahl unabhängiger Style Trials,
- Confidence und Revision,
- globale Werte gegenüber Character- oder Environment-spezifischen Ausnahmen,
- sowie Gewichtung, Alterung und Widerspruchsbehandlung positiver Bildratings für die persönliche Style-Baseline.

#### F. Tages- und Jahresökonomie

- erwartete Zahl realer Sessions pro Schuljahr,
- Darstellung von höchstens sechs normalen Ready-Games pro bekannter Figur,
  zusätzlichen Games je aktiver sensibler Inhaltseinstellung und separat
  bereitstehenden 16er-Cups,
- Häufigkeit optionaler Style-/Render-Trials,
- Verhältnis von Routine, Character Focus und Bildreview,
- sowie Queue-, Backpressure- und Abbruchregeln, weil Zeitbedarf und Bildmenge pro Storytag bewusst vom nächsten Scene Contract abhängen.

#### G. Visual-Quest-Tiefe und LoRA-Zeitpunkt

- alle turnierrelevanten Situationen sammeln über wiederholte Vierervergleiche genau sechzehn bestätigte Kandidaten; offen ist noch, welche Asset Requirements überhaupt ein eigenes Turnier statt Wiederverwendung benötigen,
- welche Assets zusätzlich einen Stability Trial benötigen,
- wann eine Figur ihr erstes LoRA benötigt,
- und ob frühe VN-Szenen mit Referenz- statt LoRA-Workflow laufen dürfen.

#### H. Fail-Forward bei blockierenden Visual Gates

- Anzahl aufeinanderfolgender Vierer-Batches ohne neuen Contender vor einer stärkeren Revision,
- erlaubte Änderung von Prompt, Recipe, Workflow oder Visual Specification,
- Verhalten bei wiederholtem technischem Scheitern,
- und ob es einen sicheren Ersatz-, Verschiebe- oder Diagnosepfad gibt, ohne ein schlechtes Bild als Champion zu akzeptieren.

#### I. Ausgelieferter Bootstrap Content

- authored Story-, Calendar-, Personality- und Blueprint-Daten,
- die zwölf geprüften freigestellten Spieler- und NPC-Porträts aus `D:\Dropbox\Favs`,
- noch fehlende neutrale Prolog-, Zimmer-, Academy- und World-Hintergründe,
- vollständig leere persönliche Playground-/Combo-Datenbanken,
- sowie Trennung zwischen globaler technischer Evidenz und save-spezifischem Canon.

#### J. Story-Authoring-Economy

- Zahl wirklich einzigartiger Szenen pro Character Blueprint,
- Anteil parameterisierter Daily Eventfamilien,
- Mindestzahl persönlicher Milestones für eine vollständige Route,
- Verteilung der 24 Specials auf Fokus-, Ensemble- und World Events,
- sowie Umfang authored NPC-zu-NPC- und Knowledge-Propagation-Events.

### 35.3 Noch offene Kalibrierungen, aber keine Konzeptblocker

Diese Punkte dürfen als technische Spikes oder Playtest-Milestones gelöst werden:

- Auswahlalgorithmus für null bis maximal vier gleichgeschlechtliche Cast-Slots,
- konkretes lokales Character-Speaker-Modell,
- lokales Prompt-Generator-Modell und Gemini-Fallback,
- konkrete Text- und Image-Embedding-Modelle,
- Vector-Store-Technik,
- genaue Preference-Confidence-Schwellen,
- endgültige Größe der Namenspools,
- genaue Renderzeit-Grenzen,
- sowie UI-Animationen und finale Präsentationsdetails.

### 35.4 Empfohlener nächster Deep Dive

Der unmittelbar wichtigste Deep Dive ist jetzt der `Asset Readiness Contract`: Welche maschinell prüfbaren Bedingungen besitzt ein Portrait, Sprite, Outfit, Place und vollständiger Scene Contract, und wann darf der Time Director deshalb fortschreiten?

Danach folgt die `Story-Authoring-Economy`. Erst wenn feststeht, welche Inhalte zwischen Personality Core, männlicher beziehungsweise weiblicher Schablone, Daily Eventfamilie und Friendship-/Romance-Route geteilt werden dürfen, lässt sich der reale Contentumfang der 32 Schablonen und 168 Story-Tage abschätzen.

## 36. Vorhandener Portrait-Bootstrap, Schablonenmodell und asset-gebundene Zeitprogression

### 36.1 Geprüfter Bestand in `D:\Dropbox\Favs`

Der Ordner enthält zwölf freigestellte Anime-Porträts mit echtem Alpha-Kanal. Alle vier Bildecken besitzen Alpha `0`; die Dateien eignen sich deshalb grundsätzlich für VN-Compositing vor wechselnden Hintergründen.

| Gruppe | Dateien | Maße | vorgesehene Rolle |
|---|---|---:|---|
| Spieler, Blau | `player_portrait_blue_female.png`, `player_portrait_blue_male.png` | weiblich `1087×2007`, männlich `1401×2048` | kühle, ruhigere Player-Archetypen |
| Spieler, Grün | `player_portrait_green_female.png`, `player_portrait_green_male.png` | jeweils `1401×2048` | natürliche, zugängliche Player-Archetypen |
| Spieler, Rot | `player_portrait_red_female.png`, `player_portrait_red_male.png` | jeweils `1401×2048` | energische, expressive Player-Archetypen |
| Spieler, Gelb | `player_portrait_yellow_female.png`, `player_portrait_yellow_male.png` | jeweils `1401×2048` | helle, offene Player-Archetypen |
| Mutter | `npc_mother.png` | `1664×2432` | authored Mutter-Portrait |
| weitere NPCs | `npc_ramdom_1.png`, `npc_wurzelheim_1.png`, `prof_wuka_portrait.png` | jeweils `1664×2432` | authored Supporting-NPC-Porträts |

Die acht Spielerbilder decken je Spielergeschlecht vier klar unterscheidbare visuelle Richtungen ab und können deshalb den Protagonisten bereits vor eigener Generierung sichtbar machen. Noch zu entscheiden ist, ob der Spieler eine Variante explizit wählt, sie indirekt aus Prologantworten erhält oder ob die vier Bilder lediglich Ausgangsanker für eine generierte individuelle Fassung sind.

`npc_mother.png` ist bereits ein vollständiges Portrait und keine reine Silhouette. Für den vagen Prolog wird keine zweite Datei benötigt: Die Runtime kann dasselbe Portrait zunächst als dunkle Silhouette, weich maskiert oder stark entsättigt darstellen und die vollständige Fassung später freigeben.

Die vier NPC-Dateien und acht Spielerdateien besitzen eine gemeinsame saubere Anime-VN-Richtung, unterscheiden sich aber leicht in Detailgrad, Linienführung und Shading. Sie sind daher sowohl Bootstrap Assets als auch sinnvolle erste Referenzen für Style-Evidence. Die abweichende Größe von `player_portrait_blue_female.png` muss beim Import über normierte Anchor-, Bounding-Box- und Display-Height-Werte ausgeglichen werden.

Der Ordner enthält **keine Hintergründe**. Umzugszimmer, Stadt, Academy, Klassenraum, Schulweg und weitere Places bleiben deshalb offene Bootstrap Requirements.

### 36.2 Die 32 Blueprints sind Schablonen, keine Figuren

Das Datenmodell trennt künftig strikt drei Ebenen:

```text
PersonalityCore
→ stabile Grundlogik eines der 16 Profile

GenderedCharacterTemplate
→ männliche oder weibliche Schablone
→ Ausgangsausprägungen, erlaubte Verschiebungen, Grenzen und Reaction Contracts

CharacterInstance
→ konkrete Person dieses Saves
→ Name, Character Brand, Aussehen, Beziehungen, Erinnerungen und Bild-Canon
```

Eine Schablone enthält mindestens:

```text
GenderedCharacterTemplate
├─ template_id
├─ personality_core_id
├─ gender
├─ starting_axis_ranges
├─ allowed_development_ranges
├─ hard_behavior_boundaries
├─ authored_reaction_table
├─ compatible_brand_modules[]
├─ incompatible_brand_combinations[]
├─ friendship_gate_templates[]
├─ romance_gate_templates[]
└─ gender_specific_scene_functions[]
```

Die verschiedenen Ausprägungen dürfen sich im Laufe des Schuljahres durch Beziehung, VN- und Character-Chat-Inputs, Konflikte, Erlebnisse und authorisierte Memory-Impulse auf einzelnen Achsen verschieben. Das Base Profile bleibt Herkunft und Rückanker; das Current Profile darf beim Überschreiten einer Achsenmitte in einen anderen der 16 zulässigen Typen wechseln. Die Entwicklung wird nicht frei vom LLM erfunden und darf weder die harten Character-Grenzen noch die vierachsige Personality-Topologie verlassen. Das LLM formuliert nur die für den aktuellen State zulässige Oberfläche.

### 36.3 Cast-Regel

Der aktive Cast besitzt weiterhin sechzehn Figuren und deckt alle 16 Personality Cores als Base-Ausgangspunkte genau einmal ab. Diese Base-Coverage bleibt bestehen, auch wenn sich Current Profiles später doppeln oder zeitweise fehlen. Das Geschlecht des Spielercharakters setzt den Korridor:

```text
Spieler männlich → 0 bis maximal 4 weitere männliche Figuren
Spieler weiblich → 0 bis maximal 4 weitere weibliche Figuren
Rest            → Figuren des jeweils anderen Geschlechts
```

Damit existieren immer mindestens zwölf Figuren des anderen Geschlechts. Wie viele der erlaubten null bis vier gleichgeschlechtlichen Slots tatsächlich belegt werden, entscheidet der Cast Assembler anhand authored Rollen-, Freundschafts-, Rivalitäts-, Club-, Event- und Social-Graph-Constraints. Das LLM entscheidet diese Verteilung nicht.

### 36.4 Prolog erzeugt Requirements statt sofort alle Figuren zu zeigen

Der Prolog muss nur lang genug sein, um die Start-Story kontrolliert loszutreten. Er muss noch keine erste Begegnung mit einer Fokusfigur enthalten.

Seine Mindestfunktion lautet:

```text
authored Einzugsszene starten
→ Spielergeschlecht und Spielername binden
→ indirekte optische und inhaltliche Präferenzsignale sammeln
→ erste World-, Uniform-, Style- und Player-Visual-Requirements erzeugen
→ benötigte Build Games in die Queue stellen
→ auf Asset Readiness des nächsten Story Contracts warten
```

Eine fest vorgegebene Zahl von Prologszenen, Bildern oder Minuten ist nicht die Endbedingung. Der Director beendet die Prologphase, sobald die notwendige Startinformation erhoben und der nächste valide Build-/Storyschritt bestimmt ist.

### 36.5 Minimale visuelle Identität pro bekannter Figur

Eine Figur darf dem Spieler nicht als bloßer Name in einem Character Chat begegnen. Bevor sie als bekannt gilt, benötigt sie mindestens ein freigegebenes Identitätsportrait:

```text
unknown
→ portrait_ready
→ introduced
→ known
```

Für mögliche Interaktionen gelten danach abgestufte Gates:

| Interaktion | minimale Assets |
|---|---|
| Handy-/Text-Chat | freigegebenes Identitätsportrait |
| kurzer Live-Chat | Identitätsportrait plus kompatibler Place oder bewusst neutraler authored Chat-Hintergrund |
| standardisierte VN-Szene | benötigtes Sprite/Portrait, Expression, Outfit und Place laut Scene Manifest |
| Focus Event oder CG | vollständiges event-spezifisches Visual Manifest einschließlich Champion- und Zusatzprüfungen |

Fehlt außer dem Portrait weiteres Material, darf die Figur gegebenenfalls per Handy erreichbar bleiben. Fehlt selbst das Portrait, wird weder eine VN- noch eine Character-Chat-Interaktion freigeschaltet.

### 36.6 Interaktionsmöglichkeit bei jeder Time Progression

Bei jedem neuen Time Window erzeugt der Interaction Director für jede bereits bekannte Figur mindestens einen zulässigen Kontaktkanal, sofern kein authored Abwesenheits-, Konflikt- oder Story Lock dagegensteht:

- persönliche VN-Interaktion am selben Ort,
- standardisierte kurze VN-Interaktion,
- Live-Chat,
- oder Handy-Chat bei räumlicher Trennung.

Das bedeutet nicht, dass der Spieler in einem Zeitfenster automatisch alle sechzehn Interaktionen ausführt. Es bedeutet, dass jede bekannte Figur eine nachvollziehbare `InteractionAvailability` erhält und nicht ohne State-Grund verschwindet. Auswahl, Zeitbudget und Konsequenzen bestimmen, welche Kontakte tatsächlich stattfinden.

### 36.7 Scene-Asset-Vorbereitung innerhalb der Time Progression

Die Menge der benötigten Bilder und die reale Dauer eines Storytages sind variabel. Für das Scene Asset Gate entscheidet ausschließlich, was der nächste konkrete Scene Contract benötigt. Seine Erfüllung ist notwendig, aber allein nicht hinreichend für Storyfortschritt.

```text
Story Director wählt zulässigen nächsten Beat
→ Scene Visual Manifest auflösen
→ vorhandene freigegebene Assets wiederverwenden
→ fehlende Asset Requirements als Build Quests erzeugen
→ währenddessen nur bereits asset-kompatible Kontakte anbieten
→ AssetReadinessService prüft das vollständige Manifest
→ `scene_asset_ready = true` setzen
→ vollständigen SceneUnlockContract mit allen vier Gates auswerten
→ erst bei `scene_unlock_ready = true` Storyzeit fortschreiben
```

Das Scene Asset Gate wird nicht nach vier Runden, sechzehn Rohbildern oder einer festen Wartezeit freigegeben, sondern erst bei zuverlässig verwendbarem Material. Die Story selbst schreitet zusätzlich nur fort, wenn Calendar Gate, Focus Character Play Gate und Ensemble Development Gate desselben `SceneUnlockContract` erfüllt sind.

### 36.8 Der Code besitzt die Readiness-Autorität

Der Spieler bewertet Bilder und liefert insbesondere semantische Hinweise wie falsche Hände, Wrong Artstyle, komischer Hintergrund, Character Drift oder „nur ganz nett“. Der Spieler bestätigt aber nicht manuell den technischen Storyfortschritt.

Der `AssetReadinessService` berechnet ausschließlich den Zustand des Scene Asset Gates aus prüfbaren Daten. Die übrigen Gates werden von den jeweils zuständigen deterministischen Director- und State-Reducer-Komponenten ausgewertet:

```text
AssetReadiness
├─ file_exists_and_decodes
├─ expected_format_and_dimensions
├─ aspect_ratio_and_safe_area_valid
├─ alpha_contract_valid, falls erforderlich
├─ no_active_delete_or_quarantine_reason
├─ player_review_complete
├─ contender_and_tournament_state_valid
├─ champion_validation_passed
├─ identity_canon_version_matches
├─ outfit_place_expression_versions_match
├─ style_baseline_version_compatible
├─ workflow_or_lora_requirement_satisfied
└─ scene_manifest_complete
```

Die Readiness ist damit deterministisch reproduzierbar. Der Code kann sowohl vollautomatische Prüfungen als auch bereits gespeicherte Spielerreviews auswerten; entscheidend ist, dass ein User ein Story Gate nicht durch ein bloßes „passt schon“ umgehen kann und dass kein LLM die Freigabe setzt.

### 36.9 Persönliche Style-Baseline

Jeder Save besitzt genau eine aktive, versionierte Style-Baseline. Sie wird primär aus wiederholt positiv bewerteten, technisch gültigen Bildern gelernt:

```text
valides positives Rating
→ Evidence für tatsächlich sichtbare Style-Achsen
→ Confidence über mehrere Figuren, Places, Seeds und Tage erhöhen
→ PlayerStyleBaseline Revision N
→ neue Prompts halten stabile Achsen und variieren nur offene Achsen kontrolliert
```

So darf jeder Spieler eine andere visuelle Richtung entwickeln, ohne dass der Stil bei jeder Generierung beliebig springt. Technische Fehler werden nicht als Geschmacksurteil missverstanden. Ein Bild mit gewünschter Farbwirkung und falschen Händen kann Style-Evidence liefern, bleibt aber als Asset ungültig.

Es existieren nicht mehrere gleichzeitig konkurrierende Prompt Styles. Eine Revision ersetzt kontrolliert die vorherige aktive Baseline; ältere Revisionen bleiben für Recovery und Vergleich nachvollziehbar.

### 36.10 Verbindlicher Vierervergleich bis zum Sechzehnerpool

Für jedes turnierpflichtige Asset Requirement gilt folgende State Machine:

```text
confirmed_candidate_count = 0

while confirmed_candidate_count < 16:
    vier neue Bilder erzeugen
    Import- und Hard-Constraint-Preflight ausführen
    Vierervergleich spielen
    jedes Bild als favorite, keep, reject oder skip bewerten
    nur technisch zulässige, kompatible favorites/keeps zum Pool hinzufügen
    Ratings, Fehlergründe, Renderzeit und Recovery-Evidenz speichern
    bei schlechter Trefferquote Prompt/Recipe kontrolliert reparieren

confirmed_candidate_count == 16
→ K.-o.-Feld mit 16 Teilnehmern erzeugen
→ Round of 16
→ Viertelfinale
→ Halbfinale
→ Finale
→ Champion validieren
→ Asset an Story Contract binden
```

Wichtige Konsequenzen:

- Die Zahl der Viererrunden und Rohbilder ist variabel.
- Vier Runden sind nur das mathematische Minimum.
- `reject`, `skip` und ungeklärte Reviews füllen keinen Kandidatenplatz.
- Ein Fehlbild zählt auch dann nicht, wenn seine übrige Optik dem Spieler gefällt.
- Eine schlechte Runde wird als Evidenz behalten; der Loop läuft weiter und wird nicht als wertlos verworfen.
- Ändert Recovery einen relevanten Canon- oder Style-Contract, müssen bereits gesammelte Kandidaten gegen den neuen `CandidateCompatibilityHash` revalidiert werden.
- Wird während des K.-o.-Turniers nachträglich ein harter Fehler entdeckt, wird das Bild invalidiert, der Queststatus kehrt zum Qualifier zurück und der Pool wird wieder auf sechzehn gültige Kandidaten aufgefüllt, bevor das betroffene Bracket neu gestartet wird.

### 36.11 Aktuell noch echte offene Punkte

Nach den neuen Festlegungen bleiben vor einer belastbaren Milestone-Zerlegung vor allem diese Verträge offen:

1. **Player Portrait Selection:** direkte Wahl aus vier geschlechtskompatiblen Bildern, indirekte Ableitung oder Nutzung als Generierungsanker.
2. **Background Bootstrap:** welche authored neutralen Räume zwingend mit dem Spiel ausgeliefert werden, da `Favs` ausschließlich freigestellte Figuren enthält.
3. **Template Axes:** genaue Ausgangsachsen, Verschiebungsräume und harten Grenzen der 32 Schablonen.
4. **Readiness Schema:** exakte maschinelle Felder und Grenzwerte pro Portrait, Sprite, Outfit, Place und CG.
5. **Visual QA Scope:** welche Fehler automatisch erkannt werden können und welche über gespeicherte Spielerreviews in die Codefreigabe eingehen.
6. **Interaction Budget:** wie viele der grundsätzlich verfügbaren bekannten Figuren der Spieler pro Time Window tatsächlich kontaktieren darf.
7. **Tournament Recovery:** nach wie vielen erfolglosen Vierer-Batches eine stärkere Prompt-, Recipe-, Modell- oder Workflow-Revision erzwungen wird.
8. **LoRA Gate:** ab welchem Figuren- und Assetstand Referenz-Workflows nicht mehr reichen und ein Character-LoRA erforderlich wird.
9. **Style Learning:** konkrete Achsen, Confidence-Schwellen, Gewichtung, Alterung und bewusste Revision der persönlichen Baseline.
10. **Cast Slot Selector:** authored Priorität, nach der null bis maximal vier gleichgeschlechtliche Figuren auf die Personality-Slots verteilt werden.

## 37. Parallele Character Quests, Champion Challenges und Visual-Progress-Gates

### 37.1 Vier unabhängige Gates für VN-Fortschritt

Ein VN-Schritt wird nicht allein dadurch freigeschaltet, dass alle benötigten Dateien existieren. Jeder progressionsrelevante `SceneUnlockContract` besitzt vier voneinander unabhängige Freigabedomänen:

```text
Calendar Gate
→ authored Zeitpunkt, Storyphase und Eventfenster sind erreicht

Scene Asset Gate
→ ausschließlich die Visual Requirements der bevorstehenden Szene sind verwendbar und codevalidiert
→ besitzt keine feste Rundengrenze und läuft bis zur Vollständigkeit

Focus Character Play Gate
→ aktuelle, characterbezogene Challenges gegen bereits existente Assets, Canon References und Recipes der Fokusfigur
→ ist ausdrücklich unabhängig vom Assetbedarf der bevorstehenden Szene
→ je nach Scene Contract und Character-Confidence null bis drei verlangte Playgate-Runden innerhalb einer VN-Runde
→ Pflicht- und freiwillige Character Trials teilen dasselbe Dreiermaximum

Ensemble Development Gate
→ alle authored Mindest-Milestones benötigter Supporting Characters sind erfüllt

Calendar Gate
AND Scene Asset Gate
AND Focus Character Play Gate
AND Ensemble Development Gate
→ VN-Progress freigeben
```

Scene-Asset-Runden und Focus-Character-Play-Runden sind getrennte Budgets. Notwendige Build Games, Qualifier und Recovery laufen so lange, bis für jedes blockierende Requirement ein akzeptierter und technisch validierter `APPROVED` Champion vorliegt, und verbrauchen keinen der höchstens drei Playgate-Plätze. Das Focus Character Play Gate fordert nur dann aktuelle Qualitäts-, Stability-, Profile- oder Champion-Challenges der Fokusfigur, wenn der Scene Contract oder ihre aktuelle Character-/Assetrollen-Confidence eine konkrete offene Frage benennt.

Nicht nur die erste Runde, sondern jeder Routine-VN-Schritt mit bereits bewährtem Profil darf `0` Pflicht-Trials besitzen. Neue Assetrollen, niedrige Confidence, eine neue Workflow-/Modell-/LoRA-/Renderprofilrevision oder eine besondere Character-Challenge können ein bis drei Runden verlangen. Auch bei `0` Pflicht-Trials bleiben freiwillige Character Trials bis zum gemeinsamen Dreierlimit möglich. Der vollständige Vertrag steht in [`../sources/generation-profiles-and-trials.md`](../sources/generation-profiles-and-trials.md).

### 37.2 Quest, Game Run und Progress Credit sind getrennte Objekte

Damit der Fortschritt später eindeutig berechnet werden kann, werden drei Ebenen unterschieden:

```text
VisualQuest
→ persistentes Ziel mit fachlichem Kontext
→ zum Beispiel „Schulportrait: Sampler Clash“

GameRun
→ eine konkret gespielte Einheit innerhalb der Quest
→ zum Beispiel ein vollständig bewerteter Vierervergleich oder eine K.-o.-Runde

PlayGateRoundCredit
→ vom Code ausgestellter Nachweis, dass ein gültiger Challenge-Run für genau ein aktuelles VN Progress Window zählt
```

Eine Quest darf aus mehreren Game Runs bestehen. Ein normaler Vierer-Game-Run
besitzt zwei Durchgänge: zuerst werden alle vier Bilder einzeln mit
`Favorite | Keep | Reject | Skip` bewertet; danach wird jedes nicht
übersprungene Bild erneut einzeln groß gezeigt und über kontextuelle positive
und negative Reason Chips ohne Freitext begründet. Erst wenn diese zweite
bildweise Runde und die vorgesehenen Vergleiche abgeschlossen sind, ist der Run
vollständig dispositioniert. Gründe werden nicht für alle vier Bilder
gemeinsam gesetzt; Batchmuster entstehen ausschließlich als Codeprojektion der
vier Einzelereignisse. Einzelne Klicks, bereits alte Ratings oder das bloße
Starten einer Generierung erzeugen keinen Credit.

Jeder Reason gehört unabhängig von seiner sichtbaren Familie genau einer
Bewertungsebene an: `generation_intent`, `visual_defect`, `character_canon`,
`asset_usability` oder `aesthetic_preference`. Mehrere Ebenen dürfen am selben
Bild gleichzeitig positive und negative Evidence tragen. Insbesondere sind ein
falscher Scene-Inhalt, ein technisch defekt gerenderter richtiger Background und
ein sauberer, aber nicht bevorzugter Background verschiedene Befunde mit
verschiedener Recovery-Autorität.

Auch ein sauber abgeschlossener Vierervergleich ohne neuen Contender kann einen Playgate-Credit liefern, weil er echte negative Evidenz und eine erfolgreiche Champion-Verteidigung darstellt. Er erfüllt jedoch niemals ein fehlendes Asset Gate. Derselbe Experiment- und Batch-Hash darf für dasselbe VN Progress Window nicht mehrfach Credits erzeugen.

### 37.3 Rotierender Questvorrat pro bekannter Figur

Der historische Foundation-Stand mit drei Versorgungskarten ist keine
Zielobergrenze. Im vollständigen MVP hält der Scheduler für jede **bekannte
Figur** höchstens sechs vollständig gerenderte normale Vierer-Games bereit.
Zusätzlich steht für jede aktive sensible beziehungsweise NSFW-
Inhaltseinstellung genau ein eigener Viererbatch dieser Figur bereit:

```text
CharacterQuestSupply
├─ normal_ready_games[0..6] → jeweils validierte 4/4 Bilder
├─ content_ready_game[active_content_setting_id] → jeweils validierte 4/4 Bilder
└─ ready_tournaments[] → aus bereits vorhandenen Kandidaten
```

Die sechs normalen Foki rotieren deterministisch zwischen Scene Asset,
Identity/Stability, Outfit/Pose/Expression/Scene, Auswahl/Champion,
Recovery/Cleanup und Experiment/Coverage/Continuity. Storybedarf, offene
Evidenzlücken, Fehlercluster, Confidence, Datasetwert, Generierungszeit und
Recency bestimmen die Rotation. Ein LLM besitzt keine Auswahl- oder
Credit-Autorität.

Bei sechzehn bekannten Figuren kann der vollständig vorgewärmte normale Vorrat
somit `16 × 6 × 4 = 384` Bilder enthalten. Jede aktive sensible Inhaltsstufe
ergänzt bis zu `16 × 1 × 4 = 64` Bilder und besitzt getrennte Candidate Pools,
Ratings und Champions. Ein 16er-Cup darf zusätzlich bereitstehen, weil er aus
bereits gerenderten Kandidaten besteht und keine vier neuen Bilder verlangt.

Ein Scene-Fokus ist außerdem kein einzelner Vierervergleich. Er kann ein
vollständiges Asset Gate mit mehreren Asset Requirements und beliebig vielen
notwendigen Build-Runden repräsentieren. Er bleibt fokussiert, bis sein Scene
Contract vollständig ist oder der Story Director den Pfad authored verwirft
beziehungsweise verschiebt.

Character-unabhängige Environment-, Style- und Render-Quests stehen im selben vorbereiteten Questökosystem, besitzen aber einen globalen statt characterbezogenen Owner Scope.

Der vollständige Spielmoduskatalog und die bildweise zweite Begründungsrunde
stehen in
[`../sources/game-modes-and-guided-evidence.md`](../sources/game-modes-and-guided-evidence.md).

#### Game Mode und Generierungsfokus

Der `GameMode` beschreibt ausschließlich die Spielerinteraktion. Jede
generierende Quest bindet ihn an genau einen primären `GenerationFocus` mit
Primary Question, Expected Composition Manifest, Locked/Varied Axes, Evidence
Scope und Recovery Routes. Ein Vierer-Qualifier kann dadurch einen Outfit-
Fokus besitzen, eine Arena einen Sampler-Fokus und ein Error Hunt einen Anatomy-
Recovery-Fokus.

Allgemeine sichtbare Fehler bleiben unabhängig vom Fokus erfassbar, erhalten
aber keinen kausalen Credit für eine nicht getestete Achse. Auswahlspiele auf
bereits vorhandenen Bildern wie 16er-Cup, Dataset Draft, Clone Hunt und Delete
or Live besitzen keinen neuen Generation Focus und deklarieren stattdessen einen
`EvaluationFocus`. Weder UI-Route noch LLM dürfen einen Focus implizit erfinden.

### 37.4 Jede Challenge-Variante ist eine eigene Quest

Die Challenge-Modi werden nicht als versteckte Parameterwechsel innerhalb einer generischen Quest behandelt. Jede kontrollierte Hypothese erzeugt eine eigene, sichtbare Quest mit eigenem Contract und eigener Evidenz:

| Questart | kontrollierte Varianz | möglicher Titel |
|---|---|---|
| Seed Gauntlet | Seeds bei gleicher Recipe | Reliability Evidence, Asset Challenger |
| Sampler Clash | Sampler und gegebenenfalls Scheduler | Recipe Champion |
| Step/CFG Trial | Steps, CFG oder vergleichbare Renderparameter | Recipe Champion |
| Prompt Weight Trial | definierte Prompt- oder LoRA-Gewichte | Recipe- oder Asset Challenger |
| Canon Defense | Pose, Expression, Licht oder Kamerawinkel bei gesperrter Identität | Canon Stability, Asset Challenger |
| Style Challenge | einzelne noch offene Style-Achsen | Style Evidence, gegebenenfalls Style-Revision |
| Recovery Revenge | gezielte Reparatur wiederkehrender Fehler | Recovery Recipe, Asset Challenger |
| Context Challenge | neuer Scene-Kontext bei vorhandener Figur oder vorhandenem Place | kontextspezifischer Asset Champion |

Ein Sampler Clash und ein Prompt Weight Trial dürfen deshalb gleichzeitig als getrennte vorbereitete Quests existieren. Ihre Ergebnisse schreiben in getrennte Evidenzräume und werden erst dann gemeinsam als Challenger betrachtet, wenn sie denselben fachlichen `ChallengeContextHash` erfüllen.

Eine vorbereitete Quest durchläuft zwei Vorstufen:

```text
planned
→ Contract aus dem aktuellen Canon-, Champion-, Style- und Story-State kompiliert

prewarmed
→ mindestens der nächste benötigte Vierer-Batch oder Spielzustand wurde erzeugt und ist unmittelbar spielbar
```

Der `PrewarmScheduler` startet erst nach dem Prolog und erst dann, wenn die für eine Challenge benötigten Ausgangsassets existieren. Er hält bevorzugt genügend aktuelle Playgate-Optionen spielbereit, damit der Spieler innerhalb einer VN-Runde aus sinnvollen Challenges wählen kann. Das bloße Vorwärmen zählt nicht als gespielte Runde.

### 37.5 Challenge Contract

Jede Challenge deklariert vor der Generierung verbindlich:

```text
ChallengeContract
├─ quest_id
├─ owner_scope
├─ champion_type
├─ champion_id
├─ context_key
├─ locked_axes[]
├─ varied_axes[]
├─ allowed_ranges{}
├─ hard_constraints[]
├─ target_evidence_domains[]
├─ contender_pool_id
├─ eligible_progress_contract_ids[]
└─ completion_rules
```

`locked_axes` müssen zwischen Champion und Challenger identisch bleiben. `varied_axes` sind die bewusst untersuchten Unterschiede. Ein Ergebnis darf nur den im Contract genannten Titel verändern:

- Ein besserer Sampler kann `Recipe Champion` werden, ohne automatisch das gebundene Storybild zu ersetzen.
- Ein besseres Bild kann `Asset Champion` werden, ohne den Character Canon umzuschreiben.
- Eine Development- oder Seasonal-Variante wird ein neuer Kontext und ersetzt keinen früheren zeitlich korrekten Champion.
- Eine Style Challenge liefert zunächst Evidence; eine saveweite Style-Revision benötigt wiederholte Bestätigung über mehrere fachliche Kontexte.

### 37.6 Persistenter Challenger Pool über mehrere Quests

Die sechzehn Herausforderer müssen nicht in einer einzigen Sitzung und nicht aus nur einem Spielmodus entstehen. Kompatible Einzelquests dürfen über mehrere Storytage hinweg Kandidaten in denselben versionierten Challenger Pool schreiben:

```text
Seed Gauntlet       → 3 bestätigte Challenger
Sampler Clash       → 2 bestätigte Challenger
Prompt Weight Trial → 4 bestätigte Challenger
Canon Defense       → 3 bestätigte Challenger
weitere Quests      → 4 bestätigte Challenger
Gesamt              → 16 bestätigte Challenger
```

Sobald der sechzehnte kompatible und aktuell rosterfähige Challenger sein
persistiertes Eligibility-Ereignis erhält, werden diese ersten sechzehn Einträge
atomar eingefroren und der `Challenger Cup` als Pflichtquest bereitgestellt.
Ihre Eligibility-Reihenfolge bestimmt reproduzierbar die Bracketplätze. Später
berechtigte Challenger bleiben für den folgenden Cup im Pool; es gibt keine
nachträgliche Score-, Rematch- oder Spieler-Kuration des fertigen Feldes:

```text
16 Challenger
→ Round of 16
→ Viertelfinale
→ Halbfinale
→ Challenger Final
→ Challenger Champion
→ blindes Title Match gegen den amtierenden Champion
```

Der amtierende Champion ist nicht Teil des Sechzehnerfeldes. Er verteidigt seinen Titel erst gegen den bereits qualifizierten Challenger Champion. Dadurch kann ein etablierter Champion nicht durch einen einzelnen zufälligen Erstvergleich verloren gehen.

Diese Wartephase definiert den gemeinsamen `ChampionCycleCooldown`: ein
vollständiger Challenger-Cup bis zum nächsten Title Match. Ein Favorite pausiert
nach seiner ersten und zweiten Niederlage jeweils exakt denselben Zyklus; die
Sperre wird mit der Verlustzahl nicht länger. Nach Niederlage drei folgt Delete
or Live. Ein dort per `Live` gerettetes Bild bleibt Favorite, setzt aktuelle
Verlustserie und Cooldown auf null und erhält ein neues Eligibility-Ereignis für
einen späteren Cup. Match-, Verlust- und DOA-Historie bleiben erhalten; das
bereits eingefrorene Bracket bleibt ausgeschlossen.

Mögliche Ausgänge:

- `incumbent_defended`: bisheriger Champion bleibt aktiv,
- `challenger_provisional_win`: Challenger muss abschließende Stability- und Readiness-Prüfung bestehen,
- `challenger_promoted`: neuer aktiver Champion mit vollständiger Lineage,
- `not_comparable`: Challenge Context war falsch oder zu breit,
- `no_champion_quality`: kein schlechter Ersatz wird erzwungen; Recovery folgt.

Ändern sich Canon, Style, Outfit oder ein anderer gesperrter Contractbestandteil, werden alle Poolkandidaten anhand ihres `ChallengeContextHash` revalidiert. Inkompatible Kandidaten bleiben als Evidenz erhalten, zählen aber nicht mehr zu den sechzehn aktiven Herausforderern.

### 37.7 Scene Unlock Contract pro VN-Runde

Der Zeitraum zwischen zwei VN-Fortschritten wird als `VNProgressWindow` gespeichert. Jeder freischaltbare VN-Schritt besitzt einen `SceneUnlockContract`, der alle Freigabedomänen zusammenführt, ohne ihre Zustände zu vermischen:

```text
SceneUnlockContract
├─ scene_unlock_contract_id
├─ vn_progress_window_id
├─ scene_id
├─ story_beat_id
├─ focus_character_id
├─ supporting_character_ids[]
├─ calendar_gate
│  ├─ required_calendar_state
│  └─ status
├─ scene_asset_gate
│  ├─ visual_manifest_id
│  └─ status
├─ focus_character_play_gate
│  ├─ required_rounds: 0..3
│  ├─ completed_rounds: 0..3
│  ├─ optional_rounds_used: 0..3
│  ├─ total_rounds_used: 0..3
│  ├─ calibration_questions[]
│  ├─ required_quest_categories[]
│  └─ source_state_revision
├─ ensemble_development_gate
│  └─ participant_requirements[]
├─ relationship_gate_ids[]
├─ knowledge_gate_ids[]
└─ completion_state
```

`focus_character_play_gate.required_rounds` liegt zwischen null und drei. Die konkrete Zahl wird aus Scene Contract, Storyfunktion, Character- und Assetrollen-Confidence sowie einer kleinen hardcodierten Preset-Tabelle bestimmt und niemals vom LLM erfunden. Pflicht- und freiwillige Trials überschreiten zusammen nie drei. Scene-Asset-Runden besitzen dagegen kein numerisches Maximum: Jedes verpflichtende Requirement läuft über Viererbatches, den Sechzehnerpool, K.-o.-Turnier, Champion-Validierung und notwendige Recovery bis zu einer `APPROVED` AssetVersion.

Beispiele für Presets, deren Zahlen noch per Playtest kalibriert werden:

| Progressionstyp | Scene Asset Gate | Focus Character Play Gate |
|---|---|---|
| erste Runde nach dem Prolog | alle ersten Requirements müssen gebaut werden | `0`, solange noch keine sinnvolle Calibration-Frage existiert |
| kurze Routine-VN | vorhandene kompatible Assets genügen | `0–1` nur bei konkreter offener Confidence |
| Character-Fortschritt | alle Character Requirements ready | `0–3` Character-, Canon-, Profile- oder Stability-Runden |
| neues Outfit oder neuer Place | neuer Champion zwingend; Build läuft bis vollständig | `0–3` zusätzliche Trials nur bei getrennter Character-Frage |
| Special Event | vollständiges Entry Manifest; unbegrenzte notwendige Build-Runden | `0–3` diverse aktuelle Playgate-Runden |
| Route Milestone | Character- und Scene-Manifest vollständig | `0–3`, darunter gegebenenfalls Canon Defense oder Title Match |

Build-, Qualifier-, Turnier- und Recovery-Runden zählen ausschließlich zum Scene Asset Gate und werden nicht auf die höchstens drei Character-Playgate-Runden angerechnet. Dadurch bleibt die Produktionsarbeit unbegrenzt bedarfsorientiert, während der zusätzliche Character-Challenge-Anteil pro VN-Runde überschaubar bleibt. Challengefähige Assets allein erzwingen keine Runde; der Contract verlangt null bis drei aktuelle Champion-, Recipe-, Canon-, Profile- oder Stability-Challenges nur bei einer benannten offenen Frage.

### 37.8 Relevanz, Verbrauch und Anti-Grind-Regeln

Playgate-Credits sind nicht frei zwischen beliebigen Figuren und VN-Runden austauschbar. Ein Credit zählt für das Focus Character Play Gate nur, wenn alle folgenden Bedingungen erfüllt sind:

- `owner_character_id` entspricht exakt `focus_character_id`,
- die Challenge betrifft ein Asset, eine Canon Reference, eine Recipe, einen LoRA-Stand oder eine Stability-Frage dieser Fokusfigur,
- der Quest Contract wurde aus der aktuellen Character-, Canon- und Champion-Revision kompiliert,
- der Game Run wurde vollständig gespielt und ausgewertet,
- und der Run gehört nicht zum Scene Asset Gate der kommenden Szene.

Globale Environment-, Style- oder Render-Quests sowie Challenges anderer Figuren dürfen parallel existieren und ihre eigenen Evidenz- oder Challenger-Pools fortschreiben. Sie erfüllen das Focus Character Play Gate der aktuellen Fokusfigur nur, wenn sie vorab ausdrücklich an genau diese Figur, Quest, State Revision und Calibration-Frage gebunden wurden; ihre bloße globale Existenz erzeugt keinen Credit.

Credits werden bei der Freischaltung eines VN-Schritts dem aktuellen `VNProgressWindow` fest zugeordnet und können nicht ein zweites Mal ausgegeben werden. Playgate-Quests werden immer aus dem zu Beginn dieses Windows aktuellen State kompiliert. Dadurch können keine alten Challenge-Runs vorproduziert und für spätere Storyphasen gehortet werden.

Nach jedem VN-Fortschritt erhöht der Director die `source_state_revision`. Noch nicht gespielte vorbereitete Quests werden dagegen geprüft:

- weiterhin exakt kompatibel: für das neue Window neu zuordnen und gegebenenfalls weiter vorwärmen,
- nur mit aktualisierten Locks kompatibel: Quest Contract neu kompilieren,
- durch neuen Champion, Canon oder Style überholt: alte Quest als Evidenzversion archivieren und aktuelle Quest erzeugen.

Der Prewarm-Vorgang beginnt unmittelbar nach dem Prolog, sobald die ersten challengefähigen Assets freigegeben sind. Im ersten Asset-Aufbau kann die Playgate-Liste deshalb noch leer sein. Nach Abschluss der ersten visuellen Baseline erzeugt der Scheduler die ersten aktuellen Challenge-Quests für die zweite VN-Runde.

Die Playgate-Questgenerierung bevorzugt fachlich nützliche Aufgaben der Fokusfigur anhand von:

- Alter und Qualitätsabstand bestehender Champions,
- geringer Recipe- oder Identity-Stabilität,
- neuen Samplern, Modellen oder Workflow-Revisionen,
- wiederkehrenden Fehlerclustern,
- offenen Style-Achsen,
- offenen Character-Outfits, Posen, Expressions und Canon-Stresstests,
- sowie Lücken im LoRA-Dataset.

Damit sind die verpflichtenden Spiele keine zufällige Beschäftigungstherapie. Jeder Playgate-Run challengt eine reale Qualitätsannahme oder verbessert die langfristige technische Produktionsbasis der Fokusfigur; die kommende Szene selbst wird ausschließlich über das getrennte Scene Asset Gate gebaut.

### 37.9 Save- und UI-Zustand

Questfortschritt gehört zur serialisierbaren Simulation und nicht zur UI:

```text
VisualQuestState
├─ quest_id
├─ owner_character_id oder global_scope
├─ is_story_priority
├─ ready_slot_index: null | 1..6
├─ content_setting_id oder null
├─ quest_kind
├─ status: planned | prewarming | prewarmed | active | completed | stale | archived
├─ challenge_contract_id
├─ source_state_revision
├─ eligible_vn_progress_window_id
├─ completed_game_runs[]
├─ issued_playgate_round_credits[]
├─ contender_ids[]
├─ evidence_event_ids[]
└─ created_from_story_contract_id
```

Die Hauptoberfläche zeigt für jede bekannte Figur den aktuellen rotierenden
Vorrat aus höchstens sechs normalen vollständig gerenderten Vierer-Games,
zusätzlichen Games aktiver sensibler Inhaltseinstellungen und gegebenenfalls
einem separat bereitstehenden 16er-Cup. Storypriorität, Playgate-Credit und
SceneAssetGate werden dabei getrennt markiert. Eine zusätzliche Questansicht
enthält geplante beziehungsweise noch nicht vollständig vorgewärmte Character-,
Environment-, Style-, Render- und Recovery-Quests. Jede Karte nennt:

- fachliches Ziel,
- herausgeforderten Champion beziehungsweise fehlendes Asset,
- bewusst variierte Achsen,
- nächsten spielbaren Modus,
- aktuellen Kandidaten- oder Stage-Fortschritt,
- Character-Owner und langfristige Challenge-Linie,
- sowie getrennt davon die VN-Schritte, deren Focus Character Play Gate sie erfüllen kann.

Der Scene-Unlock-Bereich zeigt alle vier Gates getrennt. Das Focus Character Play Gate umfasst null bis drei Pflicht-Trials und insgesamt höchstens drei Pflicht- plus freiwillige Runden; das Scene Asset Gate bleibt ohne Rundenmaximum geöffnet, bis alle Pflichtrequirements einen validierten `APPROVED` Champion besitzen. Das VN-Gate kann beispielsweise anzeigen:

```text
Calendar Gate:              bereit
Scene Asset Gate:           4 / 4 Requirements bereit
Asset Build Runs:           11 gespielt, kein festes Maximum
Focus Character Play Gate:  2 / 2 aktuelle Character-Challenges
Ensemble Development Gate:  1 / 2 Supporting Characters bereit

Blocker:
→ Ren benötigt noch den Milestone „Club-Einstieg“
→ Zu Rens verfügbarer Progression
```

### 37.10 Verbindliche Richtung und verbleibende Kalibrierung

Verbindlich sind jetzt:

- höchstens sechs normale vollständig gerenderte Ready-Games pro bekannter
  Figur sowie je aktiver sensibler Inhaltseinstellung ein zusätzliches eigenes
  Game mit getrenntem Pool, Rating und Champion,
- ein zusätzlich bereitstehender 16er-Cup, sobald genügend kompatible bereits
  gerenderte Kandidaten existieren,
- separate Questinstanzen für Sampler-, Weight-, Canon-, Style-, Recovery- und Context-Challenges,
- ein deutlich größerer parallel vorbereiteter Questpool über Figuren, Places, Styles, Recipes und Workflows hinweg,
- null bis drei verlangte Playgate-Runden und ein gemeinsames Maximum von drei Pflicht- plus freiwilligen Character Trials pro VN Progress Window,
- Playgate-Runden zählen ausschließlich für die jeweilige Fokusfigur und bleiben unabhängig von den Assets der kommenden Szene,
- unbegrenzt viele notwendige Scene-Asset-Runden bis zur vollständigen Materialfreigabe,
- eine mögliche erste VN-Runde ausschließlich mit Scene Asset Gate,
- Start des Challenge-Prewarmings erst post-Prolog und nach Verfügbarkeit erster challengefähiger Assets,
- Just-in-time-Kompilierung der Playgate-Quests aus dem aktuellen State,
- persistente Challenger Pools über mehrere Quests und Storytage,
- sechzehn bestätigte Challenger vor dem Challenger Cup,
- anschließendes separates Title Match gegen den amtierenden Champion,
- Calendar Gate, Scene Asset Gate, Focus Character Play Gate und Ensemble Development Gate als unabhängige VN-Progressionsbedingungen,
- authored Mindestentwicklungen anderer Figuren als zulässige Blocker einer Fokus-Szene,
- klare Blockerhinweise mit fehlender Figur, konkretem Milestone und direktem Progressionsziel,
- sowie verpflichtende Challenge-Anteile nur bei einer konkreten offenen Character-, Profile- oder Confidence-Frage, auch wenn benötigte Assets bereits existieren.

Noch zu kalibrieren sind:

1. konkrete Zahl zwischen null und drei Playgate-Runden pro Routine-, Character-, Special- und Route-Progression,
2. genaue Auswahl, welche der bis zu sechs spielbereiten Character-Challenges
   in einem VN Window Credit anbieten beziehungsweise verlangt werden,
3. wie viele zusätzliche Questdefinitionen nur `planned` sein dürfen und wie
   der Sechser-Vorrat fair über sechzehn bekannte Figuren vorgewärmt wird,
4. Prioritätsverteilung der sechs rotierenden Funktionsgruppen auf mögliche
   nächste Szenen, Evidenzlücken, Recovery und Datasetwert,
5. ob eine vollständige K.-o.-Runde oder ein Title Match genau eine oder eine besonders gewichtete Playgate-Runde darstellt,
6. Schwellenwert, ab dem ein alter Champion aktiv eine Defense Quest erhält,
7. sowie Revalidierungs- und Aufbewahrungsdauer vorbereiteter, aber durch State-Fortschritt überholter Quests.

### 37.11 Character Development und Ensemble Requirements

Supporting Characters werden nicht über einen einzigen pauschalen Levelwert geprüft. Jede Figureninstanz besitzt einen zusammengesetzten, serialisierbaren Entwicklungsstand:

```text
CharacterDevelopmentState
├─ character_id
├─ introduction_state: unknown | portrait_ready | introduced | known
├─ narrative_milestone_ids[]
├─ visual_development_tier
├─ relationship_state_revision
├─ knowledge_state_revision
├─ participated_event_ids[]
└─ development_revision
```

Eine Ensemble-Szene deklariert für jede benötigte Supporting Figure einen konkreten authored Vertrag:

```text
ParticipantRequirement
├─ character_id
├─ required_introduction_state
├─ required_narrative_milestone_ids[]
├─ minimum_visual_development_tier
├─ relationship_gate_ids[]
├─ required_knowledge_ids[]
├─ required_participated_event_ids[]
└─ status: satisfied | blocked
```

Das `EnsembleDevelopmentGate` ist nur erfüllt, wenn sämtliche `ParticipantRequirements` erfüllt sind. Der visuelle Mindeststand einer Supporting Figure ersetzt dabei nicht deren konkrete Assets im Scene Asset Gate: Soll die Figur sichtbar in der Szene auftreten, müssen ihre benötigten Sprites, Outfits und Expressions zusätzlich im Scene Manifest freigegeben sein.

Die Entwicklung anderer Figuren erfolgt über deren eigene VN-, Focus-Character-Play- und Milestone-Fortschritte. Eine Challenge der Supporting Figure darf nicht nachträglich als Playgate-Runde der aktuellen Fokusfigur umgedeutet werden. Stattdessen bleibt die Fokus-Szene blockiert, bis der Spieler die betreffende Figur auf ihrem eigenen Pfad ausreichend entwickelt hat.

Beispiel:

```text
Aiko · Gruppenarbeit im Bibliotheksraum

Calendar Gate:             erfüllt
Scene Asset Gate:          erfüllt
Aiko Play Gate:            2 / 2 erfüllt
Ensemble Development Gate: blockiert

Mei → „First Trust“ erfüllt
Ren → „Club Introduction“ fehlt
```

Der UI-Blocker nennt immer:

- die blockierende Figur,
- den fehlenden authored Milestone beziehungsweise State,
- eine diegetische Kurzbeschreibung,
- und einen direkten Link zu aktuell verfügbaren Szenen oder Quests, die diese Figur weiterentwickeln können.

Sobald der fehlende State erreicht ist, wertet der Director denselben `SceneUnlockContract` erneut aus. Sind alle vier Gates erfüllt, wird die Szene ohne zusätzliche künstliche Warte- oder Grindbedingung freigeschaltet.

### 37.12 Abhängigkeitsgraph und Schreibautorität

Alle `ParticipantRequirements` werden als gerichteter Story-Abhängigkeitsgraph pro Kapitel und Calendar Window kompiliert. Vor Freigabe der authored Daten prüft ein deterministischer Validator:

- keine unerfüllbare direkte oder indirekte Zykluskette,
- mindestens einen vom aktuellen State erreichbaren Entwicklungspfad zu jeder blockierenden Figur,
- zeitliche Verfügbarkeit der benötigten Milestones vor Ablauf des Scene Windows,
- konsistente Character-, Relationship-, Knowledge- und Event-IDs,
- sowie passende Supporting-Character-Rollen im Scene Contract.

Eine Fokus-Szene darf blockiert bleiben, während der Spieler über andere verfügbare Character-Szenen die benötigten Figuren entwickelt. Der Director muss dafür mindestens einen authored erreichbaren Pfad anbieten. Ein technischer oder inhaltlicher Zyklus wird nicht durch automatische Levelerhöhung, erfundene Memories oder stilles Überspringen eines Gates repariert.

Der hardcodierte Story Director und seine validierten Reducer besitzen alleinige Autorität über Requirements, Development States und Scene Unlocks. Character Speaker, Prompt Generator, RAG, Embedding-Suche und Frontend dürfen weder Milestones erfinden noch Gates erfüllen oder umgehen.

## 38. Verbindliches Personality-Koordinaten-, Entwicklungs- und Beziehungssystem

Dieser Abschnitt ist der autoritative Personality-Vertrag. Bei widersprüchlichen älteren Formulierungen in diesem Dokument gilt die hier festgelegte Trennung zwischen Base-Herkunft, langfristiger Achsenentwicklung, daraus abgeleitetem Current Type und kurzfristigem Ausdruck.

### 38.1 Geschlossene Topologie aus sechzehn Profilen

Das Spiel verwendet genau vier kontinuierliche Achsen:

| Achse | Wert `-1` | Wert `+1` | Bedeutung |
|---|---|---|---|
| `social_energy` | I | E | Rückzug und innere Verarbeitung gegen aktive soziale Energie |
| `information_focus` | S | N | konkrete Wahrnehmung gegen abstrakte Muster und Möglichkeiten |
| `decision_orientation` | T | F | sachlogische Abwägung gegen werte- und beziehungsbezogene Abwägung |
| `structure_preference` | J | P | Struktur und Festlegung gegen Offenheit und flexible Anpassung |

Jeder Achsenwert liegt im geschlossenen Bereich `[-1.0, +1.0]`. Die vier Vorzeichen ergeben genau einen der sechzehn zulässigen Typencodes. Ein Wert von exakt `0.0` behält den zuvor gültigen Pol, bis die Achse tatsächlich auf die Gegenseite wechselt. Initiale Base-Werte dürfen deshalb niemals exakt null sein.

Der optionale Assertive-/Turbulent-Wert ist ein Intensitäts-, Stress- oder Entwicklungsmodifikator außerhalb dieser Topologie. Er erzeugt weder weitere Profile noch eine fünfte Distanzachse der 16er-Matrix.

Die vier Farbgruppen sind ausschließlich abgeleitete Darstellungs- und Contentlabels. Sie werden aus dem jeweiligen Typcode bestimmt und besitzen keine eigene Nähe-, Kompatibilitäts- oder Relationship-Wirkung.

### 38.2 Verbindliche Personality-State-Ebenen

```text
BasePersonalityProfile
└─ unveränderlicher Typencode beim Cast Assembly

BaseAxisVector
└─ unveränderliche Ausgangswerte der vier Achsen

DevelopedAxisVector
└─ langfristig veränderliche Werte derselben vier Achsen

CurrentPersonalityProfile
└─ jederzeit aus dem DevelopedAxisVector abgeleiteter aktueller Typ

PersonalityExpressionState
└─ kurzfristiger Ausdruck für den aktuellen Turn oder die aktuelle Szene

PersonalityHistory
└─ Achsenbewegungen, Stabilisierungen, Memory-Impulse und Typübergänge
```

`BasePersonalityProfile` und `BaseAxisVector` werden niemals überschrieben. Sie dokumentieren Herkunft, Ausgangsstärke und den Referenzpunkt, zu dem starke Base-nahe Erinnerungen eine Figur später wieder hinziehen können.

Der `DevelopedAxisVector` ist die langfristige Gegenwart der Figur. Das `CurrentPersonalityProfile` ist kein separat frei setzbares Feld, sondern eine deterministische Ableitung seiner vier Pole. Überschreitet eine Achse die Mitte, wechselt der Current Type unmittelbar zum direkten Nachbartyp. Der Wechsel gilt ab dem folgenden Turn für Behavior-, Friendship-, Love-, Konflikt- und Scene Contracts.

Der `PersonalityExpressionState` darf den aktuellen Typ weder ersetzen noch selbst einen Typwechsel auslösen. Er beschreibt, wie Current Personality, Stress, Vertrauen, Umgebung und Gesprächskontext gerade sichtbar werden.

Jeder der sechzehn aktiven Character-Slots besitzt zu Save-Beginn ein anderes Base Profile. Nur diese Base-Coverage bleibt dauerhaft vollständig. Current Profiles entwickeln sich pro Figur unabhängig und dürfen sich daher doppeln oder zeitweise im Cast fehlen. Es gibt keine Ausgleichslogik, die eine andere Figur verschiebt, um die aktuelle 16er-Verteilung künstlich zu erhalten.

Die Spielerfigur erhält kein `BasePersonalityProfile`, keinen `DevelopedAxisVector` und keinen Typencode aus diesem System. Ihr `ProtagonistBehaviorState` bleibt eine getrennte Sammlung tatsächlicher Handlungs- und Kommunikationsmuster.

### 38.3 PersonalityInputContract

Jeder gültige Personality-relevante VN- oder Character-Chat-Input besitzt vor seiner Auswertung einen versionierten Vertrag:

```text
PersonalityInputContract
├─ contract_id und contract_version
├─ source_mode: vn_choice | character_chat
├─ primary_axis
├─ allowed_intents[]
├─ direction: toward_negative | toward_positive | stabilize_current
├─ weight_class: weak | standard | strong | anchor
├─ influence_bound: compatible | stretch | resistant | core_violation
├─ resolved_reaction: accepted | negotiated | resisted | memory_dominated
├─ relationship_modifier_policy
├─ blueprint_modifier_policy
├─ maximum_turn_delta
└─ allowed_secondary_stabilizations[]
```

Pro Turn darf genau eine primäre Achse verschoben werden. Weitere Achsen dürfen nur stabilisiert werden. Stabilisierung bedeutet einen begrenzten Impuls vom Mittelpunkt weg in Richtung des bereits gültigen Pols; bei exakt null gilt der zuletzt gültige Pol. Dadurch kann ein einzelner Turn höchstens einen Wechsel zu einem direkten Nachbartyp auslösen.

Die Gewichtsklassen besitzen eine feste Rangfolge, aber versionierbare konkrete Balancewerte:

| Klasse | Typischer Einsatz |
|---|---|
| `weak` | kleiner Alltags- oder Chatimpuls |
| `standard` | klare authored VN-Choice oder eindeutiger wiederholter Chatintent |
| `strong` | bedeutendes Character Event oder Personality Trial |
| `anchor` | besonders prägende Memory oder authored Milestone-Wirkung |

Relationship State und Blueprint-Leitplanken skalieren die Stärke und lösen aus dem authored `influence_bound` eine konkrete Reaktion auf. `compatible` führt standardmäßig zu `accepted`, `stretch` zu `negotiated` und `resistant` beziehungsweise `core_violation` zu `resisted`; ein ausreichend starker gültiger Memory-Anker kann stattdessen `memory_dominated` erzeugen. Der Director darf diese Zuordnung anhand der im Contract erlaubten Relationship- und Memory-Regeln präzisieren, aber die deklarierte Richtung nicht still umkehren:

- `accepted`: Bewegung in Richtung des Userintents,
- `negotiated`: schwächere Bewegung in Richtung des Userintents,
- `resisted`: keine Bewegung in Intent-Richtung; stattdessen Stabilisierung des bestehenden Pols und mögliche Relationship Tension,
- `memory_dominated`: der authorisierte Memory-Impuls überwiegt den aktuellen Userimpuls.

Alle konkreten Gewichtswerte, Multiplikatoren und maximalen Turn-Deltas sind versionierte Balance-Daten. Verbindlich bleiben ihre Reihenfolge, der Turn-Cap und die Beschränkung auf eine primäre Achse.

Bildratings, Menünutzung, Navigation, visuelle Taste-Evidence und reine Fokuswahl verändern keine Personality-Achse, sofern ein authored Story Contract sie nicht ausdrücklich als Personality-relevanten Input deklariert.

Für freie Character-Chat-Antworten legt der `ChatTurnContract` unsichtbar die primäre Achse und eine begrenzte Menge zulässiger Intents fest. Eine validierte Interpretation ordnet die Userantwort einem dieser Intents zu. Ungültiger, uninterpretierbarer oder nicht zum Contract gehörender Text erzeugt `no_evidence` und damit weder Verschiebung noch Stabilisierung. Das Character Dialogue LLM darf Interpretation, Achsenwert, Gewicht, Typwechsel oder Relationship-Wirkung nicht verbindlich festlegen.

### 38.4 Memory-Impulse und Base-Rückanker

Eine Memory darf langfristige Personality-Entwicklung beeinflussen, wenn sie einen authorisierten Achsenanker besitzt:

```text
MemoryPersonalityAnchor
├─ memory_id
├─ axis
├─ anchor_value oder anchor_direction
├─ weight_class
├─ emotional_salience
├─ repetition
├─ validity und story_scope
└─ source_personality_revision
```

Die wirksame Stärke berücksichtigt mindestens:

- emotionale Bedeutung,
- Wiederholung und Aktualität,
- Relationship State und Vertrauen,
- damaligen Personality-Zustand,
- Nähe des Memory-Ankers zum Base Profile oder zu einem späteren Entwicklungsstand,
- aktuellen Story-, Konflikt- und Stresskontext,
- sowie Blueprint- und Influence-Bound-Regeln.

Eine Base-nahe Erinnerung kann den Developed Axis Vector zurück in Richtung des Base Axis Vector ziehen. Eine spätere prägende Erinnerung darf stattdessen einen bereits entwickelten Zustand stabilisieren. Überschreitet der resultierende Memory-Impuls eine Achsenmitte, wird der Current Type nach denselben Regeln unmittelbar neu abgeleitet.

Embedding-Ähnlichkeit entscheidet ausschließlich, welche Memories als Kandidaten abgerufen werden. Sie erzeugt selbst keinen Achsenimpuls. Der Game Director prüft Scope, Gültigkeit, Knowledge, Widerspruchsfreiheit und gespeicherten Achsenanker und schreibt erst danach ein autorisiertes State Event. Character Speaker, Playground Author und Retrieval-System besitzen keine Personality-Schreibautorität.

### 38.5 Behavior Contract nach einer Entwicklung

Der Behavior Contract eines folgenden Turns entsteht aus:

```text
Current Personality Behavior Pack
+ kontinuierliche Stärken des DevelopedAxisVector
+ Base-Herkunft und PersonalityHistory
+ Character Brand und Character Arc
+ authorisierte Memories
+ Relationship State
+ Scene, Stress und aktueller PersonalityExpressionState
= konkreter Behavior Contract des Turns
```

Ein Typwechsel setzt keine Relationship-Werte, Memories, Knowledge Records, Character Brand, Grenzen, Versprechen, Route Flags oder Character-Arc-Beats zurück. Er verändert ab dem folgenden Turn ausschließlich die typbezogene Gewichtung und die daraus authored zulässigen Ausdrucksvarianten.

Achsen nahe null gelten als schwach ausgeprägt. Das neue Behavior Pack wird zwar unmittelbar aktiv, seine achsenspezifischen Unterschiede werden in diesem Grenzbereich jedoch gedämpft. Dadurch führt der Wechsel eines Typcodes nicht zu einem abrupten Austausch der Figur.

Friendship-, Love- und Konfliktszenen verwenden weiterhin denselben Relationship State, erhalten aber die zum Current Profile, zur kontinuierlichen Achsenstärke und zum bisherigen Arc passende Variante. Ein Wechsel kann neue Reaktions- oder Entwicklungsmöglichkeiten öffnen, erfüllt allein jedoch kein Relationship Gate und widerruft kein bestehendes Einverständnis oder Versprechen.

### 38.6 Vollständige strukturelle 16×16-Matrix

Die folgende symmetrische Matrix enthält die Hamming-Distanz der vier Typbuchstaben:

- `0`: identischer Typ,
- `1`: direkter Nachbar mit genau einer unterschiedlichen Achse,
- `2`: zwei unterschiedliche Achsen,
- `3`: drei unterschiedliche Achsen,
- `4`: vollständiger Gegenpol.

| Typ | INTJ | INTP | ENTJ | ENTP | INFJ | INFP | ENFJ | ENFP | ISTJ | ISFJ | ESTJ | ESFJ | ISTP | ISFP | ESTP | ESFP |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| INTJ | 0 | 1 | 1 | 2 | 1 | 2 | 2 | 3 | 1 | 2 | 2 | 3 | 2 | 3 | 3 | 4 |
| INTP | 1 | 0 | 2 | 1 | 2 | 1 | 3 | 2 | 2 | 3 | 3 | 4 | 1 | 2 | 2 | 3 |
| ENTJ | 1 | 2 | 0 | 1 | 2 | 3 | 1 | 2 | 2 | 3 | 1 | 2 | 3 | 4 | 2 | 3 |
| ENTP | 2 | 1 | 1 | 0 | 3 | 2 | 2 | 1 | 3 | 4 | 2 | 3 | 2 | 3 | 1 | 2 |
| INFJ | 1 | 2 | 2 | 3 | 0 | 1 | 1 | 2 | 2 | 1 | 3 | 2 | 3 | 2 | 4 | 3 |
| INFP | 2 | 1 | 3 | 2 | 1 | 0 | 2 | 1 | 3 | 2 | 4 | 3 | 2 | 1 | 3 | 2 |
| ENFJ | 2 | 3 | 1 | 2 | 1 | 2 | 0 | 1 | 3 | 2 | 2 | 1 | 4 | 3 | 3 | 2 |
| ENFP | 3 | 2 | 2 | 1 | 2 | 1 | 1 | 0 | 4 | 3 | 3 | 2 | 3 | 2 | 2 | 1 |
| ISTJ | 1 | 2 | 2 | 3 | 2 | 3 | 3 | 4 | 0 | 1 | 1 | 2 | 1 | 2 | 2 | 3 |
| ISFJ | 2 | 3 | 3 | 4 | 1 | 2 | 2 | 3 | 1 | 0 | 2 | 1 | 2 | 1 | 3 | 2 |
| ESTJ | 2 | 3 | 1 | 2 | 3 | 4 | 2 | 3 | 1 | 2 | 0 | 1 | 2 | 3 | 1 | 2 |
| ESFJ | 3 | 4 | 2 | 3 | 2 | 3 | 1 | 2 | 2 | 1 | 1 | 0 | 3 | 2 | 2 | 1 |
| ISTP | 2 | 1 | 3 | 2 | 3 | 2 | 4 | 3 | 1 | 2 | 2 | 3 | 0 | 1 | 1 | 2 |
| ISFP | 3 | 2 | 4 | 3 | 2 | 1 | 3 | 2 | 2 | 1 | 3 | 2 | 1 | 0 | 2 | 1 |
| ESTP | 3 | 2 | 2 | 1 | 4 | 3 | 3 | 2 | 2 | 3 | 1 | 2 | 1 | 2 | 0 | 1 |
| ESFP | 4 | 3 | 3 | 2 | 3 | 2 | 2 | 1 | 3 | 2 | 2 | 1 | 2 | 1 | 1 | 0 |

Die Matrix gilt gleichermaßen für den Vergleich zweier Base Profiles und zweier Current Profiles. Beide Ergebnisse bleiben getrennt:

- `base_core_distance`: unveränderliche Distanz der Ausgangstypen,
- `current_core_distance`: Distanz der momentan entwickelten Typen.

Die kontinuierliche Achsendistanz zweier Figuren wird unabhängig vom Typcode normalisiert berechnet:

```text
axis_distance(a, b)
= sum(abs(a_axis - b_axis)) / 8

axis_similarity(a, b)
= 1 - axis_distance(a, b)
```

Damit liegen Distanz und Ähnlichkeit jeweils in `[0.0, 1.0]`. Zwei Figuren mit demselben Current Type können aufgrund unterschiedlicher Achsenstärken deutlich voneinander entfernt sein. Zwei Figuren unterschiedlicher Farbgruppen können strukturell direkte Nachbarn sein.

### 38.7 Struktur, Ergänzung und Relationship-Dynamik

Personality-Nähe ist kein universeller Kompatibilitätsscore. Das Spiel führt getrennte Perspektiven:

- `structural_similarity`: symmetrische Typ- und Achsennähe,
- `complementarity`: situationsabhängiges Potenzial, unterschiedliche Stärken produktiv zu verbinden,
- `friction_risk`: mögliche Reibung aus Achsen, Brand, Boundaries, Stress und ungelösten Konflikten,
- `directed_relationship_fit`: gerichtete Bewertung aus Sicht genau einer Figur im aktuellen Relationship- und Memory-State.

`directed_relationship_fit(A → B)` darf sich von `directed_relationship_fit(B → A)` unterscheiden. Große Ähnlichkeit garantiert weder Harmonie noch Romance. Große Distanz erzwingt weder Konflikt noch Unvereinbarkeit. Authored Story-, Brand-, Boundary- und Relationship-Regeln besitzen Vorrang vor einer reinen Achsendistanz.

Die Farbgruppe erzeugt weder einen Bonus noch einen Malus. Sie darf lediglich UI, Erklärtexte und gruppenspezifische Storymodule organisieren.

### 38.8 Events, Save State und Schreibautorität

Jede Personality-Wirkung wird als serialisierbares Domain Event gespeichert. Die Events enthalten mindestens Character, Source Turn oder Memory, Personality-State-Revision, primäre Achse, Gewichtsklasse, Vorher-/Nachherwert und die angewandten Relationship-, Memory- und Blueprint-Modifikatoren.

Der verbindliche Eventkatalog umfasst:

- `PersonalityInputResolved`,
- `PersonalityAxisShifted`,
- `PersonalityAxisStabilized`,
- `MemoryAxisImpulseApplied`,
- `CurrentPersonalityProfileChanged`,
- `PersonalityChronicleUpdated`.

`CurrentPersonalityProfileChanged` enthält zusätzlich vorherigen und neuen Typ, überschrittene Achse, vorherigen und neuen Pol sowie die auslösenden Evidence-Event-IDs. Der State Reducer leitet den neuen Current Type aus dem Achsenwert ab; kein Event darf einen beliebigen Typcode ohne passende Achsenüberschreitung setzen.

Der hardcodierte Game Director und seine validierten Reducer besitzen alleinige Schreibautorität. Character Speaker, Playground Author, RAG, Embedding-Suche und Frontend dürfen weder Achsenwerte noch Profile oder Personality Events direkt schreiben.

### 38.9 Sichtbarkeit im Chronicle

Die Verhaltenswirkung eines Current-Type-Wechsels beginnt ab dem folgenden Turn. Die sichtbare Systeminformation bleibt an Bekanntheit und Storyfreigabe gebunden:

- vor ausreichender Bekanntheit zeigt das Spiel nur Verhalten und qualitative Hinweise,
- nach dem Profile Reveal zeigt das Chronicle das Base Profile als Ausgangspunkt,
- das Current Profile wird als gegenwärtige Entwicklung angezeigt,
- Achsenbewegungen erscheinen qualitativ, beispielsweise `stabil`, `in Bewegung`, `nahe der Mitte` oder `deutlich entwickelt`,
- Rohwerte, versteckte Gewichtungen und Multiplikatoren bleiben unsichtbar,
- ein Current-Type-Wechsel erzeugt nach der fachlichen Freigabe einen nachvollziehbaren Chronicle-Eintrag.

Wechselt das Current Profile die Farbgruppe, darf das Chronicle die neue aktuelle Gruppenzuordnung anzeigen. Die ursprüngliche Base-Gruppe bleibt in der Entwicklungshistorie erhalten und erzeugt keinen versteckten Compatibility-Bonus.

### 38.10 Verbindliche Prüfszenarien

1. Eine Figur startet mit Base Profile `INTJ`. Wiederholte gültige Inputs bewegen ausschließlich `decision_orientation` in Richtung F. Beim tatsächlichen Überschreiten von `0.0` wird ihr Current Profile unmittelbar `INFJ`.
2. Der folgende VN-Turn verwendet das INFJ Behavior Pack mit schwacher F-Ausprägung nahe der Mitte. Brand, Memories, Relationship State, Name, Canon und Character Arc bleiben unverändert.
3. Eine emotional starke, Base-nahe Memory erzeugt später einen authorisierten T-Impuls. Beim erneuten Überschreiten wird das Current Profile wieder `INTJ`; die zwischenzeitliche Entwicklung bleibt in der PersonalityHistory erhalten.
4. Ein abgelehnter Userimpuls bewegt die Achse nicht in Intent-Richtung. Er stabilisiert den bestehenden Pol und darf gleichzeitig `current_tension` erhöhen.
5. Ein Turn darf nur eine primäre Achse verschieben und kann daher niemals zwei Typbuchstaben gleichzeitig wechseln.
6. `INTJ` und `INFJ` besitzen trotz unterschiedlicher Farbgruppen die strukturelle Distanz `1`. `INTJ` und `ENTP` besitzen trotz gleicher Farbgruppe die Distanz `2`.
7. Zwei Figuren dürfen nach unabhängiger Entwicklung dasselbe Current Profile besitzen. Ihre unterschiedlichen Base Profiles, Axis Values, Brands, Memories und Relationships bleiben erhalten.
8. Ein visuelles Favorite, eine Menünavigation oder ein Bild-Delete erzeugt ohne ausdrücklichen PersonalityInputContract keine Achsenbewegung.
9. Ein per Embedding gefundenes Memory ohne gültigen `MemoryPersonalityAnchor` darf keinen Personality-State verändern.
10. Character Speaker und Playground Author können weder in gültigem noch in ungültigem Output einen Achsenwert oder Typwechsel verbindlich setzen.
11. Das Chronicle zeigt nach ausreichender Bekanntheit Base Profile, Current Profile und qualitative Entwicklung, aber keine internen Rohwerte.

## 39. Jahresabschluss, Character-LoRA-Audit und frei wählbares New Game Plus

Dieser Abschnitt ist der autoritative Chronicle-Vertrag für die Verbindung aus
Schuljahresabschluss, Storyfortschritt, visueller LoRA-Reife und New Game Plus.
Die ausführbare Zerlegung für die Roadmap steht zusätzlich in
[`../sources/year-end-lora-and-new-game-plus.md`](../sources/year-end-lora-and-new-game-plus.md).

### 39.1 Schuljahresabschluss und LoRA-Validierung sind getrennt

Das Ende des Schuljahres schließt Calendar, Story und die erreichten Endings ab.
Ein LoRA-Training oder dessen Validierung darf diesen narrativen Abschluss nicht
rückwirkend blockieren oder zurücksetzen. Der `ChronicleRun` führt deshalb
getrennte Zustände für `narrative_status` und `production_status`.

Die visuelle Readiness darf während des Jahres intern fortlaufend berechnet
werden, damit Questplanung und Dataset Coverage fachlich sinnvoll bleiben. Das
erste verbindliche Angebot, Figuren für LoRA-Training und New Game Plus
auszuwählen, erfolgt beim Schuljahresabschluss.

### 39.2 Keine vorab festgelegte Zahl von Character-LoRAs

Ein Schuljahres-Run besitzt genau sechzehn aktive Character-Instanzen, aber
keine vorab festgelegte Zahl finaler LoRA-Artefakte. Wie viele Figuren
qualifiziert sind, ergibt sich aus ihrem tatsächlichen narrativen und visuellen
Stand am Jahresende.

```text
ChronicleRunOutcome
├─ narrative_endings[]
├─ character_outcomes[16]
├─ validated_lora_artifact_ids[]
└─ new_game_plus_candidates[]
```

Nicht vollständig erkundete Figuren bleiben gültige Bestandteile des
abgeschlossenen Runs. Sie werden lediglich nicht automatisch zu LoRA- oder
Carry-over-Kandidaten.

### 39.3 Narrative Qualification und Visual LoRA Readiness

Jede Figur wird anhand zweier getrennter Verträge geprüft. Vollständige Visual
LoRA Readiness erlaubt die direkte Auswahl. Narrative Qualification wird vor
allem für die Frage verbindlich, ob eine noch nicht fertige Figur eine
begrenzte Auffüllphase erhalten darf:

```text
NarrativeQualification
├─ Introduction und Character Development
├─ authored Character Milestones
├─ gemeinsame Story-Evidenz
└─ gültiger Abschlussstand der Route oder Teilroute

VisualLoRAReadiness
├─ gesperrter Character Canon
├─ unveränderliche Dataset-Version
├─ Identity- und Artstyle-Stabilität
├─ Coverage und Diversität
├─ behobene kritische Fehlercluster
├─ vollständige Recipe-/Workflow-/Modell-Lineage
└─ Validation- und Holdout-Vertrag
```

Friendship oder Romance erzeugt nicht automatisch technische Readiness. Ein
bereits vollständig LoRA-ready Candidate bleibt direkt wählbar. Bei einer
technisch noch nicht fertigen Figur ersetzt ein großes, aber lückenhaftes
Dataset dagegen keine ausreichende inhaltliche Entwicklung für das Privileg
einer Auffüllphase.

### 39.4 Drei Audit-Ergebnisse

#### `ready`

Visual LoRA Readiness ist vollständig erfüllt. Die Figur kann direkt für
Training und anschließende Validierung gewählt werden. Ihr Storyprogress bleibt
Teil des Outcomes, erzeugt aber kein zusätzliches Auffüllgate.

#### `fillable`

Die Figur ist noch nicht LoRA-ready, wurde aber narrativ weit genug entwickelt
und es fehlen nur wenige, klar benannte visuelle Nachweise. Das Spiel darf eine
begrenzte Auffüllphase mit konkreten Coverage-, Stability-, Holdout- oder
Repair-Quests anbieten.

Die Auffüllphase darf ausschließlich technische beziehungsweise visuelle
Restlücken schließen. Sie darf keine verpasste Friendship-/Romance-Route, neue
Character Milestones, unbekannte Outfits oder nicht erlebte Storykontexte nach
dem Ending erfinden. Der Audit zeigt fehlende Requirements, erwartete Runden und
geschätzte Generierungszeit.

#### `not_qualified`

Die Figur ist nicht LoRA-ready und entweder reicht die narrative Entwicklung
nicht für ein Auffüllangebot oder die visuelle Restlücke ist zu groß. Sie kann
in diesem Run nicht durch unbegrenzten nachträglichen Grind zu einer
New-Game-Plus-Figur gemacht werden.

### 39.5 Deterministische Schreibautorität

```text
CharacterYearEndAudit
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

Der hardcodierte Director und die versionierten Rules entscheiden Auditstatus,
Restlücke und Zulässigkeit. Character Speaker, Prompt Generator, RAG und
Embeddings dürfen höchstens die verständliche Präsentation unterstützen.

### 39.6 Spielerwahl und Validation

Der Abschlussablauf lautet:

```text
Schuljahr und Endings abschließen
→ alle sechzehn CharacterYearEndAudits erzeugen
→ ready, fillable und not_qualified erklären
→ Spieler wählt beliebig viele fillable Figuren zum Auffüllen
→ Spieler wählt beliebig viele qualifizierte Figuren zum Training
→ jedes LoRA-Artefakt separat validieren
→ Spieler wählt beliebig viele validierte Figuren für New Game Plus
→ unveränderliches NewGamePlusManifest erzeugen
```

Der Spieler darf eine, mehrere oder keine Figur übernehmen. Ein fehlgeschlagenes
Training oder eine fehlgeschlagene Validierung ändert das Ending nicht. Es
erzeugt Repair-, Coverage- oder Stability-Quests; alternativ kann der Spieler
die Figur aus der Übernahmeauswahl entfernen.

### 39.7 NewGamePlusManifest

```text
NewGamePlusManifest
├─ parent_chronicle_run_id
├─ selected_character_artifacts[]
│  ├─ character_id und Character-Canon-Snapshot
│  ├─ validated_lora_artifact_id
│  ├─ Base-Model- und Workflow-Kompatibilität
│  └─ Dataset-/Training-/Validation-Lineage
├─ rules_snapshot
├─ content_snapshot
├─ carry_over_policy
└─ created_at
```

Nur explizit ausgewählte, validierte und kompatible Artefakte werden in New
Game Plus geladen. Ein später verbessertes Artefakt ersetzt nicht still die
Basis eines bereits gestarteten Runs.

Noch zu kalibrieren sind die narrative Mindestentwicklung, der maximal
zulässige `fillable`-Abstand, Aufwandsschätzungen und der zusätzliche Carry-over
von Personality, Relationships, Memories, Bildern oder freigespielten
Content-Snapshots. Die Grundentscheidung für mehrere frei wählbare qualifizierte
Figuren bleibt davon unberührt.
