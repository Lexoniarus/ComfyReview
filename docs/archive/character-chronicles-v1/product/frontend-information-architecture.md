> [!CAUTION]
> **ARCHIVIERT — verworfener Character-Chronicles-Entwicklungsversuch.**
> Diese Datei ist historische Entwurfsdokumentation, **keine verbindliche Spezifikation** für das heutige ComfyReview oder die neue Entwicklung zu Character Chronicles. Aussagen wie „autoritativer Vertrag“, „MVP“, „DECIDED“, „Baseline abgeschlossen“, „implementiert“, Schema- und Meilensteinangaben gelten ausschließlich im Kontext des verworfenen Versuchs. Keine Festlegung daraus ohne neue, ausdrückliche Entscheidung übernehmen.
> Originalpfad: `docs/Concepts/product/frontend-information-architecture.md`; Quellrevision: `76d71f9c7723701664785aeaf07e0d7375a4f36a`.
> Aktuelle Regeln: [Dokumentationsindex](../../../README.md) · [Roadmap](../../../ROADMAP.md) · [Entscheidungen](../../../DECISIONS.md).

---

# Frontend, Informationsarchitektur und globale Einstellungen

Dokumentrolle: fachlicher MVP-Produktvertrag

Autorität: autoritativer Zielvertrag für den beschriebenen Produktbereich

Stand: 14. September 2026

## Grundsatz

Frontend-Arbeit ist keine abschließende Polish-Phase. Jeder fachliche Vertical
Slice enthält einen eigenen UI-/UX-Schritt und gilt erst als abgeschlossen,
wenn sein Zustand sichtbar, verständlich, responsive und praktisch spielbar
ist.

Für alle spielerseitigen Begriffe und Textstimmen gilt zusätzlich der
verbindliche Vertrag in
[`12-player-facing-terminology-and-voice.md`](player-facing-terminology-and-voice.md).
Insbesondere bleiben Story-Quest, visuelle Entwicklungsaufgabe, Trial,
Archivbild und technische Implementierung sprachlich getrennt.

Die konkrete Zielhierarchie aus Visual Novel, aktuellem Ort, Social Network,
Kartenfeature und post-M6-Screens steht ergänzend in der
[`Network-first VN-Frontend Screen Map`](network-first-vn-frontend-screen-map.md).
Der vorliegende Vertrag beschreibt sowohl den aktuellen bildzentrierten
Proof-Schnitt als auch später hinzukommende Produktflächen; die Screen Map
kennzeichnet die Grenze ausdrücklich.

Die Oberfläche bleibt eine Projektion des serverseitigen Spielzustands. Sie
darf keine Gates, Credits, Readiness, Relationship-Werte oder
Generierungsfreigaben selbst bestimmen.

### Projektionsvertrag zwischen Frontend und Backend

Frontend, Spiel-/Wettbewerbslogik und Generierungs-/Evidenzbackend sind drei
getrennte Ebenen desselben Spielzustands:

```text
QuestExperimentContract und persistentes Image
├─ Spielerprojektion
│  └─ Kartenauftrag, sichtbares Motiv, Bewertungsfrage, aktuelle Aktion,
│     Bildkarte und verständlicher Fortschritt
├─ Spiel-/Wettbewerbslogik
│  └─ QuestSession, GameMode, ChampionSlot, Eligibility, Cup, Titel und Gates
└─ Generierungs-/Evidenzbackend
   └─ Focus, Expected Composition, Locks, Variationen, Recipe/Seed/Modell,
      Reasons, Roh-Evidence, Confidence, Unsicherheit und Biasmerkmale
```

Die normale Oberfläche zeigt die oberste Ebene und erhält alle bindenden
Zustände als Serverprojektion. Sie muss nicht jede gespeicherte Information
permanent zeigen. Advanced und Diagnose machen die vollständige technische
Projektion zugänglich, ohne eine zweite Autorität zu erzeugen. Der vollständige
Sprach- und Ebenenvertrag steht in
[`player-facing-terminology-and-voice.md`](player-facing-terminology-and-voice.md).

Die Trial-Übersicht projiziert `activeActivity` pro Campaign. Eine globale
Hauptaktivität darf diese Aktivitäten nur hervorheben, nicht ersetzen oder als
globale Spielsperre verwenden. Ready-Quests bleiben bei gleichzeitigem
`preparing` aktiv. Sind keine Ready-Quests vorhanden, unterscheidet die UI
persistiert `preparing`, `waiting_provider`, `worker_offline` und einen echten
Integritätsblocker. Diagnose-GETs zeigen Snapshot-Zeit und Stale-Zustand; der
Browser löst weder Providerpolling noch Generierung aus. `Spielkarte`
bezeichnet eine persistente CardIdentity und kann nach Reject bildlos bleiben;
`Bildkarte` bezeichnet ausschließlich eine durch Keep oder Favorite an ein
persistentes Bild gebundene Spielkarte. Der Questvorrat besteht dagegen aus
Ready-Quests beziehungsweise Questkarten und ist keine Kartensammlung.

## Verbindliche M6-Proof-Navigation ab Schema 44

Der Schema-44-Cutover löst die M4-Navigation im aktuellen bildzentrierten
Spielerprodukt ab. Für den M6-Lernbeweis lautet die Navigation:

```text
Chronicle | Trials | Menü
```

`Characters` ist eine kontextuelle Cast-/Character-Focus-Unterseite und keine
gleichrangige Hauptnavigation. Workshop, Advanced Workshop, Settings, Import,
Diagnose und gekennzeichnete Legacy-Kompatibilitätsansichten liegen im Menü.
Die historische M4-Navigation `Chronicle | Characters | Trials | Workshop`
bleibt in ihren damaligen Abnahmebelegen unverändert, definiert aber nicht mehr
den M6-Zielzustand.

`Chronicle | Trials | Menü` ist ausdrücklich **nicht** die dauerhafte
Hauptnavigation des vollständigen VN-/Network-Spiels. Sie ist eine reduzierte
Proof-Shell, solange M6 nur Generierung, Bewertung und Verbesserung über mehrere
Zyklen belegt. Das post-M6-Ziel verwendet je nach Runtimezustand Network,
aktuellen Ort oder VN-Szene als dominanten Spielraum. Card Battler, Booster,
Sammlung und Visual Circuit liegen dann als zusammenhängendes Feature im
Network; die vollständige Screen Map steht im verlinkten Ergänzungsvertrag.

Ein neuer persönlicher Run beginnt im post-M6-Ziel verbindlich im Zustand
`network_fullscreen` mit der authored Mutter-/Umzugsinteraktion. Dieses
persönliche Asset-unabhängige Opening verwendet nicht die vollständige VN-Bühne
und benötigt keine save-spezifisch generierten Visual Bundles. Erst ein
freigegebener Ort darf zum `location_hub` werden; die erste `vn_scene` benötigt
zusätzlich ihr vollständiges Scene Presentation Manifest.

Das freigegebene M4-Konzeptpaket liegt unter
dem [M4-Konzeptpaket](../acceptance/m4/README.md). Es konkretisiert diese Architektur für
4K, 1280×720, Mobile und geringe Landscape-Höhe. Variante A „Context Rail“ ist
produktiv; Variante B bleibt historische Alternative. Konzeptrevision v2
verwendet die helle Anime-VN-/JRPG-Art-Direction und lokal gebündelte
Kenney-UI-Bausteine.

### Chronicle

`Chronicle` ist bereits im bildzentrierten MVP der Startbereich. Es projiziert
dort ausschließlich vorhandenen State:

- aktive Character-Campaign und aktuelles Kapitel,
- nächste Hauptaktion beziehungsweise Bildquest,
- konkrete Gate- und Progressblocker,
- Quest-Supply und laufende Generierungen,
- sowie direkte Links zum benötigten Spielmodus.

Es zeigt vor Einführung der Chronicle-Simulation keinen erfundenen Schultag,
Zeitabschnitt, Ort oder Character-Kontakt.

Die späteren MVP-Slices erweitern dieselbe Shell um:

- aktuellen `DayInstance`, Time Slot und Ort,
- nächsten authored Storyschritt und erreichbare Szenen,
- anwesende, telefonisch erreichbare und nicht verfügbare Figuren,
- groben Gesprächsanlass, Kommunikationskanal und Zeitwirkung,
- Scene-, Relationship-, Knowledge- und Ensemble-Blocker,
- sowie Story Memories und CGs.

### Characters

```text
Characters
├─ Klasse/Cast mit bekannten, angedeuteten und unbekannten Figuren
├─ Academy-Jahres- und Monatsbezug
├─ aktiver Character Focus und nächstes Ziel
├─ Bildkartensammlungen, Titelübersichten und aktuelle Trials
├─ gemeinsame Relationship-/Ensemblekarten
├─ Relationship-, Personality- und Storyentwicklung
├─ Memories
└─ Visual Development; am Abschluss Charakterübernahme
```

