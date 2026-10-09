# Character Chronicles – fachliches Zielbild

**Dokumentklasse:** `WORKING_VISION` · **Stand:** 2026-10-09 · **Geltung:** langfristige Produktidee aus der fortlaufenden ComfyReview-Entwicklung; **kein** fertiger Architekturvertrag, implementiertes Produkt oder fixierter Milestone-Plan.

## Was als Richtung feststeht

ComfyReview ist die **aktuelle, noch in Entwicklung befindliche Anwendung**.
**Character Chronicles besitzt bereits eine fachlich bestätigte Zielwelt:**
Japan/Kobe ab 2032, eine bodenständige Anime-Near-Future, zwei
Academy-Jahre für junge Erwachsene, eine seit Jahren etablierte globale
Social-/Card-Battler-Kultur sowie Figuren mit eigenem Leben, Wissen und
Beziehungen. Eine storygetriebene Visual Novel mit Dating-Sim-Elementen
ist der langfristige emotionale Kern; die spielbaren Karten- und
Social-Systeme sind Teil derselben Welt. **Diese Welt ist nicht nur
möglicher Kontext**, sondern das angestrebte Spielerlebnis. Wie wir es
konkret bauen, klären **POCs und praktische Erfahrungen**.
[Bestätigte Weltbeschreibung](world.md).

Die derzeitige **ungefähre Entwicklungsorientierung** (keine starren
Release-Gates und keine bereits beschlossene Gesamtarchitektur):

1. **[Card Battler](card-battler.md)** – zuerst ein tatsächlich funktionierender Spielkern; aktuell der konkrete POC.
2. **[Timeline](timeline.md)** – als nächster begrenzter, sozialer Interaktions- und Darstellungsslice; Details und Datenmodell noch offen.
3. **[Social Network mit Charakter-Chats](social-network.md)** – die breitere soziale Plattform aufbauend auf beziehungsweise verzahnt mit der Timeline.
4. **[Storyline](storyline.md)** – das bestätigte zweijährige [Academy-Leben](academy-and-world.md), Figurenentwicklung, Beziehungen und Ereignisse erzählerisch miteinander verbinden; **die Academy ist Weltkern, keine zusätzliche technische Pflichtphase**.
5. **[Visual-Novel-Content](visual-novel.md)** – zuletzt die aufwendigen szenischen Inhalte und Präsentationen. Frühere kleine Technik-POCs zu Freistellung, Matting und Bildkomposition bleiben möglich.

**Timeline → Social/Chat** unterscheidet Entwicklungsschwerpunkte, nicht
zwangsläufig zwei unabhängig veröffentlichte Produkte. **Storyline** umfasst
das später zu definierende Erzählsystem. **Die zwei Academy-Jahre gehören
zur bestätigten Spielwelt**; die alten genauen Tages-/Kalender-, M6-
und Datenbankverträge sind nicht dadurch genehmigt.

Diese Übersicht beschreibt **was und ungefähr in welcher Reihenfolge**, nicht
**wie genau**: Kein beschlossener Gesamt-MVP, keine verpflichtenden
historischen Schemas oder M6-Gates, keine fixierten Termine.
[Entwicklungsbegründung](../../PROJECT_EVOLUTION.md).

## Die bestätigte Spielwelt – nicht die technische Roadmap

Die aktuelle [Weltvision](world.md) beschreibt Kobe 2032, Academy-Alltag,
Protagonist und Cast, die gesellschaftliche Social- und Kartenkultur sowie
wie Posts, persönliche Bilder, Duelle und Beziehungen zusammenwirken.
Sie übernimmt den inhaltlichen Kern der ausführlichen Quelltexte als
**Zielbild**, ohne deren konkrete Implementierungsverträge pauschal
wiederherzustellen. **VN-/Story-Content zuletzt entwickeln** beschreibt
nur die Ausbaureihenfolge, nicht die erzählerische Gewichtung im fertigen
Spiel. Fachliche Änderungen an der Welt bleiben nach ausdrücklicher
Neubewertung möglich, nicht als stiller Nebeneffekt technischer POCs.

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

## Späterer fachlicher Meilenstein: Spielwelt und Bildproduktion

Im späteren Character-Chronicles-Spiel müssen die **fiktionale
Weltwahrheit** und die **technische Darstellung/Lernpipeline**
nachvollziehbar getrennt sein. Das ist ein **gewollter späterer
fachlicher Meilenstein**, nicht bereits eine fertige Spielmechanik
und nicht Voraussetzung für den ersten Card-Battler-POC.

Für den **realen Spieler** können Bildauswahl, Bewertungen und
wiederholte Generationen die technische Bildqualität verbessern.
Innerhalb der **Spielwelt** handelt der Protagonist dagegen in
seinem erzählerischen Zusammenhang; Figuren besitzen eigenes Wissen,
Erinnerungen und Beziehungen. Ein besser gerendertes Bild ist
deshalb **nicht automatisch** ein körperlicher Wandel, eine neue
Erinnerung oder ein Ereignis im World Canon.

Anders ist es, wenn eine **explizite, gültige Spiel- oder
Storyentscheidung** eine solche Veränderung bewirkt. Die spätere
Umsetzung muss diese Fälle unterscheiden und spielerseitig
verständlich machen. Der Abnahmepunkt soll also die
**Kontinuität der fiktiven Welt trotz technischer Bildverbesserung**
belegen, ohne die positiven Rückwirkungen der Bilderfahrung auf
das Gesamtspiel zu verlieren.

Dieser Meilenstein steht als [bestätigtes fachliches Ziel](../../CONFIRMED_CONSTRAINTS.md#späterer-fachlicher-meilenstein-spielwelt-und-technische-bildproduktion)
fest. Zeitpunkt, konkreter POC, Benutzeroberfläche, Datenmodell,
KI-Provider und technische Trennmechanismen bleiben offen.
Er ist **keine zusätzliche verbindliche Releasephase** zwischen
Timeline, Social Network, Storyline und VN; die historische
M6-/Guardian-Architektur wird dadurch nicht übernommen.

## Wo die Details herkommen

Die [24 ausführlichen importierten Quellfassungen](../sources/README.md) dokumentieren viele Spielideen, konkrete Regelvarianten und technische Überlegungen. Sie mischen frühere ComfyReview-Vorarbeiten, einen verworfenen Character-Chronicle-Codeansatz und neuere inhaltliche Ergänzungen. **Sie sind Quellen**, keine automatisch angenommenen Bauverträge.

Der tatsächlich vorhandene gegenwärtige Code wird in [ComfyReview Active Work](../../ACTIVE_WORK.md) und [Implementation Audit](../../IMPLEMENTATION_AUDIT.md) beschrieben. [Das Audit des früheren Chronicle-Codes](../HISTORICAL_CODE_AUDIT.md) erklärt, was damals existierte, aber nicht weiterverwendet werden muss.

## Nicht automatisch entschieden

Spielfeld-/Deckgrößen, Gameplay-Detailregeln, ein Social-Datenmodell, konkrete Academy-/Story-Simulationsverfahren, UI-Technologien, LLM-/Retrieval-Architektur, Schema-Migrationen, visuelle Asset-Pipeline, Zeitplan und Meilensteine stehen **nicht** allein durch dieses Zielbild fest. **Die Weltprämisse selbst steht dagegen als Zielvision fest.** [Offene Entscheidungen](../../OPEN_DECISIONS.md) und [Entscheidungsregeln](../../DECISION_POLICY.md).
