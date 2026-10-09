# Card Battler — aktiver ComfyReview-POC

**Dokumentklasse:** `IN_PROGRESS` – aktiver ComfyReview-POC, kein fertig spielbares Gesamtprodukt.

**Status (2026-10-09):** **Aktiv in Entwicklung und Erprobung.** Dies ist **keine** implementierte vollständige Spielfunktion und **kein** fixierter Bauplan für Character Chronicles.

## Technisch bereits in ComfyReview nachweisbar

| Teilgebiet | Code / Evidenz | Was das noch nicht beweist |
| --- | --- | --- |
| Kartendomäne | [Immutable Card-/Trait-Fakten](../../comfyreview/domain/card_battler) | Keine durchgehende Spieler-Kartenlebenszeit |
| Externes Modell | [Read-only Card Battler SQLite Model](../../comfyreview/repositories/sqlite/card_battler_model_resource.py), [Tests](../../tests/test_card_battler_model.py) | Produktionsinhalt der externen Modell-DB ist nicht eingecheckt |
| Card-Imprint-Mapping | [Deterministischer Mapper](../../comfyreview/application/card_battler_mapping.py) | Noch kein Kartenentwicklungs-Befehl in der öffentlichen API |
| Mechaniken/Stats | [Materialisierung und Regeltext](../../comfyreview/application/card_battler_rules.py), [Tests](../../tests/test_card_battler_rule_rendering.py) | Keine ausführbare vollständige Matchsimulation |
| Tier/Trait-Entwicklung | [Service](../../comfyreview/application/card_battler_development_service.py), [Golden Path](../../tests/test_card_battler_development_golden_path.py) | Kein integrierter Post-Match-Experience-/Evolution-Flow |
| Visuelle Projektion | [Visual-Prompt-Projektion](../../comfyreview/application/card_battler_visual_projection.py) | Kein fertig gerendertes Card-Face und keine spielerseitige Komposition |

Die [App](../../comfyreview/bootstrap.py) erzeugt Modell-Adapter und Mapper; die [registrierten API-Router](../../routers/api_v2/__init__.py) bieten jedoch **keine** vollständigen Card-Crafting-/Deck-/Match-Operationen. Genau diese Trennung ist wichtig: **funktionierender Bibliotheks-Code ≠ spielbarer Battler**.

## Konkreter Erstversuch: eine Karte von der Bildwahl bis zur Sammlung

**Status:** aktuell vereinbarter **POC-Zielablauf**, noch **kein**
nachgewiesenes End-to-End-Feature. Zunächst soll die **Kartenerzeugung und
-entwicklung** spielerseitig funktionieren; eine fertige Match-Engine ist dafür
keine Voraussetzung.

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
4. **Vier passende Bildalternativen erzeugen.** Das ausgewählte Quellbild
   dient als visuelle Grundlage für **vier** neue Kandidaten, die zum
   Karteninhalt passen. Das sind **vier Bildoptionen für dieselbe Karte**,
   nicht vier automatisch fertiggestellte Karten.
5. **Eine Bildoption auswählen.** Der Spieler wählt **eine der vier**
   Varianten. Diese wird gemeinsam mit dem Karteninhalt zur konkreten Karte
   zusammengesetzt und angezeigt.
6. **Karte übernehmen.** Die bestätigte Karte soll in einer einfachen
   Sammlung wiedergefunden und später als Ausgangspunkt einer Entwicklung
   genutzt werden können.
7. **Karte weiterentwickeln.** Von der bestehenden Karte aus wird der
   inhaltliche Entwicklungsstand (z. B. Stats, Mechaniken und Text) fortgeführt;
   anschließend folgt erneut ein Durchlauf mit **vier passenden
   Bildalternativen** und **einer bewussten Auswahl**. Ob und wie ältere
   Stände erhalten bleiben, ist noch zu erproben.
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
**Nicht** als fertiger End-to-End-Ablauf nachgewiesen ist dagegen die
automatische Erstellung des semantischen Profils aus einem realen Bild samt
Spielerfreigabe und vollständiger Kartenübernahme. Bildanalysemodell,
Provider, Prüf-UI und Persistenzvertrag bleiben offen.

Dieser Ablauf beschreibt das gewünschte **Spielerlebnis des ersten Versuchs**.
Er schreibt weder das Datenbankschema noch einen bestimmten LLM-Provider,
Bildgenerierungsweg, Renderer oder feste Regel-/Balancing-Versionen vor.
Die bestehenden Algorithmen und der Generator können dafür verwendet
und geprüft werden, ersetzen aber nicht die noch fehlende Integration.

### Technische Lücken, die der Erstversuch tatsächlich prüfen muss

Der aktuelle [ComfyUI-Blueprint v4](../../data/workflows/default-character/v4.json)
verwendet `EmptySD3LatentImage` und besitzt keinen direkt gebundenen
Quellbild-Eingang. Die bestehende Text-zu-Bild-Generierung kann zwar neue
Ergebnisse produzieren, garantiert aber **keine visuelle Kontinuität**
zum ausgewählten Quellbild. Ob passende Varianten durch andere
Konditionierung, einen separaten Workflow oder einen weiteren Ansatz
erzeugt werden, ist **offen** und muss praktisch erprobt werden.
Vier technisch fertige PNGs allein erfüllen diesen POC daher nicht.

Auch das bisherige `SemanticImageProfile` speichert typisierte
Konzeptsignale mit Stärken, aber **noch keine eigenständige Zuordnung**
von sichtbaren Beobachtungen, Interpretationen und Unsicherheiten.
Die fachliche Trennung in Stufe 1 ist somit ein **Abnahmeziel**,
nicht schon als implementiertes Bildverständnis nachgewiesen.
Weder eine bestimmte VLM-/LLM-Lösung noch eine neue API wird
hierdurch vorab festgelegt.

