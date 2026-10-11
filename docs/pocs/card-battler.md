# Card Battler — aktiver ComfyReview-POC

**Dokumentklasse:** `IN_PROGRESS` – aktiver ComfyReview-POC, kein fertig spielbares Gesamtprodukt.

**Status (2026-10-11):** **Aktiv in Entwicklung und Erprobung.** Dies ist **keine** implementierte vollständige Spielfunktion und **kein** fixierter Bauplan für Character Chronicles.

## Technisch bereits in ComfyReview nachweisbar

| Teilgebiet | Code / Evidenz | Was das noch nicht beweist |
| --- | --- | --- |
| Kartendomäne | [Immutable Card-/Trait-Fakten](../../comfyreview/domain/card_battler) | Keine durchgehende Spieler-Kartenlebenszeit |
| Externes Modell | [Read-only Card Battler SQLite Model](../../comfyreview/repositories/sqlite/card_battler_model_resource.py), [Tests](../../tests/test_card_battler_model.py) | Für Card Battler erforderlich und später mitzuliefern; reale Inhaltsabnahme bleibt offen |
| Card-Imprint-Mapping | [Deterministischer Mapper](../../comfyreview/application/card_battler_mapping.py) | Noch keine reale Bild-/Modellabnahme |
| Mechaniken/Stats | [Materialisierung und Regeltext](../../comfyreview/application/card_battler_rules.py), [Tests](../../tests/test_card_battler_rule_rendering.py) | Keine ausführbare vollständige Matchsimulation |
| Tier/Trait-Entwicklung | [Service](../../comfyreview/application/card_battler_development_service.py), [Golden Path](../../tests/test_card_battler_development_golden_path.py) | Kein integrierter Post-Match-Experience-/Evolution-Flow |
| Visuelle Projektion | [Visual-Prompt-Projektion](../../comfyreview/application/card_battler_visual_projection.py) | Kein fertig gerendertes Card-Face und keine spielerseitige Komposition |
| Semantische Bildanalyse | [Strikter Stage-1-Analyzer](../../comfyreview/application/card_battler_semantics.py), [kanonischer Bildadapter](../../comfyreview/providers/card_source_images.py) | Noch keine reale Modellabnahme |
| Kosmetische Kartentexte | [Stage-3-Realizer](../../comfyreview/application/card_battler_presentation.py) | Keine Autorität über Regeln und noch keine reale Modellabnahme |
| Wiederverwendbare Factory | [Orchestrator](../../comfyreview/application/card_battler_factory.py) | In Candidate Groups verdrahtet; reale Modell-/Bildqualitätsabnahme fehlt |
| Isolierte POC-Runtime | [Versionierter Schema-Owner](../../comfyreview/repositories/sqlite/card_battler_runtime_schema.py), [Group-Repository](../../comfyreview/repositories/sqlite/card_battler_candidate_groups.py), [Card-Pool](../../comfyreview/repositories/sqlite/card_battler_card_pool.py), [Deck](../../comfyreview/repositories/sqlite/card_battler_deck.py) | Schema v2, CAS-API und vier UI-Seiten vorhanden; reale Providerprobe fehlt |
| Asynchroner Gruppenlauf | [Worker](../../comfyreview/application/card_battler_candidate_processing.py), [Group-Service](../../comfyreview/application/card_battler_candidate_group_service.py) | Ein Analyse-/Mapping-Lauf und vier vollständige Candidates sind automatisiert isoliert geprüft; reale Laufzeitabnahme fehlt |
| Img2img-Handoff | [Dedizierter Blueprint](../../data/workflows/card-evolution/v1.json), [Multipart-Stager](../../comfyreview/providers/comfyui_uploads.py), [Candidate-Image-Service](../../comfyreview/application/card_battler_candidate_image_service.py) | Kandidatenspezifische Bilder und Reconcile sind implementiert; reale ComfyUI-Abnahme fehlt |

