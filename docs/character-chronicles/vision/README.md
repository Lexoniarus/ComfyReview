# Character Chronicles – fachliches Zielbild

**Dokumentklasse:** `WORKING_VISION` · **Stand:** 2026-10-09 · **Geltung:** langfristige Produktidee aus der fortlaufenden ComfyReview-Entwicklung; **kein** fertiger Architekturvertrag, implementiertes Produkt oder fixierter Milestone-Plan.

## Was als Richtung feststeht

ComfyReview ist die **aktuelle, noch in Entwicklung befindliche Anwendung**. Die gewachsene Vision heißt **Character Chronicles**: Bildgenerierung und -bewertung sollen sich langfristig zu einem Spielerlebnis mit Karten, Charakteren, einer sozialen Welt, einem Academy-/Schuljahreskontext und schließlich visuellen Szenen entwickeln. Wie genau das gebaut wird, entscheiden **POCs und tatsächliche Erfahrungen**, nicht ältere technische Konzepte.

Die derzeitige **ungefähre Entwicklungsorientierung** (keine starren
Release-Gates und keine bereits beschlossene Gesamtarchitektur):

1. **[Card Battler](card-battler.md)** – zuerst ein tatsächlich funktionierender Spielkern; aktuell der konkrete POC.
2. **[Timeline](timeline.md)** – als nächster begrenzter, sozialer Interaktions- und Darstellungsslice; Details und Datenmodell noch offen.
3. **[Social Network mit Charakter-Chats](social-network.md)** – die breitere soziale Plattform aufbauend auf beziehungsweise verzahnt mit der Timeline.
4. **[Storyline](storyline.md)** – Ereignisse, Figurenentwicklung, Beziehungen und Progression in einen erzählerischen Zusammenhang bringen. **[Academy/Schuljahr](academy-and-world.md)** ist dabei ein mögliches Worldbuilding-/Zeitgerüst, keine gesondert beschlossene Pflichtphase.
5. **[Visual-Novel-Content](visual-novel.md)** – zuletzt die aufwendigen szenischen Inhalte und Präsentationen. Frühere kleine Technik-POCs zu Freistellung, Matting und Bildkomposition bleiben möglich.

**Timeline → Social/Chat** unterscheidet Entwicklungsschwerpunkte, nicht
zwangsläufig zwei unabhängig veröffentlichte Produkte. **Storyline** umfasst
das später zu definierende Erzählsystem; die alte Academy-Kalender- und
Zwei-Jahres-Spezifikation ist nicht automatisch beschlossen.

Diese Übersicht beschreibt **was und ungefähr in welcher Reihenfolge**, nicht
**wie genau**: Kein beschlossener Gesamt-MVP, keine verpflichtenden
historischen Schemas oder M6-Gates, keine fixierten Termine.
[Entwicklungsbegründung](../../PROJECT_EVOLUTION.md).

## Ein zusammenhängendes Spielerlebnis, keine drei isolierten Spiele

[Card Battler](card-battler.md), [Timeline und Social Network](social-network.md)
sowie die spätere [Storyline](storyline.md) und
[Visual Novel](visual-novel.md) sollen **ineinandergreifende Spielschleifen**
einer gemeinsamen Welt bilden. Die Entwicklungsreihenfolge legt **nicht**
fest, dass Spielende zwingend dieselbe Reihenfolge durchlaufen müssen.
Unterschiedliche Interessen können später verschiedene **Einstiegspunkte**
ermöglichen: über Karten und ihre Entwicklung, Kontakte und Chats oder
erzählerische Situationen.

Als **Beispiele für einen erst zu erprobenden Zusammenhang** kann eine
gespielte Karte Anlass für eine Social-Interaktion sein, ein Post kann eine
Storysituation eröffnen oder eine erzählerische Entscheidung den Kontext
für spätere Kartenaktivitäten verändern. Diese Beispiele definieren
**noch keine** konkreten Belohnungen, Statusübergänge, Match-/Chat-APIs,
Pflichtabhängigkeiten oder ein festes Freischaltsystem. Die Daten- und
Spielwirkungen müssen für den jeweiligen POC gesondert bestätigt werden.

Die langfristige Absicht ist ein **zusammenhängendes Spielgefühl** und
keine Sammlung bloß verlinkter Werkzeuge. Wie seine verschiedenen
Oberflächen aussehen, welche gemeinsame Zustandslogik benötigt wird und
wie die Übergänge funktionieren, bleibt Gegenstand späterer
Spieler- und Technik-POCs. Die aktuelle ComfyReview-Entwicklungsoberfläche
ist dadurch weder automatisch das Game-Frontend noch zur Ablösung
freigegeben.

## Wo die Details herkommen

Die [24 ausführlichen importierten Quellfassungen](../sources/README.md) dokumentieren viele Spielideen, konkrete Regelvarianten und technische Überlegungen. Sie mischen frühere ComfyReview-Vorarbeiten, einen verworfenen Character-Chronicle-Codeansatz und neuere inhaltliche Ergänzungen. **Sie sind Quellen**, keine automatisch angenommenen Bauverträge.

Der tatsächlich vorhandene gegenwärtige Code wird in [ComfyReview Active Work](../../ACTIVE_WORK.md) und [Implementation Audit](../../IMPLEMENTATION_AUDIT.md) beschrieben. [Das Audit des früheren Chronicle-Codes](../HISTORICAL_CODE_AUDIT.md) erklärt, was damals existierte, aber nicht weiterverwendet werden muss.

## Nicht automatisch entschieden

Spielfeld-/Deckgrößen, Gameplay-Detailregeln, ein Social-Datenmodell, die endgültige Academy-/Storysimulation, UI-Technologien, LLM-/Retrieval-Architektur, Schema-Migrationen, visuelle Asset-Pipeline, Zeitplan und Meilensteine stehen **nicht** allein durch dieses Zielbild fest. [Offene Entscheidungen](../../OPEN_DECISIONS.md) und [Entscheidungsregeln](../../DECISION_POLICY.md).