## Minimale Oberfläche für den Versuch

Der POC benötigt einen nachvollziehbaren Weg, **ein Quellbild auszuwählen**,
den **Kartenentwurf mit Stats und Text zu prüfen**, **vier Bilder zu
vergleichen**, **eines zu übernehmen** und die **Karte in einer kleinen
Sammlung erneut aufzurufen und weiterzuentwickeln**.

Dafür waren **eine oder zwei schlanke Frontend-Seiten** als erste Lösung
angedacht, nicht die vollständige spätere Card-Battler-/Social-/VN-UI.
Die konkrete Aufteilung und technische Umsetzung werden am POC erprobt.
Eine Sammlung von 40 Karten belegt noch **keinen** spielbaren Kampf- oder
Deckbauablauf; diese Integration muss separat nachgewiesen werden.

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
3. **Tatsächlich passende Auswahl:** Für **dieselbe** Kartenidee
   entstehen vier unterscheidbare, zum Quellmotiv und Karteninhalt
   passende Bildkandidaten. Fehlschläge oder unpassende Ergebnisse
   werden sichtbar; sie zählen nicht als erfolgreich erstellte Karte.
4. **Eine bestätigte Karte:** Der Spieler wählt bewusst genau
   einen Kandidaten. Bild, Kartenwerte, Text und Herkunft werden
   zusammen angezeigt und sind nach einem App-Neustart in der
   Sammlung wieder auffindbar; vier Vorschläge erzeugen **nicht**
   automatisch vier Karten.
5. **Entwicklung statt Duplikat:** Von dieser Karte aus kann erneut
   entwickelt und zwischen vier neuen Alternativen gewählt werden.
   Die Weiterentwicklung bleibt nachvollziehbar derselben Kartenidentität
   zugeordnet; wie ältere Versionen dauerhaft dargestellt und
   gespeichert werden, muss im POC erprobt werden.
6. **Versuchsumfang und Evidenz:** Die angestrebten 40 einzeln
   bestätigten Karten bilden ein **Testdeck-Ziel**, keine globale
   Deckgrößenregel. UI-Ablauf, Persistenz und relevante Fehlerfälle
   werden mit Tests und wenigstens einer realen Bedien-/Providerprobe
   geprüft. Eine Match-Engine ist **keine Voraussetzung** für diesen
   ersten Karten-Erzeugungsloop.

Die Abnahme dieser Kriterien muss mit konkreter Laufzeit- und
Bedienevidenz belegt werden. Isolierte grüne Algorithmentests
oder vier generierte Dateien reichen dafür nicht aus.

## Warum der Card Battler gerade zuerst kommt

Die konkrete Academy-/Worldbuilding-/Character-Chronicles-Vision entstand
erst nach früheren Implementierungsversuchen. Statt gleich wieder mit
kompletter VN-, Guardian- oder Schuljahres-Laufzeit zu beginnen, soll
der Card Battler zunächst als **spielerischer Kern in ComfyReview**
tatsächlich funktionieren und in der Praxis erprobt werden.

Danach ist die ungefähre Entwicklungsorientierung **Timeline →
Social Network mit Charakter-Chats → Storyline → VN-Content zuletzt**.
Die Timeline kann zuerst als kleiner Social-Slice erprobt werden, ohne
sofort die vollständige Plattform zu bauen. **Academy/Schuljahr** ist
ein möglicher Story-/Weltkontext, aber keine zusätzlich beschlossene
Pflichtphase. Figurenfreistellung und Szenenkomposition sind erheblich
komplexere Bild-/Asset-Aufgaben und **keine Voraussetzung für diesen POC**.
[Entwicklungsorientierung](../PROJECT_EVOLUTION.md#gewonnene-reihenfolge-aus-den-bisherigen-versuchen).

Das definiert weder eine feste Deck-/Kampfarchitektur noch ein Releasegate,
bis zu dem sämtliche künftigen Konzepte bereits entschieden sein müssten.

## Ausdrücklich noch offen

Offen bleiben **Umsetzung und Abnahme** dieses Ablaufs: Kartenzustand und Persistenz, konkrete Frontend-Aufteilung, Karteninhalt-/Bildvarianten-Erzeugung, Weiterentwicklungsdetails und Versionierung sowie Deck-/Kampfregeln, Integration und der spätere Einsatz in Character Chronicles. Der **erste Spielerablauf und das 40-Karten-Testziel** sind damit benannt, aber keine fertige Funktion und kein dauerhaft bindender Architektur- oder Balancing-Vertrag. Es gibt weiterhin **keinen vorgeschriebenen 7-Phasen-Implementierungsplan**.

Der bereits vor dem Dokumentenimport geschriebene [Card-Battler-Zielplan vom 2026-10-02](../archive/card-battler-target-2026-10-02.md) und die umfangreichen [Chronicles-Battler-Konzepttexte](../character-chronicles/sources/README.md) enthalten fachlich und technisch möglicherweise wertvolle Ideen. Sie sind **Referenzmaterial**, nicht das automatische Architekturmandat für den aktuellen POC.

## Wann sich dieser Status ändert

Ein Test für einen deterministischen Algorithmus bedeutet nicht, dass das zugehörige Spielmodul abgeschlossen ist. Für eine konkrete Integration die dafür zuständigen Services, registrierte API, UI, Persistenz und Tests am neuen Commit prüfen. Bis dahin **POC in Arbeit**.

[ComfyReview-Gesamtstand](../ACTIVE_WORK.md) · [Produktentwicklung](../PROJECT_EVOLUTION.md)