Die [App](../../comfyreview/bootstrap.py) verdrahtet den Card-Factory-POC und
seinen Worker; der [Card-Factory-Router](../../routers/api_v2/card_factory.py)
bietet Group-, Candidate-Accept-, Pool-, Development- und POC-Deck-Operationen.
Es gibt weiterhin **keine endgültige Collection**, Mehrdeck-, Match-, Combat-
oder XP-Runtime. Genau diese Trennung ist wichtig: **funktionierender
Karten-/Deck-POC ≠ spielbarer Battler**.

## Konkreter Erstversuch: eine Karte von der Bildwahl bis zur Sammlung

**Status:** aktuell vereinbarter **ComfyReview-Entwicklungs-POC**. Der
technische Create-/Candidate-/Accept-/Develop-Ablauf ist mit Fake-Providern
durchgängig automatisiert nachgewiesen; ein realer LM-Studio-/ComfyUI-Lauf und
die fachliche Bildqualitätsabnahme fehlen weiterhin. Eine fertige Match-Engine
ist dafür keine Voraussetzung.

**Wichtig ist der Unterschied zum späteren Spiel:** Im **ComfyReview-POC**
darf der Nutzer eine ganze Gruppe aus vier vollständigen Karten verwerfen und
eine neue Gruppe anfordern, um Qualität und Passung iterativ zu prüfen.
Im geplanten **Character Chronicles** soll dagegen **eine der vier
Varianten ausgewählt** werden. Die Entwicklungsfunktion »alle
ablehnen und erneut versuchen« wird daher **nicht** stillschweigend
zur Spielmechanik. [Späteres Spielerziel](../character-chronicles/vision/card-battler.md).

1. **Ein Quellbild wählen.** Pro Durchlauf wird **genau ein** bereits
   vorhandenes Bild aus ComfyReview als Ausgangspunkt gewählt. Es werden nicht
   automatisch alle Bilder zu Karten verarbeitet.
2. **Stufe 1 – Bildinhalt verstehen.** Zunächst werden beobachtbare Motive,
   Merkmale und visuelle Zusammenhänge des Quellbilds in einem
   **spielmechanikfreien semantischen Bildprofil** erfasst. Sichtbare Fakten,
   Interpretationen und Unsicherheiten müssen unterscheidbar bleiben:
   Bildverständnis vergibt **noch keine** Kartenwerte oder Fähigkeiten.
3. **Stufe 2 – regelkonforme Karte ableiten.** Erst das semantische Profil
   wird anhand des versionierten Card-Battler-Regelwerks in ein
   `CardImprint` und passende **Stats, zulässige Mechaniken und lesbaren
   Kartentext** überführt. Text, Werte und Motiv sollen inhaltlich
   zusammenpassen, ohne dass eine freie KI-Antwort neue Regeln erfindet.
4. **Vier vollständige Karten erzeugen.** Das ausgewählte Quellbild wird pro
   initialer Gruppe genau einmal analysiert und gemappt. Die vier Kandidaten
   teilen Imprint-DNA, StatProfile und Grundmechanik, variieren aber zulässige
   Stats/Parameter, Presentation, Visual Recipe und erzeugtes Bild.
5. **Eine Karte auswählen oder die Gruppe verwerfen.** Der Spieler kann
   **eine der vier erfolgreichen vollständigen Karten** auswählen oder die
   ganze Gruppe ablehnen. Ein initialer Neuversuch ist absichtlich eine neue
   Analyse samt neuem Mapping; ohne Accept entsteht keine Poolkarte.
6. **Karte übernehmen.** Accept erzeugt eine stabile `card_id`; die bestätigte
   Karte ist im POC-Kartenpool wieder auffindbar und kann in das POC-Deck
   aufgenommen oder als Ausgangspunkt einer Entwicklung verwendet werden.
