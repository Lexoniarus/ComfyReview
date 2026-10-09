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
2. **Karteninhalt entwerfen.** Für dieses eine Motiv werden stimmige
   Karteninformationen erstellt: insbesondere **Stats, Fähigkeiten/Mechaniken
   und lesbarer Kartentext**. Text, Werte und Motiv sollen inhaltlich
   zusammenpassen; die technische Methode der Erstellung ist noch offen.
3. **Vier passende Bildalternativen erzeugen.** Das ausgewählte Quellbild
   dient als visuelle Grundlage für **vier** neue Kandidaten, die zum
   Karteninhalt passen. Das sind **vier Bildoptionen für dieselbe Karte**,
   nicht vier automatisch fertiggestellte Karten.
4. **Eine Bildoption auswählen.** Der Spieler wählt **eine der vier**
   Varianten. Diese wird gemeinsam mit dem Karteninhalt zur konkreten Karte
   zusammengesetzt und angezeigt.
5. **Karte übernehmen.** Die bestätigte Karte soll in einer einfachen
   Sammlung wiedergefunden und später als Ausgangspunkt einer Entwicklung
   genutzt werden können.
6. **Karte weiterentwickeln.** Von der bestehenden Karte aus wird der
   inhaltliche Entwicklungsstand (z. B. Stats, Mechaniken und Text) fortgeführt;
   anschließend folgt erneut ein Durchlauf mit **vier passenden
   Bildalternativen** und **einer bewussten Auswahl**. Ob und wie ältere
   Stände erhalten bleiben, ist noch zu erproben.
7. **Schrittweise ein erstes Deck aufbauen.** Der anfängliche
   **Versuchsumfang beträgt 40 einzeln erzeugte Karten für ein Testdeck**.
   Das ist ein konkretes Arbeitsziel für den POC, **keine dauerhaft
   beschlossene Deckgrößen- oder Spielregel**.

Dieser Ablauf beschreibt das gewünschte **Spielerlebnis des ersten Versuchs**.
Er schreibt weder das Datenbankschema noch einen bestimmten LLM-Provider,
Bildgenerierungsweg, Renderer oder feste Regel-/Balancing-Versionen vor.
Die bestehenden Algorithmen und der Generator können dafür verwendet
und geprüft werden, ersetzen aber nicht die noch fehlende Integration.

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

## Warum der Card Battler gerade zuerst kommt

Die konkrete Academy-/Worldbuilding-/Character-Chronicles-Vision entstand
erst nach früheren Implementierungsversuchen. Statt gleich wieder mit
kompletter VN-, Guardian- oder Schuljahres-Laufzeit zu beginnen, soll
der Card Battler zunächst als **spielerischer Kern in ComfyReview**
tatsächlich funktionieren und in der Praxis erprobt werden.

Danach ist die übergeordnete Idee eine **Social-Network-Timeline samt
Charakter-Chats**; die **Academy-/Schuljahresentwicklung** wird daran
angeschlossen, während die **vollständige visuelle VN zuletzt** folgt.
Figurenfreistellung und Szenenkomposition sind erheblich komplexere
Bild-/Asset-Aufgaben und **keine Voraussetzung für den jetzigen POC**.
[Entwicklungsorientierung](../PROJECT_EVOLUTION.md#gewonnene-reihenfolge-aus-den-bisherigen-versuchen).

Das definiert weder eine feste Deck-/Kampfarchitektur noch ein Releasegate,
bis zu dem sämtliche künftigen Konzepte bereits entschieden sein müssten.

## Ausdrücklich noch offen

Offen bleiben **Umsetzung und Abnahme** dieses Ablaufs: Kartenzustand und Persistenz, konkrete Frontend-Aufteilung, Karteninhalt-/Bildvarianten-Erzeugung, Weiterentwicklungsdetails und Versionierung sowie Deck-/Kampfregeln, Integration und der spätere Einsatz in Character Chronicles. Der **erste Spielerablauf und das 40-Karten-Testziel** sind damit benannt, aber keine fertige Funktion und kein dauerhaft bindender Architektur- oder Balancing-Vertrag. Es gibt weiterhin **keinen vorgeschriebenen 7-Phasen-Implementierungsplan**.

Der bereits vor dem Dokumentenimport geschriebene [Card-Battler-Zielplan vom 2026-10-02](../archive/card-battler-target-2026-10-02.md) und die umfangreichen [Chronicles-Battler-Konzepttexte](../character-chronicles/sources/README.md) enthalten fachlich und technisch möglicherweise wertvolle Ideen. Sie sind **Referenzmaterial**, nicht das automatische Architekturmandat für den aktuellen POC.

## Wann sich dieser Status ändert

Ein Test für einen deterministischen Algorithmus bedeutet nicht, dass das zugehörige Spielmodul abgeschlossen ist. Für eine konkrete Integration die dafür zuständigen Services, registrierte API, UI, Persistenz und Tests am neuen Commit prüfen. Bis dahin **POC in Arbeit**.

[ComfyReview-Gesamtstand](../ACTIVE_WORK.md) · [Produktentwicklung](../PROJECT_EVOLUTION.md)