Im MVP entsteht dieser Bereich aus der heutigen Character-Ansicht und den
fachlich aufgeteilten Albumfunktionen. In den Chronicle-Slices wächst er zur Cast- und
Routeübersicht, ohne Chronicle als Tages- und Storyoberfläche zu ersetzen.

`Characters` ist keine zweite Trial-Runtime. Der Bereich projiziert
Figurenentwicklung, visuelles Material, Readiness, Lücken und figurbezogene
Ziele. Seine Quest- und Challenge-Einstiege öffnen die zuständige Oberfläche
unter `Trials` mit demselben serverseitigen Questvertrag und einem eindeutigen
Rückweg zur Figur.

Die Landing Page von `Characters` ist langfristig die Class-/Cast-Übersicht.
Sie zeigt pro sichtbarer Figur Cover beziehungsweise Signature Champion,
verständlichen Story-/Relationship-Kontext, groben Sammlungs-/Titelzustand und den nächsten
erreichbaren visuellen Bedarf. Unbekannte Figuren und zukünftige Routen dürfen
weder über Kartennamen noch über Deckzahlen, Queues oder Blockercopy geleakt
werden. Eine Academy-Jahres-/Monatsprojektion ordnet aktuelle Foki, kommende
Visual Needs und gemeinsame Ensemblekontexte zeitlich ein; sie ist kein
Klassenranking.

### Trials

```text
Trials
├─ laufende beziehungsweise fortsetzbare Trial-Session
├─ erforderliche und empfohlene Character Trials
├─ freie Trials, nach Figur und sichtbarer Bewertungsfrage geordnet
└─ Result, Fortschritt und eindeutiger Rückweg
```

`Trials` ist der einzige aktuelle spielerseitige Rahmen für Bildspiele und deren
Laufzeitoberflächen. `Trials` selbst ist kein Game Mode. `Erforderlich`,
`empfohlen` und `frei` beschreiben ausschließlich die Bindung derselben Runtime
an Story-, Character- oder reinen Zusatz-Credit. Kontextuelle Einstiege aus
Chronicle oder Characters ändern weder Trial-State noch Credit-Regeln.

Historische Einzelbezeichnungen und Routen wie `Arcade`, `Ratings`,
`Rankings` oder `Render Lab` definieren keine zusätzlichen aktuellen Modi oder
gleichrangigen Zielseiten. Soweit ihre Funktionen weiterhin benötigt werden,
erscheinen sie als konkrete Trial-Variante, Resultprojektion oder technische
Advanced-Information innerhalb des gemeinsamen Trial-Flows. Noch vorhandene
separate Screens sind zu entfernende beziehungsweise umzuleitende
Kompatibilitätsoberflächen, keine Vorlage für die Ziel-IA.

### Workshop

```text
Workshop
├─ Guided Workshop, später spielerischer Kernpfad
└─ Advanced Workshop, heutige technische Playground-Oberfläche
```

### Settings

```text
Settings
├─ Spiel
├─ Darstellung und Barrierefreiheit
├─ Bildgenerierung
├─ Inhalte und Freigaben
├─ Dienste und Modelle
├─ Speicher, Daten und Recovery
└─ Import, Legacy und Diagnose
```

`Memories` und `Training Material` bleiben fachlich getrennt. Ein Storybild
kann für beide geeignet sein, wird aber nicht allein durch seine Sichtbarkeit
im Chronicle automatisch Dataset-Mitglied.

## Globale Shell und responsives Verhalten

Ein schmaler Kontextstreifen zeigt nur serverseitig projizierten Zustand:

```text
[Run-, Character- oder Tageskontext]
                              [Generation] [Benachrichtigungen] [Settings]
```

Im MVP kann der Kontext beispielsweise
`Aiko · Wiedererkennbarkeit · Sonntagsoutfit` lauten. Der technische Focus
`identity_stability` bleibt dabei im Questvertrag und in Advanced erhalten. Mit
der Chronicle-Simulation wird daraus
`8. April · Nach der Schule · Klassenraum 2-B`. Reale Render- oder Wartezeit
verändert diesen Storykontext nicht.

- Desktop verwendet eine schmale linke Navigationsleiste mit Settings am
  unteren Ende.
- Schmale Fenster und mobile Layouts verwenden eine Bottom Navigation mit den
  vier Hauptbereichen; Settings bleibt im Header.
- Sekundärnavigation liegt innerhalb des aktiven Bereichs.
- Navigation, Kontextstreifen und offene Drawer schützen die großflächige Bild-
  beziehungsweise VN-Fläche und wirken nicht wie ein generisches Dashboard.

## Interaktionsprojektion im Chronicle

Chronicle gruppiert bekannte Figuren pro Time Slot nachvollziehbar:

- `hier`: direkte Interaktion am aktuellen Ort ist möglich,
- `telefonisch erreichbar`: ein Handy-Chat ist authorisiert,
- `nicht verfügbar`: ein authored Grund oder Gate verhindert den Kontakt.

Die Oberfläche zeigt nur den spielerrelevanten Ausschnitt einer
`InteractionSession`: Figur, Kanal, grober Gesprächsanlass, Sessionklasse,
ungefähren Umfang, Zeitwirkung und konkreten Blocker. Sie zeigt keine internen
Intent-, Personality-, Effect- oder LLM-Verträge.

## Character-Loop und gemeinsamer Trial-Rahmen

Ein Spielmodus ist nicht allein dadurch in den Character-Loop integriert, dass
er irgendwo unter `Trials` erreichbar ist. Characterbezogene Aufgaben werden
zusätzlich direkt in Chronicle und beim betreffenden Character als aktuelle
Entwicklungsaufgabe oder Challenge angeboten. Der Einstieg zeigt verständlich:

- für welche Figur die Aufgabe gilt,
- welche sichtbare Spielvariante folgt,
- welches Motiv beziehungsweise welche Karte im Mittelpunkt steht,
- welches sichtbare Ziel geprüft wird und was gleich bleiben soll,
- ob sie erforderlich, empfohlen oder frei ist,
- welche verständliche Entwicklung beziehungsweise Storyfreigabe sie bewirken kann,
- und wohin der Spieler nach Abschluss zurückkehrt.

Der zugehörige Serververtrag bindet davon getrennt Generation- oder Evaluation
Focus, Expected Composition, Locked/Varied Axes, Evidence Scope, Gateart,
Progress Credit und Recovery-Autorität. Diese Werte werden vollständig
gespeichert und in Advanced angezeigt, aber nicht als primäre Erklärung auf den
Spieler abgeladen.

Globale Sampler-, Style- und Umgebungsversuche bleiben unter `Trials` verfügbar,
erfüllen aber kein Character-Playgate, solange sie nicht ausdrücklich an einen
Character- und Questvertrag gebunden sind. Die serverseitige Bindung benötigt
mindestens `quest_id`, `progress_scope`, `target_id`, `progress_credit_kind`,
`credit_value`, `credit_cap`, `eligible_state_revision` und einen
`rules_snapshot`; `story_contract_id` bleibt optional. Die Quest-Instanz vergibt
ihren Credit höchstens einmal. Die Navigation und der verwendete Game Mode
dürfen keinen Progress-Credit aus ihrer bloßen Position beziehungsweise ihrem
Typ ableiten.

Assetgate-Runden, freie technische Vergleiche, Place-Aufgaben, reine
Resultprojektionen, Cleanup-Entscheidungen und freie Advanced-Workshop-Versuche
vergeben ohne ausdrücklich passenden Quest-Credit-Vertrag keinen
Character-Playgate-Credit. Eine identische
Trial-Oberfläche darf dadurch je nach vorbereiteter Quest Character-, Place-,
Style-, Scene- oder Global-Evidenz erzeugen, ohne ihre fachliche Bedeutung selbst
festzulegen.

Checkpoint-, LoRA-, Workflow- und KSampler-Werte erscheinen im normalen Spiel
nicht als frei veränderliche Standardsettings. Der Spieler sieht stattdessen
bildzentrierte Aufgaben mit sichtbaren Formulierungen wie „Welche Darstellung
bleibt am zuverlässigsten wiedererkennbar?“ oder „Welche Variante passt besser
zu diesem Ort?“. Interne Workflow-, Style-, Parameter- und Ablation-Verträge
bleiben in Advanced vollständig sichtbar. Pflicht- und
freiwillige Character Trials teilen pro Fokusfigur und VN Progress Window ein
Maximum von drei; unbegrenzte notwendige Assetproduktion wird getrennt
angezeigt. Details stehen in
[`10-generation-profiles-and-trials.md`](generation-profiles-and-trials.md).