7. **Karte weiterentwickeln.** Von der bestehenden Karte aus wird der
   inhaltliche Entwicklungsstand (z. B. Stats, Mechaniken und Text) fortgeführt;
   anschließend folgt erneut ein Durchlauf mit **vier vollständigen
   Kartenalternativen** und **einer bewussten Auswahl**. Semantik, Imprint-DNA,
   StatProfile und `card_id` bleiben unverändert; jeder Kandidat geht genau
   einen Tier und führt genau eine legale Trait-Aktion aus. Werden alle
   Varianten verworfen, bleibt der aktuelle Kartenzustand unverändert.
8. **Schrittweise ein erstes Deck aufbauen.** Der anfängliche
   **Versuchsumfang beträgt 40 einzeln erzeugte Karten für ein Testdeck**.
   Das ist ein konkretes Arbeitsziel für den POC, **keine dauerhaft
   beschlossene Deckgrößen- oder Spielregel**.

Die **fachliche Trennung der Stufen 1 und 2** ist Teil des aktuellen
POC-Ziels: erst beschreiben, was das Bild zeigt, dann daraus eine Karte
**innerhalb des Regelwerks** erzeugen. Im Code gibt es dafür bereits den
typisierten [`SemanticImageProfile` und den deterministischen
`CardImprintMapper`](../../comfyreview/application/card_battler_mapping.py)
sowie die getrennte
[Regel-/Wertematerialisierung](../../comfyreview/application/card_battler_common.py).
Ein injizierbarer Stage-1-Analyzer und ein Adapter über die bestehende
kanonische Bildauflösung sind inzwischen implementiert und isoliert getestet.
**Nicht** als real abgenommen sind dagegen die Modellinferenz, tatsächliche
ComfyUI-Bildentwicklung, Bildqualität und Bedienung. Runtime-Komposition,
Group-/Pool-/Deck-Befehle und die funktionale Prüf-UI sind implementiert und
fokussiert automatisiert getestet. Der Persistenzvertrag
ist als isolierte `card_battler_runtime.sqlite3` umgesetzt: Die normale
`comfyreview.sqlite3` wird nur zur Quellbildauflösung gelesen, während die
read-only `card_battler.sqlite3` ausschließlich Regel-/Modelldaten liefert.
Die Regel-/Modelldatenbank ist für Card Battler erforderlich und muss mit der
Funktion ausgeliefert werden; die Anwendung erzeugt oder repariert sie nicht.

Dieser Ablauf beschreibt das gewünschte **Spielerlebnis des ersten Versuchs**.
Er schreibt weder das Datenbankschema noch einen bestimmten LLM-Provider,
Bildgenerierungsweg, Renderer oder feste Regel-/Balancing-Versionen vor.
Die bestehenden Algorithmen und der Generator können dafür verwendet
und geprüft werden, ersetzen aber nicht die noch fehlende Integration.

### Technische Lücken, die der Erstversuch tatsächlich prüfen muss

Der allgemeine [ComfyUI-Blueprint v4](../../data/workflows/default-character/v4.json)
bleibt ein Text-zu-Bild-Workflow. Für Card Evolution existiert deshalb der
separate [Blueprint `card-evolution/v1`](../../data/workflows/card-evolution/v1.json),
der das aktive Referenzbild über `LoadImage`, VAE-Encoding und img2img-Sampling
bindet. Compilation, Upload, vier stabile Requests und die Referenzkette über
zwei Generationen sind automatisiert geprüft. Ob der Workflow mit dem realen
Checkpoint die gewünschte visuelle Kontinuität und Qualität erreicht, muss der
Projektinhaber weiterhin praktisch abnehmen. Vier technisch fertige PNGs
allein erfüllen diesen POC nicht.

Das erweiterte `SemanticImageProfile` speichert eine kurze Zusammenfassung,
begrenzte sichtbare Faktengruppen und kontrollierte Konzeptsignale mit
Stärken. Das ist eine implementierte, spielmechanikfreie Vertragsgrenze, aber
noch kein Nachweis, dass das konfigurierte reale Vision-Modell Bilder fachlich
ausreichend versteht. Modellqualität und Unsicherheitsdarstellung bleiben
deshalb Abnahmeziele statt behaupteter Ergebnisse; die vorhandene Prüf-UI
macht die gelieferten Fakten sichtbar, beweist aber nicht deren fachliche
Richtigkeit.

