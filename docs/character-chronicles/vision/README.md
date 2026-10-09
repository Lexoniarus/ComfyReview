# Character Chronicles – fachliches Zielbild

**Dokumenttyp:** `WORKING_VISION` · **Stand:** 2026-10-09 · **Geltung:** langfristige Produktidee aus der fortlaufenden ComfyReview-Entwicklung; **kein** fertiger Architekturvertrag, implementiertes Produkt oder fixierter Milestone-Plan.

## Was als Richtung feststeht

ComfyReview ist die **aktuelle, noch in Entwicklung befindliche Anwendung**. Die gewachsene Vision heißt **Character Chronicles**: Bildgenerierung und -bewertung sollen sich langfristig zu einem Spielerlebnis mit Karten, Charakteren, einer sozialen Welt, einem Academy-/Schuljahreskontext und schließlich visuellen Szenen entwickeln. Wie genau das gebaut wird, entscheiden **POCs und tatsächliche Erfahrungen**, nicht ältere technische Konzepte.

Die aktuell beschriebene **Priorität/Abhängigkeit**, ohne starre Release-Gates:

1. **[Card Battler](card-battler.md)** – zuerst ein tatsächlich funktionierender, testbarer Spielkern; aktuell der konkrete POC.
2. **[Social Network](social-network.md)** – soziale Präsenz mit Timeline und Chat-Oberflächen für die Charaktere; noch keine fertig integrierte Funktion.
3. **[Academy und Schuljahr](academy-and-world.md)** – Beziehungen, Welt, Fortschritt und Schuljahresstruktur; kann sich in der Ausarbeitung mit Social überschneiden.
4. **[Visuelle VN](visual-novel.md)** – bewusst zuletzt als aufwendige szenische Präsentation. Freistellung, Matting und konsistente Bildkomposition sind zusätzliche Risiken, die zuvor in kleinen Techniktests erprobt werden dürfen.

Diese Übersicht beschreibt **was und ungefähr in welcher Abhängigkeit**, nicht **wie genau**: Es gibt keine beschlossene Gesamtarchitektur, keine fixierte MVP-Grenze, keine verbindlichen Schemata/M6-Gates und keinen veröffentlichten Zeitplan.

## Wo die Details herkommen

Die [24 ausführlichen importierten Quellfassungen](../sources/README.md) dokumentieren viele Spielideen, konkrete Regelvarianten und technische Überlegungen. Sie mischen frühere ComfyReview-Vorarbeiten, einen verworfenen Character-Chronicle-Codeansatz und neuere inhaltliche Ergänzungen. **Sie sind Quellen**, keine automatisch angenommenen Bauverträge.

Der tatsächlich vorhandene gegenwärtige Code wird in [ComfyReview Active Work](../../ACTIVE_WORK.md) und [Implementation Audit](../../IMPLEMENTATION_AUDIT.md) beschrieben. [Das Audit des früheren Chronicle-Codes](../HISTORICAL_CODE_AUDIT.md) erklärt, was damals existierte, aber nicht weiterverwendet werden muss.

## Nicht automatisch entschieden

Spielfeld-/Deckgrößen, Gameplay-Detailregeln, ein Social-Datenmodell, die endgültige Academy-/Storysimulation, UI-Technologien, LLM-/Retrieval-Architektur, Schema-Migrationen, visuelle Asset-Pipeline, Zeitplan und Meilensteine stehen **nicht** allein durch dieses Zielbild fest. [Offene Entscheidungen](../../OPEN_DECISIONS.md) und [Entscheidungsregeln](../../DECISION_POLICY.md).
