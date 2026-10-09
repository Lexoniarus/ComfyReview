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

Die weitere Spielmechanik, UI, Datenpersistenz, Integrationsschritte, Spielfeldregeln, Regelversionen, Kartenentwicklung und späterer Einsatz in Character Chronicles werden **durch den POC gelernt und bewertet**. Es gibt in dieser Übersicht **keinen vorgeschriebenen 7-Phasen-Implementierungsplan**.

Der bereits vor dem Dokumentenimport geschriebene [Card-Battler-Zielplan vom 2026-10-02](../archive/card-battler-target-2026-10-02.md) und die umfangreichen [Chronicles-Battler-Konzepttexte](../character-chronicles/sources/README.md) enthalten fachlich und technisch möglicherweise wertvolle Ideen. Sie sind **Referenzmaterial**, nicht das automatische Architekturmandat für den aktuellen POC.

## Wann sich dieser Status ändert

Ein Test für einen deterministischen Algorithmus bedeutet nicht, dass das zugehörige Spielmodul abgeschlossen ist. Für eine konkrete Integration die dafür zuständigen Services, registrierte API, UI, Persistenz und Tests am neuen Commit prüfen. Bis dahin **POC in Arbeit**.

[ComfyReview-Gesamtstand](../ACTIVE_WORK.md) · [Produktentwicklung](../PROJECT_EVOLUTION.md)