## Minimale Oberfläche für den Versuch

Der POC benötigt einen nachvollziehbaren Weg, **ein Quellbild auszuwählen**,
**vier vollständige Karten mit Stats, Text und Bild zu vergleichen**, eine
davon zu übernehmen oder die ganze Gruppe abzulehnen, sowie die bestätigte
Karte im POC-Pool wiederzufinden, dem Deck hinzuzufügen und
weiterzuentwickeln.

Dafür existieren vier schlanke Seiten: `/card-factory` für die Quellwahl,
`/card-candidate-groups` für laufende und terminale Gruppen,
`/card-candidate-groups/{group_id}` für den Vergleich vier vollständiger
Karten sowie `/card-deck` für POC-Pool, Deckreihenfolge und Development-Start.
Sie verwenden serverseitige Aktionsprojektionen und enthalten keine
Spielregeln. Das ist nicht die vollständige spätere Card-Battler-/Social-/VN-UI.
Ein auf 40 eindeutige Karten begrenztes POC-Deck belegt noch **keinen**
spielbaren Kampf- oder endgültigen Deckbauablauf.

## Prüfkriterien für die erste spielerseitige POC-Abnahme

Diese Kriterien beschreiben **nachweisbare Spielerergebnisse**,
keine bereits bestehende Funktion, keinen Datenbankvertrag
und keine dauerhaft unveränderlichen Spielregeln:

1. **Bewusste Quelle:** Ein bestimmtes vorhandenes ComfyReview-Bild
   wird vom Spieler ausgewählt; Herkunft und stabile Bildidentität
   bleiben bis zur bestätigten Karte nachvollziehbar.
2. **Bildverständnis und Regelgrenze:** Sichtbare Beobachtungen,
   Interpretationen und Unsicherheiten können geprüft werden;
   Kartenwerte, Fähigkeiten und Text werden erst danach aus einem
   versionierten Regelkontext abgeleitet. Freie Modellantworten dürfen
   nicht eigenmächtig gültige Karteneffekte festlegen.
3. **Tatsächlich passende Auswahl:** Aus einer Analyse und einem Mapping
   entstehen vier vollständige, gemeinsam geprägte Karten mit sichtbaren
   Stats, Traits, Regeln, Presentation und Bild. Fehlschläge bleiben pro Slot
   sichtbar; nur erfolgreiche Kandidaten sind annehmbar.
4. **Auswahl ohne Zwang:** Der Spieler kann genau einen Kandidaten
   bestätigen oder den gesamten Vierer-Durchlauf verwerfen und vier
   neue Varianten anfordern. Eine Ablehnung erzeugt **keine bestätigte
   Karte**; vier Vorschläge erzeugen ebenfalls nicht automatisch vier
   Poolkarten. Nach Bestätigung werden Bild, Kartenwerte, Text und Herkunft
   zusammen angezeigt und sind nach einem App-Neustart auffindbar.
5. **Entwicklung statt Duplikat:** Von dieser Karte aus kann erneut
   entwickelt und zwischen vier neuen Alternativen gewählt werden.
   Die Weiterentwicklung bleibt nachvollziehbar derselben Kartenidentität
   zugeordnet. Werden alle Varianten abgelehnt, bleibt der vorherige
   bestätigte Kartenzustand erhalten. Ein Accept behält die `card_id` und
   ersetzt revisionssicher nur den aktuellen spielbaren POC-Zustand.
6. **Versuchsumfang und Evidenz:** Die angestrebten 40 einzeln
   bestätigten Karten bilden ein **Testdeck-Ziel**, keine globale
   Deckgrößenregel. UI-Ablauf, Persistenz und relevante Fehlerfälle
   werden mit Tests und wenigstens einer realen Bedien-/Providerprobe
   geprüft. Eine Match-Engine ist **keine Voraussetzung** für diesen
   ersten Karten-Erzeugungsloop.