Das Quest Board zeigt für jede bekannte Figur höchstens sechs normale
vollständig gerenderte `READY`-Games sowie ein zusätzliches Game je aktiver
sensibler Inhaltseinstellung. Ein vorhandener 16er-Cup erscheint separat und
verbraucht keinen sichtbaren Vierer-Slot, weil er aus bereits gerenderten
Kandidaten besteht. Ready-Vorrat, Bootstrap-`0` beziehungsweise regulärer
`1..3`-Playgate-Credit und unbegrenztes SceneAssetGate werden als drei
verschiedene Größen bezeichnet und dargestellt.
Der fachliche Trial-, Focus- und Evidenzvertrag steht in
[`11-game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md).
Die endgültige spielerseitige Modusliste wird erst im gemeinsamen Review nach
AIAM festgelegt; Arbeitsnamen aus Bestandsdokumenten sind keine automatische
Freigabe.

## Einordnung der heutigen Oberflächen

| Legacy-/Bestandsoberfläche | Zielbehandlung | Entscheidung |
|---|---|---|
| Character Campaign | `Chronicle` und `Characters` | visuelle Basis bewahren; Tages-/Zielkontext von Figurenentwicklung trennen |
| Album | `Characters → Visual Development` und später `Charakterübernahme` | kein eigener gleichgewichteter Hauptbereich mehr; Übernahme erst für Abschluss/NG+ relevant |
| Missions/Quest Supply | gemeinsamer Trial-Katalog, zusätzlich in Chronicle und beim Character | fachliche Priorität sichtbar lassen |
| Arcade-/Rating-Seiten | keine eigene Zielseite | benötigte Interaktion ausschließlich als freier Trial in den gemeinsamen Flow überführen |
| Rankings | keine eigene Spielruntime | Result- beziehungsweise Fortschrittsprojektion nur dort zeigen, wo sie die gerade gespielte Aufgabe erklärt |
| Render Lab | keine eigene spielerseitige Moduskategorie | kontrollierte technische Vergleiche als freie Trials; Detailkonfiguration und Promotion nach Advanced verschieben |
| Cleanup-Bestand | gemeinsamer Trial-Flow | genaue Spielvariante und Darstellung im anschließenden Modusreview festlegen; keine zweite Bewertungsseite ableiten |
| Playground Workbench | `Workshop → Advanced Workshop` | für alle Spieler sichtbar; vor manuellen Änderungen klar warnen |
| späterer geführter Creator | `Workshop → Guided Workshop` | Choices, Cards und LLM-Vorschläge statt Rohprompts |
| Legacy/Archive | `Settings → Import, Legacy und Diagnose` | nur Import- und Kompatibilitätspfad |

Bestehende URLs erhalten während der Umordnung Redirects oder klar markierte
Kompatibilitätsrouten. Navigation und Browser-Back dürfen keinen laufenden
Review-, Generation- oder VN-Zustand verlieren.

Characterbezogene Trial-Einträge erscheinen außerdem kontextuell in Chronicle
und Characters. Der gemeinsame Trials-Bereich ist Katalog und einzige Runtime,
nicht der einzige Zugang zu progressionsrelevanten Aufgaben.

### Verbindliche Zuständigkeitsgrenze

| Frage | Characters | Trials |
|---|---|---|
| Was entwickelt sich bei der Figur? | primäre Projektion | zeigt nur den gebundenen Credit-Kontext |
| Welche Bilder und Lücken besitzt sie? | visuelle Hauptansicht | keine parallele Materialverwaltung |
| Welche Aufgabe ist als Nächstes sinnvoll? | kontextueller Einstieg | gemeinsamer Katalog mit erforderlichen, empfohlenen und freien Trials |
| Wo wird bewertet oder verglichen? | nicht dupliziert | alleinige Runtime des jeweiligen Modus |
| Wohin führt der Abschluss? | Rückkehrziel und aktualisierte Entwicklung | Result und expliziter Rückweg |

Eine charactergebundene Quest darf damit an drei Stellen auffindbar sein, aber
nur eine serverseitige Instanz und eine Trial-Runtime besitzen.

## Zielabläufe der vorgelagerten Bildspiele

Der produktseitige Modusvertrag steht vollständig in
[`game-modes-and-guided-evidence.md`](game-modes-and-guided-evidence.md#spielmodi).
Für das Frontend gilt als harte Grenze: Disposition und Reasons eines Bildes
verwenden denselben Fokus und denselben Bildknoten. Relative Stufen sind davon
getrennt: Das Viererset ist nur beim Sortieren, das Arenapaar nur bei der
Siegerwahl sichtbar. In der anschließenden Einzelbewertung ist ausschließlich
das aktuelle Bild sichtbar.

### Vierer-Qualifier als vier Bild-Mikroloops

Der Vierer-Qualifier ist ausdrücklich **kein globaler Zweipass-Review**. Er
durchläuft viermal denselben zusammenhängenden Mikroloop:

```text
Bild groß in der Mitte
→ Favorite | Keep | Reject
→ dasselbe Bild bleibt sichtbar
→ positive und negative Teilbefunde gemeinsam in zwei Bubble-Flächen
→ erster dispositionskonformer Reason wird sichtbar markierter Primary Reason
→ einmaliges Bewertung speichern
→ nächstes Bild
```

`Favorite` und `Keep` benötigen mindestens einen positiven Primary Reason,
`Reject` mindestens einen negativen Primary Reason. Gegenläufige Secondary
Reasons sind optional. `Skip` und eine Nullbegründung wie `Nicht sicher / kein
klarer Grund` sind im Zielspiel nicht zulässig. Wenn an einem Bild nichts gut
ist, wird es abgelehnt und negativ begründet; auch vier Rejects sind ein
gültiger Batchabschluss. Ein technisch nicht bewertbares Bild blockiert mit
Recovery-Projektion und wird nicht als Skip gespeichert.

Desktop und 4K halten Fokusbild und Eingabe in einer begrenzten, gemeinsamen
Bühne. In der Reason-Stufe steht das unveränderte Bild links und die Bedienung
rechts; dadurch driften Motiv und Entscheidung auch auf großen Displays nicht
auseinander. Positive und negative Teilbefunde erscheinen gleichzeitig in zwei
Bubble-Flächen mit eigener interner Scrollposition. Der erste passende Reason
wird automatisch Primary Reason; weitere markierte Bubbles bleiben optionale
Secondary Reasons. Primary-Zusammenfassung und die einmalige Abschlussaktion
bleiben sichtbar. Die Reason-UI ist keine Checkboxliste und erzeugt nur einen
serverseitigen Evidence-Commit. Die eine idempotente
Mutation umfasst gemeinsam `attempt_image_id`, Disposition, optionalen Scalar
Score, Primary Reason und Secondary Reasons; kein Teilreview wird vorab
persistiert.

Tablet-Portrait und Mobile halten das Bild im sichtbaren oberen Stage-Bereich
und den gemeinsamen Reason-Screen darunter. iPad-Landscape darf Bild und
Bedienung nebeneinander anordnen. Ausschließlich die beiden Reason-Bereiche
scrollen; Back, Bild, Fortschritt und Abschlussaktion werden von keinem Footer
überlagert. Alle Touchziele bleiben mindestens 44 px hoch.

### Vierer-Ranking statt Weakest Link

Alle vier Bilder stehen während der Sortierung in einer Reihe beziehungsweise
responsiven 2×2-Stage. Der Spieler ordnet sie von links nach rechts als bestes
bis schwächstes Bild. Danach wird jedes Bild in dieser Reihenfolge einzeln und
bilddominant fokussiert und erhält Favorite, Keep oder Reject samt Pflichtgründen.
Die übrigen drei Bilder sind in diesem Fokus nicht sichtbar. Auswahlleiste,
gemeinsamer Reason-Screen und die einmalige Abschlussaktion funktionieren wie
im Qualifier.

Die Sortierung bleibt relative Evidence und wird abhängig von den anschließend
gesetzten Dispositionen unterschiedlich stark projiziert. Gleiche Dispositionen
erzeugen schwächere Präferenzevidenz, Favorite gegenüber Reject stärkere. Die UI
berechnet keine Faktoren. Sie erzwingt jedoch die monotone Reihenfolge
`Favorite* → Keep* → Reject*`: Ein niedriger geranktes Bild kann keine stärkere
Disposition als ein höher geranktes erhalten. Inkonsistente Optionen werden im
aktuellen Schritt nicht als gültige Fortsetzung angeboten; `Sortierung ändern`
und die direkte Korrektur bereits gesetzter Dispositionen bleiben erreichbar.
Die UI sortiert niemals still um.

### Arena als Vergleich mit zwei Einzelbild-Fokusstufen

Beide Bilder stehen ausschließlich für die Gewinnerwahl nebeneinander. Nach
Links-/Rechts-Sieg beziehungsweise `kein Gewinner` folgt unabhängig vom Sieger
zuerst Bild A und danach Bild B. In jeder Fokusstufe ist nur dieses eine Bild
sichtbar; sein Gegenstück erscheint weder als Motiv noch als Thumbnail.
Disposition und Reasons verwenden denselben Bildknoten. Der Sieger wird nicht
automatisch Keep/Favorite, der Verlierer nicht automatisch Reject. Auswahlleiste,
zwei scrollbare Bubble-Flächen und festes `Weiter` bleiben erhalten.
`Bewertung starten`, `Ergebnis übernehmen` und eine spätere
Disposition-Formularwand entfallen. Der bestehende bindende Lifecycle bleibt
sichtbar: Ein unterlegener Keep geht zu Delete or Live, ein unterlegenes
Favorite in seine Verlustserie; `kein Gewinner` ist nur mit zwei Rejects
abschließbar. Die Gewinnerdisposition darf nie schwächer als die des Verlierers
sein; insbesondere ist Keep gegen Favorite kein gültiger Abschluss.

Schema 44 registriert diese Zielabläufe als neue immutable Mode-Revisionen.
Historische Sessions behalten ihre damalige Revision und bleiben lesbar; neue
Sessions werden nicht mehr als Zweipass-Qualifier oder Weakest Link eingeplant.
`GAP-026` ist nach Player-Vertrag, Migrationstest und korrigierter Desktop-/
Mobile-Browserabnahme geschlossen.

### 16er-Cup ohne neue Bewertungsrunde

Im 16er-Cup bleiben beide Matchbilder bis zur Siegerwahl sichtbar. Diese eine
Wahl schließt das Match ab und führt zum nächsten Paar beziehungsweise zur
nächsten Runde. Der Cup zeigt vorhandene Dispositionen und Gründe höchstens als
Kontext, fragt aber weder neue Reasons noch Favorite/Keep/Reject ab. Es gibt
keinen Reason-Screen und keine Ergebnisübernahme zwischen zwei Matches.

Ist die Vierergruppe trotz vier geplanter Slots auffällig gleichförmig, kann das
Resultat einen ruhigen, rein informativen Diagnosehinweis wie `Die Bilder ähneln
sich ungewöhnlich stark` zeigen. Er verändert weder Reihenfolge noch Bewertung,
fragt kein Maschinenfeedback ab und startet keine Ersatzgeneration. Bestätigen
oder Verwerfen von Maschinenbeschreibungen gehört ausschließlich in den
separaten Zwei-Bild-Description-Review. Technischer Seed-/Recipe-Reuse erscheint
getrennt als Wiederherstellungsproblem; Prompt-/Modellkonvergenz erscheint in
Advanced als Eingabe für den nächsten kontrollierten Try.

Das Reason Panel unterscheidet für den Spieler verständlich fünf Ebenen:

- **Auftrag:** Wurde wirklich die verlangte Zusammensetzung erzeugt?
- **Bildfehler:** Ist bei Anatomie, Hintergrund oder Rendering etwas kaputt?
- **Figur:** Ist die Character Identity stabil geblieben?
- **Verwendbarkeit:** Passt Crop, Safe Area, Freistellung und Assetrolle?
- **Geschmack:** Gefällt die ansonsten mögliche Lösung?

Die zum konkreten Generierungsauftrag und Generation Focus passenden Bubbles
stehen innerhalb ihrer positiven beziehungsweise negativen Seite zuerst. Pro
Bild zeigt der erste sichtbare Bereich höchstens sechs bis acht priorisierte
Bubbles.
Weitere für die Assetrolle anwendbare Fehler bleiben in ihren Gruppen
erreichbar; der Fokus darf etwa deformierte Hände in einer Outfit-Challenge
nicht verstecken. Ein Chip zeigt nicht technische Recovery-Interna, seine ID
speichert aber Ebene und erlaubte Folgerichtung. Ähnlich klingende Fälle werden
sprachlich getrennt, beispielsweise `Falscher Ort`, `Hintergrund kaputt
generiert` und `Hintergrund gefällt mir nicht`.

Reject legt dabei sofort negative Evidenz und eine deduplizierte Cleanup-
Referral `awaiting_guided_evidence` an. Erst nach der Begründung dieses Bildes
wird sie `ready` und darf in Delete or Live erscheinen. Undo vor diesem Punkt
setzt sie auf `void`. Delete or Live konsumiert die bereits gewählten Gründe
und zeigt weder eine zweite Begründungsrunde noch einen Bestätigungsdialog.

## Delete or Live

Dieser Abschnitt friert den bereits entschiedenen Cleanup- und Dateilifecycle
ein. Er entscheidet nicht, ob `Delete or Live` nach dem gemeinsamen Modusreview
als eigener Modusname oder eigene Seite bestehen bleibt. In jedem Fall darf
daraus keine zweite Bildbewertung oder Begründungsrunde entstehen.

`Delete or Live` ist ein schnelles Worst-Candidate-Spiel und keine
Quarantäneverwaltung. Seine Queue nimmt nur `ready`-Referrals aus vollständig
begründeten Rejects, im 16er-Spiel ausgeschiedenen Keeps und Favorites nach der
dritten Niederlage in Folge mit getrennter Provenienz auf. Ein Queue-Eintrag
wird genau einmal binär bewertet:

1. `Live` behält das validierte PNG/JSON-Paar unverändert. Bei einem
   ausgeschiedenen Keep reaktiviert es zusätzlich dessen Challenger-Eignung für
   ein späteres 16er-Turnier; ein Reject bleibt lediglich als Datei erhalten.
   Bei einem Favorite bleiben Action und historische Pairwise-Evidence erhalten;
   Verlustserie und Cooldown werden auf null gesetzt und ein neues Eligibility-
   Ereignis lässt es als Favorite in einem späteren 16er-Turnier von vorn
   teilnehmen. Das eingefrorene Ursprungsbracket bleibt ausgeschlossen.
2. `Delete` entfernt PNG und JSON endgültig, behält aber die strukturierte
   Review- und Löschprovenienz.
3. Nach der Entscheidung erscheint ohne zweiten Bestätigungsdialog unmittelbar
   der nächste Worst Candidate.

Der Dateivorgang ist über ein persistentes, vorwärts gerichtetes Journal
abgesichert. Nach einem Crash wird eine begonnene Löschung abgeschlossen und
nicht in einen halbfertigen Restore-Zustand zurückgedreht.

Das soeben abgelehnte oder aus einem Bracket ausgeschiedene Bild darf nicht im
nächsten Spielschritt erneut zur Bestätigung erscheinen. Ein durch `Live`
gerettetes Keep kehrt nie in denselben eingefrorenen Bracket zurück. Es gibt keine sichtbare
Quarantäne, kein Restore und keinen nachgelagerten Purge-Schritt. Delete or Live
erteilt keinen Character-Progress-Credit.

### Reject ist Übergabe, nicht Löschen

Andere Bildspiele besitzen keine direkte Delete-Aktion. Dort
bedeutet `Reject` ausschließlich:

- Der Kandidat verliert den aktuellen Vergleich beziehungsweise qualifiziert
  sich nicht.
- Seine negative Bewertung bleibt als Review Evidence erhalten.
- Es entsteht genau eine deduplizierte Cleanup-Referral im Zustand
  `awaiting_guided_evidence`.
- Der ursprüngliche Spielmodus wechselt unmittelbar zum nächsten Kandidaten
  beziehungsweise Match.

Nach Abschluss der bildweisen Begründung wechselt die Referral auf `ready` und
erst dann in die sichtbare Eingangsqueue von Delete or Live. Ein Undo davor
setzt sie append-only auf `void`.

Erst `Delete or Live` entscheidet, ob ein solcher Kandidat live bleibt oder
endgültig gelöscht wird. Nur dieser Modus darf aus dem normalen Spiel heraus
den journalisierten Dateilöschvorgang starten.

Damit gelten vier fachlich verschiedene Zustände:

`rejected_in_game → awaiting_guided_evidence → ready
→ live_retained | permanently_deleted`

Ein Reject überspringt keinen Zustand. Mehrfache Rejects desselben Bildes
erzeugen weitere Evidenz, aber keinen mehrfachen Queue-Eintrag.

### Bindender Eliminationsverlust ist abhängig von der Reviewaction

Jede bindende Eliminationsniederlage eines Favorites zählt unabhängig von der
konkreten Spieloberfläche oder dem Turniernamen in dieselbe Verlustserie. Nach
seiner ersten beziehungsweise zweiten Niederlage in Folge bleibt es im
Challenger-Pool, ist aber jeweils für genau einen
`ChampionCycleCooldown` nicht rosterfähig: einen vollständigen Challenger-Cup
bis zum nächsten Title Match. Die UI zeigt Verluststand und den gemeinsamen
Champion-/Favorite-Zyklus. Die dritte Niederlage in Folge verweist auch das
Favorite an Delete or Live. Jeder bindende Eliminationssieg setzt den aktuellen
Verlustfolgezähler auf null; die Matchhistorie bleibt sichtbar. Gleichstand,
Abbruch und `nicht vergleichbar` verändern den Zähler nicht. Ein Keep folgt
diesem Lebenszyklus bereits nach seiner ersten bindenden Niederlage:

`keep_eliminated → delete_or_live_pending → future_pool_eligible | permanently_deleted`

`future_pool_eligible` mutiert die ursprüngliche Keep-Entscheidung nicht zu
Favorite und erzeugt keinen Wiedereintritt in das bereits laufende Turnier.

Für Favorites gilt zusätzlich:

`favorite_eliminated → champion_cycle_cooldown | delete_or_live_pending_on_loss_3`

Ein per `Live` gerettetes Favorite bleibt Favorite. Die UI projiziert
`consecutive_loss_count=0`, keinen aktiven Cooldown und ein neues
Eligibility-Ereignis für einen späteren Cup. Jeder bindende Eliminationssieg ist
ebenfalls ein Resetereignis der aktuellen Verlustserie. Das Bild kehrt niemals in dasselbe
eingefrorene Bracket zurück; historische Matches und DOA bleiben sichtbar.

Ein unterlegener Title-Match-Challenger folgt derselben Keep-/Favorite-Regel.
Ein abgelöster Amtsinhaber erscheint als geschützter `former_champion` im Pool;
bei Gleichstand oder Abbruch bleibt er Amtsinhaber und die Pflichtquest offen.

Die Matchansicht darf den Vergleich nicht als bloßen Navigationsschritt
darstellen. Nach jeder A/B-Entscheidung zeigt sie Gewinner, Verlierer, Runde und
die gewertete Achse; beide Bilder erhalten die daraus abgeleitete positive
beziehungsweise negative Pairwise-Evidence.

Historische Qualität darf die UI dabei nicht als nackten Prozentwert oder
globalen Bildscore ausgeben. Wenn eine Verhältnisgeschichte sichtbar ist,
zeigt sie immer gemeinsam die betroffene Achse, das positive/negative
Evidenzverhältnis, die Evidenzmenge und eine verständliche Confidence-Stufe.
Ein neues Bild mit bislang eindeutig positiver Einzelbewertung wird daher als
`vielversprechend, noch wenig geprüft` kenntlich gemacht; ein älteres Bild mit
gemischter Historie als `häufig geprüft, Ergebnis gemischt`. Evidenz auf einer
anderen Achse kompensiert die angezeigte Achse nicht.

### Champion-Pflichtquest statt erzwungener Navigation

Sobald der sechzehnte rosterfähige Challenger sein Eligibility-Ereignis erhält,
friert der Server atomar die ersten sechzehn Einträge in stabiler
Ereignisreihenfolge als Roster und Bracketplätze ein. Spätere Einträge zeigt die
UI als Warteschlange für den nächsten Cup; sie bietet keine nachträgliche
Roster-Kuration an. Der Server setzt die zugehörige Champion Quest auf `READY`.
Chronicle, Character und
Trials zeigen sie als Pflichtquest und den dadurch blockierten Fortschritt an.
Ein gerade laufender Einzelreview oder Viererbatch wird nicht durch einen
Redirect unterbrochen; nach seinem sauberen Abschluss führt der primäre
Progresspfad in die bereitstehende K.-o.-Quest.

## Visual Development und Charakterübernahme

Das heutige Album ist im späteren Produkt kein eigenständiger Hauptmodus.
Seine fachlichen Aufgaben werden getrennt dargestellt:

- `Visual Development`: bestätigte Character Canons, Champions und Varianten,
- `Training Material`: technische Dataset-Mitgliedschaft als Advanced-
  Detailansicht innerhalb der visuellen Entwicklung,
- `Charakterübernahme`: erst am Run-Abschluss beziehungsweise im Übergang zu
  New Game Plus sichtbare Auswahl qualifizierter Figuren einschließlich
  LoRA-Readiness, begrenztem Auffüllen, Validation und Carry-over,
- `Chronicle Memories`: erlebte Storybilder und CGs.

Der Spieler sieht primär, was stabil ist und was noch fehlt. Manuelle
Dataset-Mitgliedschaft bleibt für Korrektur und Expert Review zugänglich, ist
aber nicht der alltägliche Hauptnavigationspunkt.

### Informationsdichte von Training Material

Die normale Character-Ansicht bleibt bildzentriert und zeigt ausschließlich:

- große Album- beziehungsweise Championbilder,
- Readiness als verständlichen Zustand statt Rohscore,
- die wichtigsten Coverage-Lücken,
- das nächste konkrete Bildziel,
- und einen Einstieg in passende Trials.

Ein standardmäßig geschlossener Expert-Drawer enthält die vollständige
technische Projektion: Coverage-Tags, Provenienz, Component- und Prompt-Version,
Recipe- und Workflowreferenz, Renderprofil, Dataset-Membership sowie
Dateiverfügbarkeit. Auf Desktop ist der Drawer höchstens 440 Pixel breit; auf
Mobile wird er als fokussierte Full-Height-Sheet geöffnet. Das Öffnen verändert
weder Auswahl noch Membership.

Ein permanenter, spielerzentraler Balken namens `LoRA Progress` ist nicht Teil
der Zielnavigation. Technische Coverage und Stability dürfen intern und in
Advanced-Details sichtbar bleiben, werden dem Spieler aber erst dann als
`Charakterübernahme` angeboten, wenn der Run-Abschluss beziehungsweise New Game
Plus diesen Zweck tatsächlich eröffnet.

### Bildkartensammlung, Titelübersicht und Bildkarrieren

`Visual Development` projiziert jedes als Keep oder Favorite behaltene Bild als
eigene Bildkarte. Ein Reject erzeugt zwar ein Spielkartenresultat, aber keine
Bildkarte. Die Bildkarte steht für das persistente Bild, nicht für einen
ChampionSlot. Sie zeigt eine verständliche Bildbeschreibung, die Bewertung,
ihre Challenger-Eignungen, gewonnene Titel und getrennte Verwendungen. Dasselbe
Bild wird auch bei mehreren Titeln nur einmal als Karte geführt.

Die Bildkartensammlung trennt mindestens:

- Keep und Favorite als Bewertung,
- Bildbeschreibung und sichtbaren semantischen Kontext,
- Challenger-Eignung und Championtitel,
- Stability als eigenen Zustand,
- konkrete offene, freigegebene oder fehlgeschlagene Assetverwendungen,
- sowie Kartenhistorie und den nächsten vom Server begründeten Trial-Einstieg.

Eine getrennte Titel- beziehungsweise Arenaübersicht projiziert die benannten
ChampionSlots: offene Titel, Challenger-Fortschritt bis zum nächsten 16er-Cup,
aktuellen Champion, Former-Champion-Historie und Stability/Mastery des
Vergleichskontexts. Ein ChampionSlot ist keine leere Bildkarte. Der VN-/Card-
Battler-Bestand ist keine getrennte zweite Kartensammlung, sondern eine
gefilterte Projektion derselben Bildkarten.

Die Titelübersicht gruppiert Kombinationschampions pro Figur nach ihrer
Granularität. Der Character ist dabei immer sichtbar und fest gebunden:

- `Character + 1 Aspekt`,
- `Character + 2 Aspekte`,
- `Character + 3 Aspekte`.

Eine aspekt-only Kombination darf die UI weder anbieten noch als Titel
darstellen. Pro Titelkarte zeigt sie die konkret gebundenen Aspekte, den
Fortschritt `n/16`, den aktuellen Champion und gegebenenfalls `Title Match
bereit`. Dasselbe Bild erscheint in der Sammlung nur einmal, auch wenn es in
mehreren 1er-, 2er- oder 3er-Titelkarten referenziert wird.

Keep-Karten sind vollständige, aber vorläufige Basiskarten. Solange ihre exakt
gebundene CharacterChampionSignature keinen Kombinationschampion besitzt,
dürfen sie aktiv gespielt werden. Nach Besetzung dieses konkreten 1er-, 2er-
oder 3er-Championplatzes bleiben reine Keeps derselben Signatur sichtbar und
challengerfähig, erscheinen aber nicht mehr zusätzlich in der aktiven
Battler-Auswahl. Ein Titel anderer Granularität besetzt diesen Platz nicht.
Favorite- und Championstatus verbessern dieselbe Karte über getrennte
randomisierte Augments. Eine spätere aktive Deckzusammenstellung ist wiederum
eine Teilmenge der aktuell spielbaren Karten. Ein matchbereites Deck besitzt
exakt 40 einzigartige CardIdentities. v0.1 verwendet keine allgemeine Mana-
oder Energieressource und kein Side-/Reserve-Deck; Ausspielen folgt
Feldpräsenz, Opfermatrix und den registrierten Einzelkosten der Traits.

Die UI zeigt deshalb pro Karte nicht nur Bewertung und Titel, sondern auch
`aktiv spielbar`, `vorläufig spielbar`, `nur Challenger`, `gefährdet` oder
`Bildbindung gelöscht · als Standard aktiv` samt gebundener
CharacterChampionSignature und verständlichem Grund. Bei endgültiger
Bildlöschung behält das Deck dieselbe CardIdentity, zeigt jedoch ab der nächsten
Collection-/Deckrevision wieder ihr ursprüngliches bildloses Standardprofil.
Ein bereits laufendes Match zeigt weiterhin den eingefrorenen Snapshot.
Delete or Live darf niemals einen sofortigen Championwechsel ankündigen. `Als
Favorite retten` erhält die Bildkarte und kann sie für einen späteren Cup neu
qualifizieren; ein vorhandener Champion bleibt bis zu einem gewonnenen Cup und
gegebenenfalls Title Match unverändert.

Ein möglicher Signature Champion erscheint als Character-Cover und
Prestigetitel. Er ersetzt weder die Champions der einzelnen Titelkontexte noch
deren Stability und erzeugt keine Assetfreigabe. Der vollständige Vertrag steht in
[`champion-slots-and-character-decks.md`](champion-slots-and-character-decks.md).

Relationship- und Ensemblekarten besitzen einen gemeinsamen Portfolio-Owner.
Sie erscheinen bei allen beteiligten Characters als geteilte Karten, zählen
aber weder mehrfach zur Class-Aggregation noch als eigener Slottitel jedes
Characters. Auch hier bleibt die gemeinsame Bildkarte vom zugehörigen
ChampionSlot beziehungsweise Titelkontext getrennt. Die vollständige Hierarchie aus Academy-Run, Jahr, Klasse, Character,
Beziehung und Ensemble steht in
[`school-year-visual-portfolios-and-relationship-contexts.md`](school-year-visual-portfolios-and-relationship-contexts.md).

### Kartenkunst-Komposition: DOM plus Canvas 2D

Eine Keep-, Favorite-, Champion-, Public-Edition- oder Evolutionskarte erhält
nach ihrer unmittelbaren Rules-/Branding-Materialisierung einen eigenen
resumefähigen Gestaltungsstep. Der Spieler verschiebt und skaliert das
bestätigte Quellbild hinter einem unveränderten revisionierten Frame und
bestätigt den sichtbaren Ausschnitt. Drag, Pinch, Mausrad, Zoomslider,
Pfeiltasten, Reset, Abbruch und Bestätigung führen auf dieselben normalisierten
Transformcommands.

Diese Oberfläche ist DOM-basiert und verwendet Canvas 2D nur als verwerfbare
Vorschau. Der Server validiert Coverage und Revisionen und rendert das
autoritative Kartengesicht. Vor der Bestätigung bleibt die CardIdentity
regelgültig, zeigt aber eine neutrale ausstehende Kartenprojektion. Bildlose
Standardkarten besitzen keinen Kompositionsstep. Der vollständige Vertrag steht
in
[`card-art-composition-and-rendering.md`](card-art-composition-and-rendering.md).

### Card-Battler-Präsentation: Phaser plus DOM

Der Card Battler verwendet im späteren Vertical Slice eine eingebettete
Phaser-Spielfläche für Fünf-Slot-Board, Kartencontainer, Zielmarkierung,
Bewegung, Kamera und Effekte. Phaser erhält ausschließlich bestätigte
`CardBattlerPlayerProjection`s und `animation_cues`; Scenes, Sprites, Tweens
und Partikel sind verwerfbarer View-State und berechnen keine Regeln.

Battle-Home, Gegnerdetail, Deckwahl, Mulligan, vollständiger Kartentext,
Ziel-/Opfer-/Triggerauswahl, Reaktionsdialoge, Pause, Recovery, Ergebnis und
Accessibility bleiben im DOM. Eine gemeinsame Controllergrenze übersetzt
Pointer, Touch und Tastatur in semantische Commands. Ein optionales
Reaktionsfenster erscheint nur, wenn mindestens eine legale Spielerreaktion
existiert; andernfalls passt der Server automatisch.

Reload und Browser-Back laden die letzte bestätigte Matchrevision samt Pending
Interaction. Reduced Motion überspringt Animationen und springt direkt auf die
bestätigte Projektion. Die vollständige Modul-, API-, Persistenz- und
Recoverygrenze steht in der
[`Card-Battler-Runtime-Architektur`](card-battler-runtime-architecture.md).

## Workshop

Die heutige Playground Workbench bleibt zunächst ein technisches
Authoring-/Power-User-Werkzeug und wird als `Advanced Workshop` bezeichnet. Er
ist für alle Spieler ohne Freischaltung, Rollenprüfung oder Progressbedingung
erreichbar. Phase 0 ergänzt:

- eine klare Einleitung und Zweckbeschreibung,
- Begriffserklärungen,
- Empty-, Preview-, Generation-, Error- und Success-States,
- direkten Rückweg zum Character beziehungsweise zur erzeugenden Quest,
- die sichtbare Kennzeichnung `Advanced`,
- sowie vor manuellen Änderungen einen bestätigbaren Warnhinweis, dass diese
  Konsistenz, Vergleichbarkeit und reproduzierbare Recovery erschweren können.

Der Warnhinweis ist keine Zugangssperre. Manuelle Versuche bleiben versioniert,
erhalten einen effektiven Recipe Snapshot und können auf bewährte Defaults
zurückgesetzt werden; die Oberfläche darf keinen irreparablen Datenverlust als
akzeptiertes Risiko behandeln.

Der spätere Guided Workshop ist eine eigene Spieleroberfläche. Er sammelt
Character-, Outfit-, Scene- und Style-Input über geführte Choices, visuelle
Karten und validierte Vorschläge. Er darf nicht lediglich die heutige
Rohprompt-Oberfläche umbenennen.

## Globale Einstellungen

### Inhalte und Freigaben

Figuren- und saveübergreifend gespeichert werden mindestens:

- zugelassene Inhaltsstufen,
- sensible Themen und Kategorien,
- explizite Opt-ins beziehungsweise Bestätigungen,
- sowie eine versionierte `ContentPolicyRevision`.

Eine restriktivere Änderung gilt sofort für neue Planung und Generierung. Eine
Erweiterung der Freigaben benötigt eine ausdrückliche Bestätigung. Jede Quest
und jedes Generation Recipe speichert die tatsächlich angewandte Revision.

Aktivierte Adult-Content-Bereiche erscheinen später als eigener, klar
abgegrenzter Teil des diegetischen Networks und nicht zwischen regulären
Battle-Boostern, Decks oder Champion-Cups. Sie dürfen ebenfalls einen
Booster-Rahmen verwenden, benötigen aber eine eigene visuelle Sprache, eigene
Ergebnisprojektion und explizite Content-Kennzeichnung. Ihre Bilder und
Bewertungsevidenz bleiben für Bildlernen und eine spätere VN-Verwendung
erhalten; sie erzeugen jedoch keine Card-Battler-CardIdentity, keine
Deckverfügbarkeit und keine 1er-, 2er- oder 3er-Champion-Eligibility. Der
Vier-Spielkarten-Ergebnisvertrag gilt ausschließlich für reguläre
Battle-Booster.

### Bildgenerierung

Globale Defaults umfassen mindestens:

- maximale post-upscaled Ausgabequalität `720p`, `1080p` oder `4K`,
- sowie Standardverhalten bei langen Wartezeiten.

Asset-Rolle und Quest bestimmen Seitenverhältnis, Modell- und Zielcanvas
codeautoritativ. Spieler wählen diese Geometrie nicht in den globalen Settings.
Queue, Parallelität und technische Performanceparameter bleiben externe
Betriebskonfiguration. Jede konkrete Generierung speichert weiterhin Modell- und
Review-Auflösung, Seitenverhältnis, Workflow und Renderprofil unveränderlich im
Recipe. Eine spätere Settingänderung interpretiert vorhandene Bilder nicht neu.

### Spiel und Barrierefreiheit

- Textgeschwindigkeit, Auto-Advance und Skip-Verhalten,
- Audio und Benachrichtigungen,
- Bestätigungsdialoge,
- UI-Skalierung, Kontrast und reduzierte Bewegung,
- Tastaturnavigation und sichtbare Fokuszustände,
- sowie Sprache und lesefreundliche Darstellung.

### Dienste, Modelle und Diagnose

Der erweiterte Bereich enthält ComfyUI, LM Studio, den lokalen Docker-Image-
Analysis-Worker, Modellstatus, Speicherpfade, Queue-Diagnose und Legacy-Import.
Gemini und automatische Cloud-Fallbacks
gehören nicht zum MVP. Technische Provideroptionen werden klar von normalen
Spieleinstellungen getrennt.

Beim Öffnen und über eine explizite Aktion `Modelle neu erkennen` fragt der
Server LM Studios OpenAI-kompatiblen Modellkatalog ab und reichert ihn bei Bedarf
über die native LM-Studio-v1-API um geladen/lokal-vorhanden und Instance-State
an. Die Oberfläche zeigt keine manuell gepflegte Freitext-ID als normalen Pfad.

Die drei LM-Studio-Zuordnungen und die beiden getrennten Funktionen des Docker-
Image-Analysis-Providers werden getrennt dargestellt:

- Prompt Machine,
- Character Speaker,
- Text Embeddings,
- Image Description,
- Image Embeddings.

Jedes LM-Studio-Dropdown enthält ausschließlich entdeckte Modelle mit passendem
Typ und bestandenem funktionsbezogenem Capability-Test. `geladen`, `lokal, wird
bei Bedarf geladen`, `Test ausstehend`, `ungeeignet` und `nicht mehr gefunden`
sind unterscheidbare Zustände. Prompt Judge darf in den Advanced Settings ein
eigenes Modell erhalten, erbt standardmäßig aber die Prompt Machine.

Vor jeder Anzeige als Kandidat filtert die globale Modellpolicy sämtliche
Meta-/Facebook-Gewichte und abgeleiteten Weight-Lineages aus allen KI-Rollen.
Das betrifft nicht nur Image Analysis, sondern auch LLMs, Text Embeddings,
Vision, Segmentierung, Matting, Generation und Training; Llama und SAM sind
damit ausgeschlossen. Nicht vollständig belegte Lineage erscheint als
`lineage_unverified` und kann nicht ausgewählt werden.

Text Embeddings laufen als eigene LM-Studio-Funktion; Qwen3-Embedding-0.6B mit
festem 1024-dimensionalem Vertrag und CPU-first-Ausführung ist die
Qualifikationsreferenz. Die Bildbeschreibung wird nicht als freies
LM-Studio-Dropdown angeboten. Sie zeigt die feste, versionierte Docker-Bindung
auf Huihui Qwen3-VL 8B Instruct Abliterated, Providerstatus, Schema- und
Fixture-Test sowie Scope-Coverage für `standard`, `sexy`, `lewd`, `nude` und
`explicit`. Nach erfolgreichem Output-Ingest darf sie eine strukturierte
`MachineImageObservation` erzeugen. Im normalen Qualifier-, Ranking-, Arena-
oder Kalibrierungsscreen erscheint daraus jedoch kein zusätzlicher
Bestätigen-/Korrigieren-/Ablehnen-Block. Die Spielerprüfung erfolgt im
eigenständigen Beschreibungstest mit einer Beschreibung und zwei behaltenen
Bildkarten derselben Figur. Eine Maschinenbeobachtung ist kein Keep, Favorite,
Champion, Reject, Qualitätsurteil oder Kanonfakt.

Die validierte Maschinenbeobachtung darf zusätzlich eine verständliche
Kartenbeschreibung vorschlagen. Die UI hält technische Rohbeschreibung,
revisionsgebundene Match-Evidence, eine daraus abgeleitete semantische
Beschreibung und lokalisierte Karten-Copy auseinander. Insbesondere wird
englischer VLM-Rohtext nicht ungeprüft zum deutschen Kartentitel. Der
Beschreibungstest zeigt nur den Text, zwei große Karten, die konkrete Frage und
die Auswahlhandlungen. Modell-, Schema-, Prompt-, Similarity-, Pairing- und
Dateiprovenienz liegen in Advanced.

Image Embeddings erscheinen als separate Statusgruppe desselben lokalen Docker-
Workers mit festen Bindungen für `full_frame_semantic`/`style_view`,
`character_crop` und `anime_attribute_findings`. Sie zeigt Providerstatus,
Modell und feste Revision, Dimension beziehungsweise Tagger-Schema,
Preprocessingrevision, Fixture-Test und Five-Scope-Coverage. Bis der jeweilige
Vektor-/Befundvertrag verifiziert ist, bleibt nur diese Bindung `unavailable`;
beliebige Modelle werden nicht angeboten. Nur Image Embeddings zeigen zusätzlich
`waiting_for_human_evidence`, solange weder ein kompatibles Favorite noch eine
scopekompatible `APPROVED ChampionRevision` noch ausdrücklich vorhandenes
kompatibles Legacy-Referenzmaterial die scopegebundene
`ImageAnalysisBootstrapRevision` erzeugt hat. Favorite und Champion sind für
diese Referenzfreigabe gleichwertig; ein Keep ist positive Evidence, aber allein
kein Bootstrap-Schlüssel. In diesem Zustand dürfen bereits
Bildbeschreibungs- und Textvektor-Jobs existieren, aber noch keine persönlichen
Bildvektoren oder Anchor Sets. Danach zeigt die UI getrennt vorläufig positive
Keep-, stärkere Favorite-/Champion-Referenzen und explizit Human-gelabelte
negative Befunde; sie stellt keinen Similarity-Score als Qualitätsurteil dar.

Die Settings zeigen zusätzlich die daraus abgeleitete Funktionsverfügbarkeit,
nicht nur einen grünen Serverstatus:

```text
Prompt Machine        ready | model_missing | schema_failed | busy
Character Speaker     ready | model_missing | contract_failed | busy
Text Embeddings       ready | model_missing | dimension_mismatch | busy
Image Description     ready | provider_missing | model_missing | lineage_unverified
                      | schema_failed | test_failed | busy
Image Embeddings      waiting_for_human_evidence | ready | provider_missing
                      | model_missing | lineage_unverified | test_failed | busy
Image Generation      ready | workflow_missing | dependency_missing | busy
LoRA Training         ready | workflow_missing | dependency_missing | busy
```

## Settings-State und Funktionen

```text
GlobalSettings
├─ content_policy
├─ generation_defaults
├─ game_preferences
├─ accessibility_preferences
├─ provider_preferences
│  └─ LocalAiModelAssignments
└─ settings_revision
```

Grobe Modulgrenze:

- `get_global_settings`
- `update_content_policy`
- `update_generation_defaults`
- `update_game_preferences`
- `update_accessibility_preferences`
- `discover_lm_studio_models`
- `update_local_ai_model_assignment`
- `test_local_ai_function_capability`
- `test_provider_connection`
- `snapshot_effective_generation_settings`

Sicherheits-, Content- und Generierungsregeln werden serverseitig gespeichert.
Rein lokale Darstellungsdetails dürfen zusätzlich clientseitig gecacht werden,
aber der Browser ist nicht die einzige Source of Truth für fachlich wirksame
Einstellungen.

## Verbindlicher Frontend-Schnitt nach der AIAM-Architektur

Die laufende AIAM-Architektur wird zuerst abgeschlossen. Unmittelbar danach und
vor dem praktischen Gate `M6_LEARNING_LOOP_PROVEN` folgt ein eigener
Frontend-/Spielbarkeits-Schnitt. Er setzt keine neue fachliche Architektur und
interpretiert keine Spielregeln neu, sondern projiziert die dann verfügbaren
Serververträge verständlich, schnell und durchgängig spielbar.

Für diesen Schnitt gilt die Zuständigkeitsgrenze als Abnahmeinvariante:

| Oberfläche | Dominante Spielerfrage | Verbotene Doppelung |
|---|---|---|
| Chronicle | Was setze ich jetzt fort beziehungsweise was ist die nächste Hauptaktion? | kein vollständiges Character-Trial-Board |
| Characters | Wie entwickelt sich diese Figur und welche konkrete Lücke besitzt sie? | keine eigene Bewertungsruntime und keine vollständige Kopie des Quest Boards |
| Trials | Welche Aufgabe spiele ich – über alle verfügbaren Figuren und Bindungen hinweg? | keine parallele Character- oder Chronicle-Progressionsansicht und keine Legacy-Unterseiten als eigene Modi |

Eine Quest darf an allen drei Stellen auffindbar sein, besitzt aber genau eine
serverseitige Instanz, genau eine QuestSession und genau eine Trial-Runtime.
Chronicle zeigt neben der laufenden Hauptaktion höchstens eine empfohlene
Folgeaufgabe und einen kompakten Supply-/Generierungsstatus. Characters zeigt
die zur Entwicklung passende kontextuelle Aktion und einen Einstieg in den
globalen Katalog. Die vollständige Auswahl und die tatsächliche
Spielinteraktion liegen unter Trials.

Der Questvorrat benennt die nicht spielbaren Slotzustände getrennt: Eine
Bewertung wird ausgewertet, die nächste Quest wird entwickelt, Bilder werden
vorbereitet oder ein konkreter Integritätsblocker benötigt Prüfung. Eine reine
Soll-/Ist-Differenz behauptet weder Planung noch Generierung. Die Advanced-
Lerndiagnose zeigt zusätzlich CPU-seitige Supply- und Directorjobs, damit ein
Stillstand vor Guardian, LM Studio oder ComfyUI nicht als leere Providerdiagnose
verschwindet. „Nächste Entwicklungsetappen“ bleibt eine Fortschrittsprojektion
und ist kein Beleg für aktive Generierung.

Der globale Trial-Katalog zeigt pro Figur `bereit/gesamt` und nennt daneben
laufende Auswertung, Vorbereitung, fehlende Planung und Blockaden getrennt. Die
Zahl der vollständig gerenderten Trial-Sessions allein ist damit nie wieder die
einzige Aussage zum Vorrat. Die Anzeige stammt aus derselben serverseitigen Slotprojektion wie
Scheduler und Advanced-Diagnose.

Ein `Active`-Zustand muss aus jeder dieser Projektionen mit genau einer
verständlichen Aktion fortsetzbar sein. Sein Link bindet die bestehende
Session-ID und das tatsächliche Rückkehrziel des Einstiegs. Reine
Präsentationsphasen werden serverseitig idempotent fortgeführt und dürfen im
Frontend weder als Pflichtklick noch als aktionsloser Zwischenbildschirm
erscheinen.

Der M6-Frontend-Schnitt endet beim nachweisbaren Lernloop. Sein verbindlicher
Screenumfang sind Loop-/Character-Übersicht, Trial-Briefing, die je Modus
unterscheidbare Trial-Runtime, Trial-Resultat, Supply-/Generierungszustand,
visueller 16er-Cup und ein Zyklusvergleich mit erneutem Einstieg. Die genauen
Arbeits-IDs `M6-01` bis `M6-07` und ihre Spielerfragen stehen in der
[`Network-first VN-Frontend Screen Map`](network-first-vn-frontend-screen-map.md).
Er fingiert keine Feedposts, Chats, Orte, Decks oder Card-Battler-Partien, bevor
deren fachliche und visuelle Slices existieren.

Vor Umsetzung werden nicht entschiedene Produkt- und UX-Fragen gemeinsam
geklärt. Dazu gehören verbindlich die endgültige Liste echter Spielvarianten,
ihr jeweils unterscheidbarer Spielerablauf, ihre erlaubten Aktionen, ihr
Screenbudget pro Bild und die Trennung von Ablauf und gewonnener Evidenz. Erst
danach folgen konkrete Performancebudgets, Verdichtung und Filterung des
Trial-Katalogs sowie die Dauer rein dekorativer Übergänge. Ohne diese Klärung
werden keine Ersatzregeln, zusätzlichen Klicks, Legacy-Modi oder konkurrierenden
Navigationsstrukturen implementiert.

## Pflichtzustände jedes Screens

Jede primäre Oberfläche besitzt:

- einen verständlichen Einstieg und eine primäre Aktion,
- Loading-, Empty-, Ready-, Blocked-, Error- und Success-State,
- klare Herkunft und Wirkung der angezeigten Daten,
- direkten Rückweg zum aktuellen Character-, Run- oder Storykontext,
- Keyboard-, Browser-Back- und Reload-Verhalten,
- sowie responsive Layouts für Mobile, Tablet-Portrait, Tablet-Landscape, 720p,
  1080p und 4K.

Textschwere Menüs, Settings, Chronicle und Debugansichten bleiben DOM-basiert.
Wichtige Bild- und VN-Flächen werden nicht durch dauerhaft offene
Sekundärpanels verdeckt. Seltene Werkzeuge liegen hinter sinnvoll benannten
Unterseiten oder Drawern, nicht hinter einem unspezifischen Sammelmenü.

## Frontend-Definition-of-Done pro Slice

1. Navigation und primäre Aktion sind ohne Dokumentation auffindbar.
2. Sämtliche Pflichtzustände sind implementiert oder bewusst nicht anwendbar.
3. Fachliche Regeln stammen aus dem Serververtrag.
4. Save-Wechsel, Reload und Browser-Back verlieren keinen bestätigten State.
5. Mobile-, Tablet-Portrait-, Tablet-Landscape-, Desktop-, 720p-, 1080p- und
   4K-Layouts wurden geprüft. Auf 4K bleibt die Trial-Bühne höchstens 2400 px
   breit; Bild und aktive Eingabe liegen innerhalb derselben Bühne.
6. Tastaturnavigation, Fokus und Reduced Motion wurden geprüft.
7. Mindestens ein Screenshot- und Interaktionsplaytest ist protokolliert.
8. Alte Links besitzen einen getesteten Redirect- oder Removal-Vertrag.
9. Display-Schriften und Versalsatz bleiben auf kurze Überschriften und
   Modusmarker begrenzt; Fragen, Gründe und Aktionen verwenden eine normal
   gesetzte Leseschrift.

## Bereits entschieden und vom offenen Modusreview getrennt

- `Characters` erklärt Character State, Visual Development, Relationships,
  Memories und LoRA-Fortschritt; `Trials` führt als einziger Rahmen alle
  spielbaren QuestSessions aus. Die finalen Spielvarianten werden nach AIAM vor
  dem Frontend-Coding gemeinsam freigegeben.
- 720p, 1080p oder 4K ist eine globale maximale Ausgabequalität. Ein späterer
  Save darf lediglich Generation Defaults und Spielpräferenzen überschreiben,
  nicht Content Policy, Accessibility oder Provider.
- Die Training-Material-Ansicht zeigt zuerst Readiness, Coverage-Lücken,
  Blocker, erwarteten Aufwand und die primäre Aktion. Recipe-, Dataset-,
  Workflow- und Hash-Lineage liegt in einer aufklappbaren technischen Ebene.

Diese drei Punkte bleiben unabhängig vom offenen Modusreview verbindlich. Für
die Trial-Spielerführung gelten zusätzlich die ausdrücklich offenen Punkte aus
`PM-092`/`DEC-059`; erst nach deren gemeinsamer Freigabe bleiben dort nur noch
Responsive-Dichten, Zeilenlimits und Progressive-Disclosure-Schwellen zu
kalibrieren.

## Reaktive Projektionsgrenze für den Schema-55-Loop

Chronicle, Trials und Character Focus beobachten ausschließlich kleine,
persistierte Projektionsrevisionen beziehungsweise ETags. Ändert sich eine
Revision, wird nur die betroffene Campaign- oder Sessionprojektion aktualisiert.
Scrollposition, Tastaturfokus, ausgewählte Reasons und das aktuell sichtbare
Bild bleiben erhalten. Der Browser startet weder Reconcile, Evidence-Rebuild,
Thumbnail-Rendering noch Providerpolling.

Eine Spieleraktion zeigt innerhalb von 100 ms lokales Klickfeedback. Der
serverautorisierte Command soll im warmen Pfad p95 unter zwei Sekunden, eine
schlanke Projektion p95 unter 1,5 Sekunden antworten. Persistierter
Hintergrundfortschritt soll spätestens innerhalb von fünf Sekunden sichtbar
werden. Das sind Abnahmewerte, keine neue Domainautorität des Frontends.

Noch nicht bestätigte Spielercommands werden vor dem HTTP-Aufruf mit stabilem
Idempotency-Key in IndexedDB abgelegt. Gespeichert werden nur Session-/Attempt-
Bindung und der fachliche Commandpayload; niemals Header, Cookies, Secrets,
Bilder oder Providerdaten. Navigation bricht diesen Mutation-Request nicht ab.
Nach Reload oder Verbindungsverlust sendet der Client exakt denselben Command
erneut. Der Eintrag verschwindet erst nach bestätigtem Servercommit oder einem
eindeutigen Revisionskonflikt; semantisch ungültige Commands bleiben als
klärungsbedürftig markiert und werden nicht endlos automatisch wiederholt.

Lean-Katalog und Shell werden aus einem gemeinsamen query-only Read-Snapshot
und gebündelten Campaign-/Lifecycle-Abfragen erzeugt. GET-Routen rendern keine
Thumbnails synchron; fehlt eine vorbereitete Derivative, darf die Anzeige auf
das persistierte Original verweisen. Eine Revisionsänderung ersetzt nur die
betroffene Campaign-Kartengruppe und darf Scrollposition, Fokus, gewählte
Reasons oder sichtbares Bild nicht verlieren. Während eines Commands wird nur
die betroffene Aktion gesperrt; Navigation und Ready-Quests anderer Campaigns
bleiben verfügbar.

Ready-Quests bleiben bei `preparing`, `waiting_provider` oder einem Fehler einer
anderen Lane anklickbar. Nach dem synchronen Reviewabschluss zeigt die UI nur
den bestätigten Spielerzustand und den asynchronen Nachfüllstatus; sie wartet
nicht auf Evidence, Candidate Planning oder Generation. Dieser Stand ist bis
zum iPad-/4K- und realen Refill-Playtest `LIVE_VERIFICATION_PENDING`.

Schema-56-Projektionen zeigen zusätzlich den verständlichen Experimentnamen,
die konkrete Zielrolle und Achse, technische Vergleichswerte sowie den letzten
persistierten Ablehnungsgrund. Beispiele sind „Modell enthielt sich ohne
Begründung“, „Vorschlag wiederholt eine ausgeschlossene Aspect-Variante“,
„Judge lehnte Candidate-Erhalt ab“ und „Recipe-Diff verletzt die
Versuchsachse“. Diese Diagnose deaktiviert niemals eine bereits Ready gewordene
Quest.
