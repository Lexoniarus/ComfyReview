# Importierte Quellen – **keine gültigen Produkt- oder Architekturverträge**

**Dokumentklasse:** `SOURCE_MATERIAL` · **Herkunft:** ComfyReview-Konzeptimport vom 2026-10-09 · **Entscheidungsstatus:** ungeprüft, teils historisch, teils inhaltlich weiterverwendbar.

**Hier stehen die vollständigen 24 importierten Fachtexte zur Recherche – nicht die aktuelle, bestätigte Projektdokumentation.** Diese Sammlung enthält zugleich ältere Implementierungs- und Abnahmeaussagen aus einem später verworfenen Character-Chronicle-Ansatz, teils nach dem Archivstand ergänzte Produktideen sowie detaillierte technische Vorschläge. **„Autoritativ“, „verbindlich“, „Baseline abgeschlossen“, „MVP“ und Schema 47–58 sind Originalbegriffe früherer Arbeitsstände – kein aktueller Auftrag.**

## Wohin stattdessen für den gültigen Überblick?

- **[Arbeits-Zielbild](../vision/README.md):** kurze fachliche Richtung, priorisierte Bereiche und offene Punkte.
- **[Laufender ComfyReview-Code](../../ACTIVE_WORK.md):** technische Gegenwart, Generator/Datenbank in Arbeit und Card-Battler-POC.
- **[Code-Ist-Audit](../../IMPLEMENTATION_AUDIT.md):** konkrete Quellcode-/Testbelege.
- **[Quellen- und Versionsabgleich](SOURCE_RELATIONSHIP.md):** für alle 24 Texte Herkunft und technische Altannahmen.
- **[Früherer Character-Chronicle-Code](../HISTORICAL_CODE_AUDIT.md):** wirklich damals vorhandene Funktionen und noch offene damalige Abnahme.

## Vollständige Texte, nach Thema abgelegt

### Karte, Battler und Spielmechanik – Varianten für den aktiven POC

- [Card Crafting und Playground-Kombinationen](card-crafting-and-playground-combination-lifecycle.md)
- [Card Battler: Spielfeld, Kampf](card-battler-board-and-combat-foundation.md)
- [Decks, Züge, Ausspielhandlungen](card-battler-decks-turns-and-actions.md)
- [Zonen, Status, Opcode-Registry](card-battler-zones-statuses-and-opcode-registry.md)
- [Effektgrammatik, LLM-Authoring](card-battler-effect-grammar-and-llm-authoring.md)
- [Runtime-Architektur des früheren Battlers](card-battler-runtime-architecture.md)
- [Card-Art-Komposition](card-art-composition-and-rendering.md)

Diese Quellen enthalten auch **konkrete Regel-/Technikbehauptungen**. Sie sind POC-Kandidaten, nicht automatisch der bestätigte aktuelle Card-Battler-Regelsatz.

### Worldbuilding, Charaktere und langfristiges Erlebnis

- [Welt, VN, Social-Plattform, Kartenloop](vn-social-platform-and-card-loop-concept.md)
- [Story, Cast und Simulation](story-cast-and-simulation.md)
- [Schuljahr, visuelle Portfolios und Beziehungen](school-year-visual-portfolios-and-relationship-contexts.md)
- [Champion-Slots und Character-Decks](champion-slots-and-character-decks.md)
- [Visuelle Assets, Quests und Gates](visual-assets-quests-and-gates.md)
- [Network-first Screen Map](network-first-vn-frontend-screen-map.md)
- [Spielerseitige Begriffe und Tonfall](player-facing-terminology-and-voice.md)
- [Academy-Ende, LoRA-Audit und New Game Plus](year-end-lora-and-new-game-plus.md)

Diese Texte bewahren **inhaltliche Ideen**. Die aktuelle Priorität bleibt trotzdem [Card Battler → Social/Chats → Academy/Schuljahr → visuelle VN zuletzt](../vision/README.md); ältere Quelltexte können andere Reihenfolgen behaupten.

### Alte Foundation-, Generator-, KI-, Daten- und Frontend-Ansätze

- [Baseline und Foundation-Übergabe](baseline-and-entry-gates.md)
- [Technische Zielarchitektur](target-architecture.md)
- [Frontend und Informationsarchitektur](frontend-information-architecture.md)
- [Spielmodi und Guided Evidence](game-modes-and-guided-evidence.md)
- [Generation Profiles und Trials](generation-profiles-and-trials.md)
- [Rolling M6-Lernloop](rolling-m6-learning-loop.md)
- [Bildkarten/Embeddings/LLM-Kontext](deck-building-embeddings-and-llm-context.md)
- [LLM, RAG und Recovery](llm-rag-and-recovery.md)
- [Guardian und Monitoring](orchestration-guardian-and-monitoring.md)

**Hohe Verwechslungsgefahr:** Teile dieses Materials beschreiben Code des verworfenen Chronicle-Ansatzes und enthalten alte „erreicht“, „implementiert“ und „Schema 58“-Aussagen. Die heute entwickelte ComfyReview-Codebasis verwendet dagegen Canonical SQLite **v18** und eine andere aktive Oberfläche; private echte DB-Cutovers sind separat zu prüfen.

## Leseregel für jede einzelne Quelldatei

Jede Quelldatei erhält eine standardisierte Einordnung, danach folgt **der übernommene Originaltext**, dessen alte Autoren- und Verbindlichkeitsaussagen ausschließlich **historisch** gelten. Wenn eine Idee aktuell übernommen werden soll, wird sie nach Prüfung in das [Arbeits-Zielbild](../vision/README.md), in einen [POC](../../pocs/README.md) oder eine [klar begrenzte Entscheidung](../../DECISION_POLICY.md) übertragen – **nicht** durch stilles Umetikettieren eines alten Vertragstextes.

**Originalverweise bleiben Originalverweise:** Die 24 Quellen stammen aus einer
früheren Dokumentstruktur (unter anderem `docs/mvp/product/`). Ihre alten
relativen Links auf Foundation-, M4-/M6- und Bestandsreferenztexte bleiben
**wortgetreu erhalten**, auch wenn die damaligen Ziele **im heutigen
ComfyReview-Repository fehlen**. Sie sind über das frühere
`CharacterChronicle.zip` und den oben verlinkten historischen Code-Audit
nachvollziehbar. Ein Link auf eine heute fehlende historische Quelle ist
**keine Aufforderung**, stattdessen auf die aktuelle `vision/` oder
`README.md` umzuleiten. Solche historischen Linkziele werden beim Prüfen
**getrennt** von der aktiven Navigation ausgewiesen. Auch historische
Kapitelanker werden nicht stillschweigend umgeschrieben.

[Historischer August-Entwurf](../history/full-mvp-draft-2026-08.md) bleibt separat; [älterer Card-Battler-Plan](../../archive/card-battler-target-2026-10-02.md) ebenfalls.