Die Abnahme dieser Kriterien muss mit konkreter Laufzeit- und
Bedienevidenz belegt werden. Isolierte grüne Algorithmentests
oder vier generierte Dateien reichen dafür nicht aus.
**Die abschließenden manuellen Funktions- und Bedientests sowie
die POC-Abnahme führt der Projektinhaber selbst durch.**
Entwickler- und CI-Tests liefern dafür Vorprüfung, ersetzen aber
keine persönliche Abnahme.

## Warum der Card Battler gerade zuerst kommt

Die [bestätigte Zielwelt von Character Chronicles](../character-chronicles/vision/world.md)
spielt ab 2032 in Kobe, umfasst zwei erwachsene Academy-Jahre und eine
seit Jahren etablierte globale Social-/Battler-Kultur. Ihre Figuren,
Beziehungen und langfristige VN-Geschichte sind als Spielerlebnis gesetzt.
Statt aber die alte VN-, Guardian- oder Schuljahres-Runtime zu übernehmen,
soll
der Card Battler zunächst als **spielerischer Kern in ComfyReview**
tatsächlich funktionieren und in der Praxis erprobt werden.

Danach ist die ungefähre Entwicklungsorientierung **Timeline →
Social Network mit Charakter-Chats → Storyline → VN-Content zuletzt**.
Die Timeline kann zuerst als kleiner Social-Slice erprobt werden, ohne
sofort die vollständige Plattform zu bauen. **Academy/Schuljahr**
ist bereits **bestätigter Welt- und Storykontext**, aber keine
zusätzlich beschlossene technische Pflichtphase. Figurenfreistellung und Szenenkomposition sind erheblich
komplexere Bild-/Asset-Aufgaben und **keine Voraussetzung für diesen POC**.
[Entwicklungsorientierung](../PROJECT_EVOLUTION.md#gewonnene-reihenfolge-aus-den-bisherigen-versuchen).

Das definiert weder eine feste Deck-/Kampfarchitektur noch ein Releasegate,
bis zu dem sämtliche künftigen Konzepte bereits entschieden sein müssten.

## Ausdrücklich noch offen

Offen bleiben insbesondere die **reale Abnahme** von Semantik, Bildvarianten,
Bildqualität und Bedienung sowie die endgültige Collection, mehrere Decks,
ältere sichtbare Kartenrevisionen, Deck-/Kampfregeln, Matches, XP und der
spätere Einsatz in Character Chronicles. Der funktionale Vier-Seiten-Ablauf
ist ein technischer POC, keine fertige Spielfunktion. Die im POC technisch
erzwungene 40-Karten-Grenze ist kein dauerhaft bindender Balancing-Vertrag. Es
gibt weiterhin **keinen vorgeschriebenen 7-Phasen-Implementierungsplan**.

Der bereits vor dem Dokumentenimport geschriebene [Card-Battler-Zielplan vom 2026-10-02](../archive/card-battler-target-2026-10-02.md) und die umfangreichen [Chronicles-Battler-Konzepttexte](../character-chronicles/sources/README.md) enthalten fachlich und technisch möglicherweise wertvolle Ideen. Sie sind **Referenzmaterial**, nicht das automatische Architekturmandat für den aktuellen POC.

## Wann sich dieser Status ändert

Ein Test für einen deterministischen Algorithmus bedeutet nicht, dass das zugehörige Spielmodul abgeschlossen ist. Für eine konkrete Integration die dafür zuständigen Services, registrierte API, UI, Persistenz und Tests am neuen Commit prüfen. Bis dahin **POC in Arbeit**.

[ComfyReview-Gesamtstand](../ACTIVE_WORK.md) · [Produktentwicklung](../PROJECT_EVOLUTION.md)
